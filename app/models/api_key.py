import hashlib
import secrets
from datetime import datetime, timezone
from peewee import AutoField, CharField, BooleanField, DateTimeField, IntegerField
from . import PersistentBaseModel


class APIKey(PersistentBaseModel):
    id = AutoField()
    key_hash = CharField(unique=True)
    key_prefix = CharField(max_length=8)
    label = CharField(default="")
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    expires_at = DateTimeField(null=True)
    last_used_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    request_count = IntegerField(default=0)

    class Meta:
        table_name = "api_key"

    @staticmethod
    def generate(label: str = "") -> tuple[str, "APIKey"]:
        """Generate a new key. Returns (raw_key, unsaved APIKey instance).
        raw_key is shown once — caller must save() the instance."""
        raw = "sds_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        key_prefix = raw[:8]
        instance = APIKey(key_hash=key_hash, key_prefix=key_prefix, label=label)
        return raw, instance

    @staticmethod
    def hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at:
            expires = self.expires_at
            if isinstance(expires, str):
                # SQLite hands tz-suffixed DateTimeField values back as ISO
                # strings (peewee's parse formats don't cover the offset).
                expires = datetime.fromisoformat(expires)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                return False
        return True
