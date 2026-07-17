"""Unit tests for the SDS MCP server's key-resolution and request plumbing.

These assert the *intended* contract of the bearer-token pass-through, not a
mirror of the current implementation — e.g. a request in scope with no bearer
must never borrow an ambient SDS_API_KEY
(test_http_request_without_bearer_does_not_leak_env_key).

The pieces under test:
  * _bearer_from_request() — pull the caller's key out of an incoming HTTP
    request's `Authorization: Bearer <key>` header.
  * _current_api_key()     — bearer (HTTP) takes precedence; env key is the
    stdio fallback.
  * _headers()             — attach X-API-Key only when a key is resolved.
  * get()/post()           — the resolved key reaches the outgoing REST call.
  * server.main()          — MCP_TRANSPORT selects the transport.

Requires the `sds_mcp` package to be importable (e.g. `pip install -e ./mcp`).
"""
import contextlib
from types import SimpleNamespace

import pytest

# The sds_mcp package (mcp/) is installed separately from the backend test deps
# (pip install -e ./mcp). If it isn't present, skip these tests with a pointer
# rather than erroring the whole collection.
_MCP_HINT = "run `pip install -e ./mcp` to run the MCP client tests"
pytest.importorskip("sds_mcp", reason=_MCP_HINT)
pytest.importorskip("starlette", reason=_MCP_HINT)

from sds_mcp import client

# Production request headers are Starlette's case-insensitive Headers; use the
# real type so the case-insensitivity assumption is exercised faithfully.
from starlette.datastructures import Headers

# Tests that drive an in-scope HTTP request need the SDK's request contextvar.
# If a future SDK layout moved it, _request_ctx is None and those tests skip
# (the degrade-to-empty path is covered separately).
requires_ctx = pytest.mark.skipif(
    client._request_ctx is None,
    reason="MCP SDK request_ctx contextvar unavailable in this version",
)


@contextlib.contextmanager
def http_request(headers):
    """Simulate an in-scope HTTP request.

    headers=dict -> a request whose .headers is a Starlette Headers built from it.
    headers=None -> a request context whose .request is None (no transport request).
    """
    request = None if headers is None else SimpleNamespace(headers=Headers(headers))
    token = client._request_ctx.set(SimpleNamespace(request=request))
    try:
        yield
    finally:
        client._request_ctx.reset(token)


class TestBearerExtraction:
    """The security-critical parser: header value in, key out."""

    @requires_ctx
    @pytest.mark.parametrize(
        "header, expected",
        [
            # Happy path.
            ("Bearer sds_abc123", "sds_abc123"),
            # Auth scheme is case-insensitive (RFC 7235).
            ("bearer sds_abc123", "sds_abc123"),
            ("BEARER sds_abc123", "sds_abc123"),
            ("BeArEr sds_abc123", "sds_abc123"),
            # Tolerate sloppy spacing around the token.
            ("Bearer    sds_abc123", "sds_abc123"),
            ("Bearer sds_abc123   ", "sds_abc123"),
            # No usable token -> no key.
            ("Bearer", ""),
            ("Bearer ", ""),
            # Wrong scheme -> not our token.
            ("Basic dXNlcjpwYXNz", ""),
            # Raw key with no scheme is not accepted.
            ("sds_abc123", ""),
            # Empty header.
            ("", ""),
        ],
    )
    def test_parses_authorization_header(self, header, expected):
        with http_request({"authorization": header}):
            assert client._bearer_from_request() == expected

    @requires_ctx
    def test_header_name_is_case_insensitive(self):
        with http_request({"Authorization": "Bearer sds_capital"}):
            assert client._bearer_from_request() == "sds_capital"

    @requires_ctx
    def test_no_authorization_header_yields_empty(self):
        with http_request({"x-other": "1"}):
            assert client._bearer_from_request() == ""

    def test_no_request_in_scope_yields_empty(self):
        # stdio mode: contextvar unset -> LookupError -> "".
        assert client._bearer_from_request() == ""

    @requires_ctx
    def test_request_object_absent_yields_empty(self):
        # A ctx with no transport request (request is None).
        with http_request(None):
            assert client._bearer_from_request() == ""

    def test_missing_sdk_contextvar_yields_empty(self, monkeypatch):
        # If the SDK internal path moves, _request_ctx is None: degrade to ""
        # (fail safe) rather than crash every tool call.
        monkeypatch.setattr(client, "_request_ctx", None)
        assert client._bearer_from_request() == ""


