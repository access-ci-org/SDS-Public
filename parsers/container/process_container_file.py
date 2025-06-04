from pathlib import Path
from peewee import Model

from app.cli_loading import custom_halo
from app.app_logging import logger
from app.models import db
from app.models.containers import Container
from app.models.softwareContainer import SoftwareContainer
from app.models.resource import Resource

from parsers.container.parse_containers import parse_container_files
from parsers.exceptions import DataProcessingError
from parsers.utils import clean_versions, process_software, update_software_resource

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
            container = Container.create(**container_data)
        else:
            updates = {}
            if container_data['notes'] and container_data['notes'] not in container.notes:
                updates['notes'] = f"{container.notes}\n{container_data['notes']}"
            if container_data['definition_file'] and not container.definition_file:
                updates['definition_file'] = container_data['definition_file']
            if container_data['container_file'] and not container.container_file:
                updates['container_file'] = container_data['container_file']
            if updates:
                (Container
                .update(updates)
                .where(Container.id == container.id)
                .execute())
            logger.info(f"Found existing container: {container_name}")

        return container
    except Exception as e:
        logger.error(f"Error processing container {container_name}: {e}", exc_info=True)
        raise


def update_software_container(
    software_id: Model, container_id: Model, versions: str, command: str
) -> None:
    logger.debug(
        f"Updating software container. Software ID: {software_id}, Container ID: {container_id}"
    )
    try:
        sc_id, created = SoftwareContainer.get_or_create(
            software_id=software_id, container_id=container_id, software_versions=versions
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
            SoftwareContainer.update({
                SoftwareContainer.software_versions: final_versions,
                SoftwareContainer.command: command,
                }
            )
            .where(SoftwareContainer.id == sc_id)
            .execute()
        )
    except Exception as e:
        logger.error(f"Error updating software container: {e}", exc_info=True)
        raise e

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

                        if c_info["software_name"]:
                            s_id = process_software(c_info["software_name"], blacklist)
                            update_software_resource(
                                s_id, r_id, {c_info["software_versions"]: c_info.get("command", "")}
                            )

                            update_software_container(
                                s_id, c_id, c_info["software_versions"], c_info["command"]
                            )
                    except DataProcessingError as e:
                        logger.warning(
                            f"Skipping container/software entry: {c_info} \n{str(e)}"
                        )
                        continue
    except Exception as e:
        raise DataProcessingError(f"Container data processing failed: {str(e)}") from e