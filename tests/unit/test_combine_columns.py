"""
combine_columns is a pure pandas function with two modes:
- combine_data=False: fillna behavior (col1 stays, col2 fills col1's blanks)
- combine_data=True: merge + deduplicate values from both columns
"""
import pandas as pd
import pytest

from app.logic.table import combine_columns


# ---- combine_data=False (fillna mode) ----

def test_fillna_mode_both_columns_empty():
    df = pd.DataFrame({"a": ["", ""], "b": ["", ""]})
    out = combine_columns(df, [("a", "b")])
    assert list(out["a"]) == ["", ""]


def test_fillna_mode_primary_empty_secondary_populated():
    df = pd.DataFrame({"a": ["", ""], "b": ["x", "y"]})
    out = combine_columns(df, [("a", "b")])
    assert list(out["a"]) == ["x", "y"]


def test_fillna_mode_primary_populated_secondary_empty():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["", ""]})
    out = combine_columns(df, [("a", "b")])
    assert list(out["a"]) == ["x", "y"]


def test_fillna_mode_both_populated_keeps_primary():
    df = pd.DataFrame({"a": ["primary"], "b": ["secondary"]})
    out = combine_columns(df, [("a", "b")])
    assert list(out["a"]) == ["primary"]


def test_fillna_mode_missing_columns_is_noop():
    df = pd.DataFrame({"a": ["x"]})
    out = combine_columns(df, [("a", "b")])  # 'b' does not exist
    assert list(out["a"]) == ["x"]


def test_fillna_mode_handles_nan_in_primary():
    df = pd.DataFrame({"a": [pd.NA, "y"], "b": ["x", "z"]})
    out = combine_columns(df, [("a", "b")])
    assert list(out["a"]) == ["x", "y"]


# ---- combine_data=True (merge + dedupe mode) ----

def test_merge_mode_both_empty():
    df = pd.DataFrame({"a": [""], "b": [""]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == [""]


def test_merge_mode_primary_only():
    df = pd.DataFrame({"a": ["one, two"], "b": [""]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["one, two"]


def test_merge_mode_secondary_only():
    df = pd.DataFrame({"a": [""], "b": ["three, four"]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["three, four"]


def test_merge_mode_no_overlap_combines_both():
    df = pd.DataFrame({"a": ["one, two"], "b": ["three, four"]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["one, two, three, four"]


def test_merge_mode_full_overlap_deduplicates():
    df = pd.DataFrame({"a": ["one, two"], "b": ["one, two"]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["one, two"]


def test_merge_mode_partial_overlap_deduplicates():
    df = pd.DataFrame({"a": ["one, two"], "b": ["two, three"]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["one, two, three"]


def test_merge_mode_preserves_order_primary_first():
    df = pd.DataFrame({"a": ["b, a"], "b": ["c"]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["b, a, c"]


def test_merge_mode_strips_whitespace_in_inputs():
    df = pd.DataFrame({"a": ["  one  ,  two  "], "b": ["three"]})
    out = combine_columns(df, [("a", "b")], combine_data=True)
    assert list(out["a"]) == ["one, two, three"]


def test_merge_mode_custom_separator():
    df = pd.DataFrame({"a": ["one|two"], "b": ["three"]})
    out = combine_columns(df, [("a", "b")], combine_data=True, separator="|")
    assert list(out["a"]) == ["one|two|three"]


def test_merge_mode_does_not_mutate_input():
    df = pd.DataFrame({"a": ["x"], "b": ["y"]})
    original = df.copy()
    combine_columns(df, [("a", "b")], combine_data=True)
    assert df.equals(original)
