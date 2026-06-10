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
from app.models import db, persistent_db, ensure_snapshot_columns
from app.models.resource import Resource
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.users import Users
from app.models.containers import Container
from app.models.softwareContainer import SoftwareContainer
from app.models.software_edit import SoftwareEdit
from app.models.command_edit import CommandEdit
from app.models.banner import Banner
from app.cli_loading import custom_halo
from app.paths import data_dir, state_dir


def website_titles_path():
    return state_dir() / "websites" / "website_titles.json"
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
        raise DataProcessingError(f"CSV parsing failed: {str(pe)}") from pe
    except Exception as e:
        raise DataProcessingError(f"CSV data processing failed: {str(e)}") from e


@custom_halo(text="Fetching remote software data")
def get_remote_data(
    api_key: str,
    software: list[str],
    share_with_devs:bool,
    share_with_others: bool,
    api_data_save_file: str = "app/data/api_response.json"
    ) -> list[dict[str, any]]:
    logger.info(f"Retrieving api data")

    BATCH_SIZE = 75
    all_data = []
        # request software data in batches
    for i in range(0, len(software), BATCH_SIZE):
        batch = software[i:min(i+BATCH_SIZE, len(software))]
        url = f"{app.config["SDS_API_URL"]}api/v1"
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        data = {
            "software": batch,
            "share_with_devs": share_with_devs,
            "verified_only": False,
            "share_with_others": share_with_others
        }

        try:
            # fetch all data if user doesn't want to share with devs
            if not share_with_devs:
                data["software"] = ["*"]
                request = requests.post(url, headers=headers, json=data, timeout=60)
            else:
                request = requests.post(url, headers=headers, json=data, timeout=20)
            if request.status_code == 200:
                batch_data = request.json()
                all_data.extend(batch_data['data'])
                logger.info(f"Successfully retrieved batch {i//BATCH_SIZE + 1}. url: {url}")
            elif request.status_code == 401:
                raise DataProcessingError(f"Unable to fetch data from API: {request.json()}")
            else:
                logger.warning(f"API returned status {request.status_code} for batch {i//BATCH_SIZE+1}. url: {url}, batch data: {batch}")

            # don't loop if we are getting all data
            if not share_with_devs:
                break
        except (requests.ConnectionError, requests.ConnectTimeout) as ex:
            logger.warning(
                f"Unable to retrieve data from api call for batch {i//BATCH_SIZE + 1}: {ex}. Using cached data."
            )
            continue
        except Exception as e:
            logger.error(f"Failed to retrieve data form api:  \n {e}")
            # raise DataProcessingError(f"Failed to retrieve data from api: {str(e)}") from e
    logger.info(
        f"Successfully retrieved data from api call. Length of data is {len(all_data)}."
    )
    if all_data:
        with open(api_data_save_file, "w") as ar:
            json.dump(all_data, ar, indent=4)
        logger.info(f"Successfully updated local copy of api data")
    else:
        try:
            with open(api_data_save_file, "r") as ar:
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
        matches = df[df["software_name"] == s.software_name.lower()]
        if len(matches) == 0:
            logger.debug(f"No remote info found for software: {s.software_name}")
            continue
        if len(matches) > 1:
            logger.warning(
                f"Duplicate remote entries for '{s.software_name}', using first match"
            )
        remote_s_info = matches.iloc[0]

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
                    AISoftwareInfo.insert(**ai_software_info).on_conflict(
                        conflict_target=[AISoftwareInfo.software_id],
                        update={
                            k: v for k, v in ai_software_info.items()
                            if k != "software_id"
                        },
                    ).execute()
                except Exception as e:
                    transaction.rollback()
                    logger.error(
                        f"Error updating AI info remote info: {e}", exc_info=True
                    )
                    raise

