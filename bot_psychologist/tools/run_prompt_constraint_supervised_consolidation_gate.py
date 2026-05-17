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

from bot_agent.multiagent import prompt_constraint_supervised_consolidation as consolidation
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.11"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_a_dir = Path(args.source_a_dir).resolve()
    source_b_dir = Path(args.source_b_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    strict = bool(getattr(args, "strict", False))

    tracked, hash_before = consolidation.tracked_hashes(REPO_ROOT)
    preflight = consolidation.preflight(source_a_dir, source_b_dir)

    if not preflight["ok"]:
        blockers = list(preflight["missing"]) + list(preflight["parse_errors"])
        manifest = {
            "prd": PRD,
            "schema_version": "prompt_constraint_supervised_consolidation_manifest_v1",
            "source_cycles": [],
            "consolidation_mode": "evidence_only_no_execution",
            "provider_allowed": False,
            "production_mutation_allowed": False,
            "source_cycles_passed": False,
        }
        aggregate = {
            "schema_version": "prompt_constraint_supervised_consolidation_aggregate_metrics_v1",
            "prd": PRD,
            "cycles_total": 2,
            "cycles_passed": 0,
            "total_test_apply_applied_count": 0,
            "total_cases_compared": 0,
            "max_cohort_size_seen": 0,
            "normal_user_apply_total": 0,
            "default_off_user_path_effect_total": 0,
            "rollback_failure_total": 1,
            "stale_apply_after_force_disabled_total": 0,
            "candidate_weaker_than_baseline_total": 0,
            "safety_regression_total": 0,
            "kb_policy_regression_total": 0,
            "prompt_bloat_regression_total": 0,
            "constraint_conflict_regression_total": 0,
            "raw_kb_text_exposure_total": 0,
            "internal_only_exposure_total": 0,
            "not_for_direct_quote_violation_total": 0,
            "provider_called_total": 0,
            "production_mutation_detected_any": False,
            "artifact_encoding_hygiene_all_passed": False,
        }
        reproducibility = {
            "schema_version": "prompt_constraint_supervised_consolidation_reproducibility_v1",
            "prd": PRD,
            "both_cycles_passed": False,
            "both_cycles_continue_supervised": False,
            "normal_user_no_effect_repeated": False,
            "rollback_success_repeated": False,
            "no_safety_regression_repeated": False,
            "no_kb_regression_repeated": False,
            "no_prompt_bloat_repeated": False,
            "no_constraint_conflict_repeated": False,
            "no_raw_kb_exposure_repeated": False,
            "provider_free_repeated": False,
            "no_mutation_repeated": False,
            "reproducibility_passed": False,
        }
        risk_register = {
            "schema_version": "prompt_constraint_supervised_consolidation_risk_register_v1",
            "prd": PRD,
            "risks": [],
            "blocking_risk_count": 1,
            "risk_register_has_blockers": True,
        }
        decision_gate = {
            "schema_version": "prompt_constraint_supervised_consolidation_rollout_decision_gate_v1",
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "source_cycles_passed": False,
            "aggregate_metrics_passed": False,
            "reproducibility_passed": False,
            "risk_register_has_blockers": True,
            "normal_user_apply_total": 0,
            "rollback_failure_total": 1,
            "safety_regression_total": 0,
            "kb_policy_regression_total": 0,
            "raw_kb_text_exposure_total": 0,
            "provider_called_total": 0,
            "production_mutation_detected_any": False,
            "recommended_next_prd": "PRD-046.1.11-HF1 - Supervised Consolidation Gate Hotfix v1",
            "blockers": blockers,
            "warnings": [],
        }
        decision_payload = {
            "schema_version": "prompt_constraint_supervised_consolidation_decision_v1",
            "prd": PRD,
            "final_status": "blocked",
            "decision": "stop",
            "blockers": blockers,
            "warnings": [],
            "recommended_next_prd": "PRD-046.1.11-HF1 - Supervised Consolidation Gate Hotfix v1",
        }
        run_payload = {
            "schema_version": "prompt_constraint_supervised_consolidation_v1",
            "prd": PRD,
            "source_cycles": [],
            "aggregate_metrics": aggregate,
            "reproducibility": reproducibility,
            "risk_register": risk_register,
            "decision_gate": decision_gate,
            "decision": decision_gate["decision"],
        }
    else:
        (
            manifest,
            aggregate,
            reproducibility,
            risk_register,
            decision_gate,
            decision_payload,
            run_payload,
        ) = consolidation.execute_consolidation(strict=strict, parsed=preflight["parsed"])

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    no_mutation = consolidation.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    production_mutation_detected = any(
        bool(no_mutation.get(name, False))
        for name in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )
    aggregate["production_mutation_detected_any"] = production_mutation_detected
    decision_gate["production_mutation_detected_any"] = production_mutation_detected

    if production_mutation_detected:
        decision_gate["final_status"] = "blocked"
        decision_gate["decision"] = "stop"
        decision_gate.setdefault("blockers", []).append("production_mutation_detected")

    _write_json(out_dir / "supervised_consolidation_manifest.json", manifest)
    _write_json(out_dir / "supervised_consolidation_aggregate_metrics.json", aggregate)
    _write_json(out_dir / "supervised_consolidation_reproducibility.json", reproducibility)
    _write_json(out_dir / "supervised_consolidation_risk_register.json", risk_register)
    _write_json(out_dir / "supervised_consolidation_rollout_decision_gate.json", decision_gate)
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

    aggregate["artifact_encoding_hygiene_all_passed"] = str(encoding_report.get("final_status", "failed")) == "passed"
    if not aggregate["artifact_encoding_hygiene_all_passed"]:
        decision_gate["final_status"] = "blocked"
        decision_gate["decision"] = "stop"
        decision_gate.setdefault("blockers", []).append("artifact_encoding_hygiene_failed")

    _write_json(out_dir / "supervised_consolidation_aggregate_metrics.json", aggregate)
    _write_json(out_dir / "supervised_consolidation_rollout_decision_gate.json", decision_gate)

    return {
        "status": decision_gate["final_status"],
        "decision": decision_gate["decision"],
        "manifest": manifest,
        "aggregate": aggregate,
        "reproducibility": reproducibility,
        "risk_register": risk_register,
        "decision_gate": decision_gate,
        "decision_payload": decision_payload,
        "run": run_payload,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run supervised consolidation decision gate for PRD-046.1.11.")
    parser.add_argument("--source-a-dir", default="TO_DO_LIST/logs/PRD-046.1.9")
    parser.add_argument("--source-b-dir", default="TO_DO_LIST/logs/PRD-046.1.10")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.11")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
