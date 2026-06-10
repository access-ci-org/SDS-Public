"""
Admin edit panel — GET / PUT / DELETE.
"""
import json

import pytest

from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.command_edit import CommandEdit
from app.models.resource import Resource
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.software_edit import SoftwareEdit


# ---- GET panel ----

class TestGetPanel:
    def test_panel_returns_200_for_known_software(self, admin_client, seeded_db):
        resp = admin_client.get("/admin/edit/software/testpkg")
        assert resp.status_code == 200

    def test_panel_returns_404_for_unknown_software(self, admin_client, seeded_db):
        resp = admin_client.get("/admin/edit/software/totally_unknown")
        assert resp.status_code == 404

    def test_panel_shows_auto_value_when_no_override(self, admin_client, seeded_db):
        resp = admin_client.get("/admin/edit/software/testpkg")
        body = resp.get_data(as_text=True)
        assert "A test package" in body
        assert "source-auto" in body

    def test_panel_shows_override_value_when_set(
        self, admin_client, seeded_db, make_edit
    ):
        make_edit("testpkg", description="manually overridden")
        resp = admin_client.get("/admin/edit/software/testpkg")
        body = resp.get_data(as_text=True)
        assert "manually overridden" in body
        assert "source-admin" in body

    def test_empty_string_override_is_explicit_blank(
        self, admin_client, seeded_db, make_edit
    ):
        make_edit("testpkg", description="")
        resp = admin_client.get("/admin/edit/software/testpkg")
        body = resp.get_data(as_text=True)
        # Empty override means the auto value should NOT be shown; the
        # admin badge should be set because the override is explicit.
        assert "source-admin" in body

    def test_slash_in_name_routes_correctly(
        self, admin_client, databases,
        make_resource, make_software, make_software_resource
    ):
        resource = make_resource(name="lcc")
        sw = make_software(name="ccs/burai", description="slashpkg")
        make_software_resource(sw, resource, version="1.0", command="m")
        resp = admin_client.get("/admin/edit/software/ccs/burai")
        assert resp.status_code == 200


# ---- PUT save ----

class TestPutSave:
    def test_put_description_writes_to_software_edit(
        self, admin_client, seeded_db
    ):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "new description"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.description == "new description"

    def test_put_description_writes_through_to_software(
        self, admin_client, seeded_db
    ):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "new description"},
        )
        sw = Software.get(Software.software_name == "testpkg")
        assert sw.software_description == "new description"

    def test_put_ai_field_writes_to_software_edit(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"ai_description": "AI desc"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.ai_description == "AI desc"

    def test_put_ai_field_writes_through_to_existing_ai_row(
        self, admin_client, seeded_db
    ):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"ai_description": "AI desc"},
        )
        ai = AISoftwareInfo.get(
            AISoftwareInfo.software_id == seeded_db["software"].id
        )
        assert ai.ai_description == "AI desc"

    def test_put_creates_ai_row_when_missing(
        self, admin_client, databases,
        make_resource, make_software, make_software_resource
    ):
        resource = make_resource()
        sw = make_software(name="aipkg")
        make_software_resource(sw, resource, version="1.0", command="")
        # No AI row exists yet

        admin_client.put(
            "/admin/edit/software/aipkg",
            data={"ai_description": "first AI value"},
        )
        ai = AISoftwareInfo.get(AISoftwareInfo.software_id == sw.id)
        assert ai.ai_description == "first AI value"

    def test_put_only_touches_fields_in_request(
        self, admin_client, seeded_db, make_edit
    ):
        make_edit(
            "testpkg",
            description="initial desc",
            web_page="http://existing.example",
        )
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "updated"},  # web_page omitted
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.description == "updated"
        assert edit.web_page == "http://existing.example"

    def test_put_records_edited_by(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "x"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.edited_by == "admin1"

    def test_put_with_slash_in_name(
        self, admin_client, databases,
        make_resource, make_software, make_software_resource
    ):
        resource = make_resource()
        sw = make_software(name="ccs/burai")
        make_software_resource(sw, resource, version="1.0", command="")
        admin_client.put(
            "/admin/edit/software/ccs/burai",
            data={"description": "slashed"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "ccs/burai")
        assert edit.description == "slashed"


# ---- PUT command override ----

class TestPutCommandOverride:
    def test_command_override_round_trip_comma_to_newline(
        self, admin_client, seeded_db
    ):
        # Form field name uses cmd__{resource}__{version}
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={
                "cmd__test_cluster__1.0.0":
                    "module load testpkg/1.0.0\nmodule load deps",
            },
        )
        edit = CommandEdit.get(
            (CommandEdit.software_name == "testpkg")
            & (CommandEdit.resource_name == "test_cluster")
            & (CommandEdit.software_version == "1.0.0")
        )
        # Stored as comma-separated
        assert edit.command == "module load testpkg/1.0.0, module load deps"

    def test_command_override_writes_through_to_software_resource(
        self, admin_client, seeded_db
    ):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"cmd__test_cluster__1.0.0": "new command"},
        )
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == "new command"

    def test_unchanged_command_does_not_create_override(
        self, admin_client, seeded_db
    ):
        # Submitting the exact current command should not create a CommandEdit row
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"cmd__test_cluster__1.0.0": "module load testpkg/1.0.0"},
        )
        assert CommandEdit.select().count() == 0


