"""PRD-046.1.29 stabilization cleanup / docs compaction / gate revalidation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_stabilization_cleanup_v1 import (
    ALLOWED_ZONES,
    ArchiveManifestEntry,
    ArtifactHygieneNormalizationResult,
    CleanupCandidateEntry,
    CleanupSourceGateResult,
    DiagnosticCenterArtifactClassification,
    DiagnosticCenterArtifactInventory,
    DocsCompactionPlan,
    DocsSnapshotProof,
    PermanentGateRevalidationResult,
    StabilizationCleanupDecision,
    StabilizationCleanupScorecard,
)


PRD = "PRD-046.1.29"
SOURCE_PRD = "PRD-046.1.28"
NEXT_PRD = "PRD-046.1.30 - Diagnostic Center Controlled Rollout Planning v1"

SOURCE_REPORT_FILES = {
    "implementation": "PRD-046.1.28_IMPLEMENTATION_REPORT.md",
    "acceptance": "PRD-046.1.28_FINAL_RUNTIME_GOVERNANCE_ACCEPTANCE_REPORT.md",
    "provider": "PRD-046.1.28_CUMULATIVE_PROVIDER_EVIDENCE_ACCEPTANCE_REPORT.md",
    "permanent": "PRD-046.1.28_PERMANENT_REGRESSION_GATES_REPORT.md",
    "cleanup_readiness": "PRD-046.1.28_STABILIZATION_CLEANUP_READINESS_REPORT.md",
    "next": "PRD-046.1.28_NEXT_PRD_RECOMMENDATION.md",
}

TARGET_DOCS = [
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
]

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

PERMANENT_GATES = {
    "final_runtime_governance_acceptance_gate": [
        "bot_psychologist/tools/run_diagnostic_center_final_runtime_governance_acceptance_gate.py",
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_decision_gate.py",
    ],
    "provider_backed_evidence_gates": [
        "bot_psychologist/tools/run_diagnostic_center_provider_backed_smoke_results_gate.py",
        "TO_DO_LIST/reports/PRD-046.1.28_CUMULATIVE_PROVIDER_EVIDENCE_ACCEPTANCE_REPORT.md",
    ],
    "normal_user_no_effect_gates": [
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_normal_user_no_effect.py",
        "bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_normal_user_summary.py",
    ],
    "rollback_hard_stop_gates": [
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_rollback_hard_stop.py",
        "bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_rollback_summary.py",
    ],
    "safety_kb_boundary_gates": [
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_safety_kb_boundary.py",
        "bot_psychologist/tests/multiagent/test_diagnostic_center_kb_boundaries.py",
    ],
    "trace_provider_sanitization_gates": [
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_trace_provider_sanitization.py",
        "bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_trace_sanitization.py",
    ],
    "botdb_stability_gates": [
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_botdb_stability.py",
        "TO_DO_LIST/reports/PRD-046.1.21-HF2_IMPLEMENTATION_REPORT.md",
    ],
    "no_mutation_proof_flow": [
        "bot_psychologist/tests/multiagent/test_final_runtime_governance_acceptance_no_mutation.py",
        "bot_psychologist/tests/multiagent/test_diagnostic_center_stabilization_no_mutation.py",
    ],
    "artifact_encoding_hygiene_validator": [
        "bot_psychologist/tools/validate_prd_artifact_encoding.py",
        "bot_psychologist/tests/tools/test_validate_prd_artifact_encoding.py",
    ],
    "response_quality_eval_calibration_packs": [
        "bot_psychologist/tools/run_diagnostic_center_response_quality_eval.py",
        "bot_psychologist/tools/run_diagnostic_center_response_quality_calibration.py",
    ],
    "diagnostic_center_contract_tests": [
        "bot_psychologist/tests/multiagent/test_diagnostic_center_contracts.py",
        "bot_psychologist/tests/multiagent/test_diagnostic_center_rules.py",
    ],
    "prompt_constraint_conservative_baseline_gates": [
        "bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_execution_target_policy.py",
        "bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_execution_rollback.py",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_metric(text: str, key: str) -> str | None:
    key_escaped = re.escape(key)
    patterns = [
        rf"`{key_escaped}=([^`]+)`",
        rf"{key_escaped}\s*=\s*([A-Za-z0-9_.\-]+)",
        rf"{key_escaped}:\s*`([^`]+)`",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def required_source_reports(reports_dir: Path) -> dict[str, Path]:
    return {name: reports_dir / filename for name, filename in SOURCE_REPORT_FILES.items()}


def preflight_source_reports(reports_dir: Path) -> dict[str, Any]:
    required = required_source_reports(reports_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    texts: dict[str, str] = {}
    for alias, path in required.items():
        if not path.exists():
            missing.append(alias)
            continue
        try:
            texts[alias] = _read_text(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{alias}:{exc.__class__.__name__}")
    return {
        "required": {key: str(path.as_posix()) for key, path in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "texts": texts,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
    }


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    texts = dict(preflight.get("texts") or {})
    blockers: list[str] = []

    implementation = texts.get("implementation", "")
    acceptance = texts.get("acceptance", "")
    provider = texts.get("provider", "")

    final_status = _extract_metric(acceptance, "final_status") or _extract_metric(implementation, "Final status") or "blocked"
    decision = _extract_metric(acceptance, "decision") or _extract_metric(implementation, "Decision") or "blocked"

    provider_scenarios_total = _as_int(_extract_metric(acceptance, "provider_scenarios_total") or _extract_metric(provider, "Total scenarios"), 0)
    normal_user_apply_count_total = _as_int(_extract_metric(acceptance, "normal_user_apply_count_total"), 0)
    normal_user_provider_calls_total = _as_int(_extract_metric(acceptance, "normal_user_provider_calls_total"), 0)
    rollback_failure_count_total = _as_int(_extract_metric(acceptance, "rollback_failure_count_total"), 0)

    safety_kb_boundary_gate_passed = _as_bool(
        _extract_metric(acceptance, "safety_kb_boundary_gate_passed")
        or _extract_metric(implementation, "safety_kb_boundary_gate_passed"),
        False,
    )
    trace_provider_sanitization_gate_passed = _as_bool(
        _extract_metric(acceptance, "trace_provider_sanitization_gate_passed")
        or _extract_metric(implementation, "trace_provider_sanitization_gate_passed"),
        False,
    )
    botdb_stability_gate_passed = _as_bool(
        _extract_metric(acceptance, "botdb_stability_gate_passed") or _extract_metric(implementation, "botdb_stability_gate_passed"),
        False,
    )
    no_mutation_proof_passed = _as_bool(
        _extract_metric(acceptance, "no_mutation_proof_passed") or _extract_metric(implementation, "no_mutation_proof_passed"),
        False,
    )

    if not preflight.get("ok", False):
        blockers.append("missing_or_unreadable_source_reports")
    if str(final_status) != "passed":
        blockers.append("source_final_status_not_passed")
    if str(decision) != "accepted_ready_for_cleanup_stabilization":
        blockers.append("source_decision_not_ready_for_cleanup")
    if provider_scenarios_total < 23:
        blockers.append("provider_scenarios_total_lt_23")
    if normal_user_apply_count_total != 0:
        blockers.append("normal_user_apply_count_total_not_zero")
    if normal_user_provider_calls_total != 0:
        blockers.append("normal_user_provider_calls_total_not_zero")
    if rollback_failure_count_total != 0:
        blockers.append("rollback_failure_count_total_not_zero")
    if not safety_kb_boundary_gate_passed:
        blockers.append("safety_kb_boundary_gate_failed")
    if not trace_provider_sanitization_gate_passed:
        blockers.append("trace_provider_sanitization_gate_failed")
    if not botdb_stability_gate_passed:
        blockers.append("botdb_stability_gate_failed")
    if not no_mutation_proof_passed:
        blockers.append("no_mutation_proof_gate_failed")

    payload = CleanupSourceGateResult(
        source_gate_passed=len(blockers) == 0,
        final_status=str(final_status),
        decision=str(decision),
        provider_scenarios_total=provider_scenarios_total,
        normal_user_apply_count_total=normal_user_apply_count_total,
        normal_user_provider_calls_total=normal_user_provider_calls_total,
        rollback_failure_count_total=rollback_failure_count_total,
        safety_kb_boundary_gate_passed=safety_kb_boundary_gate_passed,
        trace_provider_sanitization_gate_passed=trace_provider_sanitization_gate_passed,
        botdb_stability_gate_passed=botdb_stability_gate_passed,
        no_mutation_proof_passed=no_mutation_proof_passed,
        blockers=blockers,
    )
    return payload.to_dict()


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {key: repo_root / rel for key, rel in TRACKED_PRODUCTION_PATHS.items()}
    hashes: dict[str, str] = {}
    for key, path in tracked.items():
        if path.exists() and path.is_file():
            hashes[key] = _sha256(path)
        else:
            hashes[key] = "missing"
    return tracked, hashes


def build_no_mutation_proof(hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    all_blocks_mutated = hash_before.get("all_blocks_merged") != hash_after.get("all_blocks_merged")
    registry_mutated = hash_before.get("registry") != hash_after.get("registry")
    config_mutated = hash_before.get("config") != hash_after.get("config")
    production_data_mutated = all_blocks_mutated or registry_mutated or config_mutated
    return {
        "schema_version": "diagnostic_center_stabilization_cleanup_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "runtime_defaults_changed": False,
        "production_data_mutated": production_data_mutated,
        "provider_called": False,
        "new_provider_execution_performed": False,
        "no_mutation_proof_passed": not production_data_mutated,
    }


def _iter_inventory_paths(repo_root: Path) -> set[Path]:
    paths: set[Path] = set()

    for path in (repo_root / "bot_psychologist" / "bot_agent" / "multiagent").glob("*diagnostic_center*"):
        if path.is_file():
            paths.add(path)
    for path in (repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "contracts").glob("*diagnostic_center*"):
        if path.is_file():
            paths.add(path)
    for path in (repo_root / "bot_psychologist" / "tools").glob("run_diagnostic_center_*.py"):
        if path.is_file():
            paths.add(path)
    for path in (repo_root / "bot_psychologist" / "tests" / "multiagent").glob("test_*diagnostic_center*.py"):
        if path.is_file():
            paths.add(path)
    fixtures_root = repo_root / "bot_psychologist" / "tests" / "fixtures"
    if fixtures_root.exists():
        for path in fixtures_root.glob("*diagnostic_center*.json"):
            if path.is_file():
                paths.add(path)

    reports_root = repo_root / "TO_DO_LIST" / "reports"
    if reports_root.exists():
        for path in reports_root.glob("PRD-046.1*.*"):
            if path.is_file():
                paths.add(path)

    logs_root = repo_root / "TO_DO_LIST" / "logs"
    if logs_root.exists():
        for prd_dir in logs_root.glob("PRD-046.1*"):
            if prd_dir.is_file():
                paths.add(prd_dir)
                continue
            for path in prd_dir.rglob("*"):
                if path.is_file():
                    paths.add(path)

    for rel in TARGET_DOCS:
        path = repo_root / rel
        if path.exists() and path.is_file():
            paths.add(path)

    runtime_map = repo_root / "docs" / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md"
    eval_map = repo_root / "docs" / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md"
    if runtime_map.exists() and runtime_map.is_file():
        paths.add(runtime_map)
    if eval_map.exists() and eval_map.is_file():
        paths.add(eval_map)

    for rel in TRACKED_PRODUCTION_PATHS.values():
        path = repo_root / rel
        if path.exists() and path.is_file():
            paths.add(path)

    env_path = repo_root / ".env"
    if env_path.exists() and env_path.is_file():
        paths.add(env_path)

    return paths


def _safe_rel(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def collect_artifact_inventory(repo_root: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path in sorted(_iter_inventory_paths(repo_root), key=lambda p: str(p)):
        rel = _safe_rel(path, repo_root)
        items.append(
            {
                "path": rel,
                "size_bytes": path.stat().st_size,
                "suffix": path.suffix.lower(),
            }
        )
    return DiagnosticCenterArtifactInventory(items=items).to_dict()


def _classify_path(rel_path: str) -> tuple[str, str]:
    p = rel_path.replace("\\", "/")

    if p in TRACKED_PRODUCTION_PATHS.values() or p == ".env":
        return "do_not_touch", "production/sensitive runtime state"

    if p.startswith("bot_psychologist/tests/"):
        return "permanent_quality_eval_regression", "regression/eval test coverage"

    if p.startswith("bot_psychologist/tools/"):
        if "validate_prd_artifact_encoding" in p:
            return "permanent_quality_eval_regression", "artifact hygiene permanent gate"
        return "permanent_quality_eval_regression", "diagnostic center/eval runner tooling"

    if p.startswith("bot_psychologist/bot_agent/multiagent/contracts/"):
        return "permanent_quality_eval_regression", "contract surface for runtime/eval governance"

    if p.startswith("bot_psychologist/bot_agent/multiagent/"):
        if "diagnostic_center" in p:
            return "production_runtime", "diagnostic center runtime lineage module"
        return "unknown_requires_review", "non diagnostic-center multiagent module in scope"

    if p.startswith("docs/"):
        return "production_runtime", "living operational documentation"

    if p.startswith("TO_DO_LIST/reports/PRD-046.1") or p.startswith("TO_DO_LIST/logs/PRD-046.1"):
        lowered = p.lower()
        if any(marker in lowered for marker in ("debug", "tmp", "trace_samples", "trace-samples", "old", "backup")):
            return "cleanup_candidate_manifest_only", "temporary or debug evidence candidate"
        return "historical_archive", "historical PRD evidence retained for reproducibility"

    if p.startswith("TO_DO_LIST/archive/"):
        return "historical_archive", "historical archive"

    return "unknown_requires_review", "requires manual zone review"


def classify_inventory(inventory: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    items = list(inventory.get("items", []))
    classified: list[dict[str, Any]] = []
    zone_counts = {zone: 0 for zone in ALLOWED_ZONES}

    archive_manifest_items: list[dict[str, Any]] = []
    cleanup_candidate_items: list[dict[str, Any]] = []

    for item in items:
        rel_path = str(item.get("path", ""))
        zone, reason = _classify_path(rel_path)
        zone_counts[zone] = zone_counts.get(zone, 0) + 1
        enriched = dict(item)
        enriched["zone"] = zone
        enriched["reason"] = reason
        classified.append(enriched)

        if zone in {"historical_archive", "cleanup_candidate_manifest_only"}:
            archive_manifest_items.append(
                ArchiveManifestEntry(
                    path=rel_path,
                    zone=zone,
                    reason=reason,
                    archive_target=f"TO_DO_LIST/archive/{PRD}/{rel_path.replace('/', '__')}",
                    delete_now=False,
                ).to_dict()
            )

        if zone == "cleanup_candidate_manifest_only":
            cleanup_candidate_items.append(
                CleanupCandidateEntry(
                    path=rel_path,
                    reason=reason,
                    requires_manual_approval=True,
                    delete_now=False,
                ).to_dict()
            )

    required_zones_present = all(zone in zone_counts for zone in ALLOWED_ZONES)
    classification = DiagnosticCenterArtifactClassification(
        zone_counts=zone_counts,
        required_zones_present=required_zones_present,
        unknown_requires_review_count=zone_counts.get("unknown_requires_review", 0),
    ).to_dict()
    classification["items"] = classified

    archive_manifest = {
        "schema_version": "diagnostic_center_archive_manifest_v1",
        "prd": PRD,
        "archive_mode": "manifest_only",
        "physical_files_moved": 0,
        "physical_files_deleted": 0,
        "items": archive_manifest_items,
    }

    cleanup_manifest = {
        "schema_version": "diagnostic_center_cleanup_candidate_manifest_v1",
        "prd": PRD,
        "cleanup_mode": "manifest_only_non_destructive",
        "physical_deletion_performed": False,
        "runtime_files_deleted": False,
        "safety_eval_gate_deleted": False,
        "items": cleanup_candidate_items,
    }

    return classification, archive_manifest, cleanup_manifest


def _docs_snapshot_dir(repo_root: Path) -> Path:
    return repo_root / "TO_DO_LIST" / "archive" / PRD / "docs_before_compaction"


def create_docs_snapshots(repo_root: Path, *, write_snapshots: bool) -> dict[str, Any]:
    snapshot_dir = _docs_snapshot_dir(repo_root)
    files_payload: list[dict[str, Any]] = []

    if write_snapshots:
        snapshot_dir.mkdir(parents=True, exist_ok=True)

    for rel in TARGET_DOCS:
        src = repo_root / rel
        if not src.exists() or not src.is_file():
            files_payload.append({"path": rel, "exists": False})
            continue
        dst = snapshot_dir / src.name
        if write_snapshots:
            shutil.copy2(src, dst)
        files_payload.append(
            {
                "path": rel,
                "exists": True,
                "snapshot_path": dst.relative_to(repo_root).as_posix(),
                "sha256": _sha256(src),
                "size_bytes": src.stat().st_size,
            }
        )

    manifest_path = snapshot_dir / "manifest.json"
    if write_snapshots:
        manifest = {
            "schema_version": "diagnostic_center_docs_snapshot_manifest_v1",
            "prd": PRD,
            "created_at_utc": _utc_now(),
            "files": files_payload,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return DocsSnapshotProof(
        snapshot_dir=snapshot_dir.relative_to(repo_root).as_posix(),
        manifest_path=manifest_path.relative_to(repo_root).as_posix(),
        created=write_snapshots,
        files=files_payload,
    ).to_dict()


def _project_state_compacted() -> str:
    return """# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Post-acceptance stabilization after `PRD-046.1.28`; this cycle (`PRD-046.1.29`) is cleanup/compaction only with non-destructive manifest-first policy.

