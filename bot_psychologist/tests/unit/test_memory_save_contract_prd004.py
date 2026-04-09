from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.config import config
from bot_agent.conversation_memory import ConversationMemory
from bot_agent.working_state import WorkingState


def _memory(monkeypatch, tmp_path) -> ConversationMemory:
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
    monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", False)
    monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", True)
    monkeypatch.setattr(config, "SUMMARY_UPDATE_INTERVAL", 1)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    return ConversationMemory(user_id="save_contract_user")


def test_set_working_state_does_not_call_save_to_disk(monkeypatch, tmp_path) -> None:
    memory = _memory(monkeypatch, tmp_path)
    save_calls = []
    memory.save_to_disk = lambda **kwargs: save_calls.append(kwargs)  # type: ignore[assignment]

    memory.set_working_state(
        WorkingState(
            dominant_state="curious",
            emotion="neutral",
            phase="осмысление",
            direction="диагностика",
        )
    )

    assert save_calls == []


def test_add_turn_persists_once_with_addturn_reason(monkeypatch, tmp_path) -> None:
    memory = _memory(monkeypatch, tmp_path)
    save_calls = []
    memory.save_to_disk = lambda **kwargs: save_calls.append(kwargs)  # type: ignore[assignment]

    memory.add_turn(
        user_input="q",
        bot_response="a",
        user_state="curious",
        blocks_used=0,
        concepts=[],
        schedule_summary_task=False,
    )

    assert save_calls == [{"reason": "addturn"}]
