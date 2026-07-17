"""
Tests for collector.py output paths.

The collector writes to ./data/container_data/<resource>/ and
./data/spider_data/<resource>/ so the output drops directly into an SDS
data/ directory without an intermediate cp/mv step.
"""
import os
import subprocess
import sys
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


def test_collect_module_spider_data_invokes_json_spider(monkeypatch, tmp_path):
    """--lmod also runs the Lmod spider tool for JSON output with dependency
    chains, targeting <resource>_spider.json in the same directory."""
    calls = []
    _stub_subprocess_run(monkeypatch, recorder=calls)
    monkeypatch.chdir(tmp_path)

    collector.collect_module_spider_data("rtest")

    cmds = [c[0][0] for c in calls]
    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in cmds]
    json_calls = [c for c in flat if "jsonSoftwarePage" in c]
    assert len(json_calls) == 1
    assert "data/spider_data/rtest/rtest_spider.json" in json_calls[0]
    # Runs in a login shell so LMOD_DIR / MODULEPATH are initialized
    assert "bash -l -c" in json_calls[0]


def test_collect_module_spider_data_json_failure_is_nonfatal(monkeypatch, tmp_path):
    """A failing spider tool (old Lmod, no Lmod) must not break collection."""
    monkeypatch.chdir(tmp_path)

    def fake_run(*args, **kwargs):
        cmd = args[0]
        flat = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        code = 1 if "jsonSoftwarePage" in flat else 0
        return SimpleNamespace(stdout="", stderr="spider: not found", returncode=code)

    monkeypatch.setattr(subprocess, "run", fake_run)

    dest = collector.collect_module_spider_data("rtest")

    assert dest.resolve() == (tmp_path / "data" / "spider_data" / "rtest").resolve()
    assert not (dest / "rtest_spider.json").exists()


def test_collect_module_spider_data_pretty_prints_json(monkeypatch, tmp_path):
    """The spider tool emits single-line JSON; the stored file is rewritten
    pretty-printed (and stays valid JSON)."""
    import json

    monkeypatch.chdir(tmp_path)
    one_line = '[{"package": "x", "versions": [{"full": "x/1.0", "versionName": "1.0"}]}]'

    def fake_run(*args, **kwargs):
        cmd = args[0]
        flat = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        if "jsonSoftwarePage" in flat:
            json_file = tmp_path / "data" / "spider_data" / "rtest" / "rtest_spider.json"
            json_file.parent.mkdir(parents=True, exist_ok=True)
            json_file.write_text(one_line)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    dest = collector.collect_module_spider_data("rtest")

    content = (dest / "rtest_spider.json").read_text()
    assert "\n" in content
    assert json.loads(content) == json.loads(one_line)


def test_collect_module_spider_data_removes_empty_json_file(monkeypatch, tmp_path):
    """The shell redirect creates the JSON file even when the tool fails;
    an empty leftover must be removed so the parser never sees it."""
    monkeypatch.chdir(tmp_path)

    def fake_run(*args, **kwargs):
        cmd = args[0]
        flat = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        if "jsonSoftwarePage" in flat:
            # Simulate the redirect touching the file before the tool dies
            json_file = tmp_path / "data" / "spider_data" / "rtest" / "rtest_spider.json"
            json_file.parent.mkdir(parents=True, exist_ok=True)
            json_file.touch()
            return SimpleNamespace(stdout="", stderr="boom", returncode=1)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    dest = collector.collect_module_spider_data("rtest")

    assert not (dest / "rtest_spider.json").exists()