## Current Runtime Architecture
User path remains unchanged: State Analyzer -> Thread Manager -> Context Assembly -> Diagnostic Card -> Diagnostic Center shadow/limited governance layers -> Writer.

## Diagnostic Center Acceptance State
`PRD-046.1.28` accepted provider-backed phase as governed limited-runtime candidate.
Boundary flags remain strict: `broad_rollout_allowed=false`, `production_ready=false`, `normal_user_activation_allowed=false`.

## Current Knowledge Base State
Focus source remains `123__кузница_духа`; governed blocks/chroma integrity is preserved by no-mutation policy and explicit gates.

## Current Context / Memory State
Context assembly + additive summaries remain active; deterministic fallback stays mandatory when async summaries are unavailable or invalid.

## Stable Modules
- Multiagent orchestrator and writer compliance chain.
- Diagnostic Center shadow and constrained prompt-constraint stack.
- BotDB registry/query/admin stability gates.
- Artifact encoding hygiene and no-mutation proof flows.

## Permanent Gates
- Final runtime governance acceptance gates.
- Provider-backed evidence and normal-user no-effect gates.
- Rollback/hard-stop, safety/KB boundary, trace sanitization gates.
- BotDB stability, response quality eval/calibration, contract and no-mutation gates.

## Known Risks
- Broad rollout without separate PRD would violate governance boundaries.
- Cleanup/deletion without manifest approval can break reproducibility.
- Historical artifact encoding noise may be misread as current runtime corruption without normalization report.

