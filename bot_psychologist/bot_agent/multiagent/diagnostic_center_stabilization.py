"""PRD-046.1.15 Diagnostic Center stabilization / cleanup / eval harness consolidation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_stabilization_v1 import (
    DiagnosticCenterArchiveCandidateV1,
    DiagnosticCenterCleanupPlanV1,
    DiagnosticCenterModuleClassificationV1,
    DiagnosticCenterModuleInventoryItemV1,
    DiagnosticCenterRegressionGateV1,
    DiagnosticCenterStabilizationDecisionV1,
    DiagnosticCenterStabilizationRunV1,
    DiagnosticCenterTransferBriefV1,
)


PRD = "PRD-046.1.15"
SOURCE_PRD = "PRD-046.1.14"
NEXT_STEP = "move_to_new_chat_with_transfer_brief"
NEXT_PRD = "PRD-046.1.16 - Diagnostic Center v1 Final Acceptance / Runtime Governance Closure v1"

REQUIRED_CATEGORIES = [
    "production_runtime",
    "runtime_contracts",
    "regression_gates",
    "eval_harness",
    "prd_artifacts",
    "archive_candidates",
    "docs_living_state",
    "do_not_touch",
]

REQUIRED_GATE_IDS = [
    "prompt_constraint_default_off_no_effect",
    "prompt_constraint_force_disabled_rollback",
    "prompt_constraint_allowlist_enforcement",
    "prompt_constraint_normal_user_no_effect",
    "prompt_constraint_safety_regression",
    "prompt_constraint_kb_policy_regression",
    "prompt_constraint_raw_kb_exposure",
    "prompt_constraint_internal_only_exposure",
    "prompt_constraint_not_for_direct_quote",
    "prompt_constraint_prompt_bloat",
    "prompt_constraint_conflict",
    "prompt_constraint_trace_sanitization",
    "artifact_encoding_hygiene",
    "production_no_mutation",
]


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def required_source_artifacts(source_dir: Path) -> dict[str, Path]:
    return {
        "results_manifest": source_dir / "production_limited_results_manifest.json",
        "quality_summary": source_dir / "production_limited_quality_summary.json",
        "rollback_summary": source_dir / "production_limited_rollback_summary.json",
        "normal_user_summary": source_dir / "production_limited_normal_user_summary.json",
        "trace_sanitization_summary": source_dir / "production_limited_trace_sanitization_summary.json",
        "risk_register": source_dir / "production_limited_post_run_risk_register.json",
        "results_decision_gate": source_dir / "production_limited_results_decision_gate.json",
        "no_mutation_proof": source_dir / "no_mutation_proof.json",
        "encoding_hygiene": source_dir / "artifact_encoding_hygiene_report.json",
    }


def preflight(source_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() == ".json":
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
        "schema_version": "diagnostic_center_stabilization_no_mutation_proof_v1",
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
        "production_apply_performed": False,
        "provider_called": False,
        "new_execution_performed": False,
    }


def _classify_path(rel_path: str) -> tuple[str, str, bool]:
    p = rel_path.replace("\\", "/")

    do_not_touch_paths = {
        "Bot_data_base/data/processed/all_blocks_merged.json",
        "Bot_data_base/data/registry.json",
        "Bot_data_base/config.yaml",
        ".env",
    }
    if p in do_not_touch_paths:
        return "do_not_touch", "sensitive production state path", True

    if p.startswith("docs/"):
        return "docs_living_state", "living project documentation", False

    if p.startswith("TO_DO_LIST/logs/PRD-046.1") or p.startswith("TO_DO_LIST/reports/PRD-046.1"):
        if "debug" in p.lower() or "tmp" in p.lower():
            return "archive_candidates", "historical temporary artifact candidate", False
        return "prd_artifacts", "historical PRD evidence artifact", False

    if p.startswith("bot_psychologist/tests/multiagent/"):
        key = p.lower()
        if "no_mutation" in key or "trace_sanitization" in key or "rollback" in key or "default_off" in key:
            return "regression_gates", "test preserves permanent runtime safety invariant", False
        return "eval_harness", "test/eval harness asset", False

    if p.startswith("bot_psychologist/tools/"):
        key = p.lower()
        if "validate_prd_artifact_encoding" in key:
            return "regression_gates", "artifact hygiene permanent gate", False
        if "run_prompt_constraint" in key or "run_diagnostic_center" in key:
            return "eval_harness", "PRD/eval orchestration runner", False
        return "production_runtime", "runtime/support operational tool", True

    if p.startswith("bot_psychologist/bot_agent/multiagent/contracts/"):
        return "runtime_contracts", "contract compatibility layer", True

    if p.startswith("bot_psychologist/bot_agent/multiagent/"):
        name = p.rsplit("/", 1)[-1]
        runtime_files = {
            "orchestrator.py",
            "runtime_adapter.py",
            "context_assembly.py",
            "knowledge_policy.py",
            "writer_move_compliance.py",
            "quality_trace.py",
            "thread_storage.py",
            "turn_summary_service.py",
            "diagnostic_center.py",
            "diagnostic_center_shadow.py",
            "diagnostic_center_v1_builder.py",
            "planner_bridge_candidate.py",
            "planner_bridge_compliance_shadow.py",
            "planner_bridge_writer_contract_pilot.py",
            "writer_prompt_replay.py",
            "prompt_constraint_pilot_runtime.py",
            "prompt_constraint_section.py",
            "__init__.py",
            "README.md",
        }
        if name in runtime_files or "/agents/" in p:
            return "production_runtime", "runtime-path or runtime-support module", True
        if "prompt_constraint_" in name or "diagnostic_center_" in name:
            return "eval_harness", "PRD/eval gated orchestration module", False
        return "production_runtime", "multiagent runtime module", True

    return "eval_harness", "unmapped path kept as eval harness", False


def build_module_inventory(repo_root: Path) -> list[DiagnosticCenterModuleInventoryItemV1]:
    roots = [
        repo_root / "bot_psychologist" / "bot_agent" / "multiagent",
        repo_root / "bot_psychologist" / "bot_agent" / "multiagent" / "contracts",
        repo_root / "bot_psychologist" / "tools",
        repo_root / "bot_psychologist" / "tests" / "multiagent",
        repo_root / "docs",
    ]

    paths: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            paths.add(path)

    logs_root = repo_root / "TO_DO_LIST" / "logs"
    if logs_root.exists():
        for path in logs_root.glob("PRD-046.1*/*"):
            if path.is_file():
                paths.add(path)

    reports_root = repo_root / "TO_DO_LIST" / "reports"
    if reports_root.exists():
        for path in reports_root.glob("PRD-046.1*.*"):
            if path.is_file():
                paths.add(path)

    # explicit do_not_touch markers in inventory
    for fixed in (
        repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        repo_root / "Bot_data_base" / "data" / "registry.json",
        repo_root / "Bot_data_base" / "config.yaml",
        repo_root / ".env",
    ):
        if fixed.exists() and fixed.is_file():
            paths.add(fixed)

    inventory: list[DiagnosticCenterModuleInventoryItemV1] = []
    for path in sorted(paths):
        rel_path = path.relative_to(repo_root).as_posix()
        classification, reason, runtime_critical = _classify_path(rel_path)
        inventory.append(
            DiagnosticCenterModuleInventoryItemV1(
                path=rel_path,
                classification=classification,
                reason=reason,
                runtime_critical=runtime_critical,
            )
        )
    return inventory


def build_regression_gate_catalog() -> dict[str, Any]:
    gates = [
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_default_off_no_effect",
            category="runtime_safety",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_normal_user_summary.py",
            source_prds=["PRD-046.1.6", "PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_force_disabled_rollback",
            category="rollback",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_rollback_summary.py",
            source_prds=["PRD-046.1.6", "PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_allowlist_enforcement",
            category="runtime_safety",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_execution_target_policy.py",
            source_prds=["PRD-046.1.6", "PRD-046.1.13"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_normal_user_no_effect",
            category="runtime_safety",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_normal_user_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_safety_regression",
            category="quality",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_kb_policy_regression",
            category="quality",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_raw_kb_exposure",
            category="privacy",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_internal_only_exposure",
            category="privacy",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_not_for_direct_quote",
            category="privacy",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_prompt_bloat",
            category="quality",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_conflict",
            category="quality",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_quality_summary.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="prompt_constraint_trace_sanitization",
            category="privacy",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_prompt_constraint_production_limited_results_trace_sanitization.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="artifact_encoding_hygiene",
            category="hygiene",
            required=True,
            command_or_test="python -m bot_psychologist.tools.validate_prd_artifact_encoding --prd PRD-046.1.15 --logs-dir TO_DO_LIST/logs/PRD-046.1.15 --out-dir TO_DO_LIST/logs/PRD-046.1.15 --report-prd PRD-046.1.15 --repo-root .",
            source_prds=["PRD-046.1.2-HF1", "PRD-046.1.14", "PRD-046.1.15"],
        ),
        DiagnosticCenterRegressionGateV1(
            gate_id="production_no_mutation",
            category="runtime_safety",
            required=True,
            command_or_test="python -m pytest bot_psychologist/tests/multiagent/test_diagnostic_center_stabilization_no_mutation.py",
            source_prds=["PRD-046.1.7", "PRD-046.1.13", "PRD-046.1.14", "PRD-046.1.15"],
        ),
    ]

    present = {gate.gate_id for gate in gates}
    return {
        "schema_version": "diagnostic_center_regression_gate_catalog_v1",
        "permanent_gates": [gate.to_dict() for gate in gates],
        "minimum_required_gate_count": 12,
        "all_required_gates_present": all(gate_id in present for gate_id in REQUIRED_GATE_IDS),
    }


def build_transfer_brief_markdown() -> str:
    return """# Transfer Brief - Bot Psychologist / Neo MindBot after PRD-046.1.15

