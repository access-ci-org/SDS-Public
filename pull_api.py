import time, requests, datetime, os, yaml, re, json, threading
import pandas as pd
import pytz # Timezone
from halo import Halo
from colorama import init, Fore, Style # print colored message to console
from app.logic.table import TableInfo, get_display_table
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Assign relative paths
FINAL_TABLE = 'app/data/final.csv'
LAST_UPDATED_PATH = 'app/static/last_updated.txt'
WEBSITE_TITLES = 'app/data/website_titles.json'

# Load API key and version from config file
try:
    with open("config.yaml", "r") as c:
        config = yaml.safe_load(c)

    api_conf = config["api"]
    API_KEY = api_conf.get("api_key")
    API_VERSION = api_conf.get("version")

    # Check if API key and version are present
    if not API_KEY or not API_VERSION:
        print("API Key or Version not found in config.yaml")
        exit(1)
except FileNotFoundError as e:
    print(f"Unable to find config file config.yaml: {e}")
    exit(1)
except KeyError as ke:
    print(f"Required config keys not found. {ke}")
    exit(1)
except Exception as e:
    print(f"Error while trying to read config file: {e}")
    exit(1)


# Load software blacklist
with open('software_blacklist.txt', 'r') as f:
    software_blacklist = f.read().splitlines()

# Initialize TableInfo object
table_info = TableInfo()


def print_status_message(status_code):
    """Prints a message based on the status code of the API response.
    Args:
        status_code (int): The status code of the API response.
    Returns:
        None
    """
    status_messages = {
        400: "400 Error: Bad request.",
        401: "401 Error: Unauthorized access. API Key is invalid.",
        404: "404 Error: Resource not found.",
        500: "500 Error: Internal server error."
    }
    print(status_messages.get(status_code, f"Unexpected status code: {status_code}"))


def fetch_data(software_api: str = f'https://ara-db.ccs.uky.edu/{API_VERSION}/{API_KEY}/software=*,exclude=ai_example_use,type=json'):
    """
    Fetches software table from ARA_SDS API and saves it to app/data/final.csv

    Args:
        software_api (str): API endpoint to grab software table from

    Returns:
        None
    """
    try:
        response = requests.get(software_api) # Grab API from web, 10s timeout
        if response.status_code == 200:
            print("Successfully grabbed software table from API")
            data = response.json()
            create_table(data)

        else:
            print_status_message(response.status_code)
    except Exception as e:
        print("Failed to grab software table from API")
        print(e)

def fetch_example_use(software_api: str = f'https://ara-db.ccs.uky.edu/{API_VERSION}/{API_KEY}/software=*,include=ai_example_use,type=json'):
    """
    Fetches example uses from ARA_SDS API and saves them as json files in examples_uses/

    Args:
        software_api (str): API endpoint to grab example_uses from

    Returns:
        None
    """
    try:
        response = requests.get(software_api) # Grab API from web, 10s timeout
        if response.status_code == 200:
            print("Successfully grabbed example uses from API")
            data = response.json()

            # Create example_uses directory if it doesn't exist
            if not os.path.exists('example_uses/'):
                os.mkdir('example_uses/')

            # Iterate through software
            for software in data:
                if software['software_name'] not in software_blacklist:
                    path = 'example_uses/' + software['software_name'] + '.txt'
                    example_use = software['ai_example_use']
                    # Replace literal "\n" with actual newline characters
                    example_use = example_use.replace("\\n", "\n")

                    with open(path, 'w') as f:
                        f.write(example_use)
        else:
            print_status_message(response.status_code)
    except Exception as e:
        print("Failed to grab example uses from API")
        print(e)