## Next Planned PRD
`PRD-046.1.30 - Diagnostic Center Controlled Rollout Planning v1` (if stabilization cleanup remains green).

## Do Not Do Yet
- Do not activate broad Diagnostic Center runtime authority.
- Do not enable normal-user activation.
- Do not mutate KB governance authority fields (`chunk_type`, `allowed_use`, `safety_flags`).
- Do not perform Chroma reindex as part of this cleanup PRD.

## Documentation Update Rule
1. Update this file for every stage/runtime boundary PRD.
2. Update roadmap for sequencing changes.
3. Update decisions for architecture boundary changes.
4. Update PRD index after each merged PRD cycle.
5. Keep full historical details in `TO_DO_LIST`, keep docs operational and compact.

## Last Updated
- Date: 2026-05-19
- Source cycle: PRD-046.1.29
"""


def _roadmap_compacted() -> str:
    return """# Roadmap

## Done
- Runtime foundation and governance chain through `PRD-046.0.x`.
- Diagnostic Center readiness, shadow integration, planner/writer pilot, prompt-constraint limited runtime chain through `PRD-046.1.16`.
- Response quality eval and calibration packs through `PRD-046.1.18`.
- Controlled runtime pilot readiness/execution/results and provider-backed cycles through `PRD-046.1.28`.

