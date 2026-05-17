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

from bot_agent.multiagent import prompt_constraint_supervised_rollout as rollout
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.8"
SOURCE_PRD = "PRD-046.1.7"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_operator_runbook_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# PRD-046.1.8 Supervised Rollout Operator Runbook",
        "",
        f"- PRD: `{payload.get('prd', PRD)}`",
        f"- Stage: `{payload.get('runbook_stage', 'plan_only_no_execution')}`",
        "",
        "## Steps",
    ]
    for idx, step in enumerate(payload.get("steps", []), start=1):
        lines.append(f"{idx}. {step}")
    lines.extend(
        [
            "",
            "## Rollback / Off Steps",
        ]
    )
    for idx, step in enumerate(payload.get("rollback_off_steps", []), start=1):
        lines.append(f"{idx}. {step}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))

    tracked_files, hash_before = rollout.tracked_hashes(REPO_ROOT)

    preflight = rollout.preflight(input_dir=input_dir, repo_root=REPO_ROOT)
    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        readiness = {
            "prd": PRD,
            "final_status": "blocked",
            "decision": "execution_blocked",
            "source_gate": {
                "prd_046_1_7_final_status": "missing",
                "prd_046_1_7_decision": "missing",
            },
            "default_safety": {
                "enabled_default_false": False,
                "force_disabled_default_true": False,
                "normal_user_apply_count": 0,
                "default_off_user_path_effect_count": 0,
            },
            "rollback": {
                "rollback_first_policy_preserved": False,
                "force_disabled_absolute_priority": False,
                "toggle_matrix_ready": False,
            },
            "scope": {
                "normal_users_allowed": False,
                "allowlist_required": True,
                "test_prefix_required": True,
                "max_initial_cohort_size": 3,
            },
            "quality": {
                "requires_baseline_vs_test_apply_comparison": True,
                "requires_trace_samples": True,
                "requires_no_safety_regression": True,
                "requires_no_kb_policy_regression": True,
            },
            "mutation": {
                "production_apply_performed": False,
                "config_mutated": False,
                "registry_mutated": False,
                "all_blocks_merged_mutated": False,
                "chroma_reindex_performed": False,
            },
            "blockers": blockers,
            "warnings": [],
        }
        abort_payload = {
            "schema_version": "prompt_constraint_supervised_rollout_abort_criteria_v1",
            "prd": PRD,
            "hard_abort_conditions": rollout.hard_abort_conditions(),
            "warning_conditions": rollout.warning_conditions(),
            "rollback_steps": rollout.rollback_steps(),
            "ready": False,
        }
        toggle = rollout.build_toggle_matrix()
        toggle["toggle_matrix_ready"] = False
        runbook = {
            "schema_version": "prompt_constraint_supervised_rollout_operator_runbook_v1",
            "prd": PRD,
            "runbook_stage": "plan_only_no_execution",
            "steps": [],
            "required_flags_for_future_execution": [],
            "rollback_off_steps": rollout.rollback_steps(),
            "ready": False,
        }
        decision_payload = {
            "schema_version": "prompt_constraint_supervised_rollout_decision_v1",
            "final_status": "blocked",
            "decision": "execution_blocked",
            "blockers": blockers,
            "warnings": [],
            "recommended_next_prd": "PRD-046.1.8-HF1 - Supervised Rollout Plan Gate Fix",
        }
        plan_payload = {
            "schema_version": "prompt_constraint_supervised_rollout_plan_v1",
            "prd": PRD,
            "source_prd": SOURCE_PRD,
            "rollout_stage": "plan_only",
            "baseline_defaults": {
                "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
                "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
                "PROMPT_CONSTRAINT_PILOT_MODE": "shadow|test_apply",
            },
            "allowed_scope": {
                "allowlisted_user_ids_only": True,
                "test_user_prefix_only": True,
                "max_cohort_size": 3,
                "normal_users_allowed": False,
            },
            "required_preflight_gates": [],
            "runtime_observation_requirements": [],
            "abort_criteria": abort_payload,
            "rollback_steps": rollout.rollback_steps(),
            "success_criteria": [],
            "next_decision_options": [
                "execution_blocked",
                "ready_for_supervised_execution_prd",
                "hotfix_required",
            ],
        }
    else:
        (
            plan_payload,
            readiness,
            abort_payload,
            toggle,
            runbook,
            decision_payload,
        ) = rollout.build_plan(parsed=preflight["parsed"], strict=strict)

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}
    no_mutation = rollout.build_no_mutation_proof(repo_root=REPO_ROOT, hash_before=hash_before, hash_after=hash_after)
    if any(bool(no_mutation.get(name, False)) for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")):
        readiness["final_status"] = "blocked"
        readiness["decision"] = "execution_blocked"
        readiness.setdefault("blockers", []).append("no_mutation_proof_failed")
        decision_payload["final_status"] = "blocked"
        decision_payload["decision"] = "execution_blocked"
        decision_payload.setdefault("blockers", []).append("no_mutation_proof_failed")

    _write_json(out_dir / "supervised_rollout_plan.json", plan_payload)
    _write_json(out_dir / "supervised_rollout_readiness_gate.json", readiness)
    _write_json(out_dir / "supervised_rollout_abort_criteria.json", abort_payload)
    _write_json(out_dir / "supervised_rollout_toggle_matrix.json", toggle)
    _write_json(out_dir / "supervised_rollout_operator_runbook.json", runbook)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)
    _write_operator_runbook_md(out_dir / "supervised_rollout_operator_runbook.md", runbook)

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

    status = str(readiness.get("final_status", "blocked"))
    decision = str(readiness.get("decision", "execution_blocked"))
    return {
        "status": status,
        "decision": decision,
        "readiness_gate": readiness,
        "decision_payload": decision_payload,
        "no_mutation": no_mutation,
        "encoding_report": encoding_report,
        "preflight": preflight,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build supervised rollout plan artifacts for PRD-046.1.8.")
    parser.add_argument("--input-dir", default="TO_DO_LIST/logs/PRD-046.1.7")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.8")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    status = str(result.get("status", "blocked"))
    return 0 if status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
