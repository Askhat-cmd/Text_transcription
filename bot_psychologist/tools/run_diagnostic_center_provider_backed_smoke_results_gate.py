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

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.24"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fallback_payload(preflight: dict[str, Any], docs_synced: bool) -> dict[str, Any]:
    blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
    decision = "fix_required"
    return {
        "schema_version": "diagnostic_center_provider_backed_smoke_results_gate_run_v1",
        "prd": PRD,
        "source_gate": {
            "schema_version": "provider_backed_smoke_results_source_gate_v1",
            "prd": PRD,
            "source_prd": "PRD-046.1.23",
            "source_final_status": "failed",
            "source_decision": "provider_backed_limited_smoke_execution_failed",
            "source_gate_passed": False,
            "reports_and_logs_present": False,
        },
        "provider_execution_evidence_review": {"provider_execution_evidence_status": "failed"},
        "provider_budget_review": {"provider_budget_status": "failed"},
        "normal_user_no_effect_review": {"normal_user_no_effect_status": "failed"},
        "quality_consolidation_review": {"quality_consolidation_status": "failed"},
        "safety_kb_boundary_consolidation": {"safety_kb_boundary_consolidation_status": "failed"},
        "provider_output_sanitization_consolidation": {"provider_output_sanitization_consolidation_status": "failed"},
        "trace_sanitization_consolidation": {"trace_sanitization_consolidation_status": "failed"},
        "rollback_evidence_review": {"rollback_evidence_status": "failed"},
        "botdb_stability_review": {"botdb_stability_status": "failed"},
        "hard_stop_absence_review": {"hard_stop_absence_status": "failed"},
        "no_mutation_review": {"no_mutation_status": "passed", "production_mutation_detected": False},
        "risk_register": gate.build_risk_register(),
        "decision_gate": {
            "schema_version": "provider_backed_smoke_results_decision_gate_v1",
            "prd": PRD,
            "final_status": "failed",
            "decision": decision,
            "source_gate_passed": False,
            "provider_execution_evidence_status": "failed",
            "provider_budget_status": "failed",
            "normal_user_no_effect_status": "failed",
            "quality_consolidation_status": "failed",
            "safety_kb_boundary_consolidation_status": "failed",
            "provider_output_sanitization_consolidation_status": "failed",
            "trace_sanitization_consolidation_status": "failed",
            "rollback_evidence_status": "failed",
            "botdb_stability_status": "failed",
            "hard_stop_absence_status": "failed",
            "no_mutation_status": "passed",
            "risk_register_has_blockers": False,
            "new_execution_performed": False,
            "provider_called_by_prd_046_1_24": False,
            "broad_rollout_allowed": False,
            "production_ready": False,
            "future_expansion_requires_new_prd": True,
            "recommended_next_prd": gate.NEXT_PRD_FIX,
            "blockers": blockers,
            "warnings": [],
        },
        "scorecard": {
            "schema_version": "provider_backed_smoke_results_scorecard_v1",
            "prd": PRD,
            "final_status": "failed",
            "decision": decision,
            "source_gate_passed": False,
            "provider_execution_evidence_status": "failed",
            "provider_budget_status": "failed",
            "normal_user_no_effect_status": "failed",
            "quality_consolidation_status": "failed",
            "safety_kb_boundary_consolidation_status": "failed",
            "provider_output_sanitization_consolidation_status": "failed",
            "trace_sanitization_consolidation_status": "failed",
            "rollback_evidence_status": "failed",
            "botdb_stability_status": "failed",
            "hard_stop_absence_status": "failed",
            "no_mutation_status": "passed",
            "risk_register_has_blockers": False,
            "new_execution_performed": False,
            "provider_called_by_prd_046_1_24": False,
            "broad_rollout_allowed": False,
            "production_ready": False,
            "future_expansion_requires_new_prd": True,
            "artifact_encoding_hygiene_passed": False,
            "docs_synced": docs_synced,
            "recommended_next_prd": gate.NEXT_PRD_FIX,
        },
        "decision_payload": {
            "schema_version": "diagnostic_center_provider_backed_smoke_results_decision_v1",
            "prd": PRD,
            "final_status": "failed",
            "decision": decision,
            "blockers": blockers,
            "warnings": [],
            "recommended_next_prd": gate.NEXT_PRD_FIX,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = gate.tracked_hashes(repo_root)
    preflight = gate.preflight_source(source_dir, reports_dir)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    generated_no_mutation_proof = gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    docs_sync = gate.docs_sync_status(repo_root)

    if preflight["ok"]:
        run_payload = gate.execute_results_gate(
            parsed=preflight["parsed"],
            generated_no_mutation_proof=generated_no_mutation_proof,
            docs_synced=bool(docs_sync["docs_synced"]),
        )
    else:
        run_payload = _fallback_payload(preflight, bool(docs_sync["docs_synced"]))

    _write_json(out_dir / "source_gate.json", run_payload["source_gate"])
    _write_json(out_dir / "provider_execution_evidence_review.json", run_payload["provider_execution_evidence_review"])
    _write_json(out_dir / "provider_budget_review.json", run_payload["provider_budget_review"])
    _write_json(out_dir / "normal_user_no_effect_review.json", run_payload["normal_user_no_effect_review"])
    _write_json(out_dir / "quality_consolidation_review.json", run_payload["quality_consolidation_review"])
    _write_json(out_dir / "safety_kb_boundary_consolidation.json", run_payload["safety_kb_boundary_consolidation"])
    _write_json(out_dir / "provider_output_sanitization_consolidation.json", run_payload["provider_output_sanitization_consolidation"])
    _write_json(out_dir / "trace_sanitization_consolidation.json", run_payload["trace_sanitization_consolidation"])
    _write_json(out_dir / "rollback_evidence_review.json", run_payload["rollback_evidence_review"])
    _write_json(out_dir / "botdb_stability_review.json", run_payload["botdb_stability_review"])
    _write_json(out_dir / "hard_stop_absence_review.json", run_payload["hard_stop_absence_review"])
    _write_json(out_dir / "no_mutation_review.json", run_payload["no_mutation_review"])
    _write_json(out_dir / "provider_backed_results_risk_register.json", run_payload["risk_register"])
    _write_json(out_dir / "provider_backed_results_decision_gate.json", run_payload["decision_gate"])
    _write_json(out_dir / "provider_backed_smoke_results_scorecard.json", run_payload["scorecard"])
    _write_json(out_dir / "no_mutation_proof.json", generated_no_mutation_proof)

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.24 runner executed.\n", encoding="utf-8")

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

    decision_gate = dict(run_payload["decision_gate"])
    decision_gate["artifact_encoding_hygiene_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    _write_json(out_dir / "provider_backed_results_decision_gate.json", decision_gate)

    scorecard = dict(run_payload["scorecard"])
    scorecard["artifact_encoding_hygiene_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    _write_json(out_dir / "provider_backed_smoke_results_scorecard.json", scorecard)

    return {
        "status": str(decision_gate.get("final_status", "failed")),
        "decision": str(decision_gate.get("decision", "fix_required")),
        "decision_gate": decision_gate,
        "scorecard": scorecard,
        "preflight": preflight,
        "docs_sync": docs_sync,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.24 provider-backed smoke results gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.23")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.24")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) in {"passed", "passed_with_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
