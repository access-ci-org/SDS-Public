from pathlib import Path
import re
from typing import Optional
import yaml
import magic
from app.cli_loading import custom_halo
from parsers.lmod.custom_parsers.custom_lmod_parser import custom_lmod_parser
from parsers.lmod.name_version_rules import (
    DEFAULT_NAME_PATTERN,
    DEFAULT_VERSION_CLEANER,
    DEFAULT_VERSION_CLEANER_MAX_SPLIT,
    DEFAULT_VERSION_SEPARATOR,
    apply_name_version_rules,
)
from parsers.lmod.parse_spider_json import get_software_info_json

def is_text_file(file_path: Path) -> bool:
    """
    Checks whether a givn file is a text file or not

    Args:
        file_path (pathlib.Path): Path object to a file
    Retruns:
        bool: True or False based on file content
    """
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(str(file_path))
    return file_type.startswith('text/')

def get_decoded_value(dictionary: dict, key: str, default: str = ""):
    """
    Gets a value from a dictionary and decodes any Unicode escape sequences.

    This is needed for yaml to decode custom user parsing regex

    Args:
        dictionary (dict): Source dictionary
        key (str): Key to look up
        default (str): Default value if key not found
    Returns:
        str: Decoded string value

    Example:
        >>> lmod_parsing = {"section_separator": "\\n(?=\\s{2}[/\\w.+-]+(?:/[\\w+\\-])*:)"}
        >>> decoded_val = get_decoded_value(lmod_parsing, "section_separator")
    """
    return dictionary.get(key, default).encode("utf-8").decode("unicode_escape")


def get_software_info(
    file_path: Path,
    section_separator: str = r"\n(?=\s{2}[/\w.+-]+(?:/[\w+\-])*:)",
    name_version_pattern: str = r"([/\w.+-]+(?:-[/\w+\-]+)?): (.+)",
    name_pattern: str = DEFAULT_NAME_PATTERN,
    version_separator: str = DEFAULT_VERSION_SEPARATOR,
    version_cleaner: str = DEFAULT_VERSION_CLEANER,
    version_cleaner_max_split: str = DEFAULT_VERSION_CLEANER_MAX_SPLIT,
    spider_description_separator: str = "----",
    custom_name_version_parser: Optional[callable] = None,
) -> list[dict[str, any]]:
    """
    Extract software information from a file.

    This function reads a file containing software information, parses it, and returns
    a list of dictionaries containing details about each software package.

    Args:
        file_path (Path): Path to the file containing software information.
        section_separator (str, optional): Regex pattern to split the file content into sections.
            A section is an entry of software name, versions, and descriptions (if availabe).
            Defaults to r'\\n(?=\\s{2}[\\/\\w.-]+(?:/[\\w-])*:)'.
        name_version_pattern (str, optional): Regex pattern to extract software name and version from section.
            Defaults to r'([\\w/.-]+(?:-[\\w/-]+)?): (.+)'.
        name_pattern (str, optional): REgex pattern to further refine software name.
            Defaults to r'^([^/]+)(?=/.*$)'
        version_separator (str, optional): Regex pattern to split multiple versions.
            Defaults to r'[,]'.
        version_cleaner (str, optional): Regex pattern to split version string. Last item from the split will be used
            Defaults to r'/'.
        spider_description_separator (str, optional): Separator for spider descriptions.
            Defaults to '----'.
        custom_name_version_parser (Optional[Callable], optional): Custom function to parse
            name and version. If provided, it should accept and return (name, versions, software_info).
            Defaults to custom_lmod_parser.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - 'name' (str): The name of the software.
            - 'versions' (Dict:[str:str]): A dict for the software where the key is inte cleaned version name and the value is the unclead version name.
            - 'description' (str): A description of the software.

    Notes:
        - The function assumes the files are in the general spider output format, with each software
          entry starting with the software name and version(s), followed by a description.
        - If a software name already exists in the output list, the versions are merged
          and duplicates are removed.
        - The function removes LMOD comments from descriptions.
        - Software names in the `exclude_software` list are skipped.
    """

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    # Split the content into section (one for each software)
    sections = re.split(section_separator, file_content)

    software_info = []

    for section in sections:
        lines = section.strip().split("\n")

        if lines:
            # Extract software name and versions
            name_line = lines[0].strip()

            name_version_match = re.match(name_version_pattern, name_line)

            if name_version_match:
                if len(name_version_match.groups()) == 1:
                    name = name_version_match.group(1)
                    versions = ""
                else:
                    name, versions = name_version_match.groups()

                name, versions, software_info = apply_name_version_rules(
                    name,
                    versions,
                    software_info,
                    name_pattern=name_pattern,
                    version_separator=version_separator,
                    version_cleaner=version_cleaner,
                    version_cleaner_max_split=version_cleaner_max_split,
                    custom_name_version_parser=custom_name_version_parser,
                )

                # Join the remaining lines as the description
                description = " ".join(line.strip() for line in lines[1:])

                # remove lmod comments
                if spider_description_separator in description:
                    description = description.split(
                        spider_description_separator, maxsplit=1
                    )[0].strip()

                # Check if software already exists in software_info
                # existing_software = next(
                #     (item for item in software_info if item["name"] == name), None
                # )

                # if existing_software:
                #     existing_software["versions"] = list(
                #         set(existing_software["versions"] + versions)
                #     )
                # else:
                software_info.append(
                    {"name": name, "versions": versions, "description": description}
                )
    return software_info


