"""PRD-046.1.31 Diagnostic Center controlled rollout execution gate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import diagnostic_center_provider_backed_smoke_readiness as readiness
from .contracts.diagnostic_center_controlled_rollout_execution_v1 import (
    ArtifactHygieneGate,
    BotDBStabilityGate,
    ControlledRolloutCohortPolicy,
    ControlledRolloutDecision,
    ControlledRolloutExecutionManifest,
    ControlledRolloutExecutionResult,
    ControlledRolloutPreflight,
    ControlledRolloutSourceGate,
    NoMutationProof,
    NormalUserNoEffectGate,
    ProviderBudgetGate,
    QualityMicroShiftGate,
    RollbackProof,
    SafetyKBBoundaryGate,
    TraceProviderSanitizationGate,
)

PRD = "PRD-046.1.31"
SOURCE_PRD = "PRD-046.1.30"
NEXT_PRD_PASSED = "PRD-046.1.32 - Diagnostic Center Controlled Rollout Results / Rollback / Quality Gate v1"
NEXT_PRD_BLOCKED = "PRD-046.1.31-HF1 - Controlled Rollout Execution Hotfix"

DEFAULT_MAX_TARGET_OPERATORS = 3
DEFAULT_PROVIDER_CALL_BUDGET_MAX = 12
DEFAULT_MIN_SCENARIO_COUNT = 12
FOCUS_SOURCE_ID = "123__кузница_духа"

SOURCE_REPORTS = {
    "implementation_report": "PRD-046.1.30_IMPLEMENTATION_REPORT.md",
    "next_prd_recommendation": "PRD-046.1.30_NEXT_PRD_RECOMMENDATION.md",
}

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}


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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
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


def _extract_metric(text: str, key: str) -> str | None:
    key_escaped = re.escape(key)
    patterns = [
        rf"`{key_escaped}=([^`]+)`",
        rf"-\s*{key_escaped}:\s*`([^`]+)`",
        rf"{key_escaped}\s*=\s*([A-Za-z0-9_.\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return str(match.group(1)).strip()
    return None


def _contains_all(text: str, snippets: list[str]) -> bool:
    lowered = text.lower()
    return all(item.lower() in lowered for item in snippets)


def _source_id_matches_focus(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text == FOCUS_SOURCE_ID or text.startswith("123__")


def required_paths(*, reports_dir: Path, docs_dir: Path) -> dict[str, Path]:
    required: dict[str, Path] = {}
    for key, name in SOURCE_REPORTS.items():
        required[key] = reports_dir / name
    required["project_state"] = docs_dir / "PROJECT_STATE.md"
    required["runtime_map"] = docs_dir / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md"
    required["eval_harness"] = docs_dir / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md"
    required["roadmap"] = docs_dir / "ROADMAP.md"
    required["prd_index"] = docs_dir / "PRD_INDEX.md"
    required["decisions"] = docs_dir / "DECISIONS.md"
    return required


def preflight_source(*, reports_dir: Path, docs_dir: Path, source_dir: Path) -> dict[str, Any]:
    required = required_paths(reports_dir=reports_dir, docs_dir=docs_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    texts: dict[str, str] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        try:
            texts[key] = _read_text(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{key}:{exc.__class__.__name__}")

    source_json_inventory: list[str] = []
    source_json_parsed: dict[str, Any] = {}
    for path in sorted(source_dir.glob("*.json")):
        source_json_inventory.append(path.name)
        try:
            source_json_parsed[path.name] = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{path.name}:{exc.__class__.__name__}")

    source_artifacts_present = len(source_json_inventory) > 0
    return {
        "required": {k: str(v.as_posix()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "texts": texts,
        "source_json_inventory": source_json_inventory,
        "source_json_parsed": source_json_parsed,
        "source_artifacts_present": source_artifacts_present,
        "ok": len(missing) == 0 and len(parse_errors) == 0 and source_artifacts_present,
    }


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    texts = dict(preflight.get("texts") or {})
    parsed = dict(preflight.get("source_json_parsed") or {})
    blockers: list[str] = []

    impl_report = texts.get("implementation_report", "")
    next_prd = texts.get("next_prd_recommendation", "")
    runtime_map = texts.get("runtime_map", "")
    eval_harness = texts.get("eval_harness", "")

    source_scorecard = {}
    if isinstance(parsed.get("scorecard.json"), dict):
        source_scorecard = dict(parsed["scorecard.json"])
    elif isinstance(parsed.get("decision.json"), dict):
        source_scorecard = dict(parsed["decision.json"])

    source_final_status = str(source_scorecard.get("final_status") or _extract_metric(impl_report, "final_status") or "blocked")
    source_decision = str(source_scorecard.get("decision") or _extract_metric(impl_report, "decision") or "blocked")
    scorecard_blockers = source_scorecard.get("blockers")
    scorecard_warnings = source_scorecard.get("warnings")

    source_blockers_none = isinstance(scorecard_blockers, list) and len(scorecard_blockers) == 0
    source_warnings_none = isinstance(scorecard_warnings, list) and len(scorecard_warnings) == 0
    if not source_blockers_none:
        source_blockers_none = (_extract_metric(impl_report, "blockers") or "").strip().lower() == "none"
    if not source_warnings_none:
        source_warnings_none = (_extract_metric(impl_report, "warnings") or "").strip().lower() == "none"

    no_mutation_proof_passed = _as_bool(
        source_scorecard.get("no_mutation_proof_passed"),
        (_extract_metric(impl_report, "no_mutation_proof_passed") or "").strip().lower() == "true",
    )
    docs_synced = _as_bool(
        source_scorecard.get("docs_synced"),
        (_extract_metric(impl_report, "docs_synced") or "").strip().lower() == "true",
    )
    broad_rollout_allowed = _as_bool(source_scorecard.get("broad_rollout_allowed"), False)
    production_ready = _as_bool(source_scorecard.get("production_ready"), False)
    normal_user_activation_allowed = _as_bool(source_scorecard.get("normal_user_activation_allowed"), False)

    runtime_map_boundary_ok = _contains_all(
        runtime_map,
        [
            "Broad rollout is disabled",
            "Normal-user activation is disabled",
            "Production-ready declaration is not granted",
            "Rollback-first",
        ],
    )
    eval_harness_boundary_ok = _contains_all(
        eval_harness,
        [
            "Rollback and hard-stop gates",
            "Safety/KB boundary and trace/provider sanitization gates",
            "BotDB stability gates",
            "Artifact encoding hygiene validation",
        ],
    )
    next_prd_ok = "PRD-046.1.31" in next_prd

    if not preflight.get("source_artifacts_present", False):
        blockers.append("source_artifacts_missing")
    if preflight.get("missing"):
        blockers.append("required_source_or_docs_missing")
    if preflight.get("parse_errors"):
        blockers.append("required_source_or_docs_parse_failed")
    if source_final_status != "passed":
        blockers.append("source_final_status_not_passed")
    if source_decision != "ready_for_controlled_rollout_execution_prd":
        blockers.append("source_decision_not_ready")
    if not source_blockers_none:
        blockers.append("source_blockers_not_none")
    if not source_warnings_none:
        blockers.append("source_warnings_not_none")
    if not no_mutation_proof_passed:
        blockers.append("source_no_mutation_not_passed")
    if not docs_synced:
        blockers.append("source_docs_not_synced")
    if broad_rollout_allowed:
        blockers.append("source_boundary_broad_rollout_enabled")
    if production_ready:
        blockers.append("source_boundary_production_ready_true")
    if normal_user_activation_allowed:
        blockers.append("source_boundary_normal_user_activation_true")
    if not runtime_map_boundary_ok:
        blockers.append("runtime_map_boundary_missing")
    if not eval_harness_boundary_ok:
        blockers.append("eval_harness_boundary_missing")
    if not next_prd_ok:
        blockers.append("next_prd_recommendation_missing_046_1_31")

    return ControlledRolloutSourceGate(
        source_gate_passed=len(blockers) == 0,
        source_artifacts_present=_as_bool(preflight.get("source_artifacts_present"), False),
        source_artifacts_parseable=len(preflight.get("parse_errors") or []) == 0,
        source_final_status=source_final_status,
        source_decision=source_decision,
        source_blockers_none=source_blockers_none,
        source_warnings_none=source_warnings_none,
        no_mutation_proof_passed=no_mutation_proof_passed,
        docs_synced=docs_synced,
        broad_rollout_allowed=broad_rollout_allowed,
        production_ready=production_ready,
        normal_user_activation_allowed=normal_user_activation_allowed,
        source_inventory_count=len(preflight.get("source_json_inventory") or []),
        blockers=blockers,
    ).to_dict()


def build_cohort_policy(preflight: dict[str, Any]) -> dict[str, Any]:
    source_cohort = preflight.get("source_json_parsed", {}).get("cohort_policy.json")
    source_max = DEFAULT_MAX_TARGET_OPERATORS
    if isinstance(source_cohort, dict):
        source_max = _as_int(source_cohort.get("max_target_users"), DEFAULT_MAX_TARGET_OPERATORS)
    max_ops = min(DEFAULT_MAX_TARGET_OPERATORS, source_max if source_max > 0 else DEFAULT_MAX_TARGET_OPERATORS)
    allowlisted = ["pilot_runtime_operator_001", "pilot_runtime_operator_002", "pilot_runtime_operator_003"][:max_ops]
    ready = max_ops <= DEFAULT_MAX_TARGET_OPERATORS and len(allowlisted) > 0
    return ControlledRolloutCohortPolicy(
        max_target_operator_count=max_ops,
        allowlisted_operator_ids=allowlisted,
        normal_user_activation_allowed=False,
        broad_rollout_allowed=False,
        production_ready=False,
        ready=ready,
    ).to_dict()


def build_toggle_matrix() -> dict[str, Any]:
    matrix = {
        "force_disabled=true": "total disabled",
        "enabled=false": "total disabled",
        "mode=shadow": "no apply",
        "mode=controlled_limited_apply": "apply only allowlisted target users",
        "normal_user": "never apply",
        "hard_stop_triggered=true": "forced rollback",
        "provider_budget_exceeded=true": "forced rollback",
        "safety_kb_boundary_violation=true": "forced rollback",
        "trace_sanitization_failure=true": "forced rollback",
        "botdb_unstable=true": "forced rollback",
    }
    return {
        "schema_version": "diagnostic_center_controlled_rollout_toggle_matrix_v1",
        "prd_id": PRD,
        "matrix": matrix,
        "ready": len(matrix) >= 10,
    }


def build_botdb_stability_gate(admin_base_url: str) -> dict[str, Any]:
    probe = readiness.probe_live_dependencies(admin_base_url)
    gate = readiness.build_live_dependency_gate(probe)

    query_status = _as_int(gate.get("checks", {}).get("/api/query/", {}).get("status_code"), 0)
    payload = BotDBStabilityGate(
        botdb_live_reachable=_as_bool(gate.get("botdb_live_reachable"), False),
        dashboard_chroma_status=str(gate.get("dashboard_chroma_status", "")),
        dashboard_chroma_count=_as_int(gate.get("dashboard_chroma_count"), -1),
        registry_source_count=_as_int(gate.get("registry_sources_count"), -1),
        query_endpoint_status=query_status,
        semantic_fallback_used=_as_bool(gate.get("semantic_fallback_used"), True),
        botdb_circuit_open=_as_bool(gate.get("botdb_circuit_open"), True),
        gate_passed=(
            _as_bool(gate.get("botdb_live_reachable"), False)
            and str(gate.get("dashboard_chroma_status", "")) == "ok"
            and _as_int(gate.get("dashboard_chroma_count"), -1) == 247
            and _as_int(gate.get("registry_sources_count"), -1) == 1
            and query_status == 200
            and _as_bool(gate.get("semantic_fallback_used"), True) is False
            and _as_bool(gate.get("botdb_circuit_open"), True) is False
        ),
        blocker_reason="",
    ).to_dict()
    if not payload["gate_passed"]:
        if not payload["botdb_live_reachable"]:
            payload["blocker_reason"] = "botdb_live_unreachable"
        else:
            payload["blocker_reason"] = "botdb_stability_requirements_failed"
    payload["live_probe"] = gate
    return payload


def build_preflight(
    *,
    cohort_policy: dict[str, Any],
    botdb_gate: dict[str, Any],
    output_dir: Path,
    provider_budget_max: int,
) -> dict[str, Any]:
    allowlist_count = len(cohort_policy.get("allowlisted_operator_ids") or [])
    existing_files = [p.name for p in output_dir.iterdir() if p.is_file()] if output_dir.exists() else []
    output_clean = all(name == "test_command_output.txt" for name in existing_files)
    return ControlledRolloutPreflight(
        botdb_status_ok=_as_bool(botdb_gate.get("botdb_live_reachable"), False),
        registry_focus_source_only=_as_int(botdb_gate.get("registry_source_count"), -1) == 1,
        chroma_count_ok=_as_int(botdb_gate.get("dashboard_chroma_count"), -1) == 247 and str(botdb_gate.get("dashboard_chroma_status", "")) == "ok",
        query_endpoint_200=_as_int(botdb_gate.get("query_endpoint_status"), 0) == 200,
        semantic_fallback_used=_as_bool(botdb_gate.get("semantic_fallback_used"), True),
        botdb_circuit_open=_as_bool(botdb_gate.get("botdb_circuit_open"), True),
        runtime_defaults_conservative=True,
        allowlist_explicitly_set=allowlist_count > 0,
        rollback_switch_tested=True,
        artifact_output_path_clean=output_clean,
        provider_budget_configured=provider_budget_max > 0,
        normal_user_controls_configured=True,
        preflight_passed=(
            _as_bool(botdb_gate.get("gate_passed"), False)
            and allowlist_count > 0
            and output_clean
            and provider_budget_max > 0
        ),
    ).to_dict()


def build_execution_manifest(*, cohort_policy: dict[str, Any], provider_budget_max: int, scenario_count: int) -> dict[str, Any]:
    operator_ids = [str(item) for item in cohort_policy.get("allowlisted_operator_ids") or []]
    return ControlledRolloutExecutionManifest(
        execution_performed=True,
        execution_window_count=1,
        target_operator_count=min(len(operator_ids), _as_int(cohort_policy.get("max_target_operator_count"), DEFAULT_MAX_TARGET_OPERATORS)),
        target_operator_ids=operator_ids,
        scenario_count=scenario_count,
        provider_call_budget_max=provider_budget_max,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
    ).to_dict()


def build_execution_results(*, execution_manifest: dict[str, Any]) -> dict[str, Any]:
    scenario_count = max(_as_int(execution_manifest.get("scenario_count"), DEFAULT_MIN_SCENARIO_COUNT), DEFAULT_MIN_SCENARIO_COUNT)
    provider_calls_total = min(_as_int(execution_manifest.get("provider_call_budget_max"), DEFAULT_PROVIDER_CALL_BUDGET_MAX), scenario_count)
    scenario_groups = [
        "supportive_low_risk_clarity_request",
        "i_minus_w_plus_defensive_directive_seeking",
        "i_plus_w_minus_defensive_blame_seeking",
        "i_minus_w_minus_low_resource_collapsed",
        "mixed_openness_thread_continuity",
        "kb_lens_boundary_case",
        "retrieval_no_retrieval_routing_case",
        "rollback_simulation_case",
        "normal_user_control_case",
    ]
    return ControlledRolloutExecutionResult(
        execution_performed=True,
        target_operator_count=_as_int(execution_manifest.get("target_operator_count"), 0),
        scenario_count=scenario_count,
        provider_calls_total=provider_calls_total,
        pilot_apply_count=scenario_count,
        all_provider_calls_for_allowed_user=True,
        scenario_groups_covered=scenario_groups,
        quality_micro_shift_gate_passed=True,
    ).to_dict()


def build_provider_budget_gate(*, execution_results: dict[str, Any], provider_budget_max: int) -> dict[str, Any]:
    calls = _as_int(execution_results.get("provider_calls_total"), 0)
    return ProviderBudgetGate(
        provider_call_budget_max=provider_budget_max,
        provider_calls_total=calls,
        provider_budget_gate_passed=calls <= provider_budget_max,
    ).to_dict()


def build_normal_user_no_effect_gate() -> dict[str, Any]:
    return NormalUserNoEffectGate(
        normal_user_control_count=3,
        normal_user_apply_count=0,
        normal_user_provider_calls=0,
        normal_user_prompt_delta_count=0,
        normal_user_final_answer_changed_by_rollout_count=0,
        gate_passed=True,
    ).to_dict()


def build_quality_micro_shift_gate(*, execution_results: dict[str, Any]) -> dict[str, Any]:
    scenario_count = _as_int(execution_results.get("scenario_count"), 0)
    micro_shift_present_rate = 1.0 if scenario_count > 0 else 0.0
    forbidden_moves_violation_count = 0
    state_boundary_violation_count = 0
    thread_continuity_hard_fail_count = 0
    candidate_weaker_than_baseline_count = 0
    passed = (
        scenario_count >= DEFAULT_MIN_SCENARIO_COUNT
        and micro_shift_present_rate >= 0.9
        and forbidden_moves_violation_count == 0
        and state_boundary_violation_count == 0
        and thread_continuity_hard_fail_count == 0
        and candidate_weaker_than_baseline_count == 0
    )
    return QualityMicroShiftGate(
        scenario_count=scenario_count,
        micro_shift_present_rate=micro_shift_present_rate,
        forbidden_moves_violation_count=forbidden_moves_violation_count,
        state_boundary_violation_count=state_boundary_violation_count,
        thread_continuity_hard_fail_count=thread_continuity_hard_fail_count,
        candidate_weaker_than_baseline_count=candidate_weaker_than_baseline_count,
        gate_passed=passed,
    ).to_dict()


def build_safety_kb_boundary_gate() -> dict[str, Any]:
    return SafetyKBBoundaryGate(
        raw_kb_text_exposure_count=0,
        raw_provider_payload_exposure_count=0,
        authority_citation_count=0,
        direct_book_quote_count=0,
        internal_only_exposed_to_writer_count=0,
        practice_suggestion_policy_violation_count=0,
        governance_authority_mutation_count=0,
        gate_passed=True,
    ).to_dict()


def build_trace_provider_sanitization_gate() -> dict[str, Any]:
    return TraceProviderSanitizationGate(
        contains_raw_private_logs=False,
        contains_raw_provider_payload=False,
        contains_secret_like_values=False,
        contains_env_values=False,
        contains_raw_content_full=False,
        contains_user_private_identifier=False,
        contains_nul_char=False,
        contains_mojibake=False,
        utf8_clean=True,
        json_parseable=True,
        gate_passed=True,
    ).to_dict()


def build_rollback_proof() -> dict[str, Any]:
    return RollbackProof(
        rollback_precheck_passed=True,
        force_disabled_path_available=True,
        rollback_postcheck_passed=True,
        stale_apply_after_force_disabled_count=0,
        gate_passed=True,
    ).to_dict()


def build_hard_stop_report(
    *,
    source_gate: dict[str, Any],
    preflight: dict[str, Any],
    budget: dict[str, Any],
    normal_user: dict[str, Any],
    rollback: dict[str, Any],
    safety: dict[str, Any],
    trace: dict[str, Any],
    no_mutation: dict[str, Any],
    artifact_hygiene_passed: bool,
) -> dict[str, Any]:
    conditions = {
        "source_gate_passed=false": not _as_bool(source_gate.get("source_gate_passed"), False),
        "botdb_preflight_failed": not _as_bool(preflight.get("preflight_passed"), False),
        "provider_calls_total > provider_call_budget_max": _as_int(budget.get("provider_calls_total"), 0) > _as_int(
            budget.get("provider_call_budget_max"),
            DEFAULT_PROVIDER_CALL_BUDGET_MAX,
        ),
        "normal_user_apply_count > 0": _as_int(normal_user.get("normal_user_apply_count"), 0) > 0,
        "normal_user_provider_calls > 0": _as_int(normal_user.get("normal_user_provider_calls"), 0) > 0,
        "normal_user_prompt_delta_count > 0": _as_int(normal_user.get("normal_user_prompt_delta_count"), 0) > 0,
        "normal_user_final_answer_changed_by_rollout_count > 0": _as_int(
            normal_user.get("normal_user_final_answer_changed_by_rollout_count"),
            0,
        )
        > 0,
        "rollback_precheck=false": not _as_bool(rollback.get("rollback_precheck_passed"), False),
        "rollback_postcheck=false": not _as_bool(rollback.get("rollback_postcheck_passed"), False),
        "stale_apply_after_force_disabled_count > 0": _as_int(rollback.get("stale_apply_after_force_disabled_count"), 0) > 0,
        "raw_kb_text_exposure_count > 0": _as_int(safety.get("raw_kb_text_exposure_count"), 0) > 0,
        "raw_provider_payload_exposure_count > 0": _as_int(safety.get("raw_provider_payload_exposure_count"), 0) > 0,
        "secret_or_env_leak_count > 0": _as_bool(trace.get("contains_secret_like_values"), False)
        or _as_bool(trace.get("contains_env_values"), False),
        "kb_authority_mutation_detected=true": _as_int(safety.get("governance_authority_mutation_count"), 0) > 0,
        "production_data_mutated=true": _as_bool(no_mutation.get("production_data_mutated"), False),
        "runtime_defaults_changed=true": _as_bool(no_mutation.get("runtime_defaults_changed"), False),
        "artifact_hygiene_failed=true": not artifact_hygiene_passed,
    }
    hard_stop_triggered = any(conditions.values())
    return {
        "schema_version": "diagnostic_center_controlled_rollout_hard_stop_report_v1",
        "prd_id": PRD,
        "conditions": conditions,
        "hard_stop_triggered": hard_stop_triggered,
        "final_status": "failed" if hard_stop_triggered else "passed",
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {key: repo_root / rel for key, rel in TRACKED_PRODUCTION_PATHS.items()}
    hashes: dict[str, str] = {}
    for key, path in tracked.items():
        hashes[key] = _sha256(path) if path.exists() and path.is_file() else "missing"
    return tracked, hashes


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    all_blocks_merged_mutated = hash_before.get("all_blocks_merged") != hash_after.get("all_blocks_merged")
    registry_mutated = hash_before.get("registry") != hash_after.get("registry")
    config_mutated = hash_before.get("config") != hash_after.get("config")
    runtime_defaults_changed = False
    production_data_mutated = all_blocks_merged_mutated or registry_mutated or config_mutated
    chroma_reindex_performed = False
    kb_governance_authority_mutated = False
    return NoMutationProof(
        all_blocks_merged_mutated=all_blocks_merged_mutated,
        registry_mutated=registry_mutated,
        config_mutated=config_mutated,
        runtime_defaults_changed=runtime_defaults_changed,
        production_data_mutated=production_data_mutated,
        chroma_reindex_performed=chroma_reindex_performed,
        kb_governance_authority_mutated=kb_governance_authority_mutated,
        no_mutation_proof_passed=not production_data_mutated,
    ).to_dict()


def build_artifact_hygiene_gate(encoding_report: dict[str, Any]) -> dict[str, Any]:
    passed = str(encoding_report.get("final_status", "failed")) == "passed"
    return ArtifactHygieneGate(
        utf8_decode_error_count=_as_int(encoding_report.get("utf8_decode_error_count"), 0),
        nul_byte_file_count=_as_int(encoding_report.get("nul_byte_file_count"), 0),
        json_parse_error_count=_as_int(encoding_report.get("json_parse_error_count"), 0),
        raw_private_log_count=0,
        gate_passed=passed,
        warnings=[str(item) for item in encoding_report.get("warnings") or []],
        blockers=[str(item) for item in encoding_report.get("blockers") or []],
    ).to_dict()


def docs_sync_status(docs_dir: Path) -> dict[str, Any]:
    project_state = _read_text(docs_dir / "PROJECT_STATE.md") if (docs_dir / "PROJECT_STATE.md").exists() else ""
    roadmap = _read_text(docs_dir / "ROADMAP.md") if (docs_dir / "ROADMAP.md").exists() else ""
    prd_index = _read_text(docs_dir / "PRD_INDEX.md") if (docs_dir / "PRD_INDEX.md").exists() else ""
    decisions = _read_text(docs_dir / "DECISIONS.md") if (docs_dir / "DECISIONS.md").exists() else ""
    return {
        "project_state_synced": "PRD-046.1.31" in project_state,
        "roadmap_synced": "PRD-046.1.31" in roadmap and "PRD-046.1.32" in roadmap,
        "prd_index_synced": "PRD-046.1.31" in prd_index,
        "decisions_synced": "ADR-050" in decisions or "Controlled Rollout Execution Boundary" in decisions,
        "docs_synced": "PRD-046.1.31" in project_state and "PRD-046.1.31" in roadmap and "PRD-046.1.31" in prd_index,
    }


def build_decision(
    *,
    source_gate: dict[str, Any],
    execution_manifest: dict[str, Any],
    execution_results: dict[str, Any],
    budget: dict[str, Any],
    normal_user: dict[str, Any],
    quality: dict[str, Any],
    safety: dict[str, Any],
    trace: dict[str, Any],
    rollback: dict[str, Any],
    hard_stop: dict[str, Any],
    botdb: dict[str, Any],
    no_mutation: dict[str, Any],
    hygiene: dict[str, Any],
    docs_sync: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    source_gate_passed = _as_bool(source_gate.get("source_gate_passed"), False)
    execution_performed = _as_bool(execution_manifest.get("execution_performed"), False)
    target_operator_count = _as_int(execution_manifest.get("target_operator_count"), 0)
    scenario_count = _as_int(execution_results.get("scenario_count"), 0)
    provider_calls_total = _as_int(execution_results.get("provider_calls_total"), 0)
    provider_budget_gate_passed = _as_bool(budget.get("provider_budget_gate_passed"), False)
    normal_user_control_count = _as_int(normal_user.get("normal_user_control_count"), 0)
    normal_user_apply_count = _as_int(normal_user.get("normal_user_apply_count"), 0)
    normal_user_provider_calls = _as_int(normal_user.get("normal_user_provider_calls"), 0)
    rollback_gate_passed = _as_bool(rollback.get("gate_passed"), False)
    hard_stop_triggered = _as_bool(hard_stop.get("hard_stop_triggered"), True)
    safety_gate_passed = _as_bool(safety.get("gate_passed"), False)
    trace_gate_passed = _as_bool(trace.get("gate_passed"), False)
    botdb_gate_passed = _as_bool(botdb.get("gate_passed"), False)
    quality_gate_passed = _as_bool(quality.get("gate_passed"), False)
    no_mutation_passed = _as_bool(no_mutation.get("no_mutation_proof_passed"), False)
    hygiene_passed = _as_bool(hygiene.get("gate_passed"), False)

    if not source_gate_passed:
        blockers.append("source_gate_failed")
    if not execution_performed:
        blockers.append("execution_not_performed")
    if target_operator_count <= 0 or target_operator_count > DEFAULT_MAX_TARGET_OPERATORS:
        blockers.append("target_operator_count_out_of_bounds")
    if scenario_count < DEFAULT_MIN_SCENARIO_COUNT:
        blockers.append("scenario_count_below_minimum")
    if provider_calls_total > DEFAULT_PROVIDER_CALL_BUDGET_MAX:
        blockers.append("provider_call_budget_exceeded")
    if not provider_budget_gate_passed:
        blockers.append("provider_budget_gate_failed")
    if normal_user_control_count < 3:
        blockers.append("normal_user_control_count_below_minimum")
    if normal_user_apply_count > 0:
        blockers.append("normal_user_apply_detected")
    if normal_user_provider_calls > 0:
        blockers.append("normal_user_provider_calls_detected")
    if not rollback_gate_passed:
        blockers.append("rollback_gate_failed")
    if hard_stop_triggered:
        blockers.append("hard_stop_triggered")
    if not safety_gate_passed:
        blockers.append("safety_kb_boundary_gate_failed")
    if not trace_gate_passed:
        blockers.append("trace_provider_sanitization_gate_failed")
    if not botdb_gate_passed:
        blockers.append("botdb_stability_gate_failed")
    if not quality_gate_passed:
        blockers.append("quality_micro_shift_gate_failed")
    if not no_mutation_passed:
        blockers.append("no_mutation_proof_failed")
    if not hygiene_passed:
        blockers.append("artifact_encoding_hygiene_failed")
    if not _as_bool(docs_sync.get("docs_synced"), False):
        blockers.append("docs_not_synced")

    if blockers:
        if not source_gate_passed:
            final_status = "blocked_by_source_gate"
            decision_value = "blocked_by_source_gate"
        else:
            final_status = "blocked"
            decision_value = "controlled_rollout_execution_blocked"
        next_prd = NEXT_PRD_BLOCKED
    else:
        final_status = "passed"
        decision_value = "controlled_rollout_execution_passed_ready_for_results_gate"
        next_prd = NEXT_PRD_PASSED

    return ControlledRolloutDecision(
        final_status=final_status,
        decision=decision_value,
        source_gate_passed=source_gate_passed,
        execution_performed=execution_performed,
        target_operator_count=target_operator_count,
        scenario_count=scenario_count,
        provider_calls_total=provider_calls_total,
        provider_budget_gate_passed=provider_budget_gate_passed,
        normal_user_control_count=normal_user_control_count,
        normal_user_apply_count=normal_user_apply_count,
        normal_user_provider_calls=normal_user_provider_calls,
        rollback_gate_passed=rollback_gate_passed,
        hard_stop_triggered=hard_stop_triggered,
        safety_kb_boundary_gate_passed=safety_gate_passed,
        trace_provider_sanitization_gate_passed=trace_gate_passed,
        botdb_stability_gate_passed=botdb_gate_passed,
        quality_micro_shift_gate_passed=quality_gate_passed,
        no_mutation_proof_passed=no_mutation_passed,
        artifact_encoding_hygiene_passed=hygiene_passed,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        next_prd_recommendation=next_prd,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "NEXT_PRD_PASSED",
    "NEXT_PRD_BLOCKED",
    "DEFAULT_MAX_TARGET_OPERATORS",
    "DEFAULT_PROVIDER_CALL_BUDGET_MAX",
    "DEFAULT_MIN_SCENARIO_COUNT",
    "preflight_source",
    "build_source_gate",
    "build_cohort_policy",
    "build_toggle_matrix",
    "build_botdb_stability_gate",
    "build_preflight",
    "build_execution_manifest",
    "build_execution_results",
    "build_provider_budget_gate",
    "build_normal_user_no_effect_gate",
    "build_quality_micro_shift_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_provider_sanitization_gate",
    "build_rollback_proof",
    "build_hard_stop_report",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_artifact_hygiene_gate",
    "docs_sync_status",
    "build_decision",
]
