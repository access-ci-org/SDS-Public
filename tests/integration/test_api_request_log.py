"""
Per-request API logging. Every successfully authenticated /api/v1 request
is recorded twice:
- one APIKeyLog DB row (key prefix, endpoint, timestamp), trimmed to the
  newest APIKeyLog.MAX_ROWS entries
- one line on the `sds.api_requests` file logger (key prefix, quoted key
  label, endpoint), which keeps complete history in weekly-rotated files
"""
import logging

import pytest

from app.models.api_key import APIKey
from app.models.api_key_log import APIKeyLog


@pytest.fixture
def auth_enabled(flask_app):
    flask_app.config["REST_API_REQUIRE_AUTH"] = True
    yield
    flask_app.config["REST_API_REQUIRE_AUTH"] = False


class TestRequestLogging:
    def test_authenticated_request_writes_one_row(self, client, api_key, auth_enabled):
        r = client.get("/api/v1/resources", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        rows = list(APIKeyLog.select())
        assert len(rows) == 1
        assert rows[0].endpoint == "/api/v1/resources"
        assert rows[0].key_prefix == api_key[:8]
        assert rows[0].timestamp

    def test_each_request_appends_a_row(self, client, api_key, auth_enabled):
        client.get("/api/v1/resources", headers={"X-API-Key": api_key})
        client.get("/api/v1/software/search", headers={"X-API-Key": api_key})
        endpoints = [row.endpoint for row in APIKeyLog.select().order_by(APIKeyLog.id)]
        assert endpoints == ["/api/v1/resources", "/api/v1/software/search"]

    def test_invalid_key_logs_nothing(self, client, auth_enabled):
        r = client.get("/api/v1/resources", headers={"X-API-Key": "sds_notavalidkey"})
        assert r.status_code == 403
        assert APIKeyLog.select().count() == 0

    def test_missing_key_logs_nothing(self, client, auth_enabled):
        r = client.get("/api/v1/resources")
        assert r.status_code == 401
        assert APIKeyLog.select().count() == 0

    def test_revoked_key_logs_nothing(self, client, auth_enabled):
        raw, key = APIKey.generate(label="revoked")
        key.is_active = False
        key.save()
        r = client.get("/api/v1/resources", headers={"X-API-Key": raw})
        assert r.status_code == 403
        assert APIKeyLog.select().count() == 0

    def test_auth_disabled_logs_nothing(self, client):
        # REST_API_REQUIRE_AUTH is False by default in tests: the request
        # succeeds without a key, so there is no key to attribute a row to.
        r = client.get("/api/v1/resources")
        assert r.status_code == 200
        assert APIKeyLog.select().count() == 0


class TestRequestFileLog:
    """One line per authenticated request on the `sds.api_requests` logger,
    across every endpoint and method the API exposes."""

    # (method, path, json body) for every authenticated endpoint, against the
    # seeded_db names so each request exercises its real 200 path.
    ENDPOINTS = [
        ("get", "/api/v1/resources", None),
        ("get", "/api/v1/software/search", None),
        ("get", "/api/v1/software/testpkg", None),
        ("get", "/api/v1/software/testpkg/containers", None),
        ("get", "/api/v1/software/testpkg/example-use", None),
        ("get", "/api/v1/resources/test_cluster/software", None),
        ("post", "/api/v1/software/match-resources", {"packages": ["testpkg"]}),
    ]

    def _request(self, client, method, path, body, key):
        headers = {"X-API-Key": key}
        if method == "post":
            return client.post(path, json=body, headers=headers)
        return client.get(path, headers=headers)

    @pytest.mark.parametrize("method,path,body", ENDPOINTS)
    def test_each_endpoint_emits_one_line(
        self, client, api_key, seeded_db, auth_enabled, caplog, method, path, body
    ):
        with caplog.at_level(logging.INFO, logger="sds.api_requests"):
            r = self._request(client, method, path, body, api_key)
        assert r.status_code == 200
        records = [rec for rec in caplog.records if rec.name == "sds.api_requests"]
        assert len(records) == 1
        # Full-line equality covers prefix, label, endpoint — and implies the
        # raw key never appears.
        assert records[0].getMessage() == f'{api_key[:8]} "test-key" {path}'

    def test_unlabeled_key_logs_empty_quotes(self, client, auth_enabled, caplog):
        raw, key = APIKey.generate()
        key.save()
        with caplog.at_level(logging.INFO, logger="sds.api_requests"):
            self._request(client, "get", "/api/v1/resources", None, raw)
        records = [rec for rec in caplog.records if rec.name == "sds.api_requests"]
        assert records[0].getMessage() == f'{raw[:8]} "" /api/v1/resources'

    def test_invalid_key_emits_nothing(self, client, auth_enabled, caplog):
        with caplog.at_level(logging.INFO, logger="sds.api_requests"):
            r = client.get("/api/v1/resources", headers={"X-API-Key": "sds_notavalidkey"})
        assert r.status_code == 403
        assert not [rec for rec in caplog.records if rec.name == "sds.api_requests"]

    def test_schema_endpoint_emits_nothing(self, client, auth_enabled, caplog):
        # /schema is unauthenticated by design, so there is no key to log.
        with caplog.at_level(logging.INFO, logger="sds.api_requests"):
            r = client.get("/api/v1/schema")
        assert r.status_code == 200
        assert not [rec for rec in caplog.records if rec.name == "sds.api_requests"]


class TestRollingCap:
    def test_log_keeps_only_newest_max_rows(self, databases, monkeypatch):
        monkeypatch.setattr(APIKeyLog, "MAX_ROWS", 5)
        for i in range(8):
            APIKeyLog.record("sds_test", f"/api/v1/endpoint{i}")
        rows = list(APIKeyLog.select().order_by(APIKeyLog.id))
        assert len(rows) == 5
        assert [row.endpoint for row in rows] == [
            f"/api/v1/endpoint{i}" for i in range(3, 8)
        ]

    def test_log_below_cap_is_untouched(self, databases, monkeypatch):
        monkeypatch.setattr(APIKeyLog, "MAX_ROWS", 5)
        for i in range(3):
            APIKeyLog.record("sds_test", f"/api/v1/endpoint{i}")
        assert APIKeyLog.select().count() == 3