class TestKeyResolution:
    """_current_api_key(): bearer is authoritative in HTTP mode; env is the
    stdio fallback."""

    @requires_ctx
    def test_bearer_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("SDS_API_KEY", "sds_env")
        with http_request({"authorization": "Bearer sds_user"}):
            assert client._current_api_key() == "sds_user"

    def test_stdio_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("SDS_API_KEY", "sds_env")
        # No request in scope -> stdio -> env key.
        assert client._current_api_key() == "sds_env"

    def test_no_request_no_env_is_empty(self, monkeypatch):
        monkeypatch.delenv("SDS_API_KEY", raising=False)
        assert client._current_api_key() == ""

    @requires_ctx
    def test_http_request_without_bearer_does_not_leak_env_key(self, monkeypatch):
        # Hosted but unauthenticated: must not borrow an ambient SDS_API_KEY;
        # the env fallback applies only in stdio (no request in scope).
        monkeypatch.setenv("SDS_API_KEY", "sds_ambient_service_key")
        with http_request({}):  # request in scope, no Authorization header
            assert client._current_api_key() == ""

    @requires_ctx
    def test_stdio_during_tool_call_uses_env_key(self, monkeypatch):
        # In stdio the SDK sets the contextvar with request=None during a tool
        # call; that must still use the env key, not be treated as an HTTP
        # request. Pins the `ctx.request is not None` discriminator.
        monkeypatch.setenv("SDS_API_KEY", "sds_env")
        with http_request(None):  # ctx set, ctx.request is None
            assert client._current_api_key() == "sds_env"

    def test_missing_sdk_contextvar_falls_back_to_env(self, monkeypatch):
        # If the SDK internal path moves (_request_ctx is None), HTTP mode can't
        # be detected; degrade to the env key rather than locking everyone out.
        monkeypatch.setattr(client, "_request_ctx", None)
        monkeypatch.setenv("SDS_API_KEY", "sds_env")
        assert client._current_api_key() == "sds_env"


class TestHeaders:
    """_headers(): X-API-Key present iff a key resolved (else the REST API 401s)."""

    @requires_ctx
    def test_includes_key_when_present(self):
        with http_request({"authorization": "Bearer sds_user"}):
            assert client._headers() == {"X-API-Key": "sds_user"}

    def test_omits_key_when_none(self, monkeypatch):
        monkeypatch.delenv("SDS_API_KEY", raising=False)
        # No request, no env -> no key -> no header (do not send an empty one).
        assert client._headers() == {}


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"ok": True}


class TestOutgoingRequest:
    """The resolved key actually reaches the outgoing REST call."""

    @requires_ctx
    def test_get_sends_resolved_key(self, monkeypatch):
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured.update(url=url, params=params, headers=headers)
            return _FakeResp()

        monkeypatch.setattr(client.requests, "get", fake_get)
        with http_request({"authorization": "Bearer sds_user"}):
            assert client.get("/resources") == {"ok": True}

        assert captured["url"] == f"{client._BASE}/resources"
        assert captured["headers"]["X-API-Key"] == "sds_user"

    @requires_ctx
    def test_post_sends_resolved_key(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured.update(url=url, json=json, headers=headers)
            return _FakeResp()

        monkeypatch.setattr(client.requests, "post", fake_post)
        with http_request({"authorization": "Bearer sds_user"}):
            assert client.post("/software/match-resources", {"packages": []}) == {"ok": True}

        assert captured["url"] == f"{client._BASE}/software/match-resources"
        assert captured["json"] == {"packages": []}
        assert captured["headers"]["X-API-Key"] == "sds_user"

    def test_get_omits_key_when_unauthenticated(self, monkeypatch):
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured.update(headers=headers)
            return _FakeResp()

        monkeypatch.delenv("SDS_API_KEY", raising=False)
        monkeypatch.setattr(client.requests, "get", fake_get)
        # No request context, no env key -> the call must carry no X-API-Key.
        client.get("/resources")
        assert "X-API-Key" not in captured["headers"]


class TestTransportToggle:
    """server.main() selects the transport from MCP_TRANSPORT, defaulting to stdio."""

    @pytest.mark.parametrize(
        "env_val, expected",
        [
            (None, "stdio"),            # default: laptop / stdio
            ("streamable-http", "streamable-http"),  # hosted
            ("sse", "sse"),             # pass-through (no allow-list enforced)
        ],
    )
    def test_transport_selection(self, env_val, expected, monkeypatch):
        server = pytest.importorskip("sds_mcp.server")
        if env_val is None:
            monkeypatch.delenv("MCP_TRANSPORT", raising=False)
        else:
            monkeypatch.setenv("MCP_TRANSPORT", env_val)

        captured = {}
        monkeypatch.setattr(
            server.mcp, "run", lambda transport=None: captured.update(transport=transport)
        )
        server.main()
        assert captured["transport"] == expected
