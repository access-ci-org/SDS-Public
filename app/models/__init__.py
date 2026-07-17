from pathlib import Path
from peewee import SqliteDatabase, Model
from playhouse.migrate import SqliteMigrator, migrate

from app.paths import state_dir

_SQLITE_PRAGMAS = {"journal_mode": "wal", "foreign_keys": 1}

_state = state_dir()
_state.mkdir(parents=True, exist_ok=True)

db_path = _state / "sds_db.db"
db = SqliteDatabase(str(db_path), pragmas=_SQLITE_PRAGMAS)

persistent_db_path = _state / "sds_persistent.db"
persistent_db = SqliteDatabase(str(persistent_db_path), pragmas=_SQLITE_PRAGMAS)


class BaseModel(Model):
    class Meta:
        database = db


class PersistentBaseModel(Model):
    class Meta:
        database = persistent_db


def _existing_columns(database, table_name):
    return {
        row[1]
        for row in database.execute_sql(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


def ensure_snapshot_columns(database):
    """Add the auto_values column to softwareedit if it doesn't yet exist.
    Idempotent. Called on boot so existing persistent DBs gain the column
    without losing data."""
    from app.models.software_edit import SoftwareEdit

    migrator = SqliteMigrator(database)
    ops = []

    sw_cols = _existing_columns(database, "softwareedit")
    if "auto_values" not in sw_cols:
        ops.append(
            migrator.add_column(
                "softwareedit", "auto_values", SoftwareEdit.auto_values
            )
        )

    if ops:
        migrate(*ops)


def ensure_command_edit_schema(database):
    """Recreate the commandedit table when it predates the per-chain
    schema (no target_command column). Old whole-list rows are dropped,
    not migrated. Idempotent; also creates the table when absent."""
    from app.models.command_edit import CommandEdit

    cols = _existing_columns(database, "commandedit")
    if cols and "target_command" not in cols:
        database.execute_sql("DROP TABLE commandedit")
    with database.bind_ctx([CommandEdit]):
        database.create_tables([CommandEdit], safe=True)
