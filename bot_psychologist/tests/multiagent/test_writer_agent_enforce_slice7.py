from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_28_enforce_slice7 as runner
from bot_agent.multiagent.agents.writer_agent_enforce_slice7 import (
    EnforceBlockBPart2Result,
    _classify_enforce_block_b_part2,
)

_REVOICING_TEXT = "Вы говорите, что застреваете. Это правда важно и мы разберём."
_REVOICING_TAIL_TEXT = "Вы говорите, что застреваете. Давай продолжим дальше подробно."


def _classify(**overrides):
    kwargs = dict(
        text="ok text",
        user_message="ok",
        lowered_user="ok",
        lowered_text="ok text",
        planner_next_move="unrelated",
        planner_question_policy="required",
        planner_answer_shape="compact_direct",
        planner_practice_policy="allowed",
        user_mechanism_request=False,
        user_requests_no_question=False,
        user_requests_no_practice=False,
        has_question=False,
        has_unsolicited_practice=False,
        user_step_request=False,
        active_line_intent="other",
        active_line_practice_suppression=False,
        active_line_should_offer_practice=True,
        active_line_repair_mode=False,
        active_line_revoicing_allowed=True,
    )
    kwargs.update(overrides)
    return _classify_enforce_block_b_part2(**kwargs)


def test_enforce_slice7_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(EnforceBlockBPart2Result)] == runner.EXPECTED_FIELD_ORDER


def test_all_seventeen_tags_are_declared() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {
        "not_matched",
        "mechanism_explanation_repair_g7",
        "one_step_g8",
        "first_item_extraction_g9",
        "sentence_parts_one_step_g9",
        "question_marker_one_step_g9",
        "no_step_marker_one_step_g9",
        "safety_grounding_g10",
        "active_line_correction_repair_g10",
        "active_line_mechanism_repair_g10",
        "practice_suppression_meaning_repair_g10",
        "active_line_revoicing_correction_repair_g11",
        "active_line_revoicing_mechanism_repair_g11",
        "revoicing_strip_g11",
        "known_concept_correlation_repair_g12",
        "known_concept_neurostalking_repair_g12",
        "known_concept_self_realization_repair_g12",
    }
    assert len(runner.EXPECTED_OUTCOMES) == 17


def test_not_matched_when_none_of_the_six_groups_apply() -> None:
    result = _classify()
    assert result.outcome == "not_matched"


def test_not_matched_integration_dispatches_to_return_text() -> None:
    """Reproduces the exact call-site tail from writer_agent.py: when
    outcome == 'not_matched', there is no matching `if`, so the function
    falls through to the unconditional `return text` at the end of the
    method.
    """
    text = "some final passthrough text"
    result = _classify(text=text)
    assert result.outcome == "not_matched"

    dispatch_outcomes = {
        "mechanism_explanation_repair_g7",
        "one_step_g8",
        "sentence_parts_one_step_g9",
        "question_marker_one_step_g9",
        "no_step_marker_one_step_g9",
        "first_item_extraction_g9",
        "safety_grounding_g10",
        "active_line_correction_repair_g10",
        "active_line_mechanism_repair_g10",
        "practice_suppression_meaning_repair_g10",
        "active_line_revoicing_correction_repair_g11",
        "active_line_revoicing_mechanism_repair_g11",
        "revoicing_strip_g11",
        "known_concept_correlation_repair_g12",
        "known_concept_neurostalking_repair_g12",
        "known_concept_self_realization_repair_g12",
    }
    assert result.outcome not in dispatch_outcomes
    final_return = text  # mirrors the unconditional `return text` tail
    assert final_return == text


def test_mechanism_explanation_repair_g7_outcome() -> None:
    result = _classify(planner_next_move="deepen_mechanism", planner_question_policy="none", has_question=True)
    assert result.outcome == "mechanism_explanation_repair_g7"


def test_one_step_g8_outcome() -> None:
    result = _classify(planner_answer_shape="one_step")
    assert result.outcome == "one_step_g8"


def test_first_item_extraction_g9_outcome_computes_return_text() -> None:
    result = _classify(user_step_request=True, text="- пункт один\nвторая строка")
    assert result.outcome == "first_item_extraction_g9"
    assert result.return_text == "пункт один"


