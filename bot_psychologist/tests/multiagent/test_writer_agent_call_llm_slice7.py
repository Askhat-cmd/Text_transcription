from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice7 as slice7_module


def test_extract_call_llm_slice7_returns_expected_fields() -> None:
    ctx = {
        "fresh_chat_context_policy_version": "fresh_chat_context_policy_v9",
        "fresh_chat_is_new_chat": True,
        "fresh_chat_turn_index": "4",
        "fresh_chat_is_greeting_or_contact": True,
        "fresh_chat_cross_session_memory_allowed": False,
        "fresh_chat_cross_session_memory_reason": "contact_only",
        "fresh_chat_active_context_source": "cross_session",
        "writer_context_package_version": "writer_context_package_v9",
        "writer_context_recent_turns_count": "8",
        "writer_context_profile_present": True,
        "writer_context_rag_candidates_count": "13",
        "writer_context_rag_for_writer_count": "5",
        "practice_rewrite_applied": True,
        "active_line_version": "active_line_v7",
        "active_line_text": "держим одну линию",
        "active_line_user_intent": "ask_concept",
        "active_line_continuity_mode": "restart_line",
        "active_line_next_meaningful_move": "answer_term",
        "active_line_should_continue_line": False,
        "active_line_should_ask_question": True,
        "active_line_should_offer_practice": True,
        "active_line_revoicing_allowed": True,
        "active_line_revoicing_style": "gentle",
        "active_line_repair_mode": "clarify",
        "active_line_practice_suppression_active": True,
    }

    result = slice7_module._extract_call_llm_slice7_fresh_chat_and_active_line(ctx)

    assert result.fresh_chat_context_policy_version == "fresh_chat_context_policy_v9"
    assert result.fresh_chat_is_new_chat == "true"
    assert result.fresh_chat_turn_index == 4
    assert result.fresh_chat_is_greeting_or_contact == "true"
    assert result.fresh_chat_cross_session_memory_allowed == "false"
    assert result.fresh_chat_cross_session_memory_reason == "contact_only"
    assert result.fresh_chat_active_context_source == "cross_session"
    assert result.writer_context_package_version == "writer_context_package_v9"
    assert result.writer_context_recent_turns_count == 8
    assert result.writer_context_profile_present == "true"
    assert result.writer_context_rag_candidates_count == 13
    assert result.writer_context_rag_for_writer_count == 5
    assert result.practice_rewrite_applied == "true"
    assert result.active_line_version == "active_line_v7"
    assert result.active_line_text == "держим одну линию"
    assert result.active_line_user_intent == "ask_concept"
    assert result.active_line_continuity_mode == "restart_line"
    assert result.active_line_next_meaningful_move == "answer_term"
    assert result.active_line_should_continue_line == "false"
    assert result.active_line_should_ask_question == "true"
    assert result.active_line_should_offer_practice == "true"
    assert result.active_line_revoicing_allowed == "true"
    assert result.active_line_revoicing_style == "gentle"
    assert result.active_line_repair_mode == "clarify"
    assert result.active_line_practice_suppression_active == "true"


def test_extract_call_llm_slice7_applies_literal_defaults() -> None:
    result = slice7_module._extract_call_llm_slice7_fresh_chat_and_active_line({})

    assert result.fresh_chat_context_policy_version == "fresh_chat_context_policy_v1"
    assert result.fresh_chat_is_new_chat == "false"
    assert result.fresh_chat_turn_index == 1
    assert result.fresh_chat_is_greeting_or_contact == "false"
    assert result.fresh_chat_cross_session_memory_allowed == "true"
    assert result.fresh_chat_cross_session_memory_reason == ""
    assert result.fresh_chat_active_context_source == "current_chat_only"
    assert result.writer_context_package_version == "writer_context_package_v1"
    assert result.writer_context_recent_turns_count == 0
    assert result.writer_context_profile_present == "false"
    assert result.writer_context_rag_candidates_count == 0
    assert result.writer_context_rag_for_writer_count == 0
    assert result.practice_rewrite_applied == "false"
    assert result.active_line_version == "active_line_v1"
    assert result.active_line_text == ""
    assert result.active_line_user_intent == "unknown"
    assert result.active_line_continuity_mode == "continue_existing_line"
    assert result.active_line_next_meaningful_move == ""
    assert result.active_line_should_continue_line == "true"
    assert result.active_line_should_ask_question == "false"
    assert result.active_line_should_offer_practice == "false"
    assert result.active_line_revoicing_allowed == "false"
    assert result.active_line_revoicing_style == "suppressed"
    assert result.active_line_repair_mode == ""
    assert result.active_line_practice_suppression_active == "false"


def test_extract_call_llm_slice7_keeps_original_or_fallback_behavior_for_empty_strings() -> None:
    result = slice7_module._extract_call_llm_slice7_fresh_chat_and_active_line(
        {
            "fresh_chat_context_policy_version": "",
            "fresh_chat_cross_session_memory_reason": "",
            "fresh_chat_active_context_source": "",
            "writer_context_package_version": "",
            "active_line_version": "",
            "active_line_text": "",
            "active_line_user_intent": "",
            "active_line_continuity_mode": "",
            "active_line_next_meaningful_move": "",
            "active_line_revoicing_style": "",
            "active_line_repair_mode": "",
        }
    )

    assert result.fresh_chat_context_policy_version == "fresh_chat_context_policy_v1"
    assert result.fresh_chat_cross_session_memory_reason == ""
    assert result.fresh_chat_active_context_source == "current_chat_only"
    assert result.writer_context_package_version == "writer_context_package_v1"
    assert result.active_line_version == ""
    assert result.active_line_text == ""
    assert result.active_line_user_intent == "unknown"
    assert result.active_line_continuity_mode == ""
    assert result.active_line_next_meaningful_move == ""
    assert result.active_line_revoicing_style == "suppressed"
    assert result.active_line_repair_mode == ""
