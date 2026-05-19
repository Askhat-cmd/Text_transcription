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

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.28"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    source_dirs = [Path(item).resolve() for item in args.source_dirs]
    strict = bool(getattr(args, "strict", False))

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    tracked_paths, hash_before = gate.eval_pack.tracked_hashes(repo_root)
    runtime_paths, runtime_hash_before = gate.eval_pack.runtime_hashes(repo_root)

    preflight = gate.preflight_source_chain(source_dirs, reports_dir, repo_root)
    source_chain_gate = gate.build_source_chain_gate(preflight)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.28 runner executed.\n", encoding="utf-8")

    _write_json(output_dir / "source_chain_gate.json", source_chain_gate)

    if strict and not preflight["ok"]:
        no_mutation_proof = gate.build_no_mutation_proof(
            hash_before=hash_before,
            hash_after={name: gate._sha256(path) for name, path in tracked_paths.items()},
            runtime_hash_before=runtime_hash_before,
            runtime_hash_after={name: gate._sha256(path) for name, path in runtime_paths.items()},
        )
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
        artifact_hygiene = gate.build_artifact_hygiene(encoding_report)
        blocked_stub = {
            "schema_version": "diagnostic_center_final_runtime_governance_stub_v1",
            "prd": PRD,
            "final_status": "blocked",
            "reason": "preflight_failed",
            "missing": list(preflight["missing"]),
            "parse_errors": list(preflight["parse_errors"]),
        }
        _write_json(output_dir / "cumulative_provider_evidence_gate.json", blocked_stub)
        _write_json(output_dir / "normal_user_no_effect_gate.json", blocked_stub)
        _write_json(output_dir / "rollback_hard_stop_gate.json", blocked_stub)
        _write_json(output_dir / "safety_kb_boundary_gate.json", blocked_stub)
        _write_json(output_dir / "trace_provider_sanitization_gate.json", blocked_stub)
        _write_json(output_dir / "botdb_stability_gate.json", blocked_stub)
        _write_json(output_dir / "quality_micro_shift_gate.json", blocked_stub)
        _write_json(output_dir / "permanent_regression_gates.json", blocked_stub)
        _write_json(output_dir / "runtime_governance_boundary_decision.json", blocked_stub)
        _write_json(output_dir / "cleanup_stabilization_readiness.json", blocked_stub)
        _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)
        _write_json(output_dir / "artifact_encoding_hygiene.json", artifact_hygiene)
        _write_json(output_dir / "risk_register.json", {"prd": PRD, "risk_register_has_blockers": True, "blockers": ["preflight_failed"]})
        _write_json(
            output_dir / "final_acceptance_scorecard.json",
            {
                "prd": PRD,
                "final_status": "blocked",
                "decision": "blocked_requires_hotfix",
                "blockers": ["preflight_failed"],
            },
        )
        return {
            "status": "blocked",
            "decision": "blocked_requires_hotfix",
            "preflight": preflight,
            "scorecard": {"final_status": "blocked", "decision": "blocked_requires_hotfix"},
            "encoding_report": encoding_report,
        }

    parsed = preflight["parsed"]
    provider_evidence = gate.build_cumulative_provider_evidence(parsed)
    normal_user_no_effect = gate.build_normal_user_no_effect_gate(parsed)
    rollback_hard_stop = gate.build_rollback_hard_stop_gate(parsed)
    safety_kb_boundary = gate.build_safety_kb_boundary_gate(parsed)
    trace_provider_sanitization = gate.build_trace_provider_sanitization_gate(parsed, preflight)
    botdb_stability = gate.build_botdb_stability_gate(parsed, args.admin_base_url)
    quality_micro_shift = gate.build_quality_micro_shift_gate(parsed, provider_evidence)
    permanent_regression_gates = gate.build_permanent_regression_gates()
    runtime_governance_boundaries = gate.build_runtime_governance_boundary_decision()
    cleanup_stabilization_readiness = gate.build_cleanup_stabilization_readiness()

    hash_after = {name: gate._sha256(path) for name, path in tracked_paths.items()}
    runtime_hash_after = {name: gate._sha256(path) for name, path in runtime_paths.items()}
    no_mutation_proof = gate.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    _write_json(output_dir / "cumulative_provider_evidence_gate.json", provider_evidence)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_user_no_effect)
    _write_json(output_dir / "rollback_hard_stop_gate.json", rollback_hard_stop)
    _write_json(output_dir / "safety_kb_boundary_gate.json", safety_kb_boundary)
    _write_json(output_dir / "trace_provider_sanitization_gate.json", trace_provider_sanitization)
    _write_json(output_dir / "botdb_stability_gate.json", botdb_stability)
    _write_json(output_dir / "quality_micro_shift_gate.json", quality_micro_shift)
    _write_json(output_dir / "permanent_regression_gates.json", permanent_regression_gates)
    _write_json(output_dir / "runtime_governance_boundary_decision.json", runtime_governance_boundaries)
    _write_json(output_dir / "cleanup_stabilization_readiness.json", cleanup_stabilization_readiness)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

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
    artifact_hygiene = gate.build_artifact_hygiene(encoding_report)
    docs_sync = gate.docs_sync_status(repo_root)

    boundary_decision, next_prd_recommendation, risk_register, scorecard = gate.build_decision_gate(
        source_chain=source_chain_gate,
        provider_evidence=provider_evidence,
        normal_user_no_effect=normal_user_no_effect,
        rollback_hard_stop=rollback_hard_stop,
        safety_kb_boundary=safety_kb_boundary,
        trace_provider_sanitization=trace_provider_sanitization,
        botdb_stability=botdb_stability,
        quality_micro_shift=quality_micro_shift,
        permanent_regression_gates=permanent_regression_gates,
        runtime_governance_boundaries=runtime_governance_boundaries,
        cleanup_stabilization_readiness=cleanup_stabilization_readiness,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene=artifact_hygiene,
        docs_sync=docs_sync,
    )

    contract = gate.build_contract(
        final_status=str(scorecard.get("final_status", "blocked")),
        decision=str(scorecard.get("decision", "blocked_requires_hotfix")),
        source_chain=source_chain_gate,
        provider_evidence=provider_evidence,
        normal_user_no_effect=normal_user_no_effect,
        rollback_hard_stop=rollback_hard_stop,
        safety_kb_boundary=safety_kb_boundary,
        trace_provider_sanitization=trace_provider_sanitization,
        botdb_stability=botdb_stability,
        quality_micro_shift=quality_micro_shift,
        permanent_regression_gates=permanent_regression_gates,
        runtime_governance_boundaries=runtime_governance_boundaries,
        cleanup_stabilization_readiness=cleanup_stabilization_readiness,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene=artifact_hygiene,
        risk_register=risk_register,
        next_prd_recommendation=next_prd_recommendation,
    )

    _write_json(output_dir / "artifact_encoding_hygiene.json", artifact_hygiene)
    _write_json(output_dir / "risk_register.json", risk_register)
    _write_json(output_dir / "final_acceptance_scorecard.json", scorecard)
    _write_json(output_dir / "runtime_governance_boundary_decision.json", boundary_decision)
    _write_json(output_dir / "diagnostic_center_final_runtime_governance_acceptance_contract.json", contract)
    _write_json(output_dir / "next_prd_recommendation.json", next_prd_recommendation)

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "blocked_requires_hotfix")),
        "preflight": preflight,
        "scorecard": scorecard,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.28 final runtime governance acceptance gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--source-dirs",
        nargs="+",
        default=[
            "TO_DO_LIST/logs/PRD-046.1.23",
            "TO_DO_LIST/logs/PRD-046.1.24",
            "TO_DO_LIST/logs/PRD-046.1.25",
            "TO_DO_LIST/logs/PRD-046.1.26",
            "TO_DO_LIST/logs/PRD-046.1.27",
        ],
    )
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.28")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

