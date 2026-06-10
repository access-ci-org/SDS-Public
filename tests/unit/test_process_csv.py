"""
process_csv_data sits in reset_database.py. We test only the error paths
here because the happy path needs the full DB and is exercised in the
integration tests.

The malformed-CSV path currently raises NameError instead of
DataProcessingError (undefined `e` in the ParserError handler).
That test is xfail until the handler is fixed.
"""
import pytest

from parsers.exceptions import DataProcessingError
from reset_database import process_csv_data


def test_empty_csv_returns_silently(fixture_path):
    # An empty file short-circuits before pd.read_csv runs.
    process_csv_data(fixture_path("csv/empty.csv"), blacklist=set())


def test_malformed_csv_raises_data_processing_error(fixture_path):
    with pytest.raises(DataProcessingError):
        process_csv_data(fixture_path("csv/malformed.csv"), blacklist=set())
