from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice9 as slice9_module


def test_extract_call_llm_slice9_returns_expected_fields() -> None:
    ctx = {
        "retrieval_decision_version": "contextual_retrieval_gating_v9",
        "retrieval_action": "include_rag",
        "retrieval_rag_candidates_count": "6",
        "retrieval_rag_included_count": "2",
        "retrieval_rag_included_reason": "direct_match",
        "retrieval_rag_suppressed_reason": "none",
        "retrieval_writer_can_ignore_rag": False,
        "retrieval_rag_relevance": "high",
        "retrieval_inherited_topic": "душа",
        "retrieval_inherited_offer_type": "clarification",
        "final_answer_shape_profile": "direct_kb_grounded_compact",
        "final_answer_shape_profile_notes": [" one ", "", "two"],
    }
    human_like_answer_policy = {
        "enabled": True,
        "answer_style": "human_compact",
        "default_depth": "medium",
        "question_is_optional": True,
        "do_not_force_question_at_end": True,
        "do_not_force_practice_frame": True,
        "do_not_force_max_sentences": True,
        "respect_user_requested_format": True,
        "direct_answer_repair_when_user_complains": True,
        "support_answer_compactness": "strict_compact",
        "preferred_shape": "direct_then_bridge",
        "target_length_chars": 420,
        "avoid_mechanism_heavy_default": True,
        "prefer_direct_answer_first": True,
        "prefer_single_main_mechanism": True,
        "max_list_items": "2",
    }
    constraint_resolution = {
        "profile": "resolved_profile",
        "planner_authority": "strict",
        "overrule_reason": "must_answer_source",
    }

    result = slice9_module._extract_call_llm_slice9_retrieval_human_like_and_final_shape(
        ctx,
        human_like_answer_policy=human_like_answer_policy,
        repair_user_dissatisfaction=True,
        constraint_resolution=constraint_resolution,
        dialogue_profile="normalized_profile",
        overruled_constraints=["old_a", "old_b"],
    )

    assert result.retrieval_decision_version == "contextual_retrieval_gating_v9"
    assert result.retrieval_action == "include_rag"
    assert result.retrieval_rag_candidates_count == 6
    assert result.retrieval_rag_included_count == 2
    assert result.retrieval_rag_included_reason == "direct_match"
    assert result.retrieval_rag_suppressed_reason == "none"
    assert result.retrieval_writer_can_ignore_rag == "false"
    assert result.retrieval_rag_relevance == "high"
    assert result.retrieval_inherited_topic == "душа"
    assert result.retrieval_inherited_offer_type == "clarification"
    assert result.human_like_enabled == "true"
    assert result.human_like_answer_style == "human_compact"
    assert result.human_like_default_depth == "medium"
    assert result.human_like_question_is_optional == "true"
    assert result.human_like_do_not_force_question == "true"
    assert result.human_like_do_not_force_practice == "true"
    assert result.human_like_flexible_length_allowed == "true"
    assert result.human_like_respect_user_requested_format == "true"
    assert result.human_like_repair_user_dissatisfaction == "true"
    assert result.human_like_direct_answer_repair == "true"
    assert result.human_like_support_answer_compactness == "strict_compact"
    assert result.human_like_preferred_shape == "direct_then_bridge"
    assert result.human_like_target_length_chars == "420"
    assert result.human_like_avoid_mechanism_heavy_default == "true"
    assert result.human_like_prefer_direct_answer_first == "true"
    assert result.human_like_prefer_single_main_mechanism == "true"
    assert result.human_like_max_list_items == "2"
    assert result.final_answer_shape_profile == "direct_kb_grounded_compact"
    assert result.final_answer_shape_profile_notes_block == "- one\n- two"
    assert result.constraint_resolution_profile == "resolved_profile"
    assert result.constraint_resolution_planner_authority == "strict"
    assert result.constraint_resolution_overruled == "old_a, old_b"
    assert result.constraint_resolution_reason == "must_answer_source"


