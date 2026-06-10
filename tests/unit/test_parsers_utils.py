"""
Tests for the small pure helpers in parsers/utils.py.

clean_versions sorts and deduplicates comma-separated version strings.
"""
import pytest

from parsers.utils import clean_versions


def test_clean_versions_empty_string_returns_empty():
    assert clean_versions("") == ""


def test_clean_versions_single_version():
    assert clean_versions("1.0.0") == "1.0.0"


def test_clean_versions_deduplicates():
    assert clean_versions("1.0.0, 1.0.0, 2.0.0") == "1.0.0, 2.0.0"


def test_clean_versions_strips_whitespace():
    assert clean_versions("  1.0.0  ,   2.0.0 ") == "1.0.0, 2.0.0"


def test_clean_versions_drops_empty_entries():
    assert clean_versions("1.0.0,, 2.0.0,") == "1.0.0, 2.0.0"


def test_clean_versions_sorts_alphabetically():
    # peewee uses lexical sort here; "1.13.0" sorts before "2.0.0" lexically
    out = clean_versions("2.0.0, 1.13.0, 1.5.0")
    assert out == "1.13.0, 1.5.0, 2.0.0"


def test_clean_versions_coerces_non_string_input():
    # parsers/utils calls str(version_string) before split
    assert clean_versions(1.0) == "1.0"
