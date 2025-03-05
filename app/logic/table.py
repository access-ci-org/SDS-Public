from typing import Sequence, List, Dict
from peewee import Model, JOIN, Case
from dataclasses import dataclass, field
import pandas as pd
from ..models.resource import Resource
from ..models.software import Software
from ..models.softwareResource import SoftwareResource
from ..models.aiSoftwareInfo import AISoftwareInfo
from ..models.softwareContainer import SoftwareContainer
from flask import current_app, has_app_context


@dataclass
class TableInfo:
    default_column_order: List[str] = field(
        default_factory=lambda: [
            "software_name",
            "resource_name",
            "container",
            "software_description",
            "ai_description",
            "software_version",
            "ai_software_type",
            "ai_software_class",
            "ai_research_field",
            "ai_research_area",
            "ai_research_discipline",
            "ai_core_features",
            "ai_general_tags",
            "software_web_page",
            "software_documentation",
            "software_use_link",
            "ai_example_use",
        ]
    )
    column_names: Dict[str, str] = field(
        default_factory=lambda: {
            "software_name": "Software",
            "resource_name": "Resource",
            "container": "Containers",
            "software_description": "Description",
            "software_version": "Versions",
            "software_web_page": "Software's Web Page",
            "software_documentation": "Software Documentation",
            "software_use_link": "Example Software Use",
            "ai_description": "AI Description",
            "ai_software_type": "AI Software Type",
            "ai_software_class": "AI Software Class",
            "ai_research_field": "AI Research Field",
            "ai_research_area": "AI Research Area",
            "ai_research_discipline": "AI Research Discipline",
            "ai_core_features": "AI Core Features",
            "ai_general_tags": "AI General Tags",
            "ai_example_use": "AI Example Use",
        }
    )
    column_order: List[str] = field(init=False)

    def __post_init__(self):
        self.update_column_order()

    def update_column_order(self):
        column_order = self.default_column_order.copy()
        if current_app.config["USE_API"]:
            if (
                not current_app.config["USE_CURATED_INFO"]
                and current_app.config["API_CURATED_COLUMNS"]
            ):
                column_order = [
                    col
                    for col in column_order
                    if col not in current_app.config["API_CURATED_COLUMNS"]
                ]

            if (
                not current_app.config["USE_AI_INFO"]
                and current_app.config["API_AI_COLUMNS"]
            ):
                column_order = [
                    col
                    for col in column_order
                    if col not in current_app.config["API_AI_COLUMNS"]
                ]
        else:
            column_order = [
                col
                for col in column_order
                if col not in current_app.config["API_CURATED_COLUMNS"]
            ]
            column_order = [
                col
                for col in column_order
                if col not in current_app.config["API_AI_COLUMNS"]
            ]
        self.column_order = column_order

    def get_renamed_columns(self, columns: List[str]) -> List[str]:
        return [self.column_names[col] for col in columns if col in self.column_names]


TABLE_INFO = None


def initialize_table_info():
    global TABLE_INFO
    if has_app_context() and TABLE_INFO is None:
        TABLE_INFO = TableInfo()
    return TABLE_INFO


def get_table() -> Sequence[Model]:

    # Subquery to check if a matching SoftwareContainer exists
    container_exists = (
        SoftwareContainer.select(
            Case(None, [(SoftwareContainer.software_id == Software.id, True)])
        )
        .where(SoftwareContainer.software_id == Software.id)
        .alias("container")
    )
    table = (
        Software.select(Software, SoftwareResource, Resource, container_exists)
        .join(SoftwareResource)
        .join(Resource, on=(SoftwareResource.resource_id == Resource.id))
    )
    if current_app.config["USE_API"] and current_app.config["USE_AI_INFO"]:
        table = table.select(
            Software, SoftwareResource, Resource, AISoftwareInfo, container_exists
        ).join(
            AISoftwareInfo,
            JOIN.LEFT_OUTER,
            on=(Software.id == AISoftwareInfo.software_id),
        )

    return table.objects()


def organize_table(
    table_object: Sequence[Model], table_info: TableInfo
) -> pd.DataFrame:
    df = pd.DataFrame(list(table_object.dicts()))
    existing_columns = [col for col in table_info.column_order if col in df.columns]
    df = df[existing_columns]

    # Group by software_name and combine resources and versions
    def combine_resources_versions(group):
        resources = group["resource_name"].tolist()
        versions = group["software_version"].tolist()
        combined = [f"{r}: {v}" for r, v in zip(resources, versions)]
        return pd.Series(
            {
                "resource_name": ", ".join(set(resources)),
                "software_version": ", ".join(combined),
            }
        )

    # Apply the grouping
    result = df.groupby("software_name").apply(combine_resources_versions).reset_index()
    # Merge the result back with one row from each group to get other columns
    first_rows = df.groupby("software_name").first().reset_index()
    column_order = df.columns.tolist()
    df = pd.merge(first_rows, result, on="software_name", suffixes=("", "_grouped"))

    # Use the grouped versions of resource_name and software_version
    df["resource_name"] = df["resource_name_grouped"]
    df["software_version"] = df["software_version_grouped"]

    # reorganize columns
    df = df.drop(columns=["resource_name_grouped", "software_version_grouped"])
    df = df[column_order]
    renamed_columns = table_info.get_renamed_columns(existing_columns)
    df.columns = renamed_columns

    # Replace None with '' for all columns except 'Containers'
    container_column_name = table_info.column_names["container"]
    for column in df.columns:
        if column != container_column_name:
            df[column] = df[column].fillna("")

    if current_app.config["DROP_COLUMNS"]:
        df = df.drop(
            columns=current_app.config["DROP_COLUMNS"], axis=1, errors="ignore"
        )
    if container_column_name in df.columns:
        df[container_column_name] = df[container_column_name].fillna("N/A")
    return df