def create_table(data: list, table: str = FINAL_TABLE):
    """
    Takes API data and converts it to a pandas dataframe, which is then formatted and saved to a csv

    Args:
        data (list): List of dictionaries containing API data
        table (str): Path to final CSV table

    Returns:
        None
    """

    # Initialize dataframe with json data from API
    df = pd.DataFrame(data)

    # Convert lists to strings separated by newlines
    arr_columns = ['rp_name', 'rp_group_id', 'rp_software_documentation', 'software_versions'] # API Columns that return multivalues as list
    df = arr_col_to_str(df, arr_columns)

    # Fix spelling of RP names
    df = fix_rp_names(df)

    # Add empty column for AI Example Use
    df['ai_example_use'] = pd.Series(None)

    # Ensure all column names are functional with the rest of the codebase
    df.rename(columns=table_info.column_names, inplace=True)

    # Create data directory if it doesn't exist
    if not os.path.exists('app/data/'):
        os.mkdir('app/data/')

    # Convert final dataframe to csv
    df.to_csv(FINAL_TABLE, index=False)


def arr_col_to_str(df: pd.DataFrame, arr_cols: list):
    """
    Converts lists to strings separated by newlines in specified columns

    Args:
        df (pd.DataFrame): Dataframe containing API data
        arr_cols (list): List of columns that send multivalues as lists

    Returns:
        df (pd.DataFrame): Dataframe with specified columns converted to strings
    """

    for col in arr_cols:
        df[col] = df[col].apply(lambda x: '\n'.join(x) if isinstance(x, list) else x)

    return df

def fix_rp_names(df: pd.DataFrame):
    """
    Fixes RP names in rp_name and software_versions columns to corrected spelling

    Args:
        df (pd.DataFrame): Dataframe containing API data

    Returns:
        df (pd.DataFrame): Dataframe containing API data with corrected RP names
    """
    # Define replacement dictionary
    replace_dict = {
        r'\baces\b': 'ACES',
        r'\banvil\b': 'Anvil',
        r'\bbridges-2\b': 'Bridges-2',
        r'\bdelta\b': 'Delta',
        r'\bderecho\b': 'Derecho',
        r'\bexpanse\b': 'Expanse',
        r'\bfaster\b': 'FASTER',
        r'\bjetstream2\b': 'Jetstream2',
        r'\bkyric\b': 'KyRIC',
        r'\bookami\b': 'Ookami',
        r'\bstampede3\b': 'Stampede3',
        r'\bdeltaai\b': 'DeltaAI',
    }

    # Fix spelling of RP names in rp_name and software_version columns
    columns = ['rp_name', 'software_versions']
    for col in columns:
        df[col] = df[col].replace(replace_dict, regex=True) # TODO: Fix in rp_software_documentation column without breaking links

    return df

def find_site_titles():
    print("Getting link titles...")
    link_columns = [
        "Software Documentation",
        "Software's Web Page",
        "Example Software Use"
    ]

    df = get_display_table()

    # Collect and deduplicate URLs
    all_urls = set()
    for col in link_columns:
        for value in df[col].dropna():
            if isinstance(value, str) and "\n" in value:
                # Split on newlines and add each link
                links = [link.strip() for link in value.split("\n") if link.strip()]
                all_urls.update(links)
            else:
                # Single URL
                all_urls.add(value)

    all_urls = [url for url in all_urls if url and str(url).strip()]
    total_urls = len(all_urls)

    # Print special colored messages
    print(f"{Fore.CYAN}{Style.BRIGHT}📢 INFO:{Style.RESET_ALL} {Fore.YELLOW}Fetching URL site titles, this will take a few minutes{Style.RESET_ALL}")
    print(f"{Fore.BLUE}🔗 Processing {total_urls} unique URLs...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ You can continue using the application while this runs in the background{Style.RESET_ALL}")
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


def main():
    while True:
        fetch_data() # Grab data from ARA_SDS API and save to final.csv
        fetch_example_use() # Grab example uses from ARA_SDS API and save to example_uses/*.txt

        init() # initialize colorama

        # Save last updated time to file
        EST = pytz.timezone('US/Eastern')
        with open(LAST_UPDATED_PATH, 'w') as f:
            f.write(str(datetime.datetime.now(EST).strftime("%Y-%d-%m %H:%M:%S")))

        find_site_titles()
        time.sleep(24*60*60)  # Sleep for 24 hours
        print("Thread resumed")
