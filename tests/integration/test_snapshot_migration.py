"""
Persistent-DB schema upkeep: the softwareedit snapshot-column migration
and the commandedit per-chain schema recreation.

Runs against a throwaway SQLite database (NOT the main test fixtures), so
the schema code is exercised in isolation from any fixture side effects.
"""
import pytest
from peewee import SqliteDatabase

from app.models import (
    _existing_columns,
    ensure_command_edit_schema,
    ensure_snapshot_columns,
)


@pytest.fixture
def legacy_db(tmp_path):
    """A throwaway sqlite db with the pre-feature schema."""
    db_path = tmp_path / "legacy.db"
    database = SqliteDatabase(str(db_path))
    database.connect()

    # Pre-feature schema: matches what existing production DBs look like
    # before the snapshot column / per-chain schema existed.
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
            auto_command TEXT,
            edited_at TEXT,
            edited_by TEXT,
            PRIMARY KEY (software_name, resource_name, software_version)
        )
    """)
    yield database
    database.close()


# ---- softwareedit snapshot column ----

def test_migration_adds_missing_column(legacy_db):
    assert "auto_values" not in _existing_columns(legacy_db, "softwareedit")

    ensure_snapshot_columns(legacy_db)

    assert "auto_values" in _existing_columns(legacy_db, "softwareedit")


def test_migration_is_idempotent(legacy_db):
    ensure_snapshot_columns(legacy_db)
    # Second call must not raise (would happen if ADD COLUMN ran twice).
    ensure_snapshot_columns(legacy_db)

    assert "auto_values" in _existing_columns(legacy_db, "softwareedit")


def test_migration_preserves_existing_rows(legacy_db):
    legacy_db.execute_sql(
        "INSERT INTO softwareedit (software_name, description) "
        "VALUES ('legacy_pkg', 'legacy desc')"
    )

    ensure_snapshot_columns(legacy_db)

    row = legacy_db.execute_sql(
        "SELECT description, auto_values FROM softwareedit WHERE software_name='legacy_pkg'"
    ).fetchone()
    assert row[0] == "legacy desc"
    assert row[1] is None  # New column NULL for legacy rows


# ---- commandedit per-chain schema ----

def test_old_commandedit_table_is_recreated(legacy_db):
    """Whole-list rows are dropped, not migrated — the shapes are not
    translatable and nothing shipped with the old schema."""
    legacy_db.execute_sql(
        "INSERT INTO commandedit (software_name, resource_name, software_version, command) "
        "VALUES ('legacy_pkg', 'r1', '1.0', 'legacy cmd')"
    )

    ensure_command_edit_schema(legacy_db)

    cols = _existing_columns(legacy_db, "commandedit")
    assert "target_command" in cols
    assert "suppressed" in cols
    assert "command" not in cols
    count = legacy_db.execute_sql("SELECT COUNT(*) FROM commandedit").fetchone()[0]
    assert count == 0


def test_new_commandedit_schema_is_left_alone(legacy_db):
    ensure_command_edit_schema(legacy_db)
    legacy_db.execute_sql(
        "INSERT INTO commandedit (software_name, resource_name, software_version, "
        "target_command, suppressed, is_primary) "
        "VALUES ('pkg', 'r1', '1.0', 'module load pkg/1.0', 1, 0)"
    )

    ensure_command_edit_schema(legacy_db)

    count = legacy_db.execute_sql("SELECT COUNT(*) FROM commandedit").fetchone()[0]
    assert count == 1


def test_missing_commandedit_table_is_created(tmp_path):
    database = SqliteDatabase(str(tmp_path / "fresh.db"))
    database.connect()

    ensure_command_edit_schema(database)

    assert "target_command" in _existing_columns(database, "commandedit")
    database.close()
