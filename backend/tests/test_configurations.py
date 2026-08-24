import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import EXAMPLE_CONFIG, auth_headers, make_user, upload_config

# A config that is NOT a valid betaflight file
INVALID_CONFIG = "this is just plain text, not a betaflight config"


class TestListConfigurations:
    async def test_empty_list_for_new_user(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        resp = await client.get("/api/configurations", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_user_configurations(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        await upload_config(client, auth_headers(user.id))
        resp = await client.get("/api/configurations", headers=auth_headers(user.id))
        assert len(resp.json()) == 1

    async def test_does_not_return_other_users_configs(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user1 = await make_user(db_session, username="u1", email="u1@e.com")
        user2 = await make_user(db_session, username="u2", email="u2@e.com")
        await upload_config(client, auth_headers(user1.id))
        resp = await client.get("/api/configurations", headers=auth_headers(user2.id))
        assert resp.json() == []

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/configurations")
        assert resp.status_code == 401

    async def test_response_contains_summary_fields(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        await upload_config(client, auth_headers(user.id))
        resp = await client.get("/api/configurations", headers=auth_headers(user.id))
        item = resp.json()[0]
        assert "id" in item
        assert "name" in item
        assert "board_name" in item
        assert "revision_count" in item
        assert "latest_revision" in item

    async def test_multiple_configs_returned(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        await upload_config(client, auth_headers(user.id))
        await upload_config(client, auth_headers(user.id), filename="second.txt")
        resp = await client.get("/api/configurations", headers=auth_headers(user.id))
        assert len(resp.json()) == 2


class TestCreateConfiguration:
    async def test_success_returns_201(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        resp = await client.post(
            "/api/configurations",
            headers=auth_headers(user.id),
            files={"file": ("test.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        assert resp.status_code == 201

    async def test_extracts_metadata(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        assert data["board_name"] == "MATEKH743"
        assert data["craft_name"] == "TESTCRAFT"
        assert data["pilot_name"] == "TESTPILOT"

    async def test_creates_first_revision(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        assert len(data["revisions"]) == 1
        assert data["revisions"][0]["revision_number"] == 1

    async def test_revision_contains_betaflight_version(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        rev = data["revisions"][0]
        assert rev["betaflight_version"] == "4.4.3"
        assert rev["msp_api_version"] == "1.45"
        assert rev["config_revision"] == "abc1234"

    async def test_name_derived_from_craft_name(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        assert data["name"] == "TESTCRAFT"

    async def test_name_derived_from_filename_when_no_craft_name(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        config_without_craft = (
            "# Betaflight / STM32H743 (H743) 4.4.3 / MSP API: 1.45\n"
            "batch start\n"
            "board_name MYBOARD\n"
        )
        resp = await client.post(
            "/api/configurations",
            headers=auth_headers(user.id),
            files={"file": ("mycraft.txt", config_without_craft.encode(), "text/plain")},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "mycraft"

    async def test_name_fallback_to_unnamed_when_all_missing(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        # No craft_name, no manufacturer_id, filename stripped of extension = "noname"
        config_minimal = (
            "# Betaflight / STM32H743 (H743) 4.4.3 / MSP API: 1.45\n"
            "batch start\n"
            "board_name MINIMALBOARD\n"
        )
        resp = await client.post(
            "/api/configurations",
            headers=auth_headers(user.id),
            files={"file": ("noname.txt", config_minimal.encode(), "text/plain")},
        )
        assert resp.status_code == 201
        # name derived from filename without extension
        assert resp.json()["name"] == "noname"

    async def test_invalid_file_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        resp = await client.post(
            "/api/configurations",
            headers=auth_headers(user.id),
            files={"file": ("bad.txt", INVALID_CONFIG.encode(), "text/plain")},
        )
        assert resp.status_code == 422

    async def test_file_too_large_returns_413(self, client: AsyncClient, db_session: AsyncSession):
        from unittest.mock import patch
        from app.config import get_settings

        user = await make_user(db_session)
        # Temporarily shrink the limit
        with patch.object(get_settings(), "max_upload_size", 10):
            resp = await client.post(
                "/api/configurations",
                headers=auth_headers(user.id),
                files={"file": ("big.txt", (b"x" * 20), "text/plain")},
            )
        assert resp.status_code == 413

    async def test_non_utf8_file_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        resp = await client.post(
            "/api/configurations",
            headers=auth_headers(user.id),
            files={"file": ("binary.txt", b"\xff\xfe\x00\x01", "application/octet-stream")},
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/configurations",
            files={"file": ("t.txt", b"data", "text/plain")},
        )
        assert resp.status_code == 401


class TestGetConfiguration:
    async def test_success_returns_200(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.get(f"/api/configurations/{data['id']}", headers=auth_headers(user.id))
        assert resp.status_code == 200

    async def test_returns_revisions_list(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.get(f"/api/configurations/{data['id']}", headers=auth_headers(user.id))
        assert "revisions" in resp.json()
        assert len(resp.json()["revisions"]) == 1

    async def test_not_found_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        resp = await client.get(
            "/api/configurations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 404

    async def test_other_users_config_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await make_user(db_session, username="owner", email="owner@e.com")
        visitor = await make_user(db_session, username="visitor", email="visitor@e.com")
        data = await upload_config(client, auth_headers(owner.id))
        resp = await client.get(
            f"/api/configurations/{data['id']}", headers=auth_headers(visitor.id)
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.get(f"/api/configurations/{data['id']}")
        assert resp.status_code == 401


class TestDeleteConfiguration:
    async def test_success_returns_204(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.delete(
            f"/api/configurations/{data['id']}", headers=auth_headers(user.id)
        )
        assert resp.status_code == 204

    async def test_deleted_config_no_longer_accessible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        await client.delete(f"/api/configurations/{data['id']}", headers=auth_headers(user.id))
        resp = await client.get(f"/api/configurations/{data['id']}", headers=auth_headers(user.id))
        assert resp.status_code == 404

    async def test_not_found_returns_404(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        resp = await client.delete(
            "/api/configurations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 404

    async def test_other_users_config_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await make_user(db_session, username="owner", email="owner@e.com")
        visitor = await make_user(db_session, username="visitor", email="visitor@e.com")
        data = await upload_config(client, auth_headers(owner.id))
        resp = await client.delete(
            f"/api/configurations/{data['id']}", headers=auth_headers(visitor.id)
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.delete(f"/api/configurations/{data['id']}")
        assert resp.status_code == 401


class TestAddRevision:
    async def test_success_returns_201(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.post(
            f"/api/configurations/{data['id']}/revisions",
            headers=auth_headers(user.id),
            files={"file": ("v2.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        assert resp.status_code == 201

    async def test_revision_number_increments(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.post(
            f"/api/configurations/{data['id']}/revisions",
            headers=auth_headers(user.id),
            files={"file": ("v2.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        assert resp.json()["revision_number"] == 2

    async def test_config_now_has_two_revisions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        await client.post(
            f"/api/configurations/{data['id']}/revisions",
            headers=auth_headers(user.id),
            files={"file": ("v2.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        detail = await client.get(
            f"/api/configurations/{data['id']}", headers=auth_headers(user.id)
        )
        assert len(detail.json()["revisions"]) == 2

    async def test_config_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        resp = await client.post(
            "/api/configurations/00000000-0000-0000-0000-000000000000/revisions",
            headers=auth_headers(user.id),
            files={"file": ("v.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        assert resp.status_code == 404

    async def test_invalid_file_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.post(
            f"/api/configurations/{data['id']}/revisions",
            headers=auth_headers(user.id),
            files={"file": ("bad.txt", INVALID_CONFIG.encode(), "text/plain")},
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.post(
            f"/api/configurations/{data['id']}/revisions",
            files={"file": ("v.txt", EXAMPLE_CONFIG.encode(), "text/plain")},
        )
        assert resp.status_code == 401


class TestDeleteRevision:
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

    async def test_success_returns_204(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        config_id, rev1_id, _ = await self._make_two_revisions(client, user.id)
        resp = await client.delete(
            f"/api/configurations/{config_id}/revisions/{rev1_id}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 204

    async def test_deleted_revision_no_longer_listed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        config_id, rev1_id, rev2_id = await self._make_two_revisions(client, user.id)
        await client.delete(
            f"/api/configurations/{config_id}/revisions/{rev1_id}",
            headers=auth_headers(user.id),
        )
        detail = await client.get(
            f"/api/configurations/{config_id}", headers=auth_headers(user.id)
        )
        revision_ids = [r["id"] for r in detail.json()["revisions"]]
        assert rev1_id not in revision_ids
        assert rev2_id in revision_ids

    async def test_only_revision_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.delete(
            f"/api/configurations/{config_id}/revisions/{rev_id}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 400

    async def test_revision_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        config_id, _, _ = await self._make_two_revisions(client, user.id)
        resp = await client.delete(
            f"/api/configurations/{config_id}/revisions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 404

    async def test_config_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        resp = await client.delete(
            "/api/configurations/00000000-0000-0000-0000-000000000000/revisions/00000000-0000-0000-0000-000000000001",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 404

    async def test_other_users_config_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await make_user(db_session, username="owner", email="o@e.com")
        visitor = await make_user(db_session, username="visitor", email="v@e.com")
        config_id, rev1_id, _ = await self._make_two_revisions(client, owner.id)
        resp = await client.delete(
            f"/api/configurations/{config_id}/revisions/{rev1_id}",
            headers=auth_headers(visitor.id),
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        config_id, rev1_id, _ = await self._make_two_revisions(client, user.id)
        resp = await client.delete(
            f"/api/configurations/{config_id}/revisions/{rev1_id}"
        )
        assert resp.status_code == 401


class TestGetRevisionContent:
    async def test_success_returns_content(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.get(
            f"/api/configurations/{config_id}/revisions/{rev_id}/content",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "content" in body
        assert "TESTCRAFT" in body["content"]

    async def test_revision_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        resp = await client.get(
            f"/api/configurations/{data['id']}/revisions/00000000-0000-0000-0000-000000000000/content",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 404

    async def test_other_users_config_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await make_user(db_session, username="owner", email="o@e.com")
        visitor = await make_user(db_session, username="visitor", email="v@e.com")
        data = await upload_config(client, auth_headers(owner.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.get(
            f"/api/configurations/{config_id}/revisions/{rev_id}/content",
            headers=auth_headers(visitor.id),
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.get(
            f"/api/configurations/{config_id}/revisions/{rev_id}/content"
        )
        assert resp.status_code == 401


class TestDiffRevisions:
    async def _setup_two_revisions(self, client, headers):
        data = await upload_config(client, headers, content=EXAMPLE_CONFIG)
        config_id = data["id"]
        rev1_id = data["revisions"][0]["id"]

        modified = EXAMPLE_CONFIG.replace("TESTCRAFT", "MODIFIEDCRAFT")
        resp2 = await client.post(
            f"/api/configurations/{config_id}/revisions",
            headers=headers,
            files={"file": ("v2.txt", modified.encode(), "text/plain")},
        )
        assert resp2.status_code == 201
        rev2_id = resp2.json()["id"]
        return config_id, rev1_id, rev2_id

    async def test_success_returns_200(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        config_id, rev1_id, rev2_id = await self._setup_two_revisions(client, auth_headers(user.id))
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev1_id}/{rev2_id}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200

    async def test_diff_contains_changes(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        config_id, rev1_id, rev2_id = await self._setup_two_revisions(client, auth_headers(user.id))
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev1_id}/{rev2_id}",
            headers=auth_headers(user.id),
        )
        body = resp.json()
        assert "diff" in body
        assert "TESTCRAFT" in body["diff"] or "MODIFIEDCRAFT" in body["diff"]

    async def test_diff_includes_revision_info(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        config_id, rev1_id, rev2_id = await self._setup_two_revisions(client, auth_headers(user.id))
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev1_id}/{rev2_id}",
            headers=auth_headers(user.id),
        )
        body = resp.json()
        assert "rev1" in body
        assert "rev2" in body

    async def test_same_revision_diff_is_empty(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev_id}/{rev_id}",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["diff"] == ""

    async def test_missing_revision_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev_id}/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 404

    async def test_other_users_config_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner = await make_user(db_session, username="owner", email="o@e.com")
        visitor = await make_user(db_session, username="visitor", email="v@e.com")
        config_id, rev1_id, rev2_id = await self._setup_two_revisions(client, auth_headers(owner.id))
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev1_id}/{rev2_id}",
            headers=auth_headers(visitor.id),
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        user = await make_user(db_session)
        data = await upload_config(client, auth_headers(user.id))
        config_id = data["id"]
        rev_id = data["revisions"][0]["id"]
        resp = await client.get(
            f"/api/configurations/{config_id}/diff/{rev_id}/{rev_id}"
        )
        assert resp.status_code == 401
