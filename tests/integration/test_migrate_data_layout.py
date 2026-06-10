"""
Tests for migrate_data_layout.sh — the legacy-to-new layout migration script.

The script runs on the operator's host (not inside the container) with cwd
set to the SDS repo root. Tests build fake legacy layouts in tmp_path and
invoke the script with cwd pointed there.
"""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "migrate_data_layout.sh"


def run_script(cwd):
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(cwd),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )


def _make_full_legacy_layout(root):
    (root / "software.csv").write_text("name,version\n")
    (root / "container_data").mkdir()
    (root / "container_data" / "x.def").write_text("Bootstrap: docker\n")
    (root / "spider_data").mkdir()
    (root / "spider_data" / "y.json").write_text("{}\n")
    (root / "software_uses").mkdir()
    (root / "analytics").mkdir()
    (root / "analytics" / "analytics_data.json").write_text("{}\n")
    (root / "websites").mkdir()
    (root / "logs").mkdir()
    (root / "sds_persistent.db").write_text("(fake sqlite)\n")


def test_migrates_full_layout(tmp_path):
    _make_full_legacy_layout(tmp_path)
    result = run_script(tmp_path)
    assert result.returncode == 0, result.stderr

    # User inputs at data/
    assert (tmp_path / "data" / "software.csv").exists()
    assert (tmp_path / "data" / "container_data" / "x.def").exists()
    assert (tmp_path / "data" / "spider_data" / "y.json").exists()
    assert (tmp_path / "data" / "software_uses").is_dir()

    # State files at data/state/
    assert (tmp_path / "data" / "state" / "analytics" / "analytics_data.json").exists()
    assert (tmp_path / "data" / "state" / "websites").is_dir()
    assert (tmp_path / "data" / "state" / "logs").is_dir()
    assert (tmp_path / "data" / "state" / "sds_persistent.db").exists()

    # Old paths gone
    assert not (tmp_path / "software.csv").exists()
    assert not (tmp_path / "container_data").exists()
    assert not (tmp_path / "analytics").exists()
    assert not (tmp_path / "sds_persistent.db").exists()


def test_skips_missing_files_silently(tmp_path):
    (tmp_path / "software.csv").write_text("a\n")
    (tmp_path / "sds_persistent.db").write_text("b\n")
    # No container_data, spider_data, analytics, etc.

    result = run_script(tmp_path)
    assert result.returncode == 0, result.stderr

    assert (tmp_path / "data" / "software.csv").exists()
    assert (tmp_path / "data" / "state" / "sds_persistent.db").exists()

    # Items that didn't exist at the source must not appear at the dest
    assert not (tmp_path / "data" / "container_data").exists()
    assert not (tmp_path / "data" / "state" / "analytics").exists()


def test_refuses_when_destination_conflicts_user_input(tmp_path):
    """Both root and data/ have the same user-input file — refuse, list the
    conflict, don't touch either copy."""
    (tmp_path / "software.csv").write_text("legacy\n")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "software.csv").write_text("already migrated\n")

    result = run_script(tmp_path)
    assert result.returncode == 1
    out = (result.stdout + result.stderr).lower()
    assert "data/software.csv" in out
    assert "cannot migrate" in out or "destinations already exist" in out
    # Neither copy touched
    assert (tmp_path / "software.csv").read_text() == "legacy\n"
    assert (tmp_path / "data" / "software.csv").read_text() == "already migrated\n"


def test_refuses_when_destination_conflicts_state(tmp_path):
    """Conflict in the state subdir — refuse and list it."""
    (tmp_path / "sds_persistent.db").write_text("legacy\n")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "state").mkdir()
    (tmp_path / "data" / "state" / "sds_persistent.db").write_text("already migrated\n")

    result = run_script(tmp_path)
    assert result.returncode == 1
    out = (result.stdout + result.stderr).lower()
    assert "data/state/sds_persistent.db" in out
    # Neither copy touched
    assert (tmp_path / "sds_persistent.db").read_text() == "legacy\n"


