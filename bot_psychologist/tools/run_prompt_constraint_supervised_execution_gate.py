from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import prompt_constraint_supervised_execution as execution
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.9"
SOURCE_PRD = "PRD-046.1.8"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = Path(args.plan_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))

    tracked, hash_before = execution.tracked_hashes(REPO_ROOT)
    preflight = execution.preflight(plan_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        manifest = {
            "schema_version": "prompt_constraint_supervised_execution_v1",
            "prd": PRD,
            "execution_mode": "controlled_harness",
            "source_plan_prd": SOURCE_PRD,
            "source_plan_status": "missing",
            "source_plan_decision": "missing",
            "cohort": {
                "size": 0,
                "user_ids": [],
                "max_size_allowed": 3,
                "normal_users_included": False,
            },
            "baseline_defaults_preserved": True,
            "supervised_run": {
                "enabled": True,
                "force_disabled": False,
                "mode": "test_apply",
                "allowlisted_only": True,
            },
            "rollback_run": {
                "enabled": True,
                "force_disabled": True,
                "mode": "test_apply",
            },
            "results": {},
            "decision": "stop",
            "runtime_flag_scenarios": [
                "baseline_default_off",
                "supervised_test_apply",
                "normal_user_control",
                "rollback_force_disabled",
            ],
            "provider_allowed": False,
            "production_mutation_allowed": False,
        }
        trace_payload = {
            "schema_version": "prompt_constraint_supervised_execution_trace_v1",
            "prd": PRD,
            "samples": [],
        }
        comparison = {
            "schema_version": "prompt_constraint_supervised_execution_comparison_v1",
            "prd": PRD,
            "cases_compared": 0,
            "test_apply_applied_count": 0,
            "candidate_weaker_than_baseline_count": 0,
            "safety_regression_count": 0,
            "kb_policy_regression_count": 0,
            "prompt_bloat_regression_count": 0,
            "constraint_conflict_regression_count": 0,
            "raw_kb_text_exposure_count": 0,
            "provider_called_by_execution_count": 0,
        }
        normal_proof = {
            "schema_version": "prompt_constraint_supervised_execution_normal_user_no_effect_v1",
            "prd": PRD,
            "normal_user_cases_total": 0,
            "normal_user_apply_count": 0,
            "normal_user_prompt_changed_by_pilot_count": 0,
            "normal_user_final_answer_changed_by_pilot_count": 0,
            "normal_user_trace_only_or_disabled": True,
        }
        rollback_proof = {
            "schema_version": "prompt_constraint_supervised_execution_rollback_proof_v1",
            "prd": PRD,
            "rollback_cases_total": 0,
            "rollback_cases_passed": 0,
            "rollback_failure_count": 1,
            "stale_apply_after_force_disabled_count": 0,
            "force_disabled_absolute_priority": False,
            "rollback_restores_no_apply": False,
        }
        scorecard = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "source_plan_gate_passed": False,
            "cohort_size": 0,
            "cohort_limit_respected": True,
            "test_apply_applied_count": 0,
            "normal_user_apply_count": 0,
            "rollback_failure_count": 1,
            "safety_regression_count": 0,
            "kb_policy_regression_count": 0,
            "prompt_bloat_regression_count": 0,
            "constraint_conflict_regression_count": 0,
            "candidate_weaker_than_baseline_count": 0,
            "raw_kb_text_exposure_count": 0,
            "provider_called_by_execution_count": 0,
            "allowlist_violation_count": 0,
            "stale_apply_after_force_disabled_count": 0,
            "production_mutation_detected": False,
            "artifact_encoding_hygiene_passed": False,
            "recommended_next_prd": "PRD-046.1.9-HF1 - Supervised Execution Gate Hotfix v1",
            "blockers": blockers,
            "warnings": [],
        }
    else:
        (
            manifest,
            trace_payload,
            comparison,
            normal_proof,
            rollback_proof,
            scorecard,
            _decision_payload,
        ) = execution.execute_harness(strict=strict, parsed=preflight["parsed"])

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = execution.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    production_mutation_detected = any(
        bool(no_mutation.get(key, False))
        for key in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )
    scorecard["production_mutation_detected"] = production_mutation_detected
    if production_mutation_detected:
        scorecard["final_status"] = "blocked"
        scorecard["decision"] = "stop"
        scorecard.setdefault("blockers", []).append("production_mutation_detected")

    _write_json(out_dir / "supervised_execution_manifest.json", manifest)
    _write_json(out_dir / "supervised_execution_trace_samples.json", trace_payload)
    _write_json(out_dir / "supervised_execution_baseline_vs_test_apply.json", comparison)
    _write_json(out_dir / "supervised_execution_normal_user_no_effect.json", normal_proof)
    _write_json(out_dir / "supervised_execution_rollback_proof.json", rollback_proof)
    _write_json(out_dir / "supervised_execution_observability_scorecard.json", scorecard)
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
    _write_json(out_dir / "supervised_execution_observability_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run supervised execution observability gate for PRD-046.1.9.")
    parser.add_argument("--plan-dir", default="TO_DO_LIST/logs/PRD-046.1.8")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.9")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
