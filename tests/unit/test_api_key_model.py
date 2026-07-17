"""
Unit tests for APIKey.is_valid().

No DB needed — is_valid() reads instance attributes only. The string cases
matter because SQLite hands tz-suffixed DateTimeField values back as ISO
strings, so the request path sees strings, not datetimes.
"""
from datetime import datetime, timedelta, timezone

from app.models.api_key import APIKey


def _key(**kwargs):
    kwargs.setdefault("is_active", True)
    kwargs.setdefault("expires_at", None)
    return APIKey(**kwargs)


class TestIsValid:
    def test_active_key_without_expiry_is_valid(self):
        assert _key().is_valid() is True

    def test_revoked_key_is_invalid(self):
        assert _key(is_active=False).is_valid() is False

    def test_revoked_wins_over_future_expiry(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert _key(is_active=False, expires_at=future).is_valid() is False

    def test_expired_datetime_is_invalid(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert _key(expires_at=past).is_valid() is False

    def test_future_datetime_is_valid(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert _key(expires_at=future).is_valid() is True

    def test_expired_naive_datetime_treated_as_utc(self):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        assert _key(expires_at=past).is_valid() is False

    def test_expired_tz_suffixed_string_is_invalid(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert _key(expires_at=past.isoformat(sep=" ")).is_valid() is False

    def test_future_tz_suffixed_string_is_valid(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert _key(expires_at=future.isoformat(sep=" ")).is_valid() is True

    def test_expired_naive_string_treated_as_utc(self):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        assert _key(expires_at=past.isoformat(sep=" ")).is_valid() is False

    def test_future_naive_string_is_valid(self):
        future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
        assert _key(expires_at=future.isoformat(sep=" ")).is_valid() is True
