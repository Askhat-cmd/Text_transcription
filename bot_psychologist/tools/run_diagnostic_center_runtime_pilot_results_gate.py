from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_runtime_pilot_results_gate as results_gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.21"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = results_gate.tracked_hashes(repo_root)
    preflight = results_gate.preflight_source(source_dir, reports_dir)
    hash_after = {name: results_gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    no_mutation_proof = results_gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    no_mutation_proof["production_mutation_detected"] = any(
        bool(no_mutation_proof.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )

    if preflight["ok"]:
        run_payload = results_gate.execute_results_gate(parsed=preflight["parsed"], no_mutation_proof=no_mutation_proof)
    else:
        run_payload = {
            "schema_version": "diagnostic_center_runtime_pilot_results_gate_run_v1",
            "prd": PRD,
            "source_gate": {
                "schema_version": "diagnostic_center_runtime_pilot_results_source_gate_v1",
                "prd": PRD,
                "source_prd": "PRD-046.1.20",
                "source_final_status": "failed",
                "source_decision": "blocked_runtime_pilot_execution",
                "source_gate_passed": False,
                "reports_and_logs_present": False,
            },
            "execution_evidence_review": {"execution_evidence_status": "failed"},
            "rollback_evidence_review": {"rollback_evidence_status": "failed"},
            "normal_user_no_effect_review": {"normal_user_no_effect_status": "failed"},
            "quality_delta_review": {"quality_gate_decision": "failed"},
            "safety_kb_boundary_review": {"safety_kb_boundary_status": "failed"},
            "trace_sanitization_review": {"trace_sanitization_status": "failed"},
            "artifact_hygiene_review": {"artifact_hygiene_status": "failed"},
            "encoding_warning_review": {"encoding_warning_status": "absent"},
            "no_mutation_review": {"no_mutation_status": "passed", "production_mutation_detected": False},
            "runtime_pilot_results_risk_register": {
                "schema_version": "diagnostic_center_runtime_pilot_results_risk_register_v1",
                "prd": PRD,
                "risks": results_gate.build_default_risk_register(),
                "risk_count": 5,
            },
            "runtime_pilot_results_decision_gate": {
                "schema_version": "diagnostic_center_runtime_pilot_results_decision_gate_v1",
                "prd": PRD,
                "final_status": "failed",
                "decision": "fix_required",
                "source_gate_passed": False,
                "execution_evidence_status": "failed",
                "rollback_evidence_status": "failed",
                "normal_user_no_effect_status": "failed",
                "quality_gate_decision": "failed",
                "safety_kb_boundary_status": "failed",
                "trace_sanitization_status": "failed",
                "artifact_hygiene_status": "failed",
                "encoding_warning_status": "absent",
                "no_mutation_status": "passed",
                "hard_stop_triggered": False,
                "new_execution_performed": False,
                "provider_called_by_results_gate": False,
                "broad_rollout_allowed": False,
                "production_ready": False,
                "future_execution_requires_new_prd": True,
                "recommended_next_prd": "PRD-046.1.21-HF1 - Runtime Pilot Results Gate Hotfix v1",
                "risk_count": 5,
                "blockers": list(preflight["missing"]) + list(preflight["parse_errors"]),
                "warnings": [],
            },
            "runtime_pilot_results_scorecard": {
                "schema_version": "diagnostic_center_runtime_pilot_results_scorecard_v1",
                "prd": PRD,
                "final_status": "failed",
                "decision": "fix_required",
                "source_gate_passed": False,
                "execution_evidence_status": "failed",
                "rollback_evidence_status": "failed",
                "normal_user_no_effect_status": "failed",
                "quality_gate_decision": "failed",
                "safety_kb_boundary_status": "failed",
                "trace_sanitization_status": "failed",
                "artifact_hygiene_status": "failed",
                "encoding_warning_status": "absent",
                "no_mutation_status": "passed",
                "hard_stop_triggered": False,
                "broad_rollout_allowed": False,
                "production_ready": False,
                "future_execution_requires_new_prd": True,
                "recommended_next_prd": "PRD-046.1.21-HF1 - Runtime Pilot Results Gate Hotfix v1",
            },
            "source_status": {
                "source_prd": "PRD-046.1.20",
                "source_final_status": "failed",
                "source_decision": "blocked_runtime_pilot_execution",
                "source_gate_passed": False,
            },
            "decision_payload": {
                "schema_version": "diagnostic_center_runtime_pilot_results_gate_decision_v1",
                "prd": PRD,
                "final_status": "failed",
                "decision": "fix_required",
                "blockers": list(preflight["missing"]) + list(preflight["parse_errors"]),
                "warnings": [],
                "recommended_next_prd": "PRD-046.1.21-HF1 - Runtime Pilot Results Gate Hotfix v1",
            },
        }

    _write_json(out_dir / "source_gate.json", run_payload["source_gate"])
    _write_json(out_dir / "execution_evidence_review.json", run_payload["execution_evidence_review"])
    _write_json(out_dir / "rollback_evidence_review.json", run_payload["rollback_evidence_review"])
    _write_json(out_dir / "normal_user_no_effect_review.json", run_payload["normal_user_no_effect_review"])
    _write_json(out_dir / "quality_delta_review.json", run_payload["quality_delta_review"])
    _write_json(out_dir / "safety_kb_boundary_review.json", run_payload["safety_kb_boundary_review"])
    _write_json(out_dir / "trace_sanitization_review.json", run_payload["trace_sanitization_review"])
    _write_json(out_dir / "artifact_hygiene_review.json", run_payload["artifact_hygiene_review"])
    _write_json(out_dir / "encoding_warning_review.json", run_payload["encoding_warning_review"])
    _write_json(out_dir / "no_mutation_review.json", run_payload["no_mutation_review"])
    _write_json(out_dir / "runtime_pilot_results_risk_register.json", run_payload["runtime_pilot_results_risk_register"])
    _write_json(out_dir / "runtime_pilot_results_decision_gate.json", run_payload["runtime_pilot_results_decision_gate"])
    _write_json(out_dir / "runtime_pilot_results_scorecard.json", run_payload["runtime_pilot_results_scorecard"])
    _write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.21 runner executed.\n", encoding="utf-8")

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

    decision_gate = dict(run_payload["runtime_pilot_results_decision_gate"])
    decision_gate["current_artifact_encoding_hygiene_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    _write_json(out_dir / "runtime_pilot_results_decision_gate.json", decision_gate)

    return {
        "status": str(decision_gate.get("final_status", "failed")),
        "decision": str(decision_gate.get("decision", "fix_required")),
        "decision_gate": decision_gate,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.21 runtime pilot results/rollback/quality gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.20")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.21")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
