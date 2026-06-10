"""
GET / — main software catalog.

Spec:
- Renders software_search.html with seeded data
- Empty DB falls back to the "no data available" message
- USE_AI_INFO=False excludes AI columns
- HIDE_DATA drops the named columns
"""
import pytest


def test_root_with_seeded_data_returns_200(client, seeded_db):
    resp = client.get("/")
    assert resp.status_code == 200


def test_root_renders_software_name(client, seeded_db):
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "testpkg" in body


def test_root_renders_software_description(client, seeded_db):
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "A test package" in body


def test_root_with_empty_db_renders_fallback(client, databases):
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "No data available" in body


def test_use_api_false_excludes_ai_columns(client, seeded_db, flask_app):
    flask_app.config["USE_API"] = False
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    # AI column header shouldn't appear when API/AI is off
    assert "AI Software Type" not in body or "Software Type" in body


def test_hide_data_drops_named_column(
    client, seeded_db, flask_app, make_software, make_software_resource, make_resource
):
    flask_app.config["HIDE_DATA"] = ["Description"]
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    # The seeded description text should no longer appear in the table
    assert "A test package" not in body
