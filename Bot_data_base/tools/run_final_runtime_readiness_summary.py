from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from tools.diagnose_chroma_runtime_count import run_diagnostic  # noqa: E402

EXPECTED_SOURCE_ID = "123__кузница_духа"
EXPECTED_SOURCE_TITLE = "Кузница Духа"
EXPECTED_BLOCKS = 247
PRD_ID = "PRD-046.0.11"
NEXT_PRD = "PRD-046.1"
DEFAULT_BASE_URL = "http://127.0.0.1:8003"

MOJIBAKE_MARKERS = ("Гђ", "Г‘", "\\u0085")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(_read_text(path))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(_read_text(path)) or {}


def _http_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            body: Any
            if not raw:
                body = None
            else:
                try:
                    body = json.loads(raw)
                except Exception:
                    body = {"raw_text": raw[:1000]}
            return {
                "ok": int(resp.status) == 200,
                "status_code": int(resp.status),
                "body": body,
                "error": None,
            }
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _extract_registry_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("sources")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _contains_case_insensitive(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def _scan_mojibake(value: Any, markers: tuple[str, ...] = MOJIBAKE_MARKERS) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def _walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                _walk(nested, f"{path}.{key}" if path else str(key))
            return
        if isinstance(item, list):
            for idx, nested in enumerate(item):
                _walk(nested, f"{path}[{idx}]")
            return
        if not isinstance(item, str):
            return

        for marker in markers:
            if marker in item:
                findings.append({"path": path, "marker": marker, "snippet": item[:180]})
        if "\u0085" in item:
            findings.append({"path": path, "marker": "\\u0085", "snippet": item[:180]})

    _walk(value, "")
    return findings


def _required_paths(repo_root: Path, logs_dir: Path) -> dict[str, Path]:
    return {
        "config": repo_root / "Bot_data_base" / "config.yaml",
        "all_blocks": repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": repo_root / "Bot_data_base" / "data" / "registry.json",
        "project_state": repo_root / "docs" / "PROJECT_STATE.md",
        "roadmap": repo_root / "docs" / "ROADMAP.md",
        "prd_index": repo_root / "docs" / "PRD_INDEX.md",
        "decisions": repo_root / "docs" / "DECISIONS.md",
        "runtime_smoke_utf8": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.10-HF1" / "runtime_smoke_utf8.json",
        "utf8_artifact_check": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.10-HF1" / "utf8_artifact_check.json",
        "sd_config_effective": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.10-HF1" / "sd_config_effective_state.json",
        "strict_gate_hf4": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.7.2-HF4" / "strict_quality_gate_hf4.json",
        "retrieval_smoke": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.7.2" / "retrieval_quality_smoke.json",
        "retrieval_scorecard": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.6-HF1" / "retrieval_eval_scorecard.json",
        "apply_result": repo_root / "TO_DO_LIST" / "logs" / "PRD-046.0.7.1" / "apply_result.json",
        "manifest": logs_dir / "readiness_sources_manifest.json",
        "live_admin": logs_dir / "live_admin_runtime_check.json",
        "kb_chroma": logs_dir / "kb_chroma_consistency_check.json",
        "retrieval_check": logs_dir / "retrieval_readiness_check.json",
        "governance_check": logs_dir / "governance_readiness_check.json",
        "sd_check": logs_dir / "sd_config_readiness_check.json",
        "utf8_check": logs_dir / "utf8_readiness_check.json",
        "docs_check": logs_dir / "docs_alignment_check.json",
        "no_mutation": logs_dir / "no_mutation_proof.json",
        "final_summary": logs_dir / "final_runtime_readiness_summary.json",
    }


def _build_manifest(base_url: str, paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "schema_version": "readiness_sources_manifest_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "source_artifacts": [
            {"path": str(paths["project_state"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "living_doc", "used_for": ["current_stage", "runtime_architecture", "kb_state"]},
            {"path": str(paths["roadmap"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "living_doc", "used_for": ["next_prd_order"]},
            {"path": str(paths["prd_index"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "living_doc", "used_for": ["historical_prd_status"]},
            {"path": str(paths["runtime_smoke_utf8"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "runtime_artifact", "used_for": ["utf8_runtime", "counts"]},
            {"path": str(paths["retrieval_scorecard"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "quality_artifact", "used_for": ["retrieval_gate"]},
            {"path": str(paths["strict_gate_hf4"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "quality_artifact", "used_for": ["chroma_consistency", "no_mutation"]},
            {"path": str(paths["apply_result"].relative_to(REPO_ROOT)).replace("\\", "/"), "kind": "apply_artifact", "used_for": ["governance_authority_invariants"]},
        ],
        "live_sources": [
            {
                "base_url": base_url,
                "endpoints": [
                    "/",
                    "/api/status",
                    "/api/registry",
                    "/api/registry/",
                    "/api/dashboard",
                    "/api/dashboard/",
                ],
            }
        ],
    }


def _check_runtime_domain(project_state_text: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    required_terms = [
        "State Analyzer",
        "Thread Manager",
        "Memory Retrieval",
        "Context Assembly",
        "Diagnostic Card",
        "Writer Move Compliance",
        "Writer",
        "Validator/Trace",
        "Memory Update",
    ]
    missing = [term for term in required_terms if term not in project_state_text]
    has_no_legacy_cascade = _contains_case_insensitive(project_state_text, "без cascade legacy") or _contains_case_insensitive(project_state_text, "without cascade legacy")

    if missing:
        blockers.append(
            {
                "domain": "runtime",
                "code": "active_pipeline_not_documented",
                "details": f"missing_terms={missing}",
            }
        )
    if not has_no_legacy_cascade:
        warnings.append("legacy_cascade_clause_not_found")

    payload = {
        "schema_version": "runtime_readiness_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "active_pipeline": required_terms,
        "missing_terms": missing,
        "no_legacy_cascade_clause_found": has_no_legacy_cascade,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _check_admin_live_domain(
    *,
    base_url: str,
    strict: bool,
    offline_docs_only: bool,
    fetch_json: Callable[[str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []
    context: dict[str, Any] = {}

    endpoints = ["/", "/api/status", "/api/registry", "/api/registry/", "/api/dashboard", "/api/dashboard/"]
    mandatory_endpoints = ["/api/status", "/api/registry", "/api/registry/", "/api/dashboard", "/api/dashboard/"]
    checks: dict[str, Any] = {}

    if offline_docs_only:
        payload = {
            "schema_version": "live_admin_runtime_check_v1",
            "prd": PRD_ID,
            "generated_at_utc": _utc_now_iso(),
            "base_url": base_url,
            "offline_docs_only": True,
            "strict": strict,
            "api_checks": {},
            "status": "skipped_offline_docs_only",
            "blockers": [],
            "warnings": ["live_checks_skipped_offline_docs_only"],
        }
        return payload, [], ["live_checks_skipped_offline_docs_only"], context

    for endpoint in endpoints:
        checks[endpoint] = fetch_json(f"{base_url.rstrip('/')}{endpoint}")

    unreachable = [ep for ep, meta in checks.items() if not bool(meta.get("ok"))]
    non_200 = [ep for ep, meta in checks.items() if meta.get("ok") and int(meta.get("status_code") or 0) != 200]
    mandatory_unreachable = [ep for ep in unreachable if ep in mandatory_endpoints]
    mandatory_non_200 = [ep for ep in non_200 if ep in mandatory_endpoints]
    optional_root_unreachable = "/" in unreachable
    optional_root_non_200 = "/" in non_200

    if mandatory_unreachable and strict:
        blockers.append(
            {
                "domain": "admin_api",
                "code": "endpoint_unreachable",
                "details": f"unreachable={mandatory_unreachable}",
            }
        )
    if mandatory_non_200:
        blockers.append(
            {
                "domain": "admin_api",
                "code": "endpoint_http_non_200",
                "details": f"non_200={mandatory_non_200}",
            }
        )
    if optional_root_unreachable:
        warnings.append("root_endpoint_unreachable")
    if optional_root_non_200:
        warnings.append("root_endpoint_http_non_200")

    registry_payload = checks.get("/api/registry", {}).get("body")
    registry_slash_payload = checks.get("/api/registry/", {}).get("body")
    if not isinstance(registry_payload, (dict, list)):
        registry_payload = registry_slash_payload

    dashboard_payload = checks.get("/api/dashboard", {}).get("body")
    dashboard_slash_payload = checks.get("/api/dashboard/", {}).get("body")
    if not isinstance(dashboard_payload, dict):
        dashboard_payload = dashboard_slash_payload

    if not isinstance(registry_payload, (dict, list)):
        blockers.append({"domain": "admin_api", "code": "registry_payload_empty", "details": "registry payload missing"})
    if not isinstance(dashboard_payload, dict):
        blockers.append({"domain": "admin_api", "code": "dashboard_payload_empty", "details": "dashboard payload missing"})

    context["registry_payload"] = registry_payload
    context["dashboard_payload"] = dashboard_payload

    payload = {
        "schema_version": "live_admin_runtime_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "base_url": base_url,
        "offline_docs_only": False,
        "strict": strict,
        "api_checks": checks,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings, context


def _check_kb_chroma_domain(
    *,
    registry_payload: Any,
    dashboard_payload: Any,
    strict: bool,
    offline_docs_only: bool,
    expected_source_id: str,
    expected_source_title: str,
    expected_blocks: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    rows = _extract_registry_rows(registry_payload)
    done_rows = [r for r in rows if _normalize(r.get("status")).lower() == "done"]
    focus_rows = [r for r in done_rows if _normalize(r.get("source_id")) == expected_source_id]
    focus_row = focus_rows[0] if focus_rows else {}

    active_sources = len(done_rows)
    focus_id = _normalize(focus_row.get("source_id"))
    focus_title = _normalize(focus_row.get("title"))
    focus_blocks = int(focus_row.get("blocks_count") or 0)
    focus_protected = False
    delete_policy = focus_row.get("delete_policy") if isinstance(focus_row, dict) else None
    if isinstance(delete_policy, dict):
        focus_protected = _normalize(delete_policy.get("state")) == "protected"

    dashboard_blocks = None
    dashboard_chroma = None
    if isinstance(dashboard_payload, dict):
        dashboard_blocks = int((((dashboard_payload.get("blocks") or {}).get("production_total")) or 0))
        dashboard_chroma = int((((dashboard_payload.get("chroma") or {}).get("count")) or 0))

    direct_diag = run_diagnostic(
        source_prd=PRD_ID,
        botdb_dir=BOTDB_DIR,
        config_path=REPO_ROOT / "Bot_data_base" / "config.yaml",
        sample_ids_limit=10,
    )
    direct_count = direct_diag.get("total_count")
    try:
        direct_count = int(direct_count) if direct_count is not None else None
    except Exception:
        direct_count = None

    if offline_docs_only:
        warnings.append("kb_chroma_live_verification_skipped_offline_docs_only")
    else:
        if active_sources != 1:
            blockers.append({"domain": "knowledge_base", "code": "active_sources_not_one", "details": f"observed={active_sources}, expected=1"})
        if focus_id != expected_source_id:
            blockers.append({"domain": "knowledge_base", "code": "focus_source_id_mismatch", "details": f"observed={focus_id}, expected={expected_source_id}"})
        if not _contains_case_insensitive(focus_title, expected_source_title):
            blockers.append({"domain": "knowledge_base", "code": "focus_source_title_mismatch", "details": f"observed={focus_title}, expected~={expected_source_title}"})
        if focus_blocks != expected_blocks:
            blockers.append({"domain": "knowledge_base", "code": "focus_blocks_mismatch", "details": f"observed={focus_blocks}, expected={expected_blocks}"})
        if dashboard_blocks != expected_blocks:
            blockers.append({"domain": "chroma", "code": "dashboard_blocks_mismatch", "details": f"observed={dashboard_blocks}, expected={expected_blocks}"})
        if dashboard_chroma != expected_blocks:
            blockers.append({"domain": "chroma", "code": "dashboard_chroma_count_mismatch", "details": f"observed={dashboard_chroma}, expected={expected_blocks}"})
        if strict and direct_count != expected_blocks:
            blockers.append({"domain": "chroma", "code": "direct_chroma_count_mismatch", "details": f"observed={direct_count}, expected={expected_blocks}"})

    payload = {
        "schema_version": "kb_chroma_consistency_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "active_sources": active_sources,
        "focus_source_id": focus_id,
        "focus_source_title": focus_title,
        "focus_source_protected": focus_protected,
        "focus_blocks": focus_blocks,
        "dashboard_blocks": dashboard_blocks,
        "dashboard_chroma": dashboard_chroma,
        "direct_chroma_diagnostic": direct_diag,
        "direct_chroma_count": direct_count,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _check_retrieval_domain(paths: dict[str, Path]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    scorecard: dict[str, Any] = {}
    scorecard_path = paths["retrieval_scorecard"]
    if scorecard_path.exists():
        loaded = _read_json(scorecard_path)
        if isinstance(loaded, dict):
            scorecard = loaded
    else:
        blockers.append({"domain": "retrieval", "code": "retrieval_scorecard_missing", "details": str(scorecard_path)})

    smoke: dict[str, Any] = {}
    smoke_path = paths["retrieval_smoke"]
    if smoke_path.exists():
        loaded = _read_json(smoke_path)
        if isinstance(loaded, dict):
            smoke = loaded
    else:
        warnings.append("retrieval_quality_smoke_missing")

    t5_sem = float(scorecard.get("top5_semantic_match_rate") or 0.0)
    t5_gov = float(scorecard.get("top5_governance_present_rate") or 0.0)
    raw_leak_scorecard = bool(scorecard.get("raw_full_text_leak_detected"))
    internal_scorecard = int(scorecard.get("internal_only_unsafe_exposure_count") or 0)
    weak_cases = int(scorecard.get("weak_cases_count") or 0)

    raw_leak_smoke = bool(smoke.get("raw_full_text_leak_detected"))
    internal_smoke = int(smoke.get("internal_only_unsafe_exposure_count") or 0)
    smoke_passed = bool(smoke.get("retrieval_quality_passed")) if smoke else True

    if t5_sem < 1.0:
        blockers.append({"domain": "retrieval", "code": "top5_semantic_match_rate_below_threshold", "details": f"observed={t5_sem}, expected=1.0"})
    if t5_gov < 1.0:
        blockers.append({"domain": "retrieval", "code": "top5_governance_present_rate_below_threshold", "details": f"observed={t5_gov}, expected=1.0"})
    if raw_leak_scorecard or raw_leak_smoke:
        blockers.append({"domain": "retrieval", "code": "raw_full_text_leak_detected", "details": "true"})
    if internal_scorecard != 0 or internal_smoke != 0:
        blockers.append({"domain": "retrieval", "code": "internal_only_unsafe_exposure_nonzero", "details": f"scorecard={internal_scorecard}, smoke={internal_smoke}"})
    if weak_cases != 0:
        blockers.append({"domain": "retrieval", "code": "weak_cases_nonzero", "details": f"observed={weak_cases}, expected=0"})
    if not smoke_passed:
        blockers.append({"domain": "retrieval", "code": "retrieval_smoke_failed", "details": "retrieval_quality_passed=false"})

    payload = {
        "schema_version": "retrieval_readiness_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "artifacts": {
            "retrieval_scorecard": str(scorecard_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "retrieval_quality_smoke": str(smoke_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        },
        "top5_semantic_match_rate": t5_sem,
        "top5_governance_present_rate": t5_gov,
        "raw_full_text_leak_detected": raw_leak_scorecard or raw_leak_smoke,
        "internal_only_unsafe_exposure_count": max(internal_scorecard, internal_smoke),
        "weak_cases_count": weak_cases,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _check_governance_domain(paths: dict[str, Path], project_state_text: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    apply_result = _read_json(paths["apply_result"]) if paths["apply_result"].exists() else {}
    apply_summary = apply_result.get("apply_summary") if isinstance(apply_result, dict) else {}
    if not isinstance(apply_summary, dict):
        apply_summary = {}

    authority_checks = {
        "text_changed_count": int(apply_summary.get("text_changed_count") or 0),
        "chunk_type_changed_count": int(apply_summary.get("chunk_type_changed_count") or 0),
        "allowed_use_changed_count": int(apply_summary.get("allowed_use_changed_count") or 0),
        "safety_flags_changed_count": int(apply_summary.get("safety_flags_changed_count") or 0),
        "source_id_changed_count": int(apply_summary.get("source_id_changed_count") or 0),
        "block_id_changed_count": int(apply_summary.get("block_id_changed_count") or 0),
        "governance_invariant_violations": int(apply_summary.get("governance_invariant_violations") or 0),
    }

    if any(value != 0 for value in authority_checks.values()):
        blockers.append({"domain": "governance", "code": "authority_fields_mutated", "details": str(authority_checks)})

    internal_lens_clause = _contains_case_insensitive(project_state_text, "internal lens library")
    if not internal_lens_clause:
        warnings.append("internal_lens_clause_not_found_in_project_state")

    payload = {
        "schema_version": "governance_readiness_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "authority_checks": authority_checks,
        "deterministic_authority_preserved": not blockers,
        "llm_enrichment_advisory_only": not blockers,
        "internal_lens_clause_found": internal_lens_clause,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _check_sd_domain(
    *,
    paths: dict[str, Path],
    dashboard_payload: Any,
    offline_docs_only: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    cfg = _parse_yaml(paths["config"])
    sd = cfg.get("sd_labeling") if isinstance(cfg.get("sd_labeling"), dict) else {}
    legacy = cfg.get("legacy_sd_labeling") if isinstance(cfg.get("legacy_sd_labeling"), dict) else {}

    sd_enabled = bool(sd.get("enabled"))
    sd_legacy_mode = bool(sd.get("explicit_legacy_mode"))
    legacy_enabled = bool(legacy.get("enabled"))
    legacy_legacy_mode = bool(legacy.get("explicit_legacy_mode"))

    sd_effective = _read_json(paths["sd_config_effective"]) if paths["sd_config_effective"].exists() else {}
    effective_legacy_active = bool(sd_effective.get("legacy_sd_enabled_effective")) if isinstance(sd_effective, dict) else False

    runtime_legacy_active = None
    if isinstance(dashboard_payload, dict):
        runtime_legacy_active = bool((((dashboard_payload.get("governance") or {}).get("legacy_sd_active")) or False))

    if sd_enabled or sd_legacy_mode:
        blockers.append({"domain": "legacy_sd", "code": "sd_labeling_not_default_disabled", "details": f"enabled={sd_enabled}, explicit_legacy_mode={sd_legacy_mode}"})
    if legacy_enabled or legacy_legacy_mode:
        blockers.append({"domain": "legacy_sd", "code": "legacy_sd_labeling_not_default_disabled", "details": f"enabled={legacy_enabled}, explicit_legacy_mode={legacy_legacy_mode}"})
    if effective_legacy_active:
        blockers.append({"domain": "legacy_sd", "code": "legacy_sd_enabled_effective_true", "details": "sd_config_effective_state"})
    if not offline_docs_only and runtime_legacy_active is not None and runtime_legacy_active:
        blockers.append({"domain": "legacy_sd", "code": "runtime_legacy_sd_active_true", "details": "dashboard governance legacy_sd_active=true"})

    payload = {
        "schema_version": "sd_config_readiness_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "sd_labeling_enabled": sd_enabled,
        "sd_labeling_explicit_legacy_mode": sd_legacy_mode,
        "legacy_sd_labeling_enabled": legacy_enabled,
        "legacy_sd_labeling_explicit_legacy_mode": legacy_legacy_mode,
        "legacy_sd_enabled_effective": effective_legacy_active,
        "runtime_legacy_sd_active": runtime_legacy_active,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _check_utf8_domain(paths: dict[str, Path], logs_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    runtime_payload = _read_json(paths["runtime_smoke_utf8"]) if paths["runtime_smoke_utf8"].exists() else None
    utf8_payload = _read_json(paths["utf8_artifact_check"]) if paths["utf8_artifact_check"].exists() else None

    if runtime_payload is None:
        blockers.append({"domain": "utf8", "code": "runtime_smoke_utf8_missing", "details": str(paths["runtime_smoke_utf8"])})
    if utf8_payload is None:
        blockers.append({"domain": "utf8", "code": "utf8_artifact_check_missing", "details": str(paths["utf8_artifact_check"])})

    historical_markers: list[Any] = []
    if isinstance(utf8_payload, dict):
        historical_markers = list(utf8_payload.get("mojibake_markers_found") or [])
    if historical_markers:
        blockers.append({"domain": "utf8", "code": "historical_mojibake_markers_found", "details": f"count={len(historical_markers)}"})

    current_files = sorted(
        [
            path
            for path in logs_dir.glob("*.json")
            if path.is_file() and path.name not in {"utf8_readiness_check.json", "final_runtime_readiness_summary.json"}
        ]
    )
    current_markers: list[dict[str, Any]] = []
    for path in current_files:
        try:
            payload = _read_json(path)
            file_markers = _scan_mojibake(payload)
            for marker in file_markers:
                try:
                    marker["file"] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                except ValueError:
                    marker["file"] = str(path).replace("\\", "/")
            current_markers.extend(file_markers)
        except Exception:
            warnings.append(f"utf8_scan_skip_non_json:{path.name}")

    if current_markers:
        blockers.append({"domain": "utf8", "code": "current_prd_artifacts_have_mojibake_markers", "details": f"count={len(current_markers)}"})

    payload = {
        "schema_version": "utf8_readiness_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "markers_checked": list(MOJIBAKE_MARKERS),
        "runtime_smoke_utf8_exists": runtime_payload is not None,
        "utf8_artifact_check_exists": utf8_payload is not None,
        "historical_mojibake_markers_found": historical_markers,
        "current_prd_artifacts_scan_files": [
            str(p.relative_to(REPO_ROOT)).replace("\\", "/") if p.is_absolute() and REPO_ROOT in p.parents else str(p).replace("\\", "/")
            for p in current_files
        ],
        "current_prd_artifacts_mojibake_markers_found": current_markers,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _check_docs_domain(project_state_text: str, roadmap_text: str, prd_index_text: str, decisions_text: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []

    stage_expected = "post-PRD-046.0.11-final-runtime-readiness-summary"
    project_state_updated = stage_expected in project_state_text

    roadmap_has_done_046011 = _contains_case_insensitive(roadmap_text, "PRD-046.0.11") and _contains_case_insensitive(roadmap_text, "Done")
    roadmap_next_first_0461 = bool(re.search(r"## Next\s*\n1\.\s*PRD-046\.1", roadmap_text, flags=re.IGNORECASE))

    prd_index_updated = _contains_case_insensitive(prd_index_text, "| PRD-046.0.11 |")
    decisions_updated = _contains_case_insensitive(decisions_text, "PRD-046.0.11")

    if not project_state_updated:
        blockers.append({"domain": "docs", "code": "project_state_not_updated", "details": stage_expected})
    if not roadmap_has_done_046011:
        blockers.append({"domain": "docs", "code": "roadmap_done_entry_missing", "details": "PRD-046.0.11"})
    if not roadmap_next_first_0461:
        blockers.append({"domain": "docs", "code": "roadmap_next_order_invalid", "details": "Next #1 must be PRD-046.1"})
    if not prd_index_updated:
        blockers.append({"domain": "docs", "code": "prd_index_not_updated", "details": "row PRD-046.0.11 missing"})

    payload = {
        "schema_version": "docs_alignment_check_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "project_state_updated": project_state_updated,
        "roadmap_updated": roadmap_has_done_046011,
        "roadmap_next_first_prd_046_1": roadmap_next_first_0461,
        "prd_index_updated": prd_index_updated,
        "decisions_updated": decisions_updated,
        "status": "passed" if not blockers else "failed",
        "blockers": blockers,
        "warnings": warnings,
    }
    return payload, blockers, warnings


def _build_no_mutation_payload(paths: dict[str, Path], before_hashes: dict[str, str], after_hashes: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "final_runtime_readiness_no_mutation_proof_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "all_blocks_path": str(paths["all_blocks"].relative_to(REPO_ROOT)).replace("\\", "/"),
        "registry_path": str(paths["registry"].relative_to(REPO_ROOT)).replace("\\", "/"),
        "config_path": str(paths["config"].relative_to(REPO_ROOT)).replace("\\", "/"),
        "all_blocks_sha256_before": before_hashes["all_blocks"],
        "all_blocks_sha256_after": after_hashes["all_blocks"],
        "registry_sha256_before": before_hashes["registry"],
        "registry_sha256_after": after_hashes["registry"],
        "config_sha256_before": before_hashes["config"],
        "config_sha256_after": after_hashes["config"],
        "all_blocks_merged_mutated": before_hashes["all_blocks"] != after_hashes["all_blocks"],
        "registry_mutated": before_hashes["registry"] != after_hashes["registry"],
        "config_mutated": before_hashes["config"] != after_hashes["config"],
        "chroma_reindex_performed": False,
        "provider_called": False,
        "production_apply_performed": False,
        "source_reprocess_performed": False,
        "legacy_sd_enabled": False,
    }


def _render_final_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {PRD_ID} FINAL RUNTIME READINESS SUMMARY",
        "",
        "## Status",
        f"- final_status: `{summary.get('final_status')}`",
        f"- diagnostic_center_prerequisites_ready: `{summary.get('diagnostic_center_prerequisites_ready')}`",
        f"- next_prd: `{summary.get('next_prd')}`",
        "",
        "## Readiness Gates",
        f"- runtime_ready: `{summary.get('runtime_ready')}`",
        f"- admin_ready: `{summary.get('admin_ready')}`",
        f"- botdb_ready: `{summary.get('botdb_ready')}`",
        f"- kb_ready: `{summary.get('kb_ready')}`",
        f"- retrieval_ready: `{summary.get('retrieval_ready')}`",
        f"- governance_ready: `{summary.get('governance_ready')}`",
        f"- legacy_sd_disabled: `{summary.get('legacy_sd_disabled')}`",
        f"- utf8_artifacts_clean: `{summary.get('utf8_artifacts_clean')}`",
        f"- docs_aligned: `{summary.get('docs_aligned')}`",
        "",
        "## Counts",
    ]

    kb = ((summary.get("domains") or {}).get("knowledge_base") or {})
    chroma = ((summary.get("domains") or {}).get("chroma") or {})
    lines.extend(
        [
            f"- active_sources: `{kb.get('active_sources')}`",
            f"- focus_source_id: `{kb.get('focus_source_id')}`",
            f"- focus_source_title: `{kb.get('focus_source_title')}`",
            f"- blocks: `{kb.get('blocks')}`",
            f"- chroma_dashboard: `{chroma.get('dashboard_count')}`",
            f"- chroma_registry: `{chroma.get('registry_count')}`",
            f"- chroma_direct: `{chroma.get('direct_count')}`",
            "",
            "## Notes",
            "- Checks were executed in read-only mode for production BotDB/registry/Chroma data.",
            "- Historical proof was never used to override live mismatch.",
            "- Diagnostic Center transition is allowed only when `final_status=passed`.",
        ]
    )

    blockers = summary.get("blockers") if isinstance(summary.get("blockers"), list) else []
    warnings = summary.get("warnings") if isinstance(summary.get("warnings"), list) else []
    if blockers:
        lines.append("")
        lines.append("## Blockers")
        lines.extend([f"- `{item.get('domain')}` / `{item.get('code')}`: {item.get('details')}" for item in blockers if isinstance(item, dict)])
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.extend([f"- `{item}`" for item in warnings])

    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace, fetch_json: Callable[[str], dict[str, Any]] | None = None) -> dict[str, Any]:
    base_url = str(args.base_url)
    strict = bool(args.strict)
    offline_docs_only = bool(args.offline_docs_only)
    logs_dir = Path(args.logs_dir)
    if not logs_dir.is_absolute():
        logs_dir = (REPO_ROOT / logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    fetch = fetch_json or _http_json

    paths = _required_paths(REPO_ROOT, logs_dir)

    before_hashes = {
        "all_blocks": _sha256(paths["all_blocks"]),
        "registry": _sha256(paths["registry"]),
        "config": _sha256(paths["config"]),
    }

    manifest = _build_manifest(base_url, paths)
    _write_json(paths["manifest"], manifest)

    project_state_text = _read_text(paths["project_state"])
    roadmap_text = _read_text(paths["roadmap"])
    prd_index_text = _read_text(paths["prd_index"])
    decisions_text = _read_text(paths["decisions"])

    runtime_payload, runtime_blockers, runtime_warnings = _check_runtime_domain(project_state_text)

    admin_payload, admin_blockers, admin_warnings, admin_context = _check_admin_live_domain(
        base_url=base_url,
        strict=strict,
        offline_docs_only=offline_docs_only,
        fetch_json=fetch,
    )
    _write_json(paths["live_admin"], admin_payload)

    kb_chroma_payload, kb_chroma_blockers, kb_chroma_warnings = _check_kb_chroma_domain(
        registry_payload=admin_context.get("registry_payload"),
        dashboard_payload=admin_context.get("dashboard_payload"),
        strict=strict,
        offline_docs_only=offline_docs_only,
        expected_source_id=EXPECTED_SOURCE_ID,
        expected_source_title=EXPECTED_SOURCE_TITLE,
        expected_blocks=EXPECTED_BLOCKS,
    )
    _write_json(paths["kb_chroma"], kb_chroma_payload)

    retrieval_payload, retrieval_blockers, retrieval_warnings = _check_retrieval_domain(paths)
    _write_json(paths["retrieval_check"], retrieval_payload)

    governance_payload, governance_blockers, governance_warnings = _check_governance_domain(paths, project_state_text)
    _write_json(paths["governance_check"], governance_payload)

    sd_payload, sd_blockers, sd_warnings = _check_sd_domain(
        paths=paths,
        dashboard_payload=admin_context.get("dashboard_payload"),
        offline_docs_only=offline_docs_only,
    )
    _write_json(paths["sd_check"], sd_payload)

    docs_payload, docs_blockers, docs_warnings = _check_docs_domain(project_state_text, roadmap_text, prd_index_text, decisions_text)
    _write_json(paths["docs_check"], docs_payload)

    after_hashes = {
        "all_blocks": _sha256(paths["all_blocks"]),
        "registry": _sha256(paths["registry"]),
        "config": _sha256(paths["config"]),
    }
    no_mutation_payload = _build_no_mutation_payload(paths, before_hashes, after_hashes)
    _write_json(paths["no_mutation"], no_mutation_payload)

    utf8_payload, utf8_blockers, utf8_warnings = _check_utf8_domain(paths, logs_dir)
    _write_json(paths["utf8_check"], utf8_payload)

    no_mutation_blockers: list[dict[str, Any]] = []
    if bool(no_mutation_payload.get("all_blocks_merged_mutated")):
        no_mutation_blockers.append({"domain": "no_mutation", "code": "all_blocks_mutated", "details": "hash changed"})
    if bool(no_mutation_payload.get("registry_mutated")):
        no_mutation_blockers.append({"domain": "no_mutation", "code": "registry_mutated", "details": "hash changed"})
    if bool(no_mutation_payload.get("config_mutated")):
        no_mutation_blockers.append({"domain": "no_mutation", "code": "config_mutated", "details": "hash changed"})

    all_blockers = [
        *runtime_blockers,
        *admin_blockers,
        *kb_chroma_blockers,
        *retrieval_blockers,
        *governance_blockers,
        *sd_blockers,
        *utf8_blockers,
        *docs_blockers,
        *no_mutation_blockers,
    ]
    all_warnings = sorted(
        set(
            [
                *runtime_warnings,
                *admin_warnings,
                *kb_chroma_warnings,
                *retrieval_warnings,
                *governance_warnings,
                *sd_warnings,
                *utf8_warnings,
                *docs_warnings,
            ]
        )
    )

    if offline_docs_only and not any(item.get("code") == "offline_docs_only_cannot_pass" for item in all_blockers if isinstance(item, dict)):
        all_blockers.append(
            {
                "domain": "final",
                "code": "offline_docs_only_cannot_pass",
                "details": "offline-docs-only mode cannot produce final passed readiness",
            }
        )

    final_status = "passed" if not all_blockers else "done_with_readiness_blocker"
    prereq_ready = final_status == "passed"

    kb_focus_blocks = kb_chroma_payload.get("focus_blocks")
    dashboard_blocks = kb_chroma_payload.get("dashboard_blocks")
    dashboard_chroma = kb_chroma_payload.get("dashboard_chroma")
    direct_chroma = kb_chroma_payload.get("direct_chroma_count")

    summary = {
        "schema_version": "final_runtime_readiness_summary_v1",
        "prd": PRD_ID,
        "generated_at_utc": _utc_now_iso(),
        "base_url": base_url,
        "final_status": final_status,
        "diagnostic_center_prerequisites_ready": prereq_ready,
        "next_prd": NEXT_PRD,
        "runtime_ready": runtime_payload.get("status") == "passed",
        "admin_ready": admin_payload.get("status") == "passed",
        "botdb_ready": (kb_chroma_payload.get("status") == "passed") and (sd_payload.get("status") == "passed"),
        "kb_ready": kb_chroma_payload.get("status") == "passed",
        "retrieval_ready": retrieval_payload.get("status") == "passed",
        "governance_ready": governance_payload.get("status") == "passed",
        "legacy_sd_disabled": sd_payload.get("status") == "passed",
        "utf8_artifacts_clean": utf8_payload.get("status") == "passed",
        "docs_aligned": docs_payload.get("status") == "passed",
        "domains": {
            "runtime": {
                "status": runtime_payload.get("status"),
                "active_pipeline": runtime_payload.get("active_pipeline"),
            },
            "admin_api": {
                "status": admin_payload.get("status"),
                "endpoints": {
                    endpoint: (meta.get("status_code") if isinstance(meta, dict) else None)
                    for endpoint, meta in (admin_payload.get("api_checks") or {}).items()
                },
            },
            "knowledge_base": {
                "status": kb_chroma_payload.get("status"),
                "active_sources": kb_chroma_payload.get("active_sources"),
                "focus_source_id": kb_chroma_payload.get("focus_source_id"),
                "focus_source_title": kb_chroma_payload.get("focus_source_title"),
                "blocks": kb_focus_blocks,
            },
            "chroma": {
                "status": "passed" if kb_chroma_payload.get("status") == "passed" else "failed",
                "dashboard_count": dashboard_chroma,
                "registry_count": kb_focus_blocks,
                "direct_count": direct_chroma,
                "dashboard_blocks_count": dashboard_blocks,
            },
            "retrieval": {
                "status": retrieval_payload.get("status"),
                "raw_full_text_leak_detected": retrieval_payload.get("raw_full_text_leak_detected"),
                "internal_only_unsafe_exposure_count": retrieval_payload.get("internal_only_unsafe_exposure_count"),
                "weak_cases_count": retrieval_payload.get("weak_cases_count"),
            },
            "governance": {
                "status": governance_payload.get("status"),
                "deterministic_authority_preserved": governance_payload.get("deterministic_authority_preserved"),
                "llm_enrichment_advisory_only": governance_payload.get("llm_enrichment_advisory_only"),
            },
            "legacy_sd": {
                "status": sd_payload.get("status"),
                "sd_labeling_enabled": sd_payload.get("sd_labeling_enabled"),
                "legacy_sd_labeling_enabled": sd_payload.get("legacy_sd_labeling_enabled"),
                "legacy_sd_active": sd_payload.get("runtime_legacy_sd_active"),
            },
            "utf8": {
                "status": utf8_payload.get("status"),
                "mojibake_markers_found": utf8_payload.get("current_prd_artifacts_mojibake_markers_found"),
            },
            "docs": {
                "status": docs_payload.get("status"),
                "project_state_updated": docs_payload.get("project_state_updated"),
                "roadmap_updated": docs_payload.get("roadmap_updated"),
                "prd_index_updated": docs_payload.get("prd_index_updated"),
                "decisions_updated": docs_payload.get("decisions_updated"),
            },
            "no_mutation": {
                "status": "passed" if not no_mutation_blockers else "failed",
                "all_blocks_merged_mutated": no_mutation_payload.get("all_blocks_merged_mutated"),
                "registry_mutated": no_mutation_payload.get("registry_mutated"),
                "chroma_reindex_performed": no_mutation_payload.get("chroma_reindex_performed"),
                "provider_called": no_mutation_payload.get("provider_called"),
                "production_apply_performed": no_mutation_payload.get("production_apply_performed"),
            },
        },
        "blockers": all_blockers,
        "warnings": all_warnings,
    }

    _write_json(paths["final_summary"], summary)

    final_report = _render_final_summary_markdown(summary)
    _write_text(REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-046.0.11_FINAL_RUNTIME_READINESS_SUMMARY.md", final_report)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.11 final runtime readiness summary runner.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--logs-dir", default="TO_DO_LIST/logs/PRD-046.0.11")
    parser.add_argument("--offline-docs-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
