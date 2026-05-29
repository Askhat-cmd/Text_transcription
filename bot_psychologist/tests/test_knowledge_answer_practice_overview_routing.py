from __future__ import annotations

from bot_agent.multiagent.knowledge_answer_routing_guard import build_knowledge_answer_routing_guard


def test_practice_overview_query_sets_answer_type_and_direct_answer() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть",
        rag_hits=[],
        response_mode="reflect",
    )
    knowledge = payload["knowledge_answer"]
    assert knowledge["needed"] is True
    assert knowledge["concept"] == "нейросталкинг"
    assert knowledge["answer_type"] == "practice_overview"
    assert knowledge["should_answer_directly"] is True
    assert knowledge["kb_grounding_available"] is True


def test_practice_overview_keeps_practice_gate_allowed() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="какие практики в нейросталкинге обычно используют?",
        rag_hits=[],
        response_mode="inform",
    )
    practice_gate = payload["practice_gate"]
    assert practice_gate["practice_allowed"] is True
    assert practice_gate["reason"] == "explicit_practice_overview_request"
