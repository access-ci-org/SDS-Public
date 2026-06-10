"""
Tests for collector.py output paths.

The collector writes to ./data/container_data/<resource>/ and
./data/spider_data/<resource>/ so the output drops directly into an SDS
data/ directory without an intermediate cp/mv step.
"""
import subprocess
from types import SimpleNamespace

import pytest

import collector


def _stub_subprocess_run(monkeypatch, recorder=None):
    """Replace subprocess.run with a no-op that returns success + empty stdout.
    Optionally records each call into a list."""
    def fake_run(*args, **kwargs):
        if recorder is not None:
            recorder.append((args, kwargs))
        return SimpleNamespace(stdout="", stderr="", returncode=0)
    monkeypatch.setattr(subprocess, "run", fake_run)


def test_find_container_files_writes_under_data_dir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _stub_subprocess_run(monkeypatch)

    dest = collector.find_container_files(tmp_path / "src", max_depth=1, resource_name="rtest")

    expected_abs = tmp_path / "data" / "container_data" / "rtest"
    assert expected_abs.is_dir()
    assert (expected_abs / "rtest.csv").exists()
    # Function returns the relative path it built; resolve to compare with the absolute target.
    assert dest.resolve() == expected_abs.resolve()


def test_collect_module_spider_data_writes_under_data_dir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _stub_subprocess_run(monkeypatch)

    dest = collector.collect_module_spider_data("rtest")

    expected_abs = tmp_path / "data" / "spider_data" / "rtest"
    assert expected_abs.is_dir()
    assert dest.resolve() == expected_abs.resolve()


def test_sync_directory_to_remote_uses_data_prefix_for_remote_target(monkeypatch, tmp_path):
    """The remote mkdir and rsync target must include the data/ prefix so
    the remote mirrors the local layout."""
    calls = []
    _stub_subprocess_run(monkeypatch, recorder=calls)

    local_dir = tmp_path / "data" / "container_data" / "rtest"
    local_dir.mkdir(parents=True)

    args = SimpleNamespace(
        remote="cluster.example.edu",
        username="user",
        remote_path="~",
        ssh_options=None,
    )

    ok = collector.sync_directory_to_remote(args, local_dir, remote_subdir="container_data")
    assert ok

    # Inspect the recorded subprocess calls — should be one mkdir and one rsync.
    cmds = [c[0][0] for c in calls]
    # Flatten any list-style commands to strings for easy substring matching.
    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in cmds]

    # mkdir target should be data/container_data, not just container_data
    mkdirs = [c for c in flat if "mkdir" in c]
    assert any("data/container_data" in c for c in mkdirs)

    # rsync target should include data/container_data/rtest
    rsyncs = [c for c in flat if "rsync" in c]
    assert any("data/container_data/rtest" in c for c in rsyncs)


def test_sync_directory_to_remote_handles_spider_data(monkeypatch, tmp_path):
    """Same path-prefixing for spider_data."""
    calls = []
    _stub_subprocess_run(monkeypatch, recorder=calls)

    local_dir = tmp_path / "data" / "spider_data" / "rtest"
    local_dir.mkdir(parents=True)

    args = SimpleNamespace(
        remote="cluster.example.edu",
        username="user",
        remote_path="~",
        ssh_options=None,
    )

    ok = collector.sync_directory_to_remote(args, local_dir, remote_subdir="spider_data")
    assert ok

    cmds = [c[0][0] for c in calls]
    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in cmds]
    rsyncs = [c for c in flat if "rsync" in c]
    assert any("data/spider_data/rtest" in c for c in rsyncs)


def test_run_on_remote_and_sync_back_uses_data_prefix(monkeypatch, tmp_path):
    """The sync-back paths from a remotely-executed collector must look
    under data/ on the remote and write to data/ locally."""
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        # The "exists" check is parsed via .stdout for "exists" substring;
        # return "exists" so the sync code path executes.
        return SimpleNamespace(stdout="exists", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    args = SimpleNamespace(
        remote="cluster.example.edu",
        username="user",
        remote_path="~",
        ssh_options=None,
        resource="rtest",
        directory="/some/dir",
        max_depth=4,
        pre_command=None,
        lmod=True,
        sync=True,
    )

    collector.run_on_remote_and_sync_back(args)

    cmds = [c[0][0] for c in calls]
    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in cmds]

    # Sync-back rsync sources should point at data/container_data and data/spider_data on remote
    rsyncs = [c for c in flat if "rsync" in c]
    joined = " ".join(rsyncs)
    assert "data/container_data/rtest" in joined
    assert "data/spider_data/rtest" in joined
