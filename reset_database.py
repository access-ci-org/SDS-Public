import argparse, json, sys, threading, re
from pathlib import Path
import pytz
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore, Style

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from bs4 import BeautifulSoup
from halo import Halo



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
from app.cli_loading import custom_halo
from app.app_logging import logger
from parsers.exceptions import DataProcessingError
from parsers.utils import process_software, update_software_resource
from parsers.lmod.process_spider_output import process_spider_data
from parsers.container.process_container_file import process_container_data

LAST_UPDATED_PATH = 'app/static/last_updated.txt'

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


@custom_halo(text="Processing csv data")
def process_csv_data(csv_path: Path, blacklist: set[str]) -> None:
    logger.info(f"Processing CSV data from: {csv_path}")
    try:
        # Check if file is empty
        if csv_path.stat().st_size == 0:
            return
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
def get_remote_data(api_key: str, software: list[str], share:bool) -> list[dict[str, any]]:
    logger.info(f"Retreving api data")

    BATCH_SIZE = 75
    all_data = []
        # request software data in batches
    for i in range(0, len(software), BATCH_SIZE):
        batch = software[i:min(i+BATCH_SIZE, len(software))]
        software_param = "+".join(batch)
        url = f"http://128.163.202.84:8080/API_0.1/{api_key}/software={software_param},share={share}"
        try:
            request = requests.get(url, timeout=20)
            if request.status_code == 200:
                batch_data = request.json()
                all_data.extend(batch_data)
                logger.info(f"Successfully retrieved batch {i//BATCH_SIZE + 1}")
            elif request.status_code == 401:
                raise DataProcessingError(f"Unable to fetch data from API: {request.json()}")
        except (requests.ConnectionError, requests.ConnectTimeout) as ex:
            logger.warning(
                f"Unable to retrieve data from api call for batch {i//BATCH_SIZE + 1}: {ex}. Using cached data."
            )
            continue
        except Exception as e:
            raise DataProcessingError(f"Failed to retreive data from api: {str(e)}") from e
    logger.info(
        f"Successfully retrievied data from api call. Length of data is {len(all_data)}"
    )
    if all_data:
        with open("app/models/api_response.json", "w+") as ar:
            json.dump(all_data, ar, indent=4)
        logger.info(f"Successfully updated local copy of api data")
    else:
        try:
            with open("app/models/api_response.json", "r") as ar:
                api_response = json.load(ar)
            return api_response
        except FileNotFoundError as FNE:
            logger.warning(
                f"Unable to find cached data"
            )
    return all_data


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
                "ai_description": remote_s_info["ai_description"] or "",
                "ai_software_type": remote_s_info["ai_software_type"] or "",
                "ai_software_class": remote_s_info["ai_software_class"] or "",
                "ai_research_field": remote_s_info["ai_research_field"] or "",
                "ai_research_area": remote_s_info["ai_research_area"] or "",
                "ai_research_discipline": remote_s_info["ai_research_discipline"] or "",
                "ai_core_features": remote_s_info["ai_core_features"] or "",
                "ai_general_tags": remote_s_info["ai_general_tags"] or "",
                "ai_example_use": remote_s_info["ai_example_use"] or "",
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

WEBSITE_TITLES = 'app/data/website_titles.json'
def find_site_titles():
    print("Getting link titles...")
    link_columns = [
        "Software Documentation",
        "Software's Web Page",
        "Example Software Use"
    ]

    # df = get_display_table()
    all_urls = set()
    links = []
    links.extend([soft.software_web_page for soft in Software.select().where(Software.software_web_page != '')])
    links.extend([soft.software_documentation for soft in Software.select().where(Software.software_documentation != '')])
    links.extend([soft.software_use_link for soft in Software.select().where(Software.software_use_link != '')])

    for link in links:
        if isinstance(link, str) and "\n" in link:
            # Split on newlines and add each link
            urls = [link.strip() for link in link.split("\n") if link.strip()]
            all_urls.update(urls)
        else:
            # Single URL
            all_urls.add(link)

    all_urls = [url for url in all_urls if url and str(url).strip()]
    total_urls = len(all_urls)
    print(f"{Fore.CYAN}{Style.BRIGHT}📢 INFO:{Style.RESET_ALL} {Fore.YELLOW}Fetching URL site titles, this will take a few minutes{Style.RESET_ALL}")
    print(f"{Fore.BLUE}🔗 Processing {total_urls} unique URLs...{Style.RESET_ALL}")
    print()  # Add blank line before spinner
    # Progress tracking
    completed = 0
    completed_lock = threading.Lock()  # Thread synchronization
    spinner  = Halo(text=f"Processing URLs: 0/{total_urls}", spinner="dots")
    spinner.start()

    def get_title_with_progress(url):
        nonlocal completed
        result = get_external_site_title(url)
        with completed_lock: # to avoid race conditions when incrementing
            completed += 1
            spinner.text = (f"Processing URLs: {completed}/{total_urls}")
        return result

    try:
        # Process with threading
        with ThreadPoolExecutor(max_workers=30) as executor:
            results = list(executor.map(get_title_with_progress, all_urls))

        spinner.succeed(f"Completed processing {total_urls} URLs")

    except Exception as e:
        spinner.fail(f"Failed to process URLs: {str(e)}")
        raise

    # Map results back to URLs
    site_titles = {}
    for url, title in zip(all_urls, results):
        site_titles[url] = title

    with open(WEBSITE_TITLES, 'w', encoding="utf-8") as wt:
        json.dump(site_titles, wt, indent=4)

    return site_titles

def get_external_site_title(url):
    try:
        # Session with connection pooling
        session = requests.Session()
        retry_strategy = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = session.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')

        if title_tag:
            title = re.sub(r'\s+', ' ', title_tag.get_text().strip())
            return title if title else ''
        return ''

    except Exception:
        return ""

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
                        All csv files must have a container_file or definition_file columns. Here is the complete list of supported \
                        columns: software_name, software_versions, container_name, definition_file, container_file, notes. If no container_name \
                        is provided then the definition_file name will be used as container name",
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
                # sys.exit(1)

        if app.config["USE_API"]:
            api_key = app.config["API_KEY"]
            if api_key:
                with db.atomic():
                    all_software = Software.select()
                software = [software.software_name for software in all_software]
                logger.info("Starting API data update")
                remote_data = get_remote_data(api_key, software, app.config["SHARE_SOFTWARE"])
                if remote_data:
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

        # Save last updated time to file
        EST = pytz.timezone('US/Eastern')
        with open(LAST_UPDATED_PATH, 'w') as f:
            f.write(str(datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S")))

        init() # initialize colorama
        find_site_titles()
    except Exception as e:
        logger.error(f"Fatal error occurred: {str(e)}", exc_info=True)
        raise e


if __name__ == "__main__":
    main()