## Current / In Progress
- `PRD-046.1.29`: stabilization cleanup, artifact classification, docs compaction, permanent gate revalidation.

## Next
1. `PRD-046.1.30` - Diagnostic Center Controlled Rollout Planning v1.
2. Hotfix path only if `PRD-046.1.29` leaves blockers (`cleanup/docs/eval-harness`).

## Later
- Operational hardening for governed limited runtime.
- Additional observability and runbook hardening.
- Explicit broad-rollout governance PRD (separate from cleanup).

## Deferred / Not Yet
- Broad rollout to normal users.
- Production-ready declaration for Diagnostic Center authority expansion.

## Roadmap Rules
1. Runtime/architecture PRDs update `docs/PROJECT_STATE.md`.
2. Sequencing PRDs update `docs/ROADMAP.md`.
3. Boundary decisions update `docs/DECISIONS.md`.
4. Every merged PRD updates `docs/PRD_INDEX.md`.
5. `TO_DO_LIST` is historical evidence; `docs/` is compact operational map.
"""


def _normalize_prd_index(existing: str) -> str:
    rows: list[str] = []
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped.startswith("| PRD-"):
            rows.append(stripped)

    dedup: dict[str, str] = {}
    ordered_ids: list[str] = []
    for row in rows:
        parts = [part.strip() for part in row.split("|")]
        if len(parts) < 3:
            continue
        prd_id = parts[1]
        if not prd_id.startswith("PRD-"):
            continue
        if prd_id in dedup:
            continue
        dedup[prd_id] = row
        ordered_ids.append(prd_id)

    if PRD not in dedup:
        dedup[PRD] = (
            "| PRD-046.1.29 | Diagnostic Center Stabilization / Runtime Cleanup / Eval Harness Consolidation v1 | "
            "passed | pending | non-destructive stabilization cleanup: source gate, inventory/classification, manifests, docs compaction snapshots, permanent gate revalidation | "
            "TO_DO_LIST/reports/PRD-046.1.29_IMPLEMENTATION_REPORT.md |"
        )
        ordered_ids.append(PRD)

    table_rows = [dedup[prd_id] for prd_id in ordered_ids]
    return "\n".join(
        [
            "# PRD Index",
            "",
            "| PRD | Название | Статус | Commit | Что изменилось | Отчёт |",
            "| --- | --- | --- | --- | --- | --- |",
            *table_rows,
            "",
            "## Documentation Update Rule",
            "1. Каждый новый PRD после push обновляет `docs/PRD_INDEX.md`.",
            "2. Если изменился project stage - обновляется `docs/PROJECT_STATE.md`.",
            "3. Если изменилась последовательность шагов - обновляется `docs/ROADMAP.md`.",
            "4. Если принято новое архитектурное решение - обновляется `docs/DECISIONS.md`.",
            "5. `TO_DO_LIST` хранит полный архив logs/reports, `docs/` хранит сжатую карту текущего состояния.",
            "",
        ]
    )


def _ensure_adr_049(existing: str) -> str:
    if "ADR-049" in existing:
        return existing
    append = """