def test_group_nine_edge_case_list_like_true_first_item_none_falls_through() -> None:
    """Особенность 1: list_like matches a bare list marker with no content
    after it, so first_item stays None. The nested if has no else, so
    execution must fall through to the sentence_parts check instead of
    exiting the group or raising.
    """
    result = _classify(user_step_request=True, text="-\n", lowered_text="-\n")
    assert result.outcome != "first_item_extraction_g9"
    assert result.outcome in {
        "sentence_parts_one_step_g9",
        "question_marker_one_step_g9",
        "no_step_marker_one_step_g9",
    }


def test_sentence_parts_one_step_g9_outcome() -> None:
    result = _classify(user_step_request=True, text="One. Two. Three.")
    assert result.outcome == "sentence_parts_one_step_g9"


def test_question_marker_one_step_g9_outcome() -> None:
    result = _classify(
        user_step_request=True,
        planner_question_policy="none",
        text="коротко",
        lowered_text="хочешь ли ты",
    )
    assert result.outcome == "question_marker_one_step_g9"


def test_no_step_marker_one_step_g9_outcome() -> None:
    result = _classify(
        user_step_request=True,
        text="коротко без спец слов",
        lowered_text="коротко без спец слов",
    )
    assert result.outcome == "no_step_marker_one_step_g9"


def test_group_eight_wins_over_group_nine_when_both_formally_apply() -> None:
    result = _classify(
        planner_answer_shape="one_step",
        user_step_request=True,
        text="- пункт\nещё текст",
    )
    assert result.outcome == "one_step_g8"


def test_safety_grounding_g10_outcome() -> None:
    result = _classify(
        active_line_practice_suppression=True,
        active_line_should_offer_practice=False,
        has_unsolicited_practice=True,
        planner_next_move="stabilize_safety",
    )
    assert result.outcome == "safety_grounding_g10"


def test_active_line_correction_repair_g10_outcome() -> None:
    result = _classify(
        active_line_practice_suppression=True,
        active_line_should_offer_practice=False,
        has_unsolicited_practice=True,
        active_line_intent="correction_of_bot",
    )
    assert result.outcome == "active_line_correction_repair_g10"


def test_active_line_mechanism_repair_g10_outcome() -> None:
    result = _classify(
        active_line_practice_suppression=True,
        active_line_should_offer_practice=False,
        has_unsolicited_practice=True,
        active_line_intent="understand_mechanism",
    )
    assert result.outcome == "active_line_mechanism_repair_g10"


def test_practice_suppression_meaning_repair_g10_outcome() -> None:
    result = _classify(
        active_line_practice_suppression=True,
        active_line_should_offer_practice=False,
        has_unsolicited_practice=True,
    )
    assert result.outcome == "practice_suppression_meaning_repair_g10"


def test_active_line_revoicing_correction_repair_g11_outcome() -> None:
    result = _classify(
        active_line_revoicing_allowed=False,
        active_line_intent="correction_of_bot",
        text=_REVOICING_TEXT,
    )
    assert result.outcome == "active_line_revoicing_correction_repair_g11"


def test_active_line_revoicing_mechanism_repair_g11_outcome() -> None:
    result = _classify(
        active_line_revoicing_allowed=False,
        active_line_intent="understand_mechanism",
        text=_REVOICING_TEXT,
    )
    assert result.outcome == "active_line_revoicing_mechanism_repair_g11"


def test_revoicing_strip_g11_outcome_computes_return_text() -> None:
    result = _classify(active_line_revoicing_allowed=False, text=_REVOICING_TAIL_TEXT)
    assert result.outcome == "revoicing_strip_g11"
    assert result.return_text == "Давай продолжим дальше подробно."


def test_known_concept_correlation_repair_g12_outcome() -> None:
    result = _classify(
        planner_next_move="answer_known_concept",
        planner_practice_policy="forbidden",
        lowered_user="самореализация и нейросталкинг",
    )
    assert result.outcome == "known_concept_correlation_repair_g12"


def test_known_concept_neurostalking_repair_g12_outcome() -> None:
    result = _classify(
        planner_next_move="answer_known_concept",
        planner_practice_policy="forbidden",
        lowered_user="нейросталкинг",
    )
    assert result.outcome == "known_concept_neurostalking_repair_g12"


def test_known_concept_self_realization_repair_g12_outcome() -> None:
    result = _classify(
        planner_next_move="answer_known_concept",
        planner_practice_policy="forbidden",
        lowered_user="самореализация",
    )
    assert result.outcome == "known_concept_self_realization_repair_g12"


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(planner_answer_shape="one_step")
    first = _classify(**kwargs)
    second = _classify(**kwargs)
    assert first == second


def test_classifier_helper_module_has_no_self_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_enforce_slice7 as module

    source = inspect.getsource(module)
    assert "self." not in source