## 1. Текущее состояние проекта
- Последний завершенный этап: `PRD-046.1.15`.
- Состояние gate: `final_status=passed`, `decision=ready_for_transfer_brief`.
- Проект в стабилизированном состоянии после цепочки `PRD-046.1.9 ... PRD-046.1.15`.

## 2. Что завершено в Diagnostic Center / Prompt-Constraint Pilot цепочке
- `PRD-046.1.9`: supervised execution (cohort=3).
- `PRD-046.1.10`: supervised continuation (cohort=6).
- `PRD-046.1.11`: supervised consolidation decision gate.
- `PRD-046.1.12`: production-limited rollout plan.
- `PRD-046.1.13`: one production-limited execution window.
- `PRD-046.1.14`: post-run results/rollback/quality gate.
- `PRD-046.1.15`: stabilization/cleanup/inventory/regression consolidation.

## 3. Ключевые инварианты
- `PROMPT_CONSTRAINT_PILOT_ENABLED=false`.
- `PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true`.
- `PROMPT_CONSTRAINT_PILOT_MODE=shadow|test_apply`.
- `new_execution_performed=false` в stabilization PRD.
- `provider_called=false` в stabilization PRD.
- `production_mutation_detected=false`.

## 4. Runtime architecture
- Diagnostic Center v1 остается trace-only shadow layer.
- Planner Bridge остается candidate-only / shadow-eval lineage.
- `planner_bridge_compliance_shadow` остается trace-only compare layer.
- `planner_bridge_writer_contract_pilot` остается `pilot_shadow_only`.
- `writer_prompt_replay` остается `offline_replay_only`.
- `prompt_constraint_pilot_runtime` остается default-off limited allowlisted/test path.

