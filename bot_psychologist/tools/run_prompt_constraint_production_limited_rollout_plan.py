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

from bot_agent.multiagent import prompt_constraint_production_limited_rollout_plan as planner
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.12"


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

    tracked, hash_before = planner.tracked_hashes(REPO_ROOT)
    preflight = planner.preflight(source_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        rollout_plan = {
            "schema_version": "prompt_constraint_production_limited_rollout_plan_v1",
            "prd": PRD,
            "source_consolidation_prd": "PRD-046.1.11",
            "source_decision": "unknown",
            "rollout_stage": "plan_only",
            "production_execution_performed": False,
            "baseline_defaults": {
                "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
                "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
            },
            "cohort_policy": {},
            "preflight_gates": {},
            "operator_checklist": {},
            "monitoring_plan": {},
            "rollback_plan": {},
            "abort_criteria": {},
            "decision": "blocked",
        }
        cohort_policy = {
            "stage": "production_limited_plan_only",
            "execution_allowed_in_this_prd": False,
            "max_initial_real_user_count": 1,
            "max_total_users_in_first_execution_prd": 2,
            "allowlist_required": True,
            "manual_operator_approval_required": True,
            "automatic_enrollment_allowed": False,
            "normal_user_default_path_unchanged": True,
            "excluded_user_categories": [],
        }
        preflight_gates = {"required_before_execution": {}, "blocked_if": ["source_consolidation_missing"]}
        operator_checklist = {"checklist": []}
        monitoring_plan = {"metrics": {}, "trace_requirements": {}, "observation_window": {}}
        rollback_plan = {"rollback_priority": "force_disabled_absolute_priority"}
        abort_criteria = {"hard_abort_if": [], "warning_if": []}
        readiness_gate = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "blocked",
            "source_consolidation_passed": False,
            "source_decision": "unknown",
            "rollout_plan_ready": False,
            "cohort_policy_ready": False,
            "preflight_gates_ready": False,
            "operator_checklist_ready": False,
            "monitoring_plan_ready": False,
            "rollback_plan_ready": False,
            "abort_criteria_ready": False,
            "execution_performed": False,
            "provider_called_by_plan": False,
            "production_mutation_detected": False,
            "default_flags_changed": False,
            "recommended_next_prd": "PRD-046.1.12-BLOCKER - Production-Limited Rollout Planning Blocker Resolution v1",
            "blockers": blockers,
            "warnings": [],
        }
        decision_payload = {
            "schema_version": "prompt_constraint_production_limited_rollout_decision_v1",
            "prd": PRD,
            "final_status": "blocked",
            "decision": "blocked",
            "blockers": blockers,
            "warnings": [],
            "recommended_next_prd": "PRD-046.1.12-BLOCKER - Production-Limited Rollout Planning Blocker Resolution v1",
        }
        runbook = "# PRD-046.1.12 Production-Limited Operator Runbook\n\nSource artifacts missing.\n"
    else:
        (
            rollout_plan,
            cohort_policy,
            preflight_gates,
            operator_checklist,
            monitoring_plan,
            rollback_plan,
            abort_criteria,
            readiness_gate,
            decision_payload,
            runbook,
        ) = planner.execute_rollout_plan(strict=strict, parsed=preflight["parsed"])

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = planner.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    production_mutation_detected = any(
        bool(no_mutation.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )

    readiness_gate["production_mutation_detected"] = production_mutation_detected
    if production_mutation_detected:
        readiness_gate["final_status"] = "blocked"
        readiness_gate["decision"] = "blocked"
        readiness_gate.setdefault("blockers", []).append("production_mutation_detected")

    _write_json(out_dir / "production_limited_rollout_plan.json", rollout_plan)
    _write_json(out_dir / "production_limited_cohort_policy.json", cohort_policy)
    _write_json(out_dir / "production_limited_preflight_gates.json", preflight_gates)
    _write_json(out_dir / "production_limited_operator_checklist.json", operator_checklist)
    _write_json(out_dir / "production_limited_monitoring_plan.json", monitoring_plan)
    _write_json(out_dir / "production_limited_rollback_plan.json", rollback_plan)
    _write_json(out_dir / "production_limited_abort_criteria.json", abort_criteria)
    _write_json(out_dir / "production_limited_readiness_gate.json", readiness_gate)
    (out_dir / "production_limited_operator_runbook.md").write_text(runbook, encoding="utf-8")
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
    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    if not artifact_hygiene_passed:
        readiness_gate["final_status"] = "blocked"
        readiness_gate["decision"] = "blocked"
        readiness_gate.setdefault("blockers", []).append("artifact_encoding_hygiene_failed")
        _write_json(out_dir / "production_limited_readiness_gate.json", readiness_gate)

    return {
        "status": readiness_gate["final_status"],
        "decision": readiness_gate["decision"],
        "readiness_gate": readiness_gate,
        "decision_payload": decision_payload,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run production-limited rollout planning gate for PRD-046.1.12.")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.11")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.12")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
