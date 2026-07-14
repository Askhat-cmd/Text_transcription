from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice8 as slice8_module


def test_extract_call_llm_slice8_returns_expected_fields() -> None:
    ctx = {
        "response_planner_version": "response_planner_v9",
        "response_planner_enabled": True,
        "response_planner_next_move": "answer_directly",
        "response_planner_answer_shape": "medium_direct",
        "response_planner_response_depth": "medium",
        "response_planner_target_micro_shift": "reduce_shame",
        "response_planner_should_answer_directly": True,
        "response_planner_question_policy": "one_optional",
        "response_planner_practice_policy": "suppress",
        "response_planner_revoicing_policy": "gentle",
        "response_planner_continuity_policy": "continue_thread",
        "response_planner_safety_priority": True,
        "response_planner_must_include": ["one", " two ", "", "3"],
        "response_planner_must_avoid": ["", "lecture", "moralizing"],
        "response_planner_confidence": "0.75",
        "response_planner_rationale": "fits current ask",
        "dialogue_profile": "adaptive",
        "dialogue_expansion_requested": True,
        "dialogue_repair_and_expand_requested": True,
        "dialogue_active_concept": "душа",
        "dialogue_pragmatics_version": "dialogue_pragmatics_v7",
        "dialogue_pragmatics_short_utterance": True,
        "dialogue_pragmatics_short_type": "micro_followup",
        "dialogue_pragmatics_is_contextual_followup": True,
        "dialogue_pragmatics_offer_type": "clarification",
        "dialogue_pragmatics_inherited_intent": "continue_offer",
        "dialogue_pragmatics_should_answer_directly": True,
        "dialogue_pragmatics_should_not_ask_confirmation_again": True,
        "dialogue_pragmatics_repair_user_dissatisfaction": True,
        "dialogue_pragmatics_reason": "followup_after_answer",
    }

    result = slice8_module._extract_call_llm_slice8_response_planner_and_dialogue_pragmatics(
        ctx
    )

    assert result.response_planner_version == "response_planner_v9"
    assert result.response_planner_enabled == "true"
    assert result.response_planner_next_move == "answer_directly"
    assert result.response_planner_answer_shape == "medium_direct"
    assert result.response_planner_response_depth == "medium"
    assert result.response_planner_target_micro_shift == "reduce_shame"
    assert result.response_planner_should_answer_directly == "true"
    assert result.response_planner_question_policy == "one_optional"
    assert result.response_planner_practice_policy == "suppress"
    assert result.response_planner_revoicing_policy == "gentle"
    assert result.response_planner_continuity_policy == "continue_thread"
    assert result.response_planner_safety_priority == "true"
    assert result.response_planner_must_include == "one,  two , 3"
    assert result.response_planner_must_avoid == "lecture, moralizing"
    assert result.response_planner_confidence == 0.75
    assert result.response_planner_rationale == "fits current ask"
    assert result.dialogue_profile == "adaptive"
    assert result.dialogue_expansion_requested == "true"
    assert result.dialogue_repair_and_expand_requested == "true"
    assert result.dialogue_active_concept == "душа"
    assert result.dialogue_pragmatics_version == "dialogue_pragmatics_v7"
    assert result.dialogue_pragmatics_short_utterance == "true"
    assert result.dialogue_pragmatics_short_type == "micro_followup"
    assert result.dialogue_pragmatics_is_contextual_followup == "true"
    assert result.dialogue_pragmatics_offer_type == "clarification"
    assert result.dialogue_pragmatics_inherited_intent == "continue_offer"
    assert result.dialogue_pragmatics_should_answer_directly == "true"
    assert result.dialogue_pragmatics_should_not_ask_confirmation_again == "true"
    assert result.dialogue_pragmatics_repair_user_dissatisfaction == "true"
    assert result.dialogue_pragmatics_reason == "followup_after_answer"


