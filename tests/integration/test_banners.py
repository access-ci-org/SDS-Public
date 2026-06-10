"""
Banner CRUD + display rules.
"""
import datetime
import json

import pytest

from app.logic.banners import banners_for_page, parse_pages, validate_pages_input
from app.models.banner import Banner


def _now():
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")


@pytest.fixture
def make_banner(databases):
    def _make(
        message="hello",
        severity="info",
        pages="software",
        is_active=True,
        dismissible=True,
        created_at=None,
        created_by="alice",
    ):
        return Banner.create(
            message=message,
            severity=severity,
            pages=pages,
            is_active=is_active,
            dismissible=dismissible,
            created_at=created_at or _now(),
            created_by=created_by,
        )
    return _make


# ---- parse_pages / validate_pages_input ----

class TestPageParsing:
    def test_specific_pages_parse(self):
        assert parse_pages("software,container") == {"software", "container"}

    def test_all_expands_to_user_facing(self):
        assert parse_pages("all-user-facing") == {"software", "container", "login"}

    def test_all_mixed_with_specific_returns_empty(self):
        # write paths reject this; read path is defensive
        assert parse_pages("all-user-facing,software") == set()

    def test_unknown_key_returns_empty(self):
        assert parse_pages("admin") == set()

    def test_empty_returns_empty(self):
        assert parse_pages("") == set()

    def test_validate_rejects_mixed(self):
        assert validate_pages_input("all-user-facing,software") is False

    def test_validate_rejects_unknown(self):
        assert validate_pages_input("software,xyz") is False

    def test_validate_accepts_all(self):
        assert validate_pages_input("all-user-facing") is True

    def test_validate_accepts_subset(self):
        assert validate_pages_input("software,container") is True

    def test_validate_rejects_empty(self):
        assert validate_pages_input("") is False


# ---- banners_for_page ----

class TestBannersForPage:
    def test_active_banner_appears_on_targeted_page(self, make_banner):
        make_banner(pages="software", message="hi")
        result = banners_for_page("software")
        assert len(result) == 1
        assert "hi" in result[0]["html"]

    def test_inactive_banner_excluded(self, make_banner):
        make_banner(pages="software", is_active=False)
        assert banners_for_page("software") == []

    def test_banner_not_on_other_page(self, make_banner):
        make_banner(pages="container")
        assert banners_for_page("software") == []

    def test_all_banner_appears_on_each_user_facing_page(self, make_banner):
        make_banner(pages="all-user-facing", message="global")
        for page in ("software", "container", "login"):
            assert any("global" in b["html"] for b in banners_for_page(page))

    def test_no_banners_on_admin_pages(self, make_banner):
        make_banner(pages="all-user-facing", message="global")
        assert banners_for_page(None) == []

    def test_ordering_newest_first(self, make_banner):
        make_banner(pages="software", message="old", created_at="2026-01-01T00:00:00")
        make_banner(pages="software", message="new", created_at="2026-06-01T00:00:00")
        result = banners_for_page("software")
        assert "new" in result[0]["html"]
        assert "old" in result[1]["html"]

    def test_invalid_severity_falls_back_to_info(self, make_banner):
        make_banner(pages="software", severity="bogus")
        result = banners_for_page("software")
        assert result[0]["severity"] == "info"

    def test_markdown_link_renders_anchor(self, make_banner):
        make_banner(pages="software", message="see [docs](https://example.com)")
        html = banners_for_page("software")[0]["html"]
        assert 'href="https://example.com"' in html
        assert "docs</a>" in html

    def test_raw_script_is_escaped(self, make_banner):
        make_banner(pages="software", message="<script>alert(1)</script>")
        html = banners_for_page("software")[0]["html"]
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ---- Admin routes ----

