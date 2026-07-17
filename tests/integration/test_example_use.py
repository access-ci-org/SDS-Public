"""
GET /example_use/<name> — markdown example-usage for the software modal.

A software with no AISoftwareInfo row, or an unknown name, returns 204.
"""
import json


def test_no_ai_info_returns_204(client, make_software, flask_app):
    flask_app.config["HIDE_DATA"] = []
    make_software(name="noai_pkg", description="no ai info")
    assert client.get("/example_use/noai_pkg").status_code == 204


def test_unknown_software_returns_204(client, flask_app):
    flask_app.config["HIDE_DATA"] = []
    assert client.get("/example_use/does_not_exist_pkg").status_code == 204


def test_example_use_returned_when_present(client, make_software, make_ai, flask_app):
    flask_app.config["HIDE_DATA"] = []
    software = make_software(name="hasuse_pkg", description="has use")
    make_ai(software, ai_example_use="# Load it\n\nmodule load hasuse")

    resp = client.get("/example_use/hasuse_pkg")
    assert resp.status_code == 200
    assert "use" in json.loads(resp.get_data(as_text=True))
