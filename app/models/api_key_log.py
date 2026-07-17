from datetime import datetime, timezone
from peewee import AutoField, CharField, DateTimeField
from . import PersistentBaseModel


class APIKeyLog(PersistentBaseModel):
    """One row per authenticated /api/v1 request."""

    id = AutoField()
    key_prefix = CharField(max_length=8)
    endpoint = CharField()
    timestamp = DateTimeField(default=lambda: datetime.now(timezone.utc))

    # Rolling cap: the persistent DB is never wiped, so the log trims itself
    # to the newest MAX_ROWS entries on every insert.
    MAX_ROWS = 10000

    class Meta:
        table_name = "api_key_log"

    @classmethod
    def record(cls, key_prefix: str, endpoint: str) -> "APIKeyLog":
        """Insert a log row, then trim to the newest MAX_ROWS. Rows are only
        ever deleted from the tail, so ids at the top stay contiguous and the
        primary-key window keeps exactly MAX_ROWS rows."""
        row = cls.create(key_prefix=key_prefix, endpoint=endpoint)
        cls.delete().where(cls.id <= row.id - cls.MAX_ROWS).execute()
        return row