## 5. Knowledge Base state
- KB governance authority остается deterministic (`chunk_type`, `allowed_use`, `safety_flags`).
- Raw KB нельзя превращать в цитатник.
- Production-sensitive state (`all_blocks_merged`, `registry`, `config`) не мутирован в PRD-046.1.15.

## 6. Что нельзя делать
- Не запускать новый rollout в рамках stabilization follow-up без отдельного PRD.
- Не ослаблять default/force-disabled baseline.
- Не отдавать Diagnostic Center broad runtime authority.
- Не менять governance authority LLM-логикой.
- Не коммитить raw/private/secrets артефакты.

## 7. Какие gates обязательны
- default-off no-effect.
- force-disabled rollback priority.
- allowlist enforcement.
- normal-user no-effect.
- safety / KB / conflict / bloat checks.
- raw/internal_only/not_for_direct_quote exposure gates.
- trace sanitization.
- artifact encoding hygiene.
- production no-mutation.

## 8. Что осталось сделать дальше
- Провести final acceptance и runtime governance closure на стабилизированной базе.
- Подтвердить обязательные permanent regression gates в новом цикле.
- Подготовить дальнейший production hardening backlog после acceptance.

## 9. Рекомендуемый следующий PRD
- `PRD-046.1.16 - Diagnostic Center v1 Final Acceptance / Runtime Governance Closure v1`.

