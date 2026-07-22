from __future__ import annotations

import copy
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_20_enforce_compliance_mapping as baseline_runner
from TO_DO_LIST.tools import run_prd_047_42_apply_22_enforce_slice2 as runner
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.agents.writer_agent_enforce_slice1 import _extract_enforce_slice1_prelude
from bot_agent.multiagent.agents.writer_agent_enforce_slice2 import (
    EnforceSlice2SecondPreludeResult,
    _extract_enforce_slice2_second_prelude_and_close_gently,
)


def _case(name: str) -> dict:
    return {case["name"]: case for case in baseline_runner.build_cases()}[name]


def _slice1_result_for_case(name: str):
    case = _case(name)
    contract = copy.deepcopy(case["contract"])
    text = str(case["response_text"] or "").strip()
    return _extract_enforce_slice1_prelude(contract, text=text), text


def test_enforce_slice2_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(EnforceSlice2SecondPreludeResult)] == runner.EXPECTED_FIELD_ORDER


def test_close_gently_branch_patch_has_exactly_five_keys_in_order_and_no_extra_locals() -> None:
    slice1_result, text = _slice1_result_for_case("close_gently_obligation")

    result = _extract_enforce_slice2_second_prelude_and_close_gently(
        slice1_result.ctx,
        text=text,
        lowered_user=slice1_result.lowered_user,
        lowered_text=slice1_result.lowered_text,
        planner_question_policy=slice1_result.planner_question_policy,
        planner_practice_policy=slice1_result.planner_practice_policy,
        planner_answer_shape=slice1_result.planner_answer_shape,
        writer_contact_mode=slice1_result.writer_contact_mode,
        direct_concrete_request=slice1_result.direct_concrete_request,
        application_request=slice1_result.application_request,
        explicit_answer_need=slice1_result.explicit_answer_need,
        user_message=slice1_result.user_message,
        practice_markers=(),
        known_concept_clarification_markers=(),
        external_surveillance_markers=(),
    )

    assert result.close_gently_triggered is True
    assert list(result.last_debug_patch.keys()) == runner.TRUE_BRANCH_LAST_DEBUG_KEYS
    assert "final_answer_shape" not in result.last_debug_patch
    assert "answer_fit_evaluator" not in result.last_debug_patch
    assert result.user_mechanism_request is None
    assert result.answer_fit is None


def test_false_branch_patch_has_exactly_six_keys_in_order_with_answer_fit_evaluator_last() -> None:
    slice1_result, text = _slice1_result_for_case("bounded_practice_be_strong")

    result = _extract_enforce_slice2_second_prelude_and_close_gently(
        slice1_result.ctx,
        text=text,
        lowered_user=slice1_result.lowered_user,
        lowered_text=slice1_result.lowered_text,
        planner_question_policy=slice1_result.planner_question_policy,
        planner_practice_policy=slice1_result.planner_practice_policy,
        planner_answer_shape=slice1_result.planner_answer_shape,
        writer_contact_mode=slice1_result.writer_contact_mode,
        direct_concrete_request=slice1_result.direct_concrete_request,
        application_request=slice1_result.application_request,
        explicit_answer_need=slice1_result.explicit_answer_need,
        user_message=slice1_result.user_message,
        practice_markers=WriterAgent._PRACTICE_MARKERS,
        known_concept_clarification_markers=(),
        external_surveillance_markers=(),
    )

    assert result.close_gently_triggered is False
    assert list(result.last_debug_patch.keys()) == runner.FALSE_BRANCH_LAST_DEBUG_KEYS
    assert list(result.last_debug_patch.keys())[-1] == "answer_fit_evaluator"
    assert result.user_mechanism_request is not None
    assert result.answer_fit is not None


def test_integration_true_branch_places_final_answer_shape_sixth_not_first_in_last_debug() -> None:
    case = _case("close_gently_obligation")
    contract = copy.deepcopy(case["contract"])
    agent = WriterAgent(client=object(), model="direct-test-model")

    result = agent._enforce_answer_compliance(case["response_text"], contract)

    assert result == agent._build_gentle_close_reply()
    keys = list(agent.last_debug.keys())
    slice2_keys = [key for key in keys if key in set(runner.TRUE_BRANCH_FULL_LAST_DEBUG_TAIL)]
    assert slice2_keys == runner.TRUE_BRANCH_FULL_LAST_DEBUG_TAIL
    assert keys.index("final_answer_shape") == keys.index("canned_step_disallowed") + 1
    assert keys.index("final_answer_shape") != 0


def test_practice_markers_parameter_is_used_instead_of_module_level_name() -> None:
    slice1_result, text = _slice1_result_for_case("template_leakage_practice_forbidden")

    result_with_real_markers = _extract_enforce_slice2_second_prelude_and_close_gently(
        slice1_result.ctx,
        text=text,
        lowered_user=slice1_result.lowered_user,
        lowered_text=slice1_result.lowered_text,
        planner_question_policy=slice1_result.planner_question_policy,
        planner_practice_policy=slice1_result.planner_practice_policy,
        planner_answer_shape=slice1_result.planner_answer_shape,
        writer_contact_mode=slice1_result.writer_contact_mode,
        direct_concrete_request=slice1_result.direct_concrete_request,
        application_request=slice1_result.application_request,
        explicit_answer_need=slice1_result.explicit_answer_need,
        user_message=slice1_result.user_message,
        practice_markers=WriterAgent._PRACTICE_MARKERS,
        known_concept_clarification_markers=(),
        external_surveillance_markers=(),
    )
    assert result_with_real_markers.has_unsolicited_practice is True

    result_with_empty_markers = _extract_enforce_slice2_second_prelude_and_close_gently(
        slice1_result.ctx,
        text=text,
        lowered_user=slice1_result.lowered_user,
        lowered_text=slice1_result.lowered_text,
        planner_question_policy=slice1_result.planner_question_policy,
        planner_practice_policy=slice1_result.planner_practice_policy,
        planner_answer_shape=slice1_result.planner_answer_shape,
        writer_contact_mode=slice1_result.writer_contact_mode,
        direct_concrete_request=slice1_result.direct_concrete_request,
        application_request=slice1_result.application_request,
        explicit_answer_need=slice1_result.explicit_answer_need,
        user_message=slice1_result.user_message,
        practice_markers=(),
        known_concept_clarification_markers=(),
        external_surveillance_markers=(),
    )
    assert result_with_empty_markers.has_unsolicited_practice is False
