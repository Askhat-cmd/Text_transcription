from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.26"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    source_dirs = [Path(item).resolve() for item in args.source_dirs]
    output_dir.mkdir(parents=True, exist_ok=True)

    tracked_paths, hash_before = gate.eval_pack.tracked_hashes(repo_root)
    runtime_paths, runtime_hash_before = gate.eval_pack.runtime_hashes(repo_root)

    preflight = gate.preflight_source_chain(source_dirs, reports_dir)
    source_gate = gate.build_source_gate(preflight)
    cumulative_provider_evidence = gate.build_cumulative_provider_evidence(preflight["parsed"])
    normal_user_no_effect_cumulative = gate.build_normal_user_no_effect_cumulative(preflight["parsed"])
    rollback_cumulative = gate.build_rollback_cumulative(preflight["parsed"])
    safety_kb_boundary_cumulative = gate.build_safety_kb_boundary_cumulative(preflight["parsed"])
    botdb_stability_trend = gate.build_botdb_stability_trend(
        preflight["parsed"],
        admin_base_url=args.admin_base_url,
        allow_unreachable_warning=True,
    )
    quality_micro_shift_cumulative = gate.build_quality_micro_shift_cumulative(preflight["parsed"])

    hash_after = {name: _sha256(path) for name, path in tracked_paths.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_paths.items()}
    no_mutation_proof = gate.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    trace_provider_sanitization_cumulative = gate.build_trace_provider_sanitization_cumulative(preflight["parsed"], artifact_hygiene={})
    decision_gate, decision_payload = gate.build_decision_gate(
        source_gate=source_gate,
        cumulative_provider_evidence=cumulative_provider_evidence,
        normal_user_no_effect_cumulative=normal_user_no_effect_cumulative,
        rollback_cumulative=rollback_cumulative,
        safety_kb_boundary_cumulative=safety_kb_boundary_cumulative,
        trace_provider_sanitization_cumulative=trace_provider_sanitization_cumulative,
        botdb_stability_trend=botdb_stability_trend,
        quality_micro_shift_cumulative=quality_micro_shift_cumulative,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=True,
    )

    controlled_cohort_expansion_readiness = gate.build_controlled_cohort_expansion_readiness(
        passed=str(decision_gate.get("final_status", "blocked")) == "passed",
        decision=str(decision_gate.get("decision", "blocker_requires_hotfix")),
    )
    future_cleanup_stabilization_requirement = gate.build_future_cleanup_stabilization_requirement()
    consolidation_scorecard = gate.build_consolidation_scorecard(
        decision_gate=decision_gate,
        source_gate=source_gate,
        cumulative_provider_evidence=cumulative_provider_evidence,
        normal_user_no_effect_cumulative=normal_user_no_effect_cumulative,
        rollback_cumulative=rollback_cumulative,
        safety_kb_boundary_cumulative=safety_kb_boundary_cumulative,
        trace_provider_sanitization_cumulative=trace_provider_sanitization_cumulative,
        botdb_stability_trend=botdb_stability_trend,
        quality_micro_shift_cumulative=quality_micro_shift_cumulative,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=True,
        controlled_cohort_expansion_readiness_ready=bool(controlled_cohort_expansion_readiness["controlled_cohort_expansion_readiness_ready"]),
        future_cleanup_stabilization_requirement_created=bool(
            future_cleanup_stabilization_requirement["future_cleanup_stabilization_requirement_created"],
        ),
    )

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "cumulative_provider_evidence.json", cumulative_provider_evidence)
    _write_json(output_dir / "normal_user_no_effect_cumulative.json", normal_user_no_effect_cumulative)
    _write_json(output_dir / "rollback_cumulative.json", rollback_cumulative)
    _write_json(output_dir / "safety_kb_boundary_cumulative.json", safety_kb_boundary_cumulative)
    _write_json(output_dir / "trace_provider_sanitization_cumulative.json", trace_provider_sanitization_cumulative)
    _write_json(output_dir / "botdb_stability_trend.json", botdb_stability_trend)
    _write_json(output_dir / "quality_micro_shift_cumulative.json", quality_micro_shift_cumulative)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)
    _write_json(output_dir / "controlled_cohort_expansion_readiness.json", controlled_cohort_expansion_readiness)
    _write_json(output_dir / "future_cleanup_stabilization_requirement.json", future_cleanup_stabilization_requirement)
    _write_json(output_dir / "consolidation_scorecard.json", consolidation_scorecard)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.26 runner executed.\n", encoding="utf-8")

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(output_dir),
            reports_dir=str(reports_dir),
            out_dir=str(output_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    artifact_encoding_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    _write_json(output_dir / "artifact_encoding_hygiene.json", encoding_report)

    trace_provider_sanitization_cumulative = gate.build_trace_provider_sanitization_cumulative(
        preflight["parsed"],
        artifact_hygiene=encoding_report,
    )
    decision_gate, decision_payload = gate.build_decision_gate(
        source_gate=source_gate,
        cumulative_provider_evidence=cumulative_provider_evidence,
        normal_user_no_effect_cumulative=normal_user_no_effect_cumulative,
        rollback_cumulative=rollback_cumulative,
        safety_kb_boundary_cumulative=safety_kb_boundary_cumulative,
        trace_provider_sanitization_cumulative=trace_provider_sanitization_cumulative,
        botdb_stability_trend=botdb_stability_trend,
        quality_micro_shift_cumulative=quality_micro_shift_cumulative,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )
    controlled_cohort_expansion_readiness = gate.build_controlled_cohort_expansion_readiness(
        passed=str(decision_gate.get("final_status", "blocked")) == "passed",
        decision=str(decision_gate.get("decision", "blocker_requires_hotfix")),
    )
    consolidation_scorecard = gate.build_consolidation_scorecard(
        decision_gate=decision_gate,
        source_gate=source_gate,
        cumulative_provider_evidence=cumulative_provider_evidence,
        normal_user_no_effect_cumulative=normal_user_no_effect_cumulative,
        rollback_cumulative=rollback_cumulative,
        safety_kb_boundary_cumulative=safety_kb_boundary_cumulative,
        trace_provider_sanitization_cumulative=trace_provider_sanitization_cumulative,
        botdb_stability_trend=botdb_stability_trend,
        quality_micro_shift_cumulative=quality_micro_shift_cumulative,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        controlled_cohort_expansion_readiness_ready=bool(controlled_cohort_expansion_readiness["controlled_cohort_expansion_readiness_ready"]),
        future_cleanup_stabilization_requirement_created=bool(
            future_cleanup_stabilization_requirement["future_cleanup_stabilization_requirement_created"],
        ),
    )

    _write_json(output_dir / "trace_provider_sanitization_cumulative.json", trace_provider_sanitization_cumulative)
    _write_json(output_dir / "controlled_cohort_expansion_readiness.json", controlled_cohort_expansion_readiness)
    _write_json(output_dir / "consolidation_scorecard.json", consolidation_scorecard)

    next_prd_recommendation = gate.build_next_prd_recommendation(scorecard=consolidation_scorecard, decision_gate=decision_gate)
    _write_json(output_dir / "next_prd_recommendation.json", next_prd_recommendation)

    return {
        "status": str(consolidation_scorecard.get("final_status", "blocked")),
        "decision": str(consolidation_scorecard.get("decision", "blocker_requires_hotfix")),
        "decision_gate": decision_gate,
        "decision_payload": decision_payload,
        "scorecard": consolidation_scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
        "next_prd_recommendation": next_prd_recommendation,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.26 limited smoke consolidation decision gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--source-dirs",
        nargs="+",
        default=[
            "TO_DO_LIST/logs/PRD-046.1.23",
            "TO_DO_LIST/logs/PRD-046.1.24",
            "TO_DO_LIST/logs/PRD-046.1.25",
        ],
    )
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.26")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) in {"passed", "passed_with_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
