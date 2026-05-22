from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_rag_delivery_hf2 as hf2


def test_hf2_trace_raw_filtered_counts() -> None:
    proof = hf2.build_rag_to_writer_delivery_proof(
        query="что такое нейросталкинг",
        botdb_probe={"botdb_http_status": 200, "botdb_chunks_returned": 4, "botdb_query_route_fallback_used": True},
        debug_trace={
            "semantic_hits_count": 2,
            "semantic_hits_detail": [{"score": 0.09}, {"score": 0.08}],
            "rag_retrieval_trace": {
                "raw_hits_count": 4,
                "raw_scores": [0.09, 0.08, 0.07, 0.04],
                "filtered_hits_count": 2,
                "filtered_by_score_count": 2,
                "salvaged_hits_count": 2,
                "score_policy_mode": "source_aware_salvage",
                "retrieval_source_used": "api",
            },
            "knowledge_policy_trace": {"input_hits_count": 2, "included_writer_count": 1},
            "context_assembly_trace": {"knowledge_hits_count": 1},
            "writer_user_prompt": "ЗНАНИЙ ИЗ БАЗЫ:\n---\nфрагмент",
        },
    )

    assert proof["retriever_raw_hits_count"] == 4
    assert proof["rag_filtered_hits_count"] == 2
    assert proof["rag_salvaged_hits_count"] == 2
    assert proof["score_policy_mode"] == "source_aware_salvage"
