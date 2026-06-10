"""
Container routes:
- GET /containers respects SHOW_CONTAINER_PAGE config flag
- POST /container_details returns container info JSON for valid pair
- POST /container_details returns 404 for unknown (xfail: currently 500)
- POST /container_details returns 400 for missing fields
"""
import json

import pytest

from app.models.softwareContainer import SoftwareContainer


def test_containers_page_renders_when_enabled(
    client, databases, make_resource, flask_app
):
    flask_app.config["SHOW_CONTAINER_PAGE"] = True
    make_resource(name="gpu_cluster")
    resp = client.get("/containers")
    assert resp.status_code == 200


def test_containers_page_redirects_when_disabled(client, databases, flask_app):
    flask_app.config["SHOW_CONTAINER_PAGE"] = False
    resp = client.get("/containers")
    assert resp.status_code == 302
    assert "/" in resp.headers.get("Location", "")


def test_container_details_returns_info_for_known_pair(
    client, databases, make_resource, make_container, make_software
):
    resource = make_resource(name="lcc")
    container = make_container(
        "demo_container", resource,
        definition_file="lcc/demo.def",
        container_file="lcc/demo.sif",
        notes="demo notes",
    )
    sw = make_software(name="numpy")
    SoftwareContainer.create(
        software_id=sw, container_id=container,
        software_versions="1.24.0", command="",
    )

    resp = client.post(
        "/container_details",
        data=json.dumps({"containerName": "demo_container", "resourceName": "lcc"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data["container_name"] == "demo_container"
    assert data["resource"] == "lcc"


def test_container_details_unknown_returns_404(client, databases, make_resource):
    make_resource(name="lcc")
    resp = client.post(
        "/container_details",
        data=json.dumps({"containerName": "missing", "resourceName": "lcc"}),
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_container_details_missing_fields_returns_400(client, databases):
    resp = client.post(
        "/container_details",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_get_software_container_returns_json_for_known_software(
    client, databases, make_resource, make_software, make_container
):
    resource = make_resource(name="lcc")
    container = make_container("c1", resource, definition_file="lcc/c1.def")
    sw = make_software(name="pytorch")
    SoftwareContainer.create(
        software_id=sw, container_id=container,
        software_versions="2.0.1", command="",
    )

    resp = client.get("/container/pytorch")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    data = json.loads(body)
    assert len(data) == 1
    assert data[0]["container_name"] == "c1"


def test_get_software_container_unknown_does_not_500(client, seeded_db):
    resp = client.get("/container/totally_unknown")
    assert resp.status_code != 500
