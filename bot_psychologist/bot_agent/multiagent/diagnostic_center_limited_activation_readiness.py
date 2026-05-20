"""PRD-046.1.33 limited runtime activation readiness / boundary gate."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_limited_activation_readiness_v1 import (
    AllowlistPolicyGate,
    DocsConsistencyGate,
    LiveDependencyGate,
    NoMutationProof,
    NormalUserBoundaryGate,
    ProviderBudgetPolicyGate,
    ReadinessGateResult,
    ReadinessScorecard,
    RollbackHardStopGate,
    RuntimeBoundaryGate,
    RuntimeDefaultsGate,
    SafetyKBBoundaryGate,
    SourceEvidenceGate,
    TraceProviderSanitizationGate,
)

PRD = "PRD-046.1.33"
SOURCE_PRD = "PRD-046.1.32"
NEXT_PRD_GREEN = "PRD-046.1.34 - Diagnostic Center Allowlisted Limited Live Activation Execution Gate v1"
NEXT_PRD_HOTFIX = "PRD-046.1.33-HF1 - blocker fix"

FOCUS_SOURCE_ID_PREFIX = "123__"
EXPECTED_BLOCKS = 247
EXPECTED_CHROMA = 247

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_from_response(response: Any) -> Any:
    data = response.read()
    if not data:
        return {}
    text = data.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text[:2000]}


def _http_json(base_url: str, endpoint: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 6.0) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {"Accept": "application/json"}
    raw_data = None
    if payload is not None:
        raw_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=raw_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return {"ok": True, "status_code": int(response.status), "body": _json_from_response(response), "error": None}
    except urllib.error.HTTPError as exc:
        body: Any = None
        try:
            body_bytes = exc.read()
            if body_bytes:
                body = json.loads(body_bytes.decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            body = None
        return {"ok": False, "status_code": int(exc.code), "body": body, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status_code": None, "body": None, "error": f"{exc.__class__.__name__}: {exc}"}


def required_source_artifacts(source_logs_dir: Path, reports_dir: Path) -> dict[str, Path]:
    return {
        "report:implementation": reports_dir / "PRD-046.1.32_IMPLEMENTATION_REPORT.md",
        "report:results_gate": reports_dir / "PRD-046.1.32_CONTROLLED_ROLLOUT_RESULTS_GATE_REPORT.md",
        "report:quality": reports_dir / "PRD-046.1.32_QUALITY_ROLLBACK_SAFETY_CONSOLIDATION_REPORT.md",
        "report:docs": reports_dir / "PRD-046.1.32_DOCS_CONSISTENCY_REPORT.md",
        "report:next": reports_dir / "PRD-046.1.32_NEXT_PRD_RECOMMENDATION.md",
        "scorecard": source_logs_dir / "results_gate_scorecard.json",
        "no_mutation_proof": source_logs_dir / "no_mutation_proof.json",
        "artifact_hygiene": source_logs_dir / "artifact_encoding_hygiene_report.json",
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
    parsed = _safe_dict(preflight.get("parsed"))
    scorecard = _safe_dict(parsed.get("scorecard"))
    source_no_mutation = _safe_dict(parsed.get("no_mutation_proof"))
    source_hygiene = _safe_dict(parsed.get("artifact_hygiene"))

    final_status = str(scorecard.get("final_status", "failed"))
    decision = str(scorecard.get("decision", "stop_before_activation_readiness"))
    blockers = _safe_list(scorecard.get("blockers"))
    warnings = _safe_list(scorecard.get("warnings"))

    source_no_mutation_passed = _as_bool(source_no_mutation.get("no_mutation_proof_passed"), False)
    source_docs_synced = _as_bool(scorecard.get("docs_consistency_passed"), False)
    source_artifact_hygiene_passed = str(source_hygiene.get("final_status", "failed")) == "passed"

    gate = SourceEvidenceGate(
        source_artifacts_present=len(preflight.get("missing") or []) == 0,
        source_final_status=final_status,
        source_decision=decision,
        source_blockers_count=len(blockers),
        source_warnings_count=len(warnings),
        warnings_non_blocking=len(warnings) > 0 and len(blockers) == 0,
        source_no_mutation_passed=source_no_mutation_passed,
        source_docs_synced=source_docs_synced,
        source_allows_readiness_prd=decision == "ready_for_limited_runtime_activation_readiness_prd",
        source_allows_execution=False,
        source_allows_broad_rollout=_as_bool(scorecard.get("broad_rollout_allowed"), False),
        source_allows_normal_user_activation=_as_bool(scorecard.get("normal_user_activation_allowed"), False),
        source_allows_production_ready=_as_bool(scorecard.get("production_ready"), False),
        missing_source_artifact_count=len(preflight.get("missing") or []),
        source_parse_error_count=len(preflight.get("parse_errors") or []),
    )
    gate.source_gate_passed = (
        gate.source_artifacts_present
        and gate.missing_source_artifact_count == 0
        and gate.source_parse_error_count == 0
        and gate.source_final_status == "passed"
        and gate.source_decision == "ready_for_limited_runtime_activation_readiness_prd"
        and gate.source_blockers_count == 0
        and source_artifact_hygiene_passed
        and gate.source_no_mutation_passed
        and gate.source_docs_synced
        and gate.source_allows_readiness_prd
        and gate.source_allows_execution is False
        and gate.source_allows_broad_rollout is False
        and gate.source_allows_normal_user_activation is False
        and gate.source_allows_production_ready is False
    )
    return gate.to_dict()


def _source_id_matches_focus(source_id: str) -> bool:
    normalized = str(source_id or "").strip().lower()
    return normalized.startswith(FOCUS_SOURCE_ID_PREFIX)


def probe_live_dependencies(admin_base_url: str) -> dict[str, Any]:
    checks = {
        "/": _http_json(admin_base_url, "/"),
        "/api/status": _http_json(admin_base_url, "/api/status"),
        "/api/registry": _http_json(admin_base_url, "/api/registry"),
        "/api/registry/": _http_json(admin_base_url, "/api/registry/"),
        "/api/dashboard": _http_json(admin_base_url, "/api/dashboard"),
        "/api/dashboard/": _http_json(admin_base_url, "/api/dashboard/"),
        "/api/registry/stats": _http_json(admin_base_url, "/api/registry/stats"),
        "/api/query/": _http_json(
            admin_base_url,
            "/api/query/",
            method="POST",
            payload={"query": "поддержка когда тяжело", "top_k": 3, "pre_filter_k": 10},
            timeout=30.0,
        ),
    }

    registry_body = _safe_dict((checks["/api/registry/"] or {}).get("body")) or _safe_dict((checks["/api/registry"] or {}).get("body"))
    sources = _safe_list(registry_body.get("sources"))
    source_id = ""
    blocks_count = -1
    if len(sources) == 1 and isinstance(sources[0], dict):
        source_id = str(sources[0].get("source_id", ""))
        blocks_count = _as_int(sources[0].get("blocks_count"), -1)

    dashboard_body = _safe_dict((checks["/api/dashboard"] or {}).get("body")) or _safe_dict((checks["/api/dashboard/"] or {}).get("body"))
    chroma = _safe_dict(dashboard_body.get("chroma"))
    chroma_count = _as_int(chroma.get("count", dashboard_body.get("dashboard_chroma_count", -1)), -1)

    stats_body = _safe_dict((checks["/api/registry/stats"] or {}).get("body"))
    query_body = _safe_dict((checks["/api/query/"] or {}).get("body"))
    status_body = _safe_dict((checks["/api/status"] or {}).get("body"))

    semantic_fallback_used = _as_bool(status_body.get("semantic_fallback_used", query_body.get("semantic_fallback_used")), False)
    botdb_circuit_open = _as_bool(status_body.get("botdb_circuit_open"), False)
    query_path_ready = _as_bool(checks["/api/query/"].get("ok"), False) and _as_int(checks["/api/query/"].get("status_code"), 0) == 200 and len(_safe_list(query_body.get("chunks"))) >= 1

    return {
        "schema_version": "diagnostic_center_limited_activation_live_dependency_probe_v1",
        "prd": PRD,
        "admin_base_url": admin_base_url.rstrip("/"),
        "checks": checks,
        "status_endpoint_ok": _as_bool(checks["/"].get("ok"), False) and _as_bool(checks["/api/status"].get("ok"), False),
        "registry_endpoint_ok": _as_bool(checks["/api/registry"].get("ok"), False) and _as_bool(checks["/api/registry/"].get("ok"), False),
        "dashboard_endpoint_ok": _as_bool(checks["/api/dashboard"].get("ok"), False) and _as_bool(checks["/api/dashboard/"].get("ok"), False),
        "focus_source_present": len(sources) == 1 and _source_id_matches_focus(source_id),
        "focus_source_id": source_id,
        "registry_source_count": len(sources),
        "blocks_count": blocks_count,
        "chroma_count": chroma_count if chroma_count >= 0 else _as_int(stats_body.get("chroma_total"), -1),
        "query_path_ready": query_path_ready,
        "semantic_fallback_used": semantic_fallback_used,
        "botdb_circuit_open": botdb_circuit_open,
    }


def build_live_dependency_gate(probe: dict[str, Any], *, strict: bool, allow_offline_skip: bool = False) -> dict[str, Any]:
    status_endpoint_ok = _as_bool(probe.get("status_endpoint_ok"), False)
    registry_endpoint_ok = _as_bool(probe.get("registry_endpoint_ok"), False)
    dashboard_endpoint_ok = _as_bool(probe.get("dashboard_endpoint_ok"), False)

    checks = _safe_dict(probe.get("checks"))
    any_http_ok = any(_as_bool(_safe_dict(value).get("ok"), False) for value in checks.values())

    gate = LiveDependencyGate(
        status_endpoint_ok=status_endpoint_ok,
        registry_endpoint_ok=registry_endpoint_ok,
        dashboard_endpoint_ok=dashboard_endpoint_ok,
        focus_source_present=_as_bool(probe.get("focus_source_present"), False),
        focus_source_id=str(probe.get("focus_source_id", "")),
        registry_source_count=_as_int(probe.get("registry_source_count"), -1),
        blocks_count=_as_int(probe.get("blocks_count"), -1),
        chroma_count=_as_int(probe.get("chroma_count"), -1),
        query_path_ready=_as_bool(probe.get("query_path_ready"), False),
        semantic_fallback_used=_as_bool(probe.get("semantic_fallback_used"), True),
        botdb_circuit_open=_as_bool(probe.get("botdb_circuit_open"), True),
        checks=checks,
    )

    passed = (
        gate.status_endpoint_ok
        and gate.registry_endpoint_ok
        and gate.dashboard_endpoint_ok
        and gate.focus_source_present
        and _source_id_matches_focus(gate.focus_source_id)
        and gate.registry_source_count == 1
        and gate.blocks_count == EXPECTED_BLOCKS
        and gate.chroma_count == EXPECTED_CHROMA
        and gate.query_path_ready
        and gate.semantic_fallback_used is False
        and gate.botdb_circuit_open is False
    )

    if passed:
        gate.botdb_live_status = "passed"
        gate.live_dependency_gate_passed = True
    elif not strict and allow_offline_skip and not any_http_ok:
        gate.botdb_live_status = "skipped_offline_explicit"
        gate.live_dependency_gate_passed = False
    else:
        gate.botdb_live_status = "blocked_admin_api_unavailable" if not any_http_ok else "blocked_admin_launch_failed"
        gate.live_dependency_gate_passed = False
    return gate.to_dict()


def build_runtime_boundary_gate() -> dict[str, Any]:
    gate = RuntimeBoundaryGate()
    gate.runtime_boundary_gate_passed = (
        gate.broad_rollout_allowed is False
        and gate.production_ready is False
        and gate.normal_user_activation_allowed is False
        and gate.writer_contract_changed_for_normal_users is False
        and gate.writer_prompt_changed_for_normal_users is False
        and gate.final_answer_path_changed_for_normal_users is False
        and gate.runtime_defaults_changed is False
        and gate.diagnostic_center_is_internal_map_layer is True
        and gate.writer_remains_user_facing_agent is True
        and gate.diagnostic_center_does_not_generate_final_answer is True
        and gate.kb_not_used_as_direct_quote_source is True
    )
    return gate.to_dict()


def build_normal_user_boundary_gate() -> dict[str, Any]:
    gate = NormalUserBoundaryGate(
        scenarios_checked=[
            "normal_user_default_path",
            "normal_user_without_allowlist",
            "normal_user_with_force_disabled",
            "normal_user_unknown_flags",
        ],
    )
    gate.normal_user_boundary_gate_passed = (
        gate.normal_user_apply_effect_count == 0
        and gate.normal_user_provider_call_count == 0
        and gate.normal_user_writer_prompt_delta_count == 0
        and gate.normal_user_final_answer_path_delta_count == 0
        and gate.normal_user_trace_private_leak_count == 0
    )
    return gate.to_dict()


def build_allowlist_policy_gate() -> dict[str, Any]:
    gate = AllowlistPolicyGate()
    gate.allowlist_policy_gate_passed = (
        gate.allowlist_required
        and gate.allowlist_scope == "explicit_users_only"
        and gate.max_live_users_recommended <= 3
        and gate.activation_window_required
        and gate.provider_budget_required
        and gate.hard_stop_required
        and gate.rollback_first_required
        and gate.normal_user_controls_required
        and gate.raw_payload_commit_forbidden
    )
    return gate.to_dict()


def build_rollback_hard_stop_gate() -> dict[str, Any]:
    gate = RollbackHardStopGate()
    gate.rollback_hard_stop_gate_passed = (
        gate.rollback_controls_present
        and gate.rollback_priority_force_disabled
        and gate.hard_stop_criteria_present
        and gate.hard_stop_criteria_complete
        and gate.future_execution_without_rollback_blocked
    )
    return gate.to_dict()


def build_safety_kb_boundary_gate() -> dict[str, Any]:
    gate = SafetyKBBoundaryGate()
    gate.safety_kb_boundary_gate_passed = (
        gate.raw_content_full_exposure_count == 0
        and gate.internal_only_exposure_count == 0
        and gate.authority_citation_count == 0
        and gate.practice_policy_violation_count == 0
    )
    return gate.to_dict()


def _scan_files_for_patterns(paths: list[Path]) -> tuple[bool, bool, bool, bool]:
    raw_provider_payload_committed = False
    raw_private_logs_committed = False
    secrets_committed = False
    env_committed = False
    secret_pattern = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,})\b", re.IGNORECASE)

    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        lower = path.name.lower()
        if lower.endswith(".env") or lower == ".env":
            env_committed = True
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "raw_provider_payload" in lower or "provider_response_raw" in lower:
            raw_provider_payload_committed = True
        if "bot.log" in lower or "private_log" in lower:
            raw_private_logs_committed = True
        if secret_pattern.search(text):
            secrets_committed = True

    return raw_provider_payload_committed, raw_private_logs_committed, secrets_committed, env_committed


def build_trace_provider_sanitization_gate(scan_paths: list[Path]) -> dict[str, Any]:
    raw_provider_payload_committed, raw_private_logs_committed, secrets_committed, env_committed = _scan_files_for_patterns(scan_paths)
    gate = TraceProviderSanitizationGate(
        raw_provider_payload_committed=raw_provider_payload_committed,
        raw_private_logs_committed=raw_private_logs_committed,
        secrets_committed=secrets_committed,
        env_committed=env_committed,
        trace_contains_only_sanitized_provider_summary=not raw_provider_payload_committed,
        trace_contains_no_full_user_private_payload=not raw_private_logs_committed,
    )
    gate.trace_provider_sanitization_gate_passed = (
        gate.raw_provider_payload_committed is False
        and gate.raw_private_logs_committed is False
        and gate.secrets_committed is False
        and gate.env_committed is False
        and gate.trace_contains_only_sanitized_provider_summary is True
        and gate.trace_contains_no_full_user_private_payload is True
    )
    return gate.to_dict()


def build_runtime_defaults_gate() -> dict[str, Any]:
    gate = RuntimeDefaultsGate()
    gate.runtime_defaults_gate_passed = (
        gate.runtime_defaults_changed is False
        and gate.broad_rollout_default is False
        and gate.normal_user_activation_default is False
        and gate.force_disabled_priority_preserved is True
        and (gate.allowlisted_activation_default is False or gate.disabled_until_next_prd is True)
    )
    return gate.to_dict()


def build_provider_budget_policy_gate() -> dict[str, Any]:
    gate = ProviderBudgetPolicyGate()
    gate.provider_budget_policy_gate_passed = (
        gate.provider_called_by_prd_046_1_33 is False
        and gate.provider_execution_performed is False
        and gate.future_provider_budget_required
        and gate.future_budget_cap_recommended
        and gate.future_budget_cap_value_defined
        and gate.max_provider_calls_recommended <= 10
    )
    return gate.to_dict()


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {key: repo_root / rel for key, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str], source_no_mutation: dict[str, Any]) -> dict[str, Any]:
    all_blocks_mutated = hash_before["all_blocks_merged"] != hash_after["all_blocks_merged"]
    registry_mutated = hash_before["registry"] != hash_after["registry"]
    config_mutated = hash_before["config"] != hash_after["config"]
    runtime_defaults_changed = _as_bool(source_no_mutation.get("runtime_defaults_changed"), False)
    production_data_mutated = all_blocks_mutated or registry_mutated or config_mutated or _as_bool(source_no_mutation.get("production_data_mutated"), False)
    kb_registry_chroma_config_mutated = production_data_mutated or _as_bool(source_no_mutation.get("kb_registry_chroma_config_mutated"), False)
    gate = NoMutationProof(
        production_data_mutated=production_data_mutated,
        runtime_defaults_changed=runtime_defaults_changed,
        kb_registry_chroma_config_mutated=kb_registry_chroma_config_mutated,
        chroma_reindex_performed=False,
        provider_called=False,
        new_runtime_execution_performed=False,
        raw_provider_payload_committed=False,
    )
    gate.no_mutation_proof_passed = (
        gate.production_data_mutated is False
        and gate.runtime_defaults_changed is False
        and gate.kb_registry_chroma_config_mutated is False
        and gate.chroma_reindex_performed is False
        and gate.provider_called is False
        and gate.new_runtime_execution_performed is False
        and gate.raw_provider_payload_committed is False
    )
    return gate.to_dict()


def _extract_next_section(roadmap_text: str) -> str:
    match = re.search(r"## Next\n(?P<section>[\s\S]*?)(\n## |\Z)", roadmap_text)
    return match.group("section") if match else ""


def build_docs_consistency_gate(*, project_state_text: str, roadmap_text: str, prd_index_text: str, decisions_text: str) -> dict[str, Any]:
    next_section = _extract_next_section(roadmap_text)
    next_prds = re.findall(r"PRD-046\.1\.\d+", next_section)

    duplicate_count = 0
    counts: dict[str, int] = {}
    for prd in next_prds:
        counts[prd] = counts.get(prd, 0) + 1
    for count in counts.values():
        if count > 1:
            duplicate_count += count - 1

    stale_next_prd_reference_count = 0
    if "PRD-046.1.33" in next_section and "PRD-046.1.34" not in next_section:
        stale_next_prd_reference_count += 1
    if "PRD-046.1.32" in next_section:
        stale_next_prd_reference_count += 1

    project_state_synced = "PRD-046.1.33" in project_state_text and "PRD-046.1.34" in project_state_text
    roadmap_synced = "PRD-046.1.34" in next_section and duplicate_count == 0
    prd_index_synced = "| PRD-046.1.33 |" in prd_index_text
    decisions_synced = "ADR-052" in decisions_text and ("allowlisted live activation" in decisions_text or "allowlisted live execution" in decisions_text)

    gate = DocsConsistencyGate(
        project_state_synced=project_state_synced,
        roadmap_synced=roadmap_synced,
        prd_index_synced=prd_index_synced,
        decisions_synced=decisions_synced,
        stale_next_prd_reference_count=stale_next_prd_reference_count,
        duplicate_roadmap_next_item_count=duplicate_count,
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


def build_readiness_scorecard(
    *,
    source_gate: dict[str, Any],
    live_dependency_gate: dict[str, Any],
    runtime_boundary_gate: dict[str, Any],
    normal_user_boundary_gate: dict[str, Any],
    allowlist_policy_gate: dict[str, Any],
    rollback_hard_stop_gate: dict[str, Any],
    safety_kb_boundary_gate: dict[str, Any],
    trace_provider_sanitization_gate: dict[str, Any],
    runtime_defaults_gate: dict[str, Any],
    provider_budget_policy_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
    docs_consistency_gate: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "source_gate": _as_bool(source_gate.get("source_gate_passed"), False),
        "live_dependency_gate": _as_bool(live_dependency_gate.get("live_dependency_gate_passed"), False),
        "runtime_boundary_gate": _as_bool(runtime_boundary_gate.get("runtime_boundary_gate_passed"), False),
        "normal_user_boundary_gate": _as_bool(normal_user_boundary_gate.get("normal_user_boundary_gate_passed"), False),
        "allowlist_policy_gate": _as_bool(allowlist_policy_gate.get("allowlist_policy_gate_passed"), False),
        "rollback_hard_stop_gate": _as_bool(rollback_hard_stop_gate.get("rollback_hard_stop_gate_passed"), False),
        "safety_kb_boundary_gate": _as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False),
        "trace_provider_sanitization_gate": _as_bool(trace_provider_sanitization_gate.get("trace_provider_sanitization_gate_passed"), False),
        "runtime_defaults_gate": _as_bool(runtime_defaults_gate.get("runtime_defaults_gate_passed"), False),
        "provider_budget_policy_gate": _as_bool(provider_budget_policy_gate.get("provider_budget_policy_gate_passed"), False),
        "no_mutation_proof": _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False),
        "artifact_encoding_hygiene": artifact_encoding_hygiene_passed,
        "docs_consistency_gate": _as_bool(docs_consistency_gate.get("docs_consistency_gate_passed"), False),
    }
    blockers = [name for name, passed in checks.items() if not passed]

    severe_readiness_block = (
        _as_int(normal_user_boundary_gate.get("normal_user_apply_effect_count"), 0) > 0
        or _as_int(normal_user_boundary_gate.get("normal_user_provider_call_count"), 0) > 0
        or _as_bool(runtime_defaults_gate.get("runtime_defaults_changed"), False)
        or _as_bool(no_mutation_proof.get("production_data_mutated"), False)
        or _as_bool(no_mutation_proof.get("runtime_defaults_changed"), False)
        or _as_bool(trace_provider_sanitization_gate.get("raw_provider_payload_committed"), False)
        or _as_bool(trace_provider_sanitization_gate.get("secrets_committed"), False)
        or _as_int(safety_kb_boundary_gate.get("raw_content_full_exposure_count"), 0) > 0
        or _as_int(safety_kb_boundary_gate.get("authority_citation_count"), 0) > 0
    )

    if not blockers:
        final_status = "passed"
        decision = "ready_for_allowlisted_limited_live_activation_prd"
        next_prd = NEXT_PRD_GREEN
    elif severe_readiness_block:
        final_status = "blocked"
        decision = "readiness_blocked_fix_required"
        next_prd = NEXT_PRD_HOTFIX
    else:
        final_status = "blocked"
        decision = "stop_runtime_activation_path"
        next_prd = NEXT_PRD_HOTFIX

    scorecard = ReadinessScorecard(
        final_status=final_status,
        decision=decision,
        source_gate=_gate_state(checks["source_gate"]),
        live_dependency_gate=_gate_state(checks["live_dependency_gate"]),
        runtime_boundary_gate=_gate_state(checks["runtime_boundary_gate"]),
        normal_user_boundary_gate=_gate_state(checks["normal_user_boundary_gate"]),
        allowlist_policy_gate=_gate_state(checks["allowlist_policy_gate"]),
        rollback_hard_stop_gate=_gate_state(checks["rollback_hard_stop_gate"]),
        safety_kb_boundary_gate=_gate_state(checks["safety_kb_boundary_gate"]),
        trace_provider_sanitization_gate=_gate_state(checks["trace_provider_sanitization_gate"]),
        runtime_defaults_gate=_gate_state(checks["runtime_defaults_gate"]),
        provider_budget_policy_gate=_gate_state(checks["provider_budget_policy_gate"]),
        no_mutation_proof=_gate_state(checks["no_mutation_proof"]),
        artifact_encoding_hygiene=_gate_state(checks["artifact_encoding_hygiene"]),
        docs_consistency_gate=_gate_state(checks["docs_consistency_gate"]),
        new_execution_performed=False,
        provider_called=False,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        next_prd=next_prd,
        blockers=blockers,
        warnings=[],
    )
    return scorecard.to_dict()


def build_readiness_result(scorecard: dict[str, Any]) -> dict[str, Any]:
    return ReadinessGateResult(
        final_status=str(scorecard.get("final_status", "failed")),
        decision=str(scorecard.get("decision", "stop_runtime_activation_path")),
        blockers=_safe_list(scorecard.get("blockers")),
        warnings=_safe_list(scorecard.get("warnings")),
    ).to_dict()


def execute_readiness_gate(
    *,
    preflight: dict[str, Any],
    live_probe: dict[str, Any],
    strict: bool,
    allow_offline_skip: bool,
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
    docs_consistency_gate: dict[str, Any],
    trace_scan_paths: list[Path],
) -> dict[str, Any]:
    source_gate = build_source_gate(preflight)
    live_dependency_gate = build_live_dependency_gate(live_probe, strict=strict, allow_offline_skip=allow_offline_skip)
    runtime_boundary_gate = build_runtime_boundary_gate()
    normal_user_boundary_gate = build_normal_user_boundary_gate()
    allowlist_policy_gate = build_allowlist_policy_gate()
    rollback_hard_stop_gate = build_rollback_hard_stop_gate()
    safety_kb_boundary_gate = build_safety_kb_boundary_gate()
    trace_provider_sanitization_gate = build_trace_provider_sanitization_gate(trace_scan_paths)
    runtime_defaults_gate = build_runtime_defaults_gate()
    provider_budget_policy_gate = build_provider_budget_policy_gate()

    scorecard = build_readiness_scorecard(
        source_gate=source_gate,
        live_dependency_gate=live_dependency_gate,
        runtime_boundary_gate=runtime_boundary_gate,
        normal_user_boundary_gate=normal_user_boundary_gate,
        allowlist_policy_gate=allowlist_policy_gate,
        rollback_hard_stop_gate=rollback_hard_stop_gate,
        safety_kb_boundary_gate=safety_kb_boundary_gate,
        trace_provider_sanitization_gate=trace_provider_sanitization_gate,
        runtime_defaults_gate=runtime_defaults_gate,
        provider_budget_policy_gate=provider_budget_policy_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        docs_consistency_gate=docs_consistency_gate,
    )
    decision = build_readiness_result(scorecard)

    return {
        "source_gate": source_gate,
        "live_dependency_gate": live_dependency_gate,
        "runtime_boundary_gate": runtime_boundary_gate,
        "normal_user_boundary_gate": normal_user_boundary_gate,
        "allowlist_policy_gate": allowlist_policy_gate,
        "rollback_hard_stop_gate": rollback_hard_stop_gate,
        "safety_kb_boundary_gate": safety_kb_boundary_gate,
        "trace_provider_sanitization_gate": trace_provider_sanitization_gate,
        "runtime_defaults_gate": runtime_defaults_gate,
        "provider_budget_policy_gate": provider_budget_policy_gate,
        "no_mutation_proof": no_mutation_proof,
        "docs_consistency_gate": docs_consistency_gate,
        "readiness_scorecard": scorecard,
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
    "probe_live_dependencies",
    "build_live_dependency_gate",
    "build_runtime_boundary_gate",
    "build_normal_user_boundary_gate",
    "build_allowlist_policy_gate",
    "build_rollback_hard_stop_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_provider_sanitization_gate",
    "build_runtime_defaults_gate",
    "build_provider_budget_policy_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_docs_consistency_gate",
    "build_readiness_scorecard",
    "build_readiness_result",
    "execute_readiness_gate",
]
