import difflib
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user, get_db
from app.config import get_settings
from app.core.betaflight import parse_betaflight_config
from app.models.configuration import Configuration, Revision
from app.models.user import User
from app.services.storage import (
    delete_config_dir,
    delete_revision,
    load_revision,
    save_revision,
)

settings = get_settings()
router = APIRouter(prefix="/configurations", tags=["configurations"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class RevisionInfo(BaseModel):
    id: str
    revision_number: int
    betaflight_version: Optional[str]
    msp_api_version: Optional[str]
    config_revision: Optional[str]
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigurationSummary(BaseModel):
    id: str
    name: str
    board_name: Optional[str]
    manufacturer_id: Optional[str]
    craft_name: Optional[str]
    pilot_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    revision_count: int
    latest_revision: Optional[RevisionInfo]

    model_config = {"from_attributes": True}


class ConfigurationDetail(BaseModel):
    id: str
    name: str
    board_name: Optional[str]
    manufacturer_id: Optional[str]
    craft_name: Optional[str]
    pilot_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    revisions: list[RevisionInfo]

    model_config = {"from_attributes": True}


class DiffResponse(BaseModel):
    diff: str
    rev1: RevisionInfo
    rev2: RevisionInfo


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_next_revision_number(db: AsyncSession, config_id: str) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Revision.revision_number), 0)).where(
            Revision.config_id == config_id
        )
    )
    return result.scalar_one() + 1


async def _get_config_or_404(
    db: AsyncSession, config_id: str, user_id: str
) -> Configuration:
    result = await db.execute(
        select(Configuration)
        .where(Configuration.id == config_id, Configuration.user_id == user_id)
        .options(selectinload(Configuration.revisions))
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return config


async def _process_upload(
    file: UploadFile,
    max_size: int,
) -> tuple[bytes, object]:
    """Read, validate, and parse an uploaded config file. Returns (raw_bytes, parsed_config)."""
    if file.content_type not in (
        "text/plain",
        "application/octet-stream",
        "text/x-conf",
        None,
    ):
        # Allow any text-like content type; validation happens on content
        pass

    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_size} bytes",
        )

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be UTF-8 encoded text",
        )

    parsed = parse_betaflight_config(text)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File does not appear to be a valid Betaflight CLI backup",
        )

    return content, parsed


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ConfigurationSummary])
async def list_configurations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ConfigurationSummary]:
    result = await db.execute(
        select(Configuration)
        .where(Configuration.user_id == current_user.id)
        .options(selectinload(Configuration.revisions))
        .order_by(Configuration.updated_at.desc())
    )
    configs = result.scalars().all()

    summaries = []
    for cfg in configs:
        revisions = sorted(cfg.revisions, key=lambda r: r.revision_number)
        latest = revisions[-1] if revisions else None
        summaries.append(
            ConfigurationSummary(
                id=cfg.id,
                name=cfg.name,
                board_name=cfg.board_name,
                manufacturer_id=cfg.manufacturer_id,
                craft_name=cfg.craft_name,
                pilot_name=cfg.pilot_name,
                created_at=cfg.created_at,
                updated_at=cfg.updated_at,
                revision_count=len(revisions),
                latest_revision=RevisionInfo.model_validate(latest) if latest else None,
            )
        )
    return summaries


