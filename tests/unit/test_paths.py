"""
Tests for app/paths.py — the SDS_DATA_DIR resolution helpers.

Resolution order for data_dir():
  1. SDS_DATA_DIR env var if set (and non-empty)
  2. ./data if ./data/state/ exists (auto-detect post-migration layout)
  3. cwd

state_dir() is always data_dir() / "state".

Both helpers re-evaluate on every call so tests (and the running app) can
change layout without restarting.
"""
from pathlib import Path

import pytest

from app.paths import data_dir, state_dir


# --- env var takes precedence ---

def test_data_dir_uses_env_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    assert data_dir() == tmp_path


def test_data_dir_uses_env_when_set_to_relative_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SDS_DATA_DIR", "./mydata")
    assert data_dir() == Path("./mydata")


def test_data_dir_env_wins_over_autodetect(monkeypatch, tmp_path):
    """Even when ./data/state/ exists, an explicit env var wins."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "state").mkdir(parents=True)
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path / "elsewhere"))
    assert data_dir() == tmp_path / "elsewhere"


def test_data_dir_returns_path_instance(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    assert isinstance(data_dir(), Path)


def test_data_dir_rereads_env_each_call(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    first = data_dir()

    other = tmp_path / "other"
    monkeypatch.setenv("SDS_DATA_DIR", str(other))
    second = data_dir()

    assert first == tmp_path
    assert second == other


# --- auto-detect ---

def test_data_dir_autodetects_data_when_state_subdir_present(monkeypatch, tmp_path):
    """If SDS_DATA_DIR is unset but ./data/state/ exists, default to ./data.
    This is the post-migration ergonomics — users don't need to remember
    to set the env var."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    (tmp_path / "data" / "state").mkdir(parents=True)

    assert data_dir() == Path("data")


def test_data_dir_does_not_autodetect_when_state_missing(monkeypatch, tmp_path):
    """./data/ exists but ./data/state/ doesn't — not post-migration layout."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    (tmp_path / "data").mkdir()

    assert data_dir() == Path(".")


def test_data_dir_does_not_autodetect_when_state_is_a_file(monkeypatch, tmp_path):
    """If somehow data/state is a regular file (not a dir), don't auto-detect."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "state").write_text("not a dir")

    assert data_dir() == Path(".")


# --- bare fallback ---

def test_data_dir_defaults_to_cwd_when_env_unset_and_no_data(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    assert data_dir() == Path(".")


def test_data_dir_empty_env_falls_back(monkeypatch, tmp_path):
    """Empty string env var treated as unset → fall through to auto-detect/cwd."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SDS_DATA_DIR", "")
    assert data_dir() == Path(".")


# --- state_dir ---

def test_state_dir_is_data_dir_slash_state(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    assert state_dir() == tmp_path / "state"


def test_state_dir_defaults_to_cwd_slash_state(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    assert state_dir() == Path("./state")


def test_state_dir_uses_autodetected_data_dir(monkeypatch, tmp_path):
    """When auto-detect kicks in, state_dir() returns data/state."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    (tmp_path / "data" / "state").mkdir(parents=True)

    assert state_dir() == Path("data") / "state"


def test_state_dir_tracks_data_dir_changes(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    assert state_dir() == tmp_path / "state"

    other = tmp_path / "other"
    monkeypatch.setenv("SDS_DATA_DIR", str(other))
    assert state_dir() == other / "state"


def test_state_dir_returns_path_instance(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    assert isinstance(state_dir(), Path)
