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

from bot_agent.multiagent import diagnostic_center_final_acceptance as final_acceptance
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.16"


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

    tracked, hash_before = final_acceptance.tracked_hashes(repo_root)
    runtime_tracked, runtime_hash_before = final_acceptance.runtime_do_not_touch_hashes(repo_root)
    preflight = final_acceptance.preflight(source_dir, repo_root)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        payloads = {
            "final_acceptance_source_gate": {
                "source_prd": "PRD-046.1.15",
                "source_final_status": "failed",
                "source_decision": "blocked",
                "all_required_regression_gates_present": False,
                "runtime_files_deleted": True,
                "regression_gates_deleted": True,
                "provider_called": True,
                "artifact_encoding_hygiene_passed": False,
                "source_no_mutation_passed": False,
                "reports_and_logs_present": False,
                "new_execution_performed": False,
                "provider_called_by_eval": False,
                "source_gate_passed": False,
                "blockers": blockers,
            },
            "runtime_governance_boundary_matrix": final_acceptance.build_runtime_governance_boundary_matrix(),
            "permanent_regression_gate_confirmation": {
                "schema_version": "permanent_regression_gate_confirmation_v1",
                "prd": PRD,
                "required_gate_classes": list(final_acceptance.REQUIRED_GATE_CLASSES),
                "gate_checks": [],
                "all_required_regression_gates_present": False,
                "permanent_regression_gates_confirmed": False,
                "final_status": "failed",
                "blockers": blockers,
            },
            "prompt_constraint_conservative_baseline_gate": final_acceptance.build_prompt_constraint_conservative_baseline_gate(repo_root),
            "normal_user_no_effect_gate": final_acceptance.build_normal_user_no_effect_gate(),
            "kb_governance_boundary_gate": {
                "schema_version": "kb_governance_boundary_gate_v1",
                "prd": PRD,
                "final_status": "failed",
                "governance_authority_mutated": True,
            },
            "trace_sanitization_gate": {
                "schema_version": "trace_sanitization_gate_v1",
                "prd": PRD,
                "final_status": "failed",
                "warnings": blockers,
            },
            "runtime_governance_closure_decision": {
                "prd_id": PRD,
                "final_status": "failed",
                "decision": "blocked_missing_permanent_regression_gate",
                "broad_rollout_allowed": False,
                "runtime_authority_expansion_allowed": False,
                "future_rollout_requires_new_prd": True,
                "permanent_regression_gates_confirmed": False,
                "conservative_defaults_preserved": False,
                "no_mutation_proof_passed": False,
                "artifact_encoding_hygiene_passed": False,
                "docs_synced": False,
                "blockers": blockers,
                "warnings": [],
            },
            "diagnostic_center_v1_final_acceptance_scorecard": {
                "prd": PRD,
                "final_status": "failed",
                "decision": "blocked_missing_permanent_regression_gate",
                "source_gate_passed": False,
                "runtime_governance_boundary_matrix_ready": False,
                "permanent_regression_gates_confirmed": False,
                "all_required_regression_gates_present": False,
                "prompt_constraint_conservative_baseline_preserved": False,
                "normal_user_no_effect_passed": False,
                "kb_governance_boundary_passed": False,
                "trace_sanitization_gate_passed": False,
                "broad_rollout_allowed": False,
                "runtime_authority_expansion_allowed": False,
                "future_rollout_requires_new_prd": True,
                "new_execution_performed": False,
                "provider_called": False,
                "production_mutation_detected": True,
                "all_blocks_merged_mutated": True,
                "registry_mutated": True,
                "config_mutated": True,
                "chroma_reindex_performed": False,
                "runtime_files_deleted": False,
                "regression_gates_deleted": False,
                "artifact_encoding_hygiene_passed": False,
                "docs_synced": False,
                "recommended_next_prd": final_acceptance.NEXT_PRD,
                "blockers": blockers,
                "warnings": [],
            },
        }
    else:
        payloads = final_acceptance.execute_final_acceptance(
            parsed=preflight["parsed"],
            repo_root=repo_root,
            strict=strict,
            artifact_hygiene_passed=True,
        )

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_tracked.items()}
    no_mutation = final_acceptance.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    docs_sync = final_acceptance.build_documentation_sync_status(repo_root)
    decision_payload, scorecard = final_acceptance.build_closure_decision(
        source_gate=payloads["final_acceptance_source_gate"],
        boundary_matrix=payloads["runtime_governance_boundary_matrix"],
        permanent_gates=payloads["permanent_regression_gate_confirmation"],
        baseline_gate=payloads["prompt_constraint_conservative_baseline_gate"],
        normal_user_gate=payloads["normal_user_no_effect_gate"],
        kb_gate=payloads["kb_governance_boundary_gate"],
        trace_gate=payloads["trace_sanitization_gate"],
        no_mutation=no_mutation,
        docs_sync=docs_sync,
        artifact_hygiene_passed=True,
        strict=strict,
    )
    payloads["runtime_governance_closure_decision"] = decision_payload
    payloads["diagnostic_center_v1_final_acceptance_scorecard"] = scorecard

    _write_json(out_dir / "final_acceptance_source_gate.json", payloads["final_acceptance_source_gate"])
    _write_json(out_dir / "runtime_governance_boundary_matrix.json", payloads["runtime_governance_boundary_matrix"])
    _write_json(out_dir / "permanent_regression_gate_confirmation.json", payloads["permanent_regression_gate_confirmation"])
    _write_json(out_dir / "prompt_constraint_conservative_baseline_gate.json", payloads["prompt_constraint_conservative_baseline_gate"])
    _write_json(out_dir / "normal_user_no_effect_gate.json", payloads["normal_user_no_effect_gate"])
    _write_json(out_dir / "kb_governance_boundary_gate.json", payloads["kb_governance_boundary_gate"])
    _write_json(out_dir / "trace_sanitization_gate.json", payloads["trace_sanitization_gate"])
    _write_json(out_dir / "runtime_governance_closure_decision.json", payloads["runtime_governance_closure_decision"])
    _write_json(out_dir / "diagnostic_center_v1_final_acceptance_scorecard.json", payloads["diagnostic_center_v1_final_acceptance_scorecard"])
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.16 runner executed.\n", encoding="utf-8")

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

    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    decision_payload, scorecard = final_acceptance.build_closure_decision(
        source_gate=payloads["final_acceptance_source_gate"],
        boundary_matrix=payloads["runtime_governance_boundary_matrix"],
        permanent_gates=payloads["permanent_regression_gate_confirmation"],
        baseline_gate=payloads["prompt_constraint_conservative_baseline_gate"],
        normal_user_gate=payloads["normal_user_no_effect_gate"],
        kb_gate=payloads["kb_governance_boundary_gate"],
        trace_gate=payloads["trace_sanitization_gate"],
        no_mutation=no_mutation,
        docs_sync=docs_sync,
        artifact_hygiene_passed=artifact_hygiene_passed,
        strict=strict,
    )
    payloads["runtime_governance_closure_decision"] = decision_payload
    payloads["diagnostic_center_v1_final_acceptance_scorecard"] = scorecard
    _write_json(out_dir / "runtime_governance_closure_decision.json", decision_payload)
    _write_json(out_dir / "diagnostic_center_v1_final_acceptance_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.16 Diagnostic Center final acceptance gate.")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.15")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.16")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
