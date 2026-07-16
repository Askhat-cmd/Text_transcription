from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice10 as slice10_module
from bot_agent.multiagent.prompt_constraint_section import (
    format_prompt_constraint_section_v1,
)


EXPECTED_PATCH_KEYS = [
    "user_prompt",
    "prompt_constraint_pilot_activation_mode",
    "prompt_constraint_pilot_applied",
    "prompt_constraint_pilot_blocked_reasons",
    "prompt_constraint_pilot_prompt_section_chars",
    "context_budget_chars",
    "context_truncated",
    "preserved_recent_turns_count",
    "older_context_omitted_chars",
    "human_like_answer_policy_enabled",
    "explicit_answer_need",
    "repair_user_dissatisfaction",
    "sarcasm_or_negative_feedback",
    "overruled_constraints",
    "dialogue_pragmatics_contextual_followup",
    "dialogue_pragmatics_offer_type",
    "retrieval_action",
    "retrieval_rag_included_count",
]


def test_apply_call_llm_slice10_keeps_user_prompt_when_decision_is_none() -> None:
    original_prompt = "user prompt"
    overruled_constraints = ["one", "two"]

    result = (
        slice10_module._apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping(
            {
                "dialogue_pragmatics_is_contextual_followup": True,
                "dialogue_pragmatics_offer_type": "clarify",
                "retrieval_action": "include_rag",
                "retrieval_rag_included_count": "2",
            },
            user_prompt=original_prompt,
            prompt_constraint_decision=None,
            context_meta={
                "context_budget_chars": "1200",
                "context_truncated": True,
                "preserved_recent_turns_count": "3",
                "older_context_omitted_chars": "88",
            },
            human_like_answer_policy={"enabled": True},
            explicit_answer_need=True,
            repair_user_dissatisfaction=False,
            sarcasm_or_negative_feedback=True,
            overruled_constraints=overruled_constraints,
        )
    )

    assert result.user_prompt == original_prompt
    assert list(result.last_debug_patch.keys()) == EXPECTED_PATCH_KEYS
    assert result.last_debug_patch["user_prompt"] == original_prompt
    assert result.last_debug_patch["prompt_constraint_pilot_activation_mode"] == "disabled"
    assert result.last_debug_patch["prompt_constraint_pilot_applied"] is False
    assert result.last_debug_patch["prompt_constraint_pilot_blocked_reasons"] == []
    assert result.last_debug_patch["prompt_constraint_pilot_prompt_section_chars"] == 0
    assert result.last_debug_patch["context_budget_chars"] == 1200
    assert result.last_debug_patch["context_truncated"] is True
    assert result.last_debug_patch["preserved_recent_turns_count"] == 3
    assert result.last_debug_patch["older_context_omitted_chars"] == 88
    assert result.last_debug_patch["human_like_answer_policy_enabled"] is True
    assert result.last_debug_patch["explicit_answer_need"] is True
    assert result.last_debug_patch["repair_user_dissatisfaction"] is False
    assert result.last_debug_patch["sarcasm_or_negative_feedback"] is True
    assert result.last_debug_patch["overruled_constraints"] is overruled_constraints
    assert result.last_debug_patch["dialogue_pragmatics_contextual_followup"] is True
    assert result.last_debug_patch["dialogue_pragmatics_offer_type"] == "clarify"
    assert result.last_debug_patch["retrieval_action"] == "include_rag"
    assert result.last_debug_patch["retrieval_rag_included_count"] == 2


def test_apply_call_llm_slice10_appends_prompt_section_when_decision_applies() -> None:
    decision = {
        "activation_mode": "test_apply",
        "apply_to_writer_prompt": True,
        "blocked_reasons": ["none"],
        "candidate_constraints": {
            "depth_limit": "short",
            "max_questions": 1,
            "max_concepts": 2,
            "must_do": ["answer directly"],
            "must_not_do": ["lecture", "exercise"],
            "kb_usage_mode": "internal_lens_only",
            "must_not_quote_source": True,
        },
    }
    prompt_section = format_prompt_constraint_section_v1(decision)
    assert prompt_section

    result = (
        slice10_module._apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping(
            {},
            user_prompt="user prompt",
            prompt_constraint_decision=decision,
            context_meta={},
            human_like_answer_policy={},
            explicit_answer_need=False,
            repair_user_dissatisfaction=True,
            sarcasm_or_negative_feedback=False,
            overruled_constraints=[],
        )
    )

    assert result.user_prompt == f"user prompt\n\n{prompt_section}"
    assert list(result.last_debug_patch.keys()) == EXPECTED_PATCH_KEYS
    assert result.last_debug_patch["user_prompt"] == result.user_prompt
    assert result.last_debug_patch["prompt_constraint_pilot_activation_mode"] == "test_apply"
    assert result.last_debug_patch["prompt_constraint_pilot_applied"] is True
    assert result.last_debug_patch["prompt_constraint_pilot_blocked_reasons"] == ["none"]
    assert result.last_debug_patch["prompt_constraint_pilot_prompt_section_chars"] == len(
        prompt_section
    )
    assert result.last_debug_patch["human_like_answer_policy_enabled"] is False
    assert result.last_debug_patch["repair_user_dissatisfaction"] is True
    assert result.last_debug_patch["dialogue_pragmatics_offer_type"] == "unknown"
    assert result.last_debug_patch["retrieval_action"] == "none"
    assert result.last_debug_patch["retrieval_rag_included_count"] == 0


def test_apply_call_llm_slice10_keeps_is_not_none_vs_isinstance_asymmetry() -> None:
    class DecisionLike:
        def get(self, key: str, default: object = None) -> object:
            if key == "activation_mode":
                return "test_apply"
            if key == "apply_to_writer_prompt":
                return True
            if key == "candidate_constraints":
                return {
                    "depth_limit": "short",
                    "max_questions": 1,
                    "max_concepts": 1,
                    "must_do": ["answer"],
                    "must_not_do": [],
                    "kb_usage_mode": "none",
                    "must_not_quote_source": True,
                }
            return default

    decision = DecisionLike()

    result = (
        slice10_module._apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping(
            {},
            user_prompt="u",
            prompt_constraint_decision=decision,  # type: ignore[arg-type]
            context_meta={},
            human_like_answer_policy={},
            explicit_answer_need=False,
            repair_user_dissatisfaction=False,
            sarcasm_or_negative_feedback=False,
            overruled_constraints=[],
        )
    )

    assert result.user_prompt == "u"
    assert result.last_debug_patch["prompt_constraint_pilot_activation_mode"] == "disabled"
    assert result.last_debug_patch["prompt_constraint_pilot_blocked_reasons"] == []
    assert result.last_debug_patch["prompt_constraint_pilot_applied"] is False
