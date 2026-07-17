"""
GET /software_info/<name> — JSON for the software details modal.

Spec:
- Known software returns JSON list-of-records with the right fields
- Unknown software returns 204 (xfail: currently returns 200 with "[]")
- Names containing '/' work via <path:> converter
- HIDE_DATA is honored
- Version entries carry load_commands: every visible way to load the
  module, resolved through admin edits, alongside the single command
"""
import json

import pytest

from app.logic.chain_projection import project_entry


def test_known_software_returns_200(client, seeded_db):
    resp = client.get("/software_info/testpkg")
    assert resp.status_code == 200


def test_known_software_returns_records_with_software_name(client, seeded_db):
    resp = client.get("/software_info/testpkg")
    data = json.loads(resp.get_data(as_text=True))
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0].get("Software") == "testpkg"


def test_unknown_software_returns_204(client, seeded_db):
    resp = client.get("/software_info/nonexistent_pkg")
    assert resp.status_code == 204


def test_slash_in_name_routes_correctly(
    client, databases, make_resource, make_software, make_software_resource, make_ai
):
    resource = make_resource(name="cluster_x")
    software = make_software(name="ccs/burai", description="Slash-in-name package")
    make_software_resource(software, resource, version="1.0", command="m load burai")
    make_ai(software)

    resp = client.get("/software_info/ccs/burai")
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data[0]["Software"] == "ccs/burai"


def test_hide_data_drops_column_from_modal_json(
    client, seeded_db, flask_app
):
    flask_app.config["HIDE_DATA"] = ["Description"]
    resp = client.get("/software_info/testpkg")
    data = json.loads(resp.get_data(as_text=True))
    assert "Description" not in data[0]


def test_version_entries_carry_load_commands(client, seeded_db):
    record = json.loads(
        client.get("/software_info/testpkg").get_data(as_text=True)
    )[0]
    entry = record["Versions"]["test_cluster"][0]
    assert entry["version"] == "1.0.0"
    # the single canonical command stays for existing readers
    assert entry["command"] == "module load testpkg/1.0.0"
    assert entry["load_commands"] == ["module load testpkg/1.0.0"]


def test_load_commands_list_visible_chains_direct_load_first(
    client, databases, make_resource, make_software, make_software_resource,
    make_src_command
):
    resource = make_resource(name="cluster_m1")
    software = make_software(name="chainpkg", description="chains")
    sr = make_software_resource(
        software, resource, version="1.0", command="module load chainpkg/1.0"
    )
    make_src_command(sr, "module load chainpkg/1.0", module_name="chainpkg/1.0")
    make_src_command(
        sr, "module load gcc/12.3.0 chainpkg/1.0",
        module_name="chainpkg/1.0", parent_chain="gcc/12.3.0",
    )
    make_src_command(
        sr, "module load intel/.2021.4.0 chainpkg/1.0",
        module_name="chainpkg/1.0", parent_chain="intel/.2021.4.0", hidden=True,
    )

    record = json.loads(
        client.get("/software_info/chainpkg").get_data(as_text=True)
    )[0]
    entry = record["Versions"]["cluster_m1"][0]
    # direct load first; the hidden chain is not shipped
    assert entry["load_commands"] == [
        "module load chainpkg/1.0",
        "module load gcc/12.3.0 chainpkg/1.0",
    ]


def test_load_commands_reflect_admin_edits(
    client, databases, make_resource, make_software, make_software_resource,
    make_src_command, make_command_edit
):
    resource = make_resource(name="cluster_m2")
    software = make_software(name="editedpkg", description="edited")
    sr = make_software_resource(
        software, resource, version="1.0", command="module load editedpkg/1.0"
    )
    make_src_command(sr, "module load editedpkg/1.0", module_name="editedpkg/1.0")
    make_src_command(
        sr, "module load gcc/12.3.0 editedpkg/1.0",
        module_name="editedpkg/1.0", parent_chain="gcc/12.3.0",
    )
    edit = make_command_edit(
        "editedpkg", "cluster_m2", "1.0",
        target_command="module load editedpkg/1.0", suppressed=True,
    )
    project_entry(sr, [edit])

    record = json.loads(
        client.get("/software_info/editedpkg").get_data(as_text=True)
    )[0]
    entry = record["Versions"]["cluster_m2"][0]
    assert entry["load_commands"] == ["module load gcc/12.3.0 editedpkg/1.0"]


