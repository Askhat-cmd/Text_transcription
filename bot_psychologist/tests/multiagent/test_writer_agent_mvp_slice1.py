from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_29_mvp_slice1 as runner
from bot_agent.multiagent.agents.writer_agent_mvp_slice1 import (
    MvpPart1Result,
    _classify_mvp_part1,
)


def _classify(**overrides):
    kwargs = dict(
        text="ok text",
        lowered_text="ok text",
        user_message="ok",
        answer_obligation="none",
        last_offer_summary="",
        last_direct_question="",
        pragmatics_repair_dissatisfaction=False,
        pragmatics_contextual_followup=False,
        pragmatics_should_not_reconfirm=False,
        pragmatics_offer_type="none",
        planner_safety_priority=False,
        planner_next_move="unrelated",
        planner_answer_shape="compact_direct",
        has_question=False,
        canned_step_disallowed=False,
        user_step_request=False,
        summary_request=False,
        sarcasm_or_negative_feedback=False,
        direct_concrete_request=False,
        explicit_answer_need=False,
        planner_question_policy="required",
        planner_practice_policy="allowed",
        has_unsolicited_practice=False,
        application_request=False,
        practice_overview_requested=False,
        answer_fit={},
    )
    kwargs.update(overrides)
    return _classify_mvp_part1(**kwargs)


def test_mvp_slice1_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(MvpPart1Result)] == runner.EXPECTED_FIELD_ORDER


def test_all_seventeen_tags_are_declared() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {
        "not_matched",
        "repair_answer_last_question",
        "repair_user_dissatisfaction",
        "contextual_followup_short_phrase",
        "contextual_followup_example",
        "contextual_followup_direct",
        "safety_grounding_literal",
        "safety_grounding_passthrough",
        "sanitized_direct_no_forced_practice",
        "one_step",
        "structured_summary",
        "sarcasm_negative_feedback_repair",
        "direct_concrete_request_repair",
        "direct_no_forced_question",
        "practice_forbidden_sanitized",
        "practice_forbidden_repair_needed",
        "practice_forbidden_repair_default",
    }
    assert len(runner.EXPECTED_OUTCOMES) == 17


def test_not_matched_when_none_of_the_groups_apply() -> None:
    result = _classify()
    assert result.outcome == "not_matched"
    assert result.updated_text == "ok text"
    assert result.updated_lowered_text == "ok text"


def test_repair_answer_last_question_outcome_uses_last_direct_question_as_target() -> None:
    result = _classify(
        pragmatics_repair_dissatisfaction=True,
        answer_obligation="repair_and_answer_last_question",
        last_direct_question="Что такое нейросталкинг?",
    )
    assert result.outcome == "repair_answer_last_question"
    assert result.computed_target == "Что такое нейросталкинг?"


def test_repair_user_dissatisfaction_outcome() -> None:
    result = _classify(pragmatics_repair_dissatisfaction=True, last_direct_question="обычный вопрос")
    assert result.outcome == "repair_user_dissatisfaction"
    assert result.computed_target == "обычный вопрос"


def test_repair_user_dissatisfaction_falls_back_to_user_message_when_target_empty() -> None:
    result = _classify(pragmatics_repair_dissatisfaction=True, user_message="fallback message")
    assert result.outcome == "repair_user_dissatisfaction"
    assert result.computed_target == "fallback message"


def test_contextual_followup_short_phrase_outcome() -> None:
    text = "сфокусируюсь на разборе"
    result = _classify(
        pragmatics_contextual_followup=True,
        pragmatics_should_not_reconfirm=True,
        text=text,
        lowered_text=text,
        pragmatics_offer_type="short_phrase",
    )
    assert result.outcome == "contextual_followup_short_phrase"


def test_contextual_followup_example_outcome() -> None:
    text = "без практик по умолчанию"
    result = _classify(
        pragmatics_contextual_followup=True,
        pragmatics_should_not_reconfirm=True,
        text=text,
        lowered_text=text,
        pragmatics_offer_type="example",
    )
    assert result.outcome == "contextual_followup_example"


def test_contextual_followup_direct_outcome() -> None:
    text = "без практик по умолчанию"
    result = _classify(
        pragmatics_contextual_followup=True,
        pragmatics_should_not_reconfirm=True,
        text=text,
        lowered_text=text,
        pragmatics_offer_type="other",
    )
    assert result.outcome == "contextual_followup_direct"


