from __future__ import annotations

import copy
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_20_enforce_compliance_mapping as baseline_runner
from TO_DO_LIST.tools import run_prd_047_42_apply_21_enforce_slice1 as runner
from bot_agent.multiagent.agents.writer_agent_enforce_slice1 import (
    EnforceSlice1PreludeResult,
    _extract_enforce_slice1_prelude,
)


def test_enforce_slice1_dataclass_field_order_matches_apply20_section_a() -> None:
    assert [field.name for field in dataclasses.fields(EnforceSlice1PreludeResult)] == runner.EXPECTED_FIELD_ORDER


def test_extract_enforce_slice1_preserves_representative_values_patch_order_and_contract() -> None:
    case_lookup = {case["name"]: case for case in baseline_runner.build_cases()}
    case = case_lookup["greeting_gate_feedback_repair"]
    contract = copy.deepcopy(case["contract"])
    before_dict = copy.deepcopy(contract.to_dict())
    before_ctx = contract.to_prompt_context()

    result = _extract_enforce_slice1_prelude(contract, text=case["response_text"])

    assert result.ctx == before_ctx
    assert result.user_message == "Привет! Как перестать наступать на одни и те же грабли?"
    assert result.lowered_user.startswith("привет!")
    assert result.dialogue_profile == "safe_guided"
    assert result.expansion_requested is False
    assert result.repair_and_expand_requested is False
    assert result.response_planner["next_move"] == "deepen_mechanism"
    assert result.planner_next_move == "deepen_mechanism"
    assert result.planner_answer_shape == "mechanism_explanation"
    assert result.planner_question_policy == "optional_none"
    assert result.planner_practice_policy == "forbidden"
    assert result.planner_safety_priority is False
    assert result.explicit_answer_need is True
    assert result.direct_concrete_request is False
    assert result.summary_request is False
    assert result.sarcasm_or_negative_feedback is False
    assert result.application_request is False
    assert result.practice_overview_requested is False
    assert result.lowered_text == case["response_text"].lower()
    assert result.final_answer_directive["acceptance_gate_feedback"]["failed_checks"] == [
        "greeting_answered_with_mechanism_explanation"
    ]
    assert result.gate_failed_checks == {"greeting_answered_with_mechanism_explanation"}
    assert list(result.last_debug_patch.keys()) == runner.EXPECTED_LAST_DEBUG_KEYS
    assert result.last_debug_patch["compliance_planner_next_move"] == "deepen_mechanism"
    assert result.last_debug_patch["compliance_planner_answer_shape"] == "mechanism_explanation"
    assert result.last_debug_patch["human_like_answer_policy_enabled"] is False
    assert result.last_debug_patch["explicit_answer_need"] is True
    assert result.last_debug_patch["repair_user_dissatisfaction"] is False
    assert result.last_debug_patch["sarcasm_or_negative_feedback"] is False
    assert result.last_debug_patch["overruled_constraints"] == []
    assert contract.to_dict() == before_dict
