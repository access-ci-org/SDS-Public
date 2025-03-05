import argparse, json, sys, logging
from pathlib import Path
from typing import Optional
from peewee import Model

import requests
import pandas as pd

from app import app
from app.models import db
from app.models.resource import Resource
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.userReports import UserReports
from app.models.users import Users
from app.models.containers import Container
from app.models.softwareContainer import SoftwareContainer
from app.logic.parse_spider import parse_spider_output
from app.logic.parse_containers import parse_container_files
from app.cli_loading import custom_halo
from app.app_logging import logger


class DataProcessingError(Exception):
    """Custom exception for data processing error"""

    def __init__(
        self, message: str, level: int = logging.ERROR, exec_info: Exception = None
    ):
        super().__init__(message)
        self.level = level
        self.exec_info = exec_info
        # Log the error when it's created
        logger.log(self.level, message, exc_info=exec_info)


@custom_halo(text="Recreating database tables")
def recreate_table() -> None:
    logger.info("Starting database table recreation")
    db.connect(reuse_if_open=True)
    tables = [
        Resource,
        Software,
        SoftwareResource,
        AISoftwareInfo,
        Users,
        Container,
        SoftwareContainer,
    ]
    with db.atomic() as transaction:
        try:
            logger.info("Dropping existing tables")
            db.drop_tables(tables)
            logger.info("Creating new tables")
            db.create_tables(tables)
            if not "userreports" in db.get_tables():
                logger.info("Creating UserReports table")
                db.create_tables([UserReports])
            logger.info("Successfully recreated all tables")
        except Exception as e:
            transaction.rollback()
            logger.error(f"Error recreating tables: {e}", exc_info=True)
            raise


def clean_versions(version_string: str) -> str:
    logger.debug(f"Cleaning version string: {version_string}")
    versions = [v.strip() for v in str(version_string).split(",") if v.strip()]
    unqiue_versions = sorted(set(versions))
    return ", ".join(unqiue_versions)


def update_software_resource(
    software_id: Model, resource_id: Model, versions: str
) -> Model:
    logger.debug(
        f"Updating software resource. Software ID: {software_id}, Resource ID: {resource_id}"
    )
    try:
        sr_id, created = SoftwareResource.get_or_create(
            software_id=software_id, resource_id=resource_id
        )
        final_versions = (
            versions
            if created
            else clean_versions(f"{sr_id.software_version}, {versions}")
        )
        logger.info(
            f"{'Creating' if created else 'Updating'} software resource with versions: {final_versions}"
        )
        (
            SoftwareResource.update(
                {SoftwareResource.software_version: final_versions}
            ).where(SoftwareResource.id == sr_id)
        ).execute()

        return sr_id
    except Exception as e:
        logger.error(f"Error updating software resource: {e}", exc_info=True)
        raise e


def process_software(
    name: str, blacklist: set[str], description: Optional[str] = None
) -> Model:
    logger.debug(f"Processing software: {name}")
    try:
        name = name.lower()
        if name in blacklist:
            raise DataProcessingError(
                f"Software {name} is blacklisted. Skipping", level=logging.WARNING
            )

        existing_software = Software.get_or_none(Software.software_name == name)

        if existing_software:
            # Add description if it doesn't exit
            if description and not existing_software.software_description:
                logger.info(f"Updating description for software: {name}")
                (
                    Software.update({Software.software_description: description})
                    .where(Software.id == existing_software)
                    .execute()
                )
            return existing_software

        logger.info(f"Create new software entry: {name}")
        # Add new software
        software_data = {
            "software_name": name,
            "software_description": description or "",
        }
        software_id = Software.insert(software_data).execute()
        return Software.get_by_id(software_id)

    except DataProcessingError:
        raise  # its already logged just raise the error again
    except Exception as e:
        raise DataProcessingError(
            f"Unexpected error processign software {name}",
            level=logging.ERROR,
            exec_info=e,
        ) from e


