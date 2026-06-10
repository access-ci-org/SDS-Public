"""
Migration idempotency for the auto-value snapshot columns.

Runs against a throwaway SQLite database (NOT the main test fixtures), so
the migration code is exercised in isolation from any fixture side effects.
"""
import tempfile
from pathlib import Path

import pytest
from peewee import SqliteDatabase

from app.models import ensure_snapshot_columns, _existing_columns


@pytest.fixture
def legacy_db(tmp_path):
    """A throwaway sqlite db with the pre-feature schema (no snapshot cols)."""
    db_path = tmp_path / "legacy.db"
    database = SqliteDatabase(str(db_path))
    database.connect()

    # Pre-feature schema: matches what existing production DBs look like
    # before the snapshot columns are added.
    database.execute_sql("""
        CREATE TABLE softwareedit (
            software_name VARCHAR(255) NOT NULL PRIMARY KEY,
            description TEXT,
            web_page TEXT,
            documentation TEXT,
            use_link TEXT,
            ai_description TEXT,
            ai_software_type TEXT,
            ai_software_class TEXT,
            ai_research_field TEXT,
            ai_research_area TEXT,
            ai_research_discipline TEXT,
            ai_core_features TEXT,
            ai_general_tags TEXT,
            ai_example_use TEXT,
            edited_at TEXT,
            edited_by TEXT
        )
    """)
    database.execute_sql("""
        CREATE TABLE commandedit (
            software_name VARCHAR(255) NOT NULL,
            resource_name VARCHAR(255) NOT NULL,
            software_version VARCHAR(255) NOT NULL,
            command TEXT,
            edited_at TEXT,
            edited_by TEXT,
            PRIMARY KEY (software_name, resource_name, software_version)
        )
    """)
    yield database
    database.close()


def test_migration_adds_missing_columns(legacy_db):
    assert "auto_values" not in _existing_columns(legacy_db, "softwareedit")
    assert "auto_command" not in _existing_columns(legacy_db, "commandedit")

    ensure_snapshot_columns(legacy_db)

    assert "auto_values" in _existing_columns(legacy_db, "softwareedit")
    assert "auto_command" in _existing_columns(legacy_db, "commandedit")


def test_migration_is_idempotent(legacy_db):
    ensure_snapshot_columns(legacy_db)
    # Second call must not raise (would happen if ADD COLUMN ran twice).
    ensure_snapshot_columns(legacy_db)

    assert "auto_values" in _existing_columns(legacy_db, "softwareedit")
    assert "auto_command" in _existing_columns(legacy_db, "commandedit")


def test_migration_preserves_existing_rows(legacy_db):
    legacy_db.execute_sql(
        "INSERT INTO softwareedit (software_name, description) "
        "VALUES ('legacy_pkg', 'legacy desc')"
    )
    legacy_db.execute_sql(
        "INSERT INTO commandedit (software_name, resource_name, software_version, command) "
        "VALUES ('legacy_pkg', 'r1', '1.0', 'legacy cmd')"
    )

    ensure_snapshot_columns(legacy_db)

    row = legacy_db.execute_sql(
        "SELECT description, auto_values FROM softwareedit WHERE software_name='legacy_pkg'"
    ).fetchone()
    assert row[0] == "legacy desc"
    assert row[1] is None  # New column NULL for legacy rows

    cmd_row = legacy_db.execute_sql(
        "SELECT command, auto_command FROM commandedit WHERE software_name='legacy_pkg'"
    ).fetchone()
    assert cmd_row[0] == "legacy cmd"
    assert cmd_row[1] is None
