"""
process_spider_data ingestion of `spider -o jsonSoftwarePage` output:
every dependency chain becomes a SoftwareResourceCommand row, the
SoftwareResource row carries one canonical working command, and JSON files
take precedence over text spider files in a resource directory.
"""
import shutil

import pytest

from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.softwareResourceCommand import SoftwareResourceCommand
from parsers.lmod.process_spider_output import process_spider_data


RESOURCE = "clusterx"


@pytest.fixture
def spider_dir(tmp_path, fixture_path):
    """A spider_data layout with one resource dir holding the JSON fixture."""
    resource_dir = tmp_path / "spider_data" / RESOURCE
    resource_dir.mkdir(parents=True)
    shutil.copy(
        fixture_path("spider/json_software_page.json"),
        resource_dir / f"{RESOURCE}_spider.json",
    )
    return tmp_path / "spider_data"


def _software_resource(name, version):
    software = Software.get(Software.software_name == name)
    return SoftwareResource.get(
        SoftwareResource.software_id == software,
        SoftwareResource.software_version == version,
    )


def _commands_for(name, version):
    sr = _software_resource(name, version)
    return list(
        SoftwareResourceCommand.select().where(
            SoftwareResourceCommand.software_resource_id == sr
        )
    )


def test_every_chain_becomes_a_command_row(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    rows = _commands_for("proj", "8.1.1")
    commands = {r.command for r in rows}
    assert commands == {
        "module load gcc/11.2.0 proj/8.1.1",
        "module load gcc/10.3.0 proj/8.1.1",
        "module load intel/.2021.4.0 proj/8.1.1",
        "module load aocc/3.1.0 proj/8.1.1",
    }


def test_command_rows_store_parts_and_hidden_flag(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    rows = {r.parent_chain: r for r in _commands_for("proj", "8.1.1")}
    assert rows["gcc/11.2.0"].module_name == "proj/8.1.1"
    assert rows["gcc/11.2.0"].hidden is False
    assert rows["intel/.2021.4.0"].hidden is True


def test_canonical_command_prefers_visible_newest_parent(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    sr = _software_resource("proj", "8.1.1")
    assert sr.command == "module load gcc/11.2.0 proj/8.1.1"


def test_directly_loadable_module_gets_plain_command(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    sr = _software_resource("antlr", "4.13.1")
    assert sr.command == "module load antlr/4.13.1"
    rows = _commands_for("antlr", "4.13.1")
    assert len(rows) == 1
    assert rows[0].parent_chain == ""


def test_multi_level_chain_renders_in_load_order(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    commands = {r.command for r in _commands_for("parmetis", "4.0.3")}
    assert "module load gcc/12.3.0 openmpi/4.1.6 parmetis/4.0.3" in commands
    assert "module load gcc/12.3.0 mpich/4.1.2 parmetis/4.0.3" in commands


def test_versionless_module_stored_with_module_name_version(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    sr = _software_resource("slurmtools", "slurmtools")
    assert sr.command == "module load slurmtools"


def test_hidden_versions_not_ingested(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    software = Software.get(Software.software_name == "secrettool")
    versions = {
        sr.software_version
        for sr in SoftwareResource.select().where(
            SoftwareResource.software_id == software
        )
    }
    assert versions == {"2.0"}
    assert Software.get_or_none(Software.software_name == "ghostpkg") is None


def test_reingest_is_idempotent(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())
    first_sr_count = SoftwareResource.select().count()
    first_cmd_count = SoftwareResourceCommand.select().count()

    process_spider_data(spider_dir, blacklist=set())

    assert SoftwareResource.select().count() == first_sr_count
    assert SoftwareResourceCommand.select().count() == first_cmd_count
    # The canonical command is overwritten, not comma-appended
    sr = _software_resource("proj", "8.1.1")
    assert sr.command == "module load gcc/11.2.0 proj/8.1.1"


def test_json_takes_precedence_over_text(databases, spider_dir):
    text_file = spider_dir / RESOURCE / f"{RESOURCE}_spider.txt"
    text_file.write_text("  textonly: textonly/1.0\n")

    process_spider_data(spider_dir, blacklist=set())

    assert Software.get_or_none(Software.software_name == "textonly") is None
    assert Software.get_or_none(Software.software_name == "proj") is not None


def test_corrupt_json_falls_back_to_text(databases, tmp_path):
    resource_dir = tmp_path / "spider_data" / RESOURCE
    resource_dir.mkdir(parents=True)
    (resource_dir / f"{RESOURCE}_spider.json").write_text("{ not valid json")
    (resource_dir / f"{RESOURCE}_spider.txt").write_text("  textonly: textonly/1.0\n")

    process_spider_data(tmp_path / "spider_data", blacklist=set())

    sr = _software_resource("textonly", "1.0")
    assert sr.command == "module load textonly/1.0"


def test_text_path_also_fills_command_table(databases, tmp_path):
    resource_dir = tmp_path / "spider_data" / RESOURCE
    resource_dir.mkdir(parents=True)
    (resource_dir / f"{RESOURCE}_spider.txt").write_text("  textonly: textonly/1.0\n")

    process_spider_data(tmp_path / "spider_data", blacklist=set())

    rows = _commands_for("textonly", "1.0")
    assert len(rows) == 1
    assert rows[0].command == "module load textonly/1.0"
    assert rows[0].module_name == "textonly/1.0"
    assert rows[0].parent_chain == ""


def test_config_rules_apply_to_json_path(databases, tmp_path, monkeypatch):
    resource_dir = tmp_path / "spider_data" / RESOURCE
    resource_dir.mkdir(parents=True)
    (resource_dir / f"{RESOURCE}_spider.json").write_text(
        '[{"package": "tool", "versions": [{"full": "tool/os8-2.5"}]}]'
    )
    (tmp_path / "config.yaml").write_text(
        "parsing:\n  lmod_spider:\n    version_cleaner: '-'\n"
    )
    monkeypatch.chdir(tmp_path)

    process_spider_data(tmp_path / "spider_data", blacklist=set())

    sr = _software_resource("tool", "2.5")
    assert sr.command == "module load tool/os8-2.5"


def test_blacklisted_software_skipped(databases, spider_dir):
    process_spider_data(spider_dir, blacklist={"proj"})

    assert Software.get_or_none(Software.software_name == "proj") is None
    assert Software.get_or_none(Software.software_name == "antlr") is not None


def test_package_url_fills_web_page(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    sw = Software.get(Software.software_name == "proj")
    assert sw.software_web_page == "https://example.org/proj"


def test_no_url_leaves_web_page_empty(databases, spider_dir):
    process_spider_data(spider_dir, blacklist=set())

    sw = Software.get(Software.software_name == "bcftools")
    assert sw.software_web_page == ""


def test_url_fills_empty_web_page_on_existing_software(databases, spider_dir):
    Software.create(software_name="proj", software_web_page="")

    process_spider_data(spider_dir, blacklist=set())

    sw = Software.get(Software.software_name == "proj")
    assert sw.software_web_page == "https://example.org/proj"


def test_url_does_not_overwrite_existing_web_page(databases, spider_dir):
    Software.create(
        software_name="proj", software_web_page="https://curated.example/proj"
    )

    process_spider_data(spider_dir, blacklist=set())

    sw = Software.get(Software.software_name == "proj")
    assert sw.software_web_page == "https://curated.example/proj"


def test_text_path_leaves_web_page_empty(databases, tmp_path):
    resource_dir = tmp_path / "spider_data" / RESOURCE
    resource_dir.mkdir(parents=True)
    (resource_dir / f"{RESOURCE}_spider.txt").write_text("  textonly: textonly/1.0\n")

    process_spider_data(tmp_path / "spider_data", blacklist=set())

    sw = Software.get(Software.software_name == "textonly")
    assert sw.software_web_page == ""
