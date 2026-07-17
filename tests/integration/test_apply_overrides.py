"""
apply_admin_overrides() — the end-of-rebuild projection in reset_database.py
that re-applies SoftwareEdit field overrides and per-chain CommandEdit edits
to the freshly rebuilt sds_db.

Critical invariants:
- non-NULL fields applied to Software / AISoftwareInfo / SoftwareResource
- NULL fields do NOT overwrite auto values
- "" (empty string) explicitly blanks the field
- sds_db reset does not touch sds_persistent
"""
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.software_edit import SoftwareEdit

from reset_database import apply_admin_overrides


def test_non_null_software_field_applied(seeded_db, make_edit):
    make_edit("testpkg", description="overridden via SoftwareEdit")
    apply_admin_overrides()
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "overridden via SoftwareEdit"


def test_non_null_ai_field_applied(seeded_db, make_edit):
    make_edit("testpkg", ai_description="overridden AI desc")
    apply_admin_overrides()
    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_description == "overridden AI desc"


def test_null_field_does_not_overwrite_auto_value(seeded_db, make_edit):
    # An edit row with description=None should leave the auto value alone
    make_edit("testpkg", description=None, web_page="http://override.example")
    apply_admin_overrides()
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "A test package"  # auto value preserved
    assert sw.software_web_page == "http://override.example"  # override applied


def test_empty_string_override_blanks_field(seeded_db, make_edit):
    make_edit("testpkg", description="")
    apply_admin_overrides()
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == ""


def test_command_edit_applied_to_software_resource(seeded_db, make_command_edit):
    # A replacement edit against the collected command projects into the
    # displayed command after a rebuild
    make_command_edit(
        "testpkg", "test_cluster", "1.0.0",
        target_command="module load testpkg/1.0.0",
        replacement="overridden command",
    )
    apply_admin_overrides()
    sr = SoftwareResource.get(
        SoftwareResource.software_id == seeded_db["software"].id
    )
    assert sr.command == "overridden command"


def test_orphan_software_edit_does_not_crash(databases, make_edit):
    # SoftwareEdit row referring to nonexistent software — should be skipped, no error
    make_edit("phantom_pkg", description="orphan override")
    apply_admin_overrides()
    # No assertion needed; success is "didn't raise"


def test_orphan_command_edit_does_not_crash(databases, make_command_edit):
    make_command_edit(
        "phantom_pkg", "phantom_cluster", "9.9.9",
        target_command="module load phantom/9.9.9", suppressed=True,
    )
    apply_admin_overrides()


def test_software_edit_survives_after_call(seeded_db, make_edit):
    """project_all reads from sds_persistent; it must not delete from it."""
    make_edit("testpkg", description="overridden")
    apply_admin_overrides()
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.description == "overridden"


def test_ai_override_creates_missing_ai_row(databases, make_software, make_edit):
    # Software exists but has no AISoftwareInfo row (e.g. USE_AI_INFO off, or the
    # AI pipeline found no match). An AI override in SoftwareEdit must still reach
    # the display, so project_all creates the row from the overrides.
    make_software(name="noai_pkg", description="no ai row")
    make_edit("noai_pkg", ai_research_field="Astrophysics", ai_software_type="CLI")

    apply_admin_overrides()

    sw = Software.get(Software.software_name == "noai_pkg")
    ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
    assert ai is not None
    assert ai.ai_research_field == "Astrophysics"
    assert ai.ai_software_type == "CLI"


def test_no_ai_row_created_without_ai_override(databases, make_software, make_edit):
    # A curated-only override must not spawn an empty AISoftwareInfo row.
    make_software(name="curated_only", description="x")
    make_edit("curated_only", web_page="http://override.example")

    apply_admin_overrides()

    sw = Software.get(Software.software_name == "curated_only")
    assert AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id) is None
