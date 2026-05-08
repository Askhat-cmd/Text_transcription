from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit


def test_semantic_hit_roundtrip_preserves_governance_and_chunking_quality() -> None:
    hit = SemanticHit(
        chunk_id="chunk_1",
        content="content",
        source="book",
        score=0.91,
        governance={"chunk_type": "practice", "allowed_use": ["writer_context", "practice_suggestion"]},
        chunking_quality={"mixed_intent_severity": "low"},
    )
    restored = SemanticHit.from_dict(hit.to_dict())
    assert restored.to_dict() == hit.to_dict()


def test_memory_bundle_roundtrip_preserves_policy_trace() -> None:
    bundle = MemoryBundle(
        semantic_hits=[
            SemanticHit(chunk_id="c", content="t", source="book", score=0.7)
        ],
        knowledge_policy_trace={
            "version": "knowledge_policy_trace_v1",
            "included_writer_count": 1,
            "dropped_count": 0,
        },
    )
    restored = MemoryBundle.from_dict(bundle.to_dict())
    assert restored.knowledge_policy_trace.get("version") == "knowledge_policy_trace_v1"
    assert restored.to_dict() == bundle.to_dict()
