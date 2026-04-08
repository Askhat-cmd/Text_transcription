from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.config import config
from bot_agent.conversation_memory import ConversationMemory


def _memory(monkeypatch, tmp_path) -> ConversationMemory:
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
    monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", False)
    monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", True)
    monkeypatch.setattr(config, "SUMMARIZER_MIN_TURNS", 3)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    return ConversationMemory(user_id="summary_v12_user")


def test_summary_min_turns_threshold(monkeypatch, tmp_path) -> None:
    memory = _memory(monkeypatch, tmp_path)
    memory.turns = [
        SimpleNamespace(user_input="u1", bot_response="b1", user_state="window"),
        SimpleNamespace(user_input="u2", bot_response="b2", user_state="window"),
    ]
    monkeypatch.setattr(memory, "_generate_summary", lambda *_args, **_kwargs: "summary text")
    memory._update_summary()
    assert memory.summary is None

    memory.turns.append(SimpleNamespace(user_input="u3", bot_response="b3", user_state="window"))
    memory._update_summary()
    assert memory.summary == "summary text"
    assert memory.summary_updated_at == 3


def test_summary_fallback_from_recent_lines() -> None:
    session_text = "u1\nb1\nu2\nb2\nu3\nb3\n"
    summary = ConversationMemory._build_minimal_summary_fallback(session_text)
    assert "u2" in summary
    assert "b3" in summary
