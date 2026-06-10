"""
Tests for the legacy-layout guard at the top of entrypoint.sh.

The guard runs before any container-only setup (conda activate, etc.), so
we can exercise it on the host with `bash entrypoint.sh` and a fake legacy
layout in tmp_path. The conda activate later in the script will fail
under test, but that's after the guard's exit path — we only assert on
guard-visible behavior.
"""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "entrypoint.sh"


def run_script(cwd):
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(cwd),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("legacy_path,kind", [
    ("software.csv", "file"),
    ("container_data", "dir"),
    ("spider_data", "dir"),
    ("software_uses", "dir"),
    ("analytics", "dir"),
    ("websites", "dir"),
    ("logs", "dir"),
    ("sds_persistent.db", "file"),
])
def test_guard_refuses_on_each_legacy_path(tmp_path, legacy_path, kind):
    """Each legacy file or dir at the working root must trip the guard."""
    target = tmp_path / legacy_path
    if kind == "file":
        target.write_text("legacy\n")
    else:
        target.mkdir()

    result = run_script(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    out = result.stdout + result.stderr
    assert "Detected legacy" in out
    assert legacy_path in out
    assert "migrate_data_layout.sh" in out


def test_guard_passes_when_no_legacy_files(tmp_path):
    """With no legacy files, the guard should not fire. The script will
    then fail later (conda activate isn't available in the test env), but
    the guard's error string must not appear."""
    result = run_script(tmp_path)
    assert "Detected legacy" not in (result.stdout + result.stderr)


def test_guard_message_points_at_migration_script_and_setup_doc(tmp_path):
    (tmp_path / "software.csv").write_text("legacy\n")

    result = run_script(tmp_path)
    out = result.stdout + result.stderr
    assert "bash migrate_data_layout.sh" in out
    assert "SDS_SETUP.md" in out


def test_guard_does_not_touch_legacy_files(tmp_path):
    """Guard is read-only — it must not move, rename, or delete anything."""
    (tmp_path / "software.csv").write_text("legacy contents\n")
    (tmp_path / "container_data").mkdir()
    (tmp_path / "container_data" / "x.def").write_text("Bootstrap: docker\n")

    run_script(tmp_path)

    assert (tmp_path / "software.csv").read_text() == "legacy contents\n"
    assert (tmp_path / "container_data" / "x.def").exists()