def get_container_name(c_info: dict[str, any]) -> str:
    logger.debug(f"Getting container name from info: {c_info}")
    if c_info.get("container_name"):
        return c_info["container_name"]

    file_path = c_info.get("definition_file") or c_info.get("container_file")
    if not file_path:
        raise DataProcessingError("No container name or file information found")
    return file_path.split("/")[-1].split(".")[0]


def process_container(container_info: dict[str, any], container_name: str) -> Model:
    logger.debug(f"Processing container: {container_name}")
    try:
        container_data = {
            "container_name": container_name,
            "definition_file": container_info.get("definition_file", ""),
            "container_file": container_info.get("container_file", ""),
            "resource_id": container_info.get("resource_id", ""),
            "notes": container_info.get("notes", ""),
        }

        container = Container.get_or_none(
            Container.container_name == container_data["container_name"],
            Container.resource_id == container_data["resource_id"],
        )

        if not container:
            logger.info(f"Creating new container: {container_name}")
            container = Container.insert(container_data).execute()
        else:
            logger.info(f"Found existing container: {container_name}")

        return container
    except Exception as e:
        logger.error(f"Error processing container {container_name}: {e}", exc_info=True)
        raise


def update_software_container(
    software_id: Model, container_id: Model, resource_id: Model, versions: str
) -> None:
    logger.debug(
        f"Updating software container. Software ID: {software_id}, Container ID: {container_id}"
    )
    try:
        sc_id, created = SoftwareContainer.get_or_create(
            software_id=software_id, container_id=container_id
        )
        final_versions = (
            versions
            if created
            else clean_versions(f"{sc_id.software_versions}, {versions}")
        )

        logger.info(
            f"{'Creating' if created else 'Updating'} software container with versions: {final_versions}"
        )
        (
            SoftwareContainer.update(
                {SoftwareContainer.software_versions: final_versions}
            )
            .where(SoftwareContainer.id == sc_id)
            .execute()
        )
    except Exception as e:
        logger.error(f"Error updating software container: {e}", exc_info=True)
        raise e


@custom_halo(text="Processing moduel spider data")
def process_spider_data(spider_path: Path, blacklist: set[str]) -> None:
    logger.info(f"Processing spider data from: {spider_path}")
    try:
        data = parse_spider_output(spider_path)
        with db.atomic():
            for resource, software_info in data.items():
                logger.debug(f"Processing resource: {resource}")
                r_id, _ = Resource.get_or_create(resource_name=resource)

                for s_info in software_info:
                    try:
                        s_id = process_software(
                            s_info["name"], blacklist, s_info.get("description")
                        )
                        update_software_resource(
                            s_id, r_id, ", ".join(s_info["versions"])
                        )
                    except DataProcessingError as e:
                        logger.warning(f"Skipping entry: {str(e)}")
                        continue
    except Exception as e:
        raise DataProcessingError(f"Spider data processnig failed: {str(e)}") from e


@custom_halo(text="Processing container data")
def process_container_data(container_dir_path: Path, blacklist: set[str]) -> None:
    logger.info(f"Processing container data from: {container_dir_path}")
    # container_data = parse_container_files(container_dir_path)
    try:
        container_data = parse_container_files(container_dir_path)
        with db.atomic():
            for resource, container_info in container_data.items():
                logger.debug(f"Processing resource: {resource}")
                r_id, _ = Resource.get_or_create(resource_name=resource)

                for c_info in container_info:
                    try:
                        c_info["resource_id"] = r_id
                        container_name = get_container_name(c_info)
                        c_id = process_container(c_info, container_name)

                        s_id = process_software(c_info["software_name"], blacklist)
                        update_software_resource(
                            s_id, r_id, c_info["software_versions"]
                        )

                        update_software_container(
                            s_id, c_id, r_id, c_info["software_versions"]
                        )
                    except DataProcessingError as e:
                        logger.warning(
                            f"Skipping container/software entry: {c_info} \n{str(e)}"
                        )
                        continue
    except Exception as e:
        raise DataProcessingError(f"Container data processing failed: {str(e)}") from e


