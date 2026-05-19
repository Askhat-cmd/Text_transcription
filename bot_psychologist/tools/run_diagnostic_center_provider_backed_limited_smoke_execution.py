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

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution
from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.23"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _minimal_pilot_payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    pilot_execution = {
        "schema_version": "provider_backed_pilot_operator_execution_v1",
        "prd": PRD,
        "allowed_user_id": execution.ALLOWLISTED_OPERATOR,
        "target_user_count": 1,
        "pilot_scenarios_executed": 0,
        "pilot_apply_count": 0,
        "pilot_apply_only_for_allowed_user": True,
        "provider_calls_performed": 0,
        "provider_call_failures_count": 0,
        "provider_calls_for_normal_users": 0,
        "all_provider_calls_for_allowed_user": True,
        "semantic_fallback_used": False,
        "botdb_circuit_open": False,
    }
    pilot_trace = {
        "schema_version": "provider_backed_pilot_operator_trace_samples_sanitized_v1",
        "prd": PRD,
        "samples": [],
    }
    aggregate = {
        "micro_shift_present_count": 0,
        "raw_kb_quote_exposure_count": 0,
        "kuznitsa_authority_citation_count": 0,
        "high_stakes_directive_advice_count": 0,
        "provider_call_failures_count": 0,
    }
    return pilot_execution, pilot_trace, aggregate


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tracked_paths, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_paths, runtime_hash_before = eval_pack.runtime_hashes(repo_root)

    preflight = execution.preflight_source(source_dir, reports_dir)
    source_gate = execution.build_source_gate(preflight["parsed"], preflight["ok"])
    live_preflight = execution.build_live_dependency_preflight(args.admin_base_url)
    provider_preflight, provider_client = execution.build_provider_availability_preflight(args.provider_mode)
    toggle_state_before = execution.build_toggle_state_before()
    rollback_precheck = execution.build_rollback_precheck()
    execution_manifest = execution._build_execution_manifest()  # noqa: SLF001

    ready_for_execution = (
        bool(source_gate.get("source_gate_passed", False))
        and bool(live_preflight.get("live_dependency_preflight_passed", False))
        and bool(provider_preflight.get("provider_availability_preflight_passed", False))
    )

    if ready_for_execution:
        scenarios = execution.load_scenarios(preflight["parsed"])
        pilot_execution, pilot_trace, aggregate = execution.execute_pilot_operator(
            scenarios=scenarios,
            provider_mode=args.provider_mode,
            provider_model_name=str(provider_preflight.get("provider_model_name") or "gpt-5-mini"),
            provider_client=provider_client,
            retrieval_source="api",
            semantic_fallback_used=bool(live_preflight.get("semantic_fallback_used", False)),
        )
    else:
        pilot_execution, pilot_trace, aggregate = _minimal_pilot_payload()

    normal_controls, normal_controls_trace = execution.build_normal_user_controls()
    provider_budget = execution.build_provider_call_budget(
        provider_calls_performed=int(pilot_execution.get("provider_calls_performed", 0)),
        provider_calls_for_normal_users=int(normal_controls.get("normal_user_provider_apply_count", 0)),
        provider_error_leak_to_user_output=False,
    )
    provider_output_review = execution.build_provider_output_sanitization_review(
        provider_error_count=int(aggregate.get("provider_call_failures_count", 0)),
    )
    quality_review = execution.build_quality_review(aggregate=aggregate, pilot_execution=pilot_execution)
    safety_review = execution.build_safety_kb_boundary_review(aggregate=aggregate)
    trace_review = execution.build_trace_sanitization_review()
    rollback_postcheck = execution.build_rollback_postcheck()

    hash_after = {name: _sha256(path) for name, path in tracked_paths.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_paths.items()}
    no_mutation_proof = execution.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
        provider_called_for_pilot_operator=int(pilot_execution.get("provider_calls_performed", 0)) > 0,
    )
    docs_sync = execution.build_docs_sync_status(repo_root)

    hard_stop = execution.build_hard_stop_evaluation(
        provider_budget=provider_budget,
        normal_controls=normal_controls,
        quality_review=quality_review,
        safety_review=safety_review,
        trace_review=trace_review,
        rollback_postcheck=rollback_postcheck,
        live_preflight=live_preflight,
        provider_output_review=provider_output_review,
        production_mutation_detected=any(
            bool(no_mutation_proof.get(name, False))
            for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated", "runtime_defaults_changed")
        ),
    )

    scorecard, decision_payload = execution.decide_final_status(
        source_gate=source_gate,
        live_preflight=live_preflight,
        provider_preflight=provider_preflight,
        execution_manifest=execution_manifest,
        pilot_execution=pilot_execution,
        normal_controls=normal_controls,
        quality_review=quality_review,
        safety_review=safety_review,
        trace_review=trace_review,
        provider_output_review=provider_output_review,
        rollback_precheck=rollback_precheck,
        rollback_postcheck=rollback_postcheck,
        provider_budget=provider_budget,
        hard_stop=hard_stop,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=True,
        docs_sync=docs_sync,
    )

    live_after = execution.build_live_dependency_preflight(args.admin_base_url)
    botdb_health_during = execution.build_botdb_health_snapshot(live_preflight=live_preflight, stage="during_execution")
    botdb_health_after = execution.build_botdb_health_snapshot(live_preflight=live_after, stage="after_execution")

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "live_dependency_preflight.json", live_preflight)
    _write_json(output_dir / "provider_availability_preflight.json", provider_preflight)
    _write_json(output_dir / "toggle_state_before.json", toggle_state_before)
    _write_json(output_dir / "rollback_precheck.json", rollback_precheck)
    _write_json(output_dir / "execution_manifest.json", execution_manifest)
    _write_json(output_dir / "provider_call_budget.json", provider_budget)
    _write_json(output_dir / "pilot_operator_provider_backed_execution.json", pilot_execution)
    _write_json(output_dir / "pilot_operator_trace_samples_sanitized.json", pilot_trace)
    _write_json(output_dir / "normal_user_control_execution.json", normal_controls)
    _write_json(output_dir / "normal_user_control_trace_samples_sanitized.json", normal_controls_trace)
    _write_json(output_dir / "provider_output_sanitization_review.json", provider_output_review)
    _write_json(output_dir / "quality_review.json", quality_review)
    _write_json(output_dir / "safety_kb_boundary_review.json", safety_review)
    _write_json(output_dir / "trace_sanitization_review.json", trace_review)
    _write_json(output_dir / "rollback_postcheck.json", rollback_postcheck)
    _write_json(output_dir / "botdb_health_during_execution.json", botdb_health_during)
    _write_json(output_dir / "botdb_health_after_execution.json", botdb_health_after)
    _write_json(output_dir / "hard_stop_evaluation.json", hard_stop)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)
    _write_json(output_dir / "provider_backed_limited_smoke_execution_scorecard.json", scorecard)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.23 runner executed.\n", encoding="utf-8")

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

    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    scorecard, decision_payload = execution.decide_final_status(
        source_gate=source_gate,
        live_preflight=live_preflight,
        provider_preflight=provider_preflight,
        execution_manifest=execution_manifest,
        pilot_execution=pilot_execution,
        normal_controls=normal_controls,
        quality_review=quality_review,
        safety_review=safety_review,
        trace_review=trace_review,
        provider_output_review=provider_output_review,
        rollback_precheck=rollback_precheck,
        rollback_postcheck=rollback_postcheck,
        provider_budget=provider_budget,
        hard_stop=hard_stop,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_sync=docs_sync,
    )
    _write_json(output_dir / "provider_backed_limited_smoke_execution_scorecard.json", scorecard)
    _write_json(output_dir / "next_prd_recommendation.json", execution.build_next_prd_recommendation(scorecard=scorecard, decision_payload=decision_payload))

    return {
        "status": str(scorecard.get("final_status", "failed")),
        "decision": str(scorecard.get("decision", "provider_backed_limited_smoke_failed")),
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "source_preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.23 provider-backed limited smoke execution gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.22")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.23")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--provider-mode", default="auto", choices=["auto", "mock", "disabled"])
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) in {"passed", "passed_with_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
