"""Unified dialogue policy descriptor for PRD-047.12."""

from __future__ import annotations

from typing import Any

from .dialogue_policy import UNIFIED_DIALOGUE_POLICY_VERSION, normalize_dialogue_profile, resolve_profile_preset


def build_unified_dialogue_profile_v1(
    *,
    active_profile: str,
    dialogue_style_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    style_state = dict(dialogue_style_state or {})
    normalized_profile = normalize_dialogue_profile(active_profile)
    profile_preset = resolve_profile_preset(normalized_profile)
    return {
        "version": UNIFIED_DIALOGUE_POLICY_VERSION,
        "active_profile_alias": normalized_profile,
        "profile_preset": profile_preset,
        "effective_writer_autonomy": "high" if profile_preset in {"free_dialogue_default", "custom_dev"} else "medium",
        "effective_safety_floor": "minimal_baseline",
        "diagnostic_center_role": "advisory_context_only",
        "planner_role": "advisory_context_only",
        "active_line_role": "advisory_context_only",
        "diagnostic_card_role": "advisory_context_only",
        "final_answer_directive_role": "single_control_block",
        "writer_context_package_role": "single_context_package",
        "legacy_blocks_visible_to_writer": False,
        "legacy_blocks_source_signals_only": True,
        "hard_boundaries": [
            "safety",
            "crisis_routing",
            "no_diagnosis",
            "no_medical_legal_financial_directives",
            "no_spiritual_authority",
            "no_raw_kb_quote_dumping",
            "privacy_sanitized_trace_only",
        ],
        "soft_guidance": [
            "state",
            "thread",
            "planner",
            "diagnostic_card",
            "knowledge_context",
            "style_preference",
            "target_micro_shift",
        ],
        "style_state_enabled": True,
        "last_offer_tracker_enabled": True,
        "unanswered_question_tracker_enabled": True,
        "dialogue_act_resolver_enabled": True,
        "answer_obligation_resolver_enabled": True,
        "style_state_summary": {
            "tone": str(style_state.get("tone", "neutral") or "neutral"),
            "length_preference": str(style_state.get("length_preference", "adaptive") or "adaptive"),
            "complexity_preference": str(style_state.get("complexity_preference", "normal") or "normal"),
            "avoid": [
                str(item)
                for item in list(style_state.get("avoid", []) or [])
                if str(item).strip()
            ],
        },
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
    }


def build_unified_dialogue_policy_v2(
    *,
    active_profile: str,
    dialogue_style_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_unified_dialogue_profile_v1(
        active_profile=active_profile,
        dialogue_style_state=dialogue_style_state,
    )


__all__ = [
    "build_unified_dialogue_profile_v1",
    "build_unified_dialogue_policy_v2",
]
