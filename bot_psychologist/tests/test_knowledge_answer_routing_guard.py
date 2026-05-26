from __future__ import annotations

from bot_agent.multiagent.agents.memory_retrieval import rag_score_policy_v1
from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.knowledge_answer_routing_guard import (
    build_knowledge_answer_routing_guard,
)


def _hit(*, chunk_id: str, score: float, content: str, source: str = "kb") -> SemanticHit:
    return SemanticHit(chunk_id=chunk_id, content=content, source=source, score=score)


def test_known_concept_question_sets_knowledge_answer_needed() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="Что такое нейросталкинг?",
        rag_hits=[],
        response_mode="reflect",
    )
    assert payload["knowledge_answer"]["needed"] is True
    assert payload["knowledge_answer"]["concept"] == "нейросталкинг"


def test_challenge_question_prefers_direct_answer_when_kb_grounding_exists() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message='Ты вообще понимаешь что такое "Нейросталкинг"?',
        rag_hits=[
            _hit(
                chunk_id="k1",
                score=0.12,
                content="Нейросталкинг — это наблюдение за паттернами, триггерами и автоматическими реакциями.",
            )
        ],
        response_mode="reflect",
    )
    assert payload["knowledge_answer"]["needed"] is True
    assert payload["knowledge_answer"]["kb_grounding_available"] is True
    assert payload["knowledge_answer"]["should_answer_directly"] is True
    assert payload["knowledge_answer"]["should_ask_definition_first"] is False


def test_lexical_override_keeps_low_score_known_concept_hit() -> None:
    raw_hits = [
        _hit(
            chunk_id="low-score-hit",
            score=0.01,
            content="Нейросталкинг и Неосталкинг — два уровня одного процесса.",
        )
    ]
    result = rag_score_policy_v1(
        raw_hits=raw_hits,
        rag_min_score=0.35,
        retrieval_source_used="api",
        query="Ты вообще понимаешь что такое нейросталкинг?",
    )
    filtered_hits = result["filtered_hits"]
    trace = result["trace"]
    assert len(filtered_hits) == 1
    assert filtered_hits[0].chunk_id == "low-score-hit"
    assert trace["score_policy_mode"] == "lexical_known_concept_override"


def test_internal_concept_not_classified_as_external_surveillance_when_kb_hit_present() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="Как самореализация коррелирует с нейросталкингом?",
        rag_hits=[
            _hit(
                chunk_id="k2",
                score=0.21,
                content="Нейросталкинг в нашей рамке — наблюдение за внутренними паттернами.",
            )
        ],
        response_mode="reflect",
    )
    assert payload["knowledge_answer"]["needed"] is True
    assert payload["knowledge_answer"]["concept"] == "нейросталкинг"
    assert payload["knowledge_answer"]["should_answer_directly"] is True


def test_greeting_does_not_enable_practice() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="Привет! Меня зовут Аскхат.",
        rag_hits=[],
        response_mode="reflect",
    )
    assert payload["practice_gate"]["practice_allowed"] is False
    assert payload["practice_gate"]["reason"] == "greeting_no_practice_default"


def test_explicit_practice_request_keeps_practice_allowed() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="Дай одну практику, как успокоиться прямо сейчас.",
        rag_hits=[],
        response_mode="regulate",
    )
    assert payload["practice_gate"]["practice_allowed"] is True
    assert payload["practice_gate"]["reason"] == "explicit_practice_request"


def test_guard_payload_does_not_include_raw_private_text() -> None:
    private_text = "МОЙ_СЕКРЕТНЫЙ_ТЕКСТ_123"
    payload = build_knowledge_answer_routing_guard(
        user_message="Что такое нейросталкинг?",
        rag_hits=[_hit(chunk_id="x", score=0.1, content=private_text)],
        response_mode="reflect",
    )
    serialized = str(payload)
    assert private_text not in serialized


def test_empty_rag_hits_does_not_break_guard() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="Что такое внутренний резонанс принятия?",
        rag_hits=[],
        response_mode="reflect",
    )
    assert isinstance(payload, dict)
    assert payload["knowledge_answer"]["kb_grounding_available"] is False


def test_relation_case_gets_internal_fallback_grounding_when_known_concepts_present() -> None:
    payload = build_knowledge_answer_routing_guard(
        user_message="Как самореализация коррелируется с нейросталкингом?",
        rag_hits=[],
        response_mode="reflect",
    )
    assert payload["knowledge_answer"]["needed"] is True
    assert payload["knowledge_answer"]["kb_grounding_available"] is True
    assert payload["knowledge_answer"]["fallback_grounding_used"] is True
    assert payload["knowledge_answer"]["should_answer_directly"] is True
