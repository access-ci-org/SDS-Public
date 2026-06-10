"""
Login / logout / session contracts.

Some tests xfail until the persistent secret key, Users-in-persistent-DB,
and open-redirect/cookie-attrs work lands.
"""
import pytest


def test_login_with_valid_credentials_redirects(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post("/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 302


def test_login_redirects_to_root_by_default(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post("/login", data={"username": "alice", "password": "pw"})
    assert resp.headers["Location"].endswith("/")


def test_login_honors_safe_next_param(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post(
        "/login?next=/settings",
        data={"username": "alice", "password": "pw"},
    )
    assert resp.headers["Location"].endswith("/settings")


def test_login_rejects_cross_host_next(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post(
        "/login?next=https://evil.example.com/path",
        data={"username": "alice", "password": "pw"},
    )
    assert "evil.example.com" not in resp.headers.get("Location", "")


def test_login_unknown_user_flashes_error(client, databases):
    resp = client.post(
        "/login",
        data={"username": "ghost", "password": "x"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_login_wrong_password_flashes_error(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post(
        "/login",
        data={"username": "alice", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Invalid" in resp.data


def test_login_empty_username_flashes_error(client, databases):
    resp = client.post(
        "/login",
        data={"username": "", "password": "pw"},
        follow_redirects=True,
    )
    assert b"required" in resp.data


def test_login_empty_password_flashes_error(client, databases):
    resp = client.post(
        "/login",
        data={"username": "alice", "password": ""},
        follow_redirects=True,
    )
    assert b"required" in resp.data


def test_already_logged_in_redirects_away_from_login(admin_client):
    resp = admin_client.get("/login")
    assert resp.status_code == 302


def test_logout_clears_session(admin_client):
    admin_client.get("/logout")
    # After logout, accessing an admin route should be denied as anonymous
    resp = admin_client.get("/admin/software")
    assert resp.status_code in (302, 401)


def test_session_cookie_has_httponly(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post("/login", data={"username": "alice", "password": "pw"})
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie


def test_session_cookie_has_samesite_lax(client, make_user):
    make_user(username="alice", password="pw")
    resp = client.post("/login", data={"username": "alice", "password": "pw"})
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "SameSite=Lax" in set_cookie


@pytest.mark.xfail(
    reason="secret key is regenerated on import and Users live in transient "
           "DB, so sessions cannot survive a restart"
)
def test_session_survives_simulated_restart(client, make_user, flask_app):
    """After 'restart', a previously-issued session cookie should still
    authenticate the user. Requires a persistent secret key AND Users in
    the persistent DB."""
    make_user(username="alice", password="pw")
    client.post("/login", data={"username": "alice", "password": "pw"})

    # Simulate restart by changing the secret key. Once the secret key is
    # persistent, this branch should not invalidate the session.
    original_key = flask_app.secret_key
    try:
        flask_app.secret_key = "new_random_secret"
        resp = client.get("/settings")
        assert resp.status_code == 200
    finally:
        flask_app.secret_key = original_key
