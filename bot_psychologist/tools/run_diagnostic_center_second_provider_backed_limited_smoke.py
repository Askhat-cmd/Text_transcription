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

from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.25"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    fixture_path = Path(args.fixture_path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tracked_paths, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_paths, runtime_hash_before = eval_pack.runtime_hashes(repo_root)

    preflight = gate.preflight_source(source_dir, reports_dir)
    source_gate = gate.build_source_gate(preflight["parsed"], preflight["ok"])
    botdb_live_preflight = gate.build_botdb_live_preflight(args.admin_base_url)
    rollback_precheck = gate.build_rollback_precheck()
    provider_preflight = gate.build_provider_availability_preflight(args.provider_mode)

    scenarios = gate.load_scenarios_from_fixture(fixture_path)
    execution_manifest = gate.build_execution_manifest(scenarios_count=len(scenarios))

    ready_for_execution = (
        bool(source_gate.get("source_gate_passed", False))
        and bool(botdb_live_preflight.get("botdb_live_preflight_passed", False))
        and bool(provider_preflight.get("provider_availability_preflight_passed", False))
    )
    execution_result, sanitized_provider_trace = gate.execute_second_provider_backed_smoke(
        scenarios=scenarios,
        provider_mode=args.provider_mode,
        provider_preflight_passed=ready_for_execution,
    )
    execution_payload = dict(execution_result.get("execution", {}))
    aggregate = dict(execution_result.get("aggregate", {}))

    normal_user_no_effect_gate = gate.build_normal_user_no_effect_gate()
    provider_budget_gate = gate.build_provider_budget_gate(
        provider_calls_performed=int(execution_payload.get("provider_calls_performed", 0)),
        normal_user_provider_calls=int(normal_user_no_effect_gate.get("provider_call_count", 0)),
    )
    quality_micro_shift_gate = gate.build_quality_micro_shift_gate(aggregate)
    safety_kb_boundary_gate = gate.build_safety_kb_boundary_gate()
    trace_sanitization_gate = gate.build_trace_sanitization_gate()
    rollback_postcheck = gate.build_rollback_postcheck()
    botdb_after = gate.build_botdb_live_preflight(args.admin_base_url)
    botdb_stability_gate = gate.build_botdb_stability_gate(before=botdb_live_preflight, after=botdb_after)

    hash_after = {name: _sha256(path) for name, path in tracked_paths.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_paths.items()}
    no_mutation_proof = gate.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "botdb_live_preflight.json", botdb_live_preflight)
    _write_json(output_dir / "rollback_precheck.json", rollback_precheck)
    _write_json(output_dir / "execution_manifest.json", execution_manifest)
    _write_json(output_dir / "provider_budget_gate.json", provider_budget_gate)
    _write_json(output_dir / "sanitized_provider_trace.json", sanitized_provider_trace)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_user_no_effect_gate)
    _write_json(output_dir / "quality_micro_shift_gate.json", quality_micro_shift_gate)
    _write_json(output_dir / "safety_kb_boundary_gate.json", safety_kb_boundary_gate)
    _write_json(output_dir / "trace_sanitization_gate.json", trace_sanitization_gate)
    _write_json(output_dir / "rollback_postcheck.json", rollback_postcheck)
    _write_json(output_dir / "botdb_stability_gate.json", botdb_stability_gate)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.25 runner executed.\n", encoding="utf-8")

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

    decision_gate, decision_payload = gate.build_decision_gate(
        source_gate=source_gate,
        botdb_live_preflight=botdb_live_preflight,
        rollback_precheck=rollback_precheck,
        execution_manifest=execution_manifest,
        provider_preflight=provider_preflight,
        execution=execution_payload,
        provider_budget_gate=provider_budget_gate,
        normal_user_no_effect_gate=normal_user_no_effect_gate,
        quality_micro_shift_gate=quality_micro_shift_gate,
        safety_kb_boundary_gate=safety_kb_boundary_gate,
        trace_sanitization_gate=trace_sanitization_gate,
        rollback_postcheck=rollback_postcheck,
        botdb_stability_gate=botdb_stability_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )
    scorecard = gate.build_scorecard(
        decision_gate=decision_gate,
        source_gate=source_gate,
        botdb_live_preflight=botdb_live_preflight,
        provider_budget_gate=provider_budget_gate,
        normal_user_no_effect_gate=normal_user_no_effect_gate,
        quality_micro_shift_gate=quality_micro_shift_gate,
        safety_kb_boundary_gate=safety_kb_boundary_gate,
        trace_sanitization_gate=trace_sanitization_gate,
        rollback_postcheck=rollback_postcheck,
        botdb_stability_gate=botdb_stability_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
    )
    _write_json(output_dir / "decision_gate.json", decision_gate)
    _write_json(output_dir / "scorecard.json", scorecard)

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "hotfix_required")),
        "source_preflight": preflight,
        "encoding_report": encoding_report,
        "decision_payload": decision_payload,
        "scorecard": scorecard,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.25 second provider-backed limited smoke gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.24")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.25")
    parser.add_argument(
        "--fixture-path",
        default="bot_psychologist/tests/fixtures/diagnostic_center_second_provider_backed_smoke_cases.json",
    )
    parser.add_argument("--provider-mode", default="auto", choices=["auto", "mock", "disabled"])
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) in {"passed", "passed_with_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
