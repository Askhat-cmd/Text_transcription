from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
DEFAULT_REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_stabilization as stabilization
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.15"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_dir = Path(args.source_dir).resolve()
    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))

    transfer_brief_path = reports_dir / "PRD-046.1.15_TRANSFER_BRIEF_TO_NEW_CHAT.md"

    tracked, hash_before = stabilization.tracked_hashes(repo_root)
    preflight = stabilization.preflight(source_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        source_gate = {
            "source_prd": "PRD-046.1.14",
            "source_final_status": "blocked",
            "source_decision": "blocked",
            "quality_gate_passed": False,
            "rollback_gate_passed": False,
            "normal_user_gate_passed": False,
            "trace_sanitization_gate_passed": False,
            "risk_register_has_blockers": True,
            "new_execution_performed": True,
            "provider_called_by_results_gate": False,
            "production_mutation_detected": True,
            "source_gate_passed": False,
            "blockers": blockers,
        }
        module_inventory = {
            "schema_version": "diagnostic_center_module_inventory_v1",
            "prd": PRD,
            "items": [],
            "inventory_count": 0,
        }
        classification = {
            "schema_version": "diagnostic_center_module_classification_v1",
            "prd": PRD,
            "category_counts": {},
            "required_categories_present": False,
        }
        gate_catalog = {
            "schema_version": "diagnostic_center_regression_gate_catalog_v1",
            "permanent_gates": [],
            "minimum_required_gate_count": 12,
            "all_required_gates_present": False,
        }
        cleanup_plan = {
            "cleanup_mode": "non_destructive_manifest_first",
            "physical_deletion_performed": False,
            "runtime_files_deleted": False,
            "regression_gates_deleted": False,
            "kb_registry_chroma_config_mutated": False,
            "archive_candidates_count": 0,
            "requires_future_cleanup_prd": True,
            "future_cleanup_prd_recommended": "PRD-046.1.16 or later",
        }
        archive_manifest = {
            "archive_mode": "manifest_only",
            "physical_files_moved": 0,
            "physical_files_deleted": 0,
            "items": [],
        }
        scorecard = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "blocked",
            "source_gate_passed": False,
            "module_inventory_ready": False,
            "module_classification_ready": False,
            "regression_gate_catalog_ready": False,
            "all_required_regression_gates_present": False,
            "cleanup_plan_ready": False,
            "archive_manifest_ready": False,
            "transfer_brief_ready": False,
            "new_execution_performed": False,
            "provider_called": False,
            "runtime_defaults_changed": False,
            "kb_registry_chroma_config_mutated": False,
            "runtime_files_deleted": False,
            "regression_gates_deleted": False,
            "physical_files_deleted": 0,
            "artifact_encoding_hygiene_passed": False,
            "recommended_next_step": "move_to_new_chat_with_transfer_brief",
            "recommended_next_prd": "PRD-046.1.16 - Diagnostic Center v1 Final Acceptance / Runtime Governance Closure v1",
            "blockers": blockers,
            "warnings": [],
        }
        decision_payload = {
            "schema_version": "diagnostic_center_stabilization_decision_v1",
            "prd": PRD,
            "final_status": "blocked",
            "decision": "blocked",
            "blockers": blockers,
            "warnings": [],
            "recommended_next_step": "move_to_new_chat_with_transfer_brief",
        }
        run_payload = {
            "schema_version": "diagnostic_center_stabilization_v1",
            "prd": PRD,
            "source_prd": "PRD-046.1.14",
            "source_decision": "blocked",
            "mode": "stabilization_cleanup_consolidation",
            "new_execution_performed": False,
            "provider_called": False,
            "runtime_defaults_changed": False,
            "module_inventory": {"inventory_count": 0},
            "classification_summary": classification,
            "regression_gate_catalog": {
                "minimum_required_gate_count": 12,
                "all_required_regression_gates_present": False,
                "gate_count": 0,
            },
            "cleanup_plan": cleanup_plan,
            "archive_manifest": {
                "archive_mode": "manifest_only",
                "physical_files_moved": 0,
                "physical_files_deleted": 0,
                "items_count": 0,
            },
            "transfer_brief": {
                "path": transfer_brief_path.as_posix(),
                "ready": False,
                "required_sections_present": False,
            },
            "decision": "blocked",
        }
        transfer_brief_md = ""
    else:
        (
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
        ) = stabilization.execute_stabilization(
            parsed=preflight["parsed"],
            repo_root=repo_root,
            strict=strict,
            transfer_brief_path=transfer_brief_path,
        )

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = stabilization.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    kb_registry_chroma_config_mutated = any(
        bool(no_mutation.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )
    scorecard["kb_registry_chroma_config_mutated"] = kb_registry_chroma_config_mutated
    if kb_registry_chroma_config_mutated:
        scorecard["final_status"] = "blocked"
        scorecard["decision"] = "blocked"
        scorecard.setdefault("blockers", []).append("production_state_mutated")

    _write_json(out_dir / "stabilization_source_gate.json", source_gate)
    _write_json(out_dir / "diagnostic_center_module_inventory.json", module_inventory)
    _write_json(out_dir / "diagnostic_center_module_classification.json", classification)
    _write_json(out_dir / "diagnostic_center_regression_gate_catalog.json", gate_catalog)
    _write_json(out_dir / "diagnostic_center_cleanup_plan.json", cleanup_plan)
    _write_json(out_dir / "diagnostic_center_archive_manifest.json", archive_manifest)
    _write_json(out_dir / "diagnostic_center_stabilization_scorecard.json", scorecard)
    _write_json(out_dir / "diagnostic_center_stabilization_run.json", run_payload)
    _write_json(out_dir / "diagnostic_center_stabilization_decision.json", decision_payload)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    if transfer_brief_md:
        transfer_brief_path.parent.mkdir(parents=True, exist_ok=True)
        transfer_brief_path.write_text(transfer_brief_md, encoding="utf-8")

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(out_dir),
            reports_dir=str(reports_dir),
            out_dir=str(out_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )

    scorecard["artifact_encoding_hygiene_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    if not scorecard["artifact_encoding_hygiene_passed"]:
        scorecard["final_status"] = "blocked"
        scorecard["decision"] = "blocked"
        scorecard.setdefault("blockers", []).append("artifact_encoding_hygiene_failed")

    _write_json(out_dir / "diagnostic_center_stabilization_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.15 diagnostic center stabilization cleanup gate.")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.14")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.15")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
