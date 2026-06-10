"""
Global column visibility / rename / reorder via the Settings page.

Per chunk-4 decisions: these are GLOBAL settings (one row per instance),
stored in sds_persistent.db.AppSettings. The AppSettings table doesn't
exist yet, so all persistence-across-restart tests xfail.

Within-process behavior (the mutation takes effect on the next request
in the same process) works today against the TABLE_INFO singleton, so
those tests pass.
"""
import json

import pytest

import app.logic.table as table_module


# ---- Within-process behavior (works today) ----

def test_column_rename_takes_effect_in_same_process(admin_client, seeded_db):
    # Trigger TABLE_INFO initialization
    admin_client.get("/")
    resp = admin_client.post(
        "/update_col_name",
        json={
            "original_key": "software_description",
            "new_name": "Custom Desc",
        },
    )
    assert resp.status_code == 200
    assert table_module.TABLE_INFO.column_names["software_description"] == "Custom Desc"


def test_column_rename_unknown_key_returns_404(admin_client, seeded_db):
    admin_client.get("/")
    resp = admin_client.post(
        "/update_col_name",
        json={"original_key": "no_such_column", "new_name": "Whatever"},
    )
    assert resp.status_code == 404


def test_column_reorder_takes_effect_in_same_process(admin_client, seeded_db):
    admin_client.get("/")
    new_order = ["software_name", "resource_name", "container", "more_info"]
    resp = admin_client.post(
        "/update_col_order",
        json={"col_order": new_order},
    )
    assert resp.status_code == 200
    assert table_module.TABLE_INFO.column_order == new_order


# ---- Persistence across restart (xfail until AppSettings ships) ----

@pytest.mark.xfail(
    reason="AppSettings table not yet built; TABLE_INFO is in-memory only"
)
def test_column_rename_persists_across_restart(admin_client, seeded_db):
    admin_client.get("/")
    admin_client.post(
        "/update_col_name",
        json={
            "original_key": "software_description",
            "new_name": "Persisted Name",
        },
    )

    # Simulate process restart by clearing the singleton.
    table_module.TABLE_INFO = None
    admin_client.get("/")  # reinitializes TABLE_INFO

    assert (
        table_module.TABLE_INFO.column_names["software_description"]
        == "Persisted Name"
    )


@pytest.mark.xfail(
    reason="AppSettings table not yet built; TABLE_INFO is in-memory only"
)
def test_column_reorder_persists_across_restart(admin_client, seeded_db):
    admin_client.get("/")
    new_order = ["software_name", "more_info", "resource_name", "container"]
    admin_client.post("/update_col_order", json={"col_order": new_order})

    table_module.TABLE_INFO = None
    admin_client.get("/")

    assert table_module.TABLE_INFO.column_order == new_order


@pytest.mark.xfail(
    reason="AppSettings table not yet built and /update_col_visibility "
           "currently only handles shareWithDevs"
)
def test_column_visibility_persists_across_restart(admin_client, seeded_db):
    admin_client.get("/")
    resp = admin_client.post("/update_col_visibility/ai_description")
    assert resp.status_code == 200

    table_module.TABLE_INFO = None
    admin_client.get("/")

    # After restart, ai_description should still be hidden
    assert "ai_description" not in table_module.TABLE_INFO.column_order