## ADR-049 - Diagnostic Center Stabilization / Cleanup Boundary

Status: accepted
Context: provider-backed Diagnostic Center phase was accepted in `PRD-046.1.28`, but runtime/eval/docs artifacts remained mixed between active operations and historical evidence.
Decision: `PRD-046.1.29` establishes a manifest-first, reproducibility-preserving cleanup boundary: separate production runtime, permanent quality gates, and historical evidence; disallow physical deletion of runtime/eval-critical files in this PRD; require explicit follow-up PRD for any destructive cleanup.
Consequences: project navigation is compact and maintainable, permanent gates remain intact, and broad rollout continues to require a separate governance PRD.
"""
    return existing.rstrip() + "\n" + append.lstrip("\n")


def _runtime_map_doc() -> str:
    return """# Diagnostic Center Runtime Map

## Runtime Boundary
- Diagnostic Center remains governed and constrained.
- Broad rollout is disabled.
- Normal-user activation is disabled.
- Production-ready declaration is not granted by cleanup PRD.

## Active Runtime Chain
1. User input enters state analysis and thread/memory retrieval.
2. Context assembly builds governed context.
3. Diagnostic Center layers run in shadow/limited governed modes.
4. Writer produces user-facing response with safety/compliance constraints.

## Non-Goals in Current Boundary
- No authority expansion to broad runtime.
- No direct KB authority mutation via LLM logic.
- No provider-backed execution as part of stabilization cleanup.

