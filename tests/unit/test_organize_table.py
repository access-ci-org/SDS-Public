"""
organize_table groups raw query rows by software_name, collapsing
multiple resource/version rows into a single row per software with
combined resource_name and a per-resource version structure.

Needs Flask app context because TableInfo and organize_table read
USE_API / HIDE_DATA from current_app.config.
"""
import pytest

from app.logic.table import organize_table, TableInfo


class StubQuery:
    """Minimal stand-in for a Peewee query that supports .dicts()."""
    def __init__(self, records):
        self._records = records

    def dicts(self):
        return self._records


def _make_rows():
    return [
        {"software_name": "pytorch", "resource_name": "gpu",
         "software_version": "2.0.1", "command": "module load pytorch/2.0.1"},
        {"software_name": "pytorch", "resource_name": "gpu",
         "software_version": "1.13.1", "command": "module load pytorch/1.13.1"},
        {"software_name": "pytorch", "resource_name": "cpu",
         "software_version": "2.0.1", "command": "module load pytorch/2.0.1"},
        {"software_name": "numpy", "resource_name": "cpu",
         "software_version": "1.24.0", "command": "module load numpy"},
    ]


def test_groups_into_one_row_per_software(flask_app):
    with flask_app.app_context():
        df = organize_table(StubQuery(_make_rows()), TableInfo())

    assert len(df) == 2
    assert set(df["Software"]) == {"pytorch", "numpy"}


def test_combines_resource_names_for_multi_resource_software(flask_app):
    with flask_app.app_context():
        df = organize_table(StubQuery(_make_rows()), TableInfo())

    pytorch_row = df[df["Software"] == "pytorch"].iloc[0]
    # Resource column lists every resource (order independent)
    assert set(r.strip() for r in pytorch_row["Resource"].split(",")) == {"gpu", "cpu"}


def test_versions_grouped_per_resource(flask_app):
    with flask_app.app_context():
        df = organize_table(StubQuery(_make_rows()), TableInfo())

    pytorch_row = df[df["Software"] == "pytorch"].iloc[0]
    versions = pytorch_row["Versions"]
    assert isinstance(versions, dict)
    assert set(versions.keys()) == {"gpu", "cpu"}
    # gpu has two versions, cpu has one
    assert len(versions["gpu"]) == 2
    assert len(versions["cpu"]) == 1


def test_command_attached_to_each_version(flask_app):
    with flask_app.app_context():
        df = organize_table(StubQuery(_make_rows()), TableInfo())

    pytorch_row = df[df["Software"] == "pytorch"].iloc[0]
    gpu_versions = pytorch_row["Versions"]["gpu"]
    for entry in gpu_versions:
        assert "version" in entry
        assert "command" in entry
        assert entry["command"].startswith("module load")


def test_hide_data_drops_specified_columns(flask_app):
    with flask_app.app_context():
        flask_app.config["HIDE_DATA"] = ["Description"]
        rows = [
            {"software_name": "pytorch", "resource_name": "gpu",
             "software_version": "2.0.1", "command": "x",
             "software_description": "Description here"},
        ]
        df = organize_table(StubQuery(rows), TableInfo())

    assert "Description" not in df.columns


def test_empty_command_does_not_appear_in_version_entry(flask_app):
    with flask_app.app_context():
        rows = [
            {"software_name": "pytorch", "resource_name": "gpu",
             "software_version": "2.0.1", "command": ""},
        ]
        df = organize_table(StubQuery(rows), TableInfo())

    pytorch_row = df[df["Software"] == "pytorch"].iloc[0]
    version_entries = pytorch_row["Versions"]["gpu"]
    assert version_entries[0] == {"version": "2.0.1"}
    assert "command" not in version_entries[0]


def test_none_values_filled_with_empty_string_except_containers(flask_app):
    with flask_app.app_context():
        rows = [
            {"software_name": "pytorch", "resource_name": "gpu",
             "software_version": "2.0.1", "command": "x",
             "software_description": None,
             "container": None},
        ]
        df = organize_table(StubQuery(rows), TableInfo())

    row = df.iloc[0]
    assert row["Description"] == ""
    # Containers column gets 'N/A' instead of empty string
    assert row["Containers"] == "N/A"