def find_site_titles():
    print("Getting link titles...")
    titles_path = website_titles_path()
    titles_path.parent.mkdir(parents=True, exist_ok=True)

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

    site_titles = {}
    if titles_path.exists():
        try:
            with open(titles_path, 'r', encoding='utf-8') as wt:
                site_titles = json.load(wt)
        except Exception as e:
            logger.error(f'Error reading data from {titles_path}. \n error: {e}')

        if site_titles: # if site titles is not empty
            # remove urls for which data already exists
            all_urls = [url for url in all_urls if url not in site_titles]

    total_urls = len(all_urls)
    print(f"{Fore.CYAN}{Style.BRIGHT} INFO:{Style.RESET_ALL} {Fore.YELLOW}Fetching URL site titles, this will take a few minutes{Style.RESET_ALL}")
    print(f"{Fore.BLUE} Processing {total_urls} new unique URLs...{Style.RESET_ALL}")
    print()  # Add blank line before spinner
    # Progress tracking
    completed = 0
    completed_lock = threading.Lock()  # Thread synchronization
    spinner  = Halo(text=f"Processing URLs: 0/{total_urls}", spinner="dots")
    spinner.start()

    # One shared session for the whole batch — connection pooling + retry
    session = requests.Session()
    retry_strategy = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    def get_title_with_progress(url):
        nonlocal completed
        result = get_external_site_title(url, session)
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
    for url, title in zip(all_urls, results):
        site_titles[url] = title

    with open(titles_path, 'w', encoding="utf-8") as wt:
        json.dump(site_titles, wt, indent=4)

    return site_titles

def get_external_site_title(url, session):
    try:
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

@custom_halo(text="Updating example use data")
def update_example_uses(example_use_dir: Path) -> None:
    """
    Updates example usage for software from user provided data
    """
    for file in example_use_dir.iterdir():
        if not file.is_file():
            print(f"Item {file} is not a file. Skipping")

        try:
            file_data = ''
            with open(file, 'r', encoding='utf-8') as f:
                file_data = f.read()

            file_name = file.name
            if file_name.endswith('.md'):
                file_name = file_name[:-len('.md')]

            software = Software.get_or_none(Software.software_name == file_name)
            if software:
                ai_software = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == software)
                if ai_software:
                    ai_software.ai_example_use = file_data
                    updated = ai_software.save()

        except Exception as e:
            print(e)


@custom_halo(text="Applying admin overrides")
def apply_overrides(software_uses_dir: Path) -> None:
    """
    Apply SoftwareEdit overrides to sds_db after a reset.
    Also migrates legacy software_uses markdown files into SoftwareEdit on first run.

    Snapshots auto_values / auto_command from the freshly derived sds_db row
    BEFORE stomping with the override, so revert restores the current
    pipeline value.
    """
    persistent_db.connect(reuse_if_open=True)
    persistent_db.create_tables([SoftwareEdit, CommandEdit, Banner], safe=True)
    ensure_snapshot_columns(persistent_db)

    # One-time migration: import markdown files into SoftwareEdit if not already there
    if software_uses_dir.exists() and software_uses_dir.is_dir():
        for md_file in software_uses_dir.glob("*.md"):
            sw_name = md_file.stem
            try:
                edit = SoftwareEdit.get(SoftwareEdit.software_name == sw_name)
                if edit.ai_example_use is None:
                    edit.ai_example_use = md_file.read_text(encoding="utf-8")
                    edit.save()
            except SoftwareEdit.DoesNotExist:
                SoftwareEdit.create(
                    software_name=sw_name,
                    ai_example_use=md_file.read_text(encoding="utf-8"),
                )

    sw_field_map = [
        ("description", "software_description"),
        ("web_page", "software_web_page"),
        ("documentation", "software_documentation"),
        ("use_link", "software_use_link"),
    ]
    ai_fields = [
        "ai_description", "ai_software_type", "ai_software_class",
        "ai_research_field", "ai_research_area", "ai_research_discipline",
        "ai_core_features", "ai_general_tags", "ai_example_use",
    ]

    for edit in SoftwareEdit.select():
        sw = Software.get_or_none(Software.software_name == edit.software_name)
        if sw is None:
            continue

        try:
            snapshots = json.loads(edit.auto_values) if edit.auto_values else {}
        except (json.JSONDecodeError, TypeError):
            snapshots = {}
        snapshots_changed = False

        sw_changed = False
        for edit_field, sw_field in sw_field_map:
            val = getattr(edit, edit_field)
            if val is not None:
                snapshots[edit_field] = getattr(sw, sw_field, "") or ""
                snapshots_changed = True
                setattr(sw, sw_field, val)
                sw_changed = True
        if sw_changed:
            sw.save()

        ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
        if ai is not None:
            ai_changed = False
            for field in ai_fields:
                val = getattr(edit, field)
                if val is not None:
                    snapshots[field] = getattr(ai, field, "") or ""
                    snapshots_changed = True
                    setattr(ai, field, val)
                    ai_changed = True
            if ai_changed:
                ai.save()

        if snapshots_changed:
            edit.auto_values = json.dumps(snapshots) if snapshots else None
            edit.save()

    for cmd_edit in CommandEdit.select():
        if cmd_edit.command is None:
            continue
        sw = Software.get_or_none(Software.software_name == cmd_edit.software_name)
        if sw is None:
            continue
        try:
            resource = Resource.get(Resource.resource_name == cmd_edit.resource_name)
            sr = SoftwareResource.get(
                (SoftwareResource.software_id == sw.id) &
                (SoftwareResource.resource_id == resource.id) &
                (SoftwareResource.software_version == cmd_edit.software_version)
            )
            cmd_edit.auto_command = sr.command or ""
            cmd_edit.save()
            sr.command = cmd_edit.command
            sr.save()
        except (Resource.DoesNotExist, SoftwareResource.DoesNotExist):
            continue


