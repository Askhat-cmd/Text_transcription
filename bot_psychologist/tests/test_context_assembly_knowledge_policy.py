from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.context_assembly import build_context_assembly_package_v1
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="core",
        phase="clarify",
    )


def test_context_assembly_preserves_governance_summary_in_knowledge_hits() -> None:
    bundle = MemoryBundle(
        knowledge_rag_hits=[
            {
                "chunk_id": "k1",
                "source": "kb",
                "score": 0.91,
                "content": "sanitized knowledge",
                "governance_summary": {
                    "chunk_type": "practice",
                    "allowed_use": ["writer_context", "practice_suggestion"],
                    "policy_action": "include_writer_context",
                },
            }
        ]
    )

    package = build_context_assembly_package_v1(
        user_message="вопрос",
        thread_state=_thread(),
        memory_bundle=bundle,
    )

    assert package.knowledge_rag_hits
    first = package.knowledge_rag_hits[0]
    assert first.get("content") == "sanitized knowledge"
    assert isinstance(first.get("governance_summary"), dict)
    assert first["governance_summary"].get("chunk_type") == "practice"
