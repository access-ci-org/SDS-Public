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
from app.models.softwareResourceCommand import SoftwareResourceCommand
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

    def test_put_value_equal_to_auto_creates_no_override(
        self, admin_client, seeded_db
    ):
        # Saving a form whose value matches the auto value must not create
        # an override row.
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "A test package"},
        )
        assert SoftwareEdit.get_or_none(SoftwareEdit.software_name == "testpkg") is None

    def test_put_existing_override_set_back_to_auto_stays_override(
        self, admin_client, seeded_db
    ):
        # Once a field is overridden, re-saving it with the original auto
        # value keeps it an override (revert is the way back to auto).
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "changed"},
        )
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": "A test package"},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.description == "A test package"
        snapshot = json.loads(edit.auto_values)
        assert snapshot["description"] == "A test package"

    def test_put_empty_string_blanks_live_value(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data={"description": ""},
        )
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
        assert edit.description == ""
        sw = Software.get(Software.software_name == "testpkg")
        assert sw.software_description == ""

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


# ---- PUT per-chain command edits ----

AUTO_CMD = "module load testpkg/1.0.0"


def _chain_form(chains, added=None, new="", primary="auto",
                resource="test_cluster", version="1.0.0"):
    """Form fields for one command block, as the panel form submits them."""
    data = {
        "block__0__resource": resource,
        "block__0__version": version,
        "block__0__primary": primary,
    }
    for i, chain in enumerate(chains):
        data[f"block__0__chain__{i}__target"] = chain["target"]
        data[f"block__0__chain__{i}__text"] = chain.get("text", chain["target"])
        if chain.get("hide"):
            data[f"block__0__chain__{i}__hide"] = "on"
    for j, text in enumerate(added or []):
        data[f"block__0__added__{j}"] = text
    if new:
        data["block__0__new"] = new
    return data


class TestPutChainEdits:
    def test_untouched_form_creates_no_edits(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD}]),
        )
        assert CommandEdit.select().count() == 0

    def test_hide_creates_suppress_edit(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD, "hide": True}]),
        )
        edit = CommandEdit.get(CommandEdit.target_command == AUTO_CMD)
        assert edit.suppressed is True
        # the only chain is hidden: nothing left to display
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == ""

    def test_edited_text_creates_replacement(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD, "text": "ml testpkg"}]),
        )
        edit = CommandEdit.get(CommandEdit.target_command == AUTO_CMD)
        assert edit.replacement == "ml testpkg"
        assert edit.suppressed is False
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == "ml testpkg"

    def test_new_input_creates_added_command(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD}], new="run-testpkg.sh"),
        )
        added = CommandEdit.get(CommandEdit.target_command.is_null())
        assert added.replacement == "run-testpkg.sh"
        # projection materialized it after the collected command
        row = SoftwareResourceCommand.get(
            SoftwareResourceCommand.command == "run-testpkg.sh"
        )
        assert row.admin_added is True
        assert row.display_rank == 1
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == AUTO_CMD

    def test_primary_pick_reorders(self, admin_client, seeded_db, make_src_command):
        chained = "module load gcc/12.3.0 testpkg/1.0.0"
        make_src_command(
            seeded_db["software_resource"], chained,
            module_name="testpkg/1.0.0", parent_chain="gcc/12.3.0",
        )
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form(
                [{"target": AUTO_CMD}, {"target": chained}],
                primary="chain__1",
            ),
        )
        edit = CommandEdit.get(CommandEdit.target_command == chained)
        assert edit.is_primary is True
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == chained

    def test_unchanged_edits_preserve_rows_and_audit(self, admin_client, seeded_db):
        form = _chain_form([{"target": AUTO_CMD, "hide": True}])
        admin_client.put("/admin/edit/software/testpkg", data=form)
        edit = CommandEdit.get(CommandEdit.target_command == AUTO_CMD)
        first_id, first_at = edit.id, edit.edited_at

        admin_client.put("/admin/edit/software/testpkg", data=form)

        edit = CommandEdit.get(CommandEdit.target_command == AUTO_CMD)
        assert (edit.id, edit.edited_at) == (first_id, first_at)

    def test_blanking_added_command_removes_it(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD}], new="run-testpkg.sh"),
        )
        assert CommandEdit.select().count() == 1

        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD}], added=[""]),
        )
        assert CommandEdit.select().count() == 0
        assert SoftwareResourceCommand.select().where(
            SoftwareResourceCommand.admin_added == True  # noqa: E712
        ).count() == 0

    def test_command_block_for_unknown_resource_is_ignored(
        self, admin_client, seeded_db
    ):
        # A block whose resource/version pair the software isn't on is
        # silently dropped, not stored as a dangling override.
        resp = admin_client.put(
            "/admin/edit/software/testpkg",
            data={
                "block__0__resource": "ghost_cluster",
                "block__0__version": "9.9.9",
                "block__0__new": "module load ghost/9.9.9",
            },
        )
        assert resp.status_code == 200
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

    def test_delete_ai_field_restores_snapshot_when_ai_row_missing(
        self, admin_client, databases, make_software, make_edit
    ):
        # The AISoftwareInfo row can be absent (e.g. the software never got
        # AI data). Revert must still land the snapshot somewhere visible,
        # so the row is created from it.
        make_software(name="noai_pkg")
        make_edit(
            "noai_pkg",
            ai_description="overridden",
            auto_values={"ai_description": "snapshotted auto"},
        )

        admin_client.delete("/admin/edit/software/noai_pkg/ai_description")

        sw = Software.get(Software.software_name == "noai_pkg")
        ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
        assert ai is not None
        assert ai.ai_description == "snapshotted auto"
        edit = SoftwareEdit.get(SoftwareEdit.software_name == "noai_pkg")
        assert edit.ai_description is None

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
    def test_delete_command_override_removes_rows(self, admin_client, seeded_db):
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD, "text": "overridden cmd"}]),
        )
        assert CommandEdit.select().count() > 0

        admin_client.delete(
            "/admin/edit/software/testpkg/command/test_cluster/1.0.0"
        )
        assert CommandEdit.select().count() == 0

    def test_delete_command_restores_collected_command(
        self, admin_client, seeded_db
    ):
        # No snapshot involved: revert re-projects from the collected
        # command rows, which the override never mutated
        admin_client.put(
            "/admin/edit/software/testpkg",
            data=_chain_form([{"target": AUTO_CMD, "text": "overridden cmd"}]),
        )
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == "overridden cmd"

        admin_client.delete(
            "/admin/edit/software/testpkg/command/test_cluster/1.0.0"
        )

        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == "module load testpkg/1.0.0"

    def test_delete_without_override_row_is_noop(self, admin_client, seeded_db):
        resp = admin_client.delete(
            "/admin/edit/software/testpkg/command/test_cluster/1.0.0"
        )
        assert resp.status_code == 200
        sr = SoftwareResource.get(
            SoftwareResource.software_id == seeded_db["software"].id
        )
        assert sr.command == "module load testpkg/1.0.0"