def setup_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete and recreate the database using data provided in the input_dir directory.\
        All files for each argument (with the exception of csv files) must be within subdirectories.\
        The name of each subdirectory should be the name of a resource to which the files belong."
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
    parser.add_argument(
        "--software_use_dir",
        "-s_u_d",
        help="Directory containing a text (markdown) file with instructions on how to use a specific software. Read the data preparation section of the README.md file for more info. Default: ./software_uses/"
    )

    args = parser.parse_args()

    return args


def main() -> None:
    init()  # initialize colorama (cross-platform terminal colors)
    args = setup_argparse()

    if not any([args.spider_dir, args.container_dir, args.csv_file]):
        logger.error("No input data location provided.")
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

        # Inputs are optional: deployments may provide any subset, so a
        # missing location is skipped with a warning rather than fatal.
        if args.spider_dir:
            spider_path = Path(args.spider_dir).resolve()
            if spider_path.is_dir():
                process_spider_data(spider_path, blacklist)
            else:
                logger.warning(f"{spider_path} is not a directory, skipping spider data")

        if args.container_dir:
            container_path = Path(args.container_dir).resolve()
            if container_path.is_dir():
                # parse_container_files(container_path)
                process_container_data(container_path, blacklist)
            else:
                logger.warning(f"{container_path} is not a directory, skipping container data")

        if args.csv_file:
            csv_path = Path(args.csv_file).resolve()
            if csv_path.is_file():
                process_csv_data(csv_path, blacklist)
            else:
                logger.warning(f"{csv_path} is not a file, skipping CSV data")

        if app.config["USE_API"]:
            api_key = app.config["API_KEY"]
            if api_key:
                with db.atomic():
                    all_software = Software.select()
                software = [software.software_name for software in all_software]
                logger.info("Starting API data update")
                remote_data = get_remote_data(
                    api_key,
                    software,
                    app.config["SHARE_WITH_DEVS"],
                    app.config["SHARE_WITH_OTHERS"]
                )
                if remote_data:
                    update_db_from_remote(remote_data)
            else:
                logger.warning(
                    "SDS API key not found in environment variables. Skipping API data update."
                )

        if args.software_use_dir:
            software_use_path = Path(args.software_use_dir)
        else:
            software_use_path = data_dir() / "software_uses"
        if software_use_path.is_dir():
            logger.info("Found software uses directory. Attempting to parse")
            update_example_uses(software_use_path)
        elif args.software_use_dir:
            logger.warning(f"{software_use_path} is not a directory, skipping example use data")

        apply_overrides(software_use_path)

        logger.info("Creating admin user")
        hashed_password = app.config["DEFAULT_PASS"]
        username = app.config["DEFAULT_USER"]
        Users.create(username=username, password=hashed_password, is_admin=True)
        logger.info("Database processing completed successfully")

        # Save last updated time to file
        EST = pytz.timezone('US/Eastern')
        with open(LAST_UPDATED_PATH, 'w') as f:
            f.write(str(datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S")))

        find_site_titles()
    except Exception as e:
        logger.error(f"Fatal error occurred: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
