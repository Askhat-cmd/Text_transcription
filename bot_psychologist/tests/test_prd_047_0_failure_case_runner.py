from __future__ import annotations

from scripts.run_prd_047_0_live_failure_cases import _evaluate_case


def _base_expected() -> dict:
    return {
        "knowledge_answer_needed": False,
        "practice_allowed": False,
        "forbid_unsolicited_practice": True,
    }


def test_greeting_with_breathing_words_fails() -> None:
    result = _evaluate_case(
        expected=_base_expected(),
        answer="Привет. Положи ладонь на грудь и сделай вдох-выдох.",
        knowledge_answer={"needed": False, "kb_grounding_available": False},
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is False
    assert result["checks"]["answer_has_no_unsolicited_practice"] is False


def test_greeting_simple_contact_passes() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": False,
            "practice_allowed": False,
            "forbid_unsolicited_practice": True,
            "required_answer_semantics": ["привет", "вопрос"],
        },
        answer="Привет. Рад знакомству. Можем начать: принеси любой вопрос.",
        knowledge_answer={"needed": False, "kb_grounding_available": False},
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is True


def test_known_concept_answer_that_asks_definition_fails() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": True,
            "should_answer_directly": True,
            "should_not_ask_user_to_define_term": True,
            "forbidden_question_patterns": ["что ты вкладываешь"],
            "require_kb_grounding_available": True,
        },
        answer="Что ты вкладываешь в этот термин?",
        knowledge_answer={
            "needed": True,
            "should_answer_directly": True,
            "should_ask_definition_first": False,
            "kb_grounding_available": True,
        },
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is False
    assert "answer_asks_user_to_define_known_term" in result["failure_reasons"]


def test_known_concept_answer_with_external_surveillance_fails() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": True,
            "should_answer_directly": True,
            "forbid_external_surveillance_frame": True,
            "require_kb_grounding_available": True,
        },
        answer="Это внешнее слежение и биофидбек через ЭЭГ.",
        knowledge_answer={
            "needed": True,
            "should_answer_directly": True,
            "kb_grounding_available": True,
        },
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is False
    assert result["checks"]["answer_avoids_external_surveillance_frame"] is False


def test_known_concept_answer_with_required_semantics_passes() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": True,
            "should_answer_directly": True,
            "required_answer_semantics": ["паттерн", "триггер", "автоматическ", "реакц"],
            "forbid_external_surveillance_frame": True,
            "require_kb_grounding_available": True,
        },
        answer="Нейросталкинг — это наблюдение за паттернами, триггерами и автоматическими реакциями.",
        knowledge_answer={
            "needed": True,
            "should_answer_directly": True,
            "kb_grounding_available": True,
        },
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is True


def test_relation_answer_missing_relation_semantics_fails() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": True,
            "should_answer_directly": True,
            "required_answer_semantics": ["самореализац", "нейросталкинг", "паттерн", "прояв"],
            "require_kb_grounding_available": True,
        },
        answer="Нейросталкинг — это просто внимание к ощущениям.",
        knowledge_answer={
            "needed": True,
            "should_answer_directly": True,
            "kb_grounding_available": True,
        },
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is False
    assert any(reason.startswith("answer_missing_required_semantics:") for reason in result["failure_reasons"])


def test_practice_gate_false_plus_practice_answer_fails() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": False,
            "practice_allowed": False,
            "forbid_unsolicited_practice": True,
        },
        answer="Сделай вдох и выдох.",
        knowledge_answer={"needed": False},
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is False


def test_required_kb_grounding_false_fails() -> None:
    result = _evaluate_case(
        expected={
            "knowledge_answer_needed": True,
            "require_kb_grounding_available": True,
        },
        answer="Краткий ответ.",
        knowledge_answer={
            "needed": True,
            "kb_grounding_available": False,
        },
        practice_gate={"practice_allowed": False},
    )
    assert result["passed"] is False
    assert result["checks"]["require_kb_grounding_available"] is False
