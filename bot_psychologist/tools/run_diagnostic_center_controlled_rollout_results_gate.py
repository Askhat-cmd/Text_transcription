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

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.32"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = gate.tracked_hashes(repo_root)
    preflight = gate.preflight_source(source_dir, reports_dir)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001

    source_no_mutation = preflight.get("parsed", {}).get("no_mutation_proof", {})
    no_mutation_proof = gate.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        source_no_mutation=source_no_mutation if isinstance(source_no_mutation, dict) else {},
    )

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.32 runner executed.\n", encoding="utf-8")

    initial_encoding_report = encoding_validator.run(
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

    project_state = (docs_dir / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (docs_dir / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (docs_dir / "PRD_INDEX.md").read_text(encoding="utf-8")
    decisions = (docs_dir / "DECISIONS.md").read_text(encoding="utf-8")

    run_payload = gate.execute_results_gate(
        preflight=preflight,
        no_mutation_proof=no_mutation_proof,
        current_encoding_report=initial_encoding_report,
        project_state_text=project_state,
        roadmap_text=roadmap,
        prd_index_text=prd_index,
        decisions_text=decisions,
    )

    _write_json(out_dir / "source_gate.json", run_payload["source_gate"])
    _write_json(out_dir / "execution_evidence_consolidation.json", run_payload["execution_evidence_consolidation"])
    _write_json(out_dir / "provider_budget_gate.json", run_payload["provider_budget_gate"])
    _write_json(out_dir / "normal_user_no_effect_gate.json", run_payload["normal_user_no_effect_gate"])
    _write_json(out_dir / "quality_micro_shift_gate.json", run_payload["quality_micro_shift_gate"])
    _write_json(out_dir / "rollback_hard_stop_gate.json", run_payload["rollback_hard_stop_gate"])
    _write_json(out_dir / "safety_kb_boundary_gate.json", run_payload["safety_kb_boundary_gate"])
    _write_json(out_dir / "trace_provider_sanitization_gate.json", run_payload["trace_provider_sanitization_gate"])
    _write_json(out_dir / "botdb_stability_gate.json", run_payload["botdb_stability_gate"])
    _write_json(out_dir / "docs_consistency_gate.json", run_payload["docs_consistency_gate"])
    _write_json(out_dir / "no_mutation_proof.json", run_payload["no_mutation_proof"])
    _write_json(out_dir / "results_gate_scorecard.json", run_payload["results_gate_scorecard"])

    final_encoding_report = encoding_validator.run(
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

    run_payload["artifact_encoding_hygiene_report"] = gate.build_artifact_hygiene_gate(
        preflight.get("parsed", {}),
        final_encoding_report,
    )
    _write_json(out_dir / "artifact_encoding_hygiene_report.json", run_payload["artifact_encoding_hygiene_report"])

    run_payload["decision"] = gate.build_decision_gate(
        source_gate=run_payload["source_gate"],
        execution_evidence=run_payload["execution_evidence_consolidation"],
        provider_budget=run_payload["provider_budget_gate"],
        normal_user=run_payload["normal_user_no_effect_gate"],
        quality=run_payload["quality_micro_shift_gate"],
        rollback=run_payload["rollback_hard_stop_gate"],
        safety=run_payload["safety_kb_boundary_gate"],
        trace=run_payload["trace_provider_sanitization_gate"],
        botdb=run_payload["botdb_stability_gate"],
        no_mutation=run_payload["no_mutation_proof"],
        artifact_hygiene=run_payload["artifact_encoding_hygiene_report"],
        docs_consistency=run_payload["docs_consistency_gate"],
    )
    run_payload["results_gate_scorecard"]["final_status"] = run_payload["decision"]["final_status"]
    run_payload["results_gate_scorecard"]["decision"] = run_payload["decision"]["decision"]
    run_payload["results_gate_scorecard"]["source_gate_passed"] = run_payload["decision"]["source_gate_passed"]
    run_payload["results_gate_scorecard"]["provider_budget_gate_passed"] = run_payload["decision"]["provider_budget_gate_passed"]
    run_payload["results_gate_scorecard"]["normal_user_no_effect_passed"] = run_payload["decision"]["normal_user_no_effect_passed"]
    run_payload["results_gate_scorecard"]["quality_micro_shift_gate_passed"] = run_payload["decision"]["quality_micro_shift_gate_passed"]
    run_payload["results_gate_scorecard"]["rollback_gate_passed"] = run_payload["decision"]["rollback_gate_passed"]
    run_payload["results_gate_scorecard"]["safety_kb_boundary_gate_passed"] = run_payload["decision"]["safety_kb_boundary_gate_passed"]
    run_payload["results_gate_scorecard"]["trace_provider_sanitization_gate_passed"] = run_payload["decision"]["trace_provider_sanitization_gate_passed"]
    run_payload["results_gate_scorecard"]["botdb_stability_gate_passed"] = run_payload["decision"]["botdb_stability_gate_passed"]
    run_payload["results_gate_scorecard"]["no_mutation_proof_passed"] = run_payload["decision"]["no_mutation_proof_passed"]
    run_payload["results_gate_scorecard"]["artifact_encoding_hygiene_passed"] = run_payload["decision"]["artifact_encoding_hygiene_passed"]
    run_payload["results_gate_scorecard"]["docs_consistency_passed"] = run_payload["decision"]["docs_consistency_passed"]
    run_payload["results_gate_scorecard"]["next_recommended_prd"] = run_payload["decision"]["next_recommended_prd"]
    run_payload["results_gate_scorecard"]["blockers"] = run_payload["decision"]["blockers"]
    run_payload["results_gate_scorecard"]["warnings"] = run_payload["decision"]["warnings"]
    _write_json(out_dir / "results_gate_scorecard.json", run_payload["results_gate_scorecard"])

    return {
        "status": str(run_payload["decision"].get("final_status", "failed")),
        "decision": str(run_payload["decision"].get("decision", "stop_before_activation_readiness")),
        "decision_payload": run_payload["decision"],
        "scorecard": run_payload["results_gate_scorecard"],
        "preflight": preflight,
        "encoding_report": final_encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.32 controlled rollout results gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.31")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.32")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
