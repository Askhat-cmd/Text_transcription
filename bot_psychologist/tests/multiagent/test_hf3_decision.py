from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf3 as hf3


def _base_inputs() -> dict:
    return {
        "source_gate": {"source_gate_passed": True},
        "runtime_reload_proof": {"runtime_reload_gate": "passed", "runtime_reload_proof_passed": True},
        "selected_evidence": {
            "botdb_chunks_returned": 4,
            "rag_raw_hits_count": 4,
            "rag_filtered_hits_count": 2,
            "rag_salvaged_hits_count": 2,
            "knowledge_policy_input_hits_count": 4,
            "knowledge_policy_included_writer_count": 2,
            "context_assembly_knowledge_hits_count": 2,
            "writer_prompt_knowledge_hits_count": 2,
            "web_trace_chunks_in_writer_count": 2,
            "has_relevant_knowledge": True,
            "writer_prompt_contains_knowledge_rag_hits": True,
        },
        "trace_alignment_gate": {"trace_alignment_gate_passed": True},
        "truncation_audit": {
            "writer_kb_truncation_gate": "warning",
            "truncation_detected": True,
            "truncation_blocker": False,
        },
        "creator_live_turn_proof": {"actual_live_turn": True},
        "normal_user_gate": {"normal_user_no_effect_gate_passed": True},
        "trace_gate": {"trace_sanitization_gate_passed": True},
        "provider_gate": {"provider_budget_gate_passed": True},
        "no_mutation_proof": {"no_mutation_proof_passed": True},
        "artifact_encoding_hygiene_passed": True,
    }


def test_hf3_decision_passed_with_truncation_warning() -> None:
    scorecard, decision = hf3.build_hf3_scorecard(**_base_inputs())
    assert scorecard["final_status"] == "passed"
    assert scorecard["decision"] == hf3.DECISION_PASSED_TRUNCATION_WARNING
    assert decision["decision"] == hf3.DECISION_PASSED_TRUNCATION_WARNING


def test_hf3_decision_blocked_runtime_trace() -> None:
    inputs = _base_inputs()
    inputs["trace_alignment_gate"] = {"trace_alignment_gate_passed": False}
    scorecard, decision = hf3.build_hf3_scorecard(**inputs)
    assert scorecard["final_status"] == "blocked"
    assert scorecard["decision"] == hf3.DECISION_BLOCKED_RUNTIME_TRACE
    assert decision["decision"] == hf3.DECISION_BLOCKED_RUNTIME_TRACE