# ---- Stale command edits ----

class TestStaleCommandEdits:
    def test_stale_edit_listed_in_panel(self, admin_client, seeded_db, make_command_edit):
        make_command_edit(
            "testpkg", "test_cluster", "1.0.0",
            target_command="module load gone/9.9", suppressed=True,
        )
        body = admin_client.get(
            "/admin/edit/software/testpkg"
        ).get_data(as_text=True)
        assert "Stale overrides" in body
        assert "module load gone/9.9" in body

    def test_matching_edit_is_not_listed_as_stale(
        self, admin_client, seeded_db, make_command_edit
    ):
        make_command_edit(
            "testpkg", "test_cluster", "1.0.0",
            target_command=AUTO_CMD, suppressed=True,
        )
        body = admin_client.get(
            "/admin/edit/software/testpkg"
        ).get_data(as_text=True)
        assert "Stale overrides" not in body

    def test_delete_stale_edit_by_id(self, admin_client, seeded_db, make_command_edit):
        edit = make_command_edit(
            "testpkg", "test_cluster", "1.0.0",
            target_command="module load gone/9.9", suppressed=True,
        )
        resp = admin_client.delete(
            f"/admin/edit/software/testpkg/command_edit/{edit.id}"
        )
        assert resp.status_code == 200
        assert CommandEdit.select().count() == 0

    def test_delete_stale_edit_scoped_to_software(
        self, admin_client, seeded_db, make_command_edit
    ):
        edit = make_command_edit(
            "otherpkg", "test_cluster", "1.0.0",
            target_command="module load other/1.0", suppressed=True,
        )
        admin_client.delete(
            f"/admin/edit/software/testpkg/command_edit/{edit.id}"
        )
        # a different software's edit id must not be deletable through
        # this software's URL
        assert CommandEdit.select().count() == 1


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

    def test_project_all_refreshes_snapshot(self, seeded_db, make_edit):
        from app.logic.overrides import project_all

        make_edit(
            "testpkg",
            description="override",
            auto_values={"description": "old auto"},
        )
        # Simulate pipeline rerun: new auto value lands in Software before
        # project_all stomps it.
        Software.update(software_description="new auto").where(
            Software.software_name == "testpkg"
        ).execute()

        project_all()

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

    def test_old_format_command_import_is_rejected(
        self, admin_client, seeded_db
    ):
        # Whole-list exports predate the per-chain model and are not
        # translatable; the whole import is refused and nothing persists
        import io
        payload = json.dumps({
            "software_edits": [],
            "command_edits": [{
                "software_name": "testpkg",
                "resource_name": "test_cluster",
                "software_version": "1.0.0",
                "command": "imported command",
                "auto_command": "old snapshot",
            }],
        })

        resp = admin_client.post(
            "/admin/software/import",
            data={"overrides_file": (io.BytesIO(payload.encode()), "overrides.json")},
            content_type="multipart/form-data",
        )

        assert resp.status_code == 400
        assert CommandEdit.select().count() == 0
