"""
/admin/api page access and rendering.

The page is the admin surface for the programmatic API; key management lives
here rather than on /settings, which hosts only display preferences and
banners. Key CRUD behavior is covered in test_api_key_management.py.

The Docs tab renders directly from _SCHEMA (the object /api/v1/schema serves),
so the docs tests here are drift tripwires: they walk the live schema and fail
only when the page fails to show something the schema says. New endpoints
render automatically via the template loop; a new key on an endpoint entry
that the template ignores fails test_docs_render_every_schema_string (unless
its value happens to already appear inside that endpoint's own card).
"""
from jinja2.utils import htmlsafe_json_dumps
from markupsafe import escape

from app.models.api_key import APIKey
from app.models.api_key_log import APIKeyLog
from app.routes.api_routes import _SCHEMA

# Endpoint-entry keys excluded from the verbatim string-leaf walk:
# auth_required renders as a badge, and response renders through |tojson,
# whose escaping differs from autoescape — it is checked as a whole rendered
# block in test_docs_render_response_shapes instead.
_NON_VERBATIM_KEYS = {"auth_required", "response"}


def _string_leaves(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _string_leaves(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _string_leaves(v)


def _make_key(label="test"):
    raw, key = APIKey.generate(label=label)
    key.save()
    return key


def test_anonymous_is_redirected_to_login(client):
    resp = client.get("/admin/api")
    assert resp.status_code in (301, 302, 401)


def test_non_admin_gets_403(user_client):
    assert user_client.get("/admin/api").status_code == 403


def test_admin_gets_page_with_keys_table(admin_client):
    resp = admin_client.get("/admin/api")
    assert resp.status_code == 200
    assert b'id="keys-table"' in resp.data


def test_existing_key_renders_with_prefix_and_label(admin_client):
    key = _make_key(label="ci pipeline")
    resp = admin_client.get("/admin/api")
    assert key.key_prefix.encode() in resp.data
    assert b"ci pipeline" in resp.data


def test_settings_page_does_not_host_key_management(admin_client):
    resp = admin_client.get("/settings")
    assert resp.status_code == 200
    assert b"apikeys-tab" not in resp.data
    assert b'id="keys-table"' not in resp.data


def test_auth_disabled_banner_shown_when_auth_off(admin_client):
    resp = admin_client.get("/admin/api")
    assert b'id="auth-disabled-banner"' in resp.data


def test_auth_disabled_banner_absent_when_auth_on(admin_client, flask_app):
    flask_app.config["REST_API_REQUIRE_AUTH"] = True
    try:
        resp = admin_client.get("/admin/api")
        assert b'id="auth-disabled-banner"' not in resp.data
    finally:
        flask_app.config["REST_API_REQUIRE_AUTH"] = False


def test_navbar_links_api_page_for_admin(admin_client):
    assert b'href="/admin/api"' in admin_client.get("/settings").data


def test_navbar_hides_api_page_for_non_admin(user_client):
    assert b'href="/admin/api"' not in user_client.get("/settings").data


def test_docs_list_every_schema_endpoint(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    for ep in _SCHEMA["endpoints"]:
        assert ep["path"] in page


def _endpoint_cards(page):
    """Slice the page into per-endpoint card chunks, in schema order.

    Anchored on each card's rendered path header so that generic leaves
    ("string", "GET") must appear inside their own endpoint's card rather
    than anywhere on the page.
    """
    anchors = [
        f'<code class="fw-semibold">{_SCHEMA["base_url"]}{ep["path"]}</code>'
        for ep in _SCHEMA["endpoints"]
    ]
    # Each slice starts at the card's opening div, found backwards from the
    # path header, because the method badge precedes the path inside the
    # header — slicing at the path itself would push every badge into the
    # previous endpoint's slice.
    starts = [
        page.rfind('<div class="card shadow-sm mb-3">', 0, page.index(a))
        for a in anchors
    ]
    assert -1 not in starts and starts == sorted(starts)
    ends = starts[1:] + [page.index('id="mcp-tab-pane"')]
    return [page[s:e] for s, e in zip(starts, ends)]


def test_docs_render_every_schema_string(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    for ep, card in zip(_SCHEMA["endpoints"], _endpoint_cards(page)):
        shown = {k: v for k, v in ep.items() if k not in _NON_VERBATIM_KEYS}
        for leaf in _string_leaves(shown):
            assert str(escape(leaf)) in card, (
                f"{ep['path']}: {leaf!r} is in the schema but not on its card"
            )


def test_docs_render_response_shapes(admin_client, flask_app):
    # The template renders responses via |tojson(indent=2); reproducing that
    # exact form here means any response content the pre block drops or
    # mangles fails the comparison.
    page = admin_client.get("/admin/api").data.decode()
    for ep in _SCHEMA["endpoints"]:
        rendered = str(
            htmlsafe_json_dumps(ep["response"], dumps=flask_app.json.dumps, indent=2)
        )
        assert rendered in page, f"{ep['path']}: response shape not rendered"


def test_docs_render_param_and_body_field_names(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    for ep in _SCHEMA["endpoints"]:
        for section in ("params", "body"):
            for field in ep.get(section, {}):
                assert f"<code>{escape(field)}</code>" in page


def test_docs_render_auth_contract(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    assert _SCHEMA["auth"]["header"] in page
    assert str(escape(_SCHEMA["auth"]["note"])) in page
    assert _SCHEMA["base_url"] in page


def test_mcp_tab_derives_endpoint_url_from_request_host(admin_client):
    # No external_url configured, so the URL falls back to the request host.
    resp = admin_client.get("/admin/api")
    assert b'id="mcp-url"' in resp.data
    assert b"http://localhost/mcp" in resp.data


def test_mcp_tab_prefers_configured_external_url(admin_client, flask_app):
    flask_app.config["EXTERNAL_URL"] = "https://sds.example.edu:8080"
    try:
        resp = admin_client.get("/admin/api")
        assert b"https://sds.example.edu:8080/mcp" in resp.data
        assert b"http://localhost/mcp" not in resp.data
    finally:
        flask_app.config["EXTERNAL_URL"] = ""


def test_mcp_tab_shows_bearer_auth_format(admin_client):
    resp = admin_client.get("/admin/api")
    assert b"Authorization: Bearer" in resp.data


def test_mcp_guide_renders_from_bundled_doc(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    pane = page[page.index('id="mcp-tab-pane"'):]
    assert "Claude Desktop" in pane
    assert "Codex CLI" in pane
    assert "http://localhost/mcp" in pane
    assert "<table>" in pane


def test_api_guide_renders_in_docs_tab(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    pane = page[page.index('id="docs-tab-pane"'):page.index('id="mcp-tab-pane"')]
    assert "SDS REST API" in pane
    assert "http://localhost/api/v1" in pane


def _activity_pane(page):
    """The activity pane's slice of the page, so assertions can't be
    satisfied by the keys table (labels) or the docs tab (endpoint paths)."""
    return page[page.index('id="activity-tab-pane"'):page.index('id="docs-tab-pane"')]


def test_activity_lists_requests_newest_first(admin_client):
    key = _make_key(label="ci pipeline")
    APIKeyLog.record(key_prefix=key.key_prefix, endpoint="/api/v1/older-request")
    APIKeyLog.record(key_prefix=key.key_prefix, endpoint="/api/v1/newer-request")
    pane = _activity_pane(admin_client.get("/admin/api").data.decode())
    assert pane.index("/api/v1/newer-request") < pane.index("/api/v1/older-request")


def test_activity_joins_label_while_key_exists(admin_client):
    key = _make_key(label="nightly sync")
    APIKeyLog.record(key_prefix=key.key_prefix, endpoint="/api/v1/resources")
    pane = _activity_pane(admin_client.get("/admin/api").data.decode())
    assert "nightly sync" in pane
    assert "(deleted)" not in pane


def test_activity_marks_deleted_keys(admin_client):
    APIKeyLog.record(key_prefix="sds_gone", endpoint="/api/v1/resources")
    pane = _activity_pane(admin_client.get("/admin/api").data.decode())
    assert "sds_gone" in pane
    assert "(deleted)" in pane


def test_activity_caps_at_latest_100_with_honest_total(admin_client):
    key = _make_key()
    APIKeyLog.record(key_prefix=key.key_prefix, endpoint="/api/v1/oldest-request")
    for _ in range(100):
        APIKeyLog.record(key_prefix=key.key_prefix, endpoint="/api/v1/filler")
    pane = _activity_pane(admin_client.get("/admin/api").data.decode())
    assert "Showing latest 100 of 101 requests" in pane
    assert "/api/v1/oldest-request" not in pane


def test_activity_filters_by_key_prefix(admin_client):
    keep = _make_key(label="keep")
    APIKeyLog.record(key_prefix=keep.key_prefix, endpoint="/api/v1/kept-request")
    APIKeyLog.record(key_prefix="sds_othr", endpoint="/api/v1/other-request")
    page = admin_client.get(f"/admin/api?key={keep.key_prefix}").data.decode()
    pane = _activity_pane(page)
    assert "/api/v1/kept-request" in pane
    assert "/api/v1/other-request" not in pane
    assert "Showing latest 1 of 1 request." in pane
    # A filtered request opens the page on the Activity tab.
    assert 'class="tab-pane show active" id="activity-tab-pane"' in page


def test_page_defaults_to_keys_tab(admin_client):
    page = admin_client.get("/admin/api").data.decode()
    assert 'class="tab-pane show active" id="keys-tab-pane"' in page


def test_keys_table_links_prefix_to_filtered_activity(admin_client):
    key = _make_key()
    page = admin_client.get("/admin/api").data.decode()
    assert f'href="/admin/api?key={key.key_prefix}"' in page


def test_show_all_link_returns_to_unfiltered_activity(admin_client):
    keep = _make_key()
    APIKeyLog.record(key_prefix=keep.key_prefix, endpoint="/api/v1/kept-request")
    filtered = admin_client.get(f"/admin/api?key={keep.key_prefix}").data.decode()
    assert 'href="/admin/api?tab=activity"' in filtered

    page = admin_client.get("/admin/api?tab=activity").data.decode()
    assert 'class="tab-pane show active" id="activity-tab-pane"' in page
    assert "/api/v1/kept-request" in _activity_pane(page)


def test_filtered_empty_state_names_the_filter(admin_client):
    key = _make_key()
    APIKeyLog.record(key_prefix=key.key_prefix, endpoint="/api/v1/resources")
    pane = _activity_pane(admin_client.get("/admin/api?key=sds_none").data.decode())
    assert "No requests logged for this key." in pane
    assert "No API requests logged yet." not in pane
