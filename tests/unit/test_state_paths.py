"""
Tests that the route-level path helpers route through state_dir(), so that
setting SDS_DATA_DIR redirects state files (analytics, website titles, DB)
under the configured root.

These cover the integration seam between app/paths.py and the consumers in
app/routes/* and reset_database.py.
"""
from pathlib import Path

import pytest


def test_analytics_file_resolves_under_state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    from app.routes.analytics_routes import analytics_file
    assert analytics_file() == tmp_path / "state" / "analytics" / "analytics_data.json"


def test_analytics_file_defaults_when_env_unset(monkeypatch, tmp_path):
    """With env unset AND no ./data/state/ to auto-detect, falls back to cwd/state/."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    from app.routes.analytics_routes import analytics_file
    assert analytics_file() == Path("state") / "analytics" / "analytics_data.json"


def test_analytics_file_autodetects_data_dir(monkeypatch, tmp_path):
    """With env unset and ./data/state/ present, auto-detect picks data/state/."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDS_DATA_DIR", raising=False)
    (tmp_path / "data" / "state").mkdir(parents=True)
    from app.routes.analytics_routes import analytics_file
    assert analytics_file() == Path("data") / "state" / "analytics" / "analytics_data.json"


def test_website_titles_path_in_routes_resolves_under_state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    from app.routes.software_routes import website_titles_path
    assert website_titles_path() == tmp_path / "state" / "websites" / "website_titles.json"


def test_website_titles_path_in_reset_resolves_under_state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    from reset_database import website_titles_path
    assert website_titles_path() == tmp_path / "state" / "websites" / "website_titles.json"


def test_db_paths_are_under_state_subdir():
    """app/models computes paths at module import using state_dir(). The
    parent dir name must be 'state' regardless of whether data_dir()
    resolved to '.', './data', or an explicit SDS_DATA_DIR — what we're
    locking in here is that the model module uses the helper, not
    Path.cwd() directly."""
    from app.models import db_path, persistent_db_path
    assert db_path.parent.name == "state"
    assert persistent_db_path.parent.name == "state"
    assert db_path.name == "sds_db.db"
    assert persistent_db_path.name == "sds_persistent.db"
