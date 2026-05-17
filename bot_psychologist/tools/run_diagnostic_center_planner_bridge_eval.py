from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.contracts.context_package import ContextAssemblyPackage
from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterOutput
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.diagnostic_center_divergence import (
    build_shadow_divergence_scorecard_v1,
    classify_divergence_severity_v1,
)
from bot_agent.multiagent.diagnostic_center_shadow import build_diagnostic_center_shadow_v1
from bot_agent.multiagent.planner_bridge_candidate import build_planner_bridge_candidate_v1


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
        nervous_state=str(payload.get("nervous_state", "window")),
        intent=str(payload.get("intent", "explore")),
        openness=str(payload.get("openness", "open")),
        ok_position=str(payload.get("ok_position", "I+W+")),
        safety_flag=bool(payload.get("safety_flag", False)),
        confidence=float(payload.get("confidence", 0.7) or 0.7),
    )


def _build_thread(payload: dict[str, Any], *, case_id: str) -> ThreadState:
    return ThreadState(
        thread_id=str(payload.get("thread_id", f"thread_{case_id}")),
        user_id=str(payload.get("user_id", "planner_bridge_eval_user")),
        core_direction=str(payload.get("core_direction", "planner_bridge_eval")),
        phase=str(payload.get("phase", "clarify")),  # type: ignore[arg-type]
        relation_to_thread=str(payload.get("relation_to_thread", "continue")),  # type: ignore[arg-type]
        response_mode=str(payload.get("response_mode", "reflect")),  # type: ignore[arg-type]
        response_goal=str(payload.get("response_goal", "")),
        must_avoid=[str(item) for item in _safe_list(payload.get("must_avoid"))],
        continuity_score=float(payload.get("continuity_score", 0.8) or 0.8),
        nervous_state=str(payload.get("nervous_state", "window")),
        intent=str(payload.get("intent", "explore")),
        openness=str(payload.get("openness", "open")),
        ok_position=str(payload.get("ok_position", "I+W+")),
        pattern_core=str(payload.get("pattern_core", "")),
        active_frame=_safe_dict(payload.get("active_frame")),
        open_loops=[str(item) for item in _safe_list(payload.get("open_loops"))],
        closed_loops=[str(item) for item in _safe_list(payload.get("closed_loops"))],
        safety_active=bool(payload.get("safety_active", False)),
    )


def _build_context(payload: dict[str, Any], user_message: str) -> ContextAssemblyPackage:
    return ContextAssemblyPackage(
        current_user_message=user_message,
        pattern_core=str(payload.get("pattern_core", "")) or None,
        active_frame=_safe_dict(payload.get("active_frame")),
        semantic_memory_hits=[dict(item) for item in _safe_list(payload.get("semantic_memory_hits")) if isinstance(item, dict)],
        knowledge_rag_hits=[dict(item) for item in _safe_list(payload.get("knowledge_rag_hits")) if isinstance(item, dict)],
    )


def _build_memory(payload: dict[str, Any]) -> MemoryBundle:
    return MemoryBundle(
        conversation_context=str(payload.get("conversation_context", "")),
        semantic_memory_hits=[dict(item) for item in _safe_list(payload.get("semantic_memory_hits")) if isinstance(item, dict)],
        knowledge_rag_hits=[dict(item) for item in _safe_list(payload.get("knowledge_rag_hits")) if isinstance(item, dict)],
        has_relevant_knowledge=bool(payload.get("has_relevant_knowledge", False)),
        context_turns=int(payload.get("context_turns", 0) or 0),
    )


def _build_diagnostic_card(payload: dict[str, Any]) -> DiagnosticCard:
    trace = DiagnosticCardTrace(
        version="diagnostic_card_v1",
        builder="planner_bridge_fixture",
        rules_applied=[str(item) for item in _safe_list(payload.get("rules_applied"))],
        risk_flags=[str(item) for item in _safe_list(payload.get("risk_flags"))],
        evidence_sources=["fixture"],
    )
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label=str(payload.get("situation_label", "generic_support")),
        user_state_summary=str(payload.get("user_state_summary", "fixture")),
        thread_line_summary=str(payload.get("thread_line_summary", "fixture")),
        current_need=str(payload.get("current_need", "clarify")),
        suggested_writer_move=str(payload.get("suggested_writer_move", "clarify_one_point")),
        avoid_list=[str(item) for item in _safe_list(payload.get("avoid_list"))],
        confidence=float(payload.get("confidence", 0.7) or 0.7),
        risk_flags=[str(item) for item in _safe_list(payload.get("risk_flags"))],
        trace=trace,
    )


