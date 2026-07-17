import os
import requests

# `request_ctx` is the per-request ContextVar the MCP SDK sets for HTTP
# transports (the same one FastMCP.get_context() reads). It carries the live
# Starlette request, from which we read the caller's bearer token. Guarded so a
# future SDK layout change degrades to stdio/env behavior instead of crashing.
try:
    from mcp.server.lowlevel.server import request_ctx as _request_ctx
except Exception:  # pragma: no cover - SDK internal path moved
    _request_ctx = None

_BASE = os.environ.get("SDS_API_URL", "http://localhost:5000/api/v1").rstrip("/")


def _current_api_key() -> str:
    """API key to send on the outgoing REST call.

    Hosted (streamable-http): forward the connecting user's bearer token so the
    REST API authenticates *that* user, preserving per-key logging and limits.
    When a request is in scope but carries no usable bearer, return "" — never
    borrow an ambient key — so the REST API answers 401.

    stdio: no request is in scope, so fall back to the single key in the
    environment. No service key and no import from the parent SDS codebase — the
    MCP server stays self-contained.
    """
    bearer = _bearer_from_request()
    if bearer:
        return bearer
    if _in_http_request():
        # Hosted but unauthenticated: do not fall back to SDS_API_KEY.
        return ""
    return os.environ.get("SDS_API_KEY", "")


def _in_http_request() -> bool:
    """True when an incoming HTTP request is in scope (hosted/streamable-http).

    In stdio mode the SDK still sets the request contextvar during a tool call,
    but its `request` is None; only HTTP transports attach a Starlette request.
    That presence is what separates "hosted, unauthenticated" (no env fallback)
    from "stdio" (use the env key).
    """
    if _request_ctx is None:
        return False
    try:
        ctx = _request_ctx.get()
    except LookupError:
        return False
    return getattr(ctx, "request", None) is not None


def _bearer_from_request() -> str:
    """The connecting user's key from the incoming request's
    `Authorization: Bearer <key>` header, or "" when no HTTP request is in scope
    (stdio mode). Returning "" is safe: the caller falls back to the env key, and
    an unauthenticated HTTP call is then rejected by the REST API's existing
    X-API-Key middleware.
    """
    if _request_ctx is None:
        return ""
    try:
        ctx = _request_ctx.get()
    except LookupError:
        # No request in scope: stdio transport, or called outside a request.
        return ""
    # ctx.request is the Starlette Request for HTTP transports, else None.
    headers = getattr(getattr(ctx, "request", None), "headers", None)
    if headers is None:
        return ""
    # Starlette Headers.get is case-insensitive; partition splits on the first
    # space so "Bearer <key>" -> scheme="Bearer", token="<key>".
    scheme, _, token = headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _headers():
    h = {}
    key = _current_api_key()
    if key:
        h["X-API-Key"] = key
    return h


def get(path: str, params: dict = None):
    url = f"{_BASE}/{path.lstrip('/')}"
    r = requests.get(url, params=params, headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def post(path: str, body: dict = None):
    url = f"{_BASE}/{path.lstrip('/')}"
    r = requests.post(url, json=body or {}, headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()
