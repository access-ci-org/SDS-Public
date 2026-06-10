"""
Legacy software_uses/*.md files migrate into SoftwareEdit.ai_example_use
on first run of apply_overrides. The migration is one-shot — re-running
must not overwrite existing overrides.
"""
import pytest

from app.models.software_edit import SoftwareEdit

from reset_database import apply_overrides


def test_markdown_file_imported_on_first_run(seeded_db, tmp_path):
    md_dir = tmp_path / "uses"
    md_dir.mkdir()
    (md_dir / "testpkg.md").write_text("# Example\nUse it like this.")

    apply_overrides(md_dir)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_example_use is not None
    assert "Use it like this" in edit.ai_example_use


def test_markdown_does_not_overwrite_existing_override(
    seeded_db, tmp_path, make_edit
):
    make_edit("testpkg", ai_example_use="admin-edited example")

    md_dir = tmp_path / "uses"
    md_dir.mkdir()
    (md_dir / "testpkg.md").write_text("from markdown")

    apply_overrides(md_dir)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_example_use == "admin-edited example"


def test_markdown_fills_null_field_only(seeded_db, tmp_path, make_edit):
    # Edit row exists but ai_example_use is NULL — markdown should fill it
    make_edit("testpkg", description="some desc")  # ai_example_use unset → NULL

    md_dir = tmp_path / "uses"
    md_dir.mkdir()
    (md_dir / "testpkg.md").write_text("filled from md")

    apply_overrides(md_dir)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_example_use == "filled from md"
    assert edit.description == "some desc"  # other fields untouched


def test_missing_software_uses_dir_does_not_crash(seeded_db, tmp_path):
    md_dir = tmp_path / "does_not_exist"  # not created
    apply_overrides(md_dir)  # should not raise


def test_empty_software_uses_dir_does_not_crash(seeded_db, tmp_path):
    md_dir = tmp_path / "uses"
    md_dir.mkdir()
    apply_overrides(md_dir)
