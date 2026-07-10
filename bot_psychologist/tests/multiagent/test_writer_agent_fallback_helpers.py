from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent_fallback_helpers import (
    _build_gentle_close_reply,
    _build_no_practice_fallback_text,
    _detect_language,
    _format_diagnostic_summary,
    _format_hits,
    _normalize_name,
    _static_fallback,
    _strip_optional_followup_invitation,
)
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _thread(*, mode: str = "reflect") -> ThreadState:
    return ThreadState(
        thread_id="th_1",
        user_id="u1",
        core_direction="тревога",
        phase="clarify",
        response_mode=mode,  # type: ignore[arg-type]
        response_goal="поддержка",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        must_avoid=[],
        open_loops=[],
        safety_active=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _contract(
    *,
    message: str = "привет",
    mode: str = "reflect",
    response_planner: dict | None = None,
    dialogue_policy: dict | None = None,
) -> WriterContract:
    bundle = MemoryBundle(
        conversation_context="u: hi\na: hello",
        user_profile=UserProfile(patterns=["avoidance"], values=["honesty"]),
        semantic_hits=[],
        has_relevant_knowledge=False,
        context_turns=2,
    )
    contract = WriterContract(
        user_message=message,
        thread_state=_thread(mode=mode),
        memory_bundle=bundle,
    )
    contract.response_planner = dict(response_planner or {})
    contract.dialogue_policy = dict(dialogue_policy or {})
    return contract


def test_build_gentle_close_reply_returns_expected_text() -> None:
    assert _build_gentle_close_reply() == "Пожалуйста. Береги себя."


def test_build_no_practice_fallback_text_handles_mechanism_request() -> None:
    text = _build_no_practice_fallback_text("Объясни, что со мной происходит")
    assert "защиты" in text


def test_strip_optional_followup_invitation_removes_tail_prompt() -> None:
    text = "Вот ответ. Если хочешь, могу продолжить дальше."
    assert _strip_optional_followup_invitation(text) == "Вот ответ"


def test_detect_language_distinguishes_ru_and_en() -> None:
    assert _detect_language("Привет, как ты?") == "ru"
    assert _detect_language("Hello there") == "en"


def test_format_hits_limits_output_and_handles_empty() -> None:
    assert _format_hits([]) == "нет релевантных знаний"
    rendered = _format_hits(["hit_1", "hit_2", "hit_3"])
    assert "hit_1" in rendered
    assert "hit_2" in rendered
    assert "hit_3" not in rendered


def test_format_diagnostic_summary_handles_missing_and_present_payload() -> None:
    assert _format_diagnostic_summary({}) == "нет"
    rendered = _format_diagnostic_summary(
        {
            "present": True,
            "situation_label": "x",
            "current_need": "y",
            "suggested_writer_move": "z",
            "confidence": 0.7,
        }
    )
    assert "situation_label=x" in rendered
    assert "confidence=0.7" in rendered


def test_static_fallback_respects_gentle_close_and_safe_override() -> None:
    close_contract = _contract(response_planner={"next_move": "close_gently"})
    assert _static_fallback(close_contract) == "Пожалуйста. Береги себя."

    safety_contract = _contract(mode="safe_override")
    assert _static_fallback(safety_contract) == "Я здесь. Ты не один."


def test_normalize_name_handles_bounds_and_trimming() -> None:
    assert _normalize_name("  анна! ") == "Анна"
    assert _normalize_name("a") is None
