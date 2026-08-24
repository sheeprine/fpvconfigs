import gzip
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

from app.services import storage as storage_module
from app.services.storage import (
    delete_config_dir,
    delete_revision,
    load_revision,
    save_revision,
)


@pytest_asyncio.fixture
async def configs_dir(tmp_path):
    """Provides a temporary configs base directory with the storage module patched."""
    base = tmp_path / "configs"
    base.mkdir()
    with patch.object(storage_module, "_get_configs_base", return_value=base):
        yield base


class TestSaveRevision:
    async def test_creates_file(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        await save_revision(config_id, rev_id, b"content")

        cid = str(config_id)
        expected = configs_dir / cid[:2] / cid[2:4] / cid / f"{rev_id}.txt.gz"
        assert expected.exists()

    async def test_file_is_gzip_compressed(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        original = b"hello betaflight config"
        await save_revision(config_id, rev_id, original)

        cid = str(config_id)
        path = configs_dir / cid[:2] / cid[2:4] / cid / f"{rev_id}.txt.gz"
        raw = path.read_bytes()
        assert gzip.decompress(raw) == original

    async def test_returns_relative_path(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        rel = await save_revision(config_id, rev_id, b"data")

        cid = str(config_id)
        expected_rel = f"{cid[:2]}/{cid[2:4]}/{cid}/{rev_id}.txt.gz"
        assert rel == expected_rel

    async def test_creates_intermediate_directories(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        await save_revision(config_id, rev_id, b"x")

        cid = str(config_id)
        assert (configs_dir / cid[:2] / cid[2:4] / cid).is_dir()


class TestLoadRevision:
    async def test_returns_original_content(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        original = "# Betaflight config\nbatch start\n"
        rel_path = await save_revision(config_id, rev_id, original.encode())

        loaded = await load_revision(rel_path)
        assert loaded == original

    async def test_round_trip_unicode(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        original = "set craft_name = Ångström\n"
        rel_path = await save_revision(config_id, rev_id, original.encode("utf-8"))

        loaded = await load_revision(rel_path)
        assert loaded == original

    async def test_path_traversal_raises(self, configs_dir):
        with pytest.raises(ValueError, match="Path traversal"):
            await load_revision("../../etc/passwd")

    async def test_path_traversal_with_encoded_slash_raises(self, configs_dir):
        with pytest.raises(ValueError, match="Path traversal"):
            await load_revision("../outside/file.txt.gz")


class TestDeleteRevision:
    async def test_removes_file(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        rel_path = await save_revision(config_id, rev_id, b"content")

        cid = str(config_id)
        full_path = configs_dir / cid[:2] / cid[2:4] / cid / f"{rev_id}.txt.gz"
        assert full_path.exists()

        await delete_revision(rel_path)
        assert not full_path.exists()

    async def test_missing_file_is_silent(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        cid = str(config_id)
        rel_path = f"{cid[:2]}/{cid[2:4]}/{cid}/{rev_id}.txt.gz"
        # Should not raise even if file doesn't exist
        await delete_revision(rel_path)

    async def test_path_traversal_raises(self, configs_dir):
        with pytest.raises(ValueError, match="Path traversal"):
            await delete_revision("../../etc/shadow")


class TestDeleteConfigDir:
    async def test_removes_directory(self, configs_dir):
        config_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        await save_revision(config_id, rev_id, b"data")

        cid = str(config_id)
        config_dir = configs_dir / cid[:2] / cid[2:4] / cid
        assert config_dir.exists()

        await delete_config_dir(config_id)
        assert not config_dir.exists()

    async def test_nonexistent_dir_is_silent(self, configs_dir):
        config_id = uuid.uuid4()
        # No files saved – directory never created
        await delete_config_dir(config_id)  # must not raise

    async def test_multiple_revisions_all_deleted(self, configs_dir):
        config_id = uuid.uuid4()
        for _ in range(3):
            await save_revision(config_id, uuid.uuid4(), b"rev")

        await delete_config_dir(config_id)
        cid = str(config_id)
        assert not (configs_dir / cid[:2] / cid[2:4] / cid).exists()
