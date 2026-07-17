"""
get_remote_data resolves its cache file under the SDS data directory
(data/state/api_response.json via app.paths), honoring SDS_DATA_DIR.

Calling with an empty software list skips the network entirely: the batch
loop never runs, so the function falls through to the cached-data path.
"""
import json

from reset_database import get_remote_data


def _call(**kwargs):
    return get_remote_data(
        api_key="",
        software=[],
        share_with_devs=False,
        share_with_others=False,
        **kwargs,
    )


def test_cache_file_defaults_to_state_dir(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    cached = [{"software_name": "genericsw"}]
    (state / "api_response.json").write_text(json.dumps(cached))
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))

    assert _call() == cached


def test_missing_cache_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))

    assert _call() == []


def test_explicit_cache_path_wins_over_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path))
    explicit = tmp_path / "elsewhere.json"
    cached = [{"software_name": "othersw"}]
    explicit.write_text(json.dumps(cached))

    assert _call(api_data_save_file=explicit) == cached
