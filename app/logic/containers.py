from typing import Dict, List
from collections import defaultdict
import pandas as pd
from app.models.containers import Container
from app.models.softwareContainer import SoftwareContainer
from app.models.resource import Resource
from app.app_logging import logger


def get_containers_for_software(software_id: int) -> List[Dict[str, str]]:
    software_contianers = (
        SoftwareContainer.select(SoftwareContainer, Container, Resource)
        .where(SoftwareContainer.software_id == software_id)
        .join(Container)
        .join(Resource, on=(Container.resource_id == Resource.id))
    )
    sc_df = pd.DataFrame(list(software_contianers.dicts()))
    sc_df = sc_df.loc[:, ~sc_df.columns.str.contains("_id")]
    sc_df = sc_df.drop(columns="id")
    # change newline for front end
    sc_df["notes"] = sc_df["notes"].str.replace("\\n", "<br> <br>")
    sc_data = sc_df.to_dict("records")
    return sc_data


def get_all_containers():
    containers = SoftwareContainer.select(SoftwareContainer, Container).join(Container)

    # Group by container and collect software
    container_map = defaultdict(list)
    for sc in containers:
        container_map[sc.container_id].append(sc.software_id.software_name)

    # Convert to list of dicts with software array
    containers_json = []
    for container, software_list in container_map.items():
        containers_json.append(
            {
                "container_id": container.id,
                "container_name": container.container_name,
                "container_file": container.container_file,
                "resource": container.resource_id.resource_name,
                "software": software_list,
            }
        )

    return containers_json


def get_container_info(container_name: str = "", resource_name: str = ""):

    if not (container_name and resource_name):
        logger.debug(
            f"Unable to get container info, not enough information provied container_name: {container_name}, resource_name: {resource_name}"
        )
        return {}
    resource = Resource.get_or_none(Resource.resource_name == resource_name)
    container = Container.get_or_none(
        Container.container_name == container_name, Container.resource_id == resource
    )
    software_containers = SoftwareContainer.select().where(
        SoftwareContainer.container_id == container
    )
    container_info = {
        "container_name": container.container_name,
        "definition_file": container.definition_file,
        "container_file": container.container_file,
        "resource": resource.resource_name,
        "container_notes": container.notes,
        "software": [cs.software_id.software_name for cs in software_containers],
    }

    return container_info
