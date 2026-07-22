from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_24_enforce_slice4 as runner
from bot_agent.multiagent.agents.writer_agent_enforce_slice4 import (
    EnforceSlice4Result,
    _classify_enforce_slice4_obligation_repairs_and_echo,
)


def _classify(**overrides):
    kwargs = dict(
        text="ок",
        user_message="ок",
        lowered_text="ок",
        answer_obligation="none",
        literal_markdown_echo="",
        concept_question=False,
        last_direct_question="",
        last_offer_summary="",
        offer_repair_context="",
    )
    kwargs.update(overrides)
    return _classify_enforce_slice4_obligation_repairs_and_echo(**kwargs)


def test_enforce_slice4_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(EnforceSlice4Result)] == runner.EXPECTED_FIELD_ORDER


def test_not_matched_when_nothing_applies() -> None:
    result = _classify()
    assert result.outcome == "not_matched"
    assert result.last_debug_patch is None
    assert result.return_text is None
    assert result.defer_signal is None
    assert result.defer_must_answer is None


def test_literal_markdown_echo_mismatch_outcome_and_exact_patch_key_order() -> None:
    result = _classify(literal_markdown_echo="точный формат", text="другой текст")
    assert result.outcome == "literal_markdown_echo_mismatch"
    assert list(result.last_debug_patch.keys()) == runner.LITERAL_MARKDOWN_ECHO_PATCH_KEY_ORDER
    assert result.last_debug_patch["format_request_repair_applied"] is True
    assert result.last_debug_patch["final_answer_shape"] == "literal_markdown_echo"
    assert result.return_text == "точный формат"


def test_literal_markdown_echo_match_does_not_trigger_mismatch_outcome() -> None:
    result = _classify(literal_markdown_echo="точный формат", text="точный формат")
    assert result.outcome != "literal_markdown_echo_mismatch"


def test_acknowledge_style_preference_repair_outcome() -> None:
    result = _classify(
        answer_obligation="acknowledge_style_preference_then_answer",
        text="расскажи больше пожалуйста",
        lowered_text="расскажи больше пожалуйста",
        concept_question=True,
    )
    assert result.outcome == "acknowledge_style_preference_repair"
    assert result.defer_signal == "style_preference_direct_answer_repair"
    assert result.defer_must_answer == "known_concept_question"


def test_repair_and_answer_last_question_repair_outcome_uses_last_direct_question_as_target() -> None:
    result = _classify(
        answer_obligation="repair_and_answer_last_question",
        text="коротко",
        lowered_text="коротко",
        last_direct_question="Что такое нейросталкинг?",
    )
    assert result.outcome == "repair_and_answer_last_question_repair"
    assert result.defer_signal == "repair_answer_last_question_repair"
    assert result.defer_must_answer == "Что такое нейросталкинг?"


def test_repair_and_answer_last_question_falls_back_to_user_message_as_target() -> None:
    result = _classify(
        answer_obligation="repair_and_answer_last_question",
        text="коротко",
        lowered_text="коротко",
        user_message="Расскажи про нейросталкинг подробнее",
        last_direct_question="",
    )
    assert result.outcome == "repair_and_answer_last_question_repair"
    assert result.defer_must_answer == "Расскажи про нейросталкинг подробнее"


def test_answer_last_offer_repair_outcome() -> None:
    result = _classify(
        answer_obligation="answer_last_offer",
        text="могу так сделать",
        lowered_text="могу так сделать",
        offer_repair_context="красный статус",
    )
    assert result.outcome == "answer_last_offer_repair"
    assert result.defer_signal == "answer_last_offer_repair"
    assert result.defer_must_answer == "last_assistant_offer"


def test_answer_knowledge_or_direct_repair_outcome() -> None:
    result = _classify(
        answer_obligation="answer_knowledge_question",
        text="коротко",
        lowered_text="коротко",
        concept_question=True,
    )
    assert result.outcome == "answer_knowledge_or_direct_repair"
    assert result.defer_signal == "knowledge_direct_answer_repair"
    assert result.defer_must_answer == "known_concept_question"


def test_all_six_outcomes_are_covered_and_exhaustive() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {
        "not_matched",
        "literal_markdown_echo_mismatch",
        "acknowledge_style_preference_repair",
        "repair_and_answer_last_question_repair",
        "answer_last_offer_repair",
        "answer_knowledge_or_direct_repair",
    }


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(
        answer_obligation="answer_knowledge_question",
        text="коротко",
        lowered_text="коротко",
        concept_question=True,
    )
    first = _classify(**kwargs)
    second = _classify(**kwargs)
    assert first == second


def test_classifier_helper_module_has_no_self_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_enforce_slice4 as module

    source = inspect.getsource(module)
    assert "self." not in source
