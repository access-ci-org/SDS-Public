"""
Example-use files (data/software_uses) are a pipeline data source:
apply_example_use_files() runs on every rebuild, before project_all(), and
writes each file's content to AISoftwareInfo.ai_example_use.

Spec:
- software name = file name, with a .md suffix stripped; .md wins when both
  forms exist
- re-applied every rebuild, so disk edits show after the next rebuild
- the AISoftwareInfo row is created when missing
- an empty file explicitly blanks the field
- admin overrides still win (project_all runs after), and an override
  byte-identical to the file content is cleared as redundant
"""
import json

from app.logic.overrides import apply_example_use_files, project_all
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.software import Software
from app.models.software_edit import SoftwareEdit


def _use_dir(tmp_path):
    d = tmp_path / "software_uses"
    d.mkdir()
    return d


def _snapshot(edit):
    return json.loads(edit.auto_values) if edit.auto_values else {}


def test_file_content_applied_to_ai_row(seeded_db, tmp_path):
    d = _use_dir(tmp_path)
    (d / "testpkg.md").write_text("# Example\nUse it like this.")

    apply_example_use_files(d)

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert "Use it like this" in ai.ai_example_use


def test_reapplied_on_every_run(seeded_db, tmp_path):
    d = _use_dir(tmp_path)
    f = d / "testpkg.md"
    f.write_text("first version")
    apply_example_use_files(d)

    f.write_text("second version")
    apply_example_use_files(d)

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "second version"


def test_bare_filename_equivalent_to_md(seeded_db, tmp_path):
    d = _use_dir(tmp_path)
    (d / "testpkg").write_text("bare-name content")

    apply_example_use_files(d)

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "bare-name content"


def test_md_wins_when_both_forms_exist(seeded_db, tmp_path):
    d = _use_dir(tmp_path)
    (d / "testpkg").write_text("bare content")
    (d / "testpkg.md").write_text("markdown content")

    apply_example_use_files(d)

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "markdown content"


def test_creates_ai_row_when_missing(databases, make_software, tmp_path):
    # No AISoftwareInfo row exists (e.g. USE_API off) — the file must still
    # reach the display.
    make_software(name="noai_pkg")
    d = _use_dir(tmp_path)
    (d / "noai_pkg.md").write_text("file shows up")

    apply_example_use_files(d)

    sw = Software.get(Software.software_name == "noai_pkg")
    ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
    assert ai is not None
    assert ai.ai_example_use == "file shows up"


def test_empty_file_blanks_field(seeded_db, tmp_path):
    AISoftwareInfo.update(ai_example_use="from pipeline").where(
        AISoftwareInfo.software_id == seeded_db["software"].id
    ).execute()
    d = _use_dir(tmp_path)
    (d / "testpkg.md").write_text("")

    apply_example_use_files(d)

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == ""


def test_admin_override_wins_after_projection(seeded_db, make_edit, tmp_path):
    make_edit("testpkg", ai_example_use="admin value")
    d = _use_dir(tmp_path)
    (d / "testpkg.md").write_text("file value")

    apply_example_use_files(d)
    project_all()

    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "admin value"
    # The file content is the field's auto value, so revert restores it.
    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert _snapshot(edit)["ai_example_use"] == "file value"


def test_override_identical_to_file_is_cleared(seeded_db, make_edit, tmp_path):
    make_edit(
        "testpkg",
        ai_example_use="same content",
        auto_values={"ai_example_use": "stale snapshot"},
    )
    d = _use_dir(tmp_path)
    (d / "testpkg.md").write_text("same content")

    apply_example_use_files(d)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_example_use is None
    assert "ai_example_use" not in _snapshot(edit)
    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "same content"


def test_ui_override_matching_file_clears_on_rebuild(
    admin_client, seeded_db, tmp_path
):
    # An override saved through the panel that exactly matches the file
    # collapses back to "no override" on the next rebuild — it duplicates
    # the auto value, and clearing it keeps future file edits live.
    d = _use_dir(tmp_path)
    (d / "testpkg.md").write_text("shared text")

    admin_client.put(
        "/admin/edit/software/testpkg",
        data={"ai_example_use": "shared text"},
    )
    apply_example_use_files(d)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_example_use is None
    assert "ai_example_use" not in _snapshot(edit)
    ai = AISoftwareInfo.get(AISoftwareInfo.software_id == seeded_db["software"].id)
    assert ai.ai_example_use == "shared text"


def test_differing_override_survives(seeded_db, make_edit, tmp_path):
    make_edit("testpkg", ai_example_use="admin value")
    d = _use_dir(tmp_path)
    (d / "testpkg.md").write_text("file value")

    apply_example_use_files(d)

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "testpkg")
    assert edit.ai_example_use == "admin value"


def test_unknown_software_file_skipped(databases, tmp_path):
    d = _use_dir(tmp_path)
    (d / "ghost_pkg.md").write_text("no such software")
    apply_example_use_files(d)  # should not raise


def test_missing_dir_does_not_crash(databases, tmp_path):
    apply_example_use_files(tmp_path / "does_not_exist")


def test_empty_dir_does_not_crash(databases, tmp_path):
    apply_example_use_files(_use_dir(tmp_path))


def test_subdirectory_skipped(seeded_db, tmp_path):
    d = _use_dir(tmp_path)
    (d / "some_subdir").mkdir()
    apply_example_use_files(d)  # should not raise
