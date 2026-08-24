import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_refresh_token
from tests.conftest import auth_headers, make_user


class TestRegister:
    async def test_success_returns_201(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "pass1234"},
        )
        assert resp.status_code == 201

    async def test_success_returns_access_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "pass1234"},
        )
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_first_user_is_admin(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "admin", "email": "admin@example.com", "password": "pass1234"},
        )
        assert resp.json()["user"]["is_admin"] is True

    async def test_second_user_is_not_admin(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"username": "first", "email": "first@example.com", "password": "pass1234"},
        )
        resp = await client.post(
            "/api/auth/register",
            json={"username": "second", "email": "second@example.com", "password": "pass1234"},
        )
        assert resp.json()["user"]["is_admin"] is False

    async def test_sets_refresh_cookie(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "pass1234"},
        )
        assert "refresh_token" in resp.cookies

    async def test_duplicate_username_returns_409(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="taken", email="taken@example.com")
        resp = await client.post(
            "/api/auth/register",
            json={"username": "taken", "email": "other@example.com", "password": "pass1234"},
        )
        assert resp.status_code == 409

    async def test_duplicate_email_returns_409(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="user1", email="shared@example.com")
        resp = await client.post(
            "/api/auth/register",
            json={"username": "user2", "email": "shared@example.com", "password": "pass1234"},
        )
        assert resp.status_code == 409

    async def test_short_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    async def test_short_username_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "ab", "email": "alice@example.com", "password": "pass1234"},
        )
        assert resp.status_code == 422

    async def test_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "not-an-email", "password": "pass1234"},
        )
        assert resp.status_code == 422

    async def test_invalid_username_chars_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "ali ce!", "email": "alice@example.com", "password": "pass1234"},
        )
        assert resp.status_code == 422

    async def test_user_response_contains_expected_fields(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "pass1234"},
        )
        user = resp.json()["user"]
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"
        assert user["is_active"] is True
        assert "id" in user


class TestLogin:
    async def test_login_with_username_returns_200(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="bob", email="bob@example.com", password="pass1234")
        resp = await client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "pass1234"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_with_email_returns_200(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="bob", email="bob@example.com", password="pass1234")
        resp = await client.post(
            "/api/auth/login",
            json={"username": "bob@example.com", "password": "pass1234"},
        )
        assert resp.status_code == 200

    async def test_wrong_password_returns_401(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="bob", email="bob@example.com", password="correct")
        resp = await client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_nonexistent_user_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "pass1234"},
        )
        assert resp.status_code == 401

    async def test_inactive_user_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="inactive", email="i@example.com", password="pass1234", is_active=False)
        resp = await client.post(
            "/api/auth/login",
            json={"username": "inactive", "password": "pass1234"},
        )
        assert resp.status_code == 403

    async def test_login_sets_refresh_cookie(self, client: AsyncClient, db_session: AsyncSession):
        await make_user(db_session, username="bob", email="bob@example.com", password="pass1234")
        resp = await client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "pass1234"},
        )
        assert "refresh_token" in resp.cookies


class TestRefresh:
    async def test_valid_refresh_cookie_returns_new_access_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session, username="carol", email="carol@example.com")
        refresh_token = create_refresh_token(user.id)
        client.cookies.set("refresh_token", refresh_token, path="/api/auth")
        resp = await client.post("/api/auth/refresh")
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_missing_cookie_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/auth/refresh")
        assert resp.status_code == 401

    async def test_invalid_cookie_returns_401(self, client: AsyncClient):
        client.cookies.set("refresh_token", "invalid-token", path="/api/auth")
        resp = await client.post("/api/auth/refresh")
        assert resp.status_code == 401

    async def test_access_token_used_as_refresh_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session, username="carol", email="carol@example.com")
        from app.core.security import create_access_token
        bad_token = create_access_token(user.id)
        client.cookies.set("refresh_token", bad_token, path="/api/auth")
        resp = await client.post("/api/auth/refresh")
        assert resp.status_code == 401

    async def test_refresh_for_inactive_user_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session, username="carol", email="carol@example.com", is_active=False)
        refresh_token = create_refresh_token(user.id)
        client.cookies.set("refresh_token", refresh_token, path="/api/auth")
        resp = await client.post("/api/auth/refresh")
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_returns_204(self, client: AsyncClient):
        resp = await client.post("/api/auth/logout")
        assert resp.status_code == 204


class TestMe:
    async def test_returns_current_user(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session, username="dave", email="dave@example.com")
        resp = await client.get("/api/auth/me", headers=auth_headers(user.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "dave"
        assert data["email"] == "dave@example.com"

    async def test_no_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token"})
        assert resp.status_code == 401

    async def test_inactive_user_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session, username="inactive", email="i@example.com", is_active=False)
        resp = await client.get("/api/auth/me", headers=auth_headers(user.id))
        assert resp.status_code == 403
