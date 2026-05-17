from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.context_package import ContextAssemblyPackage
from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterOutput
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.diagnostic_center_shadow import (
    build_diagnostic_center_shadow_divergence_v1,
    build_diagnostic_center_shadow_v1,
)


def _thread() -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="x",
        phase="stabilize",
        relation_to_thread="continue",
        response_mode="safe_override",
        response_goal="ground",
        continuity_score=0.7,
        safety_active=True,
        pattern_core="safety_case",
        created_at=now,
        updated_at=now,
    )


def _card() -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="safety_override",
        user_state_summary="x",
        thread_line_summary="x",
        current_need="ground",
        suggested_writer_move="safe_override",
        confidence=0.8,
        trace=DiagnosticCardTrace(
            version="diagnostic_card_v1",
            builder="test",
            rules_applied=[],
            risk_flags=["safety_active"],
            evidence_sources=["fixture"],
        ),
    )


def test_shadow_trace_contains_required_shape() -> None:
    state = StateSnapshot("hyper", "contact", "defensive", "I-W+", True, 0.9)
    shadow = build_diagnostic_center_shadow_v1(
        user_message="urgent",
        state_snapshot=state,
        thread_state=_thread(),
        context_package=ContextAssemblyPackage(current_user_message="urgent"),
        memory_bundle=MemoryBundle(),
        diagnostic_card=_card(),
        thread_debug={"relation": {"continuity_risk": "none"}},
    )
    assert shadow["status"] == "ok"
    assert isinstance(shadow["output"], dict)
    assert isinstance(shadow["divergence"], dict)
    assert "diagnostic_card_alignment" in shadow["divergence"]
    assert "thread_alignment" in shadow["divergence"]
    assert "kb_boundary" in shadow["divergence"]
    assert shadow["divergence"]["user_path"]["writer_contract_changed"] is False


def test_divergence_marks_safety_match_for_safety_first() -> None:
    state = StateSnapshot("hyper", "contact", "defensive", "I-W+", True, 0.9)
    thread = _thread()
    shadow = build_diagnostic_center_shadow_v1(
        user_message="urgent",
        state_snapshot=state,
        thread_state=thread,
        context_package=ContextAssemblyPackage(current_user_message="urgent"),
        memory_bundle=MemoryBundle(),
        diagnostic_card=_card(),
    )
    output = DiagnosticCenterOutput.from_dict(shadow["output"])
    divergence = build_diagnostic_center_shadow_divergence_v1(
        diagnostic_card=_card(),
        diagnostic_center_output=output,
        thread_state=thread,
        state_snapshot=state,
        kb_sanitization={"raw_kb_text_exposed": False},
    )
    assert divergence["safety_priority_match"] is True
    assert divergence["kb_boundary_ok"] is True
