from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice6 as slice6_module


def test_extract_call_llm_slice6_returns_expected_fields() -> None:
    ctx = {
        "final_answer_directive_json": '{"mode":"latest_turn"}',
        "writer_visible_final_answer_directive_json": '{"visible":true}',
        "final_answer_directive_version": "final_answer_directive_v9",
        "final_answer_current_user_request": "объясни термин",
        "final_answer_must_answer_source": "explicit_latest_turn",
        "final_answer_previous_must_answer_demoted": True,
        "final_answer_previous_must_answer": "older turn",
        "final_answer_explicit_continue_previous_detected": True,
        "final_answer_answer_target": "direct_answer",
        "final_answer_writer_contact_mode": "free_dialogue",
        "final_answer_diagnostic_center_role": "hidden",
        "final_answer_planner_role": "observer",
        "final_answer_active_line_role": "active_line_v2",
        "final_answer_diagnostic_card_role": "card_v3",
        "writer_first_prompt_assembly_enabled": True,
        "legacy_blocks_visible_to_writer": False,
        "legacy_blocks_source_signals_only": True,
        "legacy_constraints_suppressed_csv": "legacy_a,legacy_b",
        "writer_visible_advisory_summary": "нет вопросов",
        "writer_visible_practice_note": "без практики",
        "writer_grounding_authority_note": "latest-turn only",
        "writer_grounding_visibility_json": '{"grounding":"latest_turn"}',
    }

    result = slice6_module._extract_call_llm_slice6_final_answer_directive_and_legacy(ctx)

    assert result.final_answer_directive_json == '{"mode":"latest_turn"}'
    assert result.writer_visible_final_answer_directive_json == '{"visible":true}'
    assert result.final_answer_directive_version == "final_answer_directive_v9"
    assert result.final_answer_current_user_request == "объясни термин"
    assert result.final_answer_must_answer_source == "explicit_latest_turn"
    assert result.final_answer_previous_must_answer_demoted == "true"
    assert result.final_answer_previous_must_answer == "older turn"
    assert result.final_answer_explicit_continue_previous_detected == "true"
    assert result.final_answer_answer_target == "direct_answer"
    assert result.final_answer_writer_contact_mode == "free_dialogue"
    assert result.final_answer_diagnostic_center_role == "hidden"
    assert result.final_answer_planner_role == "observer"
    assert result.final_answer_active_line_role == "active_line_v2"
    assert result.final_answer_diagnostic_card_role == "card_v3"
    assert result.writer_first_prompt_assembly_enabled == "true"
    assert result.legacy_blocks_visible_to_writer == "false"
    assert result.legacy_blocks_source_signals_only == "true"
    assert result.legacy_constraints_suppressed_csv == "legacy_a,legacy_b"
    assert result.writer_visible_advisory_summary == "нет вопросов"
    assert result.writer_visible_practice_note == "без практики"
    assert result.writer_grounding_authority_note == "latest-turn only"
    assert result.writer_grounding_visibility_json == '{"grounding":"latest_turn"}'


def test_extract_call_llm_slice6_applies_literal_defaults() -> None:
    result = slice6_module._extract_call_llm_slice6_final_answer_directive_and_legacy({})

    assert result.final_answer_directive_json == "{}"
    assert result.writer_visible_final_answer_directive_json == "{}"
    assert result.final_answer_directive_version == "final_answer_directive_v1"
    assert result.final_answer_current_user_request == ""
    assert result.final_answer_must_answer_source == "latest_turn"
    assert result.final_answer_previous_must_answer_demoted == "false"
    assert result.final_answer_previous_must_answer == "none"
    assert result.final_answer_explicit_continue_previous_detected == "false"
    assert result.final_answer_answer_target == "latest_turn"
    assert result.final_answer_writer_contact_mode == "structured_answer"
    assert result.final_answer_diagnostic_center_role == "guided_legacy"
    assert result.final_answer_planner_role == "guided_legacy"
    assert result.final_answer_active_line_role == "guided_legacy"
    assert result.final_answer_diagnostic_card_role == "guided_legacy"
    assert result.writer_first_prompt_assembly_enabled == "false"
    assert result.legacy_blocks_visible_to_writer == "true"
    assert result.legacy_blocks_source_signals_only == "false"
    assert result.legacy_constraints_suppressed_csv == "none"
    assert result.writer_visible_advisory_summary == "нет"
    assert result.writer_visible_practice_note == "нет"
    assert result.writer_grounding_authority_note == "none"
    assert result.writer_grounding_visibility_json == "{}"


def test_extract_call_llm_slice6_keeps_original_or_fallback_behavior_for_empty_strings() -> None:
    result = slice6_module._extract_call_llm_slice6_final_answer_directive_and_legacy(
        {
            "final_answer_directive_version": "",
            "final_answer_current_user_request": "",
            "final_answer_previous_must_answer": "",
            "legacy_constraints_suppressed_csv": "",
            "writer_visible_advisory_summary": "",
            "writer_visible_practice_note": "",
            "writer_grounding_authority_note": "",
            "writer_grounding_visibility_json": "",
        }
    )

    assert result.final_answer_directive_version == "final_answer_directive_v1"
    assert result.final_answer_current_user_request == ""
    assert result.final_answer_previous_must_answer == "none"
    assert result.legacy_constraints_suppressed_csv == "none"
    assert result.writer_visible_advisory_summary == "нет"
    assert result.writer_visible_practice_note == "нет"
    assert result.writer_grounding_authority_note == "none"
    assert result.writer_grounding_visibility_json == "{}"
