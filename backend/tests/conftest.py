import os
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# SECRET_KEY must be present before any app module is imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production-ever!")

import app.models  # noqa: F401 – registers all models with Base
from app.api.deps import get_db
from app.core.security import create_access_token, get_password_hash
from app.database import Base
from app.main import app
from app.models.configuration import Configuration, Revision
from app.models.user import User

# ---------------------------------------------------------------------------
# Minimal valid Betaflight config fixture content
# ---------------------------------------------------------------------------

EXAMPLE_CONFIG = """\

# version
# Betaflight / STM32H743 (H743) 4.4.3 Aug  3 2023 / 08:48:14 (deadbeef) MSP API: 1.45
# config rev: abc1234

# start the command batch
batch start

# reset configuration to default settings
defaults nosave

board_name MATEKH743
manufacturer_id MTKS
mcu_id 001234567890

# name: TESTCRAFT

# master
set craft_name = TESTCRAFT
set pilot_name = TESTPILOT

# save configuration
save
"""

EXAMPLE_CONFIG_V2 = EXAMPLE_CONFIG.replace("TESTCRAFT", "MODIFIEDCRAFT")


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_engine(tmp_path):
    """Per-test SQLite engine with schema pre-created."""
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Raw async session for direct DB setup / assertions in tests."""
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(test_engine, tmp_path):
    """AsyncClient wired to the FastAPI app with test DB and temp storage."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Redirect file storage to tmp_path so tests don't touch the real configs dir.
    storage_patcher = patch(
        "app.services.storage._get_configs_base", return_value=configs_dir
    )
    # Skip alembic migration inside the lifespan (tables already exist via test_engine).
    alembic_patcher = patch("app.main._run_alembic_upgrade")
    # Skip configs dir mkdir in lifespan (tmp_path already has it).
    mkdir_patcher = patch("app.main.Path")

    storage_patcher.start()
    alembic_patcher.start()
    mkdir_patcher.start()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        storage_patcher.stop()
        alembic_patcher.stop()
        mkdir_patcher.stop()
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper functions (used directly in tests, not as fixtures)
# ---------------------------------------------------------------------------


async def make_user(
    session: AsyncSession,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "password123",
    is_admin: bool = False,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def auth_headers(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


async def upload_config(
    client: AsyncClient,
    headers: dict,
    content: str = EXAMPLE_CONFIG,
    filename: str = "test.txt",
) -> dict:
    resp = await client.post(
        "/api/configurations",
        headers=headers,
        files={"file": (filename, content.encode(), "text/plain")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
