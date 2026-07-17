"""
Contract tests for /api/v1/.

These tests verify the interface contract: routes exist with the right methods,
auth is enforced correctly, and every response has the keys the schema promises.
They do not test business logic.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.models.api_key import APIKey
from app.models.software import Software

_EXPECTED_PATHS = {
    "/schema",
    "/resources",
    "/software/search",
    "/software/match-resources",
    "/software/{name}",
    "/software/{name}/containers",
    "/software/{name}/example-use",
    "/resources/{name}/software",
}

_ENDPOINT_REQUIRED_FIELDS = {"path", "method", "auth_required", "description", "response"}


class TestSchemaEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/v1/schema").status_code == 200

    def test_content_type_is_json(self, client):
        assert client.get("/api/v1/schema").content_type.startswith("application/json")

    def test_top_level_keys(self, client):
        data = client.get("/api/v1/schema").get_json()
        assert {"version", "base_url", "auth", "endpoints"}.issubset(data.keys())

    def test_auth_section_shape(self, client):
        data = client.get("/api/v1/schema").get_json()
        assert {"type", "header"}.issubset(data["auth"].keys())

    def test_endpoints_is_nonempty_list(self, client):
        data = client.get("/api/v1/schema").get_json()
        assert isinstance(data["endpoints"], list)
        assert len(data["endpoints"]) > 0

    def test_each_endpoint_has_required_fields(self, client):
        data = client.get("/api/v1/schema").get_json()
        for ep in data["endpoints"]:
            missing = _ENDPOINT_REQUIRED_FIELDS - ep.keys()
            assert not missing, f"{ep.get('path')} is missing fields: {missing}"

    def test_all_expected_paths_present(self, client):
        data = client.get("/api/v1/schema").get_json()
        paths = {ep["path"] for ep in data["endpoints"]}
        assert paths == _EXPECTED_PATHS

    def test_schema_covers_every_served_route(self, client, flask_app):
        # Set equality against the live url_map: a route or method added
        # without a schema entry (or a schema entry gone stale) fails here.
        # Werkzeug auto-adds HEAD/OPTIONS to every rule, so they are not
        # part of the documented contract.
        served = set()
        for rule in flask_app.url_map.iter_rules():
            if not rule.rule.startswith("/api/v1"):
                continue
            path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule[len("/api/v1"):])
            for method in rule.methods - {"HEAD", "OPTIONS"}:
                served.add((path, method))
        data = client.get("/api/v1/schema").get_json()
        assert served == {(ep["path"], ep["method"]) for ep in data["endpoints"]}

    def test_api_doc_covers_every_schema_endpoint(self, client):
        # docs/API.md is the guide rendered on the admin API page; an
        # endpoint added or renamed in the schema must show up there too.
        # The doc writes path params as <name>, the schema as {name}.
        doc = Path("docs/API.md").read_text(encoding="utf-8")
        data = client.get("/api/v1/schema").get_json()
        for ep in data["endpoints"]:
            documented = ep["path"].replace("{", "<").replace("}", ">")
            assert documented in doc, f"{ep['path']} missing from docs/API.md"

    def test_schema_endpoint_marked_no_auth(self, client):
        data = client.get("/api/v1/schema").get_json()
        schema_ep = next(ep for ep in data["endpoints"] if ep["path"] == "/schema")
        assert schema_ep["auth_required"] is False

    def test_all_other_endpoints_marked_auth_required(self, client):
        data = client.get("/api/v1/schema").get_json()
        for ep in data["endpoints"]:
            if ep["path"] != "/schema":
                assert ep["auth_required"] is True, f"{ep['path']} should be auth_required"


class TestAuthEnforcement:
    """All tests here temporarily enable auth to verify enforcement."""

    @pytest.fixture(autouse=True)
    def enable_auth(self, flask_app):
        flask_app.config["REST_API_REQUIRE_AUTH"] = True
        yield
        flask_app.config["REST_API_REQUIRE_AUTH"] = False

    def test_schema_accessible_without_key(self, client):
        assert client.get("/api/v1/schema").status_code == 200

    def test_resources_rejected_without_key(self, client):
        assert client.get("/api/v1/resources").status_code in (401, 403)

    def test_search_rejected_without_key(self, client):
        assert client.get("/api/v1/software/search").status_code in (401, 403)

    def test_match_resources_rejected_without_key(self, client):
        r = client.post("/api/v1/software/match-resources", json={"packages": []})
        assert r.status_code in (401, 403)

    def test_software_detail_rejected_without_key(self, client):
        assert client.get("/api/v1/software/anything").status_code in (401, 403)

    def test_resource_software_rejected_without_key(self, client):
        assert client.get("/api/v1/resources/anything/software").status_code in (401, 403)

    def test_valid_key_grants_access(self, client, api_key):
        r = client.get("/api/v1/resources", headers={"X-API-Key": api_key})
        assert r.status_code == 200

    def test_invalid_key_is_rejected(self, client):
        r = client.get("/api/v1/resources", headers={"X-API-Key": "sds_notavalidkey"})
        assert r.status_code in (401, 403)

    def test_expired_key_is_rejected(self, client):
        # Round-trips the DB: the request path re-fetches the key, so
        # expires_at arrives as the string SQLite hands back.
        raw, key = APIKey.generate(label="expired")
        key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        key.save()
        r = client.get("/api/v1/resources", headers={"X-API-Key": raw})
        assert r.status_code == 403

    def test_unexpired_key_is_accepted(self, client):
        raw, key = APIKey.generate(label="unexpired")
        key.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        key.save()
        r = client.get("/api/v1/resources", headers={"X-API-Key": raw})
        assert r.status_code == 200


class TestResourcesEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/v1/resources").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/v1/resources").get_json(), list)

    def test_item_shape(self, client, seeded_db):
        data = client.get("/api/v1/resources").get_json()
        assert len(data) > 0
        assert all("name" in item for item in data)


class TestSoftwareSearchEndpoint:
    def test_returns_200_without_query(self, client):
        assert client.get("/api/v1/software/search").status_code == 200

    def test_returns_list_without_query(self, client):
        assert isinstance(client.get("/api/v1/software/search").get_json(), list)

    def test_returns_200_with_query(self, client):
        r = client.get("/api/v1/software/search", query_string={"q": "python"})
        assert r.status_code == 200

    def test_result_item_shape(self, client, seeded_db):
        r = client.get("/api/v1/software/search", query_string={"q": "testpkg"})
        data = r.get_json()
        assert len(data) > 0
        required = {
            "name", "description", "research_field", "software_type",
            "tags", "web_page", "documentation", "resources", "has_containers",
        }
        for item in data:
            assert required.issubset(item.keys())

    def test_resources_field_is_list(self, client, seeded_db):
        r = client.get("/api/v1/software/search", query_string={"q": "testpkg"})
        data = r.get_json()
        assert isinstance(data[0]["resources"], list)

    def test_has_containers_is_bool(self, client, seeded_db):
        r = client.get("/api/v1/software/search", query_string={"q": "testpkg"})
        data = r.get_json()
        assert isinstance(data[0]["has_containers"], bool)

    def test_version_entries_carry_load_commands(self, client, seeded_db):
        r = client.get("/api/v1/software/search", query_string={"q": "testpkg"})
        versions = r.get_json()[0]["resources"][0]["versions"]
        assert versions[0]["command"] == "module load testpkg/1.0.0"
        assert versions[0]["load_commands"] == ["module load testpkg/1.0.0"]

    def test_query_results_capped_at_100(self, client):
        for i in range(105):
            Software.create(software_name=f"captest{i:03d}")
        r = client.get("/api/v1/software/search", query_string={"q": "captest"})
        assert len(r.get_json()) == 100


class TestMatchResourcesEndpoint:
    def test_empty_packages_returns_empty_structure(self, client):
        r = client.post("/api/v1/software/match-resources", json={"packages": []})
        assert r.status_code == 200
        assert r.get_json() == {"matched": [], "unmatched": []}

    def test_response_has_matched_and_unmatched(self, client):
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": ["definitely_not_real_xyz_123"]},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert "matched" in data
        assert "unmatched" in data

    def test_unknown_package_lands_in_unmatched(self, client):
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": ["definitely_not_real_xyz_123"]},
        )
        data = r.get_json()
        assert "definitely_not_real_xyz_123" in data["unmatched"]

    def test_short_catalog_names_not_swallowed_by_long_queries(self, client):
        # Substring containment inside a single token is not a match:
        # "r" appears in "gromacs" and "tar" in "notarealpkg", but neither
        # catalog entry is what the caller asked about.
        Software.create(software_name="r")
        Software.create(software_name="tar")
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": ["gromacs", "notarealpkg"]},
        )
        data = r.get_json()
        assert data["matched"] == []
        assert set(data["unmatched"]) == {"gromacs", "notarealpkg"}

    def test_catalog_name_extending_the_query_matches(self, client):
        Software.create(software_name="py2-numpy")
        r = client.post(
            "/api/v1/software/match-resources", json={"packages": ["numpy"]}
        )
        names = [m["software_name"] for m in r.get_json()["matched"][0]["matches"]]
        assert "py2-numpy" in names

    def test_query_extending_a_catalog_name_matches_on_token_boundary(self, client):
        Software.create(software_name="numpy")
        r = client.post(
            "/api/v1/software/match-resources", json={"packages": ["py2-numpy"]}
        )
        names = [m["software_name"] for m in r.get_json()["matched"][0]["matches"]]
        assert "numpy" in names

    def test_single_character_typo_still_matches(self, client):
        Software.create(software_name="gromacs")
        r = client.post(
            "/api/v1/software/match-resources", json={"packages": ["gromcs"]}
        )
        names = [m["software_name"] for m in r.get_json()["matched"][0]["matches"]]
        assert "gromacs" in names

    def test_known_package_lands_in_matched(self, client, seeded_db):
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": ["testpkg"]},
        )
        data = r.get_json()
        assert len(data["matched"]) > 0
        assert data["matched"][0]["package"] == "testpkg"

    def test_matched_item_shape(self, client, seeded_db):
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": ["testpkg"]},
        )
        match = r.get_json()["matched"][0]
        assert {"package", "matches"}.issubset(match.keys())
        m = match["matches"][0]
        assert {"software_name", "score", "resources"}.issubset(m.keys())

    def test_wrong_content_type_returns_415_json(self, client):
        # The blueprint's JSON error handler converts get_json()'s 415 into a
        # JSON body, so the whole API surface answers with {"error": ...}.
        r = client.post(
            "/api/v1/software/match-resources",
            data="packages=testpkg",
            content_type="text/plain",
        )
        assert r.status_code == 415
        assert "error" in r.get_json()

    def test_malformed_json_returns_400_json(self, client):
        r = client.post(
            "/api/v1/software/match-resources",
            data="{not valid json",
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_more_than_500_packages_returns_400_json(self, client):
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": [f"pkg{i}" for i in range(501)]},
        )
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_exactly_500_packages_accepted(self, client):
        r = client.post(
            "/api/v1/software/match-resources",
            json={"packages": [f"pkg{i}" for i in range(500)]},
        )
        assert r.status_code == 200


class TestSoftwareDetailEndpoint:
    def test_404_on_missing(self, client):
        r = client.get("/api/v1/software/nonexistent_xyz_12345")
        assert r.status_code == 404
        assert "error" in r.get_json()

    def test_200_on_existing(self, client, seeded_db):
        r = client.get(f"/api/v1/software/{seeded_db['software'].software_name}")
        assert r.status_code == 200

    def test_response_shape(self, client, seeded_db):
        data = client.get(f"/api/v1/software/{seeded_db['software'].software_name}").get_json()
        required = {
            "name", "description", "research_field", "software_type",
            "tags", "web_page", "documentation", "resources",
            "has_containers", "containers",
        }
        assert required.issubset(data.keys())

    def test_resources_is_list(self, client, seeded_db):
        data = client.get(f"/api/v1/software/{seeded_db['software'].software_name}").get_json()
        assert isinstance(data["resources"], list)

    def test_containers_is_list(self, client, seeded_db):
        data = client.get(f"/api/v1/software/{seeded_db['software'].software_name}").get_json()
        assert isinstance(data["containers"], list)

    def test_has_containers_is_bool(self, client, seeded_db):
        data = client.get(f"/api/v1/software/{seeded_db['software'].software_name}").get_json()
        assert isinstance(data["has_containers"], bool)

    def test_lookup_is_case_insensitive(self, client, seeded_db):
        # software_name uses COLLATE NOCASE, so a differently-cased name matches
        # and the response echoes the stored (canonical) name.
        name = seeded_db["software"].software_name
        r = client.get(f"/api/v1/software/{name.swapcase()}")
        assert r.status_code == 200
        assert r.get_json()["name"] == name

    def test_load_commands_list_visible_chains(
        self, client, seeded_db, make_src_command
    ):
        # a second visible chain and a hidden one: the list is ordered
        # direct-load first and the hidden chain is not shipped
        make_src_command(
            seeded_db["software_resource"],
            "module load gcc/12.3.0 testpkg/1.0.0",
            module_name="testpkg/1.0.0", parent_chain="gcc/12.3.0",
        )
        make_src_command(
            seeded_db["software_resource"],
            "module load intel/.2021.4.0 testpkg/1.0.0",
            module_name="testpkg/1.0.0", parent_chain="intel/.2021.4.0",
            hidden=True,
        )

        data = client.get("/api/v1/software/testpkg").get_json()
        versions = data["resources"][0]["versions"]
        assert versions[0]["load_commands"] == [
            "module load testpkg/1.0.0",
            "module load gcc/12.3.0 testpkg/1.0.0",
        ]

    def test_load_commands_reflect_admin_edits(
        self, client, seeded_db, make_src_command, make_command_edit
    ):
        from app.logic.chain_projection import project_entry

        make_src_command(
            seeded_db["software_resource"],
            "module load gcc/12.3.0 testpkg/1.0.0",
            module_name="testpkg/1.0.0", parent_chain="gcc/12.3.0",
        )
        edit = make_command_edit(
            "testpkg", "test_cluster", "1.0.0",
            target_command="module load testpkg/1.0.0", suppressed=True,
        )
        project_entry(seeded_db["software_resource"], [edit])

        data = client.get("/api/v1/software/testpkg").get_json()
        versions = data["resources"][0]["versions"]
        assert versions[0]["load_commands"] == [
            "module load gcc/12.3.0 testpkg/1.0.0"
        ]


class TestSoftwareContainersEndpoint:
    def test_404_on_missing(self, client):
        r = client.get("/api/v1/software/nonexistent_xyz_12345/containers")
        assert r.status_code == 404

    def test_200_on_existing(self, client, seeded_db):
        r = client.get(f"/api/v1/software/{seeded_db['software'].software_name}/containers")
        assert r.status_code == 200

    def test_returns_list(self, client, seeded_db):
        data = client.get(
            f"/api/v1/software/{seeded_db['software'].software_name}/containers"
        ).get_json()
        assert isinstance(data, list)


class TestSoftwareExampleUseEndpoint:
    def test_404_on_missing(self, client):
        r = client.get("/api/v1/software/nonexistent_xyz_12345/example-use")
        assert r.status_code == 404

    def test_200_on_existing(self, client, seeded_db):
        r = client.get(f"/api/v1/software/{seeded_db['software'].software_name}/example-use")
        assert r.status_code == 200

    def test_response_shape(self, client, seeded_db):
        data = client.get(
            f"/api/v1/software/{seeded_db['software'].software_name}/example-use"
        ).get_json()
        assert "example_use" in data


class TestResourceSoftwareEndpoint:
    def test_404_on_missing(self, client):
        r = client.get("/api/v1/resources/nonexistent_xyz_12345/software")
        assert r.status_code == 404

    def test_200_on_existing(self, client, seeded_db):
        r = client.get(f"/api/v1/resources/{seeded_db['resource'].resource_name}/software")
        assert r.status_code == 200

    def test_returns_list(self, client, seeded_db):
        data = client.get(
            f"/api/v1/resources/{seeded_db['resource'].resource_name}/software"
        ).get_json()
        assert isinstance(data, list)

    def test_item_shape(self, client, seeded_db):
        data = client.get(
            f"/api/v1/resources/{seeded_db['resource'].resource_name}/software"
        ).get_json()
        assert len(data) > 0
        assert {"name", "version", "command"}.issubset(data[0].keys())

    def test_item_carries_load_commands(self, client, seeded_db):
        data = client.get(
            f"/api/v1/resources/{seeded_db['resource'].resource_name}/software"
        ).get_json()
        assert data[0]["load_commands"] == ["module load testpkg/1.0.0"]

    def test_lookup_is_case_sensitive(self, client, seeded_db):
        # resource_name has no collation override, so lookup is case-sensitive —
        # the counterpart to the case-insensitive software-name lookup.
        name = seeded_db["resource"].resource_name
        assert client.get(f"/api/v1/resources/{name.swapcase()}/software").status_code == 404


class TestApiErrorContract:
    """Every /api/v1 error is JSON, including routing errors (404/405) that a
    blueprint-scoped handler can't reach."""

    def test_unknown_api_path_returns_json_404(self, client):
        r = client.get("/api/v1/does-not-exist-xyz")
        assert r.status_code == 404
        assert "error" in r.get_json()

    def test_wrong_method_returns_json_405(self, client):
        r = client.post("/api/v1/resources")  # GET-only route
        assert r.status_code == 405
        assert "error" in r.get_json()

    def test_non_api_error_is_not_json(self, client):
        # The handler is guarded to /api/ paths; the HTML site keeps its default
        # (non-JSON) error responses.
        r = client.get("/definitely-not-a-route-xyz")
        assert r.status_code == 404
        assert r.get_json(silent=True) is None
