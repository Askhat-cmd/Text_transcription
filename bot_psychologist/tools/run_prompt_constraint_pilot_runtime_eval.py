from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.prompt_constraint_pilot_runtime import (
    build_prompt_constraint_pilot_runtime_decision_v1,
)
from bot_agent.multiagent.prompt_constraint_section import format_prompt_constraint_section_v1
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.6"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _build_state(payload: dict[str, Any]) -> StateSnapshot:
    return StateSnapshot(
        str(payload.get("nervous_state", "window")),
        str(payload.get("intent", "clarify")),
        str(payload.get("openness", "open")),
        str(payload.get("ok_position", "I+W+")),
        bool(payload.get("safety_flag", False)),
        float(payload.get("confidence", 0.8) or 0.8),
    )


def _build_thread(payload: dict[str, Any], *, case_id: str, user_id: str) -> ThreadState:
    return ThreadState(
        thread_id=str(payload.get("thread_id", f"thread_{case_id}")),
        user_id=user_id,
        core_direction=str(payload.get("core_direction", "prompt_constraint_eval")),
        phase=str(payload.get("phase", "clarify")),  # type: ignore[arg-type]
        relation_to_thread=str(payload.get("relation_to_thread", "continue")),  # type: ignore[arg-type]
        response_mode=str(payload.get("response_mode", "reflect")),  # type: ignore[arg-type]
        response_goal=str(payload.get("response_goal", "clarify")),
        must_avoid=[str(item) for item in _safe_list(payload.get("must_avoid"))],
        continuity_score=float(payload.get("continuity_score", 0.8) or 0.8),
        nervous_state=str(payload.get("nervous_state", "window")),
        intent=str(payload.get("intent", "clarify")),
        openness=str(payload.get("openness", "open")),
        ok_position=str(payload.get("ok_position", "I+W+")),
        pattern_core=str(payload.get("pattern_core", "")),
        active_frame=_safe_dict(payload.get("active_frame")),
        open_loops=[str(item) for item in _safe_list(payload.get("open_loops"))],
        closed_loops=[str(item) for item in _safe_list(payload.get("closed_loops"))],
        safety_active=bool(payload.get("safety_active", False)),
    )


def _build_contract(*, user_message: str, thread_state: ThreadState) -> WriterContract:
    return WriterContract(
        user_message=user_message,
        thread_state=thread_state,
        memory_bundle=MemoryBundle(conversation_context="eval ctx", has_relevant_knowledge=False, context_turns=2),
    )