# ---- DELETE field override ----

class TestDeleteFieldOverride:
    def test_delete_field_sets_software_edit_to_null(
        self, admin_client, seeded_db, make_edit
    ):
        make_edit("testpkg", description="overridden")
        admin_client.delete("/admin/edit/software/testpkg/description")
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.description is None

    def test_delete_unknown_field_returns_400(self, admin_client, seeded_db):
        resp = admin_client.delete("/admin/edit/software/testpkg/bogus_field")
        assert resp.status_code == 400

    def test_delete_field_restores_auto_value_in_software(
        self, admin_client, seeded_db, make_edit
    ):
        # Override and write-through (simulating prior PUT)
        make_edit("testpkg", description="overridden", auto_values={"description": "A test package"})
        Software.update(software_description="overridden").where(
            Software.software_name == "testpkg"
        ).execute()

        admin_client.delete("/admin/edit/software/testpkg/description")

        sw = Software.get(Software.software_name == "testpkg")
        # Should be restored to the seeded auto value
        assert sw.software_description == "A test package"


# ---- DELETE command override ----

class TestDeleteCommandOverride:
    def test_delete_command_override_removes_row(
        self, admin_client, seeded_db, make_command_edit
    ):
        make_command_edit(
            "testpkg", "test_cluster", "1.0.0",
            command="overridden cmd",
        )
        admin_client.delete(
            "/admin/edit/software/testpkg/command/test_cluster/1.0.0"
        )
        remaining = CommandEdit.select().where(
            (CommandEdit.software_name == "testpkg")
            & (CommandEdit.resource_name == "test_cluster")
            & (CommandEdit.software_version == "1.0.0")
        ).count()
        assert remaining == 0

    def test_delete_command_restores_auto_value_in_software_resource(
        self, admin_client, seeded_db, make_command_edit
    ):
        make_command_edit(
            "testpkg", "test_cluster", "1.0.0",
            command="overridden cmd",
            auto_command="module load testpkg/1.0.0",
        )
        SoftwareResource.update(command="overridden cmd").where(
            SoftwareResource.software_id == seeded_db["software"].id
        ).execute()

        admin_client.delete(
            "/admin/edit/software/testpkg/command/test_cluster/1.0.0"
        )

        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == "module load testpkg/1.0.0"


# ---- Atomicity ----

def test_put_atomic_rollback_on_partial_failure(
    admin_client, seeded_db, monkeypatch
):
    """If any save during PUT fails, nothing should persist."""
    def failing_save(self, *args, **kwargs):
        raise RuntimeError("Simulated AI save failure")

    monkeypatch.setattr(AISoftwareInfo, "save", failing_save)

    try:
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={
                "description": "should rollback",
                "ai_description": "should rollback",
            },
        )
    except RuntimeError:
        pass  # propagation under TESTING is expected

    edit = SoftwareEdit.get_or_none(SoftwareEdit.software_name == "testpkg")
    assert edit is None or edit.description is None


