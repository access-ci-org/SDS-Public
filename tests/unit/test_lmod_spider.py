"""
get_software_info parses lmod `module spider` output files into
{name, versions, description} records. The function takes regex args
with sensible defaults; we exercise the defaults against fixture files.
"""
import pytest

from parsers.lmod.parse_spider import get_software_info


def test_normal_entries_parse_name_and_versions(fixture_path):
    out = get_software_info(fixture_path("spider/normal.txt"))
    names = [entry["name"] for entry in out]
    assert "pytorch" in names
    assert "numpy" in names


def test_normal_entries_extract_description(fixture_path):
    out = get_software_info(fixture_path("spider/normal.txt"))
    pytorch = next(e for e in out if e["name"] == "pytorch")
    assert "PyTorch" in pytorch["description"]


def test_multi_version_collects_all_versions(fixture_path):
    out = get_software_info(fixture_path("spider/multi_version.txt"))
    python = next(e for e in out if e["name"] == "python")
    # versions is a dict keyed by cleaned version
    assert set(python["versions"].keys()) == {"3.11.1", "3.10.5", "3.9.7"}


def test_multi_version_preserves_uncleaned_command(fixture_path):
    out = get_software_info(fixture_path("spider/multi_version.txt"))
    python = next(e for e in out if e["name"] == "python")
    # Values are the original uncleaned version strings (used to build commands later)
    assert python["versions"]["3.11.1"] == "python/3.11.1"


def test_truncated_version_uses_ellipsis_key(fixture_path):
    out = get_software_info(fixture_path("spider/truncated.txt"))
    bigsw = next(e for e in out if e["name"] == "bigsoftware")
    assert "..." in bigsw["versions"]


def test_no_description_yields_empty_description(fixture_path):
    out = get_software_info(fixture_path("spider/no_description.txt"))
    pkg = next(e for e in out if e["name"] == "tinypkg")
    assert pkg["description"] == ""


def test_lmod_description_separator_strips_metadata(fixture_path):
    out = get_software_info(fixture_path("spider/normal.txt"))
    pytorch = next(e for e in out if e["name"] == "pytorch")
    # The '----' lines are markers; description should not contain them
    assert "----" not in pytorch["description"]