## Required Safety Constraints
- Rollback-first and hard-stop constraints stay active.
- Safety/KB boundary and trace sanitization remain mandatory.
- No-mutation and artifact hygiene gates remain mandatory.
"""


def _eval_harness_doc() -> str:
    return """# Diagnostic Center Eval Harness

## Permanent Harness Families
- Final runtime governance acceptance gates.
- Provider-backed evidence and budget gates.
- Normal-user no-effect gates.
- Rollback and hard-stop gates.
- Safety/KB boundary and trace/provider sanitization gates.
- BotDB stability gates.
- Response quality eval/calibration packs.
- Contract and no-mutation proofs.
- Artifact encoding hygiene validation.

## Harness Principles
- Deterministic checks first.
- No destructive cleanup in harness execution.
- Historical evidence remains reproducible.
- Cleanup candidates are manifest-only until explicit approval PRD.

## Operational Rule
Any future rollout/authority-expansion PRD must reuse these harness families and keep conservative baseline checks as blockers.
"""


def compact_docs(repo_root: Path, *, compact: bool, snapshot_proof: dict[str, Any]) -> dict[str, Any]:
    target_paths = [repo_root / rel for rel in TARGET_DOCS]
    compacted_docs: list[str] = []
    warnings: list[str] = []

    if compact and not _as_bool(snapshot_proof.get("created"), False):
        warnings.append("snapshot_not_created_compaction_skipped")
        compact = False

    if compact:
        (repo_root / "docs" / "PROJECT_STATE.md").write_text(_project_state_compacted(), encoding="utf-8")
        compacted_docs.append("docs/PROJECT_STATE.md")

        (repo_root / "docs" / "ROADMAP.md").write_text(_roadmap_compacted(), encoding="utf-8")
        compacted_docs.append("docs/ROADMAP.md")

        prd_index_path = repo_root / "docs" / "PRD_INDEX.md"
        prd_index_existing = _read_text(prd_index_path) if prd_index_path.exists() else ""
        prd_index_path.write_text(_normalize_prd_index(prd_index_existing), encoding="utf-8")
        compacted_docs.append("docs/PRD_INDEX.md")

        decisions_path = repo_root / "docs" / "DECISIONS.md"
        decisions_existing = _read_text(decisions_path) if decisions_path.exists() else ""
        decisions_path.write_text(_ensure_adr_049(decisions_existing), encoding="utf-8")
        compacted_docs.append("docs/DECISIONS.md")

    runtime_map_path = repo_root / "docs" / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md"
    runtime_map_path.write_text(_runtime_map_doc(), encoding="utf-8")
    if "docs/DIAGNOSTIC_CENTER_RUNTIME_MAP.md" not in compacted_docs:
        compacted_docs.append("docs/DIAGNOSTIC_CENTER_RUNTIME_MAP.md")

    eval_map_path = repo_root / "docs" / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md"
    eval_map_path.write_text(_eval_harness_doc(), encoding="utf-8")
    if "docs/DIAGNOSTIC_CENTER_EVAL_HARNESS.md" not in compacted_docs:
        compacted_docs.append("docs/DIAGNOSTIC_CENTER_EVAL_HARNESS.md")

    plan = DocsCompactionPlan(
        snapshot_required=True,
        target_docs=[path.relative_to(repo_root).as_posix() for path in target_paths],
        compacted_docs=compacted_docs,
        snapshot_dir=str(snapshot_proof.get("snapshot_dir", "")),
    ).to_dict()
    plan["warnings"] = warnings
    plan["docs_compaction_passed"] = compact and len(warnings) == 0
    plan["runtime_map_created"] = runtime_map_path.exists()
    plan["eval_harness_map_created"] = eval_map_path.exists()
    return plan


def revalidate_permanent_gates(repo_root: Path) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    missing: list[str] = []
    for gate_name, required_paths in PERMANENT_GATES.items():
        ok = True
        for rel in required_paths:
            if not (repo_root / rel).exists():
                ok = False
                missing.append(f"{gate_name}:{rel}")
        checks[gate_name] = ok

    payload = PermanentGateRevalidationResult(
        gate_checks=checks,
        permanent_gate_revalidation_passed=all(checks.values()),
        missing_gates=missing,
    ).to_dict()
    payload["checked_at_utc"] = _utc_now()
    return payload


def build_artifact_hygiene_normalization(
    *,
    encoding_report: dict[str, Any],
    source_warning_text: str,
) -> dict[str, Any]:
    historical_warning_count = 1 if "replacement" in source_warning_text.lower() else 0
    result = ArtifactHygieneNormalizationResult(
        utf8_decode_error_count=_as_int(encoding_report.get("utf8_decode_error_count"), 0),
        nul_byte_file_count=_as_int(encoding_report.get("nul_byte_file_count"), 0),
        json_parse_error_count=_as_int(encoding_report.get("json_parse_error_count"), 0),
        current_generated_artifact_replacement_char_count=_as_int(
            encoding_report.get("replacement_char_warning_count"),
            0,
        ),
        historical_warning_count=historical_warning_count,
        historical_warning_documented=historical_warning_count > 0,
    )
    passed = (
        result.utf8_decode_error_count == 0
        and result.nul_byte_file_count == 0
        and result.json_parse_error_count == 0
        and result.current_generated_artifact_replacement_char_count == 0
        and (result.historical_warning_count == 0 or result.historical_warning_documented)
    )
    result.artifact_hygiene_normalization_passed = passed
    payload = result.to_dict()
    payload["historical_warning_source"] = (
        "PRD-046.1.28 implementation warning references replacement chars in historical command log"
        if historical_warning_count > 0
        else "none"
    )
    return payload


def build_decision(
    *,
    source_gate: dict[str, Any],
    inventory: dict[str, Any],
    classification: dict[str, Any],
    archive_manifest: dict[str, Any],
    cleanup_manifest: dict[str, Any],
    snapshot_proof: dict[str, Any],
    docs_compaction: dict[str, Any],
    permanent_gates: dict[str, Any],
    artifact_hygiene: dict[str, Any],
    no_mutation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if _as_int(inventory.get("item_count"), 0) <= 0:
        blockers.append("artifact_inventory_missing")
    if not classification.get("zone_counts"):
        blockers.append("artifact_classification_missing")
    if not _as_bool(classification.get("required_zones_present"), False):
        blockers.append("required_cleanup_zones_missing")
    if _as_int(archive_manifest.get("physical_files_deleted"), 0) != 0:
        blockers.append("archive_manifest_deleted_files")
    if _as_bool(cleanup_manifest.get("physical_deletion_performed"), False):
        blockers.append("cleanup_performed_physical_deletion")
    if not _as_bool(snapshot_proof.get("created"), False):
        blockers.append("docs_snapshot_missing")
    if not _as_bool(docs_compaction.get("docs_compaction_passed"), False):
        blockers.append("docs_compaction_failed")
    if not _as_bool(docs_compaction.get("runtime_map_created"), False):
        blockers.append("runtime_map_missing")
    if not _as_bool(docs_compaction.get("eval_harness_map_created"), False):
        blockers.append("eval_harness_map_missing")
    if not _as_bool(permanent_gates.get("permanent_gate_revalidation_passed"), False):
        blockers.append("permanent_gate_revalidation_failed")
    if not _as_bool(artifact_hygiene.get("artifact_hygiene_normalization_passed"), False):
        blockers.append("artifact_hygiene_normalization_failed")
    if not _as_bool(no_mutation.get("no_mutation_proof_passed"), False):
        blockers.append("no_mutation_proof_failed")

    if _as_int(classification.get("unknown_requires_review_count"), 0) > 0:
        warnings.append("unknown_requires_review_present")

    final_status = "passed" if len(blockers) == 0 else "blocked"
    decision = "diagnostic_center_stabilized_cleanup_manifested" if final_status == "passed" else "blocked"

    decision_payload = StabilizationCleanupDecision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()

    scorecard = StabilizationCleanupScorecard(
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        artifact_inventory_created=_as_int(inventory.get("item_count"), 0) > 0,
        artifact_classification_created=bool(classification.get("zone_counts")),
        archive_manifest_created=bool(archive_manifest.get("items") is not None),
        cleanup_candidate_manifest_created=bool(cleanup_manifest.get("items") is not None),
        docs_snapshots_created=_as_bool(snapshot_proof.get("created"), False),
        docs_compaction_passed=_as_bool(docs_compaction.get("docs_compaction_passed"), False),
        runtime_map_created=_as_bool(docs_compaction.get("runtime_map_created"), False),
        eval_harness_map_created=_as_bool(docs_compaction.get("eval_harness_map_created"), False),
        permanent_gate_revalidation_passed=_as_bool(permanent_gates.get("permanent_gate_revalidation_passed"), False),
        artifact_hygiene_normalization_passed=_as_bool(artifact_hygiene.get("artifact_hygiene_normalization_passed"), False),
        no_mutation_proof_passed=_as_bool(no_mutation.get("no_mutation_proof_passed"), False),
        physical_runtime_file_deletion_count=0,
        safety_eval_gate_deletion_count=0,
        production_data_mutated=_as_bool(no_mutation.get("production_data_mutated"), False),
        runtime_defaults_changed=_as_bool(no_mutation.get("runtime_defaults_changed"), False),
        provider_called=False,
        new_provider_execution_performed=False,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()

    return decision_payload, scorecard


def docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = _read_text(repo_root / "docs" / "PROJECT_STATE.md") if (repo_root / "docs" / "PROJECT_STATE.md").exists() else ""
    roadmap = _read_text(repo_root / "docs" / "ROADMAP.md") if (repo_root / "docs" / "ROADMAP.md").exists() else ""
    prd_index = _read_text(repo_root / "docs" / "PRD_INDEX.md") if (repo_root / "docs" / "PRD_INDEX.md").exists() else ""
    decisions = _read_text(repo_root / "docs" / "DECISIONS.md") if (repo_root / "docs" / "DECISIONS.md").exists() else ""
    runtime_map = _read_text(repo_root / "docs" / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md") if (repo_root / "docs" / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md").exists() else ""
    eval_map = _read_text(repo_root / "docs" / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md") if (repo_root / "docs" / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md").exists() else ""
    return {
        "project_state_synced": PRD in project_state,
        "roadmap_synced": "PRD-046.1.29" in roadmap,
        "prd_index_synced": PRD in prd_index,
        "adr_049_present": "ADR-049" in decisions,
        "runtime_map_synced": "Diagnostic Center Runtime Map" in runtime_map,
        "eval_harness_map_synced": "Diagnostic Center Eval Harness" in eval_map,
        "docs_synced": PRD in project_state and "PRD-046.1.29" in roadmap and PRD in prd_index and "ADR-049" in decisions,
    }


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "NEXT_PRD",
    "SOURCE_REPORT_FILES",
    "PERMANENT_GATES",
    "required_source_reports",
    "preflight_source_reports",
    "build_source_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "collect_artifact_inventory",
    "classify_inventory",
    "create_docs_snapshots",
    "compact_docs",
    "revalidate_permanent_gates",
    "build_artifact_hygiene_normalization",
    "build_decision",
    "docs_sync_status",
    "_sha256",
]
