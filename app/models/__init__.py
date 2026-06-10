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
    """Add auto_values / auto_command columns to the snapshot tables if
    they don't yet exist. Idempotent. Called on boot so existing
    persistent DBs gain the new columns without losing data."""
    from app.models.software_edit import SoftwareEdit
    from app.models.command_edit import CommandEdit

    migrator = SqliteMigrator(database)
    ops = []

    sw_cols = _existing_columns(database, "softwareedit")
    if "auto_values" not in sw_cols:
        ops.append(
            migrator.add_column(
                "softwareedit", "auto_values", SoftwareEdit.auto_values
            )
        )

    cmd_cols = _existing_columns(database, "commandedit")
    if "auto_command" not in cmd_cols:
        ops.append(
            migrator.add_column(
                "commandedit", "auto_command", CommandEdit.auto_command
            )
        )

    if ops:
        migrate(*ops)
