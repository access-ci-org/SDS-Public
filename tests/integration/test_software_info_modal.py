"""
GET /software_info/<name> — JSON for the software details modal.

Spec:
- Known software returns JSON list-of-records with the right fields
- Unknown software returns 204 (xfail: currently returns 200 with "[]")
- Names containing '/' work via <path:> converter
- HIDE_DATA is honored
"""
import json

import pytest


def test_known_software_returns_200(client, seeded_db):
    resp = client.get("/software_info/testpkg")
    assert resp.status_code == 200


def test_known_software_returns_records_with_software_name(client, seeded_db):
    resp = client.get("/software_info/testpkg")
    data = json.loads(resp.get_data(as_text=True))
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0].get("Software") == "testpkg"


def test_unknown_software_returns_204(client, seeded_db):
    resp = client.get("/software_info/nonexistent_pkg")
    assert resp.status_code == 204


def test_slash_in_name_routes_correctly(
    client, databases, make_resource, make_software, make_software_resource, make_ai
):
    resource = make_resource(name="cluster_x")
    software = make_software(name="ccs/burai", description="Slash-in-name package")
    make_software_resource(software, resource, version="1.0", command="m load burai")
    make_ai(software)

    resp = client.get("/software_info/ccs/burai")
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data[0]["Software"] == "ccs/burai"


def test_hide_data_drops_column_from_modal_json(
    client, seeded_db, flask_app
):
    flask_app.config["HIDE_DATA"] = ["Description"]
    resp = client.get("/software_info/testpkg")
    data = json.loads(resp.get_data(as_text=True))
    assert "Description" not in data[0]
