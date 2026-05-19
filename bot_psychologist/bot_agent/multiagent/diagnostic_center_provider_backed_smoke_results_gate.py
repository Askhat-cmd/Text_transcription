"""PRD-046.1.24 provider-backed smoke results/quality/rollback gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_provider_backed_smoke_results_gate_v1 import (
    ProviderBackedSmokeResultsDecisionV1,
    ProviderBackedSmokeResultsGateRunV1,
)

PRD = "PRD-046.1.24"
SOURCE_PRD = "PRD-046.1.23"
NEXT_PRD_CONTINUE = "PRD-046.1.25 - Diagnostic Center Second Provider-Backed Limited Smoke Planning v1"
NEXT_PRD_FIX = "PRD-046.1.25 - Diagnostic Center Provider-Backed Smoke Calibration v1"
NEXT_PRD_STOP = "PRD-046.1.25 - Diagnostic Center Provider-Backed Pilot Stop / Rollback Closure v1"


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
        "report:implementation": reports_dir / "PRD-046.1.23_IMPLEMENTATION_REPORT.md",
        "report:execution": reports_dir / "PRD-046.1.23_PROVIDER_BACKED_LIMITED_SMOKE_EXECUTION_REPORT.md",
        "report:runtime_safety": reports_dir / "PRD-046.1.23_RUNTIME_SAFETY_AND_ROLLBACK_REPORT.md",
        "report:next": reports_dir / "PRD-046.1.23_NEXT_PRD_RECOMMENDATION.md",
        "scorecard": source_dir / "provider_backed_limited_smoke_execution_scorecard.json",
        "provider_budget": source_dir / "provider_call_budget.json",
        "pilot_execution": source_dir / "pilot_operator_provider_backed_execution.json",
        "normal_control": source_dir / "normal_user_control_execution.json",
        "quality_review": source_dir / "quality_review.json",
        "safety_review": source_dir / "safety_kb_boundary_review.json",
        "provider_output_review": source_dir / "provider_output_sanitization_review.json",
        "trace_review": source_dir / "trace_sanitization_review.json",
        "rollback_precheck": source_dir / "rollback_precheck.json",
        "rollback_postcheck": source_dir / "rollback_postcheck.json",
        "hard_stop": source_dir / "hard_stop_evaluation.json",
        "no_mutation_proof": source_dir / "no_mutation_proof.json",
        "botdb_during": source_dir / "botdb_health_during_execution.json",
        "botdb_after": source_dir / "botdb_health_after_execution.json",
        "artifact_hygiene": source_dir / "artifact_encoding_hygiene_report.json",
        "execution_manifest": source_dir / "execution_manifest.json",
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
        "schema_version": "provider_backed_smoke_results_no_mutation_proof_v1",
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
        "normal_user_path_changed": False,
        "writer_contract_changed_for_normal_users": False,
        "writer_prompt_changed_for_normal_users": False,
        "final_answer_path_changed_for_normal_users": False,
        "private_env_committed": False,
        "raw_private_logs_committed": False,
        "raw_provider_payload_committed": False,
        "new_execution_performed": False,
        "provider_called_by_prd_046_1_24": False,
    }


def build_source_gate(parsed: dict[str, Any], preflight_ok: bool) -> dict[str, Any]:
    score = _safe_dict(parsed.get("scorecard"))
    payload = {
        "schema_version": "provider_backed_smoke_results_source_gate_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "source_final_status": str(score.get("final_status", "failed")),
        "source_decision": str(score.get("decision", "provider_backed_limited_smoke_execution_failed")),
        "source_provider_calls_performed": _as_int(score.get("provider_calls_performed"), -1),
        "source_normal_user_apply_count": _as_int(score.get("normal_user_apply_count"), -1),
        "source_quality_status": str(score.get("quality_status", "failed")),
        "source_safety_kb_boundary_status": str(score.get("safety_kb_boundary_status", "failed")),
        "source_trace_sanitization_status": str(score.get("trace_sanitization_status", "failed")),
        "source_provider_output_sanitization_status": str(score.get("provider_output_sanitization_status", "failed")),
        "source_rollback_postcheck_passed": _as_bool(score.get("rollback_postcheck_passed"), False),
        "source_hard_stop_triggered": _as_bool(score.get("hard_stop_triggered"), True),
        "source_broad_rollout_allowed": _as_bool(score.get("broad_rollout_allowed"), False),
        "source_production_ready": _as_bool(score.get("production_ready"), False),
        "reports_and_logs_present": preflight_ok,
    }
    payload["source_gate_passed"] = (
        payload["source_final_status"] == "passed"
        and payload["source_decision"] == "provider_backed_limited_smoke_execution_passed"
        and payload["source_provider_calls_performed"] == 5
        and payload["source_normal_user_apply_count"] == 0
        and payload["source_quality_status"] == "passed"
        and payload["source_safety_kb_boundary_status"] == "passed"
        and payload["source_trace_sanitization_status"] == "passed"
        and payload["source_provider_output_sanitization_status"] == "passed"
        and payload["source_rollback_postcheck_passed"] is True
        and payload["source_hard_stop_triggered"] is False
        and payload["source_broad_rollout_allowed"] is False
        and payload["source_production_ready"] is False
        and payload["reports_and_logs_present"] is True
    )
    return payload


def build_provider_execution_evidence_review(parsed: dict[str, Any]) -> dict[str, Any]:
    execution_manifest = _safe_dict(parsed.get("execution_manifest"))
    pilot = _safe_dict(parsed.get("pilot_execution"))
    score = _safe_dict(parsed.get("scorecard"))
    allowed_user_ids = execution_manifest.get("allowed_user_ids")
    if not isinstance(allowed_user_ids, list):
        allowed_user_ids = score.get("allowed_user_ids")
    if not isinstance(allowed_user_ids, list):
        allowed_user_ids = []

    review = {
        "schema_version": "provider_backed_smoke_results_execution_evidence_review_v1",
        "prd": PRD,
        "execution_window_count": _as_int(score.get("execution_window_count", execution_manifest.get("execution_window_count")), 0),
        "target_user_count": _as_int(score.get("target_user_count", execution_manifest.get("target_user_count")), 0),
        "allowed_user_ids": [str(item) for item in allowed_user_ids],
        "pilot_scenarios_executed": _as_int(score.get("pilot_scenarios_executed", pilot.get("pilot_scenarios_executed")), 0),
        "pilot_apply_count": _as_int(score.get("pilot_apply_count", pilot.get("pilot_apply_count")), 0),
        "pilot_apply_only_for_allowed_user": _as_bool(score.get("pilot_apply_only_for_allowed_user", pilot.get("pilot_apply_only_for_allowed_user")), False),
        "all_provider_calls_for_allowed_user": _as_bool(score.get("all_provider_calls_for_allowed_user", pilot.get("all_provider_calls_for_allowed_user")), False),
        "provider_calls_performed": _as_int(score.get("provider_calls_performed", pilot.get("provider_calls_performed")), 0),
        "evidence_scope": "single_operator_limited_provider_backed_smoke",
        "production_ready": False,
        "broad_rollout_allowed": False,
    }
    review["provider_execution_evidence_status"] = "passed" if (
        review["execution_window_count"] == 1
        and review["target_user_count"] == 1
        and review["allowed_user_ids"] == ["pilot_runtime_operator_001"]
        and review["pilot_scenarios_executed"] == 5
        and review["pilot_apply_count"] == 5
        and review["pilot_apply_only_for_allowed_user"] is True
        and review["all_provider_calls_for_allowed_user"] is True
        and review["provider_calls_performed"] == 5
    ) else "failed"
    return review


def build_provider_budget_review(parsed: dict[str, Any]) -> dict[str, Any]:
    budget = _safe_dict(parsed.get("provider_budget"))
    payload = {
        "schema_version": "provider_backed_smoke_results_provider_budget_review_v1",
        "prd": PRD,
        "max_provider_calls": _as_int(budget.get("max_provider_calls"), 5),
        "provider_calls_performed": _as_int(budget.get("provider_calls_performed"), 0),
        "provider_calls_for_normal_users": _as_int(budget.get("provider_calls_for_normal_users"), 0),
        "budget_exceeded": _as_bool(budget.get("budget_exceeded"), False),
        "provider_error_leak_to_user_output": _as_bool(budget.get("provider_error_leak_to_user_output"), False),
    }
    payload["budget_exceeded"] = payload["budget_exceeded"] or payload["provider_calls_performed"] > payload["max_provider_calls"]
    payload["provider_budget_status"] = "passed" if (
        payload["max_provider_calls"] == 5
        and payload["provider_calls_performed"] == 5
        and payload["provider_calls_for_normal_users"] == 0
        and payload["budget_exceeded"] is False
        and payload["provider_error_leak_to_user_output"] is False
    ) else "failed"
    return payload


def build_normal_user_no_effect_review(parsed: dict[str, Any]) -> dict[str, Any]:
    controls = _safe_dict(parsed.get("normal_control"))
    payload = {
        "schema_version": "provider_backed_smoke_results_normal_user_no_effect_review_v1",
        "prd": PRD,
        "normal_user_control_count": _as_int(controls.get("normal_user_control_count"), 0),
        "normal_user_apply_count": _as_int(controls.get("normal_user_apply_count"), 0),
        "normal_user_provider_apply_count": _as_int(controls.get("normal_user_provider_apply_count"), 0),
        "writer_prompt_changed_for_normal_user": _as_bool(controls.get("writer_prompt_changed_for_normal_user"), True),
        "writer_contract_changed_for_normal_user": _as_bool(controls.get("writer_contract_changed_for_normal_user"), True),
        "final_answer_changed_for_normal_user": _as_bool(controls.get("final_answer_changed_for_normal_user"), True),
        "normal_user_diagnostic_center_apply_count": _as_int(controls.get("normal_user_diagnostic_center_apply_count"), 0),
    }
    payload["normal_user_no_effect_status"] = "passed" if (
        payload["normal_user_control_count"] >= 2
        and payload["normal_user_apply_count"] == 0
        and payload["normal_user_provider_apply_count"] == 0
        and payload["writer_prompt_changed_for_normal_user"] is False
        and payload["writer_contract_changed_for_normal_user"] is False
        and payload["final_answer_changed_for_normal_user"] is False
        and payload["normal_user_diagnostic_center_apply_count"] == 0
    ) else "failed"
    return payload


def build_quality_consolidation_review(parsed: dict[str, Any]) -> dict[str, Any]:
    quality = _safe_dict(parsed.get("quality_review"))
    payload = {
        "schema_version": "provider_backed_smoke_results_quality_consolidation_review_v1",
        "prd": PRD,
        "quality_status": str(quality.get("quality_status", "failed")),
        "candidate_weaker_than_baseline_count": _as_int(quality.get("candidate_weaker_than_baseline_count"), 0),
        "state_depth_fit_regression_count": _as_int(quality.get("state_depth_fit_regression_count"), 0),
        "non_directiveness_regression_count": _as_int(quality.get("non_directiveness_regression_count"), 0),
        "non_bookishness_regression_count": _as_int(quality.get("non_bookishness_regression_count"), 0),
        "kb_boundary_regression_count": _as_int(quality.get("kb_boundary_regression_count"), 0),
        "safety_regression_count": _as_int(quality.get("safety_regression_count"), 0),
        "prompt_bloat_blocker_count": _as_int(quality.get("prompt_bloat_blocker_count"), 0),
        "constraint_conflict_count": _as_int(quality.get("constraint_conflict_count"), 0),
        "micro_shift_present_count": _as_int(quality.get("micro_shift_present_count"), 0),
        "quality_evidence_scope": "single_operator_five_scenarios",
        "requires_future_larger_limited_validation": True,
    }
    payload["quality_consolidation_status"] = "passed" if (
        payload["quality_status"] == "passed"
        and payload["candidate_weaker_than_baseline_count"] == 0
        and payload["state_depth_fit_regression_count"] == 0
        and payload["non_directiveness_regression_count"] == 0
        and payload["non_bookishness_regression_count"] == 0
        and payload["kb_boundary_regression_count"] == 0
        and payload["safety_regression_count"] == 0
        and payload["prompt_bloat_blocker_count"] == 0
        and payload["constraint_conflict_count"] == 0
        and payload["micro_shift_present_count"] >= 4
    ) else "failed"
    return payload


def build_safety_kb_boundary_consolidation(parsed: dict[str, Any]) -> dict[str, Any]:
    safety = _safe_dict(parsed.get("safety_review"))
    payload = {
        "schema_version": "provider_backed_smoke_results_safety_kb_boundary_consolidation_v1",
        "prd": PRD,
        "safety_kb_boundary_status": str(safety.get("safety_kb_boundary_status", "failed")),
        "raw_kb_quote_exposure_count": _as_int(safety.get("raw_kb_quote_exposure_count"), 0),
        "kuznitsa_authority_citation_count": _as_int(safety.get("kuznitsa_authority_citation_count"), 0),
        "content_full_exposure_count": _as_int(safety.get("content_full_exposure_count"), 0),
        "internal_only_direct_use_count": _as_int(safety.get("internal_only_direct_use_count"), 0),
        "not_for_direct_quote_violation_count": _as_int(safety.get("not_for_direct_quote_violation_count"), 0),
        "high_stakes_directive_advice_count": _as_int(safety.get("high_stakes_directive_advice_count"), 0),
        "safety_regression_count": _as_int(safety.get("safety_regression_count"), 0),
        "kb_boundary_violation_count": _as_int(safety.get("kb_boundary_violation_count"), 0),
        "kuznitsa_duha_role": str(safety.get("kuznitsa_duha_role", "")),
        "user_facing_quote_source": _as_bool(safety.get("user_facing_quote_source"), False),
        "chunk_type_authority": str(safety.get("chunk_type_authority", "")),
        "allowed_use_authority": str(safety.get("allowed_use_authority", "")),
        "safety_flags_authority": str(safety.get("safety_flags_authority", "")),
        "llm_enrichment_role": str(safety.get("llm_enrichment_role", "")),
    }
    payload["safety_kb_boundary_consolidation_status"] = "passed" if (
        payload["safety_kb_boundary_status"] == "passed"
        and payload["raw_kb_quote_exposure_count"] == 0
        and payload["kuznitsa_authority_citation_count"] == 0
        and payload["content_full_exposure_count"] == 0
        and payload["internal_only_direct_use_count"] == 0
        and payload["not_for_direct_quote_violation_count"] == 0
        and payload["high_stakes_directive_advice_count"] == 0
        and payload["safety_regression_count"] == 0
        and payload["kb_boundary_violation_count"] == 0
        and payload["kuznitsa_duha_role"] == "internal_lens_library"
        and payload["user_facing_quote_source"] is False
        and payload["chunk_type_authority"] == "deterministic"
        and payload["allowed_use_authority"] == "deterministic"
        and payload["safety_flags_authority"] == "deterministic"
        and payload["llm_enrichment_role"] == "advisory"
    ) else "failed"
    return payload


def build_provider_output_sanitization_consolidation(parsed: dict[str, Any]) -> dict[str, Any]:
    review = _safe_dict(parsed.get("provider_output_review"))
    payload = {
        "schema_version": "provider_backed_smoke_results_provider_output_sanitization_consolidation_v1",
        "prd": PRD,
        "provider_output_sanitization_status": str(review.get("provider_output_sanitization_status", "failed")),
        "raw_provider_request_committed": _as_bool(review.get("raw_provider_request_committed"), True),
        "raw_provider_response_committed": _as_bool(review.get("raw_provider_response_committed"), True),
        "raw_provider_payload_committed": _as_bool(review.get("raw_provider_payload_committed"), True),
        "provider_error_stack_committed": _as_bool(review.get("provider_error_stack_committed"), True),
        "secret_like_values_committed": _as_bool(review.get("secret_like_values_committed"), True),
        "env_values_committed": _as_bool(review.get("env_values_committed"), True),
        "private_user_ids_committed": _as_bool(review.get("private_user_ids_committed"), True),
        "sanitized_summary_only": _as_bool(review.get("sanitized_summary_only"), False),
    }
    payload["provider_output_sanitization_consolidation_status"] = "passed" if (
        payload["provider_output_sanitization_status"] == "passed"
        and payload["raw_provider_request_committed"] is False
        and payload["raw_provider_response_committed"] is False
        and payload["raw_provider_payload_committed"] is False
        and payload["provider_error_stack_committed"] is False
        and payload["secret_like_values_committed"] is False
        and payload["env_values_committed"] is False
        and payload["private_user_ids_committed"] is False
        and payload["sanitized_summary_only"] is True
    ) else "failed"
    return payload


def build_trace_sanitization_consolidation(parsed: dict[str, Any]) -> dict[str, Any]:
    review = _safe_dict(parsed.get("trace_review"))
    payload = {
        "schema_version": "provider_backed_smoke_results_trace_sanitization_consolidation_v1",
        "prd": PRD,
        "trace_sanitization_status": str(review.get("trace_sanitization_status", "failed")),
        "contains_raw_private_logs": _as_bool(review.get("contains_raw_private_logs"), True),
        "contains_raw_provider_payload": _as_bool(review.get("contains_raw_provider_payload"), True),
        "contains_secret_like_values": _as_bool(review.get("contains_secret_like_values"), True),
        "contains_env_values": _as_bool(review.get("contains_env_values"), True),
        "contains_raw_content_full": _as_bool(review.get("contains_raw_content_full"), True),
        "contains_user_private_identifier": _as_bool(review.get("contains_user_private_identifier"), True),
        "contains_nul_char": _as_bool(review.get("contains_nul_char"), True),
        "contains_mojibake": _as_bool(review.get("contains_mojibake"), True),
        "utf8_clean": _as_bool(review.get("utf8_clean"), False),
        "json_parseable": _as_bool(review.get("json_parseable"), False),
    }
    payload["trace_sanitization_consolidation_status"] = "passed" if (
        payload["trace_sanitization_status"] == "passed"
        and payload["contains_raw_private_logs"] is False
        and payload["contains_raw_provider_payload"] is False
        and payload["contains_secret_like_values"] is False
        and payload["contains_env_values"] is False
        and payload["contains_raw_content_full"] is False
        and payload["contains_user_private_identifier"] is False
        and payload["contains_nul_char"] is False
        and payload["contains_mojibake"] is False
        and payload["utf8_clean"] is True
        and payload["json_parseable"] is True
    ) else "failed"
    return payload


def build_rollback_evidence_review(parsed: dict[str, Any]) -> dict[str, Any]:
    precheck = _safe_dict(parsed.get("rollback_precheck"))
    postcheck = _safe_dict(parsed.get("rollback_postcheck"))
    payload = {
        "schema_version": "provider_backed_smoke_results_rollback_evidence_review_v1",
        "prd": PRD,
        "rollback_precheck_passed": _as_bool(precheck.get("rollback_precheck_passed"), False),
        "rollback_postcheck_passed": _as_bool(postcheck.get("rollback_postcheck_passed"), False),
        "force_disabled_priority_preserved": _as_bool(postcheck.get("force_disabled_priority_preserved", precheck.get("force_disabled_priority_preserved")), False),
        "stale_apply_after_force_disabled_count": _as_int(postcheck.get("stale_apply_after_force_disabled_count"), 0),
        "normal_user_apply_after_rollback_count": _as_int(postcheck.get("normal_user_apply_after_rollback_count"), 0),
    }
    payload["rollback_evidence_status"] = "passed" if (
        payload["rollback_precheck_passed"] is True
        and payload["rollback_postcheck_passed"] is True
        and payload["force_disabled_priority_preserved"] is True
        and payload["stale_apply_after_force_disabled_count"] == 0
        and payload["normal_user_apply_after_rollback_count"] == 0
    ) else "failed"
    return payload


def build_botdb_stability_review(parsed: dict[str, Any]) -> dict[str, Any]:
    during = _safe_dict(parsed.get("botdb_during"))
    after = _safe_dict(parsed.get("botdb_after"))
    payload = {
        "schema_version": "provider_backed_smoke_results_botdb_stability_review_v1",
        "prd": PRD,
        "botdb_health_during_execution": {
            "dashboard_chroma_status": str(during.get("dashboard_chroma_status", "")),
            "dashboard_chroma_count": _as_int(during.get("dashboard_chroma_count"), -1),
            "registry_sources_count": _as_int(during.get("registry_sources_count"), -1),
            "query_http_200": _as_bool(during.get("query_http_200"), False),
            "semantic_fallback_used": _as_bool(during.get("semantic_fallback_used"), True),
            "botdb_circuit_open": _as_bool(during.get("botdb_circuit_open"), True),
        },
        "botdb_health_after_execution": {
            "dashboard_chroma_status": str(after.get("dashboard_chroma_status", "")),
            "dashboard_chroma_count": _as_int(after.get("dashboard_chroma_count"), -1),
            "registry_sources_count": _as_int(after.get("registry_sources_count"), -1),
            "query_http_200": _as_bool(after.get("query_http_200"), False),
            "semantic_fallback_used": _as_bool(after.get("semantic_fallback_used"), True),
            "botdb_circuit_open": _as_bool(after.get("botdb_circuit_open"), True),
        },
    }
    during_ok = (
        payload["botdb_health_during_execution"]["dashboard_chroma_status"] == "ok"
        and payload["botdb_health_during_execution"]["dashboard_chroma_count"] == 247
        and payload["botdb_health_during_execution"]["registry_sources_count"] == 1
        and payload["botdb_health_during_execution"]["query_http_200"] is True
        and payload["botdb_health_during_execution"]["semantic_fallback_used"] is False
        and payload["botdb_health_during_execution"]["botdb_circuit_open"] is False
    )
    after_ok = (
        payload["botdb_health_after_execution"]["dashboard_chroma_status"] == "ok"
        and payload["botdb_health_after_execution"]["dashboard_chroma_count"] == 247
        and payload["botdb_health_after_execution"]["registry_sources_count"] == 1
        and payload["botdb_health_after_execution"]["query_http_200"] is True
        and payload["botdb_health_after_execution"]["semantic_fallback_used"] is False
        and payload["botdb_health_after_execution"]["botdb_circuit_open"] is False
    )
    payload["botdb_stability_status"] = "passed" if during_ok and after_ok else "failed"
    return payload


def build_no_mutation_review(parsed: dict[str, Any], generated_proof: dict[str, Any]) -> dict[str, Any]:
    source = _safe_dict(parsed.get("no_mutation_proof"))
    payload = {
        "schema_version": "provider_backed_smoke_results_no_mutation_review_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": _as_bool(generated_proof.get("all_blocks_merged_mutated"), False),
        "registry_mutated": _as_bool(generated_proof.get("registry_mutated"), False),
        "config_mutated": _as_bool(generated_proof.get("config_mutated"), False),
        "chroma_reindex_performed": _as_bool(source.get("chroma_reindex_performed", generated_proof.get("chroma_reindex_performed")), False),
        "runtime_defaults_changed": _as_bool(source.get("runtime_defaults_changed", generated_proof.get("runtime_defaults_changed")), False),
        "normal_user_path_changed": _as_bool(source.get("normal_user_path_changed", generated_proof.get("normal_user_path_changed")), False),
        "writer_contract_changed_for_normal_users": _as_bool(source.get("writer_contract_changed_for_normal_users", generated_proof.get("writer_contract_changed_for_normal_users")), False),
        "writer_prompt_changed_for_normal_users": _as_bool(source.get("writer_prompt_changed_for_normal_users", generated_proof.get("writer_prompt_changed_for_normal_users")), False),
        "final_answer_path_changed_for_normal_users": _as_bool(source.get("final_answer_path_changed_for_normal_users", generated_proof.get("final_answer_path_changed_for_normal_users")), False),
        "private_env_committed": _as_bool(source.get("private_env_committed", generated_proof.get("private_env_committed")), False),
        "raw_private_logs_committed": _as_bool(source.get("raw_private_logs_committed", generated_proof.get("raw_private_logs_committed")), False),
        "raw_provider_payload_committed": _as_bool(source.get("raw_provider_payload_committed", generated_proof.get("raw_provider_payload_committed")), False),
        "new_execution_performed": _as_bool(generated_proof.get("new_execution_performed"), False),
        "provider_called_by_prd_046_1_24": _as_bool(generated_proof.get("provider_called_by_prd_046_1_24"), False),
    }
    payload["production_mutation_detected"] = any(
        payload[key]
        for key in (
            "all_blocks_merged_mutated",
            "registry_mutated",
            "config_mutated",
            "runtime_defaults_changed",
            "normal_user_path_changed",
            "writer_contract_changed_for_normal_users",
            "writer_prompt_changed_for_normal_users",
            "final_answer_path_changed_for_normal_users",
            "private_env_committed",
            "raw_private_logs_committed",
            "raw_provider_payload_committed",
            "new_execution_performed",
            "provider_called_by_prd_046_1_24",
        )
    )
    payload["no_mutation_status"] = "passed" if payload["production_mutation_detected"] is False else "failed"
    return payload


def build_hard_stop_absence_review(
    *,
    parsed: dict[str, Any],
    provider_budget_review: dict[str, Any],
    normal_user_no_effect_review: dict[str, Any],
    safety_consolidation: dict[str, Any],
    provider_output_sanitization: dict[str, Any],
    trace_sanitization: dict[str, Any],
    rollback_evidence: dict[str, Any],
    botdb_stability: dict[str, Any],
    no_mutation_review: dict[str, Any],
) -> dict[str, Any]:
    hard_stop = _safe_dict(parsed.get("hard_stop"))
    semantic_fallback_used = _as_bool(_safe_dict(botdb_stability.get("botdb_health_after_execution")).get("semantic_fallback_used"), True)

    trace_violation_count = 0 if str(trace_sanitization.get("trace_sanitization_consolidation_status", "failed")) == "passed" else 1
    rollback_failure_count = 0 if str(rollback_evidence.get("rollback_evidence_status", "failed")) == "passed" else 1

    payload = {
        "schema_version": "provider_backed_smoke_results_hard_stop_absence_review_v1",
        "prd": PRD,
        "hard_stop_triggered": _as_bool(hard_stop.get("hard_stop_triggered"), True),
        "normal_user_apply_count": _as_int(normal_user_no_effect_review.get("normal_user_apply_count"), 0),
        "provider_calls_performed": _as_int(provider_budget_review.get("provider_calls_performed"), 0),
        "provider_calls_for_normal_users": _as_int(provider_budget_review.get("provider_calls_for_normal_users"), 0),
        "raw_provider_payload_committed": _as_bool(provider_output_sanitization.get("raw_provider_payload_committed"), True),
        "raw_kb_quote_exposure_count": _as_int(safety_consolidation.get("raw_kb_quote_exposure_count"), 0),
        "kuznitsa_authority_citation_count": _as_int(safety_consolidation.get("kuznitsa_authority_citation_count"), 0),
        "safety_regression_count": _as_int(safety_consolidation.get("safety_regression_count"), 0),
        "kb_boundary_violation_count": _as_int(safety_consolidation.get("kb_boundary_violation_count"), 0),
        "trace_sanitization_violation_count": trace_violation_count,
        "rollback_failure_count": rollback_failure_count,
        "semantic_fallback_used": semantic_fallback_used,
        "production_mutation_detected": _as_bool(no_mutation_review.get("production_mutation_detected"), False),
    }
    payload["hard_stop_absence_status"] = "passed" if (
        payload["hard_stop_triggered"] is False
        and payload["normal_user_apply_count"] == 0
        and payload["provider_calls_performed"] <= 5
        and payload["provider_calls_for_normal_users"] == 0
        and payload["raw_provider_payload_committed"] is False
        and payload["raw_kb_quote_exposure_count"] == 0
        and payload["kuznitsa_authority_citation_count"] == 0
        and payload["safety_regression_count"] == 0
        and payload["kb_boundary_violation_count"] == 0
        and payload["trace_sanitization_violation_count"] == 0
        and payload["rollback_failure_count"] == 0
        and payload["semantic_fallback_used"] is False
        and payload["production_mutation_detected"] is False
    ) else "failed"
    return payload


def build_risk_register() -> dict[str, Any]:
    risks: list[dict[str, Any]] = [
        {
            "risk": "single_operator_scope_only",
            "severity": "medium",
            "status": "open",
            "mitigation": "Expand only via next limited provider-backed planning PRD.",
            "blocks_continue_limited_candidate": False,
            "next_prd_relevance": "PRD-046.1.25",
        },
        {
            "risk": "scenario_count_limited_to_five",
            "severity": "medium",
            "status": "open",
            "mitigation": "Keep deterministic scenario pack and broaden only under controlled cohort.",
            "blocks_continue_limited_candidate": False,
            "next_prd_relevance": "PRD-046.1.25",
        },
        {
            "risk": "provider_budget_headroom_zero",
            "severity": "medium",
            "status": "open",
            "mitigation": "Retain strict 5-call cap and explicit budget monitoring.",
            "blocks_continue_limited_candidate": False,
            "next_prd_relevance": "PRD-046.1.25",
        },
        {
            "risk": "normal_user_controls_minimal",
            "severity": "low",
            "status": "open",
            "mitigation": "Increase normal-user control scenarios in next cycle.",
            "blocks_continue_limited_candidate": False,
            "next_prd_relevance": "PRD-046.1.25",
        },
        {
            "risk": "production_ready_still_prohibited",
            "severity": "high",
            "status": "open",
            "mitigation": "Preserve broad-rollout prohibition until dedicated production PRD gate.",
            "blocks_continue_limited_candidate": False,
            "next_prd_relevance": "PRD-046.1.25",
        },
    ]
    return {
        "schema_version": "provider_backed_smoke_results_risk_register_v1",
        "prd": PRD,
        "risks": risks,
        "risk_count": len(risks),
        "risk_register_has_blockers": any(_as_bool(item.get("blocks_continue_limited_candidate"), False) for item in risks),
    }


def build_decision_gate(
    *,
    source_gate: dict[str, Any],
    provider_execution_evidence_review: dict[str, Any],
    provider_budget_review: dict[str, Any],
    normal_user_no_effect_review: dict[str, Any],
    quality_consolidation_review: dict[str, Any],
    safety_kb_boundary_consolidation: dict[str, Any],
    provider_output_sanitization_consolidation: dict[str, Any],
    trace_sanitization_consolidation: dict[str, Any],
    rollback_evidence_review: dict[str, Any],
    botdb_stability_review: dict[str, Any],
    hard_stop_absence_review: dict[str, Any],
    no_mutation_review: dict[str, Any],
    risk_register: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    checks = {
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
        "provider_execution_evidence_status": str(provider_execution_evidence_review.get("provider_execution_evidence_status", "failed")) == "passed",
        "provider_budget_status": str(provider_budget_review.get("provider_budget_status", "failed")) == "passed",
        "normal_user_no_effect_status": str(normal_user_no_effect_review.get("normal_user_no_effect_status", "failed")) == "passed",
        "quality_consolidation_status": str(quality_consolidation_review.get("quality_consolidation_status", "failed")) == "passed",
        "safety_kb_boundary_consolidation_status": str(safety_kb_boundary_consolidation.get("safety_kb_boundary_consolidation_status", "failed")) == "passed",
        "provider_output_sanitization_consolidation_status": str(provider_output_sanitization_consolidation.get("provider_output_sanitization_consolidation_status", "failed")) == "passed",
        "trace_sanitization_consolidation_status": str(trace_sanitization_consolidation.get("trace_sanitization_consolidation_status", "failed")) == "passed",
        "rollback_evidence_status": str(rollback_evidence_review.get("rollback_evidence_status", "failed")) == "passed",
        "botdb_stability_status": str(botdb_stability_review.get("botdb_stability_status", "failed")) == "passed",
        "hard_stop_absence_status": str(hard_stop_absence_review.get("hard_stop_absence_status", "failed")) == "passed",
        "no_mutation_status": str(no_mutation_review.get("no_mutation_status", "failed")) == "passed",
        "risk_register_has_blockers": _as_bool(risk_register.get("risk_register_has_blockers"), True) is False,
    }
    for key, passed in checks.items():
        if not passed:
            blockers.append(key)

    stop_criteria = (
        _as_int(normal_user_no_effect_review.get("normal_user_apply_count"), 0) > 0
        or _as_int(provider_budget_review.get("provider_calls_performed"), 0) > 5
        or _as_int(provider_budget_review.get("provider_calls_for_normal_users"), 0) > 0
        or str(rollback_evidence_review.get("rollback_evidence_status", "failed")) != "passed"
        or _as_int(safety_kb_boundary_consolidation.get("raw_kb_quote_exposure_count"), 0) > 0
        or _as_int(safety_kb_boundary_consolidation.get("kuznitsa_authority_citation_count"), 0) > 0
        or _as_int(safety_kb_boundary_consolidation.get("safety_regression_count"), 0) > 0
        or str(trace_sanitization_consolidation.get("trace_sanitization_consolidation_status", "failed")) != "passed"
        or str(provider_output_sanitization_consolidation.get("provider_output_sanitization_consolidation_status", "failed")) != "passed"
        or str(botdb_stability_review.get("botdb_stability_status", "failed")) != "passed"
        or _as_bool(no_mutation_review.get("production_mutation_detected"), False)
    )

    if _as_int(quality_consolidation_review.get("micro_shift_present_count"), 0) < 4 and not stop_criteria:
        warnings.append("scenario_coverage_gap_for_next_cycle")

    if stop_criteria:
        final_status = "failed"
        decision = "stop_provider_backed_pilot"
        recommended_next_prd = NEXT_PRD_STOP
    elif blockers and not warnings:
        final_status = "failed"
        decision = "fix_required"
        recommended_next_prd = NEXT_PRD_FIX
    elif blockers or warnings:
        final_status = "passed_with_warnings"
        decision = "fix_required"
        recommended_next_prd = NEXT_PRD_FIX
    else:
        final_status = "passed"
        decision = "continue_limited_candidate"
        recommended_next_prd = NEXT_PRD_CONTINUE

    decision_gate = {
        "schema_version": "provider_backed_smoke_results_decision_gate_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
        "provider_execution_evidence_status": str(provider_execution_evidence_review.get("provider_execution_evidence_status", "failed")),
        "provider_budget_status": str(provider_budget_review.get("provider_budget_status", "failed")),
        "normal_user_no_effect_status": str(normal_user_no_effect_review.get("normal_user_no_effect_status", "failed")),
        "quality_consolidation_status": str(quality_consolidation_review.get("quality_consolidation_status", "failed")),
        "safety_kb_boundary_consolidation_status": str(safety_kb_boundary_consolidation.get("safety_kb_boundary_consolidation_status", "failed")),
        "provider_output_sanitization_consolidation_status": str(provider_output_sanitization_consolidation.get("provider_output_sanitization_consolidation_status", "failed")),
        "trace_sanitization_consolidation_status": str(trace_sanitization_consolidation.get("trace_sanitization_consolidation_status", "failed")),
        "rollback_evidence_status": str(rollback_evidence_review.get("rollback_evidence_status", "failed")),
        "botdb_stability_status": str(botdb_stability_review.get("botdb_stability_status", "failed")),
        "hard_stop_absence_status": str(hard_stop_absence_review.get("hard_stop_absence_status", "failed")),
        "no_mutation_status": str(no_mutation_review.get("no_mutation_status", "failed")),
        "risk_register_has_blockers": _as_bool(risk_register.get("risk_register_has_blockers"), True),
        "new_execution_performed": False,
        "provider_called_by_prd_046_1_24": False,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "future_expansion_requires_new_prd": True,
        "recommended_next_prd": recommended_next_prd,
        "blockers": blockers,
        "warnings": warnings,
    }

    decision_payload = ProviderBackedSmokeResultsDecisionV1(
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
    artifact_encoding_hygiene_passed: bool,
    docs_synced: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "provider_backed_smoke_results_scorecard_v1",
        "prd": PRD,
        "final_status": str(decision_gate.get("final_status", "failed")),
        "decision": str(decision_gate.get("decision", "fix_required")),
        "source_gate_passed": _as_bool(decision_gate.get("source_gate_passed"), False),
        "provider_execution_evidence_status": str(decision_gate.get("provider_execution_evidence_status", "failed")),
        "provider_budget_status": str(decision_gate.get("provider_budget_status", "failed")),
        "normal_user_no_effect_status": str(decision_gate.get("normal_user_no_effect_status", "failed")),
        "quality_consolidation_status": str(decision_gate.get("quality_consolidation_status", "failed")),
        "safety_kb_boundary_consolidation_status": str(decision_gate.get("safety_kb_boundary_consolidation_status", "failed")),
        "provider_output_sanitization_consolidation_status": str(decision_gate.get("provider_output_sanitization_consolidation_status", "failed")),
        "trace_sanitization_consolidation_status": str(decision_gate.get("trace_sanitization_consolidation_status", "failed")),
        "rollback_evidence_status": str(decision_gate.get("rollback_evidence_status", "failed")),
        "botdb_stability_status": str(decision_gate.get("botdb_stability_status", "failed")),
        "hard_stop_absence_status": str(decision_gate.get("hard_stop_absence_status", "failed")),
        "no_mutation_status": str(decision_gate.get("no_mutation_status", "failed")),
        "risk_register_has_blockers": _as_bool(decision_gate.get("risk_register_has_blockers"), True),
        "new_execution_performed": False,
        "provider_called_by_prd_046_1_24": False,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "future_expansion_requires_new_prd": True,
        "artifact_encoding_hygiene_passed": artifact_encoding_hygiene_passed,
        "docs_synced": docs_synced,
        "recommended_next_prd": str(decision_gate.get("recommended_next_prd", NEXT_PRD_FIX)),
        "generated_at": _utc_now(),
    }


def docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = (repo_root / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (repo_root / "docs" / "PRD_INDEX.md").read_text(encoding="utf-8")
    decisions = (repo_root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")

    has_project = "PRD-046.1.24" in project_state
    has_roadmap = "PRD-046.1.24" in roadmap and "PRD-046.1.25" in roadmap
    has_prd_index = "PRD-046.1.24" in prd_index
    has_decision = "no-new-execution results gate" in decisions.lower() or "ADR-042" in decisions
    return {
        "project_state_synced": has_project,
        "roadmap_synced": has_roadmap,
        "prd_index_synced": has_prd_index,
        "decisions_synced": has_decision,
        "docs_synced": has_project and has_roadmap and has_prd_index and has_decision,
    }


def execute_results_gate(*, parsed: dict[str, Any], generated_no_mutation_proof: dict[str, Any], docs_synced: bool) -> dict[str, Any]:
    source_gate = build_source_gate(parsed, preflight_ok=True)
    provider_execution_evidence_review = build_provider_execution_evidence_review(parsed)
    provider_budget_review = build_provider_budget_review(parsed)
    normal_user_no_effect_review = build_normal_user_no_effect_review(parsed)
    quality_consolidation_review = build_quality_consolidation_review(parsed)
    safety_kb_boundary_consolidation = build_safety_kb_boundary_consolidation(parsed)
    provider_output_sanitization_consolidation = build_provider_output_sanitization_consolidation(parsed)
    trace_sanitization_consolidation = build_trace_sanitization_consolidation(parsed)
    rollback_evidence_review = build_rollback_evidence_review(parsed)
    botdb_stability_review = build_botdb_stability_review(parsed)
    no_mutation_review = build_no_mutation_review(parsed, generated_no_mutation_proof)
    risk_register = build_risk_register()
    hard_stop_absence_review = build_hard_stop_absence_review(
        parsed=parsed,
        provider_budget_review=provider_budget_review,
        normal_user_no_effect_review=normal_user_no_effect_review,
        safety_consolidation=safety_kb_boundary_consolidation,
        provider_output_sanitization=provider_output_sanitization_consolidation,
        trace_sanitization=trace_sanitization_consolidation,
        rollback_evidence=rollback_evidence_review,
        botdb_stability=botdb_stability_review,
        no_mutation_review=no_mutation_review,
    )

    decision_gate, decision_payload = build_decision_gate(
        source_gate=source_gate,
        provider_execution_evidence_review=provider_execution_evidence_review,
        provider_budget_review=provider_budget_review,
        normal_user_no_effect_review=normal_user_no_effect_review,
        quality_consolidation_review=quality_consolidation_review,
        safety_kb_boundary_consolidation=safety_kb_boundary_consolidation,
        provider_output_sanitization_consolidation=provider_output_sanitization_consolidation,
        trace_sanitization_consolidation=trace_sanitization_consolidation,
        rollback_evidence_review=rollback_evidence_review,
        botdb_stability_review=botdb_stability_review,
        hard_stop_absence_review=hard_stop_absence_review,
        no_mutation_review=no_mutation_review,
        risk_register=risk_register,
    )

    artifact_hygiene = _safe_dict(parsed.get("artifact_hygiene"))
    artifact_encoding_hygiene_passed = str(artifact_hygiene.get("final_status", "failed")) == "passed"
    scorecard = build_scorecard(
        decision_gate=decision_gate,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        docs_synced=docs_synced,
    )

    run_payload = ProviderBackedSmokeResultsGateRunV1(
        source_gate=source_gate,
        provider_execution_evidence_review=provider_execution_evidence_review,
        provider_budget_review=provider_budget_review,
        normal_user_no_effect_review=normal_user_no_effect_review,
        quality_consolidation_review=quality_consolidation_review,
        safety_kb_boundary_consolidation=safety_kb_boundary_consolidation,
        provider_output_sanitization_consolidation=provider_output_sanitization_consolidation,
        trace_sanitization_consolidation=trace_sanitization_consolidation,
        rollback_evidence_review=rollback_evidence_review,
        botdb_stability_review=botdb_stability_review,
        hard_stop_absence_review=hard_stop_absence_review,
        no_mutation_review=no_mutation_review,
        risk_register=risk_register,
        decision_gate=decision_gate,
        scorecard=scorecard,
    ).to_dict()
    run_payload["decision_payload"] = decision_payload
    return run_payload
