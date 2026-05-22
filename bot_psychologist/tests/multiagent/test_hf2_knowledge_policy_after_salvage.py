from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.agents.memory_retrieval import rag_score_policy_v1
from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1


def test_hf2_knowledge_policy_after_salvage() -> None:
    hit = SemanticHit(
        chunk_id="c1",
        content="Нейросталкинг — это цифровое преследование и навязчивый контроль.",
        source="kb",
        score=0.09,
        governance={"chunk_type": "concept", "allowed_use": ["writer_context"], "safety_flags": []},
    )

    result = rag_score_policy_v1(
        raw_hits=[hit],
        rag_min_score=0.45,
        retrieval_source_used="api",
        query="что такое нейросталкинг",
    )
    decisions, trace = apply_knowledge_policy_v1(result["filtered_hits"])

    assert trace["input_hits_count"] >= 1
    assert len(decisions) >= 1
