from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.diagnostic_card import (
    DiagnosticCard,
    DiagnosticCardTrace,
    DiagnosticEvidenceRef,
)
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",
        pattern_core="stable core",
        active_frame={"current_need": "gentle clarification"},
    )


def _diagnostic_card() -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="semantic_continuation",
        user_state_summary="window/explore: openness=open, ok_position=I+W+",
        thread_line_summary="semantic continuity preserved by active_frame guard",
        current_need="gentle clarification",
        suggested_writer_move="reflect_pattern_once",
        avoid_list=["avoid_restarting_context", "do_not_diagnose"],
        evidence_refs=[
            DiagnosticEvidenceRef(
                source="thread",
                key="relation_reason",
                value_preview="active_frame_semantic_continuity",
            )
        ],
        confidence=0.88,
        risk_flags=["avoid_over_exploration"],
        trace=DiagnosticCardTrace(
            version="diagnostic_card_v1",
            builder="deterministic_rules_v1",
            rules_applied=["semantic_continuation_rule"],
            risk_flags=["avoid_over_exploration"],
            evidence_sources=["thread"],
        ),
    )


def test_writer_contract_to_dict_serializes_diagnostic_card() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy context"),
        diagnostic_card=_diagnostic_card(),
    )
    payload = contract.to_dict()
    assert payload["diagnostic_card"] is not None
    assert payload["diagnostic_card"]["version"] == "diagnostic_card_v1"
    assert payload["diagnostic_card"]["situation_label"] == "semantic_continuation"


def test_writer_contract_prompt_context_exposes_diagnostic_card() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy context"),
        diagnostic_card=_diagnostic_card(),
    )
    ctx = contract.to_prompt_context()
    assert ctx["diagnostic_card"]["version"] == "diagnostic_card_v1"
    assert ctx["diagnostic_card_summary"]["present"] is True
    assert ctx["diagnostic_card_summary"]["suggested_writer_move"] == "reflect_pattern_once"
    assert "avoid_restarting_context" in ctx["diagnostic_card_avoid_list"]
    assert "avoid_over_exploration" in ctx["diagnostic_card_risk_flags"]
    assert ctx["writer_move_instructions"]["version"] == "writer_move_instructions_v1"
    assert ctx["writer_move_instructions"]["move"] == "reflect_pattern_once"
    assert "name_one_repeated_pattern_gently" in ctx["writer_move_must_do"]
    assert "do_not_list_multiple_hypotheses" in ctx["writer_move_must_not_do"]


def test_writer_contract_backward_compat_without_diagnostic_card() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy context"),
    )
    payload = contract.to_dict()
    ctx = contract.to_prompt_context()
    assert payload["diagnostic_card"] is None
    assert ctx["diagnostic_card"] == {}
    assert ctx["diagnostic_card_summary"]["present"] is False
    assert ctx["writer_move_instructions"]["version"] == "writer_move_instructions_v1"
    assert ctx["writer_move_instructions"]["move"] == "validate_briefly"