@custom_halo(text="Parsing spider output file")
def parse_spider_output(spider_output_dir: Path) -> dict[str, list[dict[str, any]]]:
    """
    Parse the output of `module spider` and associate each resource with it's software,
    versions, and any given descriptions.

    Args:
        spider_output_dir (Path): Path object to the parent directory of all spider output files

    Returns:
        Dict[str, List[Dict[str, Any]]]: A Dictionary with each key beign the rp name
        and the value is a list of Dicts with:
        - 'name' (str): The name of the software.
        - 'versions' (List[str]): A list of versions for the software.
        - 'description' (str): A description of the software.

    Behavior:
        - Iterates through all subdirectories in the specified spider_output_dir.
        - Extracts resource name from subdirectory name.
        - Aggregates software, version and description information for each RP.

    Note:
        - Non-directory items in the spider_output_dir are skipped with a warning message.
        - Non-file items in the nested directory are skipped with a warning message.
        - Non-text-files (.txt) will be ignored.

    Example:
        rp_data = parse_spider_output("/path/to/spider/output")
        for rp, software_list in rp_data.items():
            print(f"RP: {rp}")
            for s_info in software_list:
                print(f"  Software: {s_info["name"]}, Versions: {s_info["versions"]}, Description: {s_info["description"]}")
    """
    resource_software_info = {}
    try:
        with open("config.yaml", "r", encoding="utf-8") as c:
            parsing = yaml.safe_load(c).get("parsing", {})
            lmod_parsing = parsing.get("lmod_spider", {}) if parsing else {}

    except FileNotFoundError:
        lmod_parsing = {}

    if lmod_parsing:
        for key in lmod_parsing:
            lmod_parsing[key] = get_decoded_value(lmod_parsing, key)
        lmod_parsing = {
            key: value for key, value in lmod_parsing.items() if value is not None
        }

    lmod_parsing["custom_name_version_parser"] = custom_lmod_parser

    # The JSON parser takes the shared name/version rules but none of the
    # text-layout options (section_separator, name_version_pattern, ...).
    json_rules = {
        key: lmod_parsing[key]
        for key in (
            "name_pattern",
            "version_separator",
            "version_cleaner",
            "version_cleaner_max_split",
            "custom_name_version_parser",
        )
        if key in lmod_parsing
    }

    for dir_path in spider_output_dir.iterdir():
        if not dir_path.is_dir():
            print(f"Item {dir_path} not inside a resource directory. Skipping")
            continue

        resource_name = dir_path.stem
        software_info = []

        # JSON spider output (spider -o jsonSoftwarePage) carries dependency
        # chains the text output lacks, and both files describe the same
        # modules — so when a resource has usable JSON, its text files are
        # skipped to avoid double ingestion.
        parsed_json = False
        for file_path in sorted(dir_path.glob("*.json")):
            try:
                software_info += get_software_info_json(file_path, **json_rules)
                parsed_json = True
            except (ValueError, OSError) as e:
                print(f"Could not parse {file_path} as spider JSON: {e}. Skipping")

        if not parsed_json:
            for file_path in dir_path.iterdir():
                if file_path.is_dir():
                    print(
                        f"Item {file_path} inside {spider_output_dir} is not a file. Skipping"
                    )
                    continue
                if file_path.suffix == ".json":
                    continue
                if not is_text_file(file_path):
                    print(
                        f"Item {file_path} inside {spider_output_dir} is not a text file. Skipping"
                    )
                    continue
                software_info += get_software_info(file_path, **lmod_parsing)

        if resource_name in resource_software_info:
            resource_software_info[resource_name] += software_info
        else:
            resource_software_info[resource_name] = software_info

    return resource_software_info
