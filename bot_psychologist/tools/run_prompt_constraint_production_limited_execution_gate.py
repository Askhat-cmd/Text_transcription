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

from bot_agent.multiagent import prompt_constraint_production_limited_execution as execution_gate
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.13"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = Path(args.plan_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))
    operator_user_id = (getattr(args, "operator_user_id", None) or "").strip() or None

    tracked, hash_before = execution_gate.tracked_hashes(REPO_ROOT)
    preflight = execution_gate.preflight(plan_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        manifest = {
            "schema_version": "prompt_constraint_production_limited_execution_v1",
            "prd": PRD,
            "source_plan_prd": "PRD-046.1.12",
            "source_plan_status": "missing",
            "source_plan_decision": "blocked",
            "execution_mode": "production_limited_controlled_window",
            "execution_window_count": 0,
            "automatic_background_execution": False,
            "target_user_count": 0,
            "real_user_count": 0,
            "synthetic_operator_user_count": 0,
            "target_user_id": "",
            "normal_control_user_count": 0,
            "provider_allowed": False,
            "production_mutation_allowed": False,
            "decision": "stop",
        }
        preflight_result = {
            "source_plan_gate_passed": False,
            "operator_checklist_complete": False,
            "monitoring_plan_ready": False,
            "rollback_plan_ready": False,
            "abort_criteria_ready": False,
            "allowlist_ready": False,
            "target_user_count_allowed": False,
            "normal_user_controls_ready": False,
            "config_defaults_conservative": False,
            "force_disabled_available": False,
            "preflight_passed": False,
        }
        trace_payload = {
            "schema_version": "prompt_constraint_production_limited_trace_samples_v1",
            "prd": PRD,
            "samples": [],
        }
        baseline_vs = {
            "schema_version": "prompt_constraint_production_limited_baseline_vs_test_apply_v1",
            "prd": PRD,
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
        }
        normal_no_effect = {
            "schema_version": "prompt_constraint_production_limited_normal_user_no_effect_v1",
            "prd": PRD,
            "normal_user_cases_total": 0,
            "normal_user_apply_count": 0,
            "normal_user_prompt_changed_by_pilot_count": 0,
            "normal_user_final_answer_changed_by_pilot_count": 0,
            "default_off_user_path_effect_count": 0,
        }
        rollback = {
            "schema_version": "prompt_constraint_production_limited_rollback_proof_v1",
            "prd": PRD,
            "rollback_cases_total": 0,
            "rollback_cases_passed": 0,
            "rollback_failure_count": 1,
            "stale_apply_after_force_disabled_count": 0,
            "force_disabled_absolute_priority": False,
            "allowlisted_target_apply_after_rollback": 0,
        }
        scorecard = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "source_plan_gate_passed": False,
            "execution_window_count": 0,
            "target_user_count": 0,
            "target_user_limit_respected": False,
            "production_limited_apply_count": 0,
            "normal_user_apply_count": 0,
            "default_off_user_path_effect_count": 0,
            "rollback_failure_count": 1,
            "stale_apply_after_force_disabled_count": 0,
            "candidate_weaker_than_baseline_count": 0,
            "safety_regression_count": 0,
            "kb_policy_regression_count": 0,
            "prompt_bloat_regression_count": 0,
            "constraint_conflict_regression_count": 0,
            "raw_kb_text_exposure_count": 0,
            "internal_only_exposure_count": 0,
            "not_for_direct_quote_violation_count": 0,
            "provider_called_by_execution_count": 0,
            "trace_sanitization_failed": False,
            "production_mutation_detected": False,
            "artifact_encoding_hygiene_passed": False,
            "recommended_next_prd": "PRD-046.1.13-HF1 - Production-Limited Execution Gate Hotfix v1",
            "blockers": blockers,
            "warnings": [],
        }
        decision_payload = {
            "schema_version": "prompt_constraint_production_limited_execution_decision_v1",
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "blockers": blockers,
            "warnings": [],
            "recommended_next_prd": "PRD-046.1.13-HF1 - Production-Limited Execution Gate Hotfix v1",
        }
    else:
        (
            manifest,
            preflight_result,
            trace_payload,
            baseline_vs,
            normal_no_effect,
            rollback,
            scorecard,
            decision_payload,
        ) = execution_gate.execute_gate(strict=strict, parsed=preflight["parsed"], operator_user_id=operator_user_id)

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = execution_gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    production_mutation_detected = any(
        bool(no_mutation.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )

    scorecard["production_mutation_detected"] = production_mutation_detected
    if production_mutation_detected:
        scorecard["final_status"] = "blocked"
        scorecard["decision"] = "stop"
        scorecard.setdefault("blockers", []).append("production_mutation_detected")

    _write_json(out_dir / "production_limited_execution_manifest.json", manifest)
    _write_json(out_dir / "production_limited_preflight_result.json", preflight_result)
    _write_json(out_dir / "production_limited_trace_samples.json", trace_payload)
    _write_json(out_dir / "production_limited_baseline_vs_test_apply.json", baseline_vs)
    _write_json(out_dir / "production_limited_normal_user_no_effect.json", normal_no_effect)
    _write_json(out_dir / "production_limited_rollback_proof.json", rollback)
    _write_json(out_dir / "production_limited_monitoring_scorecard.json", scorecard)
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

    scorecard["artifact_encoding_hygiene_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    if not scorecard["artifact_encoding_hygiene_passed"]:
        scorecard["final_status"] = "blocked"
        scorecard["decision"] = "stop"
        scorecard.setdefault("blockers", []).append("artifact_encoding_hygiene_failed")
    _write_json(out_dir / "production_limited_monitoring_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run production-limited execution monitoring gate for PRD-046.1.13.")
    parser.add_argument("--plan-dir", default="TO_DO_LIST/logs/PRD-046.1.12")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.13")
    parser.add_argument("--operator-user-id", default=None)
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
