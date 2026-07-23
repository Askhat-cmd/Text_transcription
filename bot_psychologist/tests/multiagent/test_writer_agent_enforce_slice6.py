from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_27_enforce_slice6 as runner
from bot_agent.multiagent.agents.writer_agent_enforce_slice6 import (
    EnforceBlockBPart1Result,
    _classify_enforce_block_b_part1,
)


def _classify(**overrides):
    kwargs = dict(
        text="ok text",
        user_message="ok",
        lowered_user="ok",
        lowered_text="ok text",
        concept="",
        should_answer_directly=False,
        asks_define_known_term=False,
        has_external_surveillance_frame=False,
        planner_question_policy="required",
        planner_next_move="unrelated_move",
        planner_answer_shape="compact_direct",
        planner_practice_policy="allowed",
        has_question=False,
        has_unsolicited_practice=False,
    )
    kwargs.update(overrides)
    return _classify_enforce_block_b_part1(**kwargs)


def test_enforce_slice6_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(EnforceBlockBPart1Result)] == runner.EXPECTED_FIELD_ORDER


def test_all_nineteen_tags_are_declared() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {
        "not_matched",
        "known_concept_prefirst_correlation",
        "known_concept_prefirst_neurostalking",
        "known_concept_prefirst_self_realization",
        "no_question_one_step",
        "no_question_short_support",
        "no_question_safety_grounding",
        "no_question_known_concept_correlation",
        "no_question_known_concept_neurostalking",
        "no_question_default_strip",
        "question_marker_one_step",
        "question_marker_short_support",
        "question_marker_safety_grounding",
        "question_marker_close_gently",
        "question_marker_default",
        "none_policy_one_step",
        "none_policy_mechanism_repair",
        "repair_misalignment",
        "practice_forbidden_unsolicited_repair",
    }
    assert len(runner.EXPECTED_OUTCOMES) == 19


def test_not_matched_when_none_of_the_six_groups_apply() -> None:
    result = _classify(
        planner_question_policy="required",
        planner_next_move="unrelated_move",
        planner_practice_policy="allowed",
        has_unsolicited_practice=False,
    )
    assert result.outcome == "not_matched"


def test_known_concept_prefirst_correlation_outcome() -> None:
    result = _classify(
        should_answer_directly=True,
        asks_define_known_term=True,
        lowered_user="самореализация коррелирует",
    )
    assert result.outcome == "known_concept_prefirst_correlation"


def test_known_concept_prefirst_neurostalking_outcome() -> None:
    result = _classify(
        should_answer_directly=True,
        asks_define_known_term=True,
        concept="нейросталкинг",
        lowered_user="вопрос",
    )
    assert result.outcome == "known_concept_prefirst_neurostalking"


def test_known_concept_prefirst_self_realization_outcome() -> None:
    result = _classify(
        should_answer_directly=True,
        asks_define_known_term=True,
        concept="самореализация",
        lowered_user="вопрос",
    )
    assert result.outcome == "known_concept_prefirst_self_realization"


def test_no_question_one_step_outcome() -> None:
    result = _classify(planner_question_policy="none", has_question=True, planner_next_move="give_direct_step")
    assert result.outcome == "no_question_one_step"


def test_no_question_short_support_outcome() -> None:
    result = _classify(planner_question_policy="none", has_question=True, planner_next_move="give_short_support")
    assert result.outcome == "no_question_short_support"


def test_no_question_safety_grounding_outcome() -> None:
    result = _classify(planner_question_policy="none", has_question=True, planner_next_move="stabilize_safety")
    assert result.outcome == "no_question_safety_grounding"


def test_no_question_known_concept_correlation_outcome_is_a_distinct_tag_from_prefirst() -> None:
    result = _classify(
        planner_question_policy="none",
        has_question=True,
        planner_next_move="answer_known_concept",
        lowered_user="самореализация и нейросталкинг",
    )
    assert result.outcome == "no_question_known_concept_correlation"
    assert result.outcome != "known_concept_prefirst_correlation"


