"""Authentication tests: registration, login, logout, protected routes."""

import re

from fastapi.testclient import TestClient

from app.core.security import hash_password, verify_password

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def get_csrf(client: TestClient, path: str) -> str:
    """Fetch a form page and extract its CSRF token."""
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_RE.search(response.text)
    assert match, f"No CSRF token found on {path}"
    return match.group(1)


def register(
    client: TestClient,
    username: str = "alice",
    email: str = "alice@example.com",
    password: str = "s3curePassword",
):
    token = get_csrf(client, "/register")
    return client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "password_confirm": password,
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def login(
    client: TestClient,
    identifier: str = "alice",
    password: str = "s3curePassword",
):
    token = get_csrf(client, "/login")
    return client.post(
        "/login",
        data={"identifier": identifier, "password": password, "csrf_token": token},
        follow_redirects=False,
    )


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        hashed = hash_password("hunter2secret")
        assert hashed != "hunter2secret"
        assert hashed.startswith("$2b$")

    def test_verify_roundtrip(self) -> None:
        hashed = hash_password("hunter2secret")
        assert verify_password("hunter2secret", hashed)
        assert not verify_password("wrong-password", hashed)


class TestRegistration:
    def test_register_success_redirects_to_login(self, client: TestClient) -> None:
        response = register(client)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login")

    def test_password_stored_hashed(self, client: TestClient) -> None:
        register(client, password="plaintextNever1")
        from app.core.database import SessionLocal
        from app.models.user import User

        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            assert user.password_hash != "plaintextNever1"
            assert verify_password("plaintextNever1", user.password_hash)
            assert user.role == "student"
            assert user.is_active

    def test_duplicate_username_rejected(self, client: TestClient) -> None:
        register(client)
        response = register(client, email="other@example.com")
        assert response.status_code == 400
        assert "username is already taken" in response.text

    def test_duplicate_email_rejected(self, client: TestClient) -> None:
        register(client)
        response = register(client, username="bob")
        assert response.status_code == 400
        assert "email address is already registered" in response.text

    def test_password_mismatch_rejected(self, client: TestClient) -> None:
        token = get_csrf(client, "/register")
        response = client.post(
            "/register",
            data={
                "username": "carol",
                "email": "carol@example.com",
                "password": "s3curePassword",
                "password_confirm": "different",
                "csrf_token": token,
            },
        )
        assert response.status_code == 400
        assert "Passwords do not match" in response.text

    def test_invalid_email_rejected(self, client: TestClient) -> None:
        response = register(client, email="not-an-email")
        assert response.status_code == 400
        assert "valid email" in response.text

    def test_short_password_rejected(self, client: TestClient) -> None:
        response = register(client, password="short")
        assert response.status_code == 400
        assert "at least 8 characters" in response.text

    def test_overlong_password_rejected(self, client: TestClient) -> None:
        response = register(client, password="x" * 100)
        assert response.status_code == 400
        assert "at most 72 bytes" in response.text

    def test_missing_csrf_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/register",
            data={
                "username": "dave",
                "email": "dave@example.com",
                "password": "s3curePassword",
                "password_confirm": "s3curePassword",
            },
        )
        assert response.status_code == 400


class TestLogin:
    def test_login_with_username(self, client: TestClient) -> None:
        register(client)
        response = login(client, identifier="alice")
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    def test_login_with_email(self, client: TestClient) -> None:
        register(client)
        response = login(client, identifier="alice@example.com")
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"

    def test_wrong_password_generic_error(self, client: TestClient) -> None:
        register(client)
        response = login(client, password="wrong-password")
        assert response.status_code == 401
        assert "Invalid credentials" in response.text
        assert "password is incorrect" not in response.text

    def test_unknown_user_same_generic_error(self, client: TestClient) -> None:
        response = login(client, identifier="ghost")
        assert response.status_code == 401
        assert "Invalid credentials" in response.text

    def test_missing_csrf_rejected(self, client: TestClient) -> None:
        register(client)
        response = client.post(
            "/login",
            data={"identifier": "alice", "password": "s3curePassword"},
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_next_redirect_allows_relative_path(self, client: TestClient) -> None:
        register(client)
        token = get_csrf(client, "/login")
        response = client.post(
            "/login?next=/dashboard",
            data={
                "identifier": "alice",
                "password": "s3curePassword",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert response.headers["location"] == "/dashboard"

    def test_next_redirect_rejects_external_targets(self, client: TestClient) -> None:
        register(client)
        for evil in ("//evil.com", "https://evil.com", "/\\evil.com"):
            token = get_csrf(client, "/login")
            response = client.post(
                "/login",
                params={"next": evil},
                data={
                    "identifier": "alice",
                    "password": "s3curePassword",
                    "csrf_token": token,
                },
                follow_redirects=False,
            )
            assert response.headers["location"] == "/dashboard", evil
            # log back out for the next iteration
            token = get_csrf(client, "/dashboard")
            client.post("/logout", data={"csrf_token": token})

    def test_inactive_user_cannot_login(self, client: TestClient) -> None:
        register(client)
        from app.core.database import SessionLocal
        from app.models.user import User

        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            user.is_active = False
            db.commit()

        response = login(client)
        assert response.status_code == 401
        assert "Invalid credentials" in response.text


class TestLogoutAndProtectedRoutes:
    def test_dashboard_requires_login(self, client: TestClient) -> None:
        response = client.get(
            "/dashboard", headers={"accept": "application/json"}
        )
        assert response.status_code == 401

    def test_dashboard_redirects_browser_to_login(self, client: TestClient) -> None:
        response = client.get(
            "/dashboard", headers={"accept": "text/html"}, follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login")

    def test_dashboard_shows_user_info(self, client: TestClient) -> None:
        register(client)
        login(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "alice" in response.text
        assert "alice@example.com" in response.text
        assert "student" in response.text

    def test_logout_destroys_session(self, client: TestClient) -> None:
        register(client)
        login(client)
        token = get_csrf(client, "/dashboard")
        response = client.post(
            "/logout", data={"csrf_token": token}, follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/"

        after = client.get(
            "/dashboard", headers={"accept": "application/json"}
        )
        assert after.status_code == 401

    def test_login_page_redirects_authenticated_user(self, client: TestClient) -> None:
        register(client)
        login(client)
        response = client.get("/login", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/dashboard"
