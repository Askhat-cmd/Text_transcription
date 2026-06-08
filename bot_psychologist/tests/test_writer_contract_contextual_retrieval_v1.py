from __future__ import annotations

from datetime import datetime

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _composer() -> dict:
    return {
        "version": "contextual_retrieval_query_composer_v1",
        "retrieval_need": "knowledge_context",
        "retrieval_action": "query_kb",
        "query_source": "last_assistant_offer",
        "composed_query": "нейросталкинг автоматизм наблюдение",
        "writer_can_ignore_rag": True,
        "include_for_writer_if_found": True,
        "no_user_facing_text_created": True,
    }


def test_writer_context_package_exposes_composer_payload() -> None:
    package = build_writer_context_package_v1(
        memory_bundle=MemoryBundle(),
        context_package=None,
        retrieval_decision={
            "composer": _composer(),
            "rag_included_count": 0,
            "rag_included_for_writer": [],
        },
        fresh_chat_context_policy={},
    )

    assert package["contextual_retrieval_query_composer"]["query_source"] == "last_assistant_offer"
    assert package["composed_retrieval_query"] == "нейросталкинг автоматизм наблюдение"
    assert package["writer_can_ignore_rag"] is True


def test_writer_contract_prompt_context_exposes_composer_fields() -> None:
    contract = WriterContract(
        user_message="да",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="User: вопрос\nAssistant: offer"),
        retrieval_decision={
            "composer": _composer(),
            "rag_included_count": 0,
            "rag_included_for_writer": [],
        },
    )
    ctx = contract.to_prompt_context()

    assert ctx["contextual_retrieval_query_composer_version"] == "contextual_retrieval_query_composer_v1"
    assert ctx["retrieval_query_source"] == "last_assistant_offer"
    assert ctx["composed_retrieval_query"] == "нейросталкинг автоматизм наблюдение"
    assert ctx["retrieval_query_composer_action"] == "query_kb"
    assert ctx["retrieval_query_composer_no_user_facing_text_created"] is True
