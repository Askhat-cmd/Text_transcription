from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf2 as hf2


def test_hf2_live_delivery_scorecard_passed() -> None:
    scorecard, decision = hf2.build_HF2_scorecard(
        source_gate={"source_gate_passed": True},
        service_gate={"service_readiness_gate_passed": True},
        creator_live_proof={"actual_live_turn": True},
        botdb_probe={"botdb_http_status": 200, "botdb_chunks_returned": 4},
        rag_proof={
            "delivery_status": "passed",
            "retriever_raw_hits_count": 4,
            "retriever_raw_scores": [0.09, 0.08, 0.07, 0.04],
            "rag_filtered_hits_count": 2,
            "rag_filtered_by_score_count": 2,
            "rag_salvaged_hits_count": 2,
            "score_policy_mode": "source_aware_salvage",
            "knowledge_policy_input_hits_count": 2,
            "knowledge_policy_included_writer_count": 1,
            "knowledge_policy_dropped_count": 1,
            "knowledge_policy_drop_reasons": ["internal_only_or_style_not_user_facing"],
            "context_assembly_knowledge_hits_count": 1,
            "writer_prompt_knowledge_hits_count": 1,
        },
        ui_gate={"ui_trace_alignment_gate_passed": True, "ui_chunks_in_writer_count": 1},
        normal_user_gate={"normal_user_no_effect_gate_passed": True},
        trace_gate={"trace_sanitization_gate_passed": True},
        provider_gate={"provider_budget_gate_passed": True},
        no_mutation_proof={"no_mutation_proof_passed": True},
        artifact_encoding_hygiene_passed=True,
    )

    assert scorecard["final_status"] == "passed"
    assert scorecard["decision"] == hf2.DECISION_PASSED_RAG_READY
    assert decision["decision"] == hf2.DECISION_PASSED_RAG_READY
