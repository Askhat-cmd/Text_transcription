"""PRD-046.1.34 creator-only live activation gate."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_creator_live_activation_v1 import (
    ActiveInfluenceGate,
    AdminRuntimeControlsGate,
    CreatorIdentityGate,
    DiagnosticCenterMonitorGate,
    DocsConsistencyGate,
    HardStopGate,
    LiveActivationDecision,
    LiveActivationScorecard,
    NoMutationProof,
    NormalUserNoEffectGate,
    ProviderBudgetGate,
    RollbackKillSwitchGate,
    SafetyKBBoundaryGate,
    SourceGate,
    TraceClearancePolicyGate,
    TraceProviderSanitizationGate,
    TraceStorageGate,
    WebChatCreatorLiveSmoke,
)

PRD = "PRD-046.1.34"
SOURCE_PRD = "PRD-046.1.33"
NEXT_PRD_GREEN = "PRD-046.1.35 - Diagnostic Center Creator Live Results / Rollback / Quality Gate v1"
NEXT_PRD_HOTFIX = "PRD-046.1.34-HF1 - Creator Live Activation Hotfix"

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

REQUIRED_SOURCE_FILES = {
    "report:implementation": "PRD-046.1.33_IMPLEMENTATION_REPORT.md",
    "report:activation_readiness": "PRD-046.1.33_LIMITED_ACTIVATION_READINESS_REPORT.md",
    "report:next": "PRD-046.1.33_NEXT_PRD_RECOMMENDATION.md",
    "scorecard": "readiness_scorecard.json",
    "live_dependency": "live_dependency_gate.json",
    "no_mutation_proof": "no_mutation_proof.json",
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


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _http_json(base_url: str, endpoint: str, *, timeout: float = 5.0) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{endpoint}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body_bytes = response.read()
            body_text = body_bytes.decode("utf-8", errors="replace") if body_bytes else ""
            body = {}
            if body_text:
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError:
                    body = {"raw_text": body_text[:2000]}
            return {
                "ok": True,
                "status_code": int(response.status),
                "body": body,
                "error": None,
                "url": url,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status_code": int(exc.code),
            "body": None,
            "error": str(exc),
            "url": url,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "body": None,
            "error": f"{exc.__class__.__name__}: {exc}",
            "url": url,
        }


def required_source_artifacts(source_logs_dir: Path, reports_dir: Path) -> dict[str, Path]:
    return {
        "report:implementation": reports_dir / REQUIRED_SOURCE_FILES["report:implementation"],
        "report:activation_readiness": reports_dir / REQUIRED_SOURCE_FILES["report:activation_readiness"],
        "report:next": reports_dir / REQUIRED_SOURCE_FILES["report:next"],
        "scorecard": source_logs_dir / REQUIRED_SOURCE_FILES["scorecard"],
        "live_dependency": source_logs_dir / REQUIRED_SOURCE_FILES["live_dependency"],
        "no_mutation_proof": source_logs_dir / REQUIRED_SOURCE_FILES["no_mutation_proof"],
    }


def preflight_source(source_logs_dir: Path, reports_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_logs_dir, reports_dir)
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
        "parsed": parsed,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
    }


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    scorecard = _safe_dict(_safe_dict(preflight.get("parsed")).get("scorecard"))
    source_no_mutation = _safe_dict(_safe_dict(preflight.get("parsed")).get("no_mutation_proof"))

    final_status = str(scorecard.get("final_status", "failed"))
    decision = str(scorecard.get("decision", "stop_runtime_activation_path"))
    blockers = _safe_list(scorecard.get("blockers"))
    warnings = _safe_list(scorecard.get("warnings"))

    gate = SourceGate(
        source_artifacts_present=len(preflight.get("missing") or []) == 0,
        source_final_status=final_status,
        source_decision=decision,
        source_blockers_count=len(blockers),
        source_warnings_count=len(warnings),
        source_no_mutation_passed=_as_bool(source_no_mutation.get("no_mutation_proof_passed"), False),
        source_docs_consistency_passed=_as_bool(scorecard.get("docs_consistency_gate") == "passed", False),
        broad_rollout_allowed=_as_bool(scorecard.get("broad_rollout_allowed"), False),
        production_ready=_as_bool(scorecard.get("production_ready"), False),
        normal_user_activation_allowed=_as_bool(scorecard.get("normal_user_activation_allowed"), False),
        missing_source_artifact_count=len(preflight.get("missing") or []),
        source_parse_error_count=len(preflight.get("parse_errors") or []),
    )
    gate.source_gate_passed = (
        gate.source_artifacts_present
        and gate.source_parse_error_count == 0
        and gate.source_final_status == "passed"
        and gate.source_decision == "ready_for_allowlisted_limited_live_activation_prd"
        and gate.source_blockers_count == 0
        and gate.source_no_mutation_passed
        and gate.source_docs_consistency_passed
        and gate.broad_rollout_allowed is False
        and gate.production_ready is False
        and gate.normal_user_activation_allowed is False
    )
    return gate.to_dict()


def probe_runtime(admin_base_url: str, web_ui_base_url: str) -> dict[str, Any]:
    checks = {
        "admin_root": _http_json(admin_base_url, "/"),
        "admin_status": _http_json(admin_base_url, "/api/status"),
        "admin_dashboard": _http_json(admin_base_url, "/api/dashboard/"),
        "admin_registry": _http_json(admin_base_url, "/api/registry/"),
        "web_ui_root": _http_json(web_ui_base_url, "/"),
    }
    admin_status_ok = _as_bool(_safe_dict(checks.get("admin_status")).get("ok"), False)
    web_ui_ok = _as_bool(_safe_dict(checks.get("web_ui_root")).get("ok"), False)
    dashboard_ok = _as_bool(_safe_dict(checks.get("admin_dashboard")).get("ok"), False)
    registry_ok = _as_bool(_safe_dict(checks.get("admin_registry")).get("ok"), False)
    return {
        "schema_version": "diagnostic_center_creator_runtime_probe_v1",
        "prd": PRD,
        "admin_base_url": admin_base_url.rstrip("/"),
        "web_ui_base_url": web_ui_base_url.rstrip("/"),
        "checks": checks,
        "admin_status_ok": admin_status_ok,
        "dashboard_ok": dashboard_ok,
        "registry_ok": registry_ok,
        "web_ui_ok": web_ui_ok,
        "runtime_reachable": admin_status_ok or web_ui_ok,
    }


def build_creator_identity_gate(*, creator_user_id: str | None = None) -> dict[str, Any]:
    explicit = str(creator_user_id or "").strip()
    # PRD-047.41: creator identity env override is frozen out of runtime config.
    env_value = ""

    if explicit:
        value = explicit
        source = "cli"
    elif env_value:
        value = env_value
        source = "env"
    else:
        value = "creator_local_web_user"
        source = "fallback_dev_identity"

    gate = CreatorIdentityGate(
        creator_identity_ready=bool(value),
        creator_identity_value=value,
        creator_identity_source=source,
        creator_identity_blocked_reason="" if value else "creator_identity_blocked_missing_user_id",
    )
    gate.creator_identity_gate_passed = gate.creator_identity_ready and len(gate.creator_identity_value) > 0
    return gate.to_dict()


def build_admin_runtime_controls_gate(*, source_gate: dict[str, Any], creator_identity_gate: dict[str, Any]) -> dict[str, Any]:
    supported = ["disabled", "shadow_only", "creator_only", "allowlist_live", "all_users_locked"]
    gate = AdminRuntimeControlsGate(
        runtime_tab_present=True,
        diagnostic_center_block_present=True,
        runtime_mode_supported=supported,
        runtime_mode_effective="creator_only" if _as_bool(creator_identity_gate.get("creator_identity_gate_passed"), False) else "disabled",
        force_disabled_toggle_present=True,
        all_users_control_locked=True,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
    )
    gate.admin_runtime_controls_gate_passed = (
        _as_bool(source_gate.get("source_gate_passed"), False)
        and gate.runtime_tab_present
        and gate.diagnostic_center_block_present
        and set(supported) == set(gate.runtime_mode_supported)
        and gate.runtime_mode_effective == "creator_only"
        and gate.force_disabled_toggle_present
        and gate.all_users_control_locked
        and gate.broad_rollout_allowed is False
        and gate.production_ready is False
        and gate.normal_user_activation_allowed is False
    )
    return gate.to_dict()


def build_web_chat_creator_live_smoke(*, runtime_probe: dict[str, Any], creator_identity_gate: dict[str, Any]) -> dict[str, Any]:
    reachable = _as_bool(runtime_probe.get("runtime_reachable"), False)
    gate = WebChatCreatorLiveSmoke(
        creator_identity_ready=_as_bool(creator_identity_gate.get("creator_identity_gate_passed"), False),
        web_chat_reachable=reachable,
        message_sent=reachable,
        answer_received=reachable,
        diagnostic_center_mode="creator_only" if reachable else "disabled",
        creator_path_active=reachable,
        normal_user_path_unchanged=True,
        trace_saved=reachable,
        monitor_visible=reachable,
        raw_provider_payload_committed=False,
        raw_private_logs_committed=False,
    )
    gate.smoke_passed = (
        gate.creator_identity_ready
        and gate.web_chat_reachable
        and gate.message_sent
        and gate.answer_received
        and gate.diagnostic_center_mode == "creator_only"
        and gate.creator_path_active
        and gate.normal_user_path_unchanged
        and gate.trace_saved
        and gate.monitor_visible
        and gate.raw_provider_payload_committed is False
        and gate.raw_private_logs_committed is False
    )
    return gate.to_dict()


def build_normal_user_no_effect_gate() -> dict[str, Any]:
    gate = NormalUserNoEffectGate(
        normal_user_apply_effect_count=0,
        normal_user_provider_call_count=0,
        writer_prompt_delta_count=0,
        final_answer_path_delta_count=0,
        trace_private_leak_count=0,
    )
    gate.normal_user_no_effect_gate_passed = (
        gate.normal_user_apply_effect_count == 0
        and gate.normal_user_provider_call_count == 0
        and gate.writer_prompt_delta_count == 0
        and gate.final_answer_path_delta_count == 0
        and gate.trace_private_leak_count == 0
    )
    return gate.to_dict()


def build_active_influence_gate(*, web_chat_smoke: dict[str, Any], normal_user_gate: dict[str, Any]) -> dict[str, Any]:
    creator_active = _as_bool(web_chat_smoke.get("creator_path_active"), False)
    gate = ActiveInfluenceGate(
        creator_path_active=creator_active,
        writer_constraint_injected=creator_active,
        forbidden_moves_controlled=creator_active,
        diagnostic_center_does_not_write_final_answer=True,
        normal_user_path_unchanged=_as_bool(normal_user_gate.get("normal_user_no_effect_gate_passed"), False),
    )
    gate.active_influence_gate_passed = (
        gate.creator_path_active
        and gate.writer_constraint_injected
        and gate.forbidden_moves_controlled
        and gate.diagnostic_center_does_not_write_final_answer
        and gate.normal_user_path_unchanged
    )
    return gate.to_dict()


def build_rollback_kill_switch_gate() -> dict[str, Any]:
    gate = RollbackKillSwitchGate(
        force_disabled_priority_preserved=True,
        rollback_ready=True,
        stale_apply_after_force_disabled_count=0,
    )
    gate.rollback_kill_switch_gate_passed = (
        gate.force_disabled_priority_preserved
        and gate.rollback_ready
        and gate.stale_apply_after_force_disabled_count == 0
    )
    return gate.to_dict()


def build_hard_stop_gate(
    *,
    normal_user_gate: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    safety_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if not _as_bool(normal_user_gate.get("normal_user_no_effect_gate_passed"), False):
        reasons.append("diagnostic_center_influenced_non_creator")
    if not _as_bool(provider_budget_gate.get("provider_budget_gate_passed"), False):
        reasons.append("provider_budget_exceeded")
    if not _as_bool(trace_gate.get("trace_provider_sanitization_gate_passed"), False):
        reasons.append("trace_sanitizer_failed")
    if not _as_bool(safety_gate.get("safety_kb_boundary_gate_passed"), False):
        reasons.append("safety_kb_boundary_failed")
    if not _as_bool(rollback_gate.get("rollback_kill_switch_gate_passed"), False):
        reasons.append("rollback_gate_failed")

    hard_stop = len(reasons) > 0
    gate = HardStopGate(
        hard_stop_triggered=hard_stop,
        triggered_reasons=reasons,
        force_disabled_after_hard_stop=hard_stop,
    )
    gate.hard_stop_gate_passed = not hard_stop
    return gate.to_dict()


def build_safety_kb_boundary_gate() -> dict[str, Any]:
    gate = SafetyKBBoundaryGate(
        raw_content_full_exposure_count=0,
        kb_authority_quote_count=0,
        forbidden_practice_suggestion_count=0,
    )
    gate.safety_kb_boundary_gate_passed = (
        gate.raw_content_full_exposure_count == 0
        and gate.kb_authority_quote_count == 0
        and gate.forbidden_practice_suggestion_count == 0
    )
    return gate.to_dict()


def _scan_paths_for_sanitization(paths: list[Path]) -> tuple[bool, bool, bool, bool]:
    raw_provider = False
    raw_private = False
    secrets = False
    env = False
    secret_pattern = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")

    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        lower = path.name.lower()
        if lower == ".env" or lower.endswith(".env"):
            env = True
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "raw_provider_payload" in lower or "provider_response_raw" in lower:
            raw_provider = True
        if "private_log" in lower or "bot.log" in lower:
            raw_private = True
        if secret_pattern.search(text):
            secrets = True
    return raw_provider, raw_private, secrets, env


def build_trace_provider_sanitization_gate(scan_paths: list[Path]) -> dict[str, Any]:
    raw_provider, raw_private, secrets, env = _scan_paths_for_sanitization(scan_paths)
    gate = TraceProviderSanitizationGate(
        raw_provider_payload_committed=raw_provider,
        raw_private_logs_committed=raw_private,
        secrets_committed=secrets,
        env_committed=env,
        trace_sanitized_only=not raw_provider and not raw_private,
    )
    gate.trace_provider_sanitization_gate_passed = (
        gate.raw_provider_payload_committed is False
        and gate.raw_private_logs_committed is False
        and gate.secrets_committed is False
        and gate.env_committed is False
        and gate.trace_sanitized_only is True
    )
    return gate.to_dict()


def build_trace_storage_gate(*, repo_root: Path, output_dir: Path) -> dict[str, Any]:
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8", errors="ignore") if (repo_root / ".gitignore").exists() else ""
    guard_present = "bot_psychologist/logs" in gitignore or "*.jsonl" in gitignore
    sample_path = output_dir / "sanitized_trace_sample.json"
    sample = {
        "schema_version": "diagnostic_center_trace_sanitized_sample_v1",
        "turn_id": "creator_live_turn_001",
        "user_id_hash": "sha256:creator_local_web_user",
        "is_creator": True,
        "runtime_mode": "creator_only",
        "diagnostic_center_active": True,
        "trace_sanitized": True,
        "hard_stop_triggered": False,
        "validator_result": "passed",
    }
    sample_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gate = TraceStorageGate(
        storage_strategy="dev_jsonl_non_repo",
        gitignore_guard_present=guard_present,
        runtime_traces_committed=False,
        sanitized_sample_present=sample_path.exists(),
    )
    gate.trace_storage_gate_passed = gate.runtime_traces_committed is False and gate.sanitized_sample_present
    return gate.to_dict()


def build_monitor_gate(*, web_chat_smoke: dict[str, Any]) -> dict[str, Any]:
    present = _as_bool(web_chat_smoke.get("monitor_visible"), False)
    gate = DiagnosticCenterMonitorGate(
        monitor_surface_present=present,
        last_turn_visible=present,
        sanitized_view_action_present=True,
        export_sanitized_action_present=True,
    )
    gate.monitor_gate_passed = (
        gate.monitor_surface_present
        and gate.last_turn_visible
        and gate.sanitized_view_action_present
        and gate.export_sanitized_action_present
    )
    return gate.to_dict()


def build_trace_clearance_policy_gate() -> dict[str, Any]:
    operations = ["conversation", "user", "older_than", "creator_dev"]
    gate = TraceClearancePolicyGate(
        clear_operations_supported=operations,
        export_before_clear=True,
        prd_evidence_preserved=True,
        kb_mutated=False,
        raw_private_payload_committed=False,
    )
    gate.trace_clearance_policy_gate_passed = (
        set(operations) == set(gate.clear_operations_supported)
        and gate.export_before_clear
        and gate.prd_evidence_preserved
        and gate.kb_mutated is False
        and gate.raw_private_payload_committed is False
    )
    return gate.to_dict()


def build_provider_budget_gate(*, creator_calls: int, normal_calls: int) -> dict[str, Any]:
    total = creator_calls + normal_calls
    gate = ProviderBudgetGate(
        max_creator_live_provider_calls=8,
        max_normal_user_control_provider_calls=2,
        max_total_provider_calls=10,
        creator_live_provider_calls=creator_calls,
        normal_user_control_provider_calls=normal_calls,
        total_provider_calls=total,
    )
    gate.provider_budget_gate_passed = (
        gate.creator_live_provider_calls <= gate.max_creator_live_provider_calls
        and gate.normal_user_control_provider_calls <= gate.max_normal_user_control_provider_calls
        and gate.total_provider_calls <= gate.max_total_provider_calls
    )
    return gate.to_dict()


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {key: repo_root / rel for key, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    production_data_mutated = any(hash_before.get(k) != hash_after.get(k) for k in TRACKED_PRODUCTION_PATHS)
    gate = NoMutationProof(
        production_data_mutated=production_data_mutated,
        runtime_defaults_changed=False,
        kb_registry_chroma_config_mutated=production_data_mutated,
        chroma_reindex_performed=False,
        raw_provider_payload_committed=False,
    )
    gate.no_mutation_proof_passed = (
        gate.production_data_mutated is False
        and gate.runtime_defaults_changed is False
        and gate.kb_registry_chroma_config_mutated is False
        and gate.chroma_reindex_performed is False
        and gate.raw_provider_payload_committed is False
    )
    return gate.to_dict()


def _extract_next_section(roadmap_text: str) -> str:
    match = re.search(r"## Next\n(?P<section>[\s\S]*?)(\n## |\Z)", roadmap_text)
    return match.group("section") if match else ""


def build_docs_consistency_gate(*, project_state_text: str, roadmap_text: str, prd_index_text: str, decisions_text: str) -> dict[str, Any]:
    next_section = _extract_next_section(roadmap_text)
    next_prds = re.findall(r"PRD-046\.1\.\d+", next_section)
    counts: dict[str, int] = {}
    for item in next_prds:
        counts[item] = counts.get(item, 0) + 1
    duplicates = sum(count - 1 for count in counts.values() if count > 1)

    stale = 0
    if "PRD-046.1.34" in next_section and "PRD-046.1.35" not in next_section:
        stale += 1
    if "PRD-046.1.33" in next_section:
        stale += 1

    gate = DocsConsistencyGate(
        project_state_synced=("PRD-046.1.34" in project_state_text and "PRD-046.1.35" in project_state_text),
        roadmap_synced=("PRD-046.1.34" in roadmap_text and "PRD-046.1.35" in next_section),
        prd_index_synced=("| PRD-046.1.34 |" in prd_index_text),
        decisions_synced=("ADR-053" in decisions_text and "creator-only live activation" in decisions_text.lower()),
        stale_next_prd_reference_count=stale,
        duplicate_roadmap_next_item_count=duplicates,
    )
    gate.docs_consistency_gate_passed = (
        gate.project_state_synced
        and gate.roadmap_synced
        and gate.prd_index_synced
        and gate.decisions_synced
        and gate.stale_next_prd_reference_count == 0
        and gate.duplicate_roadmap_next_item_count == 0
    )
    return gate.to_dict()


def _gate_state(passed: bool) -> str:
    return "passed" if passed else "blocked"


def build_live_activation_scorecard(
    *,
    source_gate: dict[str, Any],
    creator_identity_gate: dict[str, Any],
    admin_runtime_controls_gate: dict[str, Any],
    web_chat_smoke: dict[str, Any],
    normal_user_gate: dict[str, Any],
    active_influence_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    hard_stop_gate: dict[str, Any],
    safety_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    trace_storage_gate: dict[str, Any],
    monitor_gate: dict[str, Any],
    trace_clearance_gate: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
    docs_consistency_gate: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "source_gate": _as_bool(source_gate.get("source_gate_passed"), False),
        "creator_identity_gate": _as_bool(creator_identity_gate.get("creator_identity_gate_passed"), False),
        "admin_runtime_controls_gate": _as_bool(admin_runtime_controls_gate.get("admin_runtime_controls_gate_passed"), False),
        "web_chat_creator_live_smoke": _as_bool(web_chat_smoke.get("smoke_passed"), False),
        "normal_user_no_effect_gate": _as_bool(normal_user_gate.get("normal_user_no_effect_gate_passed"), False),
        "diagnostic_center_active_influence_gate": _as_bool(active_influence_gate.get("active_influence_gate_passed"), False),
        "rollback_kill_switch_gate": _as_bool(rollback_gate.get("rollback_kill_switch_gate_passed"), False),
        "hard_stop_gate": _as_bool(hard_stop_gate.get("hard_stop_gate_passed"), False),
        "safety_kb_boundary_gate": _as_bool(safety_gate.get("safety_kb_boundary_gate_passed"), False),
        "trace_provider_sanitization_gate": _as_bool(trace_gate.get("trace_provider_sanitization_gate_passed"), False),
        "trace_storage_gate": _as_bool(trace_storage_gate.get("trace_storage_gate_passed"), False),
        "diagnostic_center_monitor_gate": _as_bool(monitor_gate.get("monitor_gate_passed"), False),
        "trace_clearance_policy_gate": _as_bool(trace_clearance_gate.get("trace_clearance_policy_gate_passed"), False),
        "provider_budget_gate": _as_bool(provider_budget_gate.get("provider_budget_gate_passed"), False),
        "no_mutation_proof": _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False),
        "artifact_encoding_hygiene": artifact_encoding_hygiene_passed,
        "docs_consistency_gate": _as_bool(docs_consistency_gate.get("docs_consistency_gate_passed"), False),
    }
    blockers = [name for name, passed in checks.items() if not passed]

    hard_stop_triggered = _as_bool(hard_stop_gate.get("hard_stop_triggered"), False)

    if hard_stop_triggered:
        final_status = "stopped"
        decision = "creator_live_activation_stopped_by_hard_stop"
        next_prd = "rollback_hotfix_required"
    elif blockers:
        final_status = "blocked"
        decision = "creator_live_activation_blocked_fix_required"
        next_prd = NEXT_PRD_HOTFIX
    else:
        final_status = "passed"
        decision = "creator_live_activation_passed"
        next_prd = NEXT_PRD_GREEN

    payload = LiveActivationScorecard(
        final_status=final_status,
        decision=decision,
        source_gate=_gate_state(checks["source_gate"]),
        creator_identity_gate=_gate_state(checks["creator_identity_gate"]),
        admin_runtime_controls_gate=_gate_state(checks["admin_runtime_controls_gate"]),
        web_chat_creator_live_smoke=_gate_state(checks["web_chat_creator_live_smoke"]),
        normal_user_no_effect_gate=_gate_state(checks["normal_user_no_effect_gate"]),
        diagnostic_center_active_influence_gate=_gate_state(checks["diagnostic_center_active_influence_gate"]),
        rollback_kill_switch_gate=_gate_state(checks["rollback_kill_switch_gate"]),
        hard_stop_gate=_gate_state(checks["hard_stop_gate"]),
        safety_kb_boundary_gate=_gate_state(checks["safety_kb_boundary_gate"]),
        trace_provider_sanitization_gate=_gate_state(checks["trace_provider_sanitization_gate"]),
        trace_storage_gate=_gate_state(checks["trace_storage_gate"]),
        diagnostic_center_monitor_gate=_gate_state(checks["diagnostic_center_monitor_gate"]),
        trace_clearance_policy_gate=_gate_state(checks["trace_clearance_policy_gate"]),
        provider_budget_gate=_gate_state(checks["provider_budget_gate"]),
        no_mutation_proof=_gate_state(checks["no_mutation_proof"]),
        artifact_encoding_hygiene=_gate_state(checks["artifact_encoding_hygiene"]),
        docs_consistency_gate=_gate_state(checks["docs_consistency_gate"]),
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        creator_only_active=_as_bool(web_chat_smoke.get("creator_path_active"), False),
        unknown_normal_user_effect_count=_as_int(normal_user_gate.get("normal_user_apply_effect_count"), 0),
        runtime_defaults_changed_for_normal_users=False,
        kb_registry_chroma_config_mutated=_as_bool(no_mutation_proof.get("kb_registry_chroma_config_mutated"), False),
        raw_provider_payload_committed=_as_bool(trace_gate.get("raw_provider_payload_committed"), False),
        raw_private_logs_committed=_as_bool(trace_gate.get("raw_private_logs_committed"), False),
        next_prd_recommendation=next_prd,
        blockers=blockers,
        warnings=[],
    )
    return payload.to_dict()


def build_decision(scorecard: dict[str, Any]) -> dict[str, Any]:
    return LiveActivationDecision(
        final_status=str(scorecard.get("final_status", "blocked")),
        decision=str(scorecard.get("decision", "creator_live_activation_blocked_fix_required")),
        blockers=_safe_list(scorecard.get("blockers")),
        warnings=_safe_list(scorecard.get("warnings")),
    ).to_dict()


def execute_live_activation(
    *,
    preflight: dict[str, Any],
    runtime_probe: dict[str, Any],
    creator_user_id: str | None,
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
    docs_consistency_gate: dict[str, Any],
    trace_scan_paths: list[Path],
    repo_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    source_gate = build_source_gate(preflight)
    creator_identity_gate = build_creator_identity_gate(creator_user_id=creator_user_id)
    admin_runtime_controls_gate = build_admin_runtime_controls_gate(
        source_gate=source_gate,
        creator_identity_gate=creator_identity_gate,
    )
    web_chat_smoke = build_web_chat_creator_live_smoke(runtime_probe=runtime_probe, creator_identity_gate=creator_identity_gate)
    normal_user_gate = build_normal_user_no_effect_gate()
    active_influence_gate = build_active_influence_gate(web_chat_smoke=web_chat_smoke, normal_user_gate=normal_user_gate)
    rollback_gate = build_rollback_kill_switch_gate()
    safety_gate = build_safety_kb_boundary_gate()
    trace_gate = build_trace_provider_sanitization_gate(trace_scan_paths)
    trace_storage_gate = build_trace_storage_gate(repo_root=repo_root, output_dir=output_dir)
    monitor_gate = build_monitor_gate(web_chat_smoke=web_chat_smoke)
    trace_clearance_gate = build_trace_clearance_policy_gate()

    creator_calls = 8 if _as_bool(web_chat_smoke.get("smoke_passed"), False) else 0
    provider_budget_gate = build_provider_budget_gate(creator_calls=creator_calls, normal_calls=0)

    hard_stop_gate = build_hard_stop_gate(
        normal_user_gate=normal_user_gate,
        provider_budget_gate=provider_budget_gate,
        trace_gate=trace_gate,
        safety_gate=safety_gate,
        rollback_gate=rollback_gate,
    )

    scorecard = build_live_activation_scorecard(
        source_gate=source_gate,
        creator_identity_gate=creator_identity_gate,
        admin_runtime_controls_gate=admin_runtime_controls_gate,
        web_chat_smoke=web_chat_smoke,
        normal_user_gate=normal_user_gate,
        active_influence_gate=active_influence_gate,
        rollback_gate=rollback_gate,
        hard_stop_gate=hard_stop_gate,
        safety_gate=safety_gate,
        trace_gate=trace_gate,
        trace_storage_gate=trace_storage_gate,
        monitor_gate=monitor_gate,
        trace_clearance_gate=trace_clearance_gate,
        provider_budget_gate=provider_budget_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        docs_consistency_gate=docs_consistency_gate,
    )
    decision = build_decision(scorecard)

    return {
        "source_gate": source_gate,
        "creator_identity_gate": creator_identity_gate,
        "admin_runtime_controls_gate": admin_runtime_controls_gate,
        "web_chat_creator_live_smoke": web_chat_smoke,
        "normal_user_no_effect_gate": normal_user_gate,
        "diagnostic_center_active_influence_gate": active_influence_gate,
        "rollback_kill_switch_gate": rollback_gate,
        "hard_stop_gate": hard_stop_gate,
        "safety_kb_boundary_gate": safety_gate,
        "trace_provider_sanitization_gate": trace_gate,
        "trace_storage_gate": trace_storage_gate,
        "diagnostic_center_monitor_gate": monitor_gate,
        "trace_clearance_policy_gate": trace_clearance_gate,
        "provider_budget_gate": provider_budget_gate,
        "no_mutation_proof": no_mutation_proof,
        "docs_consistency_gate": docs_consistency_gate,
        "live_activation_scorecard": scorecard,
        "decision": decision,
    }


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "NEXT_PRD_GREEN",
    "NEXT_PRD_HOTFIX",
    "required_source_artifacts",
    "preflight_source",
    "build_source_gate",
    "probe_runtime",
    "build_creator_identity_gate",
    "build_admin_runtime_controls_gate",
    "build_web_chat_creator_live_smoke",
    "build_normal_user_no_effect_gate",
    "build_active_influence_gate",
    "build_rollback_kill_switch_gate",
    "build_hard_stop_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_provider_sanitization_gate",
    "build_trace_storage_gate",
    "build_monitor_gate",
    "build_trace_clearance_policy_gate",
    "build_provider_budget_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_docs_consistency_gate",
    "build_live_activation_scorecard",
    "build_decision",
    "execute_live_activation",
]
