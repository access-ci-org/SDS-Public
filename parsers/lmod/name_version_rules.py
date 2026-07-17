import re

DEFAULT_NAME_PATTERN = r"([^/]+)(?=/.*)"
DEFAULT_VERSION_SEPARATOR = r"[,]"
DEFAULT_VERSION_CLEANER = r"/"
DEFAULT_VERSION_CLEANER_MAX_SPLIT = "1"


def apply_name_version_rules(
    name: str,
    versions: str,
    software_info: list,
    name_pattern: str = DEFAULT_NAME_PATTERN,
    version_separator: str = DEFAULT_VERSION_SEPARATOR,
    version_cleaner: str = DEFAULT_VERSION_CLEANER,
    version_cleaner_max_split: str = DEFAULT_VERSION_CLEANER_MAX_SPLIT,
    custom_name_version_parser=None,
):
    """
    Apply the user-configurable name/version rules from config.yaml's
    `parsing.lmod_spider` section: the custom parser hook, the
    name-refinement pattern, and the version separator/cleaner.

    Both spider parsers share these rules. The text parser passes the name
    and version list sliced from a text section; the JSON parser passes the
    package name and its full module names joined with ', ' — the same
    shape a text dump presents — so a site's custom rules produce the same
    software names and version keys for either dump format.

    Args:
        name (str): Software name as read from the dump.
        versions (str): Raw versions string; full module names separated by
            version_separator.
        software_info (list): Parse results accumulated so far for the
            current file; passed through the custom hook, which may modify
            it.
        name_pattern (str, optional): Regex pattern to refine the software
            name. Defaults to r'([^/]+)(?=/.*)'.
        version_separator (str, optional): Regex pattern to split multiple
            versions. Defaults to r'[,]'.
        version_cleaner (str, optional): Regex pattern to split each version
            string; the last item from the split is the cleaned version.
            Defaults to r'/'.
        version_cleaner_max_split (str, optional): Maximum splits for
            version_cleaner. Defaults to '1'.
        custom_name_version_parser (Optional[Callable], optional): Custom
            function applied before the other rules. Must accept and return
            (name, versions, software_info).

    Returns:
        Tuple of:
            - name (str): The refined software name.
            - versions (Dict[str, str]): Cleaned version mapped to its raw
              version string.
            - software_info (list): The (possibly hook-modified) parse
              results.
    """
    if custom_name_version_parser:
        name, versions, software_info = custom_name_version_parser(
            name, versions, software_info
        )
    name_match = re.match(name_pattern, name, re.VERBOSE)
    if name_match:
        # return the first not-None group
        name = next(group for group in name_match.groups() if group is not None)

    versions = {
        re.split(version_cleaner, v.strip(), int(version_cleaner_max_split))[-1]: v.strip()
        for v in re.split(version_separator, versions)
    }
    return name, versions, software_info
