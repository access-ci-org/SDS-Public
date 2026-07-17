"""
Cross-operation override sequences through the real entry points: saves and
reverts via the admin routes, rebuilds via apply_example_use_files() +
project_all().

Single operations are covered elsewhere; these tests chain them, because the
display bugs this area has produced all lived between operations (an override
written by one path, dropped or mangled by the next), not inside one.
"""
import io
import json

from app.logic.overrides import apply_example_use_files, project_all
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.resource import Resource
from app.models.software import Software
from app.models.software_edit import SoftwareEdit
from app.models.softwareResource import SoftwareResource


def _rebuild_pipeline(*, description, ai_description=None,
                      command="module load testpkg/1.0.0"):
    """Wipe the transient tables and re-ingest testpkg, as a reset does.
    ai_description=None means the pipeline produced no AI row at all."""
    SoftwareResource.delete().execute()
    AISoftwareInfo.delete().execute()
    Software.delete().execute()
    Resource.delete().execute()

    resource = Resource.create(resource_name="test_cluster")
    sw = Software.create(
        software_name="testpkg",
        software_description=description,
        software_web_page="",
        software_documentation="",
        software_use_link="",
    )
    SoftwareResource.create(
        software_id=sw,
        resource_id=resource,
        software_version="1.0.0",
        command=command,
    )
    if ai_description is not None:
        AISoftwareInfo.create(software_id=sw, ai_description=ai_description)
    return sw


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


def test_put_survives_rebuild_and_revert_restores_fresh_auto(
    admin_client, seeded_db
):
    admin_client.put(
        "/admin/edit/software/testpkg",
        data={"description": "admin override"},
    )

    _rebuild_pipeline(description="fresh pipeline desc")
    project_all()

    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "admin override"

    # Revert restores the value the latest rebuild produced, not the one
    # captured when the override was first saved.
    admin_client.delete("/admin/edit/software/testpkg/description")

    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "fresh pipeline desc"
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.description is None


def test_ai_override_survives_rebuild_that_drops_ai_row(
    admin_client, seeded_db
):
    admin_client.put(
        "/admin/edit/software/testpkg",
        data={"ai_description": "admin AI"},
    )

    # The rebuilt pipeline produced no AI row for this software.
    _rebuild_pipeline(description="A test package", ai_description=None)
    project_all()

    sw = Software.get(Software.software_name == "testpkg")
    ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
    assert ai is not None
    assert ai.ai_description == "admin AI"

    # The auto value for a row the projection had to create is empty, and
    # revert restores exactly that.
    admin_client.delete("/admin/edit/software/testpkg/ai_description")

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == sw.id)
    assert ai.ai_description == ""
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_description is None


def test_revert_restores_latest_file_content(admin_client, seeded_db, tmp_path):
    uses = tmp_path / "software_uses"
    uses.mkdir()
    (uses / "testpkg.md").write_text("file v1")
    apply_example_use_files(uses)
    project_all()

    admin_client.put(
        "/admin/edit/software/testpkg",
        data={"ai_example_use": "admin override"},
    )

    # The file changes on disk before the next rebuild.
    (uses / "testpkg.md").write_text("file v2")
    apply_example_use_files(uses)
    project_all()

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "admin override"

    admin_client.delete("/admin/edit/software/testpkg/ai_example_use")

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "file v2"


def test_imported_override_survives_rebuild(admin_client, seeded_db):
    _post_overrides(admin_client, {
        "software_edits": [
            {"software_name": "testpkg", "description": "imported override"}
        ],
        "command_edits": [],
    })

    _rebuild_pipeline(description="fresh pipeline desc")
    project_all()

    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "imported override"


def test_dormant_import_applies_once_software_exists(admin_client, databases):
    # An override imported for software this instance doesn't have yet is
    # stored, does nothing, and projects once the software shows up.
    resp = _post_overrides(admin_client, {
        "software_edits": [
            {"software_name": "future_pkg", "description": "dormant override"}
        ],
        "command_edits": [],
    })
    assert resp.status_code in (200, 302)
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "future_pkg")
    assert edit.description == "dormant override"

    Software.create(
        software_name="future_pkg",
        software_description="from pipeline",
        software_web_page="",
        software_documentation="",
        software_use_link="",
    )
    project_all()

    sw = Software.get(Software.software_name == "future_pkg")
    assert sw.software_description == "dormant override"