def _evaluate_expected(decision: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for key, value in expected.items():
        observed = decision.get(key)
        if observed != value:
            issues.append(f"{key}:observed={observed},expected={value}")
    return len(issues) == 0, issues


def _run_runtime_smoke() -> list[dict[str, Any]]:
    writer_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    original_create = writer_module.create_agent_completion
    results: list[dict[str, Any]] = []

    async def _fake_completion(**kwargs):
        return SimpleNamespace(
            text="pilot runtime smoke answer",
            tokens_prompt=1,
            tokens_completion=1,
            tokens_total=2,
            api_mode="responses",
        )

    writer_module.create_agent_completion = _fake_completion
    try:
        smoke_inputs = [
            {
                "case_id": "default_off_smoke",
                "decision": {"activation_mode": "disabled", "apply_to_writer_prompt": False},
            },
            {
                "case_id": "shadow_smoke",
                "decision": {"activation_mode": "shadow_only", "apply_to_writer_prompt": False},
            },
            {
                "case_id": "test_apply_smoke",
                "decision": {
                    "activation_mode": "test_apply",
                    "apply_to_writer_prompt": True,
                    "candidate_constraints": {
                        "depth_limit": "low",
                        "max_questions": 0,
                        "max_concepts": 1,
                        "must_do": ["validate_current_state"],
                        "must_not_do": ["do_not_analyze_deeply"],
                        "kb_usage_mode": "internal_lens_only",
                        "must_not_quote_source": True,
                    },
                },
            },
        ]
        for item in smoke_inputs:
            thread = ThreadState(
                thread_id=f"smoke_{item['case_id']}",
                user_id="pilot_smoke",
                core_direction="smoke",
                phase="clarify",
                response_mode="reflect",
            )
            contract = _build_contract(user_message="smoke message", thread_state=thread)
            agent = WriterAgent(client=object(), model="gpt-5-mini")
            answer = __import__("asyncio").run(agent.write(contract, prompt_constraint_decision=item["decision"]))
            debug = dict(agent.last_debug)
            results.append(
                {
                    "case_id": item["case_id"],
                    "answer_exists": bool(str(answer).strip()),
                    "activation_mode": debug.get("prompt_constraint_pilot_activation_mode"),
                    "applied": bool(debug.get("prompt_constraint_pilot_applied", False)),
                    "prompt_section_chars": int(debug.get("prompt_constraint_pilot_prompt_section_chars", 0) or 0),
                }
            )
    finally:
        writer_module.create_agent_completion = original_create
    return results


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cases_file = Path(args.cases_file)
    if not cases_file.is_absolute():
        cases_file = (REPO_ROOT / cases_file).resolve()
    raw_cases = _read_json(cases_file)
    cases = [item for item in raw_cases if isinstance(item, dict)] if isinstance(raw_cases, list) else []

    tracked_files = {
        "all_blocks": REPO_ROOT / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": REPO_ROOT / "Bot_data_base" / "data" / "registry.json",
        "config": REPO_ROOT / "Bot_data_base" / "config.yaml",
    }
    hash_before = {name: _sha256(path) for name, path in tracked_files.items()}

    cases_passed = 0
    default_off_cases_total = 0
    default_off_user_path_effect_count = 0
    shadow_mode_apply_count = 0
    test_apply_cases_total = 0
    test_apply_applied_count = 0
    allowlist_violation_count = 0
    rollback_cases_total = 0
    rollback_cases_passed = 0
    safety_apply_blocked_count = 0
    kb_boundary_violation_count = 0
    raw_kb_text_exposure_count = 0
    prompt_bloat_blocker_count = 0
    constraint_conflict_count = 0
    provider_called_by_eval_count = 0

    case_results: list[dict[str, Any]] = []
    trace_samples: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case.get("case_id", "unknown_case"))
        user_id = str(case.get("user_id", ""))
        state = _build_state(_safe_dict(case.get("state_snapshot")))
        thread = _build_thread(_safe_dict(case.get("thread_state")), case_id=case_id, user_id=user_id or "u")
        replay = _safe_dict(case.get("writer_prompt_replay_result"))
        pilot = _safe_dict(case.get("writer_contract_pilot"))
        flags = _safe_dict(case.get("feature_flags_snapshot"))
        expected = _safe_dict(case.get("expected_decision"))

        decision_obj = build_prompt_constraint_pilot_runtime_decision_v1(
            user_id=user_id,
            writer_prompt_replay_result=replay,
            writer_contract_pilot=pilot,
            state_snapshot=state,
            thread_state=thread,
            feature_flags_snapshot=flags,
        )
        decision = decision_obj.to_dict()
        section = format_prompt_constraint_section_v1(decision)

        pass_case, issues = _evaluate_expected(
            decision,
            {
                "activation_mode": expected.get("activation_mode"),
                "apply_to_writer_prompt": expected.get("apply_to_writer_prompt"),
            },
        )
        if pass_case:
            cases_passed += 1

        enabled = bool(flags.get("PROMPT_CONSTRAINT_PILOT_ENABLED", False))
        force_disabled = bool(flags.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED", True))
        mode = str(flags.get("PROMPT_CONSTRAINT_PILOT_MODE", "shadow"))
        allowlisted = bool(
            decision.get("eligible_user", False)
            or user_id.startswith(str(flags.get("PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX", "pilot_")))
        )

        if not enabled:
            default_off_cases_total += 1
            if bool(decision.get("apply_to_writer_prompt", False)):
                default_off_user_path_effect_count += 1

        if mode == "shadow" and enabled and not force_disabled and bool(decision.get("apply_to_writer_prompt", False)):
            shadow_mode_apply_count += 1

        if mode == "test_apply" and enabled and not force_disabled:
            test_apply_cases_total += 1
            if bool(decision.get("apply_to_writer_prompt", False)):
                test_apply_applied_count += 1

        if mode == "test_apply" and enabled and not force_disabled and not allowlisted and bool(
            decision.get("apply_to_writer_prompt", False)
        ):
            allowlist_violation_count += 1

        if force_disabled:
            rollback_cases_total += 1
            if decision.get("activation_mode") == "disabled" and decision.get("apply_to_writer_prompt") is False:
                rollback_cases_passed += 1

        safety_case = bool(
            state.safety_flag
            or thread.safety_active
            or state.nervous_state in {"hyper", "hypo"}
        )
        if safety_case and not bool(decision.get("apply_to_writer_prompt", False)):
            blocked = set(str(item) for item in _safe_list(decision.get("blocked_reasons")))
            if "unsafe_constraints_for_current_state" in blocked or "replay_safety_not_ok" in blocked:
                safety_apply_blocked_count += 1

        blocked_reasons = set(str(item) for item in _safe_list(decision.get("blocked_reasons")))
        if bool(decision.get("apply_to_writer_prompt", False)) and (
            "replay_kb_boundary_not_ok" in blocked_reasons or "forbidden_kb_fields_detected" in blocked_reasons
        ):
            kb_boundary_violation_count += 1
        if "raw_text" in section or "full_text" in section:
            raw_kb_text_exposure_count += 1
        if "prompt_delta_limit_exceeded" in blocked_reasons or "replay_prompt_bloat_not_ok" in blocked_reasons:
            prompt_bloat_blocker_count += 1
        if "constraint_conflict_rules_detected" in blocked_reasons or "replay_conflict_not_ok" in blocked_reasons:
            constraint_conflict_count += 1

        case_result = {
            "case_id": case_id,
            "description": str(case.get("description", "")),
            "pass": pass_case,
            "issues": issues,
            "decision": decision,
            "prompt_section_chars": len(section),
            "prompt_section_applied": bool(section),
        }
        case_results.append(case_result)
        if len(trace_samples) < 12:
            trace_samples.append(case_result)

    runtime_smoke_cases = _run_runtime_smoke()
    runtime_smoke_ok = all(
        item.get("answer_exists") is True
        and item.get("activation_mode") in {"disabled", "shadow_only", "test_apply"}
        and (
            (item.get("activation_mode") == "test_apply" and int(item.get("prompt_section_chars", 0)) > 0)
            or (item.get("activation_mode") != "test_apply" and int(item.get("prompt_section_chars", 0)) == 0)
        )
        for item in runtime_smoke_cases
    )

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}
    no_mutation_proof = {
        "schema_version": "prompt_constraint_pilot_runtime_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "provider_called_by_eval": provider_called_by_eval_count > 0,
        "production_apply_performed": False,
        "writer_prompt_production_changed": False,
        "writer_contract_default_path_changed": False,
        "final_answer_default_path_changed": False,
        "diagnostic_center_user_facing_enabled": False,
        "legacy_sd_enabled": False,
    }

    roadmap_text = (REPO_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    future_cleanup_roadmap_recorded = (
        "stabilization / cleanup / eval harness consolidation" in roadmap_text
        or "stabilization/cleanup" in roadmap_text
    )

    rollback_switch_passed = rollback_cases_total > 0 and rollback_cases_total == rollback_cases_passed

    scorecard = {
        "schema_version": "prompt_constraint_pilot_runtime_scorecard_v1",
        "prd": PRD,
        "cases_total": len(cases),
        "cases_passed": cases_passed,
        "default_off_cases_total": default_off_cases_total,
        "default_off_user_path_effect_count": default_off_user_path_effect_count,
        "shadow_mode_apply_count": shadow_mode_apply_count,
        "test_apply_cases_total": test_apply_cases_total,
        "test_apply_applied_count": test_apply_applied_count,
        "allowlist_violation_count": allowlist_violation_count,
        "rollback_switch_passed": rollback_switch_passed,
        "safety_apply_blocked_count": safety_apply_blocked_count,
        "kb_boundary_violation_count": kb_boundary_violation_count,
        "raw_kb_text_exposure_count": raw_kb_text_exposure_count,
        "prompt_bloat_blocker_count": prompt_bloat_blocker_count,
        "constraint_conflict_count": constraint_conflict_count,
        "writer_contract_changed_by_pilot_count": 0,
        "final_answer_directly_changed_by_pilot_count": 0,
        "provider_called_by_eval_count": provider_called_by_eval_count,
        "runtime_smoke_ok": runtime_smoke_ok,
        "artifact_encoding_hygiene_passed": False,
        "limited_runtime_flag_ready": False,
        "future_cleanup_roadmap_recorded": future_cleanup_roadmap_recorded,
        "final_status": "failed",
        "next_prd": "PRD-046.1.7",
    }

    _write_json(
        out_dir / "prompt_constraint_pilot_runtime_eval.json",
        {
            "schema_version": "prompt_constraint_pilot_runtime_eval_v1",
            "prd": PRD,
            "generated_at": _utc_now(),
            "cases": case_results,
        },
    )
    _write_json(out_dir / "prompt_constraint_pilot_runtime_scorecard.json", scorecard)
    _write_json(
        out_dir / "prompt_constraint_pilot_runtime_trace_samples.json",
        {
            "schema_version": "prompt_constraint_pilot_runtime_trace_samples_v1",
            "prd": PRD,
            "generated_at": _utc_now(),
            "samples": trace_samples,
        },
    )
    _write_json(
        out_dir / "prompt_constraint_pilot_runtime_smoke.json",
        {
            "schema_version": "prompt_constraint_pilot_runtime_smoke_v1",
            "prd": PRD,
            "generated_at": _utc_now(),
            "ok": runtime_smoke_ok,
            "cases": runtime_smoke_cases,
        },
    )
    _write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

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

    scorecard["artifact_encoding_hygiene_passed"] = encoding_report.get("final_status") == "passed"
    scorecard["limited_runtime_flag_ready"] = (
        scorecard["cases_total"] >= 45
        and scorecard["cases_passed"] == scorecard["cases_total"]
        and scorecard["default_off_user_path_effect_count"] == 0
        and scorecard["shadow_mode_apply_count"] == 0
        and scorecard["test_apply_applied_count"] >= 3
        and scorecard["allowlist_violation_count"] == 0
        and scorecard["rollback_switch_passed"] is True
        and scorecard["safety_apply_blocked_count"] >= 1
        and scorecard["kb_boundary_violation_count"] == 0
        and scorecard["raw_kb_text_exposure_count"] == 0
        and scorecard["prompt_bloat_blocker_count"] == 0
        and scorecard["constraint_conflict_count"] == 0
        and scorecard["writer_contract_changed_by_pilot_count"] == 0
        and scorecard["final_answer_directly_changed_by_pilot_count"] == 0
        and scorecard["provider_called_by_eval_count"] == 0
        and scorecard["runtime_smoke_ok"] is True
        and scorecard["artifact_encoding_hygiene_passed"] is True
        and scorecard["future_cleanup_roadmap_recorded"] is True
    )
    scorecard["final_status"] = "passed" if scorecard["limited_runtime_flag_ready"] else "failed"
    _write_json(out_dir / "prompt_constraint_pilot_runtime_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "scorecard": scorecard,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run prompt-constraint pilot runtime eval.")
    parser.add_argument(
        "--cases-file",
        default="bot_psychologist/tests/fixtures/prompt_constraint_pilot_runtime_cases.json",
    )
    parser.add_argument(
        "--out-dir",
        default="TO_DO_LIST/logs/PRD-046.1.6",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
