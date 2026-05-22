from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.agents.memory_retrieval import rag_score_policy_v1
from bot_agent.multiagent.contracts.memory_bundle import SemanticHit


def test_hf2_memory_retrieval_low_score_salvage() -> None:
    hits = [
        SemanticHit(chunk_id="c1", content="A", source="kb", score=0.09),
        SemanticHit(chunk_id="c2", content="B", source="kb", score=0.08),
        SemanticHit(chunk_id="c3", content="C", source="kb", score=0.05),
    ]

    result = rag_score_policy_v1(
        raw_hits=hits,
        rag_min_score=0.45,
        retrieval_source_used="api",
        query="что такое нейросталкинг",
    )

    assert result["trace"]["score_policy_mode"] == "source_aware_salvage"
    assert result["trace"]["salvaged_hits_count"] >= 1
    assert len(result["filtered_hits"]) >= 1
