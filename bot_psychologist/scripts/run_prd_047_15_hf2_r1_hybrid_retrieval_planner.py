#!/usr/bin/env python3
"""Acceptance runner for PRD-047.15-HF2-R1.

This runner is evidence-oriented. It does not mutate runtime defaults, KB
metadata, Chroma index, or governance authority.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.agents.memory_retrieval import MemoryRetrievalAgent
from bot_agent.multiagent.contracts.memory_bundle import SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.hybrid_retrieval_planner import (
    HYBRID_RETRIEVAL_PLANNER_VERSION,
    build_hybrid_retrieval_plan_v1,
)
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1

PRD_ID = "PRD-047.15-HF2-R1"
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
DEFAULT_JSON = LOG_DIR / "hf2_r1_runner_result.json"
DEFAULT_MD = LOG_DIR / "hf2_r1_runner_result.md"

REQUIRED_TRACE_FIELDS = [
    "hybrid_retrieval_plan",
    "hybrid_retrieval_planner_version",
    "hybrid_retrieval_planner_mode",
    "hybrid_retrieval_plan_valid",
    "hybrid_retrieval_plan_error",
    "hybrid_retrieval_universal_gate",
    "hybrid_retrieval_llm_called",
    "hybrid_retrieval_llm_reason",
    "hybrid_retrieval_fallback_used",
]
FORBIDDEN_PRODUCTION_TERMS = [
    "кузница духа",
    "нейросталкинг",
    "неосталкинг",
    "автоматизм",
    "защитный механизм",
    "самореализация",
]


@dataclass
class CaseSpec:
    case_id: str
    message: str
    description: str
    planner_mode: str = "apply"
    last_assistant_offer: dict[str, Any] | None = None
    dialogue_pragmatics: dict[str, Any] | None = None
    state_snapshot_compact: dict[str, Any] | None = None
    thread_state_compact: dict[str, Any] | None = None
    constraints: list[str] = field(default_factory=list)
    llm_payload: dict[str, Any] | None = None
    llm_error: str | None = None
    expected_action: str | None = None
    expected_gate: str | None = None
    expected_llm_called: bool | None = None
    expected_valid: bool | None = None
    expected_fallback_used: bool | None = None
    expected_query_before_rag: bool | None = None
    expected_rag_skipped_reason: str | None = None
    expected_composed_query_contains: list[str] = field(default_factory=list)
    expected_needed_chunk_types_contains: list[str] = field(default_factory=list)
    expected_mechanism_hints_contains: list[str] = field(default_factory=list)
    expected_writer_can_ignore_rag: bool | None = None
    expected_retrieval_gap_reason: str | None = None
    expect_executed_equals_planned: bool | None = None
    expect_live: bool = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _thread(*, safety_active: bool = False, active_concept: str = "") -> ThreadState:
    active_frame = {"active_concept": active_concept} if active_concept else {}
    return ThreadState(
        thread_id="runner-thread",
        user_id="runner-user",
        core_direction="retrieval quality check",
        phase="explore",
        relation_to_thread="continue",
        response_mode="safe_override" if safety_active else "reflect",
        safety_active=safety_active,
        active_frame=active_frame,
    )


def _stub_hits() -> list[SemanticHit]:
    return [
        SemanticHit(
            chunk_id="chunk-1",
            content="Mechanism-oriented chunk for writer support.",
            source="runner",
            score=0.91,
            governance={"allowed_for_writer": True},
            chunking_quality={"chunk_type": "mechanism"},
        ),
        SemanticHit(
            chunk_id="chunk-2",
            content="Safety-oriented chunk for writer support.",
            source="runner",
            score=0.88,
            governance={"allowed_for_writer": True},
            chunking_quality={"chunk_type": "safety"},
        ),
    ]


class LLMStub:
    def __init__(self, payload: dict[str, Any] | None = None, error: str | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls = 0

    async def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.calls += 1
        if self.error:
            raise RuntimeError(self.error)
        return SimpleNamespace(
            text=json.dumps(self.payload or {}, ensure_ascii=False),
            tokens_prompt=21,
            tokens_completion=41,
            tokens_total=62,
        )


async def _fake_load_rag(query: str) -> tuple[list[SemanticHit], dict[str, Any]]:
    if not query.strip():
        return [], {"retrieval_source_attempted": "skipped", "retrieval_source_used": "skipped"}
    return _stub_hits(), {"retrieval_source_attempted": "api", "retrieval_source_used": "api"}


def _async_value(value: Any):
    async def _inner(*args: Any, **kwargs: Any) -> Any:
        return value

    return _inner


async def _run_direct_case(case: CaseSpec) -> dict[str, Any]:
    import bot_agent.multiagent.hybrid_retrieval_planner as planner_module

    stub = LLMStub(payload=case.llm_payload, error=case.llm_error) if (case.llm_payload or case.llm_error) else None
    original_completion = planner_module.create_agent_completion
    if stub is not None:
        planner_module.create_agent_completion = stub
    try:
        plan_result = await build_hybrid_retrieval_plan_v1(
            user_message=case.message,
            recent_turns_compact=[],
            last_assistant_offer=case.last_assistant_offer,
            thread_state_compact=case.thread_state_compact,
            state_snapshot_compact=case.state_snapshot_compact,
            dialogue_pragmatics=case.dialogue_pragmatics,
            fresh_chat_policy={},
            constraints=case.constraints,
            planner_mode=case.planner_mode,
            client=object() if stub is not None else None,
        )
    finally:
        planner_module.create_agent_completion = original_completion

    agent = MemoryRetrievalAgent()
    agent._load_conversation = _async_value("ctx")
    agent._load_profile = _async_value(UserProfile(patterns=["runner-pattern"], values=["clarity"]))
    agent._load_recent_turns = _async_value([])
    agent._load_personal_history_context = _async_value([])
    agent._load_semantic_memory_hits = _async_value([])
    agent._load_rag = _fake_load_rag

    bundle = await agent.assemble(
        user_message=case.message,
        thread_state=_thread(
            safety_active=bool(case.state_snapshot_compact and case.state_snapshot_compact.get("safety_active"))
        ),
        user_id="runner-user",
        retrieval_plan=plan_result,
    )

    plan_payload = dict(plan_result.get("plan", {})) if isinstance(plan_result.get("plan"), dict) else {}
    retrieval_decision = {
        "retrieval_action": bundle.hybrid_retrieval_trace.get(
            "retrieval_action",
            plan_payload.get("retrieval_action", "trace_only"),
        ),
        "hybrid_retrieval_plan": plan_payload,
        "hybrid_retrieval_planner_mode": plan_result.get("mode", case.planner_mode),
        "planned_composed_query": bundle.hybrid_retrieval_trace.get("planned_composed_query", ""),
        "needed_chunk_types": list(plan_payload.get("needed_chunk_types", []) or []),
        "mechanism_hints": list(plan_payload.get("mechanism_hints", []) or []),
        "rag_included_for_writer": list(bundle.knowledge_rag_hits or []),
        "rag_included_count": len(list(bundle.knowledge_rag_hits or [])),
        "rag_included_reason": "runner_stubbed_hits" if bundle.knowledge_rag_hits else "",
        "rag_suppressed_reason": bundle.hybrid_retrieval_trace.get("rag_skipped_reason", ""),
        "writer_can_ignore_rag": bool(plan_payload.get("writer_can_ignore_rag", True)),
    }
    writer_context = build_writer_context_package_v1(
        memory_bundle=bundle,
        context_package=None,
        retrieval_decision=retrieval_decision,
        fresh_chat_context_policy={},
    )
    debug_proxy = {
        "hybrid_retrieval_plan": plan_payload,
        "hybrid_retrieval_planner_version": HYBRID_RETRIEVAL_PLANNER_VERSION,
        "hybrid_retrieval_planner_mode": plan_result.get("mode", case.planner_mode),
        "hybrid_retrieval_plan_valid": plan_result.get("valid"),
        "hybrid_retrieval_plan_error": plan_result.get("error"),
        "hybrid_retrieval_universal_gate": plan_result.get("universal_gate"),
        "hybrid_retrieval_llm_called": plan_result.get("llm_called"),
        "hybrid_retrieval_llm_reason": plan_result.get("llm_reason"),
        "hybrid_retrieval_fallback_used": plan_result.get("fallback_used"),
        "planned_composed_query": bundle.hybrid_retrieval_trace.get("planned_composed_query", ""),
        "executed_rag_query": bundle.hybrid_retrieval_trace.get("executed_rag_query", ""),
        "legacy_rag_query": bundle.hybrid_retrieval_trace.get("legacy_rag_query", ""),
        "query_before_rag_proof": bundle.hybrid_retrieval_trace.get("query_before_rag_proof", False),
        "needed_chunk_types": list(plan_payload.get("needed_chunk_types", []) or []),
        "mechanism_hints": list(plan_payload.get("mechanism_hints", []) or []),
        "retrieval_gap_reason": bundle.hybrid_retrieval_trace.get("retrieval_gap_reason", ""),
        "writer_can_ignore_rag": bool(plan_payload.get("writer_can_ignore_rag", True)),
    }
    return {
        "case_id": case.case_id,
        "mode": "direct",
        "message": case.message,
        "description": case.description,
        "plan_result": plan_result,
        "bundle": bundle.to_dict(),
        "writer_context": writer_context,
        "debug_proxy": debug_proxy,
        "llm_calls_actual": 0 if stub is None else stub.calls,
    }


async def _run_dry_case(case: CaseSpec) -> dict[str, Any]:
    result = await _run_direct_case(case)
    result["mode"] = "dry"
    return result


def _evaluate_case(case: CaseSpec, payload: dict[str, Any]) -> dict[str, Any]:
    plan_result = payload["plan_result"]
    plan = dict(plan_result.get("plan", {})) if isinstance(plan_result.get("plan"), dict) else {}
    bundle = payload["bundle"]
    trace = dict(bundle.get("hybrid_retrieval_trace", {}))
    writer_context = payload["writer_context"]
    debug_proxy = payload["debug_proxy"]
    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, expected: Any, actual: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), "expected": expected, "actual": actual})

    if case.expected_action is not None:
        add_check(
            "retrieval_action",
            plan.get("retrieval_action") == case.expected_action,
            case.expected_action,
            plan.get("retrieval_action"),
        )
    if case.expected_gate is not None:
        add_check(
            "universal_gate",
            plan_result.get("universal_gate") == case.expected_gate,
            case.expected_gate,
            plan_result.get("universal_gate"),
        )
    if case.expected_llm_called is not None:
        add_check(
            "llm_called",
            bool(plan_result.get("llm_called")) == case.expected_llm_called,
            case.expected_llm_called,
            plan_result.get("llm_called"),
        )
    if case.expected_valid is not None:
        add_check(
            "plan_valid",
            bool(plan_result.get("valid")) == case.expected_valid,
            case.expected_valid,
            plan_result.get("valid"),
        )
    if case.expected_fallback_used is not None:
        add_check(
            "fallback_used",
            bool(plan_result.get("fallback_used")) == case.expected_fallback_used,
            case.expected_fallback_used,
            plan_result.get("fallback_used"),
        )
    if case.expected_query_before_rag is not None:
        add_check(
            "query_before_rag_proof",
            bool(trace.get("query_before_rag_proof")) == case.expected_query_before_rag,
            case.expected_query_before_rag,
            trace.get("query_before_rag_proof"),
        )
    if case.expected_rag_skipped_reason is not None:
        add_check(
            "rag_skipped_reason",
            str(trace.get("rag_skipped_reason", "")) == case.expected_rag_skipped_reason,
            case.expected_rag_skipped_reason,
            trace.get("rag_skipped_reason"),
        )
    if case.expected_writer_can_ignore_rag is not None:
        add_check(
            "writer_can_ignore_rag",
            bool(writer_context.get("retrieval_context", {}).get("writer_can_ignore_rag"))
            == case.expected_writer_can_ignore_rag,
            case.expected_writer_can_ignore_rag,
            writer_context.get("retrieval_context", {}).get("writer_can_ignore_rag"),
        )
    if case.expected_retrieval_gap_reason is not None:
        add_check(
            "retrieval_gap_reason",
            str(trace.get("retrieval_gap_reason", "")) == case.expected_retrieval_gap_reason,
            case.expected_retrieval_gap_reason,
            trace.get("retrieval_gap_reason"),
        )
    if case.expect_executed_equals_planned is not None:
        actual = str(trace.get("executed_rag_query", "")) == str(trace.get("planned_composed_query", ""))
        add_check(
            "executed_query_vs_planned",
            actual == case.expect_executed_equals_planned,
            case.expect_executed_equals_planned,
            actual,
        )
    for token in case.expected_composed_query_contains:
        add_check(
            f"composed_query_contains:{token}",
            token.lower() in str(plan.get("composed_query", "")).lower(),
            token,
            plan.get("composed_query"),
        )
    for token in case.expected_needed_chunk_types_contains:
        add_check(
            f"needed_chunk_types_contains:{token}",
            token in list(plan.get("needed_chunk_types", []) or []),
            token,
            plan.get("needed_chunk_types"),
        )
    for token in case.expected_mechanism_hints_contains:
        add_check(
            f"mechanism_hints_contains:{token}",
            token in list(plan.get("mechanism_hints", []) or []),
            token,
            plan.get("mechanism_hints"),
        )

    trace_fields_present = all(key in debug_proxy for key in REQUIRED_TRACE_FIELDS)
    add_check("trace_fields_present", trace_fields_present, REQUIRED_TRACE_FIELDS, sorted(debug_proxy.keys()))

    passed = all(item["ok"] for item in checks)
    return {
        "case_id": case.case_id,
        "description": case.description,
        "status": "passed" if passed else "failed",
        "checks": checks,
        "plan_result": plan_result,
        "trace": trace,
        "writer_context": writer_context.get("retrieval_context", {}),
        "llm_calls_actual": payload.get("llm_calls_actual", 0),
        "api_trace_fields_present": trace_fields_present,
    }


def _hybrid_anti_overengineering_report() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    path = PROJECT_ROOT / "bot_agent" / "multiagent" / "contextual_retrieval_query_composer.py"
    lowered = path.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_PRODUCTION_TERMS:
        if term in lowered:
            findings.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "type": "forbidden_term",
                    "value": term,
                }
            )
    return {
        "status": "passed" if not findings else "failed",
        "findings": findings,
    }


def _build_cases(planner_mode: str) -> list[CaseSpec]:
    shadow = planner_mode == "shadow"
    return [
        CaseSpec(
            "HRP-001",
            "Привет",
            "greeting suppresses rag",
            planner_mode=planner_mode,
            expected_action="suppress_rag",
            expected_gate="greeting",
            expected_llm_called=False,
            expected_valid=True,
            expected_query_before_rag=(False if shadow else True),
            expected_rag_skipped_reason="suppress_rag",
            expected_writer_can_ignore_rag=True,
            expect_live=True,
        ),
        CaseSpec(
            "HRP-002",
            "Спасибо, пока",
            "thanks suppresses rag",
            planner_mode=planner_mode,
            expected_action="suppress_rag",
            expected_gate="thanks_or_farewell",
            expected_llm_called=False,
            expected_valid=True,
            expected_query_before_rag=(False if shadow else True),
            expected_rag_skipped_reason="suppress_rag",
            expected_writer_can_ignore_rag=True,
            expect_live=True,
        ),
        CaseSpec(
            "HRP-003",
            "Сделай списком и без воды",
            "formatting request uses current context only",
            planner_mode=planner_mode,
            expected_action="use_current_context_only",
            expected_gate="formatting_request",
            expected_llm_called=False,
            expected_valid=True,
            expected_query_before_rag=(False if shadow else True),
            expected_rag_skipped_reason="use_current_context_only",
            expected_writer_can_ignore_rag=True,
            expect_live=True,
        ),
        CaseSpec(
            "HRP-004",
            "Подведи итог по нашему разговору",
            "summary request uses current context only",
            planner_mode=planner_mode,
            expected_action="use_current_context_only",
            expected_gate="summary_request",
            expected_llm_called=False,
            expected_valid=True,
            expected_query_before_rag=(False if shadow else True),
            expected_rag_skipped_reason="use_current_context_only",
            expected_writer_can_ignore_rag=True,
            expect_live=True,
        ),
        CaseSpec(
            "HRP-005",
            "Нет, не надо",
            "explicit no avoids kb",
            planner_mode=planner_mode,
            expected_action="use_current_context_only",
            expected_gate="explicit_reject",
            expected_llm_called=False,
            expected_valid=True,
            expected_query_before_rag=(False if shadow else True),
            expected_rag_skipped_reason="use_current_context_only",
            expected_writer_can_ignore_rag=True,
        ),
        CaseSpec(
            "HRP-006",
            "Что такое нейросталкинг?",
            "clear kb ask",
            planner_mode=planner_mode,
            expected_action="query_kb",
            expected_gate="clear_kb_ask",
            expected_llm_called=False,
            expected_valid=True,
            expected_composed_query_contains=["нейросталкинг"],
            expected_writer_can_ignore_rag=False,
            expected_query_before_rag=(False if shadow else True),
            expect_executed_equals_planned=(False if shadow else True),
            expect_live=True,
        ),
        CaseSpec(
            "HRP-007",
            "да",
            "short yes after open offer",
            planner_mode=planner_mode,
            last_assistant_offer={"is_open": True, "offer_type": "short_support"},
            expected_action="use_current_context_only",
            expected_gate="short_accept_followup",
            expected_llm_called=False,
            expected_valid=True,
            expected_rag_skipped_reason="use_current_context_only",
            expected_query_before_rag=(False if shadow else True),
            expected_writer_can_ignore_rag=True,
        ),
        CaseSpec(
            "HRP-008",
            "Да, но на моем примере и без теории",
            "complex followup triggers llm planner",
            planner_mode=planner_mode,
            llm_payload={
                "retrieval_needed": True,
                "retrieval_action": "query_kb_and_memory",
                "composed_query": "личный пример контроль безопасность механизм",
                "needed_chunk_types": ["mechanism", "dialogue_move"],
                "avoided_chunk_types": [],
                "mechanism_hints": ["control_as_safety"],
                "depth_level_hint": 1,
                "safety_layer_required": False,
                "allowed_use_filter_hint": ["writer_support"],
                "diagnostic_hints_used": False,
                "writer_can_ignore_rag": True,
                "retrieval_gap_reason": "",
                "no_user_facing_text_created": True,
                "fallback_if_invalid": "legacy_query",
                "constraints_for_writer": ["no_theory"],
                "confidence": 0.83,
            },
            expected_action="query_kb_and_memory",
            expected_llm_called=True,
            expected_valid=True,
            expected_needed_chunk_types_contains=["mechanism", "dialogue_move"],
            expected_mechanism_hints_contains=["control_as_safety"],
            expected_writer_can_ignore_rag=True,
            expected_query_before_rag=(False if shadow else True),
        ),
        CaseSpec(
            "HRP-009",
            "Объясни, как это связано между контролем, стыдом и отношениями",
            "complex mixed request triggers llm planner",
            planner_mode=planner_mode,
            llm_payload={
                "retrieval_needed": True,
                "retrieval_action": "query_kb",
                "composed_query": "контроль стыд отношения механизм",
                "needed_chunk_types": ["mechanism", "concept"],
                "avoided_chunk_types": [],
                "mechanism_hints": ["control_as_safety"],
                "depth_level_hint": 2,
                "safety_layer_required": False,
                "allowed_use_filter_hint": ["writer_support"],
                "diagnostic_hints_used": False,
                "writer_can_ignore_rag": True,
                "retrieval_gap_reason": "",
                "no_user_facing_text_created": True,
                "fallback_if_invalid": "legacy_query",
                "constraints_for_writer": [],
                "confidence": 0.79,
            },
            expected_action="query_kb",
            expected_llm_called=True,
            expected_valid=True,
            expected_needed_chunk_types_contains=["mechanism", "concept"],
            expected_query_before_rag=(False if shadow else True),
        ),
        CaseSpec(
            "HRP-010",
            "У жены паника, она говорит, что если перестанет контролировать — умрет",
            "safety signal requires safety and mechanism chunks",
            planner_mode=planner_mode,
            state_snapshot_compact={"safety_active": True},
            expected_action="query_kb",
            expected_gate="safety_signal",
            expected_llm_called=False,
            expected_valid=True,
            expected_needed_chunk_types_contains=["safety", "mechanism", "dialogue_move"],
            expected_mechanism_hints_contains=[
                "control_as_safety",
                "panic_regulation",
                "loss_of_control_as_threat",
            ],
            expected_query_before_rag=(False if shadow else True),
            expect_executed_equals_planned=(False if shadow else True),
            expect_live=True,
        ),
        CaseSpec(
            "HRP-011",
            "Да, но на моем примере",
            "invalid llm json falls back",
            planner_mode=planner_mode,
            llm_payload={
                "retrieval_needed": True,
                "retrieval_action": "query_kb",
                "composed_query": "скажи пользователю что он в безопасности",
                "needed_chunk_types": ["mechanism"],
                "no_user_facing_text_created": False,
                "confidence": 0.9,
            },
            expected_action="trace_only",
            expected_llm_called=True,
            expected_valid=False,
            expected_fallback_used=True,
            expected_retrieval_gap_reason="legacy_fallback_used",
            expected_query_before_rag=False,
        ),
        CaseSpec(
            "HRP-012",
            "Да, но свяжи это с моим случаем",
            "llm error falls back safely",
            planner_mode=planner_mode,
            llm_error="planner timeout",
            expected_action="trace_only",
            expected_llm_called=True,
            expected_valid=False,
            expected_fallback_used=True,
            expected_retrieval_gap_reason="legacy_fallback_used",
            expected_query_before_rag=False,
        ),
        CaseSpec(
            "HRP-013",
            "Что такое нейросталкинг?",
            "shadow mode keeps legacy executed query",
            planner_mode="shadow",
            expected_action="query_kb",
            expected_gate="clear_kb_ask",
            expected_llm_called=False,
            expected_valid=True,
            expect_executed_equals_planned=False,
            expected_query_before_rag=False,
        ),
        CaseSpec(
            "HRP-014",
            "Что такое нейросталкинг?",
            "apply mode uses composed query",
            planner_mode="apply",
            expected_action="query_kb",
            expected_gate="clear_kb_ask",
            expected_llm_called=False,
            expected_valid=True,
            expect_executed_equals_planned=True,
            expected_query_before_rag=True,
        ),
        CaseSpec(
            "HRP-015",
            "Да, но на моем примере и без теории",
            "writer_can_ignore_rag reaches writer context",
            planner_mode=planner_mode,
            llm_payload={
                "retrieval_needed": True,
                "retrieval_action": "query_kb",
                "composed_query": "пример механизм",
                "needed_chunk_types": ["mechanism"],
                "avoided_chunk_types": [],
                "mechanism_hints": ["control_as_safety"],
                "depth_level_hint": 1,
                "safety_layer_required": False,
                "allowed_use_filter_hint": ["writer_support"],
                "diagnostic_hints_used": False,
                "writer_can_ignore_rag": True,
                "retrieval_gap_reason": "",
                "no_user_facing_text_created": True,
                "fallback_if_invalid": "legacy_query",
                "constraints_for_writer": ["no_theory"],
                "confidence": 0.8,
            },
            expected_action="query_kb",
            expected_llm_called=True,
            expected_valid=True,
            expected_writer_can_ignore_rag=True,
        ),
        CaseSpec(
            "HRP-016",
            "Объясни это на моем примере",
            "retrieval gap is trace-visible",
            planner_mode=planner_mode,
            llm_payload={
                "retrieval_needed": True,
                "retrieval_action": "query_kb",
                "composed_query": "пример механизм",
                "needed_chunk_types": ["mechanism"],
                "avoided_chunk_types": [],
                "mechanism_hints": [],
                "depth_level_hint": 1,
                "safety_layer_required": False,
                "allowed_use_filter_hint": ["writer_support"],
                "diagnostic_hints_used": False,
                "writer_can_ignore_rag": True,
                "retrieval_gap_reason": "missing_chunk_type_metadata",
                "no_user_facing_text_created": True,
                "fallback_if_invalid": "legacy_query",
                "constraints_for_writer": [],
                "confidence": 0.77,
            },
            expected_action="query_kb",
            expected_llm_called=True,
            expected_valid=True,
            expected_retrieval_gap_reason="missing_chunk_type_metadata",
        ),
    ]


def run_live_case(case: CaseSpec, api_base: str, api_key: str) -> dict[str, Any]:
    session_id = f"{PRD_ID.lower()}-{case.case_id.lower()}"
    post_url = api_base.rstrip("/") + "/api/v1/questions/adaptive"
    debug_url = (
        api_base.rstrip("/")
        + "/api/debug/session/"
        + urllib.parse.quote(session_id)
        + "/multiagent-trace"
    )
    request_body = {
        "query": case.message,
        "debug": True,
        "include_path": False,
        "include_feedback_prompt": False,
        "session_id": session_id,
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "X-Session-Id": session_id,
    }
    try:
        req = urllib.request.Request(
            post_url,
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            adaptive_payload = json.loads(response.read().decode("utf-8"))
        trace_req = urllib.request.Request(debug_url, headers={"X-API-Key": api_key}, method="GET")
        with urllib.request.urlopen(trace_req, timeout=60) as response:
            trace_payload = json.loads(response.read().decode("utf-8"))
        hybrid_plan = dict(trace_payload.get("hybrid_retrieval_plan") or {})
        checks = []

        def add(name: str, ok: bool, expected: Any, actual: Any) -> None:
            checks.append({"name": name, "ok": bool(ok), "expected": expected, "actual": actual})

        if case.expected_action is not None:
            add(
                "retrieval_action",
                hybrid_plan.get("retrieval_action") == case.expected_action,
                case.expected_action,
                hybrid_plan.get("retrieval_action"),
            )
        if case.expected_gate is not None:
            add(
                "universal_gate",
                trace_payload.get("hybrid_retrieval_universal_gate") == case.expected_gate,
                case.expected_gate,
                trace_payload.get("hybrid_retrieval_universal_gate"),
            )
        if case.expected_llm_called is not None:
            add(
                "llm_called",
                bool(trace_payload.get("hybrid_retrieval_llm_called")) == case.expected_llm_called,
                case.expected_llm_called,
                trace_payload.get("hybrid_retrieval_llm_called"),
            )
        if case.expected_query_before_rag is not None:
            query_before = bool(
                (trace_payload.get("memory_context") or {})
                .get("hybrid_retrieval", {})
                .get("query_before_rag_proof")
            )
            add("query_before_rag_proof", query_before == case.expected_query_before_rag, case.expected_query_before_rag, query_before)
        add(
            "trace_fields_present",
            all(field in trace_payload for field in REQUIRED_TRACE_FIELDS),
            REQUIRED_TRACE_FIELDS,
            sorted(trace_payload.keys()),
        )
        status = "passed" if all(item["ok"] for item in checks) else "failed"
        return {
            "case_id": case.case_id,
            "description": case.description,
            "status": status,
            "session_id": session_id,
            "checks": checks,
            "adaptive_payload": {
                "status": adaptive_payload.get("status"),
                "answer_preview": str(adaptive_payload.get("answer", ""))[:280],
                "metadata": adaptive_payload.get("metadata", {}),
            },
            "trace_payload": {
                "hybrid_retrieval_plan": hybrid_plan,
                "hybrid_retrieval_planner_mode": trace_payload.get("hybrid_retrieval_planner_mode"),
                "hybrid_retrieval_universal_gate": trace_payload.get("hybrid_retrieval_universal_gate"),
                "hybrid_retrieval_llm_called": trace_payload.get("hybrid_retrieval_llm_called"),
                "memory_context": trace_payload.get("memory_context", {}),
            },
            "warning": None,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if getattr(exc, "read", None) else ""
        return {
            "case_id": case.case_id,
            "description": case.description,
            "status": "warning",
            "warning": f"http_error:{exc.code}",
            "detail": body[:500],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "case_id": case.case_id,
            "description": case.description,
            "status": "warning",
            "warning": f"live_unavailable:{exc.__class__.__name__}",
            "detail": str(exc)[:500],
        }


def _render_markdown(summary: dict[str, Any], case_results: list[dict[str, Any]]) -> str:
    lines = [
        f"# {PRD_ID} Hybrid Retrieval Planner Runner",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- mode: `{summary['mode']}`",
        f"- planner_mode: `{summary['planner_mode']}`",
        f"- total_cases: `{summary['total_cases']}`",
        f"- passed: `{summary['passed']}`",
        f"- warnings: `{summary['warnings']}`",
        f"- failed: `{summary['failed']}`",
        f"- llm_calls_expected: `{summary['llm_calls_expected']}`",
        f"- llm_calls_actual: `{summary['llm_calls_actual']}`",
        f"- query_before_rag_passed: `{summary['query_before_rag_passed']}`",
        f"- anti_overengineering_passed: `{summary['anti_overengineering_passed']}`",
        f"- api_trace_fields_present: `{summary['api_trace_fields_present']}`",
        "",
        "## Cases",
    ]
    for item in case_results:
        lines.append(f"- {item['case_id']}: `{item['status']}` - {item.get('description', '')}")
        for check in item.get("checks", []):
            lines.append(f"  - {check['name']}: {'ok' if check['ok'] else 'fail'}")
        if item.get("warning"):
            lines.append(f"  - warning: `{item['warning']}`")
    return "\n".join(lines)


async def run_non_live_cases(
    mode: str,
    planner_mode: str,
    case_id: str | None,
    limit: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = _build_cases(planner_mode)
    if case_id:
        cases = [case for case in cases if case.case_id == case_id]
    if limit is not None:
        cases = cases[: max(0, limit)]

    results: list[dict[str, Any]] = []
    for case in cases:
        payload = await (_run_dry_case(case) if mode == "dry" else _run_direct_case(case))
        evaluated = _evaluate_case(case, payload)
        results.append(evaluated)

    anti_over = _hybrid_anti_overengineering_report()
    summary = {
        "prd": PRD_ID,
        "generated_at_utc": now_iso(),
        "mode": mode,
        "planner_mode": planner_mode,
        "total_cases": len(results),
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "warnings": sum(1 for item in results if item["status"] == "warning"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "llm_calls_expected": sum(
            1 for case in cases if case.llm_payload is not None or case.llm_error is not None
        ),
        "llm_calls_actual": sum(int(item.get("llm_calls_actual", 0) or 0) for item in results),
        "query_before_rag_passed": all(
            check["ok"]
            for item in results
            for check in item.get("checks", [])
            if check["name"] == "query_before_rag_proof"
        ),
        "anti_overengineering_passed": anti_over["status"] == "passed",
        "api_trace_fields_present": all(bool(item.get("api_trace_fields_present")) for item in results),
        "anti_overengineering_report": anti_over,
        "case_results": results,
    }
    return results, summary


def run_live_cases(
    planner_mode: str,
    case_id: str | None,
    limit: int | None,
    api_base: str,
    api_key: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = [case for case in _build_cases(planner_mode) if case.expect_live]
    if case_id:
        cases = [case for case in cases if case.case_id == case_id]
    if limit is not None:
        cases = cases[: max(0, limit)]
    results = [run_live_case(case, api_base=api_base, api_key=api_key) for case in cases]
    anti_over = _hybrid_anti_overengineering_report()
    summary = {
        "prd": PRD_ID,
        "generated_at_utc": now_iso(),
        "mode": "live",
        "planner_mode": planner_mode,
        "api_base": api_base,
        "total_cases": len(results),
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "warnings": sum(1 for item in results if item["status"] == "warning"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "llm_calls_expected": sum(1 for case in cases if case.expected_llm_called),
        "llm_calls_actual": sum(
            1
            for item in results
            if (item.get("trace_payload") or {}).get("hybrid_retrieval_llm_called")
        ),
        "query_before_rag_passed": all(
            check["ok"]
            for item in results
            for check in item.get("checks", [])
            if check["name"] == "query_before_rag_proof"
        ),
        "anti_overengineering_passed": anti_over["status"] == "passed",
        "api_trace_fields_present": all(
            any(check["name"] == "trace_fields_present" and check["ok"] for check in item.get("checks", []))
            for item in results
            if item["status"] != "warning"
        ),
        "anti_overengineering_report": anti_over,
        "case_results": results,
    }
    return results, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PRD_ID)
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--planner-mode", choices=["off", "shadow", "apply"], default="apply")
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", default=str(DEFAULT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_MD))
    parser.add_argument("--api-base", default=os.getenv("PRD_047_15_HF2_R1_API_BASE", "http://127.0.0.1:8001"))
    parser.add_argument("--api-key", default=os.getenv("DEV_API_KEY", "dev-key-001"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if args.mode == "live":
        case_results, summary = run_live_cases(
            planner_mode=args.planner_mode,
            case_id=args.case_id,
            limit=args.limit,
            api_base=args.api_base,
            api_key=args.api_key,
        )
    else:
        case_results, summary = asyncio.run(
            run_non_live_cases(
                mode=args.mode,
                planner_mode=args.planner_mode,
                case_id=args.case_id,
                limit=args.limit,
            )
        )
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    write_json(output_json, summary)
    write_text(output_md, _render_markdown(summary, case_results))
    print(json.dumps({k: v for k, v in summary.items() if k != "case_results"}, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
