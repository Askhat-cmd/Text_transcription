from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.context_package import ContextAssemblyPackage, TurnContextItem
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.diagnostic_center import build_diagnostic_card_v1


def _snapshot(
    *,
    nervous_state: str = "window",
    intent: str = "explore",
    safety_flag: bool = False,
) -> StateSnapshot:
    return StateSnapshot(
        nervous_state=nervous_state,
        intent=intent,
        openness="open",
        ok_position="I+W+",
        safety_flag=safety_flag,
        confidence=0.82,
    )


def _thread(
    *,
    relation_to_thread: str = "continue",
    response_mode: str = "reflect",
    continuity_score: float = 0.7,
) -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="support continuity",
        phase="clarify",
        relation_to_thread=relation_to_thread,  # type: ignore[arg-type]
        response_mode=response_mode,  # type: ignore[arg-type]
        continuity_score=continuity_score,
        pattern_core="stable continuity core",
        active_frame={"current_need": "short support without pressure"},
        must_avoid=["open_new_topics_without_user_request"],
    )


def _context() -> ContextAssemblyPackage:
    return ContextAssemblyPackage(
        current_user_message="текущее сообщение",
        recent_turns_full=[
            TurnContextItem(
                turn_id="turn_1_user",
                role="user",
                content="мне тяжело снова начать",
                raw_chars=22,
                source="recent_full",
            )
        ],
        recent_turns_summarized=[],
        pattern_core="stable continuity core",
        active_frame={"current_need": "short support without pressure"},
    )


def test_diagnostic_card_low_resource_contact() -> None:
    card = build_diagnostic_card_v1(
        state_snapshot=_snapshot(nervous_state="hypo", intent="contact"),
        thread_state=_thread(response_mode="validate"),
        context_package=_context(),
        thread_diagnostics={"relation": {"relation_reason": "low_resource_continuation_marker"}},
    )
    assert card.situation_label == "low_resource_contact"
    assert card.suggested_writer_move in {"validate_briefly", "regulate_first"}
    assert "low_resource" in card.risk_flags
    assert "avoid_deep_analysis" in card.avoid_list


def test_diagnostic_card_solution_practice() -> None:
    card = build_diagnostic_card_v1(
        state_snapshot=_snapshot(intent="solution"),
        thread_state=_thread(response_mode="practice"),
        context_package=_context(),
        thread_diagnostics={"relation": {"relation_reason": "continuity_continue"}},
    )
    assert card.situation_label == "concrete_next_step"
    assert card.suggested_writer_move == "offer_one_micro_step"
    assert "avoid_abstract_theory" in card.avoid_list


def test_diagnostic_card_semantic_continuation() -> None:
    card = build_diagnostic_card_v1(
        state_snapshot=_snapshot(intent="explore"),
        thread_state=_thread(relation_to_thread="continue", response_mode="explore"),
        context_package=_context(),
        thread_diagnostics={"relation": {"relation_reason": "active_frame_semantic_continuity"}},
    )
    assert card.situation_label == "semantic_continuation"
    assert card.suggested_writer_move == "reflect_pattern_once"
    assert "avoid_restarting_context" in card.avoid_list
    assert any(
        ref.source == "thread"
        and ref.key == "relation_reason"
        and ref.value_preview == "active_frame_semantic_continuity"
        for ref in card.evidence_refs
    )


def test_diagnostic_card_safety_override() -> None:
    safe_thread = _thread(response_mode="safe_override")
    safe_thread.safety_active = True
    card = build_diagnostic_card_v1(
        state_snapshot=_snapshot(intent="contact", safety_flag=True),
        thread_state=safe_thread,
        context_package=_context(),
        thread_diagnostics={"relation": {"relation_reason": "safety_patch"}},
    )
    assert card.situation_label == "safety_override"
    assert card.suggested_writer_move == "safe_override"
    assert "safety_active" in card.risk_flags
    assert "prioritize_safety_protocol" in card.avoid_list


def test_diagnostic_card_serialization_roundtrip() -> None:
    card = build_diagnostic_card_v1(
        state_snapshot=_snapshot(),
        thread_state=_thread(),
        context_package=_context(),
        thread_diagnostics={"relation": {"relation_reason": "continuity_continue"}},
    )
    restored = card.from_dict(card.to_dict())
    assert restored.to_dict() == card.to_dict()
