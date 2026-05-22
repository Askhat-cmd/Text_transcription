from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def test_hf1_writer_contract_knowledge_prompt_count() -> None:
    botdb_probe = {
        "botdb_http_status": 200,
        "botdb_chunks_returned": 1,
        "botdb_query_route_fallback_used": False,
    }
    debug_trace = {
        "semantic_hits_count": 1,
        "semantic_hits_detail": [{"score": 0.92}],
        "knowledge_policy_trace": {"input_hits_count": 1, "included_writer_count": 1},
        "context_assembly_trace": {"knowledge_hits_count": 1},
        "writer_user_prompt": "ЗНАНИЙ ИЗ БАЗЫ:\n---\nФрагмент 1\n",
    }

    proof = hf1.build_rag_to_writer_delivery_proof(
        query="что такое нейросталкинг",
        botdb_probe=botdb_probe,
        debug_trace=debug_trace,
    )

    assert proof["writer_prompt_contains_knowledge_block"] is True
    assert proof["writer_prompt_knowledge_hits_count"] >= 1
    assert proof["delivery_status"] == "passed"