def test_extract_call_llm_slice8_applies_literal_defaults() -> None:
    result = slice8_module._extract_call_llm_slice8_response_planner_and_dialogue_pragmatics(
        {}
    )

    assert result.response_planner_version == "response_planner_v1"
    assert result.response_planner_enabled == "false"
    assert result.response_planner_next_move == "continue_active_line"
    assert result.response_planner_answer_shape == "compact_direct"
    assert result.response_planner_response_depth == "short"
    assert result.response_planner_target_micro_shift == ""
    assert result.response_planner_should_answer_directly == "false"
    assert result.response_planner_question_policy == "none"
    assert result.response_planner_practice_policy == "forbidden"
    assert result.response_planner_revoicing_policy == "suppressed"
    assert result.response_planner_continuity_policy == "continue_active_line"
    assert result.response_planner_safety_priority == "false"
    assert result.response_planner_must_include == "none"
    assert result.response_planner_must_avoid == "none"
    assert result.response_planner_confidence == 0.0
    assert result.response_planner_rationale == ""
    assert result.dialogue_profile == "safe_guided"
    assert result.dialogue_expansion_requested == "false"
    assert result.dialogue_repair_and_expand_requested == "false"
    assert result.dialogue_active_concept == ""
    assert result.dialogue_pragmatics_version == "dialogue_pragmatics_v1"
    assert result.dialogue_pragmatics_short_utterance == "false"
    assert result.dialogue_pragmatics_short_type == "not_short"
    assert result.dialogue_pragmatics_is_contextual_followup == "false"
    assert result.dialogue_pragmatics_offer_type == "unknown"
    assert result.dialogue_pragmatics_inherited_intent == "continue_previous_offer"
    assert result.dialogue_pragmatics_should_answer_directly == "false"
    assert result.dialogue_pragmatics_should_not_ask_confirmation_again == "false"
    assert result.dialogue_pragmatics_repair_user_dissatisfaction == "false"
    assert result.dialogue_pragmatics_reason == "none"


def test_extract_call_llm_slice8_keeps_original_fallback_and_ctx_semantics() -> None:
    result = slice8_module._extract_call_llm_slice8_response_planner_and_dialogue_pragmatics(
        {
            "response_planner_version": "",
            "response_planner_next_move": "",
            "response_planner_answer_shape": "",
            "response_planner_response_depth": "",
            "response_planner_target_micro_shift": "",
            "response_planner_question_policy": "",
            "response_planner_practice_policy": "",
            "response_planner_revoicing_policy": "",
            "response_planner_continuity_policy": "",
            "response_planner_must_include": [],
            "response_planner_must_avoid": [],
            "response_planner_rationale": "",
            "dialogue_profile": "",
            "dialogue_active_concept": "",
            "dialogue_pragmatics_version": "",
            "dialogue_pragmatics_short_type": "",
            "dialogue_pragmatics_offer_type": "",
            "dialogue_pragmatics_inherited_intent": "",
            "dialogue_pragmatics_reason": "",
        }
    )

    assert result.response_planner_version == ""
    assert result.response_planner_next_move == "continue_active_line"
    assert result.response_planner_answer_shape == "compact_direct"
    assert result.response_planner_response_depth == "short"
    assert result.response_planner_target_micro_shift == ""
    assert result.response_planner_question_policy == "none"
    assert result.response_planner_practice_policy == "forbidden"
    assert result.response_planner_revoicing_policy == "suppressed"
    assert result.response_planner_continuity_policy == "continue_active_line"
    assert result.response_planner_must_include == "none"
    assert result.response_planner_must_avoid == "none"
    assert result.response_planner_rationale == ""
    assert result.dialogue_profile == "safe_guided"
    assert result.dialogue_active_concept == ""
    assert result.dialogue_pragmatics_version == ""
    assert result.dialogue_pragmatics_short_type == "not_short"
    assert result.dialogue_pragmatics_offer_type == "unknown"
    assert result.dialogue_pragmatics_inherited_intent == "continue_previous_offer"
    assert result.dialogue_pragmatics_reason == "none"
