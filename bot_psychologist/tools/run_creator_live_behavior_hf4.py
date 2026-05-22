from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_behavior_hf4 as hf4  # noqa: E402
from tools import validate_prd_artifact_encoding as encoding_validator  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _render_behavior_report(smoke: dict, routing: dict, anti: dict, move: dict) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF4 Behavior Calibration Report",
            "",
            f"- creator_live_behavior_smoke_gate: `{smoke.get('creator_live_behavior_smoke_gate', 'blocked')}`",
            f"- example_request_routing_gate: `{routing.get('example_request_routing_gate', 'blocked')}`",
            f"- anti_regulate_loop_gate: `{anti.get('anti_regulate_loop_gate', 'blocked')}`",
            f"- writer_move_calibration_gate: `{move.get('writer_move_calibration_gate', 'blocked')}`",
            f"- example_cases_total: `{smoke.get('example_cases_total', 0)}`",
            f"- example_cases_passed: `{smoke.get('example_cases_passed', 0)}`",
            f"- true_regulate_case_passed: `{str(smoke.get('true_regulate_case_passed', False)).lower()}`",
        ]
    )


def _render_trace_report(chunks_gate: dict) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF4 Trace Chunks Display Report",
            "",
            f"- writer_chunks_display_gate: `{chunks_gate.get('writer_chunks_display_gate', 'blocked')}`",
            f"- writer_chunks_count: `{chunks_gate.get('writer_chunks_count', 0)}`",
            f"- writer_chunks_non_empty_preview_count: `{chunks_gate.get('writer_chunks_non_empty_preview_count', 0)}`",
            f"- writer_chunks_empty_preview_count: `{chunks_gate.get('writer_chunks_empty_preview_count', 0)}`",
            f"- warning: `{chunks_gate.get('warning', '')}`",
        ]
    )


def _render_next_prd(scorecard: dict) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35-HF4 Next PRD Recommendation",
            "",
            f"- recommendation: `{scorecard.get('next_prd_recommendation', hf4.NEXT_PRD)}`",
            f"- based_on_decision: `{scorecard.get('decision', hf4.DECISION_BLOCKED_ROUTING)}`",
        ]
    )


def run(args: argparse.Namespace) -> dict:
    repo_root = Path(args.repo_root).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    test_output = output_dir / "test_command_output.txt"
    test_output.write_text("PRD-046.1.35-HF4 runner executed.\n", encoding="utf-8")

    tracked, hash_before = hf4.tracked_hashes(repo_root)

    source_gate = hf4.preflight_source_gate(repo_root)
    smoke, anti, routing, move = hf4.run_behavior_smoke(repo_root)
    chunks_gate = hf4.build_writer_chunks_display_gate(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )
    rag_gate = hf4.build_rag_regression_gate(repo_root)
    normal_gate = hf4.build_normal_user_no_effect_gate(repo_root)
    provider_gate = hf4.build_provider_budget_gate(repo_root)

    hash_after = {name: hf4._sha256_path(path) for name, path in tracked.items()}  # noqa: SLF001
    no_mutation = hf4.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "anti_regulate_loop_audit.json", anti)
    _write_json(output_dir / "example_request_routing_probe.json", routing)
    _write_json(output_dir / "writer_move_calibration_probe.json", move)
    _write_json(output_dir / "creator_live_behavior_smoke.json", smoke)
    _write_json(output_dir / "writer_chunks_display_gate.json", chunks_gate)
    _write_json(output_dir / "rag_regression_gate.json", rag_gate)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_gate)
    _write_json(output_dir / "provider_budget_gate.json", provider_gate)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation)

    trace_gate = hf4.build_trace_sanitization_gate(output_dir)
    _write_json(output_dir / "trace_sanitization_gate.json", trace_gate)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=hf4.PRD,
            logs_dir=str(output_dir),
            reports_dir=str(reports_dir),
            out_dir=str(output_dir),
            report_prd=hf4.PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    encoding_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    _write_json(output_dir / "artifact_encoding_hygiene_report.json", encoding_report)

    scorecard, decision_payload = hf4.build_hf4_scorecard(
        source_gate=source_gate,
        creator_live_behavior_smoke=smoke,
        anti_loop_audit=anti,
        routing_probe=routing,
        writer_move_probe=move,
        writer_chunks_gate=chunks_gate,
        rag_regression_gate=rag_gate,
        normal_user_gate=normal_gate,
        trace_gate=trace_gate,
        provider_gate=provider_gate,
        no_mutation_proof=no_mutation,
        artifact_encoding_hygiene_passed=encoding_passed,
    )
    _write_json(output_dir / "hf4_scorecard.json", scorecard)

    hf4.update_docs(docs_dir=docs_dir, scorecard=scorecard)

    strict_status = "passed" if str(scorecard.get("final_status", "blocked")) == "passed" else "blocked"
    _write_text(
        reports_dir / "PRD-046.1.35-HF4_IMPLEMENTATION_REPORT.md",
        hf4.render_implementation_report(scorecard, strict_status),
    )
    _write_text(
        reports_dir / "PRD-046.1.35-HF4_BEHAVIOR_CALIBRATION_REPORT.md",
        _render_behavior_report(smoke, routing, anti, move),
    )
    _write_text(
        reports_dir / "PRD-046.1.35-HF4_TRACE_CHUNKS_DISPLAY_REPORT.md",
        _render_trace_report(chunks_gate),
    )
    _write_text(
        reports_dir / "PRD-046.1.35-HF4_NEXT_PRD_RECOMMENDATION.md",
        _render_next_prd(scorecard),
    )

    return {
        "status": scorecard.get("final_status", "blocked"),
        "decision": scorecard.get("decision", hf4.DECISION_BLOCKED_ROUTING),
        "scorecard": scorecard,
        "decision_payload": decision_payload,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.35-HF4 creator live behavior gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.35-HF4")
    parser.add_argument("--backend-base-url", default="http://localhost:8001")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--api-key", default="dev-key-001")
    parser.add_argument("--creator-user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