@router.post("", response_model=ConfigurationDetail, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConfigurationDetail:
    content, parsed = await _process_upload(file, settings.max_upload_size)

    config_id = uuid.uuid4()
    revision_id = uuid.uuid4()

    # Derive name from craft_name > filename > board_name
    name = parsed.craft_name or (
        file.filename.rsplit(".", 1)[0] if file.filename else None
    ) or parsed.board_name or "Unnamed Config"

    config = Configuration(
        id=str(config_id),
        user_id=current_user.id,
        name=name,
        board_name=parsed.board_name,
        manufacturer_id=parsed.manufacturer_id,
        craft_name=parsed.craft_name,
        pilot_name=parsed.pilot_name,
    )
    db.add(config)
    await db.flush()

    file_path = await save_revision(config_id, revision_id, content)

    revision = Revision(
        id=str(revision_id),
        config_id=str(config_id),
        revision_number=1,
        betaflight_version=parsed.betaflight_version,
        msp_api_version=parsed.msp_api,
        config_revision=parsed.config_revision,
        file_path=file_path,
        file_size=len(content),
    )
    db.add(revision)
    await db.flush()
    await db.refresh(config)
    await db.refresh(revision)

    return ConfigurationDetail(
        id=config.id,
        name=config.name,
        board_name=config.board_name,
        manufacturer_id=config.manufacturer_id,
        craft_name=config.craft_name,
        pilot_name=config.pilot_name,
        created_at=config.created_at,
        updated_at=config.updated_at,
        revisions=[RevisionInfo.model_validate(revision)],
    )


@router.get("/{config_id}", response_model=ConfigurationDetail)
async def get_configuration(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConfigurationDetail:
    config = await _get_config_or_404(db, config_id, current_user.id)
    revisions = sorted(config.revisions, key=lambda r: r.revision_number)
    return ConfigurationDetail(
        id=config.id,
        name=config.name,
        board_name=config.board_name,
        manufacturer_id=config.manufacturer_id,
        craft_name=config.craft_name,
        pilot_name=config.pilot_name,
        created_at=config.created_at,
        updated_at=config.updated_at,
        revisions=[RevisionInfo.model_validate(r) for r in revisions],
    )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    config = await _get_config_or_404(db, config_id, current_user.id)
    await db.delete(config)
    await db.flush()
    await delete_config_dir(uuid.UUID(config_id))


@router.post("/{config_id}/revisions", response_model=RevisionInfo, status_code=status.HTTP_201_CREATED)
async def add_revision(
    config_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RevisionInfo:
    config = await _get_config_or_404(db, config_id, current_user.id)
    content, parsed = await _process_upload(file, settings.max_upload_size)

    latest_revision = config.revisions[-1] if config.revisions else None
    if latest_revision is not None:
        existing_text = await load_revision(latest_revision.file_path)
        if existing_text == content.decode("utf-8"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes since the latest revision",
            )

    revision_id = uuid.uuid4()
    revision_number = await _get_next_revision_number(db, config_id)

    file_path = await save_revision(uuid.UUID(config_id), revision_id, content)

    revision = Revision(
        id=str(revision_id),
        config_id=config_id,
        revision_number=revision_number,
        betaflight_version=parsed.betaflight_version,
        msp_api_version=parsed.msp_api,
        config_revision=parsed.config_revision,
        file_path=file_path,
        file_size=len(content),
    )
    db.add(revision)

    # Update config metadata from new revision
    if parsed.board_name:
        config.board_name = parsed.board_name
    if parsed.manufacturer_id:
        config.manufacturer_id = parsed.manufacturer_id
    if parsed.craft_name:
        config.craft_name = parsed.craft_name
    if parsed.pilot_name:
        config.pilot_name = parsed.pilot_name

    await db.flush()
    await db.refresh(revision)

    return RevisionInfo.model_validate(revision)


@router.delete(
    "/{config_id}/revisions/{revision_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_config_revision(
    config_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    # Verify ownership
    await _get_config_or_404(db, config_id, current_user.id)

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


@router.get("/{config_id}/revisions/{revision_id}/content")
async def get_revision_content(
    config_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    # Verify ownership
    config = await _get_config_or_404(db, config_id, current_user.id)

    result = await db.execute(
        select(Revision).where(
            Revision.id == revision_id, Revision.config_id == config_id
        )
    )
    revision = result.scalar_one_or_none()
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

    text = await load_revision(revision.file_path)
    return {"content": text, "revision": RevisionInfo.model_validate(revision)}


@router.get("/{config_id}/diff/{rev1_id}/{rev2_id}", response_model=DiffResponse)
async def diff_revisions(
    config_id: str,
    rev1_id: str,
    rev2_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiffResponse:
    # Verify ownership
    await _get_config_or_404(db, config_id, current_user.id)

    # Load both revisions
    result = await db.execute(
        select(Revision).where(
            Revision.config_id == config_id,
            Revision.id.in_([rev1_id, rev2_id]),
        )
    )
    revisions = {r.id: r for r in result.scalars().all()}

    if rev1_id not in revisions or rev2_id not in revisions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or both revisions not found"
        )

    rev1 = revisions[rev1_id]
    rev2 = revisions[rev2_id]

    text1 = await load_revision(rev1.file_path)
    text2 = await load_revision(rev2.file_path)

    diff_lines = list(
        difflib.unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=f"revision-{rev1.revision_number}",
            tofile=f"revision-{rev2.revision_number}",
        )
    )
    diff_text = "".join(diff_lines)

    return DiffResponse(
        diff=diff_text,
        rev1=RevisionInfo.model_validate(rev1),
        rev2=RevisionInfo.model_validate(rev2),
    )