def test_hidden_versions_column_skips_load_commands(client, seeded_db, flask_app):
    flask_app.config["HIDE_DATA"] = ["Versions"]
    resp = client.get("/software_info/testpkg")
    assert resp.status_code == 200
    record = json.loads(resp.get_data(as_text=True))[0]
    assert "Versions" not in record


def test_research_field_merged_into_discipline_and_field_dropped(
    client, databases, make_resource, make_software, make_software_resource, make_ai, flask_app
):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_AI_INFO"] = True
    resource = make_resource(name="cluster_y")
    software = make_software(name="mergepkg", description="merge test")
    make_software_resource(software, resource, version="1.0", command="m load mergepkg")
    make_ai(software, ai_research_discipline="Physics", ai_research_field="Chemistry")

    record = json.loads(
        client.get("/software_info/mergepkg").get_data(as_text=True)
    )[0]

    # Research Field is folded into Research Discipline...
    discipline = record["AI Research Discipline"]
    assert "Physics" in discipline
    assert "Chemistry" in discipline
    # ...and the raw Field column is not shipped separately.
    assert "AI Research Field" not in record


def test_research_field_not_duplicated_in_discipline(
    client, databases, make_resource, make_software, make_software_resource, make_ai, flask_app
):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_AI_INFO"] = True
    resource = make_resource(name="cluster_z")
    software = make_software(name="duppkg", description="dup test")
    make_software_resource(software, resource, version="1.0", command="m load duppkg")
    # Field value already present in Discipline must not be appended a second time.
    make_ai(
        software,
        ai_research_discipline="Physics, Chemistry",
        ai_research_field="Chemistry",
    )

    record = json.loads(
        client.get("/software_info/duppkg").get_data(as_text=True)
    )[0]
    disciplines = [d.strip() for d in record["AI Research Discipline"].split(",")]
    assert disciplines.count("Chemistry") == 1


def test_research_area_folded_into_discipline(
    client, databases, make_resource, make_software, make_software_resource, make_ai, flask_app
):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_AI_INFO"] = True
    resource = make_resource(name="cluster_a1")
    software = make_software(name="areapkg", description="area test")
    make_software_resource(software, resource, version="1.0", command="m load areapkg")
    make_ai(software, ai_research_area="Astrophysics")

    record = json.loads(
        client.get("/software_info/areapkg").get_data(as_text=True)
    )[0]

    # Research Area shows up in the discipline chips...
    assert "Astrophysics" in record["AI Research Discipline"]
    # ...and the raw Area column is not shipped separately.
    assert "AI Research Area" not in record


def test_software_class_folded_into_software_type(
    client, databases, make_resource, make_software, make_software_resource, make_ai, flask_app
):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_AI_INFO"] = True
    resource = make_resource(name="cluster_c1")
    software = make_software(name="classpkg", description="class test")
    make_software_resource(software, resource, version="1.0", command="m load classpkg")
    make_ai(software, ai_software_type="CLI", ai_software_class="Utility")

    record = json.loads(
        client.get("/software_info/classpkg").get_data(as_text=True)
    )[0]

    # Software Class shows up in the Software Type chips...
    software_type = record["AI Software Type"]
    assert "CLI" in software_type
    assert "Utility" in software_type
    # ...and the raw Class column is not shipped separately.
    assert "AI Software Class" not in record


def test_software_class_not_duplicated_in_software_type(
    client, databases, make_resource, make_software, make_software_resource, make_ai, flask_app
):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_AI_INFO"] = True
    resource = make_resource(name="cluster_c2")
    software = make_software(name="classduppkg", description="class dup test")
    make_software_resource(software, resource, version="1.0", command="m load classduppkg")
    make_ai(software, ai_software_type="CLI, Library", ai_software_class="Library")

    record = json.loads(
        client.get("/software_info/classduppkg").get_data(as_text=True)
    )[0]
    types = [t.strip() for t in record["AI Software Type"].split(",")]
    assert types.count("Library") == 1
