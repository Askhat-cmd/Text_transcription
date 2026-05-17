from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.diagnostic_center_divergence import (
    build_shadow_divergence_scorecard_v1,
    classify_divergence_severity_v1,
    evaluate_diagnostic_center_divergence_v1,
)
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1


def _diagnostic_card(move: str = "clarify_one_point") -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="test",
        user_state_summary="test",
        thread_line_summary="test",
        current_need="clarify",
        suggested_writer_move=move,
        confidence=0.8,
        trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
    )


def _state(*, nervous_state: str = "window", safety_flag: bool = False) -> StateSnapshot:
    return StateSnapshot(
        nervous_state=nervous_state,
        intent="explore",
        openness="open",
        ok_position="I+W+",
        safety_flag=safety_flag,
        confidence=0.8,
    )


def _thread(*, relation_to_thread: str = "continue", pattern_core: str = "core") -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="d1",
        phase="clarify",
        relation_to_thread=relation_to_thread,  # type: ignore[arg-type]
        response_mode="reflect",
        response_goal="clarify",
        pattern_core=pattern_core,
        openness="open",
        ok_position="I+W+",
    )


def test_evaluate_divergence_expected_branch_case() -> None:
    output = build_diagnostic_center_output_v1(
        DiagnosticCenterInput(
            user_message="branch",
            nervous_state="window",
            intent="clarify",
            openness="mixed",
            ok_position="I-W+",
            relation_to_thread="branch",
            phase="clarify",
            response_mode="reflect",
            pattern_core="same_core",
        )
    )
    divergence = evaluate_diagnostic_center_divergence_v1(
        diagnostic_card=_diagnostic_card("reflect_pattern_once"),
        diagnostic_center_output=output,
        thread_state=_thread(relation_to_thread="branch", pattern_core="same_core"),
        state_snapshot=_state(),
    )
    assert divergence["safety_priority_match"] is True
    assert divergence["kb_boundary_ok"] is True
    assert divergence["expected_divergence"] is True
    assert classify_divergence_severity_v1(divergence) == "expected_divergence"


def test_classify_divergence_severity_all_levels() -> None:
    assert classify_divergence_severity_v1({"hard_blocker_reasons": ["x"]}) == "hard_blocker"
    assert classify_divergence_severity_v1({"expected_divergence": True}) == "expected_divergence"
    assert classify_divergence_severity_v1({"warnings": ["w1", "w2"], "confidence": 0.9}) == "needs_review"
    assert classify_divergence_severity_v1({"warnings": ["w1"], "confidence": 0.9}) == "soft_warning"
    assert classify_divergence_severity_v1({"warnings": [], "confidence": 0.9}) == "compatible"


def test_build_shadow_divergence_scorecard_counts() -> None:
    scorecard = build_shadow_divergence_scorecard_v1(
        case_results=[
            {"divergence_severity": "hard_blocker"},
            {"divergence_severity": "soft_warning"},
            {"divergence_severity": "expected_divergence"},
            {"divergence_severity": "needs_review"},
            {"divergence_severity": "compatible"},
        ],
        prd="PRD-046.1.2",
    )
    assert scorecard["cases_total"] == 5
    assert scorecard["hard_blocker_count"] == 1
    assert scorecard["soft_warning_count"] == 1
    assert scorecard["expected_divergence_count"] == 1
    assert scorecard["needs_review_count"] == 1
    assert scorecard["compatible_count"] == 1

