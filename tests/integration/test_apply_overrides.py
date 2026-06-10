"""
apply_overrides() — the function that re-applies SoftwareEdit + CommandEdit
to the freshly rebuilt sds_db at the end of reset_database.py.

Critical invariants:
- non-NULL fields applied to Software / AISoftwareInfo / SoftwareResource
- NULL fields do NOT overwrite auto values
- "" (empty string) explicitly blanks the field
- sds_db reset does not touch sds_persistent
"""
from pathlib import Path

import pytest

from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.software_edit import SoftwareEdit

from reset_database import apply_overrides


NONEXISTENT = Path("/tmp/never_existed_software_uses_dir_for_test")


def test_non_null_software_field_applied(seeded_db, make_edit):
    make_edit("testpkg", description="overridden via SoftwareEdit")
    apply_overrides(NONEXISTENT)
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "overridden via SoftwareEdit"


def test_non_null_ai_field_applied(seeded_db, make_edit):
    make_edit("testpkg", ai_description="overridden AI desc")
    apply_overrides(NONEXISTENT)
    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_description == "overridden AI desc"


def test_null_field_does_not_overwrite_auto_value(seeded_db, make_edit):
    # An edit row with description=None should leave the auto value alone
    make_edit("testpkg", description=None, web_page="http://override.example")
    apply_overrides(NONEXISTENT)
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == "A test package"  # auto value preserved
    assert sw.software_web_page == "http://override.example"  # override applied


def test_empty_string_override_blanks_field(seeded_db, make_edit):
    make_edit("testpkg", description="")
    apply_overrides(NONEXISTENT)
    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_description == ""


def test_command_edit_applied_to_software_resource(seeded_db, make_command_edit):
    make_command_edit(
        "testpkg", "test_cluster", "1.0.0",
        command="overridden command",
    )
    apply_overrides(NONEXISTENT)
    sr = SoftwareResource.get(
        SoftwareResource.software_id == seeded_db["software"].id
    )
    assert sr.command == "overridden command"


def test_orphan_software_edit_does_not_crash(databases, make_edit):
    # SoftwareEdit row referring to nonexistent software — should be skipped, no error
    make_edit("phantom_pkg", description="orphan override")
    apply_overrides(NONEXISTENT)
    # No assertion needed; success is "didn't raise"


def test_orphan_command_edit_does_not_crash(databases, make_command_edit):
    make_command_edit(
        "phantom_pkg", "phantom_cluster", "9.9.9",
        command="orphan",
    )
    apply_overrides(NONEXISTENT)


def test_software_edit_survives_after_call(seeded_db, make_edit):
    """apply_overrides reads from sds_persistent; it must not delete from it."""
    make_edit("testpkg", description="overridden")
    apply_overrides(NONEXISTENT)
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.description == "overridden"
