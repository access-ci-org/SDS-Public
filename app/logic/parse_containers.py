from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
import re


def parse_csv_container(file_path: Path) -> List[Dict[str, str]]:
    csv_df = pd.read_csv(file_path)
    csv_df = csv_df.fillna("")
    # Apply strip() to every cell
    csv_df = csv_df.map(lambda x: x.strip() if isinstance(x, str) else str(x).strip())
    return csv_df.to_dict("records")


def remove_comments(content, file_type):
    if file_type == "singularity":
        # Remove full-line comments
        content = re.sub(r"^\s*#.*$", "", content, flags=re.MULTILINE)
        # Remove end-of-line comments
        content = re.sub(r"((?<!\\)#).*", "", content)
    elif file_type == "containerfile":
        # Remove full-line comments
        content = re.sub(r"^\s*#.*$", "", content, flags=re.MULTILINE)
        # Remove end-of-line comments, but not in RUN instructions
        content = re.sub(r"^(?!RUN).*?(?<!\\)#.*$", "", content, flags=re.MULTILINE)
    return content


def is_valid_package(s):
    # remove common file extensions
    s = re.sub(
        r"\.(?:-)(?:tar\.gz|tgz|tar\.bz2|rpm|tbz2|tar|gz|zip|rar)$",
        "",
        s,
        flags=re.IGNORECASE,
    )

    if not s or s.startswith(("-", ".")) or not any(c.isalpha() for c in s):
        return False

    # Reject strings that are just version numbers
    if re.match(r"^[\d.]+$", s):
        return False

    # Reject strings that start with just numbers and underscores
    if re.match(r"^\d+(?:_\d+)*_", s):
        return False
    return True


def clean_package_matches(matches):

    cleaned_words = []
    # Remove items that are just numbers and '.'
    matches = re.sub(r"(?:^|\s)[0-9.]+(?:\s|$)", "", matches)
    words = matches.split()
    # Remove flags
    cleaned_words = [w for w in words if not w.startswith("-")]

    # skip command words
    skip_words = {"install", "update"}

    cleaned_words = [w.strip() for w in cleaned_words if w not in skip_words]
    # cleaned.append(' '.join(cleaned_words))
    return cleaned_words


def extract_packages_strings(content, file_type="auto"):
    patterns = [
        # Package manager installations
        r"^\s*(?:apt-get|apt|yum|pip|conda)\s+(?:-[a-zA-Z]*\s+)*(?:install)\s*(?:-[a-zA-Z]*\s+)*(?:-[nc]\s+[\w.-]+\s+)*(?:-c\s+[\w.-]+\s+)*([a-zA-Z0-9._+=-]+(?:\s+[a-zA-Z0-9._+=-]+)*)$",
        # Install scripts
        r"install(?:-[a-z-]+)?.sh\s+([a-zA-Z0-9._=-]+)",
        # Conda sepcific captures for conda create
        r"conda\s+create\s+.*?-c\s+\S+\s+((?:\S*[^-]\S*\s+)*)",
        # installs from tar
        r"tar\s+(?:-[a-zA-Z]+\s*)+\s+(?!v\d+)(?!v.)([a-zA-Z][a-zA-Z0-9._=-]*).tar",
    ]

    combined_pattern = "|".join(f"(?:{pattern})" for pattern in patterns)
    package_strings = []

    if file_type == "auto":
        if "%post" in content:
            file_type = "singularity"
        elif "FROM" in content and "RUN" in content:
            file_type = "containerfile"
        else:
            file_type = "unknown"

    content = remove_comments(content, file_type)

    if file_type == "singularity":
        if "%post" in content:
            content = content.split("%post", 1)[1]
    elif file_type == "containerfile":
        run_instructions = re.findall(r"RUN\s+(.*?)(?=\n\w+\s+|$)", content, re.DOTALL)
        content = "\n".join(run_instructions)

    content = content.replace("\\\n", " ")  # replace any escaped newlines with space

    for line in content.splitlines():
        if line:
            line = " ".join(
                line.split()
            )  # normalize line to have only 1 space separator
            matches = re.findall(combined_pattern, line, re.IGNORECASE | re.MULTILINE)
            if matches:
                filtered_matches = [
                    match for match in matches[0] if match
                ]  # remove empty items
                if filtered_matches:
                    # The list should have only one items since parsing shouldn't match for
                    # multiple patterns
                    cleaned_matches = clean_package_matches(filtered_matches[0])
                    package_strings.extend(cleaned_matches)

    return package_strings


def get_parsed_data(package_string, data) -> Dict[str, str]:

    sv_pattern = r"([a-zA-Z0-9._-]+)(?:[-=]|==)v?(\d+(?:\.\d+)*(?:[-_.][a-zA-Z0-9]+)*)"
    software_versions = re.match(sv_pattern, package_string)
    if software_versions:
        s = software_versions.group(1)
        v = software_versions.group(2)
    else:
        s = package_string
        v = ""
    if s not in data or (v and not data["software_versions"]):
        data["software_name"] = s
        data["software_versions"] = v

    elif v and v not in data["software_versions"]:
        data["software_versions"] += f", {v}"

    return data


def parse_container_def(file_path: Path) -> List[Dict[str, Any]]:
    with open(file_path, "r") as file:
        content = file.read()

    package_strings = extract_packages_strings(content)

    parsed_data = []
    for package_string in package_strings:
        data = {
            "container_name": file_path.stem,
            "definition_file": f"{file_path.stem}{file_path.suffix}",
            "container_file": "",
            "container_description": "",
            "notes": "",
        }
        if package_string.startswith(("http://", "https://")):
            data["software_name"] = package_string
            data["software_versions"] = ""
        else:
            data = get_parsed_data(package_string, data)
        parsed_data.append(data)
    return parsed_data


def parse_container_files(container_dir: Path) -> Dict[str, Any]:
    resource_container_info = {}
    for dir_path in container_dir.iterdir():
        num_processed_containers = 0  # TODO remove this
        if not dir_path.is_dir():
            print(f"Item {dir_path} not inside a resource directory. Skipping")
            continue

        for file_path in dir_path.iterdir():
            num_processed_containers += 1
            if file_path.is_dir():
                print(f"Item {file_path} inside {dir_path} is not a file. Skipping")
                continue
            resource_name = dir_path.stem
            parsed_data = None
            if file_path.suffix == ".csv":
                parsed_data = parse_csv_container(file_path)
            elif file_path.suffix == ".def":
                parsed_data = parse_container_def(file_path)
            else:
                print(f"Unknown file type: {file_path.suffix}. Skipping")
                continue
            if not parsed_data:
                continue
            if resource_name in resource_container_info:
                resource_container_info[resource_name] += parsed_data
            else:
                resource_container_info[resource_name] = parsed_data
    return resource_container_info
