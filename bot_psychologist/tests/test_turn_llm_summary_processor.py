from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import process_turn_llm_summaries as processor


class _FakeMemory:
    def __init__(self, payload: dict):
        self._payload = payload

    async def process_pending_turn_summaries(self, *, limit: int, provider: str) -> dict:
        assert limit == 10
        assert provider == "mock"
        return dict(self._payload)


@pytest.mark.asyncio
async def test_processor_mock_creates_ready_stats(monkeypatch, capsys) -> None:
    memories = {
        "u1": _FakeMemory({"pending_count": 1, "ready_count": 2, "failed_count": 0, "processed_count": 2}),
        "u2": _FakeMemory({"pending_count": 0, "ready_count": 1, "failed_count": 0, "processed_count": 1}),
    }

    monkeypatch.setattr(processor, "_discover_user_ids", lambda: ["u1", "u2"])
    monkeypatch.setattr(processor, "get_conversation_memory", lambda user_id: memories[user_id])

    code = await processor._main_async(
        Namespace(limit=10, provider=None, mock=True, confirm=False, user_id=None)
    )
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["status"] == "ok"
    assert payload["processed_users"] == 2
    assert sum(item["ready_count"] for item in payload["items"]) == 3


@pytest.mark.asyncio
async def test_processor_openai_requires_confirm() -> None:
    code = await processor._main_async(
        Namespace(limit=10, provider="openai", mock=False, confirm=False, user_id=None)
    )
    assert code == 2
