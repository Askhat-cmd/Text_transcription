"""PRD-046.1.35 creator live results / rollback / quality gate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_creator_live_results_gate_v1 import (
    EvidenceStrengthAudit,
    PRD_ID,
    ResultsDecision,
    ResultsScorecard,
    SOURCE_PRD_ID,
    SourceArtifactsManifest,
)

PRD = PRD_ID
SOURCE_PRD = SOURCE_PRD_ID

DECISION_CONTINUE = "continue_creator_limited_observation"
DECISION_EVIDENCE_HOTFIX = "evidence_incomplete_hotfix_required"
DECISION_ROLLBACK = "rollback_required"
DECISION_BLOCKED = "blocked_fix_required"

NEXT_PRD_CONTINUE = "PRD-046.1.36 - Final Creator Limited Runtime Acceptance / Next Phase Transfer v1"
NEXT_PRD_HF1 = "PRD-046.1.35-HF1 - Creator Live Evidence Capture Repair / Real Sanitized Turn Proof v1"
NEXT_PRD_RB1 = "PRD-046.1.35-RB1 - Diagnostic Center Creator Live Rollback / Safety Repair v1"

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

REQUIRED_REPORTS = [
    "PRD-046.1.34_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.34_CREATOR_LIVE_ACTIVATION_REPORT.md",
    "PRD-046.1.34_WEB_CHAT_SMOKE_REPORT.md",
    "PRD-046.1.34_ADMIN_RUNTIME_CONTROLS_REPORT.md",
    "PRD-046.1.34_DIAGNOSTIC_TRACE_MONITOR_REPORT.md",
    "PRD-046.1.34_ROLLBACK_HARD_STOP_REPORT.md",
    "PRD-046.1.34_NEXT_PRD_RECOMMENDATION.md",
]

REQUIRED_LOGS = [
    "live_activation_scorecard.json",
    "source_gate.json",
    "creator_identity_gate.json",
    "admin_runtime_controls_gate.json",
    "web_chat_creator_live_smoke.json",
    "normal_user_no_effect_gate.json",
    "diagnostic_center_active_influence_gate.json",
    "rollback_kill_switch_gate.json",
    "hard_stop_gate.json",
    "safety_kb_boundary_gate.json",
    "trace_provider_sanitization_gate.json",
    "trace_storage_gate.json",
    "diagnostic_center_monitor_gate.json",
    "trace_clearance_policy_gate.json",
    "provider_budget_gate.json",
    "no_mutation_proof.json",
    "docs_consistency_gate.json",
    "sanitized_trace_sample.json",
]

SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_source_artifacts(source_logs_dir: Path, source_reports_dir: Path) -> dict[str, Path]:
    required: dict[str, Path] = {}
    for name in REQUIRED_REPORTS:
        required[f"report:{name}"] = source_reports_dir / name
    for name in REQUIRED_LOGS:
        required[f"log:{name}"] = source_logs_dir / name
    return required


def preflight_source_artifacts(source_logs_dir: Path, source_reports_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_logs_dir, source_reports_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed_json: dict[str, Any] = {}
    text_reports: dict[str, str] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() == ".json":
            try:
                parsed_json[key] = _read_json(path)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{key}:{exc.__class__.__name__}")
        else:
            text_reports[key] = path.read_text(encoding="utf-8")

    consistency_warnings: list[str] = []
    impl_text = text_reports.get("report:PRD-046.1.34_IMPLEMENTATION_REPORT.md", "")
    next_text = text_reports.get("report:PRD-046.1.34_NEXT_PRD_RECOMMENDATION.md", "")
    scorecard = _safe_dict(parsed_json.get("log:live_activation_scorecard.json"))
    if impl_text and scorecard:
        impl_status = _extract_inline_code_value(impl_text, "final_status")
        impl_decision = _extract_inline_code_value(impl_text, "decision")
        if impl_status and impl_status != str(scorecard.get("final_status", "")):
            consistency_warnings.append("implementation_report_final_status_mismatch")
        if impl_decision and impl_decision != str(scorecard.get("decision", "")):
            consistency_warnings.append("implementation_report_decision_mismatch")
    if next_text and "PRD-046.1.35" not in next_text:
        consistency_warnings.append("next_prd_report_missing_046_1_35_reference")

    present_count = len(required) - len(missing)
    manifest = SourceArtifactsManifest(
        required_artifact_count=len(required),
        present_artifact_count=present_count,
        missing_artifact_count=len(missing),
        parse_error_count=len(parse_errors),
        report_consistency_warning_count=len(consistency_warnings),
        source_artifacts_gate="passed" if not missing and not parse_errors else "blocked",
        missing_artifacts=missing,
        parse_errors=parse_errors,
        consistency_warnings=consistency_warnings,
    ).to_dict()
    return {
        "required": {k: str(v.resolve()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "parsed_json": parsed_json,
        "text_reports": text_reports,
        "consistency_warnings": consistency_warnings,
        "source_artifacts_manifest": manifest,
        "ok": not missing and not parse_errors,
    }


def _extract_inline_code_value(text: str, key: str) -> str:
    pattern = re.compile(rf"-\s*{re.escape(key)}:\s*`([^`]+)`")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def build_evidence_strength_audit(preflight: dict[str, Any]) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed_json"))
    items: list[dict[str, Any]] = []
    counts = {
        "actual_live_turn_evidence": 0,
        "runtime_probe_evidence": 0,
        "simulated_gate_evidence": 0,
        "missing_evidence": 0,
        "strong": 0,
        "medium": 0,
        "weak": 0,
        "missing": 0,
    }

    web_chat = _safe_dict(parsed.get("log:web_chat_creator_live_smoke.json"))
    if web_chat:
        has_turn_fields = any(k in web_chat for k in ("turn_id", "session_id", "trace_id", "timestamp", "answer_preview"))
        if _as_bool(web_chat.get("answer_received"), False) and not has_turn_fields:
            klass = "simulated_gate_evidence"
            strength = "weak"
            reason = "message/answer flags present without real turn/session/timestamp artifacts"
        else:
            klass = "runtime_probe_evidence"
            strength = "medium"
            reason = "runtime smoke evidence without complete live turn proof"
    else:
        klass = "missing_evidence"
        strength = "missing"
        reason = "web_chat_creator_live_smoke.json missing or invalid"
    items.append(
        {
            "artifact": "web_chat_creator_live_smoke",
            "evidence_class": klass,
            "evidence_strength": strength,
            "reason": reason,
            "source_files": ["TO_DO_LIST/logs/PRD-046.1.34/web_chat_creator_live_smoke.json"],
        }
    )
    counts[klass] += 1
    counts[strength] += 1

    trace_sample = _safe_dict(parsed.get("log:sanitized_trace_sample.json"))
    if trace_sample:
        has_turn_id = bool(str(trace_sample.get("turn_id", "")).strip())
        has_runtime = str(trace_sample.get("runtime_mode", "")) == "creator_only"
        has_answer_preview = bool(str(trace_sample.get("answer_preview", "")).strip())
        has_timestamp = bool(str(trace_sample.get("timestamp", "")).strip())
        if has_turn_id and has_runtime and has_answer_preview and has_timestamp:
            klass = "actual_live_turn_evidence"
            strength = "strong"
            reason = "sanitized trace includes turn id, timestamp, runtime mode and answer preview"
        elif has_turn_id and has_runtime:
            klass = "runtime_probe_evidence"
            strength = "medium"
            reason = "trace sample proves creator path shape, but lacks full live answer evidence"
        else:
            klass = "simulated_gate_evidence"
            strength = "weak"
            reason = "trace sample exists but lacks concrete live-turn metadata"
    else:
        klass = "missing_evidence"
        strength = "missing"
        reason = "sanitized_trace_sample.json missing or invalid"
    items.append(
        {
            "artifact": "sanitized_trace_sample",
            "evidence_class": klass,
            "evidence_strength": strength,
            "reason": reason,
            "source_files": ["TO_DO_LIST/logs/PRD-046.1.34/sanitized_trace_sample.json"],
        }
    )
    counts[klass] += 1
    counts[strength] += 1

    monitor = _safe_dict(parsed.get("log:diagnostic_center_monitor_gate.json"))
    if monitor:
        klass = "runtime_probe_evidence"
        strength = "medium"
        reason = "monitor gate confirms runtime surface but not direct user turn payload"
    else:
        klass = "missing_evidence"
        strength = "missing"
        reason = "diagnostic_center_monitor_gate.json missing or invalid"
    items.append(
        {
            "artifact": "diagnostic_center_monitor_gate",
            "evidence_class": klass,
            "evidence_strength": strength,
            "reason": reason,
            "source_files": ["TO_DO_LIST/logs/PRD-046.1.34/diagnostic_center_monitor_gate.json"],
        }
    )
    counts[klass] += 1
    counts[strength] += 1

    if counts["missing_evidence"] > 0:
        gate = "blocked"
    elif counts["actual_live_turn_evidence"] >= 1:
        gate = "passed"
    else:
        gate = "warning"

    return EvidenceStrengthAudit(
        evidence_strength_gate=gate,
        actual_live_turn_evidence_count=counts["actual_live_turn_evidence"],
        runtime_probe_evidence_count=counts["runtime_probe_evidence"],
        simulated_gate_evidence_count=counts["simulated_gate_evidence"],
        missing_evidence_count=counts["missing_evidence"],
        strong_evidence_count=counts["strong"],
        medium_evidence_count=counts["medium"],
        weak_evidence_count=counts["weak"],
        missing_strength_count=counts["missing"],
        items=items,
    ).to_dict()


def build_live_results_quality_gate(*, evidence_audit: dict[str, Any], strict: bool) -> dict[str, Any]:
    has_actual = int(evidence_audit.get("actual_live_turn_evidence_count", 0)) >= 1
    passed = has_actual
    gate_state = "passed" if passed else ("blocked" if strict else "warning")
    reason = "actual_sanitized_live_turn_artifact_present" if passed else "actual_live_answer_artifact_missing"
    return {
        "schema_version": "diagnostic_center_creator_live_results_quality_gate_v1",
        "prd_id": PRD,
        "live_turn_quality_evaluable": has_actual,
        "answer_present": has_actual,
        "diagnostic_center_mode": "creator_only" if has_actual else "unknown",
        "writer_completed": has_actual,
        "validator_completed": has_actual,
        "trace_sanitized": has_actual,
        "quality_flags_present": has_actual,
        "quality_gate_passed": passed,
        "quality_gate_reason": reason,
        "live_results_quality_gate": gate_state,
    }


def build_rollback_quality_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    rollback = _safe_dict(parsed.get("log:rollback_kill_switch_gate.json"))
    hard_stop = _safe_dict(parsed.get("log:hard_stop_gate.json"))
    admin = _safe_dict(parsed.get("log:admin_runtime_controls_gate.json"))

    force_toggle_present = _as_bool(admin.get("force_disabled_toggle_present"), False)
    force_priority = _as_bool(rollback.get("force_disabled_priority_preserved"), False)
    all_users_locked = _as_bool(admin.get("all_users_control_locked"), False)
    hard_stop_passed = _as_bool(hard_stop.get("hard_stop_gate_passed"), False)
    rollback_passed = _as_bool(rollback.get("rollback_kill_switch_gate_passed"), False)
    gate_passed = force_toggle_present and force_priority and all_users_locked and hard_stop_passed and rollback_passed
    return {
        "schema_version": "diagnostic_center_creator_live_results_rollback_quality_gate_v1",
        "prd_id": PRD,
        "force_disabled_toggle_present": force_toggle_present,
        "force_disabled_priority_preserved": force_priority,
        "all_users_control_locked": all_users_locked,
        "hard_stop_gate_passed": hard_stop_passed,
        "rollback_kill_switch_gate_passed": rollback_passed,
        "rollback_quality_gate_passed": gate_passed,
        "rollback_quality_gate": "passed" if gate_passed else "blocked",
    }


def build_normal_user_boundary_proof(parsed: dict[str, Any]) -> dict[str, Any]:
    normal_gate = _safe_dict(parsed.get("log:normal_user_no_effect_gate.json"))
    scorecard = _safe_dict(parsed.get("log:live_activation_scorecard.json"))
    apply_effect = int(normal_gate.get("normal_user_apply_effect_count", 999))
    provider_calls = int(normal_gate.get("normal_user_provider_call_count", 999))
    writer_delta = int(normal_gate.get("writer_prompt_delta_count", 999))
    answer_delta = int(normal_gate.get("final_answer_path_delta_count", 999))
    leaks = int(normal_gate.get("trace_private_leak_count", 999))
    activation_allowed = _as_bool(scorecard.get("normal_user_activation_allowed"), True)
    all_users_enabled = _as_bool(scorecard.get("all_users_mode_enabled"), True)
    passed = (
        apply_effect == 0
        and provider_calls == 0
        and writer_delta == 0
        and answer_delta == 0
        and leaks == 0
        and activation_allowed is False
        and all_users_enabled is False
    )
    return {
        "schema_version": "diagnostic_center_creator_live_results_normal_user_boundary_v1",
        "prd_id": PRD,
        "normal_user_apply_effect_count": apply_effect,
        "normal_user_provider_call_count": provider_calls,
        "writer_prompt_delta_count": writer_delta,
        "final_answer_path_delta_count": answer_delta,
        "trace_private_leak_count": leaks,
        "normal_user_activation_allowed": activation_allowed,
        "all_users_mode_enabled": all_users_enabled,
        "normal_user_boundary_gate_passed": passed,
        "normal_user_boundary_gate": "passed" if passed else "blocked",
    }


def _scan_paths_for_secrets(paths: list[Path]) -> dict[str, bool]:
    raw_provider = False
    raw_private = False
    secrets = False
    env_committed = False
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        lower = path.name.lower()
        if lower == ".env" or lower.endswith(".env"):
            env_committed = True
        if "raw_provider_payload" in lower or "provider_response_raw" in lower:
            raw_provider = True
        if "private_log" in lower or lower.startswith("bot.log"):
            raw_private = True
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "OPENAI_API_KEY" in text or "BOT_TOKEN" in text or "DATABASE_URL" in text:
            secrets = True
        if SECRET_PATTERN.search(text):
            secrets = True
    return {
        "raw_provider_payload_committed": raw_provider,
        "raw_private_logs_committed": raw_private,
        "secrets_committed": secrets,
        "env_committed": env_committed,
    }


def build_trace_sanitization_results_gate(parsed: dict[str, Any], scan_paths: list[Path]) -> dict[str, Any]:
    source_trace = _safe_dict(parsed.get("log:trace_provider_sanitization_gate.json"))
    source_storage = _safe_dict(parsed.get("log:trace_storage_gate.json"))
    source_sample_present = bool(_safe_dict(parsed.get("log:sanitized_trace_sample.json")))
    scan = _scan_paths_for_secrets(scan_paths)
    raw_provider = _as_bool(source_trace.get("raw_provider_payload_committed"), False) or scan["raw_provider_payload_committed"]
    raw_private = _as_bool(source_trace.get("raw_private_logs_committed"), False) or scan["raw_private_logs_committed"]
    secrets = _as_bool(source_trace.get("secrets_committed"), False) or scan["secrets_committed"]
    env = _as_bool(source_trace.get("env_committed"), False) or scan["env_committed"]
    trace_sanitized_only = _as_bool(source_trace.get("trace_sanitized_only"), False)
    storage_passed = _as_bool(source_storage.get("trace_storage_gate_passed"), False)
    passed = (not raw_provider) and (not raw_private) and (not secrets) and (not env) and trace_sanitized_only and source_sample_present and storage_passed
    return {
        "schema_version": "diagnostic_center_creator_live_results_trace_sanitization_gate_v1",
        "prd_id": PRD,
        "raw_provider_payload_committed": raw_provider,
        "raw_private_logs_committed": raw_private,
        "secrets_committed": secrets,
        "env_committed": env,
        "trace_sanitized_only": trace_sanitized_only,
        "sanitized_trace_sample_present": source_sample_present,
        "trace_storage_gate_passed": storage_passed,
        "trace_sanitization_gate_passed": passed,
        "trace_sanitization_gate": "passed" if passed else "blocked",
    }


def build_provider_budget_results_gate(parsed: dict[str, Any]) -> dict[str, Any]:
    source = _safe_dict(parsed.get("log:provider_budget_gate.json"))
    creator = int(source.get("creator_live_provider_calls", -1))
    normal = int(source.get("normal_user_control_provider_calls", -1))
    total = int(source.get("total_provider_calls", -1))
    max_creator = int(source.get("max_creator_live_provider_calls", 8))
    max_normal = int(source.get("max_normal_user_control_provider_calls", 2))
    max_total = int(source.get("max_total_provider_calls", 10))
    counts_known = creator >= 0 and normal >= 0 and total >= 0
    passed = counts_known and creator <= max_creator and normal <= max_normal and total <= max_total
    return {
        "schema_version": "diagnostic_center_creator_live_results_provider_budget_gate_v1",
        "prd_id": PRD,
        "max_creator_live_provider_calls": max_creator,
        "max_normal_user_control_provider_calls": max_normal,
        "max_total_provider_calls": max_total,
        "creator_live_provider_calls": creator,
        "normal_user_control_provider_calls": normal,
        "total_provider_calls": total,
        "counts_known": counts_known,
        "provider_budget_gate_passed": passed,
        "provider_budget_gate": "passed" if passed else "blocked",
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {name: repo_root / rel for name, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str], source_parsed: dict[str, Any]) -> dict[str, Any]:
    source = _safe_dict(source_parsed.get("log:no_mutation_proof.json"))
    production_data_mutated = any(hash_before.get(k) != hash_after.get(k) for k in TRACKED_PRODUCTION_PATHS)
    source_passed = _as_bool(source.get("no_mutation_proof_passed"), False)
    kb_mutated = _as_bool(source.get("kb_registry_chroma_config_mutated"), False)
    runtime_changed = _as_bool(source.get("runtime_defaults_changed"), False)
    passed = (not production_data_mutated) and source_passed and (not kb_mutated) and (not runtime_changed)
    return {
        "schema_version": "diagnostic_center_creator_live_results_no_mutation_proof_v1",
        "prd_id": PRD,
        "production_data_mutated": production_data_mutated,
        "runtime_defaults_changed": runtime_changed,
        "kb_registry_chroma_config_mutated": kb_mutated,
        "source_no_mutation_proof_passed": source_passed,
        "no_mutation_proof_passed": passed,
    }


def _extract_next_section(roadmap_text: str) -> str:
    match = re.search(r"## Next\n(?P<section>[\s\S]*?)(\n## |\Z)", roadmap_text)
    return match.group("section") if match else ""


def build_docs_consistency_gate(*, project_state_text: str, roadmap_text: str, prd_index_text: str, decisions_text: str, expected_next: str) -> dict[str, Any]:
    next_section = _extract_next_section(roadmap_text)
    next_contains_expected = expected_next in roadmap_text
    stale = 0
    if "PRD-046.1.35 - Diagnostic Center Creator Live Results / Rollback / Quality Gate v1" in next_section:
        stale += 1
    duplicates = 1 if next_section.count(expected_next) > 1 else 0
    passed = (
        "PRD-046.1.35" in project_state_text
        and next_contains_expected
        and "| PRD-046.1.35 |" in prd_index_text
        and "ADR-054" in decisions_text
        and stale == 0
        and duplicates == 0
    )
    return {
        "schema_version": "diagnostic_center_creator_live_results_docs_consistency_gate_v1",
        "prd_id": PRD,
        "project_state_synced": "PRD-046.1.35" in project_state_text,
        "roadmap_synced": next_contains_expected,
        "prd_index_synced": "| PRD-046.1.35 |" in prd_index_text,
        "decisions_synced": "ADR-054" in decisions_text,
        "stale_next_prd_reference_count": stale,
        "duplicate_roadmap_next_item_count": duplicates,
        "docs_consistency_gate_passed": passed,
    }


def build_results_scorecard(
    *,
    source_manifest: dict[str, Any],
    evidence_audit: dict[str, Any],
    quality_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    normal_user_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    provider_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    docs_consistency_gate: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> dict[str, Any]:
    source_state = str(source_manifest.get("source_artifacts_gate", "blocked"))
    evidence_state = str(evidence_audit.get("evidence_strength_gate", "blocked"))
    quality_state = str(quality_gate.get("live_results_quality_gate", "blocked"))
    rollback_state = str(rollback_gate.get("rollback_quality_gate", "blocked"))
    normal_state = str(normal_user_gate.get("normal_user_boundary_gate", "blocked"))
    trace_state = str(trace_gate.get("trace_sanitization_gate", "blocked"))
    provider_state = str(provider_gate.get("provider_budget_gate", "blocked"))
    no_mut_state = "passed" if _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False) else "blocked"
    docs_state = "passed" if _as_bool(docs_consistency_gate.get("docs_consistency_gate_passed"), False) else "blocked"
    encoding_state = "passed" if artifact_encoding_hygiene_passed else "blocked"

    blockers: list[str] = []
    warnings: list[str] = []
    if rollback_state == "blocked" or normal_state == "blocked" or trace_state == "blocked":
        final_status = "rollback_required"
        decision = DECISION_ROLLBACK
        next_prd = NEXT_PRD_RB1
        blockers.append("safety_or_boundary_gate_failed")
    elif source_state == "blocked" or provider_state == "blocked" or no_mut_state == "blocked" or docs_state == "blocked" or encoding_state == "blocked":
        final_status = "blocked"
        decision = DECISION_BLOCKED
        next_prd = NEXT_PRD_HF1
        blockers.append("core_gate_blocked")
    elif int(evidence_audit.get("actual_live_turn_evidence_count", 0)) < 1 or evidence_state != "passed" or quality_state != "passed":
        final_status = "evidence_incomplete"
        decision = DECISION_EVIDENCE_HOTFIX
        next_prd = NEXT_PRD_HF1
        warnings.append("actual_live_turn_evidence_missing_or_weak")
    else:
        final_status = "passed"
        decision = DECISION_CONTINUE
        next_prd = NEXT_PRD_CONTINUE

    return ResultsScorecard(
        final_status=final_status,
        decision=decision,
        source_artifacts_gate=source_state,
        evidence_strength_gate=evidence_state,
        live_results_quality_gate=quality_state,
        rollback_quality_gate=rollback_state,
        normal_user_boundary_gate=normal_state,
        trace_sanitization_gate=trace_state,
        provider_budget_gate=provider_state,
        no_mutation_proof=no_mut_state,
        docs_consistency_gate=docs_state,
        artifact_encoding_hygiene=encoding_state,
        actual_live_turn_evidence_count=int(evidence_audit.get("actual_live_turn_evidence_count", 0)),
        runtime_probe_evidence_count=int(evidence_audit.get("runtime_probe_evidence_count", 0)),
        simulated_gate_evidence_count=int(evidence_audit.get("simulated_gate_evidence_count", 0)),
        missing_evidence_count=int(evidence_audit.get("missing_evidence_count", 0)),
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        next_prd_recommendation=next_prd,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()


def build_decision(scorecard: dict[str, Any]) -> dict[str, Any]:
    return ResultsDecision(
        final_status=str(scorecard.get("final_status", "blocked")),
        decision=str(scorecard.get("decision", DECISION_BLOCKED)),
        blockers=_safe_list(scorecard.get("blockers")),
        warnings=_safe_list(scorecard.get("warnings")),
    ).to_dict()


def execute_results_gate(
    *,
    preflight: dict[str, Any],
    hash_before: dict[str, str],
    hash_after: dict[str, str],
    docs_consistency_gate: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
    strict: bool,
    scan_paths: list[Path],
) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed_json"))
    source_manifest = _safe_dict(preflight.get("source_artifacts_manifest"))
    evidence_audit = build_evidence_strength_audit(preflight)
    quality_gate = build_live_results_quality_gate(evidence_audit=evidence_audit, strict=strict)
    rollback_gate = build_rollback_quality_gate(parsed)
    normal_user_gate = build_normal_user_boundary_proof(parsed)
    trace_gate = build_trace_sanitization_results_gate(parsed, scan_paths)
    provider_gate = build_provider_budget_results_gate(parsed)
    no_mutation = build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after, source_parsed=parsed)
    scorecard = build_results_scorecard(
        source_manifest=source_manifest,
        evidence_audit=evidence_audit,
        quality_gate=quality_gate,
        rollback_gate=rollback_gate,
        normal_user_gate=normal_user_gate,
        trace_gate=trace_gate,
        provider_gate=provider_gate,
        no_mutation_proof=no_mutation,
        docs_consistency_gate=docs_consistency_gate,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )
    decision = build_decision(scorecard)
    return {
        "source_artifacts_manifest": source_manifest,
        "evidence_strength_audit": evidence_audit,
        "live_results_quality_gate": quality_gate,
        "rollback_quality_gate": rollback_gate,
        "normal_user_boundary_proof": normal_user_gate,
        "trace_sanitization_results_gate": trace_gate,
        "provider_budget_results_gate": provider_gate,
        "no_mutation_proof": no_mutation,
        "docs_consistency_gate": docs_consistency_gate,
        "results_scorecard": scorecard,
        "decision": decision,
    }


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "DECISION_CONTINUE",
    "DECISION_EVIDENCE_HOTFIX",
    "DECISION_ROLLBACK",
    "DECISION_BLOCKED",
    "NEXT_PRD_CONTINUE",
    "NEXT_PRD_HF1",
    "NEXT_PRD_RB1",
    "required_source_artifacts",
    "preflight_source_artifacts",
    "build_evidence_strength_audit",
    "build_live_results_quality_gate",
    "build_rollback_quality_gate",
    "build_normal_user_boundary_proof",
    "build_trace_sanitization_results_gate",
    "build_provider_budget_results_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_docs_consistency_gate",
    "build_results_scorecard",
    "build_decision",
    "execute_results_gate",
]

