import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import EXAMPLE_CONFIG, auth_headers, make_user, upload_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def make_admin(session: AsyncSession, username="admin", email="admin@e.com", **kw) -> object:
    return await make_user(session, username=username, email=email, is_admin=True, **kw)


async def make_regular(session: AsyncSession, username="user", email="user@e.com", **kw) -> object:
    return await make_user(session, username=username, email=email, is_admin=False, **kw)


# ---------------------------------------------------------------------------
# Users – GET /admin/users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_admin_can_list_users(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.get("/api/admin/users", headers=auth_headers(admin.id))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 1

    async def test_pagination_fields_present(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.get("/api/admin/users", headers=auth_headers(admin.id))
        body = resp.json()
        assert "page" in body
        assert "page_size" in body

    async def test_page_size_param(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        await make_regular(db_session, username="u1", email="u1@e.com")
        await make_regular(db_session, username="u2", email="u2@e.com")
        resp = await client.get(
            "/api/admin/users?page_size=1", headers=auth_headers(admin.id)
        )
        assert len(resp.json()["items"]) == 1
        assert resp.json()["total"] >= 2

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.get("/api/admin/users", headers=auth_headers(user.id))
        assert resp.status_code == 403

    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/admin/users")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Users – POST /admin/users
# ---------------------------------------------------------------------------


class TestCreateUser:
    async def test_admin_can_create_user(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.post(
            "/api/admin/users",
            headers=auth_headers(admin.id),
            json={"username": "newuser", "email": "new@e.com", "password": "pass1234"},
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    async def test_can_create_admin_user(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.post(
            "/api/admin/users",
            headers=auth_headers(admin.id),
            json={
                "username": "newadmin",
                "email": "newadmin@e.com",
                "password": "pass1234",
                "is_admin": True,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["is_admin"] is True

    async def test_duplicate_username_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        await make_regular(db_session, username="existing", email="existing@e.com")
        resp = await client.post(
            "/api/admin/users",
            headers=auth_headers(admin.id),
            json={"username": "existing", "email": "other@e.com", "password": "pass1234"},
        )
        assert resp.status_code == 409

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        await make_regular(db_session, username="existing", email="taken@e.com")
        resp = await client.post(
            "/api/admin/users",
            headers=auth_headers(admin.id),
            json={"username": "newuser", "email": "taken@e.com", "password": "pass1234"},
        )
        assert resp.status_code == 409

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.post(
            "/api/admin/users",
            headers=auth_headers(user.id),
            json={"username": "x", "email": "x@e.com", "password": "pass1234"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Users – GET /admin/users/{id}
# ---------------------------------------------------------------------------


class TestGetUser:
    async def test_admin_can_get_user(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.get(
            f"/api/admin/users/{user.id}", headers=auth_headers(admin.id)
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == user.id

    async def test_not_found_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.get(
            "/api/admin/users/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 404

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.get(
            f"/api/admin/users/{user.id}", headers=auth_headers(user.id)
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Users – PUT /admin/users/{id}
# ---------------------------------------------------------------------------


class TestUpdateUser:
    async def test_update_username(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"username": "renamed"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "renamed"

    async def test_update_email(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"email": "new@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@example.com"

    async def test_update_password(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session, password="oldpass1")
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"password": "newpass99"},
        )
        assert resp.status_code == 200
        # Verify new password works on login
        login = await client.post(
            "/api/auth/login",
            json={"username": user.username, "password": "newpass99"},
        )
        assert login.status_code == 200

    async def test_update_is_admin(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"is_admin": True},
        )
        assert resp.json()["is_admin"] is True

    async def test_update_is_active(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"is_active": False},
        )
        assert resp.json()["is_active"] is False

    async def test_duplicate_username_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        other = await make_regular(db_session, username="occupied", email="occ@e.com")
        user = await make_regular(db_session, username="target", email="target@e.com")
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"username": "occupied"},
        )
        assert resp.status_code == 409

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        await make_regular(db_session, username="occ", email="taken@e.com")
        user = await make_regular(db_session, username="target", email="target@e.com")
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"email": "taken@e.com"},
        )
        assert resp.status_code == 409

    async def test_not_found_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.put(
            "/api/admin/users/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin.id),
            json={"username": "x"},
        )
        assert resp.status_code == 404

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(user.id),
            json={"username": "hacked"},
        )
        assert resp.status_code == 403

    async def test_short_new_password_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.put(
            f"/api/admin/users/{user.id}",
            headers=auth_headers(admin.id),
            json={"password": "short"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Users – DELETE /admin/users/{id}
# ---------------------------------------------------------------------------


class TestDeleteUser:
    async def test_admin_can_delete_user(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        resp = await client.delete(
            f"/api/admin/users/{user.id}", headers=auth_headers(admin.id)
        )
        assert resp.status_code == 204

    async def test_deleted_user_no_longer_exists(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        await client.delete(f"/api/admin/users/{user.id}", headers=auth_headers(admin.id))
        resp = await client.get(
            f"/api/admin/users/{user.id}", headers=auth_headers(admin.id)
        )
        assert resp.status_code == 404

    async def test_self_deletion_returns_400(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.delete(
            f"/api/admin/users/{admin.id}", headers=auth_headers(admin.id)
        )
        assert resp.status_code == 400

    async def test_not_found_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.delete(
            "/api/admin/users/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 404

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        user2 = await make_regular(db_session, username="u2", email="u2@e.com")
        resp = await client.delete(
            f"/api/admin/users/{user2.id}", headers=auth_headers(user.id)
        )
        assert resp.status_code == 403

    async def test_deleting_user_removes_their_configs(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        await upload_config(client, auth_headers(user.id))
        await client.delete(f"/api/admin/users/{user.id}", headers=auth_headers(admin.id))
        # Admin can no longer find configs for that user
        resp = await client.get(
            "/api/admin/configurations?user_id=" + user.id,
            headers=auth_headers(admin.id),
        )
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Configurations – GET /admin/configurations
# ---------------------------------------------------------------------------


class TestAdminListConfigurations:
    async def test_admin_can_list_all_configs(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        await upload_config(client, auth_headers(user.id))
        resp = await client.get(
            "/api/admin/configurations", headers=auth_headers(admin.id)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert "items" in body

    async def test_filter_by_user_id(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user1 = await make_regular(db_session, username="u1", email="u1@e.com")
        user2 = await make_regular(db_session, username="u2", email="u2@e.com")
        await upload_config(client, auth_headers(user1.id))
        await upload_config(client, auth_headers(user2.id))
        resp = await client.get(
            f"/api/admin/configurations?user_id={user1.id}",
            headers=auth_headers(admin.id),
        )
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["user_id"] == user1.id

    async def test_filter_by_name(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        await upload_config(client, auth_headers(user.id))
        resp = await client.get(
            "/api/admin/configurations?name=TESTCRAFT",
            headers=auth_headers(admin.id),
        )
        assert resp.json()["total"] >= 1

    async def test_filter_by_name_no_match(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        await upload_config(client, auth_headers(user.id))
        resp = await client.get(
            "/api/admin/configurations?name=DOESNOTEXIST",
            headers=auth_headers(admin.id),
        )
        assert resp.json()["total"] == 0

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.get(
            "/api/admin/configurations", headers=auth_headers(user.id)
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Configurations – DELETE /admin/configurations/{id}
# ---------------------------------------------------------------------------


class TestAdminDeleteConfiguration:
    async def test_admin_can_delete_config(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.delete(
            f"/api/admin/configurations/{data['id']}",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 204

    async def test_not_found_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        admin = await make_admin(db_session)
        resp = await client.delete(
            "/api/admin/configurations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 404

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.delete(
            "/api/admin/configurations/anything",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Configurations – DELETE /admin/configurations/{id}/revisions/{rev_id}
# ---------------------------------------------------------------------------


class TestAdminDeleteRevision:
    async def _make_two_revisions(self, client, user_id):
        data = await upload_config(client, auth_headers(user_id))
        config_id = data["id"]
        rev1_id = data["revisions"][0]["id"]
        resp2 = await client.post(
            f"/api/configurations/{config_id}/revisions",
            headers=auth_headers(user_id),
            files={"file": ("v2.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        assert resp2.status_code == 201
        rev2_id = resp2.json()["id"]
        return config_id, rev1_id, rev2_id

    async def test_admin_can_delete_revision(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        config_id, rev1_id, rev2_id = await self._make_two_revisions(client, user.id)
        resp = await client.delete(
            f"/api/admin/configurations/{config_id}/revisions/{rev1_id}",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 204

    async def test_only_revision_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.delete(
            f"/api/admin/configurations/{config_id}/revisions/{rev_id}",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 400

    async def test_revision_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        user = await make_regular(db_session)
        config_id, rev1_id, _ = await self._make_two_revisions(client, user.id)
        resp = await client.delete(
            f"/api/admin/configurations/{config_id}/revisions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 404

    async def test_config_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        admin = await make_admin(db_session)
        resp = await client.delete(
            "/api/admin/configurations/00000000-0000-0000-0000-000000000000/revisions/any",
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 404

    async def test_non_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_regular(db_session)
        resp = await client.delete(
            "/api/admin/configurations/any/revisions/any",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 403
