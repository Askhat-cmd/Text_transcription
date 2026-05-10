from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
import sys
import uuid

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.config import config
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.multiagent.turn_summary_service import compute_turn_source_hash
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


@pytest.mark.asyncio
async def test_processor_real_pending_to_ready_with_mock_provider(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
    monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", False)
    monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", True)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "bot_sessions.db")
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_ENABLED", True)
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_PROVIDER", "mock")
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_MODEL", "gpt-4o-mini")

    user_id = f"prd_04563_hf1_smoke_{uuid.uuid4().hex[:8]}"
    user_input = "Мне тревожно перед разговором о проекте."
    bot_response = "Я рядом. Давай выберем один маленький шаг."

    memory = get_conversation_memory(user_id=user_id)
    memory.add_turn(user_input=user_input, bot_response=bot_response, schedule_summary_task=False)
    pending = memory.turns[-1].turn_llm_summary
    assert isinstance(pending, dict)
    assert pending.get("status") == "pending"

    stats = await memory.process_pending_turn_summaries(limit=10, provider="mock")
    assert stats["processed_count"] >= 1
    assert stats["ready_count"] >= 1
    assert stats["pending_count"] == 0

    resolved = memory.turns[-1].turn_llm_summary
    assert isinstance(resolved, dict)
    assert resolved.get("status") == "ready"
    assert resolved.get("source_hash") == compute_turn_source_hash(user_input, bot_response)