def test_group_b_mutates_text_when_it_does_not_return() -> None:
    """Особенность 1: group B mutates text/lowered_text in place ('хочешь'
    + '?' triggers a rewrite), and when the group falls through without
    returning, the mutation must still survive via updated_text/
    updated_lowered_text.
    """
    text_in = "хочешь узнать больше?"
    result = _classify(
        pragmatics_contextual_followup=True,
        pragmatics_should_not_reconfirm=True,
        text=text_in,
        lowered_text=text_in,
    )
    assert result.outcome == "not_matched"
    assert result.updated_text != text_in
    assert result.updated_text == "хочешь узнать больше."
    assert result.updated_lowered_text == result.updated_text.lower()


def test_safety_grounding_literal_outcome() -> None:
    result = _classify(planner_safety_priority=True, has_question=True)
    assert result.outcome == "safety_grounding_literal"
    assert "стабилизироваться" in result.return_text


def test_safety_grounding_passthrough_outcome() -> None:
    result = _classify(planner_safety_priority=True, text="short")
    assert result.outcome == "safety_grounding_passthrough"
    assert result.return_text == "short"


def test_sanitized_direct_no_forced_practice_outcome() -> None:
    result = _classify(canned_step_disallowed=True, planner_answer_shape="one_step")
    assert result.outcome == "sanitized_direct_no_forced_practice"


def test_one_step_outcome() -> None:
    result = _classify(planner_answer_shape="one_step")
    assert result.outcome == "one_step"


def test_structured_summary_outcome() -> None:
    result = _classify(summary_request=True)
    assert result.outcome == "structured_summary"


def test_sarcasm_negative_feedback_repair_outcome() -> None:
    result = _classify(sarcasm_or_negative_feedback=True)
    assert result.outcome == "sarcasm_negative_feedback_repair"


def test_direct_concrete_request_repair_outcome() -> None:
    result = _classify(direct_concrete_request=True)
    assert result.outcome == "direct_concrete_request_repair"


def test_direct_no_forced_question_outcome_computes_return_text() -> None:
    result = _classify(
        explicit_answer_need=True,
        has_question=True,
        planner_question_policy="none",
        text="Question one? Question two?",
    )
    assert result.outcome == "direct_no_forced_question"
    assert result.return_text == "Question one. Question two."


def test_practice_forbidden_sanitized_outcome() -> None:
    result = _classify(
        planner_practice_policy="forbidden",
        has_unsolicited_practice=True,
        answer_obligation="answer_direct_question",
        text="x" * 230,
    )
    assert result.outcome == "practice_forbidden_sanitized"


def test_practice_forbidden_repair_needed_outcome_and_patch() -> None:
    result = _classify(
        planner_practice_policy="forbidden",
        has_unsolicited_practice=True,
        answer_fit={"needs_repair": True},
    )
    assert result.outcome == "practice_forbidden_repair_needed"
    assert result.last_debug_patch == {
        "answer_fit_repair_applied": True,
        "template_leakage_repair_deferred_to_gate": True,
    }


def test_practice_forbidden_repair_default_outcome_and_patch() -> None:
    result = _classify(
        planner_practice_policy="forbidden",
        has_unsolicited_practice=True,
        answer_fit={},
    )
    assert result.outcome == "practice_forbidden_repair_default"
    assert result.last_debug_patch == {
        "answer_fit_repair_applied": True,
        "template_leakage_repair_deferred_to_gate": True,
    }


def test_practice_forbidden_two_branches_share_identical_patch_but_distinct_outcomes() -> None:
    needed = _classify(
        planner_practice_policy="forbidden",
        has_unsolicited_practice=True,
        answer_fit={"needs_repair": True},
    )
    default = _classify(
        planner_practice_policy="forbidden",
        has_unsolicited_practice=True,
        answer_fit={},
    )
    assert needed.outcome != default.outcome
    assert needed.last_debug_patch == default.last_debug_patch


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(planner_answer_shape="one_step")
    first = _classify(**kwargs)
    second = _classify(**kwargs)
    assert first == second


def test_classifier_helper_module_has_no_self_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_mvp_slice1 as module

    source = inspect.getsource(module)
    assert "self." not in source