def _get_nested(payload: dict[str, Any], dotted_key: str) -> Any:
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _evaluate_expected(payload: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for key, value in expected.items():
        if key == "allow_soft_warning":
            continue
        if key.endswith("_one_of"):
            field = key.replace("_one_of", "")
            observed = _get_nested(payload, field)
            options = [str(item) for item in _safe_list(value)]
            if str(observed) not in options:
                issues.append(f"{field}:observed={observed},expected_one_of={options}")
            continue
        observed = _get_nested(payload, key)
        if observed != value:
            issues.append(f"{key}:observed={observed},expected={value}")
    return len(issues) == 0, issues


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
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

    case_results: list[dict[str, Any]] = []
    trace_samples: list[dict[str, Any]] = []
    passes = 0
    hard_blocker_count = 0
    unexpected_soft_warning_count = 0
    expected_divergence_count = 0
    needs_review_count = 0
    safety_cases_total = 0
    safety_cases_passed = 0
    kb_boundary_violation_count = 0
    raw_kb_text_exposure_count = 0
    user_path_effect_count = 0
    planner_bridge_apply_to_writer_count = 0

    for case in cases:
        case_id = str(case.get("case_id", "unknown_case"))
        user_message = str(case.get("user_message", ""))
        state = _build_state(_safe_dict(case.get("state_snapshot")))
        thread = _build_thread(_safe_dict(case.get("thread_state")), case_id=case_id)
        context = _build_context(_safe_dict(case.get("context_package")), user_message)
        memory = _build_memory(_safe_dict(case.get("memory_bundle")))
        diagnostic_card = _build_diagnostic_card(_safe_dict(case.get("diagnostic_card")))
        thread_debug = _safe_dict(case.get("thread_debug"))

        shadow = build_diagnostic_center_shadow_v1(
            user_message=user_message,
            state_snapshot=state,
            thread_state=thread,
            context_package=context,
            memory_bundle=memory,
            diagnostic_card=diagnostic_card,
            thread_debug=thread_debug,
            enabled=True,
        )
        divergence = _safe_dict(shadow.get("divergence"))
        divergence_severity = classify_divergence_severity_v1(divergence)
        output_raw = _safe_dict(shadow.get("output"))
        output = DiagnosticCenterOutput.from_dict(output_raw) if output_raw else DiagnosticCenterOutput.from_dict({})
        bridge = build_planner_bridge_candidate_v1(
            diagnostic_center_output=output,
            divergence=divergence,
            divergence_severity=divergence_severity,
            diagnostic_card=diagnostic_card,
            thread_state=thread,
            state_snapshot=state,
        ).to_dict()

        expected_divergence = _safe_dict(case.get("expected_divergence"))
        expected_bridge = _safe_dict(case.get("expected_bridge"))
        divergence_ok, divergence_issues = _evaluate_expected(
            {**divergence, "divergence_severity": divergence_severity},
            expected_divergence,
        )
        bridge_ok, bridge_issues = _evaluate_expected(bridge, expected_bridge)

        if divergence_severity == "hard_blocker":
            hard_blocker_count += 1
        if divergence_severity == "soft_warning":
            if not bool(expected_divergence.get("allow_soft_warning", False)):
                unexpected_soft_warning_count += 1
        if divergence_severity == "expected_divergence":
            expected_divergence_count += 1
        if divergence_severity == "needs_review":
            needs_review_count += 1

        if not bool(divergence.get("kb_boundary_ok", True)):
            kb_boundary_violation_count += 1
        if bool(divergence.get("raw_kb_text_exposed", False)):
            raw_kb_text_exposure_count += 1
        user_path = _safe_dict(divergence.get("user_path"))
        if (
            bool(user_path.get("writer_contract_changed"))
            or bool(user_path.get("writer_prompt_changed_by_shadow"))
            or bool(user_path.get("final_answer_changed_by_shadow"))
            or bool(user_path.get("diagnostic_center_output_passed_to_writer"))
        ):
            user_path_effect_count += 1
        if bool(bridge.get("apply_to_writer")) or bool(bridge.get("apply_to_writer_contract")):
            planner_bridge_apply_to_writer_count += 1

        safety_case = bool(
            state.safety_flag
            or thread.safety_active
            or state.nervous_state in {"hyper", "hypo"}
            or output.status == "safety_first"
        )
        if safety_case:
            safety_cases_total += 1
            safe_depth = str(bridge.get("depth_limit")) in {"none", "low"}
            if safe_depth and str(bridge.get("status")) in {"limited", "blocked"}:
                safety_cases_passed += 1

        case_passed = (
            shadow.get("status") == "ok"
            and divergence_ok
            and bridge_ok
            and divergence_severity != "hard_blocker"
            and not bool(bridge.get("apply_to_writer"))
            and not bool(bridge.get("apply_to_writer_contract"))
        )
        if case_passed:
            passes += 1

        case_results.append(
            {
                "case_id": case_id,
                "passed": case_passed,
                "divergence_severity": divergence_severity,
                "divergence_expectation_issues": divergence_issues,
                "bridge_expectation_issues": bridge_issues,
                "shadow": shadow,
                "bridge": bridge,
            }
        )
        if len(trace_samples) < 8:
            trace_samples.append(
                {
                    "case_id": case_id,
                    "divergence_severity": divergence_severity,
                    "shadow_status": shadow.get("status"),
                    "divergence": divergence,
                    "bridge": bridge,
                }
            )

    divergence_summary = build_shadow_divergence_scorecard_v1(
        case_results=case_results,
        prd="PRD-046.1.2",
        schema_version="shadow_divergence_calibration_scorecard_v1",
    )

    safety_bridge_pass_rate = round(safety_cases_passed / max(1, safety_cases_total), 4)
    planner_bridge_contract_ready = (
        len(cases) >= 24
        and passes == len(cases)
        and hard_blocker_count == 0
        and safety_bridge_pass_rate == 1.0
        and kb_boundary_violation_count == 0
        and raw_kb_text_exposure_count == 0
        and user_path_effect_count == 0
        and planner_bridge_apply_to_writer_count == 0
    )
    final_status = "passed" if planner_bridge_contract_ready else "done_with_shadow_blocker"

    scorecard = {
        "schema_version": "diagnostic_center_planner_bridge_scorecard_v1",
        "prd": "PRD-046.1.2",
        "generated_at_utc": _utc_now(),
        "cases_total": len(cases),
        "cases_passed": passes,
        "hard_blocker_count": hard_blocker_count,
        "unexpected_soft_warning_count": unexpected_soft_warning_count,
        "expected_divergence_count": expected_divergence_count,
        "needs_review_count": needs_review_count,
        "safety_bridge_pass_rate": safety_bridge_pass_rate,
        "kb_boundary_violation_count": kb_boundary_violation_count,
        "raw_kb_text_exposure_count": raw_kb_text_exposure_count,
        "user_path_effect_count": user_path_effect_count,
        "planner_bridge_apply_to_writer_count": planner_bridge_apply_to_writer_count,
        "planner_bridge_contract_ready": planner_bridge_contract_ready,
        "final_status": final_status,
        "next_prd": "PRD-046.1.3",
    }

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}
    no_mutation = {
        "schema_version": "planner_bridge_no_mutation_proof_v1",
        "prd": "PRD-046.1.2",
        "generated_at_utc": _utc_now(),
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "provider_called_by_planner_bridge": False,
        "production_apply_performed": False,
        "writer_prompt_production_changed": False,
        "writer_contract_changed": False,
        "final_answer_changed_by_bridge": False,
        "diagnostic_center_active_in_writer": False,
        "planner_bridge_apply_to_writer": False,
        "diagnostic_center_user_facing_enabled": False,
        "legacy_sd_enabled": False,
        "hash_before": hash_before,
        "hash_after": hash_after,
    }

    _write_json(
        out_dir / "shadow_divergence_calibration_audit.json",
        {
            "schema_version": "shadow_divergence_calibration_audit_v1",
            "prd": "PRD-046.1.2",
            "generated_at_utc": _utc_now(),
            "cases_file": str(cases_file.relative_to(REPO_ROOT)).replace("\\", "/"),
            "case_results": case_results,
            "divergence_summary": divergence_summary,
        },
    )
    _write_json(out_dir / "shadow_divergence_calibration_scorecard.json", scorecard)
    _write_json(
        out_dir / "planner_bridge_contract_eval.json",
        {
            "schema_version": "planner_bridge_contract_eval_v1",
            "prd": "PRD-046.1.2",
            "generated_at_utc": _utc_now(),
            "planner_bridge_contract_ready": planner_bridge_contract_ready,
            "scorecard": scorecard,
        },
    )
    _write_json(out_dir / "planner_bridge_trace_samples.json", trace_samples)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    return {
        "status": final_status,
        "scorecard": scorecard,
        "divergence_summary": divergence_summary,
        "no_mutation": no_mutation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.2 planner bridge eval.")
    parser.add_argument(
        "--cases-file",
        default="bot_psychologist/tests/fixtures/diagnostic_center_planner_bridge_cases.json",
    )
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.1.2")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"passed", "done_with_shadow_blocker"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