class TestBannerRoutes:
    def test_create_requires_admin(self, user_client):
        resp = user_client.post("/admin/banners", data={
            "message": "x", "severity": "info", "pages": "software",
        })
        assert resp.status_code == 403

    def test_anonymous_cannot_create(self, client):
        resp = client.post("/admin/banners", data={
            "message": "x", "severity": "info", "pages": "software",
        })
        # login_required redirects
        assert resp.status_code in (302, 401)

    def test_create_valid(self, admin_client):
        resp = admin_client.post("/admin/banners", data={
            "message": "hi",
            "severity": "info",
            "pages": "software",
            "is_active": "on",
            "dismissible": "on",
        })
        # Now returns the banners-tab fragment (HTMX swap), not a redirect.
        assert resp.status_code == 200
        assert Banner.select().count() == 1
        b = Banner.select().first()
        assert b.message == "hi"
        assert b.is_active is True
        assert b.dismissible is True

    def test_create_all_pages_displays_on_each_user_page(self, admin_client):
        resp = admin_client.post("/admin/banners", data={
            "message": "global notice text",
            "severity": "warning",
            "pages": "all-user-facing",
            "is_active": "on",
            "dismissible": "on",
        })
        assert resp.status_code == 200
        b = Banner.select().first()
        assert b is not None, "banner was not created"
        assert b.pages == "all-user-facing"
        assert b.is_active is True

        # Log out through the same client to drop both the session cookie and
        # the cached g._login_user that flask_login left behind. Spawning a
        # fresh test_client doesn't help here: the `with ... as c:` pattern
        # in conftest preserves admin's app context for the whole test, so
        # any new client would still see the cached current_user.
        admin_client.get("/logout")

        for url in ("/", "/containers", "/login"):
            page = admin_client.get(url)
            assert page.status_code == 200, (
                f"{url} returned {page.status_code} → {page.headers.get('Location')}"
            )
            assert b"global notice text" in page.data, f"banner missing on {url}"

    def test_create_rejects_invalid_severity(self, admin_client):
        admin_client.post("/admin/banners", data={
            "message": "hi", "severity": "bogus", "pages": "software",
        })
        assert Banner.select().count() == 0

    def test_create_rejects_mixed_pages(self, admin_client):
        admin_client.post("/admin/banners", data={
            "message": "hi", "severity": "info", "pages": ["all-user-facing", "software"],
        })
        assert Banner.select().count() == 0

    def test_create_rejects_empty_message(self, admin_client):
        admin_client.post("/admin/banners", data={
            "message": "", "severity": "info", "pages": "software",
        })
        assert Banner.select().count() == 0

    def test_toggle_flips_is_active(self, admin_client, make_banner):
        b = make_banner(is_active=True)
        admin_client.post(f"/admin/banners/{b.id}/toggle")
        assert Banner.get_by_id(b.id).is_active is False
        admin_client.post(f"/admin/banners/{b.id}/toggle")
        assert Banner.get_by_id(b.id).is_active is True

    def test_delete_removes_row(self, admin_client, make_banner):
        b = make_banner()
        admin_client.post(f"/admin/banners/{b.id}/delete")
        assert Banner.select().count() == 0

    def test_edit_updates_fields(self, admin_client, make_banner):
        b = make_banner(message="old", severity="info")
        admin_client.post(f"/admin/banners/{b.id}/edit", data={
            "message": "new",
            "severity": "warning",
            "pages": "container",
            "is_active": "on",
            "dismissible": "on",
        })
        b2 = Banner.get_by_id(b.id)
        assert b2.message == "new"
        assert b2.severity == "warning"
        assert b2.pages == "container"
        assert b2.updated_at is not None

    def test_toggle_unknown_banner_returns_404(self, admin_client):
        resp = admin_client.post("/admin/banners/999/toggle")
        assert resp.status_code == 404

    def test_create_returns_rendered_fragment_with_new_banner(self, admin_client):
        resp = admin_client.post("/admin/banners", data={
            "message": "fragment check",
            "severity": "info",
            "pages": "software",
            "is_active": "on",
            "dismissible": "on",
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # The returned fragment must include the wrapper used as the HTMX
        # swap target, the success notice, and the new banner row.
        assert 'id="banners-tab-content"' in body
        assert "Banner created." in body
        assert "fragment check" in body
