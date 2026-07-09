from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403
from .admin_runtime_compat import *  # noqa: F401,F403
from .admin_surface_helpers import *  # noqa: F401,F403

def _build_runtime_effective_payload(session_id: str | None = None) -> dict[str, Any]:
    status_payload = _status_snapshot()
    flags_snapshot = _filter_operational_flags(feature_flags.snapshot())
    runtime_config_trace = feature_flags.runtime_config_trace()
    writer_kb_payload_resolution = feature_flags.resolve_bool("WRITER_KB_PAYLOAD_ENABLED")
    semantic_cards_runtime = build_semantic_cards_runtime_status()
    env_flags = _env_flags_snapshot()
    effective_config = build_effective_config_payload()
    runtime_warnings = _deprecated_runtime_warnings(env_flags)
    validation = validate_runtime_config(config)
    # session_id retained only for route-level backward compatibility.
    _ = session_id
    pipeline_version = str(getattr(orchestrator, "pipeline_version", "multiagent_v1") or "multiagent_v1")
    compatibility_payload = _compatibility_runtime_payload()
    quality_calibration = _load_prd_047_2_quality_calibration_status()
    active_line_calibration = _load_prd_047_3_active_line_calibration_status()
    response_planner_calibration = _load_prd_047_4_response_planner_calibration_status()
    planner_drift_replay_status = _load_prd_047_6_planner_drift_replay_status()
    guided_live_testing_status = _load_prd_047_7_guided_live_testing_status()
    hybrid_retrieval_planner_settings = get_hybrid_retrieval_planner_settings()
    dialogue_profile = normalize_dialogue_profile(getattr(config, "DIALOGUE_PROFILE", "safe_guided"))
    profile_preset = resolve_profile_preset(dialogue_profile)
    compatibility_payload["dialogue_profile_alias"] = {
        "primary_profile": profile_preset,
        "legacy_alias": dialogue_profile,
        "modern_label": profile_preset,
        "surface_role": "compatibility_only",
    }
    effective_dialogue_policy = build_effective_dialogue_policy(
        profile=dialogue_profile,
        user_message="",
        state_snapshot={"safety_flag": False},
        thread_state={"safety_active": False, "response_mode": "reflect"},
        knowledge_answer_guard={},
    )

    return {
        "schema_version": ADMIN_EFFECTIVE_SCHEMA_VERSION,
        "admin_schema_version": ADMIN_SCHEMA_VERSION,
        "prompt_stack_version": PROMPT_STACK_VERSION,
        "active_runtime": _compute_active_runtime(),
        "runtime_entrypoint": _runtime_entrypoint(),
        "pipeline_version": pipeline_version,
        "legacy": _legacy_status_payload(),
        "compatibility": compatibility_payload,
        "pipeline_mode": compatibility_payload["pipeline_mode"],
        "pipeline_mode_read_only": compatibility_payload["pipeline_mode_read_only"],
        "pipeline_mode_legacy_value": compatibility_payload["pipeline_mode_legacy_value"],
        "legacy_modes_selectable": compatibility_payload["legacy_modes_selectable"],
        "deprecated_runtime_flags": feature_flags.deprecated_runtime_flags(),
        "runtime_warnings": runtime_warnings,
        "agents": _runtime_agents_contract_payload(),
        "status": status_payload,
        "feature_flags": {
            "all": flags_snapshot,
            "groups": _group_feature_flags(flags_snapshot),
        },
        "diagnostics": {
            "contract": "v1",
            "enabled": bool(flags_snapshot.get("USE_NEW_DIAGNOSTICS_V1")),
            "informational_branch_enabled": bool(flags_snapshot.get("INFORMATIONAL_BRANCH_ENABLED")),
        },
        "routing": {
            "deterministic_resolver_enabled": bool(flags_snapshot.get("USE_DETERMINISTIC_ROUTE_RESOLVER")),
            "curiosity_decoupling_enabled": True,
            "false_inform_protection_enabled": bool(flags_snapshot.get("USE_OUTPUT_VALIDATION")),
            "practice_trigger_guard_enabled": bool(_group_param_value("routing", "FREE_CONVERSATION_MODE", True)),
        },
        "validation": {
            "enabled": bool(flags_snapshot.get("USE_OUTPUT_VALIDATION")),
            "config_validation_status": {
                "valid": validation.valid,
                "errors": list(validation.errors),
            },
        },
        "effective_config": effective_config,
        "trace": {
            "available": True,
            "developer_trace_supported": True,
            "developer_trace_enabled": True,
            "developer_trace_mode_available": True,
            "runtime_config_trace": runtime_config_trace,
        },
        "writer_kb_payload": {
            "enabled": bool(writer_kb_payload_resolution.get("effective_value", False)),
            "enabled_source": str(writer_kb_payload_resolution.get("source", "") or ""),
            "raw_value": writer_kb_payload_resolution.get("raw_value"),
            "default_value": bool(writer_kb_payload_resolution.get("default_value", False)),
            "runtime_mode": str(writer_kb_payload_resolution.get("runtime_mode", "unknown") or "unknown"),
            "primary_path": "writer_kb_payload_v1",
            "legacy_fallback_role": "emergency_only",
            "fallback_warning_required": True,
            "manual_web_chat_canonical": True,
            "broad_rollout_allowed": False,
            "production_default_requires_explicit_gate": True,
        },
        "semantic_cards_pilot": semantic_cards_runtime,
        "philosophy_kernel": {
            "enabled": True,
            "version": KERNEL_V1.version,
            "kernel_enabled": True,
            "kernel_version": KERNEL_V1.version,
            "identity": {
                "bot_identity": str(KERNEL_V1.identity.get("bot_identity", "")),
                "role": str(KERNEL_V1.identity.get("role", "")),
            },
            "quote_policy": "internal_lens_not_citation",
            "practice_policy": "gate_required",
            "principles_count": len(KERNEL_V1.principles),
            "boundaries_count": len(KERNEL_V1.boundaries),
            "lenses": sorted(list(KERNEL_V1.lens_map.keys())),
            "selected_lenses_visible": True,
            "prompt_budget": {
                "max_kernel_chars": 1800,
                "max_freedom_chars": 1000,
                "max_combined_chars": 2600,
                "max_selected_lenses": 3,
            },
            "quality_calibration": quality_calibration,
        },
        "writer_freedom_contract": {
            "enabled": True,
            "version": WRITER_FREEDOM_CONTRACT_VERSION,
            "freedom_level": (
                "mvp_free" if profile_preset == "free_dialogue_default" else ("custom_dev" if profile_preset == "custom_dev" else "guided")
            ),
            "mode_is_hint_not_cage": True,
            "question_limit": 1,
            "practice_requires_gate": True,
            "writer_max_tokens": 3200 if profile_preset == "custom_dev" else (2500 if profile_preset == "free_dialogue_default" else 900),
            "writer_target_tokens_default": 900 if profile_preset == "custom_dev" else (700 if profile_preset == "free_dialogue_default" else 300),
            "writer_target_tokens_expanded": 2000 if profile_preset == "custom_dev" else (1500 if profile_preset == "free_dialogue_default" else 700),
            "writer_allow_long_answer": profile_preset in {"free_dialogue_default", "custom_dev"},
        },
        "dialogue_policy": {
            "version": str(effective_dialogue_policy.get("version", UNIFIED_DIALOGUE_POLICY_VERSION)),
            "profile": str(effective_dialogue_policy.get("profile", dialogue_profile)),
            "active_profile_alias": str(effective_dialogue_policy.get("active_profile_alias", dialogue_profile)),
            "profile_preset": str(effective_dialogue_policy.get("profile_preset", profile_preset)),
            "writer_autonomy": str(effective_dialogue_policy.get("writer_autonomy", "guided")),
            "effective_writer_autonomy": str(effective_dialogue_policy.get("effective_writer_autonomy", "medium")),
            "effective_safety_floor": str(effective_dialogue_policy.get("effective_safety_floor", "minimal_baseline")),
            "planner_authority": str(effective_dialogue_policy.get("planner_authority", "guided")),
            "diagnostic_card_authority": str(
                effective_dialogue_policy.get("diagnostic_card_authority", "guided")
            ),
            "writer_move_authority": str(
                effective_dialogue_policy.get("writer_move_authority", "guided")
            ),
            "active_line_authority": str(
                effective_dialogue_policy.get("active_line_authority", "guided")
            ),
            "context_budget_chars": int(
                effective_dialogue_policy.get("context_budget_chars", 2800) or 2800
            ),
            "allow_numbered_lists": bool(
                effective_dialogue_policy.get("allow_numbered_lists", False)
            ),
            "allow_examples": bool(effective_dialogue_policy.get("allow_examples", False)),
            "allow_practice_catalog": bool(
                effective_dialogue_policy.get("allow_practice_catalog", False)
            ),
            "human_like_answer_policy": (
                dict(effective_dialogue_policy.get("human_like_answer_policy", {}))
                if isinstance(effective_dialogue_policy.get("human_like_answer_policy"), dict)
                else {}
            ),
            "constraint_resolution": (
                dict(effective_dialogue_policy.get("constraint_resolution", {}))
                if isinstance(effective_dialogue_policy.get("constraint_resolution"), dict)
                else {}
            ),
            "writer_runtime_max_tokens_effective": (
                3200 if profile_preset == "custom_dev" else (2500 if profile_preset == "free_dialogue_default" else 900)
            ),
            "final_answer_directive_enabled": True,
            "final_answer_directive_version": FINAL_ANSWER_DIRECTIVE_VERSION,
            "final_answer_directive_role": str(effective_dialogue_policy.get("final_answer_directive_role", "single_control_block")),
            "final_answer_acceptance_gate": {
                "enabled": True,
                "version": FINAL_ANSWER_ACCEPTANCE_GATE_VERSION,
                "runtime_position": "after_writer_validator_before_state_memory_offer_acceptance",
                "status_source": "latest_turn_debug.final_answer_acceptance_gate",
                "counters_visible_in_trace": True,
                "quarantine_supported": True,
                "retry_supported": True,
            },
            "writer_context_package_role": str(effective_dialogue_policy.get("writer_context_package_role", "single_context_package")),
            "diagnostic_center_role": str(effective_dialogue_policy.get("diagnostic_center_role", "advisory_context_only")),
            "planner_role": str(effective_dialogue_policy.get("planner_role", "advisory_context_only")),
            "active_line_role": str(effective_dialogue_policy.get("active_line_role", "advisory_context_only")),
            "diagnostic_card_role": str(effective_dialogue_policy.get("diagnostic_card_role", "advisory_context_only")),
            "legacy_prompt_blocks_mode": str(effective_dialogue_policy.get("legacy_prompt_blocks_mode", "source_signals_only")),
            "legacy_blocks_visible_to_writer": bool(effective_dialogue_policy.get("legacy_blocks_visible_to_writer", False)),
            "legacy_blocks_source_signals_only": bool(effective_dialogue_policy.get("legacy_blocks_source_signals_only", True)),
            "writer_first_prompt_assembly_enabled": bool(effective_dialogue_policy.get("writer_first_prompt_assembly_enabled", True)),
            "legacy_advisory_sanitizer_version": "legacy_advisory_sanitizer_v1",
            "writer_visible_practice_semantics": "no_exercise_but_answer_normally",
            "fresh_chat_context_policy_version": FRESH_CHAT_CONTEXT_POLICY_VERSION,
            "writer_context_package_version": WRITER_CONTEXT_PACKAGE_VERSION,
            "fresh_chat_rag_default": "suppress_on_greeting_without_explicit_question",
            "current_chat_reset_control": {
                "endpoint": "/api/v1/users/{user_id}/sessions/{session_id}/reset-context",
                "scope": "session_only",
                "preserves_session_id": True,
            },
            "user_memory_profile_clear_control": {
                "endpoint": "/api/v1/users/{user_id}/history",
                "scope": "user_level",
                "developer_visible": True,
            },
            "web_chat_markdown_renderer": "react_markdown_gfm",
            "dialogue_act_resolver_enabled": True,
            "last_offer_tracker_enabled": True,
            "unanswered_question_tracker_enabled": True,
            "style_state_enabled": True,
            "broad_rollout_allowed": False,
            "production_ready": False,
            "normal_user_activation_allowed": False,
        },
        "dialogue_profile": {
            "value": dialogue_profile,
            "allowed_values": list(ALLOWED_DIALOGUE_PROFILES),
            "scope": "developer_local",
            "description": "Controls unified dialogue preset resolution for developer-local testing.",
            "developer_local_only": True,
            "profile_preset": profile_preset,
            "primary_profile": profile_preset,
            "legacy_alias": dialogue_profile,
            "legacy_alias_visible_in_runtime": False,
            "warning": (
                "Developer-local free dialogue preset. Freer, longer answers. Not production-ready."
                if profile_preset == "free_dialogue_default"
                else ("Developer-local custom preset. Controlled experiments only." if profile_preset == "custom_dev" else "")
            ),
        },
        "active_line": {
            "enabled": True,
            "version": "active_line_v1",
            "revoicing_policy": "suppress_mechanical_revoicing",
            "practice_suppression_active": True,
            "user_intent": "runtime_per_turn",
            "continuity_mode": "runtime_per_turn",
            "last_quality_calibration": active_line_calibration,
        },
        "response_planner": {
            "enabled": True,
            "version": "response_planner_v1",
            "kind": "deterministic",
            "role": "next_meaningful_move_selector",
            "advisory_mode": True,
            "live_acceptance_requires_api_trace": True,
            "last_quality_calibration": response_planner_calibration,
        },
        "hybrid_retrieval_planner": {
            "enabled": bool(hybrid_retrieval_planner_settings.get("enabled", True)),
            "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
            "mode": str(hybrid_retrieval_planner_settings.get("mode", "shadow") or "shadow"),
            "model": str(hybrid_retrieval_planner_settings.get("model", "gpt-5-nano") or "gpt-5-nano"),
            "max_tokens": int(hybrid_retrieval_planner_settings.get("max_tokens", 320) or 320),
            "default_safe_mode": "shadow",
            "metadata_only": True,
            "query_before_rag_supported": True,
            "writer_final_author_preserved": True,
            "allowed_modes": ["off", "shadow", "apply"],
            "llm_optional_for_complex_cases": True,
            "domain_specific_hardcoding_allowed": False,
        },
        "planner_drift_guard": {
            "enabled": True,
            "version": "planner_drift_guard_v1",
            "mode": "observe_only",
            "blocking_user_answers": False,
            "window_size": 100,
            "thresholds": {
                "warning_violation_rate": 0.10,
                "critical_rate": 0.03,
            },
            "mvp_expansion_exceptions": {
                "answer_length_long_when_expansion_requested": True,
                "numbered_list_when_expansion_requested": True,
                "multi_block_answer_when_concept_explanation_full": True,
            },
            "last_summary": get_planner_drift_summary(),
            "last_replay_status": planner_drift_replay_status,
        },
        "guided_live_testing": guided_live_testing_status,
        "diagnostic_center_control": build_diagnostic_center_effective_payload(),
    }

__all__ = [name for name in globals() if not name.startswith("__")]
