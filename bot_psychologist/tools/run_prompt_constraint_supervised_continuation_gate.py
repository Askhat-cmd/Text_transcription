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

from bot_agent.multiagent import prompt_constraint_supervised_continuation as continuation
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.10"


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

    tracked, hash_before = continuation.tracked_hashes(REPO_ROOT)
    preflight = continuation.preflight(source_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        manifest = {
            "schema_version": "prompt_constraint_supervised_continuation_v1",
            "prd": PRD,
            "source_execution_prd": "PRD-046.1.9",
            "source_execution_decision": "unknown",
            "source_final_status": "missing",
            "source_execution_gate_passed": False,
            "execution_mode": "controlled_harness_expanded_eval",
            "cohort": {
                "max_size": 6,
                "actual_size": 0,
                "normal_users_included": False,
                "user_ids": [],
                "all_user_ids_allowlisted_or_test_prefix": True,
            },
            "scenario_coverage": {
                "required_scenarios": [],
                "covered_scenarios_count": 0,
                "missing_scenarios": [],
                "coverage_passed": False,
            },
            "baseline_defaults_preserved": True,
            "results": {},
            "decision": "stop",
        }
        scenario_coverage = {
            "required_scenarios": [],
            "covered_scenarios_count": 0,
            "missing_scenarios": [],
            "coverage_passed": False,
        }
        trace_payload = {"schema_version": "prompt_constraint_supervised_continuation_trace_v1", "prd": PRD, "samples": []}
        comparison = {
            "schema_version": "prompt_constraint_supervised_continuation_comparison_v1",
            "prd": PRD,
            "cases_compared": 0,
            "test_apply_applied_count": 0,
            "candidate_weaker_than_baseline_count": 0,
            "safety_regression_count": 0,
            "kb_policy_regression_count": 0,
            "prompt_bloat_regression_count": 0,
            "constraint_conflict_regression_count": 0,
            "raw_kb_text_exposure_count": 0,
            "internal_only_exposure_count": 0,
            "not_for_direct_quote_violation_count": 0,
            "provider_called_by_continuation_count": 0,
        }
        normal_no_effect = {
            "schema_version": "prompt_constraint_supervised_continuation_normal_user_no_effect_v1",
            "prd": PRD,
            "normal_user_cases_total": 0,
            "normal_user_apply_count": 0,
            "normal_user_prompt_changed_by_pilot_count": 0,
            "normal_user_final_answer_changed_by_pilot_count": 0,
            "default_off_user_path_effect_count": 0,
        }
        rollback = {
            "schema_version": "prompt_constraint_supervised_continuation_rollback_v1",
            "prd": PRD,
            "rollback_cases_total": 0,
            "rollback_cases_passed": 0,
            "rollback_failure_count": 1,
            "stale_apply_after_force_disabled_count": 0,
            "force_disabled_absolute_priority": False,
        }
        scorecard = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "source_execution_gate_passed": False,
            "cohort_size": 0,
            "cohort_limit_respected": True,
            "scenario_coverage_passed": False,
            "test_apply_applied_count": 0,
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
            "provider_called_by_continuation_count": 0,
            "allowlist_violation_count": 0,
            "production_mutation_detected": False,
            "artifact_encoding_hygiene_passed": False,
            "recommended_next_prd": "PRD-046.1.10-HF1 - Supervised Continuation Gate Hotfix v1",
            "blockers": blockers,
            "warnings": [],
        }
    else:
        (
            manifest,
            scenario_coverage,
            trace_payload,
            comparison,
            normal_no_effect,
            rollback,
            scorecard,
            _decision,
        ) = continuation.execute_continuation(strict=strict, parsed=preflight["parsed"])

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = continuation.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    production_mutation_detected = any(
        bool(no_mutation.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )
    scorecard["production_mutation_detected"] = production_mutation_detected
    if production_mutation_detected:
        scorecard["final_status"] = "blocked"
        scorecard["decision"] = "stop"
        scorecard.setdefault("blockers", []).append("production_mutation_detected")

    _write_json(out_dir / "supervised_continuation_manifest.json", manifest)
    _write_json(out_dir / "supervised_continuation_scenario_coverage.json", scenario_coverage)
    _write_json(out_dir / "supervised_continuation_trace_samples.json", trace_payload)
    _write_json(out_dir / "supervised_continuation_baseline_vs_test_apply.json", comparison)
    _write_json(out_dir / "supervised_continuation_normal_user_no_effect.json", normal_no_effect)
    _write_json(out_dir / "supervised_continuation_rollback_proof.json", rollback)
    _write_json(out_dir / "supervised_continuation_observability_scorecard.json", scorecard)
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
    _write_json(out_dir / "supervised_continuation_observability_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run supervised continuation observability gate for PRD-046.1.10.")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.9")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.10")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