# ---- Auto-value snapshot ----

class TestAutoValueSnapshot:
    def test_first_put_captures_snapshot(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "override"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        snapshot = json.loads(edit.auto_values)
        assert snapshot == {"description": "A test package"}

    def test_second_put_preserves_snapshot(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "first override"},
        )
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "second override"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        snapshot = json.loads(edit.auto_values)
        # Snapshot remains the original pre-override auto value
        assert snapshot["description"] == "A test package"

    def test_apply_overrides_refreshes_snapshot(
        self, seeded_db, make_edit, tmp_path
    ):
        from reset_database import apply_overrides

        make_edit(
            "testpkg",
            description="override",
            auto_values={"description": "old auto"},
        )
        # Simulate pipeline rerun: new auto value lands in Software before
        # apply_overrides stomps it.
        Software.update(software_description="new auto").where(
            Software.software_name == "testpkg"
        ).execute()

        apply_overrides(tmp_path / "no_such_dir")

        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        snapshot = json.loads(edit.auto_values)
        assert snapshot["description"] == "new auto"
        sw = Software.get(Software.software_name == "testpkg")
        # Override still stomps as before
        assert sw.software_description == "override"

    def test_revert_with_null_snapshot_is_noop_on_software(
        self, admin_client, seeded_db, make_edit
    ):
        # Legacy override row: no snapshot column data
        make_edit("testpkg", description="overridden")  # auto_values stays NULL
        Software.update(software_description="overridden").where(
            Software.software_name == "testpkg"
        ).execute()

        admin_client.delete("/admin/edit/software/testpkg/description")

        sw = Software.get(Software.software_name == "testpkg")
        # No snapshot -> Software is not touched
        assert sw.software_description == "overridden"
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.description is None

    def test_revert_clears_field_from_auto_values(
        self, admin_client, seeded_db, make_edit
    ):
        make_edit(
            "testpkg",
            description="overridden",
            ai_description="ai overridden",
            auto_values={
                "description": "A test package",
                "ai_description": "AI description for testpkg",
            },
        )
        admin_client.delete("/admin/edit/software/testpkg/description")

        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        snapshot = json.loads(edit.auto_values)
        # description key removed, ai_description still present
        assert "description" not in snapshot
        assert snapshot["ai_description"] == "AI description for testpkg"

    def test_import_strips_incoming_snapshots(
        self, admin_client, seeded_db, tmp_path
    ):
        import io
        payload = json.dumps({
            "software_edits": [{
                "software_name": "testpkg",
                "description": "imported override",
                "auto_values": json.dumps({"description": "FAKE FROM IMPORT"}),
            }],
            "command_edits": [],
        })

        admin_client.post(
            "/admin/software/import",
            data={"overrides_file": (io.BytesIO(payload.encode()), "overrides.json")},
            content_type="multipart/form-data",
        )

        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        snapshot = json.loads(edit.auto_values)
        # The snapshot should be the pre-import sds_db value, NOT the
        # imported "FAKE FROM IMPORT" value.
        assert snapshot["description"] == "A test package"

    def test_command_import_strips_incoming_snapshots(
        self, admin_client, seeded_db
    ):
        import io
        payload = json.dumps({
            "software_edits": [],
            "command_edits": [{
                "software_name": "testpkg",
                "resource_name": "test_cluster",
                "software_version": "1.0.0",
                "command": "imported command",
                "auto_command": "FAKE FROM IMPORT",
            }],
        })

        admin_client.post(
            "/admin/software/import",
            data={"overrides_file": (io.BytesIO(payload.encode()), "overrides.json")},
            content_type="multipart/form-data",
        )

        cmd_edit = CommandEdit.get(
            (CommandEdit.software_name == "testpkg")
            & (CommandEdit.resource_name == "test_cluster")
            & (CommandEdit.software_version == "1.0.0")
        )
        # Snapshot should be the pre-import sds_db value, not the imported one.
        assert cmd_edit.auto_command == "module load testpkg/1.0.0"
