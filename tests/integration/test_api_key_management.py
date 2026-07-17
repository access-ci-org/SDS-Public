"""
API-key management is admin-only.

API keys are a single global pool granting programmatic access to the whole
catalog via /api/v1, so minting, revoking, and deleting them is gated to admins
(mirroring the Banners admin surface). Non-admins get 403; anonymous callers are
bounced by login_required. The management UI lives on the /admin/api page;
page access and rendering are covered in test_api_admin_page.py.
"""
import pytest

from app.models.api_key import APIKey


def _make_key(active=True, label="test"):
    raw, key = APIKey.generate(label=label)
    key.is_active = active
    key.save()
    return key


def test_non_admin_cannot_create_key(user_client):
    resp = user_client.post("/admin/api/keys/create", data={"label": "x"})
    assert resp.status_code == 403


def test_admin_can_create_key(admin_client):
    resp = admin_client.post("/admin/api/keys/create", data={"label": "x"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["key"].startswith("sds_")
    assert APIKey.get_or_none(APIKey.id == body["id"]) is not None


def test_non_admin_cannot_revoke_key(user_client):
    key = _make_key()
    resp = user_client.post(f"/admin/api/keys/{key.id}/revoke")
    assert resp.status_code == 403
    assert APIKey.get_by_id(key.id).is_active is True


def test_admin_can_revoke_key(admin_client):
    key = _make_key()
    resp = admin_client.post(f"/admin/api/keys/{key.id}/revoke")
    assert resp.status_code == 200
    assert APIKey.get_by_id(key.id).is_active is False


def test_non_admin_cannot_delete_key(user_client):
    key = _make_key(active=False)
    resp = user_client.post(f"/admin/api/keys/{key.id}/delete")
    assert resp.status_code == 403
    assert APIKey.get_or_none(APIKey.id == key.id) is not None


def test_admin_can_delete_revoked_key(admin_client):
    key = _make_key(active=False)
    resp = admin_client.post(f"/admin/api/keys/{key.id}/delete")
    assert resp.status_code == 200
    assert APIKey.get_or_none(APIKey.id == key.id) is None


def test_revoke_unknown_key_returns_404(admin_client):
    resp = admin_client.post("/admin/api/keys/999999/revoke")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Key not found"}


def test_delete_unknown_key_returns_404(admin_client):
    resp = admin_client.post("/admin/api/keys/999999/delete")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Key not found"}


def test_delete_active_key_is_refused(admin_client):
    key = _make_key(active=True)
    resp = admin_client.post(f"/admin/api/keys/{key.id}/delete")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Revoke the key before deleting it"}
    assert APIKey.get_or_none(APIKey.id == key.id) is not None


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/admin/api/keys/create"),
        ("post", "/admin/api/keys/1/revoke"),
        ("post", "/admin/api/keys/1/delete"),
    ],
)
def test_anonymous_cannot_manage_keys(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code in (301, 302, 401)
