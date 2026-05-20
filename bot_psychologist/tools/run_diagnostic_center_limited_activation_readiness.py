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

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.33"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_logs_dir = Path(args.source_logs_dir).resolve()
    source_reports_dir = Path(args.source_reports_dir).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = gate.tracked_hashes(repo_root)
    preflight = gate.preflight_source(source_logs_dir, source_reports_dir)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001

    source_no_mutation = preflight.get("parsed", {}).get("no_mutation_proof", {})
    no_mutation_proof = gate.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        source_no_mutation=source_no_mutation if isinstance(source_no_mutation, dict) else {},
    )

    project_state_text = (docs_dir / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap_text = (docs_dir / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index_text = (docs_dir / "PRD_INDEX.md").read_text(encoding="utf-8")
    decisions_text = (docs_dir / "DECISIONS.md").read_text(encoding="utf-8")
    docs_consistency_gate = gate.build_docs_consistency_gate(
        project_state_text=project_state_text,
        roadmap_text=roadmap_text,
        prd_index_text=prd_index_text,
        decisions_text=decisions_text,
    )

    live_probe = gate.probe_live_dependencies(args.admin_base_url)
    trace_scan_paths = list(source_logs_dir.glob("*")) + list(source_reports_dir.glob("PRD-046.1.32*")) + list(out_dir.glob("*"))

    preliminary = gate.execute_readiness_gate(
        preflight=preflight,
        live_probe=live_probe,
        strict=bool(args.strict),
        allow_offline_skip=bool(args.allow_offline_skip),
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=False,
        docs_consistency_gate=docs_consistency_gate,
        trace_scan_paths=trace_scan_paths,
    )

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.33 runner executed.\n", encoding="utf-8")

    _write_json(out_dir / "source_gate.json", preliminary["source_gate"])
    _write_json(out_dir / "live_dependency_gate.json", preliminary["live_dependency_gate"])
    _write_json(out_dir / "runtime_boundary_gate.json", preliminary["runtime_boundary_gate"])
    _write_json(out_dir / "normal_user_boundary_gate.json", preliminary["normal_user_boundary_gate"])
    _write_json(out_dir / "allowlist_policy_gate.json", preliminary["allowlist_policy_gate"])
    _write_json(out_dir / "rollback_hard_stop_gate.json", preliminary["rollback_hard_stop_gate"])
    _write_json(out_dir / "safety_kb_boundary_gate.json", preliminary["safety_kb_boundary_gate"])
    _write_json(out_dir / "trace_provider_sanitization_gate.json", preliminary["trace_provider_sanitization_gate"])
    _write_json(out_dir / "runtime_defaults_gate.json", preliminary["runtime_defaults_gate"])
    _write_json(out_dir / "provider_budget_policy_gate.json", preliminary["provider_budget_policy_gate"])
    _write_json(out_dir / "no_mutation_proof.json", preliminary["no_mutation_proof"])
    _write_json(out_dir / "docs_consistency_gate.json", preliminary["docs_consistency_gate"])

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(out_dir),
            reports_dir=str(source_reports_dir),
            out_dir=str(out_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    artifact_encoding_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"

    final_payload = gate.execute_readiness_gate(
        preflight=preflight,
        live_probe=live_probe,
        strict=bool(args.strict),
        allow_offline_skip=bool(args.allow_offline_skip),
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        docs_consistency_gate=docs_consistency_gate,
        trace_scan_paths=trace_scan_paths,
    )
    _write_json(out_dir / "source_gate.json", final_payload["source_gate"])
    _write_json(out_dir / "live_dependency_gate.json", final_payload["live_dependency_gate"])
    _write_json(out_dir / "runtime_boundary_gate.json", final_payload["runtime_boundary_gate"])
    _write_json(out_dir / "normal_user_boundary_gate.json", final_payload["normal_user_boundary_gate"])
    _write_json(out_dir / "allowlist_policy_gate.json", final_payload["allowlist_policy_gate"])
    _write_json(out_dir / "rollback_hard_stop_gate.json", final_payload["rollback_hard_stop_gate"])
    _write_json(out_dir / "safety_kb_boundary_gate.json", final_payload["safety_kb_boundary_gate"])
    _write_json(out_dir / "trace_provider_sanitization_gate.json", final_payload["trace_provider_sanitization_gate"])
    _write_json(out_dir / "runtime_defaults_gate.json", final_payload["runtime_defaults_gate"])
    _write_json(out_dir / "provider_budget_policy_gate.json", final_payload["provider_budget_policy_gate"])
    _write_json(out_dir / "no_mutation_proof.json", final_payload["no_mutation_proof"])
    _write_json(out_dir / "docs_consistency_gate.json", final_payload["docs_consistency_gate"])
    _write_json(out_dir / "readiness_scorecard.json", final_payload["readiness_scorecard"])

    return {
        "status": str(final_payload["readiness_scorecard"].get("final_status", "failed")),
        "decision": str(final_payload["readiness_scorecard"].get("decision", "stop_runtime_activation_path")),
        "scorecard": final_payload["readiness_scorecard"],
        "decision_payload": final_payload["decision"],
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.33 limited activation readiness gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-logs-dir", default="TO_DO_LIST/logs/PRD-046.1.32")
    parser.add_argument("--source-reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.33")
    parser.add_argument("--admin-base-url", default="http://localhost:8003")
    parser.add_argument("--allow-offline-skip", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
