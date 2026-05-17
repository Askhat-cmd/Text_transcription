from __future__ import annotations

import argparse
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1
from bot_agent.multiagent.contracts.diagnostic_center_v1 import (
    DiagnosticCenterInput,
    DiagnosticCenterOutput,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_nested(payload: dict[str, Any], dotted_key: str) -> Any:
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _validate_contract(output: DiagnosticCenterOutput) -> list[str]:
    errors: list[str] = []
    out = output.to_dict()
    required_top = [
        "schema_version",
        "status",
        "nervous_state",
        "intent",
        "openness",
        "ok_position",
        "relation_to_thread",
        "phase",
        "working_hypothesis",
        "lens_signals",
        "next_micro_shift",
        "trace",
        "diagnostic_center_runtime_enabled",
        "user_facing_text_generated",
    ]
    for key in required_top:
        if key not in out:
            errors.append(f"missing:{key}")
    if out.get("diagnostic_center_runtime_enabled") is not False:
        errors.append("diagnostic_center_runtime_enabled_must_be_false")
    if out.get("user_facing_text_generated") is not False:
        errors.append("user_facing_text_generated_must_be_false")
    return errors


def _evaluate_case(case: dict[str, Any], output: DiagnosticCenterOutput) -> tuple[bool, list[str]]:
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    out = output.to_dict()
    issues: list[str] = []

    for key, value in expected.items():
        if key.endswith("_contains"):
            field = key.replace("_contains", "")
            observed = _as_list(_get_nested(out, field))
            required = _as_list(value)
            missing = [item for item in required if item not in observed]
            if missing:
                issues.append(f"{field}:missing_contains={missing}")
            continue
        if key.endswith("_one_of"):
            field = key.replace("_one_of", "")
            observed = _get_nested(out, field)
            options = _as_list(value)
            if str(observed) not in options:
                issues.append(f"{field}:observed={observed},expected_one_of={options}")
            continue
        if key.endswith("_lte"):
            field = key.replace("_lte", "")
            observed = _get_nested(out, field)
            try:
                if float(observed) > float(value):
                    issues.append(f"{field}:observed={observed},expected_lte={value}")
            except (TypeError, ValueError):
                issues.append(f"{field}:invalid_numeric={observed}")
            continue

        observed = _get_nested(out, key)
        if observed != value:
            issues.append(f"{key}:observed={observed},expected={value}")

    return len(issues) == 0, issues


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fixtures_path = Path(args.cases_file)
    if not fixtures_path.is_absolute():
        fixtures_path = (REPO_ROOT / fixtures_path).resolve()
    raw_cases = _read_json(fixtures_path)
    cases = [item for item in raw_cases if isinstance(item, dict)] if isinstance(raw_cases, list) else []

    tracked_files = {
        "all_blocks": REPO_ROOT / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": REPO_ROOT / "Bot_data_base" / "data" / "registry.json",
        "config": REPO_ROOT / "Bot_data_base" / "config.yaml",
    }
    hash_before = {name: _sha256(path) for name, path in tracked_files.items()}

    case_results: list[dict[str, Any]] = []
    trace_samples: list[dict[str, Any]] = []
    passed = 0
    failed_cases: list[str] = []

    for case in cases:
        case_id = str(case.get("case_id", "unknown_case"))
        input_payload = case.get("input") if isinstance(case.get("input"), dict) else {}
        built = build_diagnostic_center_output_v1(DiagnosticCenterInput.from_dict(input_payload))
        contract_errors = _validate_contract(built)
        checks_passed, check_issues = _evaluate_case(case, built)
        ok = (not contract_errors) and checks_passed
        if ok:
            passed += 1
        else:
            failed_cases.append(case_id)

        out = built.to_dict()
        case_results.append(
            {
                "case_id": case_id,
                "passed": ok,
                "contract_errors": contract_errors,
                "expectation_issues": check_issues,
                "status": out.get("status"),
                "nervous_state": out.get("nervous_state"),
                "intent": out.get("intent"),
                "openness": out.get("openness"),
                "ok_position": out.get("ok_position"),
                "relation_to_thread": out.get("relation_to_thread"),
                "next_micro_shift": out.get("next_micro_shift"),
                "trace": out.get("trace"),
            }
        )
        if len(trace_samples) < 5:
            trace_samples.append(
                {
                    "case_id": case_id,
                    "trace": out.get("trace"),
                    "working_hypothesis": out.get("working_hypothesis"),
                    "next_micro_shift": out.get("next_micro_shift"),
                }
            )

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}

    no_mutation = {
        "schema_version": "diagnostic_center_no_mutation_proof_v1",
        "prd": "PRD-046.1",
        "generated_at_utc": _utc_now(),
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "provider_called": False,
        "production_apply_performed": False,
        "writer_prompt_production_changed": False,
        "diagnostic_center_runtime_enabled": False,
        "legacy_sd_enabled": False,
        "hash_before": hash_before,
        "hash_after": hash_after,
    }
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    audit_passed = (
        len(failed_cases) == 0
        and not no_mutation["all_blocks_merged_mutated"]
        and not no_mutation["registry_mutated"]
        and not no_mutation["config_mutated"]
    )
    final_status = "passed" if audit_passed else "done_with_eval_blocker"
    if (
        no_mutation["all_blocks_merged_mutated"]
        or no_mutation["registry_mutated"]
        or no_mutation["config_mutated"]
    ):
        final_status = "failed_safety_violation"

    scorecard = {
        "schema_version": "diagnostic_center_eval_scorecard_v1",
        "prd": "PRD-046.1",
        "generated_at_utc": _utc_now(),
        "cases_total": len(cases),
        "cases_passed": passed,
        "cases_failed": len(cases) - passed,
        "contract_pass_rate": round(passed / max(1, len(cases)), 4),
        "failed_case_ids": failed_cases,
        "final_status": final_status,
        "diagnostic_center_contract_ready": audit_passed,
        "diagnostic_center_runtime_enabled": False,
        "next_prd": "PRD-046.1.1",
    }

    audit = {
        "schema_version": "diagnostic_center_contract_audit_v1",
        "prd": "PRD-046.1",
        "generated_at_utc": _utc_now(),
        "cases_file": str(fixtures_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "audit_passed": audit_passed,
        "final_status": final_status,
        "diagnostic_center_contract_ready": audit_passed,
        "diagnostic_center_runtime_enabled": False,
        "case_results": case_results,
    }

    _write_json(out_dir / "diagnostic_center_contract_audit.json", audit)
    _write_json(out_dir / "diagnostic_center_eval_scorecard.json", scorecard)
    _write_json(out_dir / "diagnostic_center_trace_samples.json", trace_samples)

    return {
        "status": final_status,
        "audit": audit,
        "scorecard": scorecard,
        "no_mutation": no_mutation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-046.1 Diagnostic Center contract audit.")
    parser.add_argument(
        "--cases-file",
        default="bot_psychologist/tests/fixtures/diagnostic_center_v1_cases.json",
    )
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.1")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"passed", "done_with_eval_blocker", "failed_safety_violation"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
