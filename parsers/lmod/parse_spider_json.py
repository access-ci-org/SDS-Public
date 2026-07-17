import json
from pathlib import Path

from app.app_logging import logger
from parsers.lmod.name_version_rules import (
    DEFAULT_NAME_PATTERN,
    DEFAULT_VERSION_CLEANER,
    DEFAULT_VERSION_CLEANER_MAX_SPLIT,
    DEFAULT_VERSION_SEPARATOR,
    apply_name_version_rules,
)


def is_hidden_module(module_name: str) -> bool:
    """
    Check whether a module name refers to a hidden module.

    Lmod hides a module by dot-prefixing its last path component,
    e.g. 'intel/.2021.4.0' or a bare '.hiddenpkg'.

    Args:
        module_name (str): Full module name as reported by spider.
    Returns:
        bool: True when the module is hidden.
    """
    return module_name.rsplit("/", 1)[-1].startswith(".")


def get_software_info_json(
    file_path: Path,
    name_pattern: str = DEFAULT_NAME_PATTERN,
    version_separator: str = DEFAULT_VERSION_SEPARATOR,
    version_cleaner: str = DEFAULT_VERSION_CLEANER,
    version_cleaner_max_split: str = DEFAULT_VERSION_CLEANER_MAX_SPLIT,
    custom_name_version_parser=None,
) -> list[dict[str, any]]:
    """
    Extract software information from a `spider -o jsonSoftwarePage` dump.

    The spider tool ships with Lmod ($LMOD_DIR/spider) and reports one
    entry per modulefile, so the same software version appears once per
    toolchain it was built under. Entries are merged by their full module
    name, and every way of reaching a version is kept as a separate chain.

    Software names and version keys go through the same user-configurable
    rules as the text parser (see apply_name_version_rules), so a module
    gets the same name and version string from either dump format.

    Args:
        file_path (Path): Path to the JSON file produced by
            `$LMOD_DIR/spider -o jsonSoftwarePage "$MODULEPATH"`.
        name_pattern, version_separator, version_cleaner,
        version_cleaner_max_split, custom_name_version_parser: The shared
            name/version rules, documented on apply_name_version_rules.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - 'name' (str): The package name.
            - 'description' (str): Package description; falls back to the
              first version-level description when the package has none.
            - 'url' (str): Package homepage from the modulefile; '' when
              absent.
            - 'versions' (Dict[str, dict]): Keyed by the version derived
              from the full module name via the version rules (by default
              the text after the first '/'), each value:
                - 'full' (str): Full module name (e.g. 'proj/8.1.1').
                - 'chains' (List[dict]): One entry per way the module can be
                  loaded:
                    - 'parents' (List[str]): Modules that must be loaded
                      first, in load order. Empty when directly loadable.
                    - 'hidden' (bool): True when the chain goes through a
                      hidden module.

    Notes:
        - Version entries that are themselves hidden (a `hidden` flag or a
          dot-prefixed version component) are skipped; packages left with no
          visible versions are dropped.
        - Versionless modulefiles (`full` contains no '/') are keyed by
          their module name under the default rules, as in the text parser.
        - A raw module name rewritten by the custom hook has no recorded
          chains and is stored as directly loadable, as in the text path.
        - Field presence varies across Lmod versions, so all access is
          tolerant of missing keys.

    Raises:
        ValueError: If the file is not valid JSON or not a JSON array.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        packages = json.load(f)

    if not isinstance(packages, list):
        raise ValueError(f"{file_path} is not a jsonSoftwarePage array")

    software_info = []

    for package in packages:
        name = package.get("package", "")
        if not name:
            logger.debug(f"Skipping {file_path} entry with no package name")
            continue

        chains_by_full = {}
        fallback_description = ""

        for entry in package.get("versions", []):
            full = entry.get("full", "")
            if not full:
                continue
            if entry.get("hidden") or is_hidden_module(full):
                continue

            if not fallback_description:
                fallback_description = entry.get("description", "")

            record = chains_by_full.setdefault(full, [])

            # No parent data means the module is directly loadable — that is
            # still one valid chain (with no prerequisites), so a version
            # reachable both directly and through parents keeps both routes.
            for parents in entry.get("parent") or [[]]:
                chain = {
                    "parents": list(parents),
                    "hidden": any(is_hidden_module(p) for p in parents),
                }
                if chain not in record:
                    record.append(chain)

        if not chains_by_full:
            logger.debug(
                f"Dropping package '{name}' from {file_path}: "
                "no visible versions (every entry hidden or missing a full "
                "module name)"
            )
            continue

        # The visible full module names joined with ', ' are exactly what a
        # text dump lists after a package name, so the user's configured
        # rules see the same input for either dump format. The versionName
        # field is never used: some clusters populate it with a display
        # string, and distinct modulefiles can share one.
        name, cleaned, software_info = apply_name_version_rules(
            name,
            ", ".join(chains_by_full),
            software_info,
            name_pattern=name_pattern,
            version_separator=version_separator,
            version_cleaner=version_cleaner,
            version_cleaner_max_split=version_cleaner_max_split,
            custom_name_version_parser=custom_name_version_parser,
        )

        versions = {
            version: {
                "full": raw,
                "chains": chains_by_full.get(
                    raw, [{"parents": [], "hidden": is_hidden_module(raw)}]
                ),
            }
            for version, raw in cleaned.items()
        }

        software_info.append(
            {
                "name": name,
                "description": package.get("description") or fallback_description,
                "url": (package.get("url") or "").strip(),
                "versions": versions,
            }
        )

    return software_info
