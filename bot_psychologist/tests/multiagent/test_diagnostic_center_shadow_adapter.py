from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.context_package import ContextAssemblyPackage
from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.diagnostic_center_shadow import build_diagnostic_center_shadow_v1


def _thread() -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="shadow_t1",
        user_id="u1",
        core_direction="test",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        response_goal="clarify",
        pattern_core="external_confirmation_seek",
        continuity_score=0.8,
        created_at=now,
        updated_at=now,
    )


def _diagnostic_card() -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="generic_support",
        user_state_summary="state",
        thread_line_summary="thread",
        current_need="clarify",
        suggested_writer_move="clarify_one_point",
        confidence=0.7,
        trace=DiagnosticCardTrace(
            version="diagnostic_card_v1",
            builder="test",
            rules_applied=[],
            risk_flags=[],
            evidence_sources=["fixture"],
        ),
    )


def test_shadow_adapter_builds_trace_only_payload() -> None:
    state = StateSnapshot("window", "solution", "defensive", "I-W+", False, 0.82)
    thread = _thread()
    context = ContextAssemblyPackage(
        current_user_message="help",
        knowledge_rag_hits=[{"chunk_id": "k1", "score": 0.9, "lens_family": "insufficient_self"}],
    )
    memory = MemoryBundle()
    shadow = build_diagnostic_center_shadow_v1(
        user_message="help",
        state_snapshot=state,
        thread_state=thread,
        context_package=context,
        memory_bundle=memory,
        diagnostic_card=_diagnostic_card(),
        thread_debug={"action": {"thread_action": "continue"}},
    )
    assert shadow["enabled"] is True
    assert shadow["status"] == "ok"
    assert shadow["runtime_mode"] == "shadow_only"
    assert shadow["user_path_effect"] == "none"
    assert shadow["output"]["intent"] == "practical_step"
    assert shadow["output"]["diagnostic_center_runtime_enabled"] is False
    assert shadow["output"]["user_facing_text_generated"] is False


def test_shadow_adapter_disabled_mode() -> None:
    state = StateSnapshot("window", "explore", "open", "I+W+", False, 0.7)
    shadow = build_diagnostic_center_shadow_v1(
        user_message="x",
        state_snapshot=state,
        thread_state=_thread(),
        context_package=ContextAssemblyPackage(current_user_message="x"),
        memory_bundle=MemoryBundle(),
        diagnostic_card=_diagnostic_card(),
        enabled=False,
    )
    assert shadow == {
        "enabled": False,
        "status": "disabled",
        "runtime_mode": "shadow_only",
        "user_path_effect": "none",
    }
