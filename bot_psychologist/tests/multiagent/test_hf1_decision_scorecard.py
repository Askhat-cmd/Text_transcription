from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def _base_inputs() -> dict:
    return {
        "source_gate": {"source_gate_passed": True},
        "service_gate": {"service_readiness_gate_passed": True, "botdb_ready": True},
        "creator_live_proof": {"actual_live_turn": True},
        "botdb_probe": {"botdb_http_status": 200, "botdb_chunks_returned": 4},
        "rag_proof": {
            "delivery_status": "passed",
            "retriever_raw_hits_count": 4,
            "memory_semantic_hits_count": 4,
            "knowledge_policy_included_writer_count": 2,
            "knowledge_policy_included_diagnostic_count": 0,
            "context_assembly_knowledge_hits_count": 2,
            "writer_prompt_knowledge_hits_count": 2,
        },
        "ui_gate": {"ui_trace_alignment_gate_passed": True},
        "normal_user_gate": {"normal_user_no_effect_gate_passed": True},
        "trace_gate": {"trace_sanitization_gate_passed": True},
        "provider_gate": {"provider_budget_gate_passed": True},
        "no_mutation_proof": {"no_mutation_proof_passed": True},
        "artifact_encoding_hygiene_passed": True,
    }


def test_hf1_decision_scorecard_passed_ready() -> None:
    scorecard, decision = hf1.build_hf1_scorecard(**_base_inputs())
    assert scorecard["final_status"] == "passed"
    assert scorecard["decision"] == hf1.DECISION_PASSED_RAG_READY
    assert decision["decision"] == hf1.DECISION_PASSED_RAG_READY


def test_hf1_decision_scorecard_governance_blocked_pass() -> None:
    payload = _base_inputs()
    payload["rag_proof"] = dict(payload["rag_proof"])
    payload["rag_proof"]["delivery_status"] = "governance_blocked"
    payload["rag_proof"]["knowledge_policy_included_writer_count"] = 0
    payload["rag_proof"]["knowledge_policy_included_diagnostic_count"] = 2
    payload["rag_proof"]["context_assembly_knowledge_hits_count"] = 0
    payload["rag_proof"]["writer_prompt_knowledge_hits_count"] = 0

    scorecard, decision = hf1.build_hf1_scorecard(**payload)
    assert scorecard["final_status"] == "passed"
    assert scorecard["decision"] == hf1.DECISION_PASSED_GOV_BLOCKED
    assert decision["decision"] == hf1.DECISION_PASSED_GOV_BLOCKED

