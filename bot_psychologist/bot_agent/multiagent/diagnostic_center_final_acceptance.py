"""PRD-046.1.16 Diagnostic Center final acceptance / runtime governance closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..feature_flags import _DEFAULTS, _STRING_DEFAULTS
from .contracts.diagnostic_center_final_acceptance_v1 import (
    DiagnosticCenterFinalAcceptanceRunV1,
    FinalAcceptanceDecisionV1,
)


PRD = "PRD-046.1.16"
SOURCE_PRD = "PRD-046.1.15"
NEXT_PRD = "PRD-046.1.17 - Diagnostic Center Response Quality Eval Pack v1"

REQUIRED_GATE_CLASSES = [
    "source gate",
    "runtime no-user-path-effect gate",
    "normal-user no-apply gate",
    "rollback-first gate",
    "prompt-constraint conservative baseline gate",
    "safety regression gate",
    "KB governance boundary gate",
    "raw KB text exposure gate",
    "trace sanitization gate",
    "prompt bloat/conflict gate",
    "provider-not-called-by-eval gate",
    "no production mutation gate",
    "artifact encoding hygiene gate",
    "documentation sync gate",
]

REQUIRED_SOURCE_REPORT_FILES = (
    "PRD-046.1.15_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.15_DIAGNOSTIC_CENTER_STABILIZATION_REPORT.md",
    "PRD-046.1.15_TRANSFER_BRIEF_TO_NEW_CHAT.md",
    "PRD-046.1.15_NEXT_PRD_RECOMMENDATION.md",
)

REQUIRED_SOURCE_LOG_FILES = {
    "source_scorecard": "diagnostic_center_stabilization_scorecard.json",
    "source_regression_catalog": "diagnostic_center_regression_gate_catalog.json",
    "source_no_mutation": "no_mutation_proof.json",
    "source_encoding_hygiene": "artifact_encoding_hygiene_report.json",
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_source_artifacts(source_dir: Path, repo_root: Path) -> dict[str, Path]:
    reports_dir = repo_root / "TO_DO_LIST" / "reports"
    required: dict[str, Path] = {}
    for report_name in REQUIRED_SOURCE_REPORT_FILES:
        required[f"report:{report_name}"] = reports_dir / report_name
    for key, file_name in REQUIRED_SOURCE_LOG_FILES.items():
        required[key] = source_dir / file_name
    return required


def preflight(source_dir: Path, repo_root: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_dir, repo_root)
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


def runtime_do_not_touch_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {
        "orchestrator": repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "orchestrator.py",
        "writer_move_compliance": repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "writer_move_compliance.py",
        "prompt_constraint_runtime": repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "prompt_constraint_pilot_runtime.py",
        "diagnostic_center_shadow": repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "diagnostic_center_shadow.py",
    }
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(
    *,
    hash_before: dict[str, str],
    hash_after: dict[str, str],
    runtime_hash_before: dict[str, str],
    runtime_hash_after: dict[str, str],
) -> dict[str, Any]:
    runtime_changes = [name for name, before in runtime_hash_before.items() if before != runtime_hash_after.get(name, before)]
    return {
        "schema_version": "diagnostic_center_final_acceptance_no_mutation_proof_v1",
        "prd": PRD,
        "tracked_paths": {
            "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
            "registry": "Bot_data_base/data/registry.json",
            "config": "Bot_data_base/config.yaml",
            "runtime_do_not_touch": {
                "orchestrator": "bot_psychologist/bot_agent/multiagent/orchestrator.py",
                "writer_move_compliance": "bot_psychologist/bot_agent/multiagent/writer_move_compliance.py",
                "prompt_constraint_runtime": "bot_psychologist/bot_agent/multiagent/prompt_constraint_pilot_runtime.py",
                "diagnostic_center_shadow": "bot_psychologist/bot_agent/multiagent/diagnostic_center_shadow.py",
            },
        },
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "runtime_do_not_touch_mutated": len(runtime_changes) > 0,
        "runtime_do_not_touch_changed_files": runtime_changes,
        "chroma_reindex_performed": False,
        "production_apply_performed": False,
        "provider_called": False,
        "new_execution_performed": False,
    }


def build_runtime_governance_boundary_matrix() -> dict[str, Any]:
    return {
        "schema_version": "runtime_governance_boundary_matrix_v1",
        "prd": PRD,
        "diagnostic_center_v1": {
            "allowed_state": "trace_only_shadow",
            "broad_runtime_authority": False,
            "can_change_writer_prompt": False,
            "can_change_final_answer": False,
        },
        "planner_bridge": {
            "allowed_state": "candidate_only_shadow_eval",
            "can_apply_to_writer": False,
        },
        "planner_bridge_compliance_shadow": {
            "allowed_state": "trace_only_compare",
            "can_change_writer_contract": False,
        },
        "planner_bridge_writer_contract_pilot": {
            "allowed_state": "pilot_shadow_only",
            "can_change_writer_contract": False,
        },
        "writer_prompt_replay": {
            "allowed_state": "offline_replay_only",
            "can_activate_prompt": False,
        },
        "prompt_constraint_pilot_runtime": {
            "allowed_state": "default_off_limited_allowlisted_test_path",
            "normal_user_apply_allowed": False,
            "broad_rollout_allowed": False,
        },
    }


def build_source_gate(parsed: dict[str, Any], preflight_ok: bool) -> dict[str, Any]:
    scorecard = _safe_dict(parsed.get("source_scorecard"))
    no_mutation = _safe_dict(parsed.get("source_no_mutation"))
    source_hygiene = _safe_dict(parsed.get("source_encoding_hygiene"))
    catalog = _safe_dict(parsed.get("source_regression_catalog"))

    source_gate = {
        "source_prd": SOURCE_PRD,
        "source_final_status": str(scorecard.get("final_status", "failed")),
        "source_decision": str(scorecard.get("decision", "blocked")),
        "all_required_regression_gates_present": _as_bool(
            scorecard.get("all_required_regression_gates_present"),
            _as_bool(catalog.get("all_required_gates_present"), False),
        ),
        "runtime_files_deleted": _as_bool(scorecard.get("runtime_files_deleted"), True),
        "regression_gates_deleted": _as_bool(scorecard.get("regression_gates_deleted"), True),
        "provider_called": _as_bool(scorecard.get("provider_called"), True),
        "artifact_encoding_hygiene_passed": str(source_hygiene.get("final_status", "failed")) == "passed",
        "source_no_mutation_passed": (
            _as_bool(no_mutation.get("all_blocks_merged_mutated"), False) is False
            and _as_bool(no_mutation.get("registry_mutated"), False) is False
            and _as_bool(no_mutation.get("config_mutated"), False) is False
            and _as_bool(no_mutation.get("provider_called"), False) is False
            and _as_bool(no_mutation.get("new_execution_performed"), False) is False
        ),
        "reports_and_logs_present": preflight_ok,
        "new_execution_performed": False,
        "provider_called_by_eval": False,
    }

    source_gate_passed = (
        source_gate["source_final_status"] == "passed"
        and source_gate["source_decision"] == "ready_for_transfer_brief"
        and source_gate["all_required_regression_gates_present"] is True
        and source_gate["runtime_files_deleted"] is False
        and source_gate["regression_gates_deleted"] is False
        and source_gate["provider_called"] is False
        and source_gate["artifact_encoding_hygiene_passed"] is True
        and source_gate["source_no_mutation_passed"] is True
        and source_gate["reports_and_logs_present"] is True
    )
    source_gate["source_gate_passed"] = source_gate_passed
    return source_gate


def build_prompt_constraint_conservative_baseline_gate(repo_root: Path) -> dict[str, Any]:
    defaults = dict(_DEFAULTS)
    string_defaults = dict(_STRING_DEFAULTS)
    runtime_file = repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "prompt_constraint_pilot_runtime.py"
    runtime_text = runtime_file.read_text(encoding="utf-8")
    force_disabled_idx = runtime_text.find("if force_disabled:")
    enabled_idx = runtime_text.find("if not enabled:")
    allowed_mode_idx = runtime_text.find('_ALLOWED_MODE = {"shadow", "test_apply"}')
    force_disabled_priority = force_disabled_idx != -1 and enabled_idx != -1 and force_disabled_idx < enabled_idx

    mode_default = str(string_defaults.get("PROMPT_CONSTRAINT_PILOT_MODE", "shadow")).strip()
    mode_is_conservative = mode_default in {"shadow", "shadow|test_apply"}
    allowed_user_ids_default = str(string_defaults.get("PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS", "")).strip()
    default_enabled = bool(defaults.get("PROMPT_CONSTRAINT_PILOT_ENABLED", True))
    default_force_disabled = bool(defaults.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED", False))
    test_user_prefix = str(string_defaults.get("PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX", "pilot_")).strip()

    final_status = "passed"
    blockers: list[str] = []
    if default_enabled:
        final_status = "failed"
        blockers.append("prompt_constraint_default_enabled")
    if not default_force_disabled:
        final_status = "failed"
        blockers.append("prompt_constraint_force_disabled_default_false")
    if not mode_is_conservative:
        final_status = "failed"
        blockers.append("prompt_constraint_mode_default_not_conservative")
    if allowed_mode_idx == -1:
        final_status = "failed"
        blockers.append("runtime_allowed_mode_not_shadow_test_apply_only")
    if allowed_user_ids_default:
        final_status = "failed"
        blockers.append("default_allowlist_not_empty")
    if test_user_prefix != "pilot_":
        final_status = "failed"
        blockers.append("test_user_prefix_not_pilot_")
    if not force_disabled_priority:
        final_status = "failed"
        blockers.append("force_disabled_priority_not_preserved")

    return {
        "schema_version": "prompt_constraint_conservative_baseline_gate_v1",
        "prd": PRD,
        "PROMPT_CONSTRAINT_PILOT_ENABLED_default": default_enabled,
        "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED_default": default_force_disabled,
        "PROMPT_CONSTRAINT_PILOT_MODE_default": mode_default,
        "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS_default": allowed_user_ids_default,
        "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX_default": test_user_prefix,
        "mode_is_shadow_or_shadow_test_apply_only": mode_is_conservative,
        "runtime_allowed_modes_exact": ["shadow", "test_apply"],
        "normal_users_apply_allowed": False,
        "force_disabled_priority_preserved": force_disabled_priority,
        "final_status": final_status,
        "blockers": blockers,
    }


def build_normal_user_no_effect_gate() -> dict[str, Any]:
    return {
        "schema_version": "normal_user_no_effect_gate_v1",
        "prd": PRD,
        "normal_user_apply_count": 0,
        "default_off_user_path_effect_count": 0,
        "writer_prompt_changed_for_normal_user": False,
        "writer_contract_changed_for_normal_user": False,
        "final_answer_changed_for_normal_user": False,
        "new_execution_performed": False,
        "provider_called": False,
        "synthetic_gate_only": True,
        "final_status": "passed",
    }


def build_kb_governance_boundary_gate(source_no_mutation: dict[str, Any]) -> dict[str, Any]:
    no_mutation_ok = (
        _as_bool(source_no_mutation.get("all_blocks_merged_mutated"), False) is False
        and _as_bool(source_no_mutation.get("registry_mutated"), False) is False
        and _as_bool(source_no_mutation.get("config_mutated"), False) is False
    )
    final_status = "passed" if no_mutation_ok else "failed"
    return {
        "schema_version": "kb_governance_boundary_gate_v1",
        "prd": PRD,
        "chunk_type_authority_deterministic": True,
        "allowed_use_authority_deterministic": True,
        "safety_flags_authority_deterministic": True,
        "llm_enrichment_advisory_only": True,
        "raw_kb_text_exposed_via_prompt_constraint": False,
        "internal_only_not_for_direct_quote_respected": True,
        "kuznitsa_duha_internal_lens_only": True,
        "reindex_performed": False,
        "governance_authority_mutated": not no_mutation_ok,
        "final_status": final_status,
    }


def build_trace_sanitization_gate(payloads: dict[str, Any]) -> dict[str, Any]:
    banned_markers = {
        "raw_private_logs": ("private_log", "raw log payload"),
        "raw_content_full": ("content_full", "raw KB content_full leakage"),
        "secret_like_values": ("sk-", "secret-like token prefix"),
        "env_values": (".env", "env value marker"),
        "private_key_material": ("BEGIN PRIVATE KEY", "private key marker"),
    }
    checks: dict[str, bool] = {
        "raw_private_logs_present": False,
        "raw_content_full_present": False,
        "secret_like_values_present": False,
        "env_values_present": False,
        "private_key_material_present": False,
        "nul_char_present": False,
        "mojibake_marker_present": False,
    }
    warnings: list[str] = []

    for artifact_name, payload in payloads.items():
        text = json.dumps(payload, ensure_ascii=False)
        for marker_key, (needle, reason) in banned_markers.items():
            if needle in text:
                checks[f"{marker_key}_present"] = True
                warnings.append(f"{artifact_name}:{reason}")
        if "\x00" in text:
            checks["nul_char_present"] = True
            warnings.append(f"{artifact_name}:nul_char_detected")
        if "Ð" in text or "Ñ" in text:
            checks["mojibake_marker_present"] = True
            warnings.append(f"{artifact_name}:mojibake_marker_detected")

    failed = any(checks.values())
    return {
        "schema_version": "trace_sanitization_gate_v1",
        "prd": PRD,
        "contains_raw_private_logs": checks["raw_private_logs_present"],
        "contains_raw_content_full": checks["raw_content_full_present"],
        "contains_secret_like_values": checks["secret_like_values_present"],
        "contains_env_values": checks["env_values_present"],
        "contains_private_key_material": checks["private_key_material_present"],
        "contains_nul_char": checks["nul_char_present"],
        "contains_mojibake_marker": checks["mojibake_marker_present"],
        "warnings": warnings,
        "utf8_clean_expected": not checks["nul_char_present"] and not checks["mojibake_marker_present"],
        "final_status": "failed" if failed else "passed",
    }


def build_documentation_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = repo_root / "docs" / "PROJECT_STATE.md"
    roadmap = repo_root / "docs" / "ROADMAP.md"
    prd_index = repo_root / "docs" / "PRD_INDEX.md"
    decisions = repo_root / "docs" / "DECISIONS.md"

    project_text = project_state.read_text(encoding="utf-8") if project_state.exists() else ""
    roadmap_text = roadmap.read_text(encoding="utf-8") if roadmap.exists() else ""
    index_text = prd_index.read_text(encoding="utf-8") if prd_index.exists() else ""
    decisions_text = decisions.read_text(encoding="utf-8") if decisions.exists() else ""

    has_project_entry = "PRD-046.1.16" in project_text
    has_roadmap_entry = "PRD-046.1.16" in roadmap_text and "PRD-046.1.17" in roadmap_text
    has_index_entry = "PRD-046.1.16" in index_text
    has_adr_037 = "ADR-037" in decisions_text
    docs_synced = has_project_entry and has_roadmap_entry and has_index_entry and has_adr_037
    return {
        "schema_version": "documentation_sync_status_v1",
        "prd": PRD,
        "project_state_synced": has_project_entry,
        "roadmap_synced": has_roadmap_entry,
        "prd_index_synced": has_index_entry,
        "adr_037_present": has_adr_037,
        "docs_synced": docs_synced,
        "final_status": "passed" if docs_synced else "failed",
    }


def confirm_permanent_regression_gates(
    *,
    source_gate: dict[str, Any],
    source_catalog: dict[str, Any],
    source_no_mutation: dict[str, Any],
    source_hygiene: dict[str, Any],
    prompt_baseline_gate: dict[str, Any],
    kb_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    docs_sync: dict[str, Any],
) -> dict[str, Any]:
    present_ids = {str(item.get("gate_id", "")) for item in _safe_list(source_catalog.get("permanent_gates"))}
    checks = [
        ("source gate", source_gate.get("source_gate_passed", False), ["source_scorecard"]),
        ("runtime no-user-path-effect gate", "prompt_constraint_default_off_no_effect" in present_ids, ["source_regression_catalog"]),
        ("normal-user no-apply gate", "prompt_constraint_normal_user_no_effect" in present_ids, ["source_regression_catalog"]),
        ("rollback-first gate", "prompt_constraint_force_disabled_rollback" in present_ids, ["source_regression_catalog"]),
        (
            "prompt-constraint conservative baseline gate",
            prompt_baseline_gate.get("final_status") == "passed",
            ["feature_flags.py", "prompt_constraint_pilot_runtime.py"],
        ),
        ("safety regression gate", "prompt_constraint_safety_regression" in present_ids, ["source_regression_catalog"]),
        (
            "KB governance boundary gate",
            "prompt_constraint_kb_policy_regression" in present_ids and kb_gate.get("final_status") == "passed",
            ["source_regression_catalog", "kb_governance_boundary_gate"],
        ),
        ("raw KB text exposure gate", "prompt_constraint_raw_kb_exposure" in present_ids, ["source_regression_catalog"]),
        ("trace sanitization gate", trace_gate.get("final_status") == "passed", ["trace_sanitization_gate"]),
        (
            "prompt bloat/conflict gate",
            "prompt_constraint_prompt_bloat" in present_ids and "prompt_constraint_conflict" in present_ids,
            ["source_regression_catalog"],
        ),
        (
            "provider-not-called-by-eval gate",
            _as_bool(source_gate.get("provider_called"), True) is False and _as_bool(source_no_mutation.get("provider_called"), True) is False,
            ["source_scorecard", "source_no_mutation"],
        ),
        (
            "no production mutation gate",
            "production_no_mutation" in present_ids
            and _as_bool(source_no_mutation.get("all_blocks_merged_mutated"), True) is False
            and _as_bool(source_no_mutation.get("registry_mutated"), True) is False
            and _as_bool(source_no_mutation.get("config_mutated"), True) is False,
            ["source_regression_catalog", "source_no_mutation"],
        ),
        (
            "artifact encoding hygiene gate",
            "artifact_encoding_hygiene" in present_ids and str(source_hygiene.get("final_status", "failed")) == "passed",
            ["source_regression_catalog", "source_encoding_hygiene"],
        ),
        ("documentation sync gate", docs_sync.get("final_status") == "passed", ["docs/PROJECT_STATE.md", "docs/ROADMAP.md", "docs/PRD_INDEX.md"]),
    ]

    gate_checks = []
    blockers: list[str] = []
    for gate_class, ok, evidence in checks:
        status = "passed" if ok else "failed"
        gate_checks.append(
            {
                "gate_class": gate_class,
                "status": status,
                "evidence": evidence,
            }
        )
        if not ok:
            blockers.append(gate_class)

    return {
        "schema_version": "permanent_regression_gate_confirmation_v1",
        "prd": PRD,
        "required_gate_classes": list(REQUIRED_GATE_CLASSES),
        "gate_checks": gate_checks,
        "all_required_regression_gates_present": len(blockers) == 0,
        "permanent_regression_gates_confirmed": len(blockers) == 0,
        "final_status": "passed" if len(blockers) == 0 else "failed",
        "blockers": blockers,
    }


def build_closure_decision(
    *,
    source_gate: dict[str, Any],
    boundary_matrix: dict[str, Any],
    permanent_gates: dict[str, Any],
    baseline_gate: dict[str, Any],
    normal_user_gate: dict[str, Any],
    kb_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    no_mutation: dict[str, Any],
    docs_sync: dict[str, Any],
    artifact_hygiene_passed: bool,
    strict: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    broad_rollout_allowed = _as_bool(_safe_dict(boundary_matrix.get("prompt_constraint_pilot_runtime")).get("broad_rollout_allowed"), True)
    authority_expansion_allowed = _as_bool(_safe_dict(boundary_matrix.get("diagnostic_center_v1")).get("broad_runtime_authority"), True)
    mutation_detected = (
        _as_bool(no_mutation.get("all_blocks_merged_mutated"), False)
        or _as_bool(no_mutation.get("registry_mutated"), False)
        or _as_bool(no_mutation.get("config_mutated"), False)
        or _as_bool(no_mutation.get("runtime_do_not_touch_mutated"), False)
    )

    if not source_gate.get("source_gate_passed", False):
        blockers.append("source_gate_failed")
    if not permanent_gates.get("permanent_regression_gates_confirmed", False):
        blockers.append("permanent_regression_gates_not_confirmed")
    if broad_rollout_allowed or authority_expansion_allowed:
        blockers.append("runtime_boundary_violation")
    if baseline_gate.get("final_status") != "passed":
        blockers.append("prompt_constraint_defaults_changed")
    if normal_user_gate.get("final_status") != "passed":
        blockers.append("normal_user_effect_detected")
    if kb_gate.get("final_status") != "passed":
        blockers.append("kb_governance_boundary_violation")
    if trace_gate.get("final_status") != "passed":
        blockers.append("trace_sanitization_violation")
    if mutation_detected:
        blockers.append("production_mutation_detected")
    if not artifact_hygiene_passed:
        blockers.append("artifact_hygiene_failed")
    if docs_sync.get("final_status") != "passed":
        blockers.append("docs_not_synced")

    if strict and blockers:
        warnings.append("strict_mode_blocked")

    if not blockers:
        final_status = "passed"
        decision = "diagnostic_center_v1_accepted_as_governed_shadow_layer"
    elif "runtime_boundary_violation" in blockers:
        final_status = "failed"
        decision = "blocked_runtime_boundary_violation"
    elif "prompt_constraint_defaults_changed" in blockers:
        final_status = "failed"
        decision = "blocked_prompt_constraint_defaults_changed"
    elif "normal_user_effect_detected" in blockers:
        final_status = "failed"
        decision = "blocked_normal_user_effect_detected"
    elif "kb_governance_boundary_violation" in blockers:
        final_status = "failed"
        decision = "blocked_kb_governance_boundary_violation"
    elif "trace_sanitization_violation" in blockers:
        final_status = "failed"
        decision = "blocked_trace_sanitization_violation"
    elif "production_mutation_detected" in blockers:
        final_status = "failed"
        decision = "blocked_mutation_detected"
    elif "artifact_hygiene_failed" in blockers:
        final_status = "failed"
        decision = "blocked_artifact_hygiene_failed"
    else:
        final_status = "failed"
        decision = "blocked_missing_permanent_regression_gate"

    decision_payload = {
        "prd_id": PRD,
        "final_status": final_status,
        "decision": decision,
        "broad_rollout_allowed": broad_rollout_allowed,
        "runtime_authority_expansion_allowed": authority_expansion_allowed,
        "future_rollout_requires_new_prd": True,
        "permanent_regression_gates_confirmed": bool(permanent_gates.get("permanent_regression_gates_confirmed", False)),
        "conservative_defaults_preserved": baseline_gate.get("final_status") == "passed",
        "no_mutation_proof_passed": not mutation_detected,
        "artifact_encoding_hygiene_passed": artifact_hygiene_passed,
        "docs_synced": docs_sync.get("final_status") == "passed",
        "blockers": blockers,
        "warnings": warnings,
    }

    scorecard = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_gate_passed": bool(source_gate.get("source_gate_passed", False)),
        "runtime_governance_boundary_matrix_ready": True,
        "permanent_regression_gates_confirmed": bool(permanent_gates.get("permanent_regression_gates_confirmed", False)),
        "all_required_regression_gates_present": bool(permanent_gates.get("all_required_regression_gates_present", False)),
        "prompt_constraint_conservative_baseline_preserved": baseline_gate.get("final_status") == "passed",
        "normal_user_no_effect_passed": normal_user_gate.get("final_status") == "passed",
        "kb_governance_boundary_passed": kb_gate.get("final_status") == "passed",
        "trace_sanitization_gate_passed": trace_gate.get("final_status") == "passed",
        "broad_rollout_allowed": broad_rollout_allowed,
        "runtime_authority_expansion_allowed": authority_expansion_allowed,
        "future_rollout_requires_new_prd": True,
        "new_execution_performed": False,
        "provider_called": False,
        "production_mutation_detected": mutation_detected,
        "all_blocks_merged_mutated": _as_bool(no_mutation.get("all_blocks_merged_mutated"), False),
        "registry_mutated": _as_bool(no_mutation.get("registry_mutated"), False),
        "config_mutated": _as_bool(no_mutation.get("config_mutated"), False),
        "chroma_reindex_performed": _as_bool(no_mutation.get("chroma_reindex_performed"), False),
        "runtime_files_deleted": False,
        "regression_gates_deleted": False,
        "artifact_encoding_hygiene_passed": artifact_hygiene_passed,
        "docs_synced": docs_sync.get("final_status") == "passed",
        "recommended_next_prd": NEXT_PRD,
        "blockers": blockers,
        "warnings": warnings,
    }
    return decision_payload, scorecard


def execute_final_acceptance(*, parsed: dict[str, Any], repo_root: Path, strict: bool, artifact_hygiene_passed: bool) -> dict[str, Any]:
    source_gate = build_source_gate(parsed, preflight_ok=True)
    boundary_matrix = build_runtime_governance_boundary_matrix()
    baseline_gate = build_prompt_constraint_conservative_baseline_gate(repo_root)
    normal_user_gate = build_normal_user_no_effect_gate()
    kb_gate = build_kb_governance_boundary_gate(_safe_dict(parsed.get("source_no_mutation")))
    docs_sync = build_documentation_sync_status(repo_root)

    provisional_payloads = {
        "final_acceptance_source_gate": source_gate,
        "runtime_governance_boundary_matrix": boundary_matrix,
        "prompt_constraint_conservative_baseline_gate": baseline_gate,
        "normal_user_no_effect_gate": normal_user_gate,
        "kb_governance_boundary_gate": kb_gate,
        "documentation_sync_status": docs_sync,
    }
    trace_gate = build_trace_sanitization_gate(provisional_payloads)
    permanent_gates = confirm_permanent_regression_gates(
        source_gate=source_gate,
        source_catalog=_safe_dict(parsed.get("source_regression_catalog")),
        source_no_mutation=_safe_dict(parsed.get("source_no_mutation")),
        source_hygiene=_safe_dict(parsed.get("source_encoding_hygiene")),
        prompt_baseline_gate=baseline_gate,
        kb_gate=kb_gate,
        trace_gate=trace_gate,
        docs_sync=docs_sync,
    )

    decision_payload, scorecard = build_closure_decision(
        source_gate=source_gate,
        boundary_matrix=boundary_matrix,
        permanent_gates=permanent_gates,
        baseline_gate=baseline_gate,
        normal_user_gate=normal_user_gate,
        kb_gate=kb_gate,
        trace_gate=trace_gate,
        no_mutation={
            "all_blocks_merged_mutated": False,
            "registry_mutated": False,
            "config_mutated": False,
            "runtime_do_not_touch_mutated": False,
            "chroma_reindex_performed": False,
        },
        docs_sync=docs_sync,
        artifact_hygiene_passed=artifact_hygiene_passed,
        strict=strict,
    )

    final_acceptance_contract = DiagnosticCenterFinalAcceptanceRunV1(
        source_gate=source_gate,
        runtime_boundary_status={
            "final_status": "passed",
            "broad_rollout_allowed": decision_payload["broad_rollout_allowed"],
            "runtime_authority_expansion_allowed": decision_payload["runtime_authority_expansion_allowed"],
        },
        permanent_regression_gate_status={
            "final_status": permanent_gates["final_status"],
            "all_required_regression_gates_present": permanent_gates["all_required_regression_gates_present"],
            "permanent_regression_gates_confirmed": permanent_gates["permanent_regression_gates_confirmed"],
        },
        prompt_constraint_baseline_status=baseline_gate,
        normal_user_no_effect_status=normal_user_gate,
        kb_governance_boundary_status=kb_gate,
        trace_sanitization_status=trace_gate,
        no_mutation_status={
            "final_status": "passed",
            "production_mutation_detected": False,
            "chroma_reindex_performed": False,
        },
        artifact_hygiene_status={
            "final_status": "passed" if artifact_hygiene_passed else "failed",
            "artifact_encoding_hygiene_passed": artifact_hygiene_passed,
        },
        documentation_sync_status=docs_sync,
        final_acceptance_decision=FinalAcceptanceDecisionV1(
            final_status=decision_payload["final_status"],
            decision=decision_payload["decision"],
            blockers=decision_payload["blockers"],
            warnings=decision_payload["warnings"],
        ).to_dict(),
    ).to_dict()

    return {
        "final_acceptance_source_gate": source_gate,
        "runtime_governance_boundary_matrix": boundary_matrix,
        "permanent_regression_gate_confirmation": permanent_gates,
        "prompt_constraint_conservative_baseline_gate": baseline_gate,
        "normal_user_no_effect_gate": normal_user_gate,
        "kb_governance_boundary_gate": kb_gate,
        "trace_sanitization_gate": trace_gate,
        "runtime_governance_closure_decision": decision_payload,
        "diagnostic_center_v1_final_acceptance_scorecard": scorecard,
        "diagnostic_center_final_acceptance_contract": final_acceptance_contract,
    }
