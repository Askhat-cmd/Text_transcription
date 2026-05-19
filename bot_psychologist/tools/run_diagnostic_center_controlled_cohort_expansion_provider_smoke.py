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

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate
from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.27"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    fixture_path = Path(args.fixture_path).resolve()
    source_dirs = [Path(item).resolve() for item in args.source_dirs]
    output_dir.mkdir(parents=True, exist_ok=True)

    tracked_paths, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_paths, runtime_hash_before = eval_pack.runtime_hashes(repo_root)

    preflight = gate.preflight_source_chain(source_dirs, reports_dir)
    source_gate = gate.build_source_gate(preflight)
    botdb_preflight = gate.build_botdb_preflight(args.admin_base_url)

    scenarios = gate.load_scenarios_from_fixture(fixture_path)
    cohort_policy = gate.build_cohort_policy(scenarios)
    execution_evidence, sanitized_trace = gate.execute_controlled_cohort_expansion(
        scenarios=scenarios,
        provider_mode=args.provider_mode,
        provider_preflight_passed=bool(botdb_preflight.get("botdb_preflight_passed", False)),
    )
    normal_user_no_effect_gate = gate.build_normal_user_no_effect_gate()
    provider_budget_gate = gate.build_provider_budget_gate(
        provider_calls_total=int(execution_evidence.get("provider_calls_total", 0)),
        target_provider_calls_total=int(execution_evidence.get("target_provider_calls_total", 0)),
        normal_user_provider_calls_total=int(normal_user_no_effect_gate.get("normal_user_provider_calls", 0)),
    )
    quality_micro_shift_gate = gate.build_quality_micro_shift_gate(execution_evidence)
    safety_kb_boundary_gate = gate.build_safety_kb_boundary_gate()
    rollback_gate = gate.build_rollback_gate()
    botdb_post = gate.build_botdb_preflight(args.admin_base_url)
    botdb_stability_gate = gate.build_botdb_stability_gate(before=botdb_preflight, after=botdb_post)

    hash_after = {name: _sha256(path) for name, path in tracked_paths.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_paths.items()}
    no_mutation_proof = gate.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.27 runner executed.\n", encoding="utf-8")

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
    trace_provider_sanitization_gate = gate.build_trace_provider_sanitization_gate(sanitized_trace, artifact_hygiene=encoding_report)
    hard_stop_gate = gate.build_hard_stop_gate(
        source_gate=source_gate,
        botdb_preflight=botdb_preflight,
        cohort_policy=cohort_policy,
        provider_budget_gate=provider_budget_gate,
        normal_user_no_effect_gate=normal_user_no_effect_gate,
        safety_kb_boundary_gate=safety_kb_boundary_gate,
        rollback_gate=rollback_gate,
        no_mutation_proof=no_mutation_proof,
        trace_provider_sanitization_gate=trace_provider_sanitization_gate,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )

    decision_gate, decision_payload = gate.build_decision_gate(
        source_gate=source_gate,
        botdb_preflight=botdb_preflight,
        cohort_policy=cohort_policy,
        provider_execution_evidence=execution_evidence,
        provider_budget_gate=provider_budget_gate,
        normal_user_no_effect_gate=normal_user_no_effect_gate,
        quality_micro_shift_gate=quality_micro_shift_gate,
        safety_kb_boundary_gate=safety_kb_boundary_gate,
        trace_provider_sanitization_gate=trace_provider_sanitization_gate,
        rollback_gate=rollback_gate,
        botdb_stability_gate=botdb_stability_gate,
        hard_stop_gate=hard_stop_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )
    scorecard = gate.build_scorecard(
        decision_gate=decision_gate,
        source_gate=source_gate,
        botdb_preflight=botdb_preflight,
        cohort_policy=cohort_policy,
        provider_execution_evidence=execution_evidence,
        provider_budget_gate=provider_budget_gate,
        normal_user_no_effect_gate=normal_user_no_effect_gate,
        quality_micro_shift_gate=quality_micro_shift_gate,
        safety_kb_boundary_gate=safety_kb_boundary_gate,
        trace_provider_sanitization_gate=trace_provider_sanitization_gate,
        rollback_gate=rollback_gate,
        botdb_stability_gate=botdb_stability_gate,
        hard_stop_gate=hard_stop_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "botdb_preflight.json", botdb_preflight)
    _write_json(output_dir / "cohort_policy.json", cohort_policy)
    _write_json(output_dir / "provider_execution_evidence.json", execution_evidence)
    _write_json(output_dir / "provider_budget_gate.json", provider_budget_gate)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_user_no_effect_gate)
    _write_json(output_dir / "quality_micro_shift_gate.json", quality_micro_shift_gate)
    _write_json(output_dir / "safety_kb_boundary_gate.json", safety_kb_boundary_gate)
    _write_json(output_dir / "trace_provider_sanitization_gate.json", trace_provider_sanitization_gate)
    _write_json(output_dir / "rollback_gate.json", rollback_gate)
    _write_json(output_dir / "botdb_stability_gate.json", botdb_stability_gate)
    _write_json(output_dir / "hard_stop_gate.json", hard_stop_gate)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)
    _write_json(output_dir / "artifact_encoding_hygiene.json", encoding_report)
    _write_json(output_dir / "decision_gate.json", decision_gate)
    _write_json(output_dir / "scorecard.json", scorecard)
    _write_json(output_dir / "sanitized_provider_trace.json", sanitized_trace)
    _write_json(output_dir / "next_prd_recommendation.json", gate.build_next_prd_recommendation(scorecard=scorecard, decision_gate=decision_gate))

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "blocked_requires_hotfix")),
        "preflight": preflight,
        "decision_payload": decision_payload,
        "scorecard": scorecard,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.27 controlled cohort expansion provider-backed execution gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--source-dirs",
        nargs="+",
        default=[
            "TO_DO_LIST/logs/PRD-046.1.23",
            "TO_DO_LIST/logs/PRD-046.1.24",
            "TO_DO_LIST/logs/PRD-046.1.25",
            "TO_DO_LIST/logs/PRD-046.1.26",
        ],
    )
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.27")
    parser.add_argument(
        "--fixture-path",
        default="bot_psychologist/tests/fixtures/diagnostic_center_controlled_cohort_expansion_cases.json",
    )
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--provider-mode", default="mock", choices=["mock", "auto", "disabled"])
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) in {"passed", "passed_with_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