def test_extract_call_llm_slice9_applies_literal_defaults_and_fallbacks() -> None:
    result = slice9_module._extract_call_llm_slice9_retrieval_human_like_and_final_shape(
        {},
        human_like_answer_policy={},
        repair_user_dissatisfaction=False,
        constraint_resolution={},
        dialogue_profile="safe_guided_normalized",
        overruled_constraints=[],
    )

    assert result.retrieval_decision_version == "contextual_retrieval_gating_v1"
    assert result.retrieval_action == "none"
    assert result.retrieval_rag_candidates_count == 0
    assert result.retrieval_rag_included_count == 0
    assert result.retrieval_rag_included_reason == ""
    assert result.retrieval_rag_suppressed_reason == ""
    assert result.retrieval_writer_can_ignore_rag == "true"
    assert result.retrieval_rag_relevance == "unknown"
    assert result.retrieval_inherited_topic == ""
    assert result.retrieval_inherited_offer_type == "unknown"
    assert result.human_like_enabled == "false"
    assert result.human_like_answer_style == "guided_compact"
    assert result.human_like_default_depth == "short_to_medium"
    assert result.human_like_question_is_optional == "false"
    assert result.human_like_do_not_force_question == "false"
    assert result.human_like_do_not_force_practice == "false"
    assert result.human_like_flexible_length_allowed == "false"
    assert result.human_like_respect_user_requested_format == "false"
    assert result.human_like_repair_user_dissatisfaction == "false"
    assert result.human_like_direct_answer_repair == "false"
    assert result.human_like_support_answer_compactness == "adaptive"
    assert result.human_like_preferred_shape == "adaptive"
    assert result.human_like_target_length_chars == ""
    assert result.human_like_avoid_mechanism_heavy_default == "false"
    assert result.human_like_prefer_direct_answer_first == "false"
    assert result.human_like_prefer_single_main_mechanism == "false"
    assert result.human_like_max_list_items == "0"
    assert result.final_answer_shape_profile == "adaptive_current_pipeline"
    assert (
        result.final_answer_shape_profile_notes_block
        == "- Follow the current answer obligation and stay direct."
    )
    assert result.constraint_resolution_profile == "safe_guided_normalized"
    assert result.constraint_resolution_planner_authority == "guided"
    assert result.constraint_resolution_overruled == "none"
    assert result.constraint_resolution_reason == "none"


def test_extract_call_llm_slice9_preserves_local_dialogue_profile_and_passthrough_semantics() -> None:
    result = slice9_module._extract_call_llm_slice9_retrieval_human_like_and_final_shape(
        {
            "retrieval_decision_version": "",
            "retrieval_action": "",
            "retrieval_rag_relevance": "",
            "retrieval_inherited_offer_type": "",
            "final_answer_shape_profile": "",
            "final_answer_shape_profile_notes": [],
        },
        human_like_answer_policy={
            "answer_style": "",
            "default_depth": "",
            "support_answer_compactness": "",
            "preferred_shape": "",
            "target_length_chars": "",
            "max_list_items": "",
        },
        repair_user_dissatisfaction=False,
        constraint_resolution={"profile": "", "planner_authority": "", "overrule_reason": ""},
        dialogue_profile="normalized_from_slice1",
        overruled_constraints=[],
    )

    assert result.retrieval_decision_version == "contextual_retrieval_gating_v1"
    assert result.retrieval_action == "none"
    assert result.retrieval_rag_relevance == "unknown"
    assert result.retrieval_inherited_offer_type == "unknown"
    assert result.human_like_answer_style == "guided_compact"
    assert result.human_like_default_depth == "short_to_medium"
    assert result.human_like_support_answer_compactness == "adaptive"
    assert result.human_like_preferred_shape == "adaptive"
    assert result.human_like_target_length_chars == ""
    assert result.human_like_max_list_items == "0"
    assert result.final_answer_shape_profile == "adaptive_current_pipeline"
    assert result.constraint_resolution_profile == "normalized_from_slice1"
    assert result.constraint_resolution_planner_authority == "guided"
    assert result.constraint_resolution_reason == "none"
