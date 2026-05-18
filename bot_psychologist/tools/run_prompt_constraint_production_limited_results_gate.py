from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import prompt_constraint_production_limited_results_gate as results_gate
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.14"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_dir = Path(args.source_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))

    tracked, hash_before = results_gate.tracked_hashes(REPO_ROOT)
    preflight = results_gate.preflight(source_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        manifest = {
            "prd": PRD,
            "schema_version": "production_limited_results_manifest_v1",
            "source_execution_prd": "PRD-046.1.13",
            "source_final_status": "blocked",
            "source_decision": "stop",
            "gate_mode": "post_run_results_only",
            "new_execution_performed": False,
            "source_execution_window_count": 0,
            "source_target_user_count": 0,
            "source_production_limited_apply_count": 0,
            "provider_allowed": False,
            "production_mutation_allowed": False,
        }
        quality_summary = {
            "cases_compared": 0,
            "production_limited_apply_count": 0,
            "candidate_weaker_than_baseline_count": 0,
            "safety_regression_count": 0,
            "kb_policy_regression_count": 0,
            "prompt_bloat_regression_count": 0,
            "constraint_conflict_regression_count": 0,
            "raw_kb_text_exposure_count": 0,
            "internal_only_exposure_count": 0,
            "not_for_direct_quote_violation_count": 0,
            "provider_called_by_execution_count": 0,
            "quality_gate_passed": False,
        }
        rollback_summary = {
            "rollback_cases_total": 0,
            "rollback_cases_passed": 0,
            "rollback_failure_count": 1,
            "stale_apply_after_force_disabled_count": 0,
            "force_disabled_absolute_priority": False,
            "allowlisted_target_apply_after_rollback": 0,
            "rollback_gate_passed": False,
        }
        normal_user_summary = {
            "normal_user_cases_total": 0,
            "normal_user_apply_count": 0,
            "default_off_user_path_effect_count": 0,
            "normal_user_prompt_changed_by_pilot_count": 0,
            "normal_user_final_answer_changed_by_pilot_count": 0,
            "normal_user_gate_passed": False,
        }
        trace_summary = {
            "trace_samples_checked": 0,
            "raw_prompt_saved_count": 0,
            "raw_kb_text_saved_count": 0,
            "private_user_text_saved_count": 0,
            "secret_like_value_count": 0,
            "provider_payload_dump_count": 0,
            "trace_sanitization_failed": False,
            "trace_sanitization_gate_passed": False,
        }
        risk_register = {
            "risks": results_gate.build_default_risk_register(),
            "risk_register_has_blockers": False,
            "blocking_risk_count": 0,
        }
        decision_gate = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "source_execution_gate_passed": False,
            "quality_gate_passed": False,
            "rollback_gate_passed": False,
            "normal_user_gate_passed": False,
            "trace_sanitization_gate_passed": False,
            "risk_register_has_blockers": False,
            "new_execution_performed": False,
            "provider_called_by_results_gate": False,
            "production_mutation_detected": False,
            "artifact_encoding_hygiene_passed": False,
            "recommended_next_prd": "PRD-046.1.14-HF1 - Production-Limited Results Gate Hotfix v1",
            "blockers": blockers,
            "warnings": [],
        }
        decision_payload = {
            "schema_version": "prompt_constraint_production_limited_results_decision_v1",
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "blockers": blockers,
            "warnings": [],
            "recommended_next_prd": "PRD-046.1.14-HF1 - Production-Limited Results Gate Hotfix v1",
        }
        run_payload = {
            "schema_version": "prompt_constraint_production_limited_results_gate_v1",
            "prd": PRD,
            "source_execution_prd": "PRD-046.1.13",
            "gate_mode": "post_run_results_only",
            "new_execution_performed": False,
            "source_evidence": {},
            "quality_summary": quality_summary,
            "rollback_summary": rollback_summary,
            "normal_user_summary": normal_user_summary,
            "trace_sanitization_summary": trace_summary,
            "post_run_risk_register": risk_register,
            "decision": "stop",
        }
    else:
        (
            manifest,
            quality_summary,
            rollback_summary,
            normal_user_summary,
            trace_summary,
            risk_register,
            decision_gate,
            decision_payload,
            run_payload,
        ) = results_gate.execute_results_gate(strict=strict, parsed=preflight["parsed"])

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = results_gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    production_mutation_detected = any(
        bool(no_mutation.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )

    decision_gate["production_mutation_detected"] = production_mutation_detected
    if production_mutation_detected:
        decision_gate["final_status"] = "blocked"
        decision_gate["decision"] = "stop"
        decision_gate.setdefault("blockers", []).append("production_mutation_detected")

    _write_json(out_dir / "production_limited_results_manifest.json", manifest)
    _write_json(out_dir / "production_limited_quality_summary.json", quality_summary)
    _write_json(out_dir / "production_limited_rollback_summary.json", rollback_summary)
    _write_json(out_dir / "production_limited_normal_user_summary.json", normal_user_summary)
    _write_json(out_dir / "production_limited_trace_sanitization_summary.json", trace_summary)
    _write_json(out_dir / "production_limited_post_run_risk_register.json", risk_register)
    _write_json(out_dir / "production_limited_results_decision_gate.json", decision_gate)
    _write_json(out_dir / "production_limited_results_gate_run.json", run_payload)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(out_dir),
            reports_dir=str((REPO_ROOT / "TO_DO_LIST" / "reports").resolve()),
            out_dir=str(out_dir),
            report_prd=PRD,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )

    decision_gate["artifact_encoding_hygiene_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    if not decision_gate["artifact_encoding_hygiene_passed"]:
        decision_gate["final_status"] = "blocked"
        decision_gate["decision"] = "stop"
        decision_gate.setdefault("blockers", []).append("artifact_encoding_hygiene_failed")
    _write_json(out_dir / "production_limited_results_decision_gate.json", decision_gate)

    return {
        "status": decision_gate["final_status"],
        "decision": decision_gate["decision"],
        "decision_gate": decision_gate,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run production-limited post-run results gate for PRD-046.1.14.")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.13")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.14")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
