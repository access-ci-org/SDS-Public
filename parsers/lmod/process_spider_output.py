import logging
from pathlib import Path
from app.models import db
from app.models.resource import Resource
from app.app_logging import logger
from app.cli_loading import custom_halo
from parsers.lmod.parse_spider import parse_spider_output
from parsers.exceptions import DataProcessingError
from parsers.utils import process_software, update_software_resource

@custom_halo(text="Processing moduel spider data")
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
                            s_info["name"], blacklist, s_info.get("description")
                        )
                        update_software_resource(
                            s_id, r_id, ", ".join(s_info["versions"])
                        )
                    except DataProcessingError as e:
                        logger.warning(f"Skipping entry: {str(e)}")
                        continue
    except Exception as e:
        raise DataProcessingError(f"Spider data processnig failed: {str(e)}") from e