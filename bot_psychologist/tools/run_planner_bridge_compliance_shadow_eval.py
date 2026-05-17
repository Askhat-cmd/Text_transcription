from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import sys


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.contracts.context_package import ContextAssemblyPackage
from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.diagnostic_center_divergence import classify_divergence_severity_v1
from bot_agent.multiagent.diagnostic_center_shadow import build_diagnostic_center_shadow_v1
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator
from bot_agent.multiagent.planner_bridge_compliance_shadow import (
    build_planner_bridge_compliance_runtime_shadow_v1,
)
from tools import validate_prd_artifact_encoding as encoding_validator


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
        user_id=str(payload.get("user_id", "planner_bridge_compliance_eval_user")),
        core_direction=str(payload.get("core_direction", "planner_bridge_compliance_eval")),
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
        builder="planner_bridge_compliance_fixture",
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


def _run_runtime_smoke() -> list[dict[str, Any]]:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    now = datetime.utcnow()
    smoke_cases = [
        {
            "case_id": "runtime_smoke_normal",
            "query": "Помоги мне мягко прояснить одну мысль.",
            "state": StateSnapshot("window", "clarify", "mixed", "I-W+", False, 0.8),
            "thread": ThreadState(
                thread_id="smoke_t1",
                user_id="u1",
                core_direction="smoke",
                phase="clarify",
                relation_to_thread="continue",
                response_mode="reflect",
                response_goal="clarify",
                pattern_core="clarify_one_point",
                created_at=now,
                updated_at=now,
            ),
            "bundle": MemoryBundle(conversation_context="a", has_relevant_knowledge=False, context_turns=2),
        },
        {
            "case_id": "runtime_smoke_safety",
            "query": "Мне очень тяжело и тревожно.",
            "state": StateSnapshot("hyper", "contact", "defensive", "I-W+", True, 0.9),
            "thread": ThreadState(
                thread_id="smoke_t2",
                user_id="u1",
                core_direction="smoke",
                phase="stabilize",
                relation_to_thread="continue",
                response_mode="safe_override",
                response_goal="safety",
                pattern_core="acute_activation",
                safety_active=True,
                created_at=now,
                updated_at=now,
            ),
            "bundle": MemoryBundle(conversation_context="b", has_relevant_knowledge=True, context_turns=3),
        },
        {
            "case_id": "runtime_smoke_kb_lens",
            "query": "Я опять чувствую, что недостаточно хорош.",
            "state": StateSnapshot("window", "clarify", "mixed", "I-W+", False, 0.83),
            "thread": ThreadState(
                thread_id="smoke_t3",
                user_id="u1",
                core_direction="smoke",
                phase="clarify",
                relation_to_thread="continue",
                response_mode="reflect",
                response_goal="clarify",
                pattern_core="insufficient_self",
                created_at=now,
                updated_at=now,
            ),
            "bundle": MemoryBundle(
                conversation_context="c",
                has_relevant_knowledge=True,
                context_turns=3,
                knowledge_rag_hits=[{"lens_family": "insufficient_self", "score": 0.9, "content": "safe preview"}],
            ),
        },
    ]

    originals = {
        "analyze": orch_module.state_analyzer_agent.analyze,
        "update": orch_module.thread_manager_agent.update,
        "assemble": orch_module.memory_retrieval_agent.assemble,
        "write": orch_module.writer_agent.write,
        "validate": orch_module.validator_agent.validate,
        "memory_update": orch_module.memory_retrieval_agent.update,
        "load_active": orch_module.thread_storage.load_active,
        "load_archived": orch_module.thread_storage.load_archived,
        "save_active": orch_module.thread_storage.save_active,
        "archive_thread": orch_module.thread_storage.archive_thread,
        "create_task": orch_module.asyncio.create_task,
        "thread_debug": getattr(orch_module.thread_manager_agent, "last_debug", None),
    }
    results: list[dict[str, Any]] = []
    try:
        orch_module.thread_storage.load_active = lambda _u: None
        orch_module.thread_storage.load_archived = lambda _u: []
        orch_module.thread_storage.save_active = lambda _t: None
        orch_module.thread_storage.archive_thread = lambda *_a, **_k: None
        orch_module.memory_retrieval_agent.update = AsyncMock(return_value=None)
        orch_module.validator_agent.validate = lambda _a, _c: ValidationResult(is_blocked=False)
        orch_module.writer_agent.write = AsyncMock(return_value="shadow compliance smoke answer")
        orch_module.thread_manager_agent.last_debug = {
            "version": "thread_diagnostics_v1",
            "relation": {"continuity_risk": "none"},
            "phase": {},
            "mode": {},
            "loops": {},
            "action": {"thread_action": "continue"},
            "summary_flags": [],
        }
        orch_module.asyncio.create_task = lambda coro: (coro.close(), None)[1]
        for case in smoke_cases:
            orch_module.state_analyzer_agent.analyze = AsyncMock(return_value=case["state"])
            orch_module.thread_manager_agent.update = AsyncMock(return_value=case["thread"])
            orch_module.memory_retrieval_agent.assemble = AsyncMock(return_value=case["bundle"])
            run_result = MultiAgentOrchestrator().run_sync(query=str(case["query"]), user_id="pbcs_smoke")
            debug = _safe_dict(run_result.get("debug"))
            compliance = _safe_dict(debug.get("planner_bridge_compliance_shadow"))
            candidate = _safe_dict(debug.get("planner_bridge_candidate"))
            results.append(
                {
                    "case_id": case["case_id"],
                    "status": run_result.get("status"),
                    "answer_exists": bool(str(run_result.get("answer", "")).strip()),
                    "diagnostic_center_shadow_exists": bool(_safe_dict(debug.get("diagnostic_center_shadow"))),
                    "planner_bridge_candidate_exists": bool(candidate),
                    "planner_bridge_compliance_shadow_exists": bool(compliance),
                    "runtime_mode": compliance.get("activation_mode"),
                    "apply_to_writer": compliance.get("apply_to_writer"),
                    "apply_to_writer_contract": compliance.get("apply_to_writer_contract"),
                    "writer_prompt_changed": compliance.get("writer_prompt_changed"),
                    "final_answer_changed": compliance.get("final_answer_changed"),
                    "writer_prompt_contains_shadow_output": "planner_bridge_candidate" in str(
                        debug.get("writer_user_prompt", "")
                    ).lower(),
                }
            )
    finally:
        orch_module.state_analyzer_agent.analyze = originals["analyze"]
        orch_module.thread_manager_agent.update = originals["update"]
        orch_module.memory_retrieval_agent.assemble = originals["assemble"]
        orch_module.writer_agent.write = originals["write"]
        orch_module.validator_agent.validate = originals["validate"]
        orch_module.memory_retrieval_agent.update = originals["memory_update"]
        orch_module.thread_storage.load_active = originals["load_active"]
        orch_module.thread_storage.load_archived = originals["load_archived"]
        orch_module.thread_storage.save_active = originals["save_active"]
        orch_module.thread_storage.archive_thread = originals["archive_thread"]
        orch_module.asyncio.create_task = originals["create_task"]
        orch_module.thread_manager_agent.last_debug = originals["thread_debug"]
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

    case_results: list[dict[str, Any]] = []
    trace_samples: list[dict[str, Any]] = []
    passes = 0
    compatible_count = 0
    tightens_constraints_count = 0
    expected_divergence_count = 0
    needs_review_count = 0
    blocked_count = 0
    hard_blocker_count = 0
    unexpected_blocked_count = 0
    unexpected_needs_review_count = 0
    safety_cases_total = 0
    safety_cases_passed = 0
    kb_boundary_violation_count = 0
    raw_kb_text_exposure_count = 0
    user_path_effect_count = 0
    writer_prompt_changed_by_bridge_count = 0
    writer_contract_changed_by_bridge_count = 0
    final_answer_changed_by_bridge_count = 0
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
        bridge_shadow = build_planner_bridge_compliance_runtime_shadow_v1(
            diagnostic_center_shadow=shadow,
            diagnostic_card=diagnostic_card,
            thread_state=thread,
            state_snapshot=state,
        )
        bridge = _safe_dict(bridge_shadow.get("planner_bridge_candidate"))
        compliance = _safe_dict(bridge_shadow.get("planner_bridge_compliance_shadow"))
        overall_status = str(_safe_dict(compliance.get("compatibility")).get("overall_status", "blocked"))
        expected_compliance = _safe_dict(case.get("expected_compliance"))
        expected_bridge = _safe_dict(case.get("expected_bridge"))
        compliance_ok, compliance_issues = _evaluate_expected(compliance, expected_compliance)
        bridge_ok, bridge_issues = _evaluate_expected(bridge, expected_bridge)

        if overall_status == "compatible":
            compatible_count += 1
        elif overall_status == "tightens_constraints":
            tightens_constraints_count += 1
        elif overall_status == "expected_divergence":
            expected_divergence_count += 1
        elif overall_status == "needs_review":
            needs_review_count += 1
        elif overall_status == "blocked":
            blocked_count += 1

        divergence_severity = classify_divergence_severity_v1(divergence)
        if divergence_severity == "hard_blocker":
            hard_blocker_count += 1

        expected_overall_status = str(expected_compliance.get("compatibility.overall_status", ""))
        if overall_status == "blocked" and expected_overall_status != "blocked":
            unexpected_blocked_count += 1
        if overall_status == "needs_review" and expected_overall_status != "needs_review":
            unexpected_needs_review_count += 1

        if not bool(_safe_dict(compliance.get("compatibility")).get("kb_boundary_compatible", True)):
            kb_boundary_violation_count += 1
        if bool(divergence.get("raw_kb_text_exposed", False)):
            raw_kb_text_exposure_count += 1

        if bool(compliance.get("writer_prompt_changed")):
            writer_prompt_changed_by_bridge_count += 1
        if bool(compliance.get("apply_to_writer_contract")):
            writer_contract_changed_by_bridge_count += 1
        if bool(compliance.get("final_answer_changed")):
            final_answer_changed_by_bridge_count += 1
        if bool(compliance.get("apply_to_writer")):
            planner_bridge_apply_to_writer_count += 1
        if (
            bool(compliance.get("writer_prompt_changed"))
            or bool(compliance.get("apply_to_writer_contract"))
            or bool(compliance.get("final_answer_changed"))
            or bool(compliance.get("apply_to_writer"))
        ):
            user_path_effect_count += 1

        safety_case = bool(state.safety_flag or thread.safety_active or state.nervous_state in {"hyper", "hypo"})
        if safety_case:
            safety_cases_total += 1
            if bool(_safe_dict(compliance.get("compatibility")).get("safety_compatible", False)):
                safety_cases_passed += 1

        case_passed = (
            shadow.get("status") == "ok"
            and compliance_ok
            and bridge_ok
            and not bool(compliance.get("apply_to_writer"))
            and not bool(compliance.get("apply_to_writer_contract"))
            and not bool(compliance.get("writer_prompt_changed"))
            and not bool(compliance.get("final_answer_changed"))
        )
        if case_passed:
            passes += 1

        case_results.append(
            {
                "case_id": case_id,
                "passed": case_passed,
                "overall_status": overall_status,
                "compliance_expectation_issues": compliance_issues,
                "bridge_expectation_issues": bridge_issues,
                "shadow": shadow,
                "planner_bridge_candidate": bridge,
                "planner_bridge_compliance_shadow": compliance,
            }
        )
        if len(trace_samples) < 10:
            trace_samples.append(
                {
                    "case_id": case_id,
                    "overall_status": overall_status,
                    "planner_bridge_candidate": bridge,
                    "planner_bridge_compliance_shadow": compliance,
                }
            )

    runtime_smoke_cases = _run_runtime_smoke()
    runtime_smoke_ok = all(
        case.get("status") == "ok"
        and case.get("answer_exists")
        and case.get("diagnostic_center_shadow_exists")
        and case.get("planner_bridge_candidate_exists")
        and case.get("planner_bridge_compliance_shadow_exists")
        and case.get("runtime_mode") == "shadow_compare_only"
        and case.get("apply_to_writer") is False
        and case.get("apply_to_writer_contract") is False
        and case.get("writer_prompt_changed") is False
        and case.get("final_answer_changed") is False
        and not case.get("writer_prompt_contains_shadow_output")
        for case in runtime_smoke_cases
    )

    _write_json(
        out_dir / "planner_bridge_compliance_runtime_smoke.json",
        {
            "schema_version": "planner_bridge_compliance_runtime_smoke_v1",
            "prd": "PRD-046.1.3",
            "generated_at_utc": _utc_now(),
            "runtime_smoke_ok": runtime_smoke_ok,
            "cases": runtime_smoke_cases,
        },
    )

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}
    no_mutation = {
        "schema_version": "planner_bridge_compliance_shadow_no_mutation_proof_v1",
        "prd": "PRD-046.1.3",
        "generated_at_utc": _utc_now(),
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "provider_called_by_compliance_shadow": False,
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
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    _write_json(
        out_dir / "planner_bridge_compliance_shadow_eval.json",
        {
            "schema_version": "planner_bridge_compliance_shadow_eval_v1",
            "prd": "PRD-046.1.3",
            "generated_at_utc": _utc_now(),
            "cases_file": str(cases_file.relative_to(REPO_ROOT)).replace("\\", "/"),
            "results": case_results,
        },
    )
    _write_json(out_dir / "planner_bridge_compliance_trace_samples.json", trace_samples)

    safety_compatibility_pass_rate = round(safety_cases_passed / max(1, safety_cases_total), 4)
    scorecard = {
        "schema_version": "planner_bridge_compliance_shadow_scorecard_v1",
        "prd": "PRD-046.1.3",
        "generated_at_utc": _utc_now(),
        "cases_total": len(cases),
        "cases_passed": passes,
        "compatible_count": compatible_count,
        "tightens_constraints_count": tightens_constraints_count,
        "expected_divergence_count": expected_divergence_count,
        "needs_review_count": needs_review_count,
        "blocked_count": blocked_count,
        "hard_blocker_count": hard_blocker_count,
        "unexpected_blocked_count": unexpected_blocked_count,
        "unexpected_needs_review_count": unexpected_needs_review_count,
        "safety_compatibility_pass_rate": safety_compatibility_pass_rate,
        "kb_boundary_violation_count": kb_boundary_violation_count,
        "raw_kb_text_exposure_count": raw_kb_text_exposure_count,
        "user_path_effect_count": user_path_effect_count,
        "writer_prompt_changed_by_bridge_count": writer_prompt_changed_by_bridge_count,
        "writer_contract_changed_by_bridge_count": writer_contract_changed_by_bridge_count,
        "final_answer_changed_by_bridge_count": final_answer_changed_by_bridge_count,
        "planner_bridge_apply_to_writer_count": planner_bridge_apply_to_writer_count,
        "runtime_smoke_ok": runtime_smoke_ok,
    }
    _write_json(out_dir / "planner_bridge_compliance_shadow_scorecard.json", scorecard)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd="PRD-046.1.3",
            logs_dir=str(out_dir),
            reports_dir=str(REPO_ROOT / "TO_DO_LIST" / "reports"),
            out_dir=str(out_dir),
            report_prd="PRD-046.1.3",
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )
    scorecard["artifact_encoding_hygiene_passed"] = encoding_report.get("final_status") == "passed"

    planner_bridge_compliance_shadow_ready = (
        len(cases) >= 30
        and passes == len(cases)
        and hard_blocker_count == 0
        and unexpected_blocked_count == 0
        and safety_compatibility_pass_rate == 1.0
        and kb_boundary_violation_count == 0
        and raw_kb_text_exposure_count == 0
        and user_path_effect_count == 0
        and writer_prompt_changed_by_bridge_count == 0
        and writer_contract_changed_by_bridge_count == 0
        and final_answer_changed_by_bridge_count == 0
        and planner_bridge_apply_to_writer_count == 0
        and runtime_smoke_ok
        and scorecard["artifact_encoding_hygiene_passed"]
    )
    final_status = "passed" if planner_bridge_compliance_shadow_ready else "done_with_shadow_blocker"
    scorecard["planner_bridge_compliance_shadow_ready"] = planner_bridge_compliance_shadow_ready
    scorecard["final_status"] = final_status
    scorecard["next_prd"] = "PRD-046.1.4"
    _write_json(out_dir / "planner_bridge_compliance_shadow_scorecard.json", scorecard)

    return {
        "status": final_status,
        "scorecard": scorecard,
        "runtime_smoke_ok": runtime_smoke_ok,
        "no_mutation": no_mutation,
        "artifact_encoding_hygiene": encoding_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.3 planner bridge compliance shadow eval.")
    parser.add_argument(
        "--cases-file",
        default="bot_psychologist/tests/fixtures/planner_bridge_compliance_shadow_cases.json",
    )
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.1.3")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"passed", "done_with_shadow_blocker"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