def test_apply_pre_command_adopts_environment(monkeypatch):
    """pre_command runs in a login shell and the environment it produces is
    adopted, so later collection subprocesses inherit it."""
    def fake_run(*args, **kwargs):
        cmd = args[0]
        flat = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "echo hi && env -0" in flat
        return SimpleNamespace(
            stdout=b"SDS_TEST_PRE_VAR=hello\0SDS_TEST_PRE_OTHER=x\0",
            stderr=b"",
            returncode=0,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    # Register both vars with monkeypatch so teardown removes them again
    monkeypatch.setenv("SDS_TEST_PRE_VAR", "sentinel")
    monkeypatch.setenv("SDS_TEST_PRE_OTHER", "sentinel")

    collector.apply_pre_command("echo hi")

    assert os.environ["SDS_TEST_PRE_VAR"] == "hello"
    assert os.environ["SDS_TEST_PRE_OTHER"] == "x"


def test_apply_pre_command_failure_exits(monkeypatch):
    """A failing pre_command aborts collection, matching server mode where
    the && chain stops the script from running."""
    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=b"", stderr=b"boom", returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        collector.apply_pre_command("badcmd")


def test_check_python_version_noop_on_supported_interpreter(monkeypatch):
    """A supported running interpreter needs no subprocess check at all."""
    def fail_run(*args, **kwargs):
        raise AssertionError("should not spawn a subprocess")

    monkeypatch.setattr(subprocess, "run", fail_run)

    collector.check_python_version()


def test_check_python_version_exits_when_no_newer_python_available(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 6, 9))

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=b"3.6", stderr=b"", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        collector.check_python_version()


def test_check_python_version_exits_when_python3_missing(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 6, 9))

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("python3")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        collector.check_python_version()


def test_check_python_version_reexecs_with_env_python(monkeypatch):
    """An old interpreter with a suitable python3 on PATH (e.g. loaded by
    pre_command) re-executes the script under that python3."""
    monkeypatch.setattr(sys, "version_info", (3, 6, 9))

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=b"3.8", stderr=b"", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    execs = []

    def fake_execvp(file, args):
        execs.append((file, args))
        raise RuntimeError("execvp called")

    monkeypatch.setattr(os, "execvp", fake_execvp)

    with pytest.raises(RuntimeError, match="execvp called"):
        collector.check_python_version()

    assert execs == [("python3", ["python3"] + sys.argv)]


def test_cluster_mode_version_check_runs_after_pre_command(monkeypatch, tmp_path):
    """On an old interpreter with no newer python3 available, cluster mode
    runs pre_command, then stops at the version check before any
    collection command."""
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(stdout=b"3.6", stderr=b"", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "version_info", (3, 6, 9))
    monkeypatch.setattr(
        sys, "argv",
        ["collector.py", "--resource", "rtest", "--lmod",
         "--pre_command", "module load foo"],
    )

    with pytest.raises(SystemExit):
        collector.main()

    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in calls]
    # Exactly two subprocesses: the pre_command, then the python3 probe
    assert len(flat) == 2
    assert "module load foo && env -0" in flat[0]
    assert flat[1].startswith("python3")


def test_server_mode_version_check_runs_before_remote_execution(monkeypatch, tmp_path):
    """Server mode checks the local interpreter too — its sync-back probes
    need Python 3.7+ — and stops before any ssh/scp on an old one."""
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(stdout=b"3.6", stderr=b"", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "version_info", (3, 6, 9))
    monkeypatch.setattr(
        sys, "argv",
        ["collector.py", "--resource", "rtest", "--lmod",
         "--remote", "cluster.example.edu", "--username", "user"],
    )

    with pytest.raises(SystemExit):
        collector.main()

    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in calls]
    # Only the python3 probe ran; no ssh/scp was attempted
    assert len(flat) == 1
    assert flat[0].startswith("python3")


def test_cluster_mode_runs_pre_command_before_collection(monkeypatch, tmp_path):
    """In cluster mode, --pre_command executes before any collection step."""
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(stdout=b"", stderr=b"", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys, "argv",
        ["collector.py", "--resource", "rtest", "--lmod",
         "--pre_command", "module load foo"],
    )

    collector.main()

    flat = [" ".join(c) if isinstance(c, list) else str(c) for c in calls]
    assert "module load foo && env -0" in flat[0]
    assert any("module --redirect" in c for c in flat[1:])


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
