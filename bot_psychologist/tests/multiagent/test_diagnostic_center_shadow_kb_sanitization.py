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
        thread_id="tkb",
        user_id="u1",
        core_direction="x",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        continuity_score=0.8,
        created_at=now,
        updated_at=now,
    )


def _card() -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="generic_support",
        user_state_summary="x",
        thread_line_summary="x",
        current_need="x",
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


def test_shadow_kb_sanitization_strips_forbidden_fields() -> None:
    state = StateSnapshot("window", "explore", "open", "I+W+", False, 0.8)
    context = ContextAssemblyPackage(
        current_user_message="test",
        knowledge_rag_hits=[
            {
                "chunk_id": "kb_1",
                "score": 0.82,
                "lens_family": "insufficient_self",
                "content": "safe summary",
                "content_full": "super secret raw full text",
                "raw_text": "raw",
                "text": "raw2",
            }
        ],
    )
    shadow = build_diagnostic_center_shadow_v1(
        user_message="test",
        state_snapshot=state,
        thread_state=_thread(),
        context_package=context,
        memory_bundle=MemoryBundle(),
        diagnostic_card=_card(),
    )
    assert shadow["status"] == "ok"
    assert shadow["kb_sanitization"]["forbidden_fields_stripped"] >= 1
    assert shadow["divergence"]["kb_boundary_ok"] is True
    assert shadow["divergence"]["raw_kb_text_exposed"] is False
    serialized = str(shadow)
    assert "super secret raw full text" not in serialized
