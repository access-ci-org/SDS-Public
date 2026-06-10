"""
Downloads (login-required):
- /download_software_csv returns a CSV with seeded data
- /download_software_json returns JSON with seeded data
- HIDE_DATA is reflected in the download
- /download_analytics_json returns a JSON file (or empty struct, not 500, when missing)
"""
import json

import pytest


def test_download_csv_returns_200(user_client, seeded_db):
    resp = user_client.get("/download_software_csv")
    assert resp.status_code == 200


def test_download_csv_contains_seeded_software(user_client, seeded_db):
    resp = user_client.get("/download_software_csv")
    body = resp.get_data(as_text=True)
    assert "testpkg" in body


def test_download_csv_attachment_filename(user_client, seeded_db):
    resp = user_client.get("/download_software_csv")
    disposition = resp.headers.get("Content-Disposition", "")
    assert "software_data.csv" in disposition


def test_download_json_returns_200(user_client, seeded_db):
    resp = user_client.get("/download_software_json")
    assert resp.status_code == 200


def test_download_json_contains_seeded_software(user_client, seeded_db):
    resp = user_client.get("/download_software_json")
    body = resp.get_data(as_text=True)
    # JSON download uses Software name as key
    data = json.loads(body)
    assert "testpkg" in data


def test_download_csv_anonymous_requires_login(client, seeded_db):
    resp = client.get("/download_software_csv")
    # Either redirects to login (302) or returns 401
    assert resp.status_code in (302, 401)


def test_download_csv_hides_columns_per_hide_data(
    user_client, seeded_db, flask_app
):
    flask_app.config["HIDE_DATA"] = ["Description"]
    resp = user_client.get("/download_software_csv")
    body = resp.get_data(as_text=True)
    assert "A test package" not in body


def test_download_analytics_json_returns_200_when_missing(user_client, databases):
    resp = user_client.get("/download_analytics_json")
    assert resp.status_code == 200