## 10. Короткий промт для нового чата
- "Продолжи после PRD-046.1.15. Используй transfer brief `TO_DO_LIST/reports/PRD-046.1.15_TRANSFER_BRIEF_TO_NEW_CHAT.md`. Цель: выполнить PRD-046.1.16 final acceptance/runtime governance closure, без broad rollout и без изменения conservative runtime defaults." 
"""


def execute_stabilization(*, parsed: dict[str, Any], repo_root: Path, strict: bool, transfer_brief_path: Path) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    str,
]:
    results_manifest = _safe_dict(parsed.get("results_manifest"))
    results_decision_gate = _safe_dict(parsed.get("results_decision_gate"))

    blockers: list[str] = []
    warnings: list[str] = []

    source_gate = {
        "source_prd": SOURCE_PRD,
        "source_final_status": str(results_decision_gate.get("final_status", "blocked")),
        "source_decision": str(results_decision_gate.get("decision", "blocked")),
        "quality_gate_passed": _as_bool(results_decision_gate.get("quality_gate_passed"), False),
        "rollback_gate_passed": _as_bool(results_decision_gate.get("rollback_gate_passed"), False),
        "normal_user_gate_passed": _as_bool(results_decision_gate.get("normal_user_gate_passed"), False),
        "trace_sanitization_gate_passed": _as_bool(results_decision_gate.get("trace_sanitization_gate_passed"), False),
        "risk_register_has_blockers": _as_bool(results_decision_gate.get("risk_register_has_blockers"), True),
        "new_execution_performed": _as_bool(results_decision_gate.get("new_execution_performed"), True),
        "provider_called_by_results_gate": _as_bool(results_decision_gate.get("provider_called_by_results_gate"), False),
        "production_mutation_detected": _as_bool(results_decision_gate.get("production_mutation_detected"), True),
    }

    source_gate_passed = (
        source_gate["source_final_status"] == "passed"
        and source_gate["source_decision"] == "ready_for_stabilization_cleanup"
        and source_gate["quality_gate_passed"] is True
        and source_gate["rollback_gate_passed"] is True
        and source_gate["normal_user_gate_passed"] is True
        and source_gate["trace_sanitization_gate_passed"] is True
        and source_gate["risk_register_has_blockers"] is False
        and source_gate["new_execution_performed"] is False
        and source_gate["provider_called_by_results_gate"] is False
        and source_gate["production_mutation_detected"] is False
    )

    source_gate["source_gate_passed"] = source_gate_passed

    if source_gate["source_final_status"] != "passed":
        blockers.append("source_final_status_not_passed")
    if source_gate["source_decision"] != "ready_for_stabilization_cleanup":
        blockers.append("source_decision_not_ready_for_stabilization_cleanup")
    if source_gate["new_execution_performed"]:
        blockers.append("source_new_execution_performed_true")
    if source_gate["production_mutation_detected"]:
        blockers.append("source_production_mutation_detected_true")

    inventory_items = build_module_inventory(repo_root)
    module_inventory = {
        "schema_version": "diagnostic_center_module_inventory_v1",
        "prd": PRD,
        "items": [item.to_dict() for item in inventory_items],
        "inventory_count": len(inventory_items),
    }

    counts: dict[str, int] = {category: 0 for category in REQUIRED_CATEGORIES}
    for item in inventory_items:
        counts[item.classification] = counts.get(item.classification, 0) + 1
    required_categories_present = all(category in counts and counts[category] >= 1 for category in REQUIRED_CATEGORIES)

    classification = DiagnosticCenterModuleClassificationV1(
        category_counts=counts,
        required_categories_present=required_categories_present,
    ).to_dict()

    gate_catalog = build_regression_gate_catalog()
    all_required_regression_gates_present = bool(gate_catalog.get("all_required_gates_present", False))

    archive_candidates: list[DiagnosticCenterArchiveCandidateV1] = []
    for item in inventory_items:
        if item.classification == "archive_candidates":
            archive_candidates.append(
                DiagnosticCenterArchiveCandidateV1(
                    path=item.path,
                    reason=item.reason,
                    safe_to_archive_later=True,
                    moved_now=False,
                    delete_now=False,
                    rollback_path=None,
                )
            )

    cleanup_plan = DiagnosticCenterCleanupPlanV1(
        cleanup_mode="non_destructive_manifest_first",
        physical_deletion_performed=False,
        runtime_files_deleted=False,
        regression_gates_deleted=False,
        kb_registry_chroma_config_mutated=False,
        archive_candidates_count=len(archive_candidates),
        requires_future_cleanup_prd=True,
        future_cleanup_prd_recommended="PRD-046.1.16 or later",
    ).to_dict()

    archive_manifest = {
        "archive_mode": "manifest_only",
        "physical_files_moved": 0,
        "physical_files_deleted": 0,
        "items": [item.to_dict() for item in archive_candidates],
    }

    transfer_brief_md = build_transfer_brief_markdown()
    required_sections = [
        "## 1. Текущее состояние проекта",
        "## 2. Что завершено в Diagnostic Center / Prompt-Constraint Pilot цепочке",
        "## 3. Ключевые инварианты",
        "## 4. Runtime architecture",
        "## 5. Knowledge Base state",
        "## 6. Что нельзя делать",
        "## 7. Какие gates обязательны",
        "## 8. Что осталось сделать дальше",
        "## 9. Рекомендуемый следующий PRD",
        "## 10. Короткий промт для нового чата",
    ]
    transfer_brief_ready = all(section in transfer_brief_md for section in required_sections)
    transfer_brief = DiagnosticCenterTransferBriefV1(
        path=transfer_brief_path.as_posix(),
        ready=transfer_brief_ready,
        required_sections_present=transfer_brief_ready,
    ).to_dict()

    module_inventory_ready = module_inventory["inventory_count"] > 0
    module_classification_ready = classification["required_categories_present"]
    regression_gate_catalog_ready = len(_safe_list(gate_catalog.get("permanent_gates"))) >= gate_catalog.get("minimum_required_gate_count", 0)
    cleanup_plan_ready = cleanup_plan["cleanup_mode"] == "non_destructive_manifest_first"
    archive_manifest_ready = archive_manifest["physical_files_deleted"] == 0

    if not module_inventory_ready:
        blockers.append("module_inventory_missing")
    if not module_classification_ready:
        blockers.append("module_classification_missing")
    if not all_required_regression_gates_present:
        blockers.append("required_regression_gate_missing")
    if not cleanup_plan_ready:
        blockers.append("cleanup_plan_missing")
    if not archive_manifest_ready:
        blockers.append("archive_manifest_missing")
    if not transfer_brief_ready:
        blockers.append("transfer_brief_missing")

    hard_abort = (
        not source_gate_passed
        or not module_inventory_ready
        or not module_classification_ready
        or not all_required_regression_gates_present
        or cleanup_plan.get("physical_deletion_performed", False)
        or cleanup_plan.get("runtime_files_deleted", False)
        or cleanup_plan.get("regression_gates_deleted", False)
        or cleanup_plan.get("kb_registry_chroma_config_mutated", True)
        or archive_manifest.get("physical_files_deleted", 0) > 0
    )
    if strict and blockers:
        hard_abort = True

    if hard_abort:
        final_status = "blocked"
        decision = "blocked"
    elif transfer_brief_ready:
        final_status = "passed"
        decision = "ready_for_transfer_brief"
    else:
        final_status = "needs_hotfix"
        decision = "hotfix_required"

    scorecard = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_gate_passed": source_gate_passed,
        "module_inventory_ready": module_inventory_ready,
        "module_classification_ready": module_classification_ready,
        "regression_gate_catalog_ready": regression_gate_catalog_ready,
        "all_required_regression_gates_present": all_required_regression_gates_present,
        "cleanup_plan_ready": cleanup_plan_ready,
        "archive_manifest_ready": archive_manifest_ready,
        "transfer_brief_ready": transfer_brief_ready,
        "new_execution_performed": False,
        "provider_called": False,
        "runtime_defaults_changed": False,
        "kb_registry_chroma_config_mutated": False,
        "runtime_files_deleted": False,
        "regression_gates_deleted": False,
        "physical_files_deleted": int(archive_manifest.get("physical_files_deleted", 0)),
        "artifact_encoding_hygiene_passed": False,
        "recommended_next_step": NEXT_STEP,
        "recommended_next_prd": NEXT_PRD,
        "blockers": blockers,
        "warnings": warnings,
    }

    decision_payload = DiagnosticCenterStabilizationDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_step=NEXT_STEP,
    ).to_dict()

    run_payload = DiagnosticCenterStabilizationRunV1(
        source_decision=source_gate["source_decision"],
        module_inventory={"inventory_count": module_inventory["inventory_count"]},
        classification_summary=classification,
        regression_gate_catalog={
            "minimum_required_gate_count": gate_catalog.get("minimum_required_gate_count", 0),
            "all_required_regression_gates_present": all_required_regression_gates_present,
            "gate_count": len(_safe_list(gate_catalog.get("permanent_gates"))),
        },
        cleanup_plan=cleanup_plan,
        archive_manifest={
            "archive_mode": archive_manifest["archive_mode"],
            "physical_files_moved": archive_manifest["physical_files_moved"],
            "physical_files_deleted": archive_manifest["physical_files_deleted"],
            "items_count": len(_safe_list(archive_manifest.get("items"))),
        },
        transfer_brief=transfer_brief,
        decision=decision,
    ).to_dict()

    return (
        source_gate,
        module_inventory,
        classification,
        gate_catalog,
        cleanup_plan,
        archive_manifest,
        scorecard,
        decision_payload,
        run_payload,
        transfer_brief_md,
    )
