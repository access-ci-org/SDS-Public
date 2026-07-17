from pathlib import Path
from app.logic.chain_projection import chain_sort_key
from app.models import db
from app.models.resource import Resource
from app.models.softwareResource import SoftwareResource
from app.models.softwareResourceCommand import SoftwareResourceCommand
from app.app_logging import logger
from app.cli_loading import custom_halo
from parsers.lmod.parse_spider import parse_spider_output
from parsers.exceptions import DataProcessingError
from parsers.utils import process_software, update_software_resource


def _select_canonical_chain(chains: list[dict]) -> dict:
    """Pick the chain used for the single displayed command: prefer chains
    without hidden modules, then fewer prerequisites, then the newest
    parents by natural version order."""
    def rank(chain):
        return (chain["hidden"], len(chain["parents"]))

    best = min(rank(c) for c in chains)
    candidates = [c for c in chains if rank(c) == best]
    return max(candidates, key=lambda c: chain_sort_key(c["parents"]))


def _render_command(parents: list[str], module_name: str) -> str:
    return "module load " + " ".join([*parents, module_name])


def _store_command(sr: SoftwareResource, command: str, module_name: str,
                   parent_chain: str, hidden: bool) -> None:
    SoftwareResourceCommand.get_or_create(
        software_resource_id=sr,
        command=command,
        defaults={
            "module_name": module_name,
            "parent_chain": parent_chain,
            "hidden": hidden,
        },
    )


def _has_chain_data(s_info: dict) -> bool:
    """JSON-parsed entries carry {full, chains} dicts per version; text
    entries carry raw module-name strings."""
    return any(isinstance(v, dict) for v in s_info["versions"].values())


def _ingest_chain_versions(s_id, r_id, versions: dict) -> None:
    """Store spider JSON versions: every load chain becomes a
    SoftwareResourceCommand row, and one canonical chain provides the
    command on the SoftwareResource row itself."""
    for version, info in versions.items():
        canonical = _select_canonical_chain(info["chains"])
        canonical_command = _render_command(canonical["parents"], info["full"])

        sr, _ = SoftwareResource.get_or_create(
            software_id=s_id, resource_id=r_id, software_version=version
        )
        if sr.command != canonical_command:
            SoftwareResource.update(
                {SoftwareResource.command: canonical_command}
            ).where(SoftwareResource.id == sr.id).execute()

        for chain in info["chains"]:
            _store_command(
                sr,
                _render_command(chain["parents"], info["full"]),
                info["full"],
                " ".join(chain["parents"]),
                chain["hidden"],
            )


def _ingest_text_versions(s_id, r_id, s_info: dict) -> None:
    """Store text-parsed versions: raw module names become `module load`
    commands, except truncated version listings ('...') which point users
    at `module spider` instead."""
    commands = {}
    modules = {}
    for version, raw in s_info["versions"].items():
        if version == "...":
            commands[version] = f"module spider {s_info['name']}"
            modules[version] = ""
        else:
            commands[version] = f"module load {raw}"
            modules[version] = raw

    update_software_resource(s_id, r_id, commands)

    for version, command in commands.items():
        sr = SoftwareResource.get_or_none(
            SoftwareResource.software_id == s_id,
            SoftwareResource.resource_id == r_id,
            SoftwareResource.software_version == version,
        )
        if sr is None:
            continue
        _store_command(sr, command, modules[version], "", False)


@custom_halo(text="Processing module spider data")
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
                            s_info["name"],
                            blacklist,
                            s_info.get("description"),
                            web_page=s_info.get("url"),
                        )
                        if _has_chain_data(s_info):
                            _ingest_chain_versions(s_id, r_id, s_info["versions"])
                        else:
                            _ingest_text_versions(s_id, r_id, s_info)
                    except DataProcessingError as e:
                        logger.warning(f"Skipping entry: {str(e)}")
                        continue
    except Exception as e:
        raise DataProcessingError(f"Spider data processing failed: {str(e)}") from e