@custom_halo(text="Processing csv data")
def process_csv_data(csv_path: Path, blacklist: set[str]) -> None:
    logger.info(f"Processing CSV data from: {csv_path}")
    try:
        df = pd.read_csv(csv_path, skipinitialspace=True)

        # additional whitespace cleaning
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        with db.atomic():
            # process data in chunks for better memory usage
            for chunk in df.groupby(df.index // 1000):
                logger.debug(f"Processing chunk of {len(chunk[1])} rows")
                for _, row in chunk[1].iterrows():
                    try:
                        resource_id, created = Resource.get_or_create(
                            resource_name=row["resource"]
                        )
                        software_id = process_software(
                            row["software"], blacklist, row["software_description"]
                        )
                        update_software_resource(
                            software_id, resource_id, row["software_versions"]
                        )
                    except DataProcessingError as e:
                        logger.warning(f"Skipping CSV entry: {row} \n {str(e)}")
                        continue
                    except KeyError as ke:
                        logger.error(f"Missing required column: {ke}")
                        raise DataProcessingError(
                            f"CSV format error: missing column {ke}. Could be a space issue"
                        ) from ke
    except pd.errors.EmptyDataError as ede:
        raise DataProcessingError("CSV file is empty") from ede
    except pd.errors.ParserError as pe:
        raise DataProcessingError(f"CSV parsing failed: {str(e)}") from pe
    except Exception as e:
        raise DataProcessingError(f"CSV data processing failed: {str(e)}") from e


@custom_halo(text="Fetching remote software data")
def get_remote_data(api_key: str) -> dict[str, any]:
    logger.info(f"Retreving api data")
    try:
        request = requests.get(
            f"http://128.163.202.84:8080/api=API_0/{api_key}/software=*", timeout=2000
        )
        data = request.json()
        logger.info(
            f"Successfully retrievied data from api call. Lenght of data is {len(data)}"
        )
        if len(data):
            with open("app/models/api_response.json", "w+") as ar:
                ar.write(str(data))
            logger.info(f"Successfully updated local copy of api data")
        return data
    except ConnectionError as ce:
        logger.warning(
            f"Unable to retrieve data from api call: {ce}. Using cached data."
        )

        with open("app/models/api_response.json", "r") as ar:
            api_response = json.load(ar)
        return api_response
    except Exception as e:
        raise DataProcessingError(f"Failed to retreive data from api: {str(e)}") from e


@custom_halo(text="Updating database from remote data")
def update_db_from_remote(remote_data: dict[str, any]) -> None:
    logger.info(
        f"Updating DB from remote. USE_API: {app.config['USE_API']}, USE_AI_INFO: {app.config['USE_AI_INFO']}"
    )
    software = Software.select()
    df = pd.DataFrame(remote_data)

    for s in software:
        try:
            remote_s_info = df[
                df["software_name"] == s.software_name.lower()
            ].squeeze()  # ensure there is exactly one item that matches, otherwise return an error
        except IndexError:
            logger.debug(f"No remote info found for software: {s.software_name}")
            continue

        if remote_s_info.empty:
            logger.debug(f"Empty remote info for software: {s.software_name}")
            continue

        if app.config["USE_CURATED_INFO"]:
            # logger.info(f"Updating curated info for software: {s.software_name}")
            software_update_data = {
                "software_web_page": remote_s_info["software_web_page"],
                "software_documentation": remote_s_info["software_documentation"],
                "software_use_link": remote_s_info["software_use_link"],
            }
            if not s.software_description:
                software_update_data["software_description"] = remote_s_info[
                    "software_description"
                ]
            with db.atomic() as transaction:
                try:
                    software_query = Software.update(**software_update_data).where(
                        Software.id == s.id
                    )
                    software_query.execute()
                except Exception as e:
                    transaction.rollback()
                    logger.error(
                        f"Error updating software from remote info: {e}", exc_info=True
                    )
                    raise

        if app.config["USE_AI_INFO"]:
            # logger.info(f"Updating AI info for software: {s.software_name}")
            ai_software_info = {
                "software_id": s.id,
                "ai_description": remote_s_info["ai_description"],
                "ai_software_type": remote_s_info["ai_software_type"],
                "ai_software_class": remote_s_info["ai_software_class"],
                "ai_research_field": remote_s_info["ai_research_field"],
                "ai_research_area": remote_s_info["ai_research_area"],
                "ai_research_discipline": remote_s_info["ai_research_discipline"],
                "ai_core_features": remote_s_info["ai_core_features"],
                "ai_general_tags": remote_s_info["ai_general_tags"],
                "ai_example_use": remote_s_info["ai_example_use"],
            }
            with db.atomic() as transaction:
                try:
                    AISoftwareInfo.create(**ai_software_info)
                except Exception as e:
                    transaction.rollback()
                    logger.error(
                        f"Error updating AI info remote info: {e}", exc_info=True
                    )
                    raise


def setup_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete and recreate the database using data provided in the input_dir directory.\
        All files for each arguement (with the exception of csv files) must be within subdirectories.\
        The name of each subdirecory should be the name of a resource to which the files belong."
    )
    parser.add_argument(
        "-s_d",
        "--spider_dir",
        help="Location of directory with lmod 'module spider' outputs",
    )
    parser.add_argument(
        "-c_d",
        "--container_dir",
        help="Location of directory with container definitions or csv files. \
                        All csv files must have a software_name and (container_file or definition_file) columns. Here is the complete list of supported \
                        columns: software_name, software_versions, container_name, definition_file, container_file, container_description, \
                        notes. If no container_name is provided then the definition_file name will be used as container name",
    )
    parser.add_argument(
        "-csv_f",
        "--csv_file",
        help="Location of csv file with pre-parsed data. The first row must have column names \
                        and the following columns are necessary but only the software column needs any data: software, resource, software_description, software_versions.",
    )

    args = parser.parse_args()

    return args