def test_no_question_known_concept_neurostalking_outcome_is_a_distinct_tag_from_prefirst() -> None:
    result = _classify(
        planner_question_policy="none",
        has_question=True,
        planner_next_move="answer_known_concept",
        lowered_user="нейросталкинг",
    )
    assert result.outcome == "no_question_known_concept_neurostalking"
    assert result.outcome != "known_concept_prefirst_neurostalking"


def test_no_question_default_strip_computes_return_text() -> None:
    result = _classify(
        planner_question_policy="none",
        has_question=True,
        planner_next_move="unrelated",
        text="Text? More?",
    )
    assert result.outcome == "no_question_default_strip"
    assert result.return_text == "Text. More."


def test_no_question_default_strip_return_text_varies_with_input() -> None:
    result = _classify(
        planner_question_policy="none",
        has_question=True,
        planner_next_move="unrelated",
        text="Alpha?   Beta??",
    )
    assert result.return_text == "Alpha. Beta."


def test_question_marker_one_step_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="что именно тут", planner_next_move="give_direct_step")
    assert result.outcome == "question_marker_one_step"


def test_question_marker_short_support_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="что именно", planner_next_move="give_short_support")
    assert result.outcome == "question_marker_short_support"


def test_question_marker_safety_grounding_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="что именно", planner_next_move="stabilize_safety")
    assert result.outcome == "question_marker_safety_grounding"


def test_question_marker_close_gently_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="что именно", planner_next_move="close_gently")
    assert result.outcome == "question_marker_close_gently"


def test_question_marker_default_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="что именно", planner_next_move="unrelated")
    assert result.outcome == "question_marker_default"


def test_none_policy_one_step_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="no marker", planner_next_move="give_direct_step")
    assert result.outcome == "none_policy_one_step"


def test_none_policy_mechanism_repair_outcome() -> None:
    result = _classify(planner_question_policy="none", lowered_text="no marker", planner_next_move="deepen_mechanism")
    assert result.outcome == "none_policy_mechanism_repair"


def test_repair_misalignment_outcome() -> None:
    result = _classify(planner_next_move="repair_misalignment", has_question=True)
    assert result.outcome == "repair_misalignment"


def test_practice_forbidden_unsolicited_repair_outcome_and_patch() -> None:
    result = _classify(planner_practice_policy="forbidden", has_unsolicited_practice=True, planner_next_move="unrelated")
    assert result.outcome == "practice_forbidden_unsolicited_repair"
    assert result.last_debug_patch == {"template_leakage_repair_deferred_to_gate": True}


def test_practice_forbidden_last_debug_patch_key_order_survives_call_site_sequence() -> None:
    """Reproduces the exact call-site sequence from writer_agent.py:
    self.last_debug.update(patch) BEFORE self._set_final_answer_shape_debug(...).
    template_leakage_repair_deferred_to_gate must land before final_answer_shape.
    """
    result = _classify(planner_practice_policy="forbidden", has_unsolicited_practice=True, planner_next_move="unrelated")

    last_debug: dict = {}
    last_debug.update(result.last_debug_patch)
    last_debug["final_answer_shape"] = "template_repair_deferred_to_gate"

    keys = list(last_debug.keys())
    assert keys == ["template_leakage_repair_deferred_to_gate", "final_answer_shape"]


def test_group_two_priority_resolution_give_direct_step_wins_over_short_support() -> None:
    result = _classify(
        planner_question_policy="none",
        has_question=True,
        planner_next_move="give_direct_step",
        planner_answer_shape="short_support",
    )
    assert result.outcome == "no_question_one_step"


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(planner_next_move="repair_misalignment", has_question=True)
    first = _classify(**kwargs)
    second = _classify(**kwargs)
    assert first == second


def test_classifier_helper_module_has_no_self_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_enforce_slice6 as module

    source = inspect.getsource(module)
    assert "self." not in source
