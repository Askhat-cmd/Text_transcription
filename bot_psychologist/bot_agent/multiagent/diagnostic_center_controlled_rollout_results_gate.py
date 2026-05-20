"""PRD-046.1.32 controlled rollout results/rollback/quality gate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_controlled_rollout_results_gate_v1 import ControlledRolloutResultsGateDecisionV1

PRD = "PRD-046.1.32"
SOURCE_PRD = "PRD-046.1.31"
NEXT_PRD_GREEN = "PRD-046.1.33 - Diagnostic Center Limited Runtime Activation Readiness / Normal-User Boundary Decision Gate v1"
NEXT_PRD_HOTFIX = "PRD-046.1.32-HF1 - Controlled Rollout Results Gate Hotfix / Evidence Repair v1"

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}


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


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_source_artifacts(source_dir: Path, reports_dir: Path) -> dict[str, Path]:
    return {
        "report:implementation": reports_dir / "PRD-046.1.31_IMPLEMENTATION_REPORT.md",
        "report:next": reports_dir / "PRD-046.1.31_NEXT_PRD_RECOMMENDATION.md",
        "report:execution": reports_dir / "PRD-046.1.31_CONTROLLED_ROLLOUT_EXECUTION_REPORT.md",
        "test_command_output": source_dir / "test_command_output.txt",
        "decision": source_dir / "controlled_rollout_decision.json",
        "execution_manifest": source_dir / "controlled_rollout_execution_manifest.json",
        "execution_results": source_dir / "controlled_rollout_execution_results.json",
        "provider_budget": source_dir / "controlled_rollout_provider_budget.json",
        "normal_user_no_effect": source_dir / "controlled_rollout_normal_user_no_effect.json",
        "quality_micro_shift": source_dir / "controlled_rollout_quality_micro_shift.json",
        "rollback_proof": source_dir / "controlled_rollout_rollback_proof.json",
        "hard_stop_report": source_dir / "controlled_rollout_hard_stop_report.json",
        "safety_kb_boundary": source_dir / "controlled_rollout_safety_kb_boundary.json",
        "trace_provider_sanitization": source_dir / "controlled_rollout_trace_provider_sanitization.json",
        "botdb_stability": source_dir / "controlled_rollout_botdb_stability.json",
        "no_mutation_proof": source_dir / "no_mutation_proof.json",
        "artifact_hygiene": source_dir / "artifact_encoding_hygiene_report.json",
        "source_gate": source_dir / "controlled_rollout_source_gate.json",
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

    json_count = len(list(source_dir.glob("*.json")))
    return {
        "required": {k: str(v.resolve()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "parsed": parsed,
        "source_json_count": json_count,
        "ok": len(missing) == 0 and len(parse_errors) == 0 and json_count > 0,
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {key: repo_root / rel for key, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str], source_no_mutation: dict[str, Any]) -> dict[str, Any]:
    all_blocks_mutated = hash_before["all_blocks_merged"] != hash_after["all_blocks_merged"]
    registry_mutated = hash_before["registry"] != hash_after["registry"]
    config_mutated = hash_before["config"] != hash_after["config"]
    runtime_defaults_changed = _as_bool(source_no_mutation.get("runtime_defaults_changed"), False)
    source_production_mutated = _as_bool(source_no_mutation.get("production_data_mutated"), False)
    kb_authority_mutated = _as_bool(source_no_mutation.get("kb_governance_authority_mutated"), False)
    chroma_reindex_performed = _as_bool(source_no_mutation.get("chroma_reindex_performed"), False)

    production_data_mutated = all_blocks_mutated or registry_mutated or config_mutated or source_production_mutated
    kb_registry_chroma_config_mutated = all_blocks_mutated or registry_mutated or config_mutated or kb_authority_mutated or chroma_reindex_performed

    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_no_mutation_proof_v1",
        "prd": PRD,
        "tracked_paths": TRACKED_PRODUCTION_PATHS,
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "runtime_defaults_changed": runtime_defaults_changed,
        "production_data_mutated": production_data_mutated,
        "kb_registry_chroma_config_mutated": kb_registry_chroma_config_mutated,
        "no_mutation_proof_passed": not (runtime_defaults_changed or production_data_mutated or kb_registry_chroma_config_mutated),
        "new_execution_performed": False,
        "provider_called_by_results_gate": False,
    }


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed"))
    decision = _safe_dict(parsed.get("decision"))

    payload = {
        "schema_version": "diagnostic_center_controlled_rollout_results_source_gate_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "source_gate_passed": False,
        "missing_source_artifact_count": len(preflight.get("missing") or []),
        "source_parse_error_count": len(preflight.get("parse_errors") or []),
        "source_json_count": _as_int(preflight.get("source_json_count"), 0),
        "source_final_status": str(decision.get("final_status", "failed")),
        "source_decision": str(decision.get("decision", "controlled_rollout_execution_blocked")),
        "execution_performed": _as_bool(decision.get("execution_performed"), False),
        "target_operator_count": _as_int(decision.get("target_operator_count"), 0),
        "scenario_count": _as_int(decision.get("scenario_count"), 0),
        "provider_calls_total": _as_int(decision.get("provider_calls_total"), 0),
        "provider_budget_gate_passed": _as_bool(decision.get("provider_budget_gate_passed"), False),
        "broad_rollout_allowed": _as_bool(decision.get("broad_rollout_allowed"), False),
        "production_ready": _as_bool(decision.get("production_ready"), False),
        "normal_user_activation_allowed": _as_bool(decision.get("normal_user_activation_allowed"), False),
    }

    payload["source_gate_passed"] = (
        payload["missing_source_artifact_count"] == 0
        and payload["source_parse_error_count"] == 0
        and payload["source_final_status"] == "passed"
        and payload["source_decision"] == "controlled_rollout_execution_passed_ready_for_results_gate"
        and payload["execution_performed"] is True
        and payload["target_operator_count"] <= 3
        and payload["scenario_count"] >= 12
        and payload["provider_calls_total"] <= 12
        and payload["provider_budget_gate_passed"] is True
        and payload["broad_rollout_allowed"] is False
        and payload["production_ready"] is False
        and payload["normal_user_activation_allowed"] is False
    )
    return payload


def build_execution_evidence_consolidation(source_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_execution_evidence_consolidation_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "new_execution_performed": False,
        "provider_called_by_results_gate": False,
        "target_operator_count": _as_int(source_gate.get("target_operator_count"), 0),
        "scenario_count": _as_int(source_gate.get("scenario_count"), 0),
        "provider_calls_total": _as_int(source_gate.get("provider_calls_total"), 0),
        "execution_evidence_consolidation_passed": _as_bool(source_gate.get("source_gate_passed"), False),
    }


def build_provider_budget_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    budget = _safe_dict(parsed.get("provider_budget"))
    provider_calls_total = _as_int(budget.get("provider_calls_total"), 0)
    max_calls = _as_int(budget.get("provider_call_budget_max"), 12)
    budget_passed = _as_bool(budget.get("provider_budget_gate_passed"), False)
    provider_budget_violation_count = 0 if provider_calls_total <= max_calls and budget_passed else 1
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_provider_budget_gate_v1",
        "prd": PRD,
        "provider_calls_total": provider_calls_total,
        "provider_call_budget_max": max_calls,
        "provider_budget_gate_passed": budget_passed and provider_calls_total <= max_calls,
        "provider_budget_violation_count": provider_budget_violation_count,
    }


def build_normal_user_no_effect_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    normal = _safe_dict(parsed.get("normal_user_no_effect"))
    controls = _as_int(normal.get("normal_user_control_count"), 0)
    apply_count = _as_int(normal.get("normal_user_apply_count"), 0)
    provider_calls = _as_int(normal.get("normal_user_provider_calls"), 0)
    passed = _as_bool(normal.get("gate_passed"), False) and controls >= 3 and apply_count == 0 and provider_calls == 0
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_normal_user_no_effect_gate_v1",
        "prd": PRD,
        "normal_user_controls_total": controls,
        "normal_user_apply_count": apply_count,
        "normal_user_provider_calls_total": provider_calls,
        "normal_user_no_effect_passed": passed,
    }


def build_quality_micro_shift_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    quality = _safe_dict(parsed.get("quality_micro_shift"))
    candidate_weaker = _as_int(quality.get("candidate_weaker_than_baseline_count"), 0)
    hard_fail = _as_int(quality.get("thread_continuity_hard_fail_count"), 0)
    response_regressions = _as_int(quality.get("forbidden_moves_violation_count"), 0) + _as_int(quality.get("state_boundary_violation_count"), 0)
    passed = _as_bool(quality.get("gate_passed"), False) and candidate_weaker == 0 and hard_fail == 0 and response_regressions == 0
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_quality_micro_shift_gate_v1",
        "prd": PRD,
        "quality_micro_shift_gate_passed": passed,
        "candidate_weaker_than_baseline_count": candidate_weaker,
        "hard_fail_count": hard_fail,
        "response_quality_regression_count": response_regressions,
    }


def build_rollback_hard_stop_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    rollback = _safe_dict(parsed.get("rollback_proof"))
    hard_stop = _safe_dict(parsed.get("hard_stop_report"))

    stale_apply = _as_int(rollback.get("stale_apply_after_force_disabled_count"), 0)
    rollback_passed = _as_bool(rollback.get("gate_passed"), False)
    hard_stop_triggered = _as_bool(hard_stop.get("hard_stop_triggered"), True)
    rollback_failure_count = 0 if rollback_passed else 1
    gate_passed = rollback_passed and stale_apply == 0 and not hard_stop_triggered

    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_rollback_hard_stop_gate_v1",
        "prd": PRD,
        "rollback_gate_passed": gate_passed,
        "rollback_failure_count": rollback_failure_count,
        "stale_apply_after_force_disabled_count": stale_apply,
        "hard_stop_triggered": hard_stop_triggered,
    }


def build_safety_kb_boundary_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    safety = _safe_dict(parsed.get("safety_kb_boundary"))
    raw_kb = _as_int(safety.get("raw_kb_text_exposure_count"), 0)
    kb_authority_violations = _as_int(safety.get("authority_citation_count"), 0) + _as_int(safety.get("governance_authority_mutation_count"), 0)
    unsafe_practice = _as_int(safety.get("practice_suggestion_policy_violation_count"), 0)
    passed = _as_bool(safety.get("gate_passed"), False) and raw_kb == 0 and kb_authority_violations == 0 and unsafe_practice == 0
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_safety_kb_boundary_gate_v1",
        "prd": PRD,
        "safety_kb_boundary_gate_passed": passed,
        "raw_kb_text_exposure_count": raw_kb,
        "kb_authority_violation_count": kb_authority_violations,
        "unsafe_practice_suggestion_count": unsafe_practice,
    }


def build_trace_provider_sanitization_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    trace = _safe_dict(parsed.get("trace_provider_sanitization"))

    raw_provider_payload = 1 if _as_bool(trace.get("contains_raw_provider_payload"), False) else 0
    secret_like = (
        (1 if _as_bool(trace.get("contains_secret_like_values"), False) else 0)
        + (1 if _as_bool(trace.get("contains_env_values"), False) else 0)
    )
    private_leak = (
        (1 if _as_bool(trace.get("contains_raw_private_logs"), False) else 0)
        + (1 if _as_bool(trace.get("contains_user_private_identifier"), False) else 0)
        + (1 if _as_bool(trace.get("contains_raw_content_full"), False) else 0)
    )

    passed = (
        _as_bool(trace.get("gate_passed"), False)
        and raw_provider_payload == 0
        and secret_like == 0
        and private_leak == 0
        and _as_bool(trace.get("utf8_clean"), True)
        and _as_bool(trace.get("json_parseable"), True)
    )

    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_trace_provider_sanitization_gate_v1",
        "prd": PRD,
        "trace_provider_sanitization_gate_passed": passed,
        "raw_provider_payload_committed_count": raw_provider_payload,
        "secret_like_value_count": secret_like,
        "private_log_leak_count": private_leak,
    }


def build_botdb_stability_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    botdb = _safe_dict(parsed.get("botdb_stability"))
    query_ok = _as_int(botdb.get("query_endpoint_status"), 0) == 200
    fallback_used = _as_bool(botdb.get("semantic_fallback_used"), True)
    gate_passed = _as_bool(botdb.get("gate_passed"), False) and query_ok and not fallback_used
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_botdb_stability_gate_v1",
        "prd": PRD,
        "botdb_stability_gate_passed": gate_passed,
        "botdb_query_ok": query_ok,
        "botdb_semantic_fallback_used": fallback_used,
    }


def build_artifact_hygiene_gate(parsed: dict[str, Any], current_encoding_report: dict[str, Any]) -> dict[str, Any]:
    source_hygiene = _safe_dict(parsed.get("artifact_hygiene"))
    source_passed = str(source_hygiene.get("final_status", "failed")) == "passed"
    current_passed = str(current_encoding_report.get("final_status", "failed")) == "passed"

    utf8_decode_error_count = _as_int(source_hygiene.get("utf8_decode_error_count"), 0) + _as_int(current_encoding_report.get("utf8_decode_error_count"), 0)
    nul_byte_file_count = _as_int(source_hygiene.get("nul_byte_file_count"), 0) + _as_int(current_encoding_report.get("nul_byte_file_count"), 0)
    json_parse_error_count = _as_int(source_hygiene.get("json_parse_error_count"), 0) + _as_int(current_encoding_report.get("json_parse_error_count"), 0)
    replacement_char_warning_count = _as_int(source_hygiene.get("replacement_char_warning_count"), 0) + _as_int(current_encoding_report.get("replacement_char_warning_count"), 0)

    passed = source_passed and current_passed and utf8_decode_error_count == 0 and nul_byte_file_count == 0 and json_parse_error_count == 0
    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_artifact_hygiene_gate_v1",
        "prd": PRD,
        "artifact_encoding_hygiene_passed": passed,
        "utf8_decode_error_count": utf8_decode_error_count,
        "nul_byte_file_count": nul_byte_file_count,
        "json_parse_error_count": json_parse_error_count,
        "replacement_char_warning_count": replacement_char_warning_count,
    }


def _extract_next_section(roadmap: str) -> str:
    match = re.search(r"## Next\n(?P<section>[\s\S]*?)(\n## |\Z)", roadmap)
    return match.group("section") if match else ""


def build_docs_consistency_gate(*, project_state_text: str, roadmap_text: str, prd_index_text: str, decisions_text: str) -> dict[str, Any]:
    next_section = _extract_next_section(roadmap_text)
    next_prds = re.findall(r"PRD-046\.1\.\d+", next_section)

    duplicates = 0
    counts: dict[str, int] = {}
    for prd in next_prds:
        counts[prd] = counts.get(prd, 0) + 1
    for count in counts.values():
        if count > 1:
            duplicates += count - 1

    stale_next_references = 0
    project_next_section_match = re.search(r"## Next Planned PRD[\s\S]*?(\n## |\Z)", project_state_text)
    project_next_section = project_next_section_match.group(0) if project_next_section_match else ""
    if "PRD-046.1.31" in project_next_section:
        stale_next_references += 1
    stale_next_references += sum(1 for prd in next_prds if prd == "PRD-046.1.31")

    project_state_synced = (
        "PRD-046.1.32" in project_state_text
        and "PRD-046.1.33" in project_state_text
        and "PRD-046.1.31" not in project_next_section
    )
    roadmap_synced = "PRD-046.1.33" in next_section and "PRD-046.1.31" not in next_section and duplicates == 0
    prd_index_synced = "| PRD-046.1.32 |" in prd_index_text
    decisions_synced = "PRD-046.1.32" in decisions_text or "Controlled Rollout Results Gate Boundary" in decisions_text

    docs_consistency_passed = (
        project_state_synced
        and roadmap_synced
        and prd_index_synced
        and decisions_synced
        and stale_next_references == 0
        and duplicates == 0
    )

    return {
        "schema_version": "diagnostic_center_controlled_rollout_results_docs_consistency_gate_v1",
        "prd": PRD,
        "docs_consistency_passed": docs_consistency_passed,
        "project_state_synced": project_state_synced,
        "roadmap_synced": roadmap_synced,
        "prd_index_synced": prd_index_synced,
        "decisions_synced": decisions_synced,
        "stale_next_prd_reference_count": stale_next_references,
        "duplicate_roadmap_next_item_count": duplicates,
    }


def build_decision_gate(
    *,
    source_gate: dict[str, Any],
    execution_evidence: dict[str, Any],
    provider_budget: dict[str, Any],
    normal_user: dict[str, Any],
    quality: dict[str, Any],
    rollback: dict[str, Any],
    safety: dict[str, Any],
    trace: dict[str, Any],
    botdb: dict[str, Any],
    no_mutation: dict[str, Any],
    artifact_hygiene: dict[str, Any],
    docs_consistency: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    checks = {
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
        "new_execution_performed_false": _as_bool(execution_evidence.get("new_execution_performed"), False) is False,
        "provider_called_by_results_gate_false": _as_bool(execution_evidence.get("provider_called_by_results_gate"), False) is False,
        "provider_budget_gate_passed": _as_bool(provider_budget.get("provider_budget_gate_passed"), False),
        "normal_user_no_effect_passed": _as_bool(normal_user.get("normal_user_no_effect_passed"), False),
        "quality_micro_shift_gate_passed": _as_bool(quality.get("quality_micro_shift_gate_passed"), False),
        "rollback_gate_passed": _as_bool(rollback.get("rollback_gate_passed"), False),
        "safety_kb_boundary_gate_passed": _as_bool(safety.get("safety_kb_boundary_gate_passed"), False),
        "trace_provider_sanitization_gate_passed": _as_bool(trace.get("trace_provider_sanitization_gate_passed"), False),
        "botdb_stability_gate_passed": _as_bool(botdb.get("botdb_stability_gate_passed"), False),
        "no_mutation_proof_passed": _as_bool(no_mutation.get("no_mutation_proof_passed"), False),
        "artifact_encoding_hygiene_passed": _as_bool(artifact_hygiene.get("artifact_encoding_hygiene_passed"), False),
        "docs_consistency_passed": _as_bool(docs_consistency.get("docs_consistency_passed"), False),
    }
    for key, passed in checks.items():
        if not passed:
            blockers.append(key)

    severe_runtime_regression = (
        _as_int(normal_user.get("normal_user_apply_count"), 0) > 0
        or _as_bool(rollback.get("hard_stop_triggered"), False)
        or _as_int(safety.get("raw_kb_text_exposure_count"), 0) > 0
        or _as_int(safety.get("kb_authority_violation_count"), 0) > 0
        or _as_int(trace.get("raw_provider_payload_committed_count"), 0) > 0
        or _as_int(trace.get("secret_like_value_count"), 0) > 0
        or _as_bool(no_mutation.get("production_data_mutated"), False)
        or _as_bool(no_mutation.get("runtime_defaults_changed"), False)
    )

    docs_blocker = not _as_bool(docs_consistency.get("docs_consistency_passed"), False)

    if severe_runtime_regression:
        final_status = "blocked_runtime_safety_regression"
        decision = "rollback_and_hotfix_required"
        next_prd = NEXT_PRD_HOTFIX
    elif docs_blocker:
        final_status = "done_with_docs_sync_blocker"
        decision = "fix_docs_before_next_readiness"
        next_prd = NEXT_PRD_HOTFIX
    elif blockers:
        final_status = "blocked_missing_or_invalid_source_evidence"
        decision = "stop_before_activation_readiness"
        next_prd = NEXT_PRD_HOTFIX
    else:
        final_status = "passed"
        decision = "ready_for_limited_runtime_activation_readiness_prd"
        next_prd = NEXT_PRD_GREEN

    return ControlledRolloutResultsGateDecisionV1(
        final_status=final_status,
        decision=decision,
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        missing_source_artifact_count=_as_int(source_gate.get("missing_source_artifact_count"), 0),
        source_final_status=str(source_gate.get("source_final_status", "failed")),
        source_decision=str(source_gate.get("source_decision", "controlled_rollout_execution_blocked")),
        new_execution_performed=False,
        provider_called_by_results_gate=False,
        target_operator_count=_as_int(execution_evidence.get("target_operator_count"), 0),
        scenario_count=_as_int(execution_evidence.get("scenario_count"), 0),
        provider_calls_total=_as_int(execution_evidence.get("provider_calls_total"), 0),
        provider_budget_gate_passed=_as_bool(provider_budget.get("provider_budget_gate_passed"), False),
        normal_user_controls_total=_as_int(normal_user.get("normal_user_controls_total"), 0),
        normal_user_apply_count=_as_int(normal_user.get("normal_user_apply_count"), 0),
        normal_user_provider_calls_total=_as_int(normal_user.get("normal_user_provider_calls_total"), 0),
        normal_user_no_effect_passed=_as_bool(normal_user.get("normal_user_no_effect_passed"), False),
        quality_micro_shift_gate_passed=_as_bool(quality.get("quality_micro_shift_gate_passed"), False),
        candidate_weaker_than_baseline_count=_as_int(quality.get("candidate_weaker_than_baseline_count"), 0),
        hard_fail_count=_as_int(quality.get("hard_fail_count"), 0),
        response_quality_regression_count=_as_int(quality.get("response_quality_regression_count"), 0),
        rollback_gate_passed=_as_bool(rollback.get("rollback_gate_passed"), False),
        rollback_failure_count=_as_int(rollback.get("rollback_failure_count"), 0),
        stale_apply_after_force_disabled_count=_as_int(rollback.get("stale_apply_after_force_disabled_count"), 0),
        hard_stop_triggered=_as_bool(rollback.get("hard_stop_triggered"), False),
        safety_kb_boundary_gate_passed=_as_bool(safety.get("safety_kb_boundary_gate_passed"), False),
        raw_kb_text_exposure_count=_as_int(safety.get("raw_kb_text_exposure_count"), 0),
        kb_authority_violation_count=_as_int(safety.get("kb_authority_violation_count"), 0),
        unsafe_practice_suggestion_count=_as_int(safety.get("unsafe_practice_suggestion_count"), 0),
        trace_provider_sanitization_gate_passed=_as_bool(trace.get("trace_provider_sanitization_gate_passed"), False),
        raw_provider_payload_committed_count=_as_int(trace.get("raw_provider_payload_committed_count"), 0),
        secret_like_value_count=_as_int(trace.get("secret_like_value_count"), 0),
        private_log_leak_count=_as_int(trace.get("private_log_leak_count"), 0),
        botdb_stability_gate_passed=_as_bool(botdb.get("botdb_stability_gate_passed"), False),
        botdb_query_ok=_as_bool(botdb.get("botdb_query_ok"), False),
        botdb_semantic_fallback_used=_as_bool(botdb.get("botdb_semantic_fallback_used"), True),
        no_mutation_proof_passed=_as_bool(no_mutation.get("no_mutation_proof_passed"), False),
        runtime_defaults_changed=_as_bool(no_mutation.get("runtime_defaults_changed"), False),
        production_data_mutated=_as_bool(no_mutation.get("production_data_mutated"), False),
        kb_registry_chroma_config_mutated=_as_bool(no_mutation.get("kb_registry_chroma_config_mutated"), False),
        artifact_encoding_hygiene_passed=_as_bool(artifact_hygiene.get("artifact_encoding_hygiene_passed"), False),
        utf8_decode_error_count=_as_int(artifact_hygiene.get("utf8_decode_error_count"), 0),
        nul_byte_file_count=_as_int(artifact_hygiene.get("nul_byte_file_count"), 0),
        json_parse_error_count=_as_int(artifact_hygiene.get("json_parse_error_count"), 0),
        replacement_char_warning_count=_as_int(artifact_hygiene.get("replacement_char_warning_count"), 0),
        docs_consistency_passed=_as_bool(docs_consistency.get("docs_consistency_passed"), False),
        project_state_synced=_as_bool(docs_consistency.get("project_state_synced"), False),
        roadmap_synced=_as_bool(docs_consistency.get("roadmap_synced"), False),
        prd_index_synced=_as_bool(docs_consistency.get("prd_index_synced"), False),
        decisions_synced=_as_bool(docs_consistency.get("decisions_synced"), False),
        stale_next_prd_reference_count=_as_int(docs_consistency.get("stale_next_prd_reference_count"), 0),
        duplicate_roadmap_next_item_count=_as_int(docs_consistency.get("duplicate_roadmap_next_item_count"), 0),
        next_recommended_prd=next_prd,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()


def execute_results_gate(
    *,
    preflight: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    current_encoding_report: dict[str, Any],
    project_state_text: str,
    roadmap_text: str,
    prd_index_text: str,
    decisions_text: str,
) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed"))
    source_gate = build_source_gate(preflight)
    execution_evidence = build_execution_evidence_consolidation(source_gate)
    provider_budget = build_provider_budget_gate(parsed)
    normal_user = build_normal_user_no_effect_gate(parsed)
    quality = build_quality_micro_shift_gate(parsed)
    rollback = build_rollback_hard_stop_gate(parsed)
    safety = build_safety_kb_boundary_gate(parsed)
    trace = build_trace_provider_sanitization_gate(parsed)
    botdb = build_botdb_stability_gate(parsed)
    artifact_hygiene = build_artifact_hygiene_gate(parsed, current_encoding_report)
    docs_consistency = build_docs_consistency_gate(
        project_state_text=project_state_text,
        roadmap_text=roadmap_text,
        prd_index_text=prd_index_text,
        decisions_text=decisions_text,
    )

    decision = build_decision_gate(
        source_gate=source_gate,
        execution_evidence=execution_evidence,
        provider_budget=provider_budget,
        normal_user=normal_user,
        quality=quality,
        rollback=rollback,
        safety=safety,
        trace=trace,
        botdb=botdb,
        no_mutation=no_mutation_proof,
        artifact_hygiene=artifact_hygiene,
        docs_consistency=docs_consistency,
    )

    scorecard = {
        "schema_version": "diagnostic_center_controlled_rollout_results_scorecard_v1",
        "prd": PRD,
        "final_status": str(decision.get("final_status", "failed")),
        "decision": str(decision.get("decision", "stop_before_activation_readiness")),
        "source_gate_passed": _as_bool(decision.get("source_gate_passed"), False),
        "provider_budget_gate_passed": _as_bool(decision.get("provider_budget_gate_passed"), False),
        "normal_user_no_effect_passed": _as_bool(decision.get("normal_user_no_effect_passed"), False),
        "quality_micro_shift_gate_passed": _as_bool(decision.get("quality_micro_shift_gate_passed"), False),
        "rollback_gate_passed": _as_bool(decision.get("rollback_gate_passed"), False),
        "safety_kb_boundary_gate_passed": _as_bool(decision.get("safety_kb_boundary_gate_passed"), False),
        "trace_provider_sanitization_gate_passed": _as_bool(decision.get("trace_provider_sanitization_gate_passed"), False),
        "botdb_stability_gate_passed": _as_bool(decision.get("botdb_stability_gate_passed"), False),
        "no_mutation_proof_passed": _as_bool(decision.get("no_mutation_proof_passed"), False),
        "artifact_encoding_hygiene_passed": _as_bool(decision.get("artifact_encoding_hygiene_passed"), False),
        "docs_consistency_passed": _as_bool(decision.get("docs_consistency_passed"), False),
        "new_execution_performed": False,
        "provider_called_by_results_gate": False,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "next_recommended_prd": str(decision.get("next_recommended_prd", NEXT_PRD_HOTFIX)),
        "blockers": list(decision.get("blockers") or []),
        "warnings": list(decision.get("warnings") or []),
    }

    return {
        "source_gate": source_gate,
        "execution_evidence_consolidation": execution_evidence,
        "provider_budget_gate": provider_budget,
        "normal_user_no_effect_gate": normal_user,
        "quality_micro_shift_gate": quality,
        "rollback_hard_stop_gate": rollback,
        "safety_kb_boundary_gate": safety,
        "trace_provider_sanitization_gate": trace,
        "botdb_stability_gate": botdb,
        "docs_consistency_gate": docs_consistency,
        "no_mutation_proof": no_mutation_proof,
        "artifact_encoding_hygiene_report": artifact_hygiene,
        "results_gate_scorecard": scorecard,
        "decision": decision,
    }


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "NEXT_PRD_GREEN",
    "NEXT_PRD_HOTFIX",
    "required_source_artifacts",
    "preflight_source",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_source_gate",
    "build_execution_evidence_consolidation",
    "build_provider_budget_gate",
    "build_normal_user_no_effect_gate",
    "build_quality_micro_shift_gate",
    "build_rollback_hard_stop_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_provider_sanitization_gate",
    "build_botdb_stability_gate",
    "build_artifact_hygiene_gate",
    "build_docs_consistency_gate",
    "build_decision_gate",
    "execute_results_gate",
]