def test_completes_partial_migration_when_no_conflict(tmp_path):
    """data/ exists with prior-migration content, and a new stray file
    appears at root that has no conflicting destination. The script should
    move the stray file without refusing."""
    # Prior successful migration left these in place:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "software.csv").write_text("already migrated\n")
    (tmp_path / "data" / "state").mkdir()
    (tmp_path / "data" / "state" / "sds_persistent.db").write_text("already migrated\n")
    # New stray file at root (e.g. logs/ re-created by the app):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "sds.log").write_text("fresh log\n")

    result = run_script(tmp_path)
    assert result.returncode == 0, result.stderr

    # Stray moved into state/
    assert (tmp_path / "data" / "state" / "logs" / "sds.log").exists()
    assert not (tmp_path / "logs").exists()
    # Prior-migration content untouched
    assert (tmp_path / "data" / "software.csv").read_text() == "already migrated\n"
    assert (tmp_path / "data" / "state" / "sds_persistent.db").read_text() == "already migrated\n"


def test_no_op_when_no_legacy_files(tmp_path):
    result = run_script(tmp_path)
    assert result.returncode == 0
    assert "no legacy" in (result.stdout + result.stderr).lower()
    # No data/ created
    assert not (tmp_path / "data").exists()


def test_output_includes_docker_run_command(tmp_path):
    (tmp_path / "software.csv").write_text("a\n")
    result = run_script(tmp_path)
    assert result.returncode == 0
    out = result.stdout
    assert "docker run" in out
    assert "-v ./data:/sds/data" in out
    assert "-v ./config.yaml:/sds/config.yaml" in out


def test_output_includes_compose_volumes_snippet(tmp_path):
    (tmp_path / "software.csv").write_text("a\n")
    result = run_script(tmp_path)
    assert result.returncode == 0
    assert "./data:/sds/data" in result.stdout
    assert "./config.yaml:/sds/config.yaml" in result.stdout
    assert "volumes:" in result.stdout


@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="root can write to 0o555 dirs; the permission gate doesn't apply",
)
def test_helpful_error_when_data_dir_not_writable(tmp_path):
    """data/ exists but isn't writable (e.g. stale root-owned mountpoint).
    Script must exit 1 with a message that mentions both the move/backup
    path and the remove path, so users with valuable contents inside data/
    don't lose them."""
    (tmp_path / "software.csv").write_text("legacy\n")
    (tmp_path / "data").mkdir(mode=0o555)  # r-xr-xr-x, no write even for owner
    try:
        result = run_script(tmp_path)
        assert result.returncode == 1
        out = (result.stdout + result.stderr).lower()
        assert "permission denied" in out
        # Both options should be surfaced
        assert "backup" in out
        assert "remove" in out or "rm -rf" in out
        # Legacy file must not have been touched
        assert (tmp_path / "software.csv").exists()
        assert (tmp_path / "software.csv").read_text() == "legacy\n"
    finally:
        # Restore perms so pytest's tmp_path cleanup can succeed
        (tmp_path / "data").chmod(0o755)


def test_output_warns_about_push_scripts(tmp_path):
    """Operators commonly have cron jobs / rsync wrappers pushing data into
    the legacy paths. The script must remind them to update those."""
    (tmp_path / "software.csv").write_text("a\n")
    result = run_script(tmp_path)
    assert result.returncode == 0
    out = result.stdout.lower()
    assert "push" in out
    assert "data/" in out


def test_output_lists_each_moved_file(tmp_path):
    (tmp_path / "software.csv").write_text("a\n")
    (tmp_path / "sds_persistent.db").write_text("b\n")
    result = run_script(tmp_path)
    assert result.returncode == 0
    out = result.stdout
    assert "Moved:" in out
    assert "software.csv" in out
    assert "sds_persistent.db" in out
