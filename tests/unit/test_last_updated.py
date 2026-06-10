"""
get_last_updated reads app/static/last_updated.txt, which is produced by
the data pipeline. The file is gitignored, so a fresh checkout (CI, new
contributor) doesn't have it. The function must not crash in that case.
"""
from app.logic.lastUpdated import get_last_updated


def test_missing_file_returns_empty_string(tmp_path):
    missing = tmp_path / "does_not_exist.txt"
    assert get_last_updated(file_path=str(missing)) == ""


def test_valid_datetime_is_formatted(tmp_path):
    f = tmp_path / "last_updated.txt"
    f.write_text("2026-06-08 13:45:00\n")
    out = get_last_updated(file_path=str(f))
    assert "June 08, 2026" in out
    assert "01:45:00 PM" in out


def test_malformed_content_returns_raw_string(tmp_path):
    f = tmp_path / "last_updated.txt"
    f.write_text("not-a-date\n")
    assert get_last_updated(file_path=str(f)) == "not-a-date"