def main() -> None:
    args = setup_argparse()

    if not any([args.spider_dir, args.container_dir, args.csv_file]):
        logger.error("No input data location provided")
        print(
            "Must include at least one argument with data location. Pass in --help for more info."
        )
        sys.exit(1)

    try:
        # load blacklist
        logger.info("Loading software blacklist")
        with open("software_blacklist.txt", "r", encoding="utf-8") as sb:
            blacklist = set(line.lower() for line in sb.read().splitlines())
        logger.info(f"Loaded {len(blacklist)} blacklisted items")
    except FileNotFoundError:
        blacklist = {}
        logger.warning("No software blacklist found")

    try:
        logger.info("Starting database processing")
        recreate_table()

        if args.spider_dir:
            spider_path = Path(args.spider_dir).resolve()
            if spider_path.is_dir():
                process_spider_data(spider_path, blacklist)
            else:
                logger.error(f"{spider_path} is not a directory")
                sys.exit(1)

        if args.container_dir:
            container_path = Path(args.container_dir).resolve()
            if container_path.is_dir():
                # parse_container_files(container_path)
                process_container_data(container_path, blacklist)
            else:
                logger.error(f"{container_path} is not a directory")
                sys.exit(1)

        if args.csv_file:
            csv_path = Path(args.csv_file).resolve()
            if csv_path.is_file():
                process_csv_data(csv_path, blacklist)
            else:
                logger.error(f"{csv_path} is not a file")
                sys.exit(1)

        if app.config["USE_API"]:
            api_key = app.config["API_KEY"]
            if api_key:
                logger.info("Starting API data update")
                remote_data = get_remote_data(api_key)
                update_db_from_remote(remote_data)
            else:
                logger.warning(
                    "SDS API key not found in environment variables. Skipping API data update."
                )

        logger.info("Creating admin user")
        hashed_password = app.config["DEFAULT_PASS"]
        username = app.config["DEFAULT_USER"]
        Users.create(username=username, password=hashed_password, is_admin=True)
        logger.info("Database processing completed successfully")

    except Exception as e:
        logger.error(f"Fatal error occurred: {str(e)}", exc_info=True)
        raise e


if __name__ == "__main__":
    main()
