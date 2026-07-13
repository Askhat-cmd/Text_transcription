from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice4 as slice4_module


def test_extract_call_llm_slice4_returns_expected_policy_and_dialogue_state_fields() -> None:
    ctx = {
        "unified_dialogue_policy_version": "unified_dialogue_policy_v9",
        "unified_active_profile_alias": "mvp_free_dialogue",
        "profile_preset": "mvp_free_dialogue",
        "unified_effective_writer_autonomy": "high",
        "unified_effective_safety_floor": "soft",
        "unified_legacy_blocks_visible_to_writer": True,
        "unified_legacy_blocks_source_signals_only": False,
        "unified_hard_boundaries_csv": "safety, truth",
        "unified_soft_guidance_csv": "state, planner",
        "dialogue_act": "answer_known_concept",
        "dialogue_act_confidence": "0.75",
        "dialogue_act_evidence": "latest_turn",
        "last_assistant_offer_open": True,
        "last_assistant_offer_type": "example",
        "last_assistant_offer_summary": "пример про нейросталкинг",
        "unanswered_question_answer_required": True,
        "unanswered_question_status": "pending",
        "unanswered_question_summary": "что именно делать",
        "dialogue_style_tone": "warm",
        "dialogue_style_length_preference": "long",
        "dialogue_style_complexity_preference": "simple",
        "dialogue_style_avoid_csv": "cliche, jargon",
        "answer_obligation": "answer_direct_question",
        "answer_obligation_shape": "direct_explanation",
        "answer_obligation_depth": "deep",
        "answer_obligation_question_policy": "none",
        "answer_obligation_source": "latest_turn",
        "diagnostic_card_summary": {"main": "freeze"},
        "diagnostic_card_avoid_list": ["pressure", "diagnosis"],
        "diagnostic_card_risk_flags": ["panic"],
        "writer_move_instruction_summary": {"kind": "dict_kept_as_is"},
        "writer_move_must_do": ["answer directly"],
        "writer_move_must_not_do": ["ask definition"],
        "user_profile_patterns": ["control", "freeze"],
        "user_profile_values": ["clarity"],
    }
    context_meta = {
        "context_budget_chars": "2800",
        "context_truncated": True,
        "preserved_recent_turns_count": "3",
        "older_context_omitted_chars": "150",
    }

    result = slice4_module._extract_call_llm_slice4_policy_and_dialogue_state(
        ctx,
        context_meta,
        "safe_guided",
    )

    assert result.unified_dialogue_policy_version == "unified_dialogue_policy_v9"
    assert result.unified_active_profile_alias == "mvp_free_dialogue"
    assert result.unified_legacy_blocks_visible_to_writer == "true"
    assert result.unified_legacy_blocks_source_signals_only == "false"
    assert result.dialogue_act_confidence == 0.75
    assert result.unanswered_question_answer_required == "true"
    assert result.diagnostic_card_avoid == "pressure, diagnosis"
    assert result.diagnostic_card_risk_flags == "panic"
    assert result.writer_move_instruction_summary == {"kind": "dict_kept_as_is"}
    assert result.context_budget_chars == 2800
    assert result.context_truncated == "true"
    assert result.preserved_recent_turns_count == 3
    assert result.older_context_omitted_chars == 150
    assert result.user_profile_patterns == "control, freeze"
    assert result.user_profile_values == "clarity"


def test_extract_call_llm_slice4_applies_defaults_and_falsey_fallbacks() -> None:
    result = slice4_module._extract_call_llm_slice4_policy_and_dialogue_state(
        {
            "diagnostic_card_summary": None,
            "diagnostic_card_avoid_list": [],
            "diagnostic_card_risk_flags": [],
            "writer_move_instruction_summary": "",
            "writer_move_must_do": [],
            "writer_move_must_not_do": [],
            "user_profile_patterns": [],
            "user_profile_values": [],
        },
        {},
        "safe_guided",
    )

    assert result.unified_dialogue_policy_version == "unified_dialogue_policy_v2"
    assert result.unified_active_profile_alias == "safe_guided"
    assert result.profile_preset == "safe_guided"
    assert result.unified_legacy_blocks_visible_to_writer == "false"
    assert result.unified_legacy_blocks_source_signals_only == "true"
    assert result.dialogue_act == "unknown"
    assert result.dialogue_act_confidence == 0.0
    assert result.dialogue_act_evidence == "none"
    assert result.answer_obligation == "continue_thread"
    assert result.answer_obligation_shape == "structured_explanation"
    assert result.answer_obligation_depth == "medium"
    assert result.answer_obligation_question_policy == "optional_none"
    assert result.answer_obligation_source == "none"
    assert result.diagnostic_card_summary == "нет"
    assert result.diagnostic_card_avoid == "нет"
    assert result.diagnostic_card_risk_flags == "нет"
    assert result.writer_move_instruction_summary == "нет"
    assert result.writer_move_must_do == "нет"
    assert result.writer_move_must_not_do == "нет"
    assert result.context_budget_chars == 0
    assert result.context_truncated == "false"
    assert result.preserved_recent_turns_count == 0
    assert result.older_context_omitted_chars == 0
    assert result.user_profile_patterns == "нет"
    assert result.user_profile_values == "нет"


def test_extract_call_llm_slice4_preserves_writer_move_instruction_summary_without_str() -> None:
    sentinel = ["keep", "raw", 7]

    result = slice4_module._extract_call_llm_slice4_policy_and_dialogue_state(
        {
            "writer_move_instruction_summary": sentinel,
            "user_profile_patterns": ["p1"],
            "user_profile_values": ["v1"],
        },
        {},
        "safe_guided",
    )

    assert result.writer_move_instruction_summary is sentinel
