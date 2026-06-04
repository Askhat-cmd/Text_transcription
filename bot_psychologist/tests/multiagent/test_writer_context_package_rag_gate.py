from __future__ import annotations

from bot_agent.multiagent.context_assembly import build_context_assembly_package_v1
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.fresh_chat_context_policy import build_fresh_chat_context_policy_v1
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _thread() -> ThreadState:
    return ThreadState(thread_id="t-hf2", user_id="u-hf2", core_direction="contact", phase="clarify")


def test_writer_context_package_suppresses_rag_for_fresh_greeting() -> None:
    memory_bundle = MemoryBundle(
        user_profile=UserProfile(patterns=["old-topic"], values=["clarity"], progress_notes=["old summary"]),
        semantic_hits=[
            SemanticHit(
                chunk_id="k1",
                content="Старый knowledge chunk, который не должен попадать в greeting prompt.",
                source="kb",
                score=0.18,
            )
        ],
        knowledge_rag_hits=[
            {
                "chunk_id": "k1",
                "content": "Старый knowledge chunk, который не должен попадать в greeting prompt.",
                "source": "kb",
                "score": 0.18,
            }
        ],
        recent_turns=[],
    )
    context_package = build_context_assembly_package_v1(
        user_message="привет, меня зовут Асхат!",
        thread_state=_thread(),
        memory_bundle=memory_bundle,
    )
    fresh_policy = build_fresh_chat_context_policy_v1(
        user_message="привет, меня зовут Асхат!",
        recent_turns=[],
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )
    payload = build_writer_context_package_v1(
        memory_bundle=memory_bundle,
        context_package=context_package,
        retrieval_decision={
            "rag_included_count": 0,
            "rag_suppressed_reason": "fresh_greeting_no_knowledge_need",
            "rag_included_for_writer": [],
        },
        fresh_chat_context_policy=fresh_policy,
    )

    assert payload["version"] == "writer_context_package_v1"
    assert payload["profile_for_writer"] == {}
    assert payload["rag_for_writer"] == []
    assert len(payload["rag_candidates_for_trace"]) == 1
    assert payload["rag_candidates_for_trace"][0]["reason_not_included"] == "fresh_greeting_no_knowledge_need"

