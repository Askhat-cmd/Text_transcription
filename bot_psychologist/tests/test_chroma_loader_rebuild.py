from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.chroma_loader import ChromaLoader


def test_rebuild_parallel_collection_requires_confirm() -> None:
    loader = ChromaLoader()
    with pytest.raises(ValueError, match="--confirm|confirm"):
        loader.rebuild_parallel_collection(confirm=False)


def test_rebuild_parallel_collection_requires_backup() -> None:
    loader = ChromaLoader()
    missing_tag = f"missing-{uuid4().hex}"
    with pytest.raises(ValueError, match="backup|Backup|Не найден backup"):
        loader.rebuild_parallel_collection(confirm=True, backup_tag=missing_tag)
