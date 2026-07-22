from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_26_enforce_slice5 as runner
from bot_agent.multiagent.agents.writer_agent import _LOW_RESOURCE_NO_PRACTICE_MARKERS
from bot_agent.multiagent.agents.writer_agent_enforce_slice5 import (
    EnforceSlice5Result,
    _classify_enforce_slice5_block_a,
)


def _classify(**overrides):
    kwargs = dict(
        text="ok text",
        user_message="ok",
        lowered_user="ok",
        lowered_text="ok text",
        practice_allowed=True,
        should_answer_directly=False,
        is_greeting=False,
        has_unsolicited_practice=False,
        has_question=False,
        active_line_intent="unknown",
        planner_safety_priority=False,
        planner_next_move="continue_active_line",
        planner_answer_shape="compact_direct",
        user_repair_signal=False,
        low_resource_no_practice_markers=_LOW_RESOURCE_NO_PRACTICE_MARKERS,
    )
    kwargs.update(overrides)
    return _classify_enforce_slice5_block_a(**kwargs)


def test_enforce_slice5_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(EnforceSlice5Result)] == runner.EXPECTED_FIELD_ORDER


def test_all_fifteen_outcomes_are_declared() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {
        "not_matched",
        "greeting_path",
        "low_resource_no_practice",
        "thanks_close",
        "safety_priority_has_question",
        "give_short_support_primary",
        "give_short_support_len_or_flags",
        "stabilize_safety_len_or_question",
        "stabilize_safety_markers",
        "close_gently",
        "give_short_support_markers",
        "clarify_one_point_zero_questions",
        "clarify_one_point_multi_questions",
        "clarify_one_point_long",
        "user_repair_signal",
    }
    assert len(runner.EXPECTED_OUTCOMES) == 15


def test_not_matched_when_nothing_applies() -> None:
    assert _classify().outcome == "not_matched"


def test_greeting_path_outcome() -> None:
    result = _classify(practice_allowed=False, is_greeting=True)
    assert result.outcome == "greeting_path"


def test_low_resource_no_practice_outcome() -> None:
    result = _classify(lowered_user=_LOW_RESOURCE_NO_PRACTICE_MARKERS[0], has_unsolicited_practice=True)
    assert result.outcome == "low_resource_no_practice"


def test_thanks_close_outcome() -> None:
    result = _classify(active_line_intent="thanks_close", has_unsolicited_practice=True)
    assert result.outcome == "thanks_close"


def test_safety_priority_has_question_outcome() -> None:
    result = _classify(planner_safety_priority=True, has_question=True)
    assert result.outcome == "safety_priority_has_question"


def test_give_short_support_primary_outcome() -> None:
    result = _classify(planner_next_move="give_short_support")
    assert result.outcome == "give_short_support_primary"


def test_give_short_support_via_answer_shape_also_hits_primary() -> None:
    result = _classify(planner_next_move="continue_active_line", planner_answer_shape="short_support")
    assert result.outcome == "give_short_support_primary"


def test_stabilize_safety_len_or_question_outcome() -> None:
    result = _classify(planner_next_move="stabilize_safety", has_question=True)
    assert result.outcome == "stabilize_safety_len_or_question"


def test_stabilize_safety_markers_outcome() -> None:
    result = _classify(planner_next_move="stabilize_safety", lowered_text="в тексте есть механизм")
    assert result.outcome == "stabilize_safety_markers"


def test_close_gently_outcome() -> None:
    result = _classify(planner_next_move="close_gently", has_question=True)
    assert result.outcome == "close_gently"


def test_clarify_one_point_zero_questions_outcome() -> None:
    result = _classify(planner_next_move="clarify_one_point", text="no question mark here")
    assert result.outcome == "clarify_one_point_zero_questions"


def test_clarify_one_point_multi_questions_outcome_computes_return_text() -> None:
    result = _classify(planner_next_move="clarify_one_point", text="First question? Second question?")
    assert result.outcome == "clarify_one_point_multi_questions"
    assert result.return_text == "First question?"


def test_clarify_one_point_multi_questions_return_text_varies_with_input() -> None:
    result = _classify(planner_next_move="clarify_one_point", text="Alpha? Beta? Gamma?")
    assert result.return_text == "Alpha?"


def test_clarify_one_point_long_outcome() -> None:
    long_text = "?" + "x" * 330
    result = _classify(planner_next_move="clarify_one_point", text=long_text)
    assert result.outcome == "clarify_one_point_long"


def test_user_repair_signal_outcome() -> None:
    result = _classify(user_repair_signal=True)
    assert result.outcome == "user_repair_signal"


def test_give_short_support_primary_wins_order_over_len_or_flags_and_markers_even_when_both_formally_true() -> None:
    """give_short_support_len_or_flags/markers share the exact same gating
    predicate (`planner_next_move == "give_short_support"`) as
    give_short_support_primary, whose own condition is a strict OR-superset
    of theirs. This means, by construction (preserved verbatim from the
    original code), those two outcomes can never fire in practice -- primary
    always wins first. This is not a defect introduced by the classifier;
    it is the same dead branch the original cascade already had. This test
    proves the order guarantee the PRD explicitly requires.
    """
    result = _classify(
        planner_next_move="give_short_support",
        text="x" * 300,
        has_question=True,
        has_unsolicited_practice=True,
        lowered_text="механизм теория стратегия",
    )
    assert result.outcome == "give_short_support_primary"


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(planner_next_move="stabilize_safety", has_question=True)
    first = _classify(**kwargs)
    second = _classify(**kwargs)
    assert first == second


def test_classifier_helper_module_has_no_self_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_enforce_slice5 as module

    source = inspect.getsource(module)
    assert "self." not in source
