from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def test_hf1_memory_retrieval_trace_counts() -> None:
    botdb_probe = {
        "botdb_http_status": 200,
        "botdb_chunks_returned": 4,
        "botdb_query_route_fallback_used": False,
    }
    debug_trace = {
        "semantic_hits_count": 2,
        "semantic_hits_detail": [{"score": 0.91}, {"score": 0.73}],
        "knowledge_policy_trace": {"input_hits_count": 2, "included_writer_count": 2},
        "context_assembly_trace": {"knowledge_hits_count": 2},
        "writer_user_prompt": "ЗНАНИЙ ИЗ БАЗЫ:\n---\nchunk one\n---\nchunk two",
    }

    proof = hf1.build_rag_to_writer_delivery_proof(
        query="что такое нейросталкинг",
        botdb_probe=botdb_probe,
        debug_trace=debug_trace,
    )

    assert proof["retriever_raw_hits_count"] == 2
    assert proof["memory_semantic_hits_count"] == 2
    assert proof["knowledge_policy_input_hits_count"] == 2
    assert proof["delivery_status"] == "passed"

