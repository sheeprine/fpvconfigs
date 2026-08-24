import gzip
import os
import shutil
from pathlib import Path
from uuid import UUID

import aiofiles
import aiofiles.os

from app.config import get_settings

settings = get_settings()


def _get_configs_base() -> Path:
    base = Path(settings.configs_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _revision_path(config_id: UUID, revision_id: UUID) -> Path:
    cid = str(config_id)
    base = _get_configs_base()
    return base / cid[:2] / cid[2:4] / cid / f"{revision_id}.txt.gz"


def _config_dir(config_id: UUID) -> Path:
    cid = str(config_id)
    base = _get_configs_base()
    return base / cid[:2] / cid[2:4] / cid


async def save_revision(config_id: UUID, revision_id: UUID, content: bytes) -> str:
    """
    Gzip-compress content and save to the storage tree.
    Returns the relative path from the configs base directory.
    """
    path = _revision_path(config_id, revision_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    compressed = gzip.compress(content, compresslevel=9)

    async with aiofiles.open(str(path), "wb") as f:
        await f.write(compressed)

    # Return path relative to configs base
    base = _get_configs_base()
    return str(path.relative_to(base))


async def load_revision(file_path: str) -> str:
    """
    Load and decompress a revision file. file_path is relative to configs base.
    Returns the decompressed text content.
    """
    base = _get_configs_base()
    full_path = base / file_path

    # Safety: resolve and ensure it stays within the base directory
    resolved = full_path.resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError("Path traversal attempt detected")

    async with aiofiles.open(str(resolved), "rb") as f:
        compressed = await f.read()

    return gzip.decompress(compressed).decode("utf-8", errors="replace")


async def delete_revision(file_path: str) -> None:
    """Delete a single revision file. file_path is relative to configs base."""
    base = _get_configs_base()
    full_path = base / file_path

    resolved = full_path.resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError("Path traversal attempt detected")

    try:
        await aiofiles.os.remove(str(resolved))
    except FileNotFoundError:
        pass


async def delete_config_dir(config_id: UUID) -> None:
    """Delete the entire directory for a configuration (all revisions)."""
    config_dir = _config_dir(config_id)
    if config_dir.exists():
        shutil.rmtree(str(config_dir), ignore_errors=True)
