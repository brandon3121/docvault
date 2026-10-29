from app.config import get_settings
from tests.conftest import TEST_PASSWORD

COOKIE_NAME = get_settings().session_cookie_name


def login(client, username: str = "alice", password: str = TEST_PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_sets_httponly_cookie(client, create_user):
    create_user()
    response = login(client)
    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{COOKIE_NAME}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


def test_login_wrong_password_returns_401(client, create_user):
    create_user()
    response = login(client, password="wrong")
    assert response.status_code == 401


def test_login_unknown_user_has_same_message(client, create_user):
    create_user()
    wrong_password = login(client, password="wrong")
    unknown_user = login(client, username="nobody")
    assert unknown_user.status_code == 401
    assert unknown_user.json() == wrong_password.json()


def test_me_without_cookie_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_login_cookie_returns_user(client, create_user):
    create_user()
    login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["full_name"] == "Alice Tester"
    assert body["role"] == "admin"
    assert "password_hash" not in body


def test_logout_invalidates_session(client, create_user):
    create_user()
    login(client)
    token = client.cookies.get(COOKIE_NAME)

    assert client.post("/api/auth/logout").status_code == 204

    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/auth/me").status_code == 401


def test_inactive_user_cannot_login(client, create_user):
    create_user(is_active=False)
    assert login(client).status_code == 401


def test_regular_user_gets_403_on_admin_route(client, create_user):
    create_user(username="bob", role="user")
    login(client, username="bob")
    assert client.get("/api/test/admin-only").status_code == 403


def test_admin_can_access_admin_route(client, create_user):
    create_user()
    login(client)
    response = client.get("/api/test/admin-only")
    assert response.status_code == 200
    assert response.json() == {"username": "alice"}
