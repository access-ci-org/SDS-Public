import logging
from peewee import Model
from typing import Optional
from app.app_logging import logger
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from parsers.exceptions import DataProcessingError


def clean_versions(version_string: str) -> str:
    logger.debug(f"Cleaning version string: {version_string}")
    versions = [v.strip() for v in str(version_string).split(",") if v.strip()]
    unqiue_versions = sorted(set(versions))
    return ", ".join(unqiue_versions)

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

def update_software_resource(
    software_id: Model, resource_id: Model, versions: dict
) -> Model:
    logger.debug(
        f"Updating software resource. Software ID: {software_id}, Resource ID: {resource_id}"
    )
    try:
        if type(versions) == dict:
            sr_ids = []
            for version, command in versions.items():
                sr_id, created = SoftwareResource.get_or_create(
                    software_id=software_id, resource_id=resource_id,
                    software_version=version
                )
                old_commands = sr_id.command.split(",")
                old_commands = [command.strip() for command in old_commands if command]
                old_commands.append(command)
                new_command = ", ".join(old_commands)
                SoftwareResource.update({
                    SoftwareResource.command: new_command
                }).where(SoftwareResource.id == sr_id).execute()
                if sr_id:
                    sr_ids.append(sr_id)

            logger.info(
                f"Creating/Updating software resource with version and command: {version}"
            )

            return sr_ids

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

        return [sr_id]
    except Exception as e:
        logger.error(f"Error updating software resource: {e}", exc_info=True)
        raise e