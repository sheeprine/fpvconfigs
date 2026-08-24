import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_admin
from app.core.security import get_password_hash
from app.models.configuration import Configuration, Revision
from app.models.user import User
from app.services.storage import delete_config_dir, delete_revision

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class AdminUserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: bool = False

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 64:
            raise ValueError("Username must be between 3 and 64 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class AdminConfigSummary(BaseModel):
    id: str
    name: str
    board_name: Optional[str]
    craft_name: Optional[str]
    pilot_name: Optional[str]
    user_id: str
    username: str
    revision_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminConfigListResponse(BaseModel):
    items: list[AdminConfigSummary]
    total: int
    page: int
    page_size: int


class RevisionInfo(BaseModel):
    id: str
    revision_number: int
    betaflight_version: Optional[str]
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Users ─────────────────────────────────────────────────────────────────────


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminUserListResponse:
    offset = (page - 1) * page_size

    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminUserResponse:
    existing = await db.execute(
        select(User).where(
            (User.username == body.username) | (User.email == body.email)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        is_admin=body.is_admin,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return AdminUserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.username is not None:
        # Check uniqueness
        dup = await db.execute(
            select(User).where(User.username == body.username, User.id != user_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )
        user.username = body.username

    if body.email is not None:
        dup = await db.execute(
            select(User).where(User.email == body.email, User.id != user_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already taken"
            )
        user.email = body.email

    if body.is_admin is not None:
        user.is_admin = body.is_admin

    if body.is_active is not None:
        user.is_active = body.is_active

    if body.password is not None:
        user.hashed_password = get_password_hash(body.password)

    await db.flush()
    await db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> None:
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    result = await db.execute(
        select(User).where(User.id == user_id).options(
            selectinload(User.configurations).selectinload(Configuration.revisions)
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Collect config IDs before deletion for storage cleanup
    config_ids = [uuid.UUID(cfg.id) for cfg in user.configurations]

    await db.delete(user)
    await db.flush()

    # Clean up storage directories
    for config_id in config_ids:
        await delete_config_dir(config_id)


# ── Configurations ────────────────────────────────────────────────────────────


@router.get("/configurations", response_model=AdminConfigListResponse)
async def list_all_configurations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminConfigListResponse:
    offset = (page - 1) * page_size

    query = select(Configuration, User.username).join(User, Configuration.user_id == User.id)
    count_query = select(func.count()).select_from(Configuration)

    if user_id:
        query = query.where(Configuration.user_id == user_id)
        count_query = count_query.where(Configuration.user_id == user_id)
    if name:
        query = query.where(Configuration.name.ilike(f"%{name}%"))
        count_query = count_query.where(Configuration.name.ilike(f"%{name}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(
        query.order_by(Configuration.updated_at.desc()).offset(offset).limit(page_size)
    )
    rows = result.all()

    items = []
    for cfg, username in rows:
        rev_count_result = await db.execute(
            select(func.count()).select_from(Revision).where(Revision.config_id == cfg.id)
        )
        rev_count = rev_count_result.scalar_one()
        items.append(
            AdminConfigSummary(
                id=cfg.id,
                name=cfg.name,
                board_name=cfg.board_name,
                craft_name=cfg.craft_name,
                pilot_name=cfg.pilot_name,
                user_id=cfg.user_id,
                username=username,
                revision_count=rev_count,
                created_at=cfg.created_at,
                updated_at=cfg.updated_at,
            )
        )

    return AdminConfigListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_configuration(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    result = await db.execute(
        select(Configuration).where(Configuration.id == config_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    await db.delete(config)
    await db.flush()
    await delete_config_dir(uuid.UUID(config_id))


@router.delete(
    "/configurations/{config_id}/revisions/{revision_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_revision(
    config_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    # Check config exists
    cfg_result = await db.execute(
        select(Configuration).where(Configuration.id == config_id)
    )
    if cfg_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    # Count revisions
    count_result = await db.execute(
        select(func.count()).select_from(Revision).where(Revision.config_id == config_id)
    )
    if count_result.scalar_one() <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the only revision of a configuration",
        )

    rev_result = await db.execute(
        select(Revision).where(
            Revision.id == revision_id, Revision.config_id == config_id
        )
    )
    revision = rev_result.scalar_one_or_none()
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

    file_path = revision.file_path
    await db.delete(revision)
    await db.flush()
    await delete_revision(file_path)
