"""
API-key management is admin-only.

API keys are a single global pool granting programmatic access to the whole
catalog via /api/v1, so minting, revoking, and deleting them is gated to admins
(mirroring the Banners admin surface). Non-admins get 403; anonymous callers are
bounced by login_required. The settings page still renders for everyone, but the
API Keys tab only appears for admins.
"""
import pytest

from app.models.api_key import APIKey


def _make_key(active=True, label="test"):
    raw, key = APIKey.generate(label=label)
    key.is_active = active
    key.save()
    return key


def test_non_admin_cannot_create_key(user_client):
    resp = user_client.post("/settings/api-keys/create", data={"label": "x"})
    assert resp.status_code == 403


def test_admin_can_create_key(admin_client):
    resp = admin_client.post("/settings/api-keys/create", data={"label": "x"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["key"].startswith("sds_")
    assert APIKey.get_or_none(APIKey.id == body["id"]) is not None


def test_non_admin_cannot_revoke_key(user_client):
    key = _make_key()
    resp = user_client.post(f"/settings/api-keys/{key.id}/revoke")
    assert resp.status_code == 403
    assert APIKey.get_by_id(key.id).is_active is True


def test_admin_can_revoke_key(admin_client):
    key = _make_key()
    resp = admin_client.post(f"/settings/api-keys/{key.id}/revoke")
    assert resp.status_code == 200
    assert APIKey.get_by_id(key.id).is_active is False


def test_non_admin_cannot_delete_key(user_client):
    key = _make_key(active=False)
    resp = user_client.post(f"/settings/api-keys/{key.id}/delete")
    assert resp.status_code == 403
    assert APIKey.get_or_none(APIKey.id == key.id) is not None


def test_admin_can_delete_revoked_key(admin_client):
    key = _make_key(active=False)
    resp = admin_client.post(f"/settings/api-keys/{key.id}/delete")
    assert resp.status_code == 200
    assert APIKey.get_or_none(APIKey.id == key.id) is None


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/settings/api-keys"),
        ("post", "/settings/api-keys/create"),
        ("post", "/settings/api-keys/1/revoke"),
        ("post", "/settings/api-keys/1/delete"),
    ],
)
def test_anonymous_cannot_manage_keys(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code in (301, 302, 401)


def test_api_keys_get_redirects_for_admin(admin_client):
    resp = admin_client.get("/settings/api-keys")
    assert resp.status_code in (301, 302)


def test_api_keys_get_forbidden_for_non_admin(user_client):
    resp = user_client.get("/settings/api-keys")
    assert resp.status_code == 403


def test_settings_renders_without_api_keys_tab_for_non_admin(user_client):
    resp = user_client.get("/settings")
    assert resp.status_code == 200
    assert b"apikeys-tab" not in resp.data


def test_settings_shows_api_keys_tab_for_admin(admin_client):
    resp = admin_client.get("/settings")
    assert resp.status_code == 200
    assert b"apikeys-tab" in resp.data
