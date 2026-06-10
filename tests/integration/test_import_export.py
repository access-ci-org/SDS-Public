"""
Import / export of admin overrides.

Spec:
- Export returns SoftwareEdit + CommandEdit as JSON
- Import upserts (creates new + updates existing)
- Round-trip is lossless
- Import writes through to live Software / AI / SoftwareResource
- Malformed input returns 400, not 500
"""
import io
import json

import pytest

from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.command_edit import CommandEdit
from app.models.software import Software
from app.models.software_edit import SoftwareEdit


def _post_overrides(admin_client, payload):
    return admin_client.post(
        "/admin/software/import",
        data={
            "overrides_file": (
                io.BytesIO(json.dumps(payload).encode()),
                "overrides.json",
            )
        },
        content_type="multipart/form-data",
    )


# ---- Export ----

def test_export_returns_200_with_empty_arrays_when_no_overrides(
    admin_client, databases
):
    resp = admin_client.get("/admin/software/export")
    assert resp.status_code == 200
    payload = json.loads(resp.get_data(as_text=True))
    assert payload == {"software_edits": [], "command_edits": []}


def test_export_includes_software_edit_rows(
    admin_client, seeded_db, make_edit
):
    make_edit("testpkg", description="x", web_page="http://e.example")
    resp = admin_client.get("/admin/software/export")
    payload = json.loads(resp.get_data(as_text=True))
    names = [e["software_name"] for e in payload["software_edits"]]
    assert "testpkg" in names


def test_export_includes_command_edit_rows(
    admin_client, seeded_db, make_command_edit
):
    make_command_edit("testpkg", "test_cluster", "1.0.0", command="overridden")
    resp = admin_client.get("/admin/software/export")
    payload = json.loads(resp.get_data(as_text=True))
    assert len(payload["command_edits"]) == 1
    assert payload["command_edits"][0]["command"] == "overridden"


def test_export_attaches_download_filename(admin_client, databases):
    resp = admin_client.get("/admin/software/export")
    disposition = resp.headers.get("Content-Disposition", "")
    assert "sds_overrides.json" in disposition


# ---- Import ----

def test_import_creates_new_software_edit(admin_client, seeded_db):
    _post_overrides(admin_client, {
        "software_edits": [
            {"software_name": "testpkg", "description": "imported"}
        ],
        "command_edits": [],
    })
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.description == "imported"


def test_import_updates_existing_software_edit(
    admin_client, seeded_db, make_edit
):
    make_edit("testpkg", description="existing")
    _post_overrides(admin_client, {
        "software_edits": [
            {"software_name": "testpkg", "description": "updated"}
        ],
        "command_edits": [],
    })
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.description == "updated"


def test_import_writes_through_to_software(admin_client, seeded_db):
    _post_overrides(admin_client, {
        "software_edits": [
            {"software_name": "testpkg", "description": "imported live"}
        ],
        "command_edits": [],
    })
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "imported live"


def test_import_writes_through_to_ai(admin_client, seeded_db):
    _post_overrides(admin_client, {
        "software_edits": [
            {"software_name": "testpkg", "ai_description": "imported ai"}
        ],
        "command_edits": [],
    })
    ai = AISoftwareInfo.get(
        AISoftwareInfo.software_id == seeded_db["software"].id
    )
    assert ai.ai_description == "imported ai"


def test_import_command_edits_persist(admin_client, seeded_db):
    _post_overrides(admin_client, {
        "software_edits": [],
        "command_edits": [
            {
                "software_name": "testpkg",
                "resource_name": "test_cluster",
                "software_version": "1.0.0",
                "command": "imported cmd",
            }
        ],
    })
    edit = CommandEdit.get(
        (CommandEdit.software_name == "testpkg")
        & (CommandEdit.resource_name == "test_cluster")
        & (CommandEdit.software_version == "1.0.0")
    )
    assert edit.command == "imported cmd"


def test_round_trip_preserves_overrides(
    admin_client, seeded_db, make_edit, make_command_edit
):
    make_edit("testpkg", description="rt desc", web_page="http://rt.example")
    make_command_edit("testpkg", "test_cluster", "1.0.0", command="rt cmd")

    export_resp = admin_client.get("/admin/software/export")
    payload = json.loads(export_resp.get_data(as_text=True))

    # Wipe and re-import
    SoftwareEdit.delete().execute()
    CommandEdit.delete().execute()
    _post_overrides(admin_client, payload)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.description == "rt desc"
    assert edit.web_page == "http://rt.example"

    cmd_edit = CommandEdit.get(
        (CommandEdit.software_name == "testpkg")
        & (CommandEdit.resource_name == "test_cluster")
        & (CommandEdit.software_version == "1.0.0")
    )
    assert cmd_edit.command == "rt cmd"


def test_import_without_file_returns_400(admin_client, databases):
    resp = admin_client.post("/admin/software/import")
    assert resp.status_code == 400


def test_import_with_malformed_json_returns_400(admin_client, databases):
    resp = admin_client.post(
        "/admin/software/import",
        data={
            "overrides_file": (
                io.BytesIO(b"this is not json"),
                "overrides.json",
            )
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
