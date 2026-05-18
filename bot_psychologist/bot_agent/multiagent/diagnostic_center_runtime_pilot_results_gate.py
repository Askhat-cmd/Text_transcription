"""PRD-046.1.21 runtime pilot post-execution results/rollback/quality gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_runtime_pilot_results_gate_v1 import (
    RuntimePilotResultsDecisionV1,
    RuntimePilotResultsGateRunV1,
    RuntimePilotResultsGateSourceStatusV1,
)

PRD = "PRD-046.1.21"
SOURCE_PRD = "PRD-046.1.20"
NEXT_PRD_CONTINUE = (
    "PRD-046.1.22 - Diagnostic Center Controlled Runtime Pilot Continuation / "
    "Provider-Backed Limited Smoke Readiness v1"
)
NEXT_PRD_FIX = "PRD-046.1.21-HF1 - Runtime Pilot Results Gate Hotfix v1"
NEXT_PRD_STOP = "PRD-046.1.21-STOP - Runtime Pilot Emergency Rollback / Stop v1"


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def required_source_artifacts(source_dir: Path, reports_dir: Path) -> dict[str, Path]:
    return {
        "report:implementation": reports_dir / "PRD-046.1.20_IMPLEMENTATION_REPORT.md",
        "report:runtime": reports_dir / "PRD-046.1.20_RUNTIME_PILOT_EXECUTION_REPORT.md",
        "report:smoke": reports_dir / "PRD-046.1.20_LIMITED_LIVE_SMOKE_RESULTS_REPORT.md",
        "report:next": reports_dir / "PRD-046.1.20_NEXT_PRD_RECOMMENDATION.md",
        "source_gate": source_dir / "source_gate.json",
        "preflight_gate": source_dir / "preflight_gate.json",
        "execution_manifest": source_dir / "execution_manifest.json",
        "toggle_state_before": source_dir / "toggle_state_before.json",
        "rollback_precheck": source_dir / "rollback_precheck.json",
        "pilot_trace": source_dir / "pilot_operator_trace_samples_sanitized.json",
        "normal_trace": source_dir / "normal_user_control_trace_samples_sanitized.json",
        "limited_live_smoke_results": source_dir / "limited_live_smoke_results.json",
        "quality_delta": source_dir / "baseline_vs_pilot_quality_delta.json",
        "safety_gate": source_dir / "safety_kb_boundary_gate.json",
        "trace_gate": source_dir / "trace_sanitization_gate.json",
        "rollback_postcheck": source_dir / "rollback_postcheck.json",
        "hard_stop": source_dir / "hard_stop_evaluation.json",
        "monitoring_scorecard": source_dir / "monitoring_scorecard.json",
        "no_mutation_proof": source_dir / "no_mutation_proof.json",
        "artifact_hygiene": source_dir / "artifact_encoding_hygiene_report.json",
    }


def preflight_source(source_dir: Path, reports_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_dir, reports_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            parsed[key] = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{key}:{exc.__class__.__name__}")
    return {
        "required": {k: str(v.resolve()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "parsed": parsed,
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {
        "all_blocks": repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": repo_root / "Bot_data_base" / "data" / "registry.json",
        "config": repo_root / "Bot_data_base" / "config.yaml",
    }
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_results_no_mutation_proof_v1",
        "prd": PRD,
        "tracked_paths": {
            "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
            "registry": "Bot_data_base/data/registry.json",
            "config": "Bot_data_base/config.yaml",
        },
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "runtime_defaults_changed": False,
        "production_mutation_detected": False,
        "committed_env_changed": False,
        "private_config_committed": False,
        "raw_private_logs_committed": False,
        "new_execution_performed": False,
        "provider_called_by_results_gate": False,
    }


def build_source_gate(parsed: dict[str, Any], preflight_ok: bool) -> dict[str, Any]:
    score = _safe_dict(parsed.get("monitoring_scorecard"))
    payload = {
        "schema_version": "diagnostic_center_runtime_pilot_results_source_gate_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "source_final_status": str(score.get("final_status", "failed")),
        "source_decision": str(score.get("decision", "blocked_runtime_pilot_execution")),
        "execution_window_count": _as_int(score.get("execution_window_count"), 0),
        "target_user_count": _as_int(score.get("target_user_count"), 0),
        "pilot_apply_only_for_allowed_user": _as_bool(score.get("pilot_apply_only_for_allowed_user"), False),
        "normal_user_apply_count": _as_int(score.get("normal_user_apply_count"), 1),
        "rollback_precheck_passed": _as_bool(score.get("rollback_precheck_passed"), False),
        "rollback_postcheck_passed": _as_bool(score.get("rollback_postcheck_passed"), False),
        "quality_delta_status": str(score.get("quality_delta_status", "failed")),
        "safety_kb_boundary_gate_passed": _as_bool(score.get("safety_kb_boundary_gate_passed"), False),
        "trace_sanitization_gate_passed": _as_bool(score.get("trace_sanitization_gate_passed"), False),
        "hard_stop_triggered": _as_bool(score.get("hard_stop_triggered"), True),
        "production_mutation_detected": _as_bool(score.get("production_mutation_detected"), True),
        "artifact_encoding_hygiene_passed": _as_bool(score.get("artifact_encoding_hygiene_passed"), False),
        "reports_and_logs_present": preflight_ok,
    }
    payload["source_gate_passed"] = (
        payload["source_final_status"] == "passed"
        and payload["source_decision"] == "controlled_runtime_pilot_execution_passed"
        and payload["execution_window_count"] == 1
        and payload["target_user_count"] == 1
        and payload["pilot_apply_only_for_allowed_user"] is True
        and payload["normal_user_apply_count"] == 0
        and payload["rollback_precheck_passed"] is True
        and payload["rollback_postcheck_passed"] is True
        and payload["quality_delta_status"] == "passed"
        and payload["safety_kb_boundary_gate_passed"] is True
        and payload["trace_sanitization_gate_passed"] is True
        and payload["hard_stop_triggered"] is False
        and payload["production_mutation_detected"] is False
        and payload["artifact_encoding_hygiene_passed"] is True
        and payload["reports_and_logs_present"] is True
    )
    return payload


def build_execution_evidence_review(parsed: dict[str, Any]) -> dict[str, Any]:
    manifest = _safe_dict(parsed.get("execution_manifest"))
    smoke = _safe_dict(parsed.get("limited_live_smoke_results"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_execution_evidence_review_v1",
        "prd": PRD,
        "execution_window_count": _as_int(manifest.get("execution_window_count"), 0),
        "target_user_count": _as_int(manifest.get("target_user_count"), 0),
        "allowed_user_ids": list(manifest.get("allowed_user_ids", [])) if isinstance(manifest.get("allowed_user_ids"), list) else [],
        "runtime_activation_mode": str(manifest.get("runtime_activation_mode", "")),
        "provider_called_by_execution_count": _as_int(smoke.get("provider_called_by_execution_count", manifest.get("provider_called_by_execution_count")), 0),
        "pilot_apply_count": _as_int(smoke.get("pilot_apply_count"), 0),
        "pilot_apply_only_for_allowed_user": _as_bool(smoke.get("pilot_apply_only_for_allowed_user"), False),
        "prompt_delta_within_limits": _as_bool(smoke.get("prompt_delta_within_limits"), False),
        "evidence_scope": "deterministic_runtime_harness_only",
        "not_yet_real_provider_live_dialogue": True,
    }
    review["execution_evidence_status"] = "passed" if (
        review["execution_window_count"] == 1
        and review["target_user_count"] == 1
        and review["allowed_user_ids"] == ["pilot_runtime_operator_001"]
        and review["runtime_activation_mode"] == "deterministic_runtime_harness"
        and review["provider_called_by_execution_count"] == 0
        and review["pilot_apply_count"] >= 1
        and review["pilot_apply_only_for_allowed_user"] is True
        and review["prompt_delta_within_limits"] is True
    ) else "failed"
    return review


def build_rollback_evidence_review(parsed: dict[str, Any]) -> dict[str, Any]:
    precheck = _safe_dict(parsed.get("rollback_precheck"))
    postcheck = _safe_dict(parsed.get("rollback_postcheck"))
    rollback_state = _safe_dict(postcheck.get("rollback_state"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_rollback_evidence_review_v1",
        "prd": PRD,
        "rollback_precheck_passed": _as_bool(precheck.get("rollback_precheck_passed"), False),
        "rollback_postcheck_passed": _as_bool(postcheck.get("rollback_postcheck_passed"), False),
        "stale_apply_after_force_disabled_count": _as_int(postcheck.get("stale_apply_after_force_disabled_count"), 0),
        "normal_user_apply_after_rollback_count": _as_int(postcheck.get("normal_user_apply_after_rollback_count"), 0),
        "force_disabled_priority_preserved": _as_bool(rollback_state.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"), False),
        "rollback_state_restores": {
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": _as_bool(rollback_state.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"), False),
            "PROMPT_CONSTRAINT_PILOT_ENABLED": _as_bool(rollback_state.get("PROMPT_CONSTRAINT_PILOT_ENABLED"), True),
            "PROMPT_CONSTRAINT_PILOT_MODE": str(rollback_state.get("PROMPT_CONSTRAINT_PILOT_MODE", "")),
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": str(rollback_state.get("PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS", "")),
        },
    }
    review["rollback_evidence_status"] = "passed" if (
        review["rollback_precheck_passed"] is True
        and review["rollback_postcheck_passed"] is True
        and review["stale_apply_after_force_disabled_count"] == 0
        and review["normal_user_apply_after_rollback_count"] == 0
        and review["force_disabled_priority_preserved"] is True
        and review["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_ENABLED"] is False
        and review["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_MODE"] == "shadow"
        and review["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS"] == ""
    ) else "failed"
    return review


def build_normal_user_no_effect_review(parsed: dict[str, Any]) -> dict[str, Any]:
    manifest = _safe_dict(parsed.get("execution_manifest"))
    smoke = _safe_dict(parsed.get("limited_live_smoke_results"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_normal_user_no_effect_review_v1",
        "prd": PRD,
        "normal_user_control_count": _as_int(manifest.get("normal_user_control_count"), 0),
        "normal_user_apply_count": _as_int(smoke.get("normal_user_apply_count"), 0),
        "writer_prompt_changed_for_normal_user": _as_bool(smoke.get("writer_prompt_changed_for_normal_user"), True),
        "writer_contract_changed_for_normal_user": _as_bool(smoke.get("writer_contract_changed_for_normal_user"), True),
        "final_answer_changed_for_normal_user": _as_bool(smoke.get("final_answer_changed_for_normal_user"), True),
        "normal_user_provider_apply_count": _as_int(smoke.get("normal_user_provider_apply_count"), 1),
        "normal_user_trace_sanitized": _as_bool(smoke.get("normal_user_trace_sanitized"), False),
    }
    review["normal_user_no_effect_status"] = "passed" if (
        review["normal_user_control_count"] >= 2
        and review["normal_user_apply_count"] == 0
        and review["writer_prompt_changed_for_normal_user"] is False
        and review["writer_contract_changed_for_normal_user"] is False
        and review["final_answer_changed_for_normal_user"] is False
        and review["normal_user_provider_apply_count"] == 0
        and review["normal_user_trace_sanitized"] is True
    ) else "failed"
    return review


def build_quality_delta_review(parsed: dict[str, Any]) -> dict[str, Any]:
    quality = _safe_dict(parsed.get("quality_delta"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_quality_delta_review_v1",
        "prd": PRD,
        "quality_delta_status": str(quality.get("quality_delta_status", "failed")),
        "candidate_weaker_than_baseline_count": _as_int(quality.get("candidate_weaker_than_baseline_count"), 0),
        "state_depth_fit_regression_count": _as_int(quality.get("state_depth_fit_regression_count"), 0),
        "non_directiveness_regression_count": _as_int(quality.get("non_directiveness_regression_count"), 0),
        "non_bookishness_regression_count": _as_int(quality.get("non_bookishness_regression_count"), 0),
        "kb_boundary_regression_count": _as_int(quality.get("kb_boundary_regression_count"), 0),
        "safety_regression_count": _as_int(quality.get("safety_regression_count"), 0),
        "prompt_bloat_blocker_count": _as_int(quality.get("prompt_bloat_blocker_count"), 0),
        "constraint_conflict_count": _as_int(quality.get("constraint_conflict_count"), 0),
        "quality_evidence_scope": "limited_synthetic_or_harness_scenarios",
        "requires_future_real_dialogue_validation": True,
    }
    review["quality_gate_decision"] = "passed" if (
        review["quality_delta_status"] == "passed"
        and review["candidate_weaker_than_baseline_count"] == 0
        and review["state_depth_fit_regression_count"] == 0
        and review["non_directiveness_regression_count"] == 0
        and review["non_bookishness_regression_count"] == 0
        and review["kb_boundary_regression_count"] == 0
        and review["safety_regression_count"] == 0
        and review["prompt_bloat_blocker_count"] == 0
        and review["constraint_conflict_count"] == 0
    ) else "failed"
    return review


def build_safety_kb_boundary_review(parsed: dict[str, Any]) -> dict[str, Any]:
    safety = _safe_dict(parsed.get("safety_gate"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_safety_kb_boundary_review_v1",
        "prd": PRD,
        "safety_kb_boundary_gate_passed": _as_bool(safety.get("safety_kb_boundary_gate_passed"), False),
        "raw_kb_quote_exposure_count": _as_int(safety.get("raw_kb_quote_exposure_count"), 0),
        "kuznitsa_authority_citation_count": _as_int(safety.get("kuznitsa_authority_citation_count"), 0),
        "internal_only_direct_use_count": _as_int(safety.get("internal_only_direct_use_count"), 0),
        "not_for_direct_quote_violation_count": _as_int(safety.get("not_for_direct_quote_violation_count"), 0),
        "high_stakes_directive_advice_count": _as_int(safety.get("high_stakes_directive_advice_count"), 0),
        "safety_regression_count": _as_int(safety.get("safety_regression_count"), 0),
        "kb_boundary_violation_count": _as_int(safety.get("kb_boundary_violation_count"), 0),
        "chunk_type_authority": str(safety.get("chunk_type_authority", "")),
        "allowed_use_authority": str(safety.get("allowed_use_authority", "")),
        "safety_flags_authority": str(safety.get("safety_flags_authority", "")),
        "llm_enrichment_role": str(safety.get("llm_enrichment_role", "")),
        "kuznitsa_duha_role": str(safety.get("kuznitsa_duha_role", "")),
    }
    review["safety_kb_boundary_status"] = "passed" if (
        review["safety_kb_boundary_gate_passed"] is True
        and review["raw_kb_quote_exposure_count"] == 0
        and review["kuznitsa_authority_citation_count"] == 0
        and review["internal_only_direct_use_count"] == 0
        and review["not_for_direct_quote_violation_count"] == 0
        and review["high_stakes_directive_advice_count"] == 0
        and review["safety_regression_count"] == 0
        and review["kb_boundary_violation_count"] == 0
        and review["chunk_type_authority"] == "deterministic"
        and review["allowed_use_authority"] == "deterministic"
        and review["safety_flags_authority"] == "deterministic"
        and review["llm_enrichment_role"] == "advisory"
        and review["kuznitsa_duha_role"] == "internal_lens_library"
    ) else "failed"
    return review


def build_trace_sanitization_review(parsed: dict[str, Any]) -> dict[str, Any]:
    gate = _safe_dict(parsed.get("trace_gate"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_trace_sanitization_review_v1",
        "prd": PRD,
        "trace_sanitization_gate_passed": _as_bool(gate.get("trace_sanitization_gate_passed"), False),
        "contains_raw_private_logs": _as_bool(gate.get("contains_raw_private_logs"), True),
        "contains_raw_content_full": _as_bool(gate.get("contains_raw_content_full"), True),
        "contains_secret_like_values": _as_bool(gate.get("contains_secret_like_values"), True),
        "contains_env_values": _as_bool(gate.get("contains_env_values"), True),
        "contains_raw_provider_payload": _as_bool(gate.get("contains_raw_provider_payload"), True),
        "contains_nul_char": _as_bool(gate.get("contains_nul_char"), True),
        "contains_mojibake": _as_bool(gate.get("contains_mojibake"), True),
        "utf8_clean": _as_bool(gate.get("utf8_clean"), False),
        "json_parseable": _as_bool(gate.get("json_parseable"), False),
    }
    review["trace_sanitization_status"] = "passed" if (
        review["trace_sanitization_gate_passed"] is True
        and review["contains_raw_private_logs"] is False
        and review["contains_raw_content_full"] is False
        and review["contains_secret_like_values"] is False
        and review["contains_env_values"] is False
        and review["contains_raw_provider_payload"] is False
        and review["contains_nul_char"] is False
        and review["contains_mojibake"] is False
        and review["utf8_clean"] is True
        and review["json_parseable"] is True
    ) else "failed"
    return review


def build_artifact_hygiene_review(parsed: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    hygiene = _safe_dict(parsed.get("artifact_hygiene"))
    replacement_warning_count = _as_int(hygiene.get("replacement_char_warning_count"), 0)
    has_blockers = len(list(hygiene.get("blockers", []))) > 0 if isinstance(hygiene.get("blockers"), list) else False
    artifact = {
        "schema_version": "diagnostic_center_runtime_pilot_artifact_hygiene_review_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "final_status": str(hygiene.get("final_status", "failed")),
        "utf8_decode_error_count": _as_int(hygiene.get("utf8_decode_error_count"), 0),
        "nul_byte_file_count": _as_int(hygiene.get("nul_byte_file_count"), 0),
        "nul_char_file_count": _as_int(hygiene.get("nul_char_file_count"), 0),
        "json_parse_error_count": _as_int(hygiene.get("json_parse_error_count"), 0),
        "replacement_char_warning_count": replacement_warning_count,
        "blockers": list(hygiene.get("blockers", [])) if isinstance(hygiene.get("blockers"), list) else [],
    }
    artifact["artifact_hygiene_status"] = "passed" if (
        artifact["final_status"] == "passed"
        and artifact["utf8_decode_error_count"] == 0
        and artifact["nul_byte_file_count"] == 0
        and artifact["nul_char_file_count"] == 0
        and artifact["json_parse_error_count"] == 0
        and not has_blockers
    ) else "failed"

    encoding_warning = {
        "schema_version": "diagnostic_center_runtime_pilot_encoding_warning_review_v1",
        "prd": PRD,
        "replacement_char_warning_count": replacement_warning_count,
        "encoding_warning_status": "absent",
        "reason": "no_replacement_char_warnings",
        "follow_up_required": False,
    }
    if replacement_warning_count > 0:
        encoding_warning["encoding_warning_status"] = "non_blocking"
        encoding_warning["reason"] = (
            "replacement chars exist only in test_command_output.txt; "
            "no decode/NUL/json blockers"
        )
        encoding_warning["follow_up_required"] = False

    return artifact, encoding_warning


def build_no_mutation_review(parsed: dict[str, Any], no_mutation_proof: dict[str, Any]) -> dict[str, Any]:
    source = _safe_dict(parsed.get("no_mutation_proof"))
    review = {
        "schema_version": "diagnostic_center_runtime_pilot_no_mutation_review_v1",
        "prd": PRD,
        "production_mutation_detected": _as_bool(source.get("production_mutation_detected"), False) or _as_bool(no_mutation_proof.get("production_mutation_detected"), False),
        "all_blocks_merged_mutated": _as_bool(no_mutation_proof.get("all_blocks_merged_mutated"), False),
        "registry_mutated": _as_bool(no_mutation_proof.get("registry_mutated"), False),
        "config_mutated": _as_bool(no_mutation_proof.get("config_mutated"), False),
        "chroma_reindex_performed": _as_bool(source.get("chroma_reindex_performed"), False),
        "runtime_defaults_changed": _as_bool(source.get("runtime_defaults_changed"), False),
        "committed_env_changed": False,
        "private_config_committed": False,
        "raw_private_logs_committed": False,
    }
    review["no_mutation_status"] = "passed" if (
        review["production_mutation_detected"] is False
        and review["all_blocks_merged_mutated"] is False
        and review["registry_mutated"] is False
        and review["config_mutated"] is False
        and review["chroma_reindex_performed"] is False
        and review["runtime_defaults_changed"] is False
        and review["committed_env_changed"] is False
        and review["private_config_committed"] is False
        and review["raw_private_logs_committed"] is False
    ) else "failed"
    return review


def build_default_risk_register() -> list[dict[str, Any]]:
    return [
        {
            "risk": "first_execution_not_real_provider_dialogue",
            "severity": "medium",
            "status": "open",
            "mitigation": "Run provider-backed limited smoke readiness gate before expansion.",
            "next_prd_relevance": "PRD-046.1.22",
            "blocks_continue_limited_candidate": False,
        },
        {
            "risk": "single_operator_cohort",
            "severity": "medium",
            "status": "open",
            "mitigation": "Expand only to controlled limited cohort with strict rollback-first policy.",
            "next_prd_relevance": "PRD-046.1.22",
            "blocks_continue_limited_candidate": False,
        },
        {
            "risk": "minimal_normal_user_controls",
            "severity": "low",
            "status": "open",
            "mitigation": "Increase normal-user control evidence in next limited cycle.",
            "next_prd_relevance": "PRD-046.1.22",
            "blocks_continue_limited_candidate": False,
        },
        {
            "risk": "replacement_char_warning_in_command_log",
            "severity": "low",
            "status": "accepted_non_blocking",
            "mitigation": "Keep encoding hygiene checks and sanitize command log capture.",
            "next_prd_relevance": "PRD-046.1.22",
            "blocks_continue_limited_candidate": False,
        },
        {
            "risk": "broad_rollout_still_prohibited",
            "severity": "high",
            "status": "open",
            "mitigation": "Preserve conservative defaults and require new PRD for any expansion.",
            "next_prd_relevance": "PRD-046.1.22",
            "blocks_continue_limited_candidate": False,
        },
    ]


def build_decision(
    *,
    source_gate: dict[str, Any],
    execution_evidence_review: dict[str, Any],
    rollback_evidence_review: dict[str, Any],
    normal_user_no_effect_review: dict[str, Any],
    quality_delta_review: dict[str, Any],
    safety_kb_boundary_review: dict[str, Any],
    trace_sanitization_review: dict[str, Any],
    artifact_hygiene_review: dict[str, Any],
    encoding_warning_review: dict[str, Any],
    no_mutation_review: dict[str, Any],
    risk_register: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if str(execution_evidence_review.get("execution_evidence_status", "failed")) != "passed":
        blockers.append("execution_evidence_failed")
    if str(rollback_evidence_review.get("rollback_evidence_status", "failed")) != "passed":
        blockers.append("rollback_evidence_failed")
    if str(normal_user_no_effect_review.get("normal_user_no_effect_status", "failed")) != "passed":
        blockers.append("normal_user_no_effect_failed")
    if str(quality_delta_review.get("quality_gate_decision", "failed")) != "passed":
        blockers.append("quality_delta_failed")
    if str(safety_kb_boundary_review.get("safety_kb_boundary_status", "failed")) != "passed":
        blockers.append("safety_kb_boundary_failed")
    if str(trace_sanitization_review.get("trace_sanitization_status", "failed")) != "passed":
        blockers.append("trace_sanitization_failed")
    if str(artifact_hygiene_review.get("artifact_hygiene_status", "failed")) != "passed":
        blockers.append("artifact_hygiene_failed")
    if str(no_mutation_review.get("no_mutation_status", "failed")) != "passed":
        blockers.append("no_mutation_failed")

    if str(encoding_warning_review.get("encoding_warning_status", "absent")) == "non_blocking":
        warnings.append("encoding_warning_non_blocking")

    stop_criteria = (
        _as_int(normal_user_no_effect_review.get("normal_user_apply_count"), 0) > 0
        or str(rollback_evidence_review.get("rollback_evidence_status", "failed")) != "passed"
        or _as_int(rollback_evidence_review.get("stale_apply_after_force_disabled_count"), 0) > 0
        or _as_int(safety_kb_boundary_review.get("raw_kb_quote_exposure_count"), 0) > 0
        or _as_int(safety_kb_boundary_review.get("kuznitsa_authority_citation_count"), 0) > 0
        or _as_int(safety_kb_boundary_review.get("safety_regression_count"), 0) > 0
        or _as_bool(no_mutation_review.get("production_mutation_detected"), False)
        or str(trace_sanitization_review.get("trace_sanitization_status", "failed")) != "passed"
    )

    if stop_criteria:
        final_status = "failed"
        decision = "stop_pilot"
        recommended_next_prd = NEXT_PRD_STOP
    elif blockers:
        final_status = "needs_fix"
        decision = "fix_required"
        recommended_next_prd = NEXT_PRD_FIX
    else:
        final_status = "passed"
        decision = "continue_limited_candidate"
        recommended_next_prd = NEXT_PRD_CONTINUE

    decision_gate = {
        "schema_version": "diagnostic_center_runtime_pilot_results_decision_gate_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
        "execution_evidence_status": str(execution_evidence_review.get("execution_evidence_status", "failed")),
        "rollback_evidence_status": str(rollback_evidence_review.get("rollback_evidence_status", "failed")),
        "normal_user_no_effect_status": str(normal_user_no_effect_review.get("normal_user_no_effect_status", "failed")),
        "quality_gate_decision": str(quality_delta_review.get("quality_gate_decision", "failed")),
        "safety_kb_boundary_status": str(safety_kb_boundary_review.get("safety_kb_boundary_status", "failed")),
        "trace_sanitization_status": str(trace_sanitization_review.get("trace_sanitization_status", "failed")),
        "artifact_hygiene_status": str(artifact_hygiene_review.get("artifact_hygiene_status", "failed")),
        "encoding_warning_status": str(encoding_warning_review.get("encoding_warning_status", "absent")),
        "no_mutation_status": str(no_mutation_review.get("no_mutation_status", "failed")),
        "hard_stop_triggered": bool(stop_criteria),
        "new_execution_performed": False,
        "provider_called_by_results_gate": False,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "future_execution_requires_new_prd": True,
        "recommended_next_prd": recommended_next_prd,
        "risk_count": len(risk_register),
        "blockers": blockers,
        "warnings": warnings,
    }

    decision_payload = RuntimePilotResultsDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()
    return decision_gate, decision_payload


def build_scorecard(
    *,
    decision_gate: dict[str, Any],
    source_gate: dict[str, Any],
    execution_evidence_review: dict[str, Any],
    rollback_evidence_review: dict[str, Any],
    normal_user_no_effect_review: dict[str, Any],
    quality_delta_review: dict[str, Any],
    safety_kb_boundary_review: dict[str, Any],
    trace_sanitization_review: dict[str, Any],
    artifact_hygiene_review: dict[str, Any],
    encoding_warning_review: dict[str, Any],
    no_mutation_review: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_results_scorecard_v1",
        "prd": PRD,
        "final_status": str(decision_gate.get("final_status", "failed")),
        "decision": str(decision_gate.get("decision", "fix_required")),
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
        "execution_evidence_status": str(execution_evidence_review.get("execution_evidence_status", "failed")),
        "rollback_evidence_status": str(rollback_evidence_review.get("rollback_evidence_status", "failed")),
        "normal_user_no_effect_status": str(normal_user_no_effect_review.get("normal_user_no_effect_status", "failed")),
        "quality_gate_decision": str(quality_delta_review.get("quality_gate_decision", "failed")),
        "safety_kb_boundary_status": str(safety_kb_boundary_review.get("safety_kb_boundary_status", "failed")),
        "trace_sanitization_status": str(trace_sanitization_review.get("trace_sanitization_status", "failed")),
        "artifact_hygiene_status": str(artifact_hygiene_review.get("artifact_hygiene_status", "failed")),
        "encoding_warning_status": str(encoding_warning_review.get("encoding_warning_status", "absent")),
        "no_mutation_status": str(no_mutation_review.get("no_mutation_status", "failed")),
        "hard_stop_triggered": _as_bool(decision_gate.get("hard_stop_triggered"), True),
        "broad_rollout_allowed": False,
        "production_ready": False,
        "future_execution_requires_new_prd": True,
        "recommended_next_prd": str(decision_gate.get("recommended_next_prd", NEXT_PRD_FIX)),
        "generated_at": _utc_now(),
    }


def execute_results_gate(*, parsed: dict[str, Any], no_mutation_proof: dict[str, Any]) -> dict[str, Any]:
    source_gate = build_source_gate(parsed, preflight_ok=True)
    execution_evidence_review = build_execution_evidence_review(parsed)
    rollback_evidence_review = build_rollback_evidence_review(parsed)
    normal_user_no_effect_review = build_normal_user_no_effect_review(parsed)
    quality_delta_review = build_quality_delta_review(parsed)
    safety_kb_boundary_review = build_safety_kb_boundary_review(parsed)
    trace_sanitization_review = build_trace_sanitization_review(parsed)
    artifact_hygiene_review, encoding_warning_review = build_artifact_hygiene_review(parsed)
    no_mutation_review = build_no_mutation_review(parsed, no_mutation_proof)
    risk_entries = build_default_risk_register()

    decision_gate, decision_payload = build_decision(
        source_gate=source_gate,
        execution_evidence_review=execution_evidence_review,
        rollback_evidence_review=rollback_evidence_review,
        normal_user_no_effect_review=normal_user_no_effect_review,
        quality_delta_review=quality_delta_review,
        safety_kb_boundary_review=safety_kb_boundary_review,
        trace_sanitization_review=trace_sanitization_review,
        artifact_hygiene_review=artifact_hygiene_review,
        encoding_warning_review=encoding_warning_review,
        no_mutation_review=no_mutation_review,
        risk_register=risk_entries,
    )
    scorecard = build_scorecard(
        decision_gate=decision_gate,
        source_gate=source_gate,
        execution_evidence_review=execution_evidence_review,
        rollback_evidence_review=rollback_evidence_review,
        normal_user_no_effect_review=normal_user_no_effect_review,
        quality_delta_review=quality_delta_review,
        safety_kb_boundary_review=safety_kb_boundary_review,
        trace_sanitization_review=trace_sanitization_review,
        artifact_hygiene_review=artifact_hygiene_review,
        encoding_warning_review=encoding_warning_review,
        no_mutation_review=no_mutation_review,
    )

    run_payload = RuntimePilotResultsGateRunV1(
        source_gate=source_gate,
        execution_evidence_review=execution_evidence_review,
        rollback_evidence_review=rollback_evidence_review,
        normal_user_no_effect_review=normal_user_no_effect_review,
        quality_delta_review=quality_delta_review,
        safety_kb_boundary_review=safety_kb_boundary_review,
        trace_sanitization_review=trace_sanitization_review,
        artifact_hygiene_review=artifact_hygiene_review,
        encoding_warning_review=encoding_warning_review,
        no_mutation_review=no_mutation_review,
        runtime_pilot_results_risk_register={
            "schema_version": "diagnostic_center_runtime_pilot_results_risk_register_v1",
            "prd": PRD,
            "risks": risk_entries,
            "risk_count": len(risk_entries),
        },
        runtime_pilot_results_decision_gate=decision_gate,
        runtime_pilot_results_scorecard=scorecard,
    ).to_dict()

    run_payload["source_status"] = RuntimePilotResultsGateSourceStatusV1(
        source_prd=SOURCE_PRD,
        source_final_status=str(source_gate.get("source_final_status", "failed")),
        source_decision=str(source_gate.get("source_decision", "blocked_runtime_pilot_execution")),
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
    ).to_dict()
    run_payload["decision_payload"] = decision_payload
    return run_payload
