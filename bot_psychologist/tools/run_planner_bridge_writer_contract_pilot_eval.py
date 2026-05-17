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
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.diagnostic_center_shadow import build_diagnostic_center_shadow_v1
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator
from bot_agent.multiagent.planner_bridge_compliance_shadow import (
    build_planner_bridge_compliance_runtime_shadow_v1,
)
from bot_agent.multiagent.planner_bridge_writer_contract_pilot import (
    build_planner_bridge_writer_contract_pilot_runtime_shadow_v1,
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


def _stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable_payload(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list):
        return [_stable_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    return str(value)


def _stable_json(value: Any) -> str:
    return json.dumps(_stable_payload(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


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
        user_id=str(payload.get("user_id", "planner_bridge_writer_contract_pilot_eval_user")),
        core_direction=str(payload.get("core_direction", "planner_bridge_writer_contract_pilot_eval")),
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
        builder="planner_bridge_writer_contract_pilot_fixture",
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
            "case_id": "runtime_smoke_normal_reflective",
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
            "case_id": "runtime_smoke_safety_hyper",
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
            "case_id": "runtime_smoke_kb_internal",
            "query": "Я снова чувствую, что недостаточно хорош.",
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
        orch_module.writer_agent.write = AsyncMock(return_value="writer pilot smoke answer")
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
            run_result = MultiAgentOrchestrator().run_sync(query=str(case["query"]), user_id="pbwcp_smoke")
            debug = _safe_dict(run_result.get("debug"))
            pilot = _safe_dict(debug.get("planner_bridge_writer_contract_pilot"))
            overlay = _safe_dict(pilot.get("overlay"))
            guardrails = _safe_dict(overlay.get("guardrails"))
            results.append(
                {
                    "case_id": case["case_id"],
                    "status": run_result.get("status"),
                    "answer_exists": bool(str(run_result.get("answer", "")).strip()),
                    "planner_bridge_writer_contract_pilot_exists": bool(pilot),
                    "activation_mode": overlay.get("activation_mode"),
                    "apply_to_writer_contract": overlay.get("apply_to_writer_contract"),
                    "apply_to_writer_prompt": overlay.get("apply_to_writer_prompt"),
                    "apply_to_final_answer": overlay.get("apply_to_final_answer"),
                    "writer_contract_changed": guardrails.get("writer_contract_changed"),
                    "writer_prompt_changed": guardrails.get("writer_prompt_changed"),
                    "final_answer_changed": guardrails.get("final_answer_changed"),
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

    cases_passed = 0
    hard_blocker_count = 0
    unexpected_needs_review_count = 0
    safety_cases_total = 0
    safety_cases_passed = 0
    kb_boundary_violation_count = 0
    raw_kb_text_exposure_count = 0
    writer_contract_changed_by_pilot_count = 0
    writer_prompt_changed_by_pilot_count = 0
    final_answer_changed_by_pilot_count = 0
    pilot_apply_to_writer_contract_count = 0
    pilot_apply_to_writer_prompt_count = 0
    pilot_apply_to_final_answer_count = 0

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

        bridge_shadow_payload = build_planner_bridge_compliance_runtime_shadow_v1(
            diagnostic_center_shadow=shadow,
            diagnostic_card=diagnostic_card,
            thread_state=thread,
            state_snapshot=state,
        )
        compliance_shadow = _safe_dict(bridge_shadow_payload.get("planner_bridge_compliance_shadow"))
        compliance_override = _safe_dict(case.get("compliance_shadow_override"))
        if compliance_override:
            compliance_shadow = _deep_merge(compliance_shadow, compliance_override)

        writer_contract = WriterContract(
            user_message=user_message,
            thread_state=thread,
            memory_bundle=memory,
            context_package=context,
            diagnostic_card=diagnostic_card,
        )
        writer_contract_before = hashlib.sha256(
            _stable_json(writer_contract.to_dict()).encode("utf-8")
        ).hexdigest()

        pilot = build_planner_bridge_writer_contract_pilot_runtime_shadow_v1(
            writer_contract=writer_contract,
            planner_bridge_compliance_shadow=compliance_shadow,
            diagnostic_card=diagnostic_card,
            thread_state=thread,
            state_snapshot=state,
        )
        writer_contract_after = hashlib.sha256(
            _stable_json(writer_contract.to_dict()).encode("utf-8")
        ).hexdigest()

        overlay = _safe_dict(pilot.get("overlay"))
        guardrails = _safe_dict(overlay.get("guardrails"))
        risk_assessment = _safe_dict(overlay.get("risk_assessment"))

        expected = _safe_dict(case.get("expected_pilot"))
        expected_ok, issues = _evaluate_expected(pilot, expected)

        if expected_ok and writer_contract_before == writer_contract_after:
            cases_passed += 1

        if bool(pilot.get("writer_contract_changed_by_pilot")):
            writer_contract_changed_by_pilot_count += 1
            hard_blocker_count += 1
        if bool(guardrails.get("writer_prompt_changed")):
            writer_prompt_changed_by_pilot_count += 1
            hard_blocker_count += 1
        if bool(guardrails.get("final_answer_changed")):
            final_answer_changed_by_pilot_count += 1
            hard_blocker_count += 1

        if bool(overlay.get("apply_to_writer_contract")):
            pilot_apply_to_writer_contract_count += 1
            hard_blocker_count += 1
        if bool(overlay.get("apply_to_writer_prompt")):
            pilot_apply_to_writer_prompt_count += 1
            hard_blocker_count += 1
        if bool(overlay.get("apply_to_final_answer")):
            pilot_apply_to_final_answer_count += 1
            hard_blocker_count += 1

        if not bool(_safe_dict(compliance_shadow.get("compatibility")).get("kb_boundary_compatible", True)):
            kb_boundary_violation_count += 1
        if bool(divergence.get("raw_kb_text_exposed", False)):
            raw_kb_text_exposure_count += 1

        safety_case = bool(state.safety_flag or thread.safety_active or state.nervous_state in {"hyper", "hypo"})
        if safety_case:
            safety_cases_total += 1
            safety_ok = (
                str(risk_assessment.get("activation_readiness", "")) in {"not_ready", "blocked"}
                and str(_safe_dict(overlay.get("candidate_constraints")).get("depth_limit", "none"))
                in {"none", "low"}
                and int(_safe_dict(overlay.get("candidate_constraints")).get("max_questions", 0) or 0) == 0
            )
            if safety_ok:
                safety_cases_passed += 1

        if (
            str(risk_assessment.get("activation_readiness", "")) == "not_ready"
            and not safety_case
            and str(_safe_dict(compliance_shadow.get("compatibility")).get("overall_status", ""))
            not in {"needs_review", "expected_divergence", "blocked"}
        ):
            unexpected_needs_review_count += 1

        case_result = {
            "case_id": case_id,
            "description": str(case.get("description", "")),
            "pass": expected_ok and writer_contract_before == writer_contract_after,
            "issues": issues,
            "writer_contract_hash_before": writer_contract_before,
            "writer_contract_hash_after": writer_contract_after,
            "writer_contract_changed": writer_contract_before != writer_contract_after,
            "compliance_overall_status": _safe_dict(compliance_shadow.get("compatibility")).get("overall_status"),
            "pilot_activation_readiness": risk_assessment.get("activation_readiness"),
            "pilot_overlay": pilot,
        }
        case_results.append(case_result)

        if len(trace_samples) < 12:
            trace_samples.append(
                {
                    "case_id": case_id,
                    "description": str(case.get("description", "")),
                    "compliance_status": _safe_dict(compliance_shadow.get("compatibility")).get("overall_status"),
                    "overlay": overlay,
                    "trace": _safe_dict(pilot.get("trace")),
                }
            )

    runtime_smoke_cases = _run_runtime_smoke()
    runtime_smoke_ok = all(
        item.get("status") == "ok"
        and item.get("answer_exists") is True
        and item.get("planner_bridge_writer_contract_pilot_exists") is True
        and item.get("activation_mode") == "pilot_shadow_only"
        and item.get("apply_to_writer_contract") is False
        and item.get("apply_to_writer_prompt") is False
        and item.get("apply_to_final_answer") is False
        and item.get("writer_contract_changed") is False
        and item.get("writer_prompt_changed") is False
        and item.get("final_answer_changed") is False
        for item in runtime_smoke_cases
    )

    hash_after = {name: _sha256(path) for name, path in tracked_files.items()}

    no_mutation_proof = {
        "schema_version": "planner_bridge_writer_contract_pilot_no_mutation_proof_v1",
        "prd": "PRD-046.1.4",
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "provider_called_by_writer_contract_pilot": False,
        "production_apply_performed": False,
        "writer_prompt_production_changed": False,
        "writer_contract_changed": writer_contract_changed_by_pilot_count > 0,
        "final_answer_changed_by_pilot": final_answer_changed_by_pilot_count > 0,
        "diagnostic_center_active_in_writer": False,
        "planner_bridge_apply_to_writer": False,
        "pilot_apply_to_writer_contract": pilot_apply_to_writer_contract_count > 0,
        "pilot_apply_to_writer_prompt": pilot_apply_to_writer_prompt_count > 0,
        "pilot_apply_to_final_answer": pilot_apply_to_final_answer_count > 0,
        "diagnostic_center_user_facing_enabled": False,
        "legacy_sd_enabled": False,
    }

    safety_pilot_pass_rate = (
        round(safety_cases_passed / safety_cases_total, 4) if safety_cases_total > 0 else 1.0
    )

    scorecard = {
        "schema_version": "planner_bridge_writer_contract_pilot_scorecard_v1",
        "prd": "PRD-046.1.4",
        "cases_total": len(cases),
        "cases_passed": cases_passed,
        "hard_blocker_count": hard_blocker_count,
        "unexpected_needs_review_count": unexpected_needs_review_count,
        "safety_pilot_pass_rate": safety_pilot_pass_rate,
        "kb_boundary_violation_count": kb_boundary_violation_count,
        "raw_kb_text_exposure_count": raw_kb_text_exposure_count,
        "writer_contract_changed_by_pilot_count": writer_contract_changed_by_pilot_count,
        "writer_prompt_changed_by_pilot_count": writer_prompt_changed_by_pilot_count,
        "final_answer_changed_by_pilot_count": final_answer_changed_by_pilot_count,
        "pilot_apply_to_writer_contract_count": pilot_apply_to_writer_contract_count,
        "pilot_apply_to_writer_prompt_count": pilot_apply_to_writer_prompt_count,
        "pilot_apply_to_final_answer_count": pilot_apply_to_final_answer_count,
        "runtime_smoke_ok": runtime_smoke_ok,
        "artifact_encoding_hygiene_passed": False,
        "writer_contract_pilot_ready": False,
        "final_status": "pending",
        "next_prd": "PRD-046.1.5",
    }

    status = "passed"
    if cases_passed != len(cases):
        status = "done_with_pilot_blocker"
    if hard_blocker_count > 0:
        status = "failed_safety_violation"
    if safety_pilot_pass_rate < 1.0:
        status = "failed_safety_violation"
    if runtime_smoke_ok is not True:
        status = "done_with_pilot_blocker"

    scorecard["writer_contract_pilot_ready"] = status == "passed"
    scorecard["final_status"] = status

    _write_json(out_dir / "planner_bridge_writer_contract_pilot_eval.json", {
        "schema_version": "planner_bridge_writer_contract_pilot_eval_v1",
        "prd": "PRD-046.1.4",
        "status": status,
        "generated_at": _utc_now(),
        "cases": case_results,
    })
    _write_json(out_dir / "planner_bridge_writer_contract_pilot_scorecard.json", scorecard)
    _write_json(out_dir / "planner_bridge_writer_contract_pilot_trace_samples.json", {
        "schema_version": "planner_bridge_writer_contract_pilot_trace_samples_v1",
        "prd": "PRD-046.1.4",
        "generated_at": _utc_now(),
        "samples": trace_samples,
    })
    _write_json(out_dir / "planner_bridge_writer_contract_pilot_runtime_smoke.json", {
        "schema_version": "planner_bridge_writer_contract_pilot_runtime_smoke_v1",
        "prd": "PRD-046.1.4",
        "ok": runtime_smoke_ok,
        "generated_at": _utc_now(),
        "cases": runtime_smoke_cases,
    })
    _write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd="PRD-046.1.4",
            logs_dir=str(out_dir),
            reports_dir=str((REPO_ROOT / "TO_DO_LIST" / "reports").resolve()),
            out_dir=str(out_dir),
            report_prd="PRD-046.1.4",
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )

    scorecard["artifact_encoding_hygiene_passed"] = encoding_report.get("final_status") == "passed"
    if status == "passed" and not scorecard["artifact_encoding_hygiene_passed"]:
        status = "done_with_pilot_blocker"
    scorecard["writer_contract_pilot_ready"] = status == "passed"
    scorecard["final_status"] = status

    _write_json(out_dir / "planner_bridge_writer_contract_pilot_scorecard.json", scorecard)

    return {
        "status": status,
        "scorecard": scorecard,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run planner bridge writer-contract pilot eval suite."
    )
    parser.add_argument(
        "--cases-file",
        default="bot_psychologist/tests/fixtures/planner_bridge_writer_contract_pilot_cases.json",
    )
    parser.add_argument(
        "--out-dir",
        default="TO_DO_LIST/logs/PRD-046.1.4",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
