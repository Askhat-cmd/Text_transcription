from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def test_hf1_knowledge_policy_governance_blocked_classification() -> None:
    botdb_probe = {
        "botdb_http_status": 200,
        "botdb_chunks_returned": 3,
        "botdb_query_route_fallback_used": False,
    }
    debug_trace = {
        "semantic_hits_count": 3,
        "semantic_hits_detail": [{"score": 0.8}, {"score": 0.75}, {"score": 0.7}],
        "knowledge_policy_trace": {
            "input_hits_count": 3,
            "included_writer_count": 0,
            "included_diagnostic_count": 3,
            "drop_reasons": ["internal_only_or_style_not_user_facing"],
        },
        "context_assembly_trace": {"knowledge_hits_count": 0},
        "writer_user_prompt": "ЗНАНИЙ ИЗ БАЗЫ:\nнет релевантных знаний",
    }

    proof = hf1.build_rag_to_writer_delivery_proof(
        query="что такое нейросталкинг",
        botdb_probe=botdb_probe,
        debug_trace=debug_trace,
    )

    assert proof["knowledge_policy_included_writer_count"] == 0
    assert proof["knowledge_policy_included_diagnostic_count"] == 3
    assert proof["delivery_status"] == "governance_blocked"

