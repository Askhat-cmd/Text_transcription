"""Minimal multi-agent orchestrator for PRD-017 bootstrap."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone

from bot_agent.config import config
from .agents.memory_retrieval import memory_retrieval_agent
from .agents.state_analyzer import state_analyzer_agent
from .agents.thread_manager import THREAD_DIAGNOSTICS_VERSION, thread_manager_agent
from .agents.validator_agent import validator_agent
from .agents.writer_agent import writer_agent
from .active_line import build_active_line_state
from .context_assembly import (
    CONTEXT_ASSEMBLY_TRACE_VERSION,
    build_context_assembly_package_v1,
)
from .contextual_retrieval_query_composer import (
    build_contextual_retrieval_query_composer_v1,
    merge_composer_into_retrieval_decision_v1,
)
from .contracts.writer_contract import WriterContract
from .contracts.thread_state import ThreadState
from .diagnostic_center import DIAGNOSTIC_CARD_VERSION, build_diagnostic_card_v1
from .diagnostic_center_shadow import build_diagnostic_center_shadow_v1
from .dialogue_act_resolver import build_dialogue_act_resolution_v1
from .dialogue_pragmatics import (
    build_contextual_retrieval_decision_v1,
    build_dialogue_pragmatics_v1,
)
from .dialogue_style_state import (
    build_dialogue_style_state_v1,
    finalize_dialogue_style_state_v1,
)
from .dialogue_policy import (
    apply_active_concept_continuation,
    build_effective_dialogue_policy,
    detect_expansion_request,
    detect_repair_and_expand_request,
    normalize_dialogue_profile,
)
from .answer_obligation_resolver import build_answer_obligation_resolver_v1
from .final_answer_directive import build_final_answer_directive_v1
from .final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1
from .fresh_chat_context_policy import (
    FRESH_CHAT_CONTEXT_POLICY_VERSION,
    build_fresh_chat_context_policy_v1,
)
from .hybrid_retrieval_planner import (
    HYBRID_RETRIEVAL_PLANNER_VERSION,
    build_hybrid_retrieval_plan_v1,
)
from .knowledge_policy import build_safe_knowledge_debug_detail_v1
from .knowledge_answer_routing_guard import build_knowledge_answer_routing_guard
from .live_turn_evidence import build_live_turn_evidence_v1
from .overlay_shadow_trace import (
    build_overlay_shadow_trace,
    get_overlay_shadow_trace_settings,
)
from .planner_bridge_compliance_shadow import (
    build_planner_bridge_compliance_runtime_shadow_v1,
)
from .planner_bridge_writer_contract_pilot import (
    build_planner_bridge_writer_contract_pilot_runtime_shadow_v1,
)
from .philosophy_kernel import build_philosophy_kernel_runtime_payload
from .planner_drift_guard import (
    PLANNER_DRIFT_GUARD_VERSION,
    build_planner_drift_check,
)
from .planner_drift_monitor import (
    get_planner_drift_summary,
    record_planner_drift_check,
)
from .prompt_constraint_pilot_runtime import (
    build_prompt_constraint_pilot_runtime_decision_v1,
)
from .quality_trace import QUALITY_TRACE_VERSION, build_quality_trace
from .response_planner import (
    RESPONSE_PLANNER_VERSION,
    build_response_planner_decision,
    build_response_planner_fallback_decision,
)
from .thread_storage import thread_storage
from .last_assistant_offer_tracker import (
    build_last_assistant_offer_v1,
    update_last_assistant_offer_after_answer_v1,
)
from .unanswered_question_tracker import (
    build_unanswered_question_state_v1,
    update_unanswered_question_state_after_answer_v1,
)
from .unified_dialogue_profile import build_unified_dialogue_profile_v1
from .writer_prompt_replay import build_writer_prompt_replay_runtime_shadow_v1


logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Coordinates StateSnapshot -> ThreadManager -> Memory -> Writer."""

    def __init__(self) -> None:
        self.pipeline_version = "multiagent_v1"
        self._agent_metrics: dict[str, dict] = {
            "state_analyzer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "thread_manager": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "memory_retrieval": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "writer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
            "validator": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
        }
        self._agent_traces: list[dict] = []

    def _record_agent_metric(
        self,
        *,
        agent_id: str,
        latency_ms: int,
        user_id: str,
        input_preview: str,
        output_preview: str = "",
        error: str | None = None,
    ) -> None:
        metric = self._agent_metrics.setdefault(
            agent_id,
            {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
        )
        metric["call_count"] = int(metric.get("call_count", 0)) + 1
        metric["total_ms"] = int(metric.get("total_ms", 0)) + int(latency_ms)
        if error:
            metric["error_count"] = int(metric.get("error_count", 0)) + 1
        metric["last_run"] = datetime.now(timezone.utc).isoformat()
        self._agent_traces.append(
            {
                "agent_id": agent_id,
                "request_id": "",
                "user_id": user_id,
                "input_preview": input_preview[:300],
                "output_preview": output_preview[:300],
                "latency_ms": int(latency_ms),
                "error": error,
                "timestamp": metric["last_run"],
            }
        )
        if len(self._agent_traces) > 200:
            self._agent_traces = self._agent_traces[-200:]

    @staticmethod
    def _has_cyrillic(text: str) -> bool:
        return any(("А" <= ch <= "я") or ch in {"Ё", "ё"} for ch in text)

    @staticmethod
    def _looks_like_mojibake(text: str) -> bool:
        # Typical UTF-8->cp1251 mojibake contains many capital 'Р'/'С' markers.
        marker_count = text.count("Р") + text.count("С")
        return marker_count >= 3 and marker_count > max(2, len(text) // 10)

    def _normalize_query(self, query: str) -> str:
        if not query:
            return query

        if self._looks_like_mojibake(query):
            try:
                repaired = query.encode("cp1251").decode("utf-8")
                if self._has_cyrillic(repaired) and not self._looks_like_mojibake(repaired):
                    logger.warning("[MULTIAGENT] query mojibake repaired")
                    return repaired
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

        # Don't touch already-correct Cyrillic text.
        if self._has_cyrillic(query):
            return query

        # Attempt to repair cp1251/latin-1 mojibake from shell environments.
        try:
            repaired = query.encode("latin-1").decode("cp1251")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return query

        if self._has_cyrillic(repaired):
            logger.warning("[MULTIAGENT] query encoding repaired")
            return repaired
        return query

    async def run(self, *, query: str, user_id: str) -> dict:
        query = self._normalize_query(query)
        t_total_start = time.perf_counter()

        current_thread = thread_storage.load_active(user_id)
        archived_threads = thread_storage.load_archived(user_id)

        t0 = time.perf_counter()
        state_snapshot = await state_analyzer_agent.analyze(
            user_message=query,
            previous_thread=current_thread,
        )
        t_state = int((time.perf_counter() - t0) * 1000)
        state_debug = (
            state_analyzer_agent.last_debug
            if isinstance(getattr(state_analyzer_agent, "last_debug", None), dict)
            else {}
        )
        self._record_agent_metric(
            agent_id="state_analyzer",
            latency_ms=t_state,
            user_id=user_id,
            input_preview=query,
            output_preview=f"state={state_snapshot.nervous_state}; intent={state_snapshot.intent}",
            error=str(state_debug.get("error")) if state_debug.get("error") else None,
        )

        t0 = time.perf_counter()
        updated_thread = await thread_manager_agent.update(
            user_message=query,
            state_snapshot=state_snapshot,
            user_id=user_id,
            current_thread=current_thread,
            archived_threads=archived_threads,
        )
        thread_debug = (
            thread_manager_agent.last_debug
            if isinstance(getattr(thread_manager_agent, "last_debug", None), dict)
            else {}
        )
        t_thread = int((time.perf_counter() - t0) * 1000)
        self._record_agent_metric(
            agent_id="thread_manager",
            latency_ms=t_thread,
            user_id=user_id,
            input_preview=query,
            output_preview=f"thread={updated_thread.thread_id}; phase={updated_thread.phase}",
        )
        if updated_thread.relation_to_thread == "new_thread" and current_thread is not None:
            thread_storage.archive_thread(current_thread, reason="new_thread")
        thread_storage.save_active(updated_thread)

        previous_dialogue_state_for_retrieval = (
            dict(current_thread.active_frame.get("dialogue_state", {}))
            if current_thread is not None
            and isinstance(getattr(current_thread, "active_frame", None), dict)
            and isinstance(current_thread.active_frame.get("dialogue_state"), dict)
            else {}
        )
        pre_retrieval_last_offer = (
            dict(previous_dialogue_state_for_retrieval.get("last_assistant_offer", {}))
            if isinstance(previous_dialogue_state_for_retrieval.get("last_assistant_offer"), dict)
            else (
                dict(current_thread.active_frame.get("last_assistant_offer", {}))
                if current_thread is not None
                and isinstance(getattr(current_thread, "active_frame", None), dict)
                and isinstance(current_thread.active_frame.get("last_assistant_offer"), dict)
                else {}
            )
        )
        pre_retrieval_composer = build_contextual_retrieval_query_composer_v1(
            user_message=query,
            last_assistant_offer=pre_retrieval_last_offer,
            thread_state=(
                dict(updated_thread.active_frame)
                if isinstance(updated_thread.active_frame, dict)
                else {}
            ),
        )
        retrieval_thread = ThreadState.from_dict(updated_thread.to_dict())
        planner_client_getter = getattr(state_analyzer_agent, "_get_client", None)
        planner_client = planner_client_getter() if callable(planner_client_getter) else None
        hybrid_retrieval_plan = await build_hybrid_retrieval_plan_v1(
            user_message=query,
            recent_turns_compact=[],
            last_assistant_offer=pre_retrieval_last_offer,
            thread_state_compact={
                "thread_id": str(updated_thread.thread_id or ""),
                "phase": str(updated_thread.phase or ""),
                "response_mode": str(updated_thread.response_mode or ""),
                "core_direction": str(updated_thread.core_direction or "")[:200],
                "open_loops": [str(item) for item in list(updated_thread.open_loops or [])[:2]],
                "active_concept": str(
                    dict(updated_thread.active_frame).get("active_concept", "")
                    if isinstance(updated_thread.active_frame, dict)
                    else ""
                ),
                "safety_active": bool(updated_thread.safety_active),
            },
            state_snapshot_compact={
                "nervous_state": str(state_snapshot.nervous_state or ""),
                "intent": str(state_snapshot.intent or ""),
                "safety_active": bool(state_snapshot.safety_flag or updated_thread.safety_active),
            },
            dialogue_pragmatics={},
            fresh_chat_policy={},
            constraints=[
                item
                for item, enabled in (
                    ("no_theory", "без теории" in query.lower()),
                    ("no_practice", ("без практик" in query.lower()) or ("без упражнений" in query.lower())),
                    ("keep_brief", "короче" in query.lower()),
                )
                if enabled
            ],
            client=planner_client,
        )
        pre_retrieval_composer["hybrid_retrieval_plan"] = (
            dict(hybrid_retrieval_plan.get("plan", {}))
            if isinstance(hybrid_retrieval_plan.get("plan"), dict)
            else {}
        )
        pre_retrieval_composer["hybrid_retrieval_universal_gate"] = str(
            hybrid_retrieval_plan.get("universal_gate", "")
            or ""
        )

        t0 = time.perf_counter()
        memory_bundle = await memory_retrieval_agent.assemble(
            user_message=query,
            thread_state=retrieval_thread,
            user_id=user_id,
            retrieval_plan=hybrid_retrieval_plan,
        )
        t_memory = int((time.perf_counter() - t0) * 1000)
        self._record_agent_metric(
            agent_id="memory_retrieval",
            latency_ms=t_memory,
            user_id=user_id,
            input_preview=query,
            output_preview=f"hits={len(memory_bundle.semantic_hits)}; has_knowledge={memory_bundle.has_relevant_knowledge}",
        )
        hybrid_retrieval_trace = (
            dict(getattr(memory_bundle, "hybrid_retrieval_trace", {}) or {})
            if isinstance(getattr(memory_bundle, "hybrid_retrieval_trace", None), dict)
            else {}
        )
        overlay_shadow_settings = get_overlay_shadow_trace_settings()
        overlay_shadow = build_overlay_shadow_trace(
            user_message=query,
            retrieval_query=(
                str(hybrid_retrieval_trace.get("executed_rag_query", "") or "")
                or str(getattr(memory_bundle, "rag_query", "") or "")
            ),
            state_snapshot={
                "nervous_state": str(state_snapshot.nervous_state or ""),
                "intent": str(state_snapshot.intent or ""),
                "safety_active": bool(state_snapshot.safety_flag or updated_thread.safety_active),
            },
            thread_state={
                "thread_id": str(updated_thread.thread_id or ""),
                "phase": str(updated_thread.phase or ""),
                "response_mode": str(updated_thread.response_mode or ""),
                "active_frame": (
                    dict(updated_thread.active_frame)
                    if isinstance(updated_thread.active_frame, dict)
                    else {}
                ),
            },
            overlay_file=str(overlay_shadow_settings.get("overlay_file", "") or ""),
            enabled=bool(overlay_shadow_settings.get("enabled", False)),
            max_matches=int(overlay_shadow_settings.get("max_matches", 5) or 5),
            min_score=float(overlay_shadow_settings.get("min_score", 0.0) or 0.0),
        )
        context_package = build_context_assembly_package_v1(
            user_message=query,
            thread_state=updated_thread,
            memory_bundle=memory_bundle,
        )
        knowledge_answer_guard = build_knowledge_answer_routing_guard(
            user_message=query,
            rag_hits=list(memory_bundle.semantic_hits or []),
            response_mode=str(updated_thread.response_mode or ""),
        )
        dialogue_profile = normalize_dialogue_profile(getattr(config, "DIALOGUE_PROFILE", "safe_guided"))
        knowledge_answer_guard, active_concept = apply_active_concept_continuation(
            user_message=query,
            dialogue_profile=dialogue_profile,
            knowledge_answer_guard=knowledge_answer_guard,
            thread_active_frame=(
                dict(updated_thread.active_frame)
                if isinstance(updated_thread.active_frame, dict)
                else {}
            ),
        )
        if active_concept:
            updated_thread.active_frame = dict(updated_thread.active_frame or {})
            updated_thread.active_frame["active_concept"] = active_concept
        dialogue_policy = build_effective_dialogue_policy(
            profile=dialogue_profile,
            user_message=query,
            state_snapshot=state_snapshot,
            thread_state=updated_thread,
            knowledge_answer_guard=knowledge_answer_guard,
        )
        dialogue_policy["knowledge_answer"] = dict(knowledge_answer_guard.get("knowledge_answer", {}))
        dialogue_policy["expansion_requested"] = detect_expansion_request(query)
        dialogue_policy["repair_and_expand_requested"] = detect_repair_and_expand_request(query)
        dialogue_policy["active_concept"] = active_concept
        previous_assistant_message = ""
        for recent_turn in reversed(list(memory_bundle.recent_turns or [])):
            if not isinstance(recent_turn, dict):
                continue
            candidate = str(recent_turn.get("bot_response", "") or "").strip()
            if candidate:
                previous_assistant_message = candidate
                break
        dialogue_pragmatics = build_dialogue_pragmatics_v1(
            user_message=query,
            conversation_context=str(memory_bundle.conversation_context or ""),
            previous_assistant_message=previous_assistant_message,
            thread_state=updated_thread,
            active_frame=(
                dict(updated_thread.active_frame)
                if isinstance(updated_thread.active_frame, dict)
                else {}
            ),
            dialogue_policy=dialogue_policy,
        )
        dialogue_policy["dialogue_pragmatics"] = dict(dialogue_pragmatics)
        previous_dialogue_state = (
            dict(updated_thread.active_frame.get("dialogue_state", {}))
            if isinstance(updated_thread.active_frame, dict)
            else {}
        )
        current_turn_index = int(getattr(memory_bundle, "context_turns", 0) or 0) + 1
        last_assistant_offer = build_last_assistant_offer_v1(
            previous_state=(
                dict(previous_dialogue_state.get("last_assistant_offer", {}))
                if isinstance(previous_dialogue_state.get("last_assistant_offer"), dict)
                else {}
            ),
            previous_assistant_message=previous_assistant_message,
            dialogue_pragmatics=dialogue_pragmatics,
        )
        dialogue_act_resolution = build_dialogue_act_resolution_v1(
            user_message=query,
            dialogue_pragmatics=dialogue_pragmatics,
            last_assistant_offer=last_assistant_offer,
            knowledge_answer_guard=knowledge_answer_guard,
        )
        unanswered_question_state = build_unanswered_question_state_v1(
            previous_state=(
                dict(previous_dialogue_state.get("unanswered_question_state", {}))
                if isinstance(previous_dialogue_state.get("unanswered_question_state"), dict)
                else {}
            ),
            user_message=query,
            dialogue_act_resolution=dialogue_act_resolution,
            turn_index=current_turn_index,
        )
        dialogue_style_state = build_dialogue_style_state_v1(
            previous_state=(
                dict(previous_dialogue_state.get("dialogue_style_state", {}))
                if isinstance(previous_dialogue_state.get("dialogue_style_state"), dict)
                else {}
            ),
            user_message=query,
            dialogue_act_resolution=dialogue_act_resolution,
        )
        answer_obligation_resolution = build_answer_obligation_resolver_v1(
            dialogue_act_resolution=dialogue_act_resolution,
            last_assistant_offer=last_assistant_offer,
            unanswered_question_state=unanswered_question_state,
            dialogue_style_state=dialogue_style_state,
            dialogue_policy=dialogue_policy,
        )
        unified_dialogue_profile = build_unified_dialogue_profile_v1(
            active_profile=dialogue_profile,
            dialogue_style_state=dialogue_style_state,
        )
        dialogue_policy["unified_dialogue_profile"] = dict(unified_dialogue_profile)
        dialogue_policy["dialogue_act_resolution"] = dict(dialogue_act_resolution)
        dialogue_policy["last_assistant_offer"] = dict(last_assistant_offer)
        dialogue_policy["unanswered_question_state"] = dict(unanswered_question_state)
        dialogue_policy["dialogue_style_state"] = dict(dialogue_style_state)
        dialogue_policy["answer_obligation_resolution"] = dict(answer_obligation_resolution)
        fresh_chat_context_policy = build_fresh_chat_context_policy_v1(
            user_message=query,
            recent_turns=list(memory_bundle.recent_turns or []),
            knowledge_answer_guard=knowledge_answer_guard,
        )
        dialogue_policy["fresh_chat_context_policy"] = dict(fresh_chat_context_policy)
        if bool(dialogue_pragmatics.get("repair_user_dissatisfaction", False)):
            dialogue_policy["sarcasm_or_negative_feedback"] = True
            dialogue_policy["explicit_answer_need"] = True
        philosophy_kernel_payload = build_philosophy_kernel_runtime_payload(
            user_message=query,
            safety_active=bool(updated_thread.safety_active),
            response_mode=str(updated_thread.response_mode or ""),
            practice_allowed=bool(
                dict(knowledge_answer_guard.get("practice_gate", {})).get("practice_allowed", True)
            ),
        )
        active_line_state = build_active_line_state(
            user_message=query,
            conversation_context=str(memory_bundle.conversation_context or ""),
            response_mode=str(updated_thread.response_mode or ""),
            practice_allowed=bool(
                dict(knowledge_answer_guard.get("practice_gate", {})).get("practice_allowed", True)
            ),
            evidence_turn_ids=[],
        ).to_dict()
        response_planner_error: str | None = None
        try:
            response_planner_state = build_response_planner_decision(
                user_message=query,
                state_snapshot=state_snapshot,
                thread_state=updated_thread,
                diagnostic_card=None,
                active_line=active_line_state,
                knowledge_answer_guard=knowledge_answer_guard,
                philosophy_kernel=philosophy_kernel_payload,
                context_package=context_package,
                dialogue_policy=dialogue_policy,
            ).to_dict()
        except Exception as exc:  # noqa: BLE001
            response_planner_error = f"response_planner_build_failed:{exc.__class__.__name__}"
            response_planner_state = build_response_planner_fallback_decision(
                reason=response_planner_error,
                source_signals={
                    "response_mode": str(updated_thread.response_mode or ""),
                    "active_line_user_intent": str(active_line_state.get("user_intent", "unknown")),
                    "practice_gate_allowed": bool(
                        dict(knowledge_answer_guard.get("practice_gate", {})).get("practice_allowed", True)
                    ),
                },
            ).to_dict()
            response_planner_state["_fallback_source"] = "orchestrator_exception_fallback"
        retrieval_decision = build_contextual_retrieval_decision_v1(
            dialogue_pragmatics=dialogue_pragmatics,
            knowledge_answer_guard=knowledge_answer_guard,
            semantic_hits=list(memory_bundle.semantic_hits or []),
            fresh_chat_context_policy=fresh_chat_context_policy,
        )
        retrieval_decision["hybrid_retrieval_planner_version"] = HYBRID_RETRIEVAL_PLANNER_VERSION
        retrieval_decision["hybrid_retrieval_planner_mode"] = str(hybrid_retrieval_plan.get("mode", "shadow") or "shadow")
        retrieval_decision["hybrid_retrieval_plan"] = (
            dict(hybrid_retrieval_plan.get("plan", {}))
            if isinstance(hybrid_retrieval_plan.get("plan"), dict)
            else {}
        )
        retrieval_decision["hybrid_retrieval_plan_valid"] = bool(hybrid_retrieval_plan.get("valid", False))
        retrieval_decision["hybrid_retrieval_plan_error"] = hybrid_retrieval_plan.get("error")
        retrieval_decision["hybrid_retrieval_universal_gate"] = str(
            hybrid_retrieval_plan.get("universal_gate", "")
            or ""
        )
        retrieval_decision["hybrid_retrieval_llm_called"] = bool(hybrid_retrieval_plan.get("llm_called", False))
        retrieval_decision["hybrid_retrieval_llm_reason"] = str(
            hybrid_retrieval_plan.get("llm_reason", "")
            or ""
        )
        retrieval_decision["hybrid_retrieval_fallback_used"] = bool(
            hybrid_retrieval_plan.get("fallback_used", False)
        )
        dialogue_policy["retrieval_decision"] = dict(retrieval_decision)
        diagnostic_card = build_diagnostic_card_v1(
            user_message=query,
            state_snapshot=state_snapshot,
            thread_state=updated_thread,
            context_package=context_package,
            thread_diagnostics=thread_debug,
        )
        rules_applied = list(getattr(diagnostic_card.trace, "rules_applied", []) or [])
        behavior_request_type = "unknown"
        practice_suppressed = False
        suppression_reasons: list[str] = []
        for rule in rules_applied:
            text = str(rule or "").strip()
            if text.startswith("request_type="):
                behavior_request_type = text.split("=", 1)[1].strip() or "unknown"
            elif text.startswith("practice_suppressed="):
                practice_suppressed = text.split("=", 1)[1].strip().lower() == "true"
            elif text.startswith("practice_suppression_reason="):
                value = text.split("=", 1)[1].strip()
                if value:
                    suppression_reasons.append(value)
        diagnostic_center_shadow = build_diagnostic_center_shadow_v1(
            user_message=query,
            state_snapshot=state_snapshot,
            thread_state=updated_thread,
            context_package=context_package,
            memory_bundle=memory_bundle,
            diagnostic_card=diagnostic_card,
            thread_debug=thread_debug,
            enabled=True,
        )
        planner_bridge_shadow = build_planner_bridge_compliance_runtime_shadow_v1(
            diagnostic_center_shadow=diagnostic_center_shadow,
            diagnostic_card=diagnostic_card,
            thread_state=updated_thread,
            state_snapshot=state_snapshot,
        )
        final_answer_directive = build_final_answer_directive_v1(
            user_message=query,
            dialogue_policy=dialogue_policy,
            dialogue_pragmatics=dialogue_pragmatics,
            response_planner=response_planner_state,
            active_line=active_line_state,
            diagnostic_card=diagnostic_card.to_dict(),
            diagnostic_center_shadow=diagnostic_center_shadow,
            retrieval_decision=retrieval_decision,
            knowledge_answer_guard=knowledge_answer_guard,
            thread_state=updated_thread,
            state_snapshot=state_snapshot,
            answer_obligation_resolution=answer_obligation_resolution,
            unified_dialogue_profile=unified_dialogue_profile,
        ).to_dict()
        contextual_retrieval_query_composer = build_contextual_retrieval_query_composer_v1(
            user_message=query,
            recent_turns=list(memory_bundle.recent_turns or []),
            last_assistant_offer=last_assistant_offer,
            dialogue_pragmatics=dialogue_pragmatics,
            dialogue_act_resolution=dialogue_act_resolution,
            answer_obligation_resolution=answer_obligation_resolution,
            final_answer_directive=final_answer_directive,
            active_line=active_line_state,
            response_planner=response_planner_state,
            diagnostic_card=diagnostic_card.to_dict(),
            diagnostic_center_shadow=diagnostic_center_shadow,
            knowledge_answer_guard=knowledge_answer_guard,
            retrieval_decision_previous=retrieval_decision,
            memory_bundle_summary={
                "rag_query": getattr(memory_bundle, "rag_query", "") or "",
                "semantic_hits_count": len(list(memory_bundle.semantic_hits or [])),
                "has_relevant_knowledge": bool(memory_bundle.has_relevant_knowledge),
                "fresh_chat_is_greeting_or_contact": bool(
                    fresh_chat_context_policy.get("is_greeting_or_contact", False)
                ),
            },
            current_concept=active_concept,
            thread_state=(
                dict(updated_thread.active_frame)
                if isinstance(updated_thread.active_frame, dict)
                else {}
            ),
        )
        contextual_retrieval_query_composer["pre_retrieval"] = dict(pre_retrieval_composer)
        contextual_retrieval_query_composer["executed_rag_query"] = getattr(memory_bundle, "rag_query", "") or ""
        contextual_retrieval_query_composer["hybrid_retrieval_plan"] = (
            dict(hybrid_retrieval_plan.get("plan", {}))
            if isinstance(hybrid_retrieval_plan.get("plan"), dict)
            else {}
        )
        retrieval_decision = merge_composer_into_retrieval_decision_v1(
            retrieval_decision=retrieval_decision,
            composer_payload=contextual_retrieval_query_composer,
        )
        retrieval_decision["planned_composed_query"] = str(
            dict(hybrid_retrieval_plan.get("plan", {})).get("composed_query", "")
            if isinstance(hybrid_retrieval_plan.get("plan"), dict)
            else ""
        )
        retrieval_decision["executed_rag_query"] = str(
            hybrid_retrieval_trace.get("executed_rag_query", getattr(memory_bundle, "rag_query", "") or "")
        )
        retrieval_decision["legacy_rag_query"] = str(
            hybrid_retrieval_trace.get("legacy_rag_query", "")
        )
        retrieval_decision["query_before_rag_proof"] = bool(
            hybrid_retrieval_trace.get("query_before_rag_proof", False)
        )
        retrieval_decision["retrieval_gap_reason"] = str(
            hybrid_retrieval_trace.get("retrieval_gap_reason", "")
            or ""
        )
        retrieval_decision["needed_chunk_types"] = list(
            dict(hybrid_retrieval_plan.get("plan", {})).get("needed_chunk_types", [])
            if isinstance(hybrid_retrieval_plan.get("plan"), dict)
            else []
        )
        retrieval_decision["mechanism_hints"] = list(
            dict(hybrid_retrieval_plan.get("plan", {})).get("mechanism_hints", [])
            if isinstance(hybrid_retrieval_plan.get("plan"), dict)
            else []
        )
        dialogue_policy["retrieval_decision"] = dict(retrieval_decision)

        writer_contract = WriterContract(
            user_message=query,
            thread_state=updated_thread,
            memory_bundle=memory_bundle,
            context_package=context_package,
            diagnostic_card=diagnostic_card,
            knowledge_answer_guard=knowledge_answer_guard,
            philosophy_kernel=philosophy_kernel_payload,
            writer_freedom_contract=dict(
                philosophy_kernel_payload.get("writer_freedom_contract", {})
            ),
            active_line=active_line_state,
            response_planner=response_planner_state,
            dialogue_policy=dialogue_policy,
            dialogue_pragmatics=dialogue_pragmatics,
            retrieval_decision=retrieval_decision,
            final_answer_directive=final_answer_directive,
        )
        planner_bridge_writer_contract_pilot = (
            build_planner_bridge_writer_contract_pilot_runtime_shadow_v1(
                writer_contract=writer_contract,
                planner_bridge_compliance_shadow=planner_bridge_shadow.get(
                    "planner_bridge_compliance_shadow", {}
                ),
                diagnostic_card=diagnostic_card,
                thread_state=updated_thread,
                state_snapshot=state_snapshot,
            )
        )
        writer_prompt_replay_shadow = build_writer_prompt_replay_runtime_shadow_v1(
            writer_contract=writer_contract,
            writer_contract_pilot=planner_bridge_writer_contract_pilot,
            diagnostic_card=diagnostic_card,
            thread_state=updated_thread,
            state_snapshot=state_snapshot,
        )
        prompt_constraint_pilot_runtime_decision = (
            build_prompt_constraint_pilot_runtime_decision_v1(
                user_id=user_id,
                writer_prompt_replay_result=writer_prompt_replay_shadow,
                writer_contract_pilot=planner_bridge_writer_contract_pilot,
                state_snapshot=state_snapshot,
                thread_state=updated_thread,
            ).to_dict()
        )
        t0 = time.perf_counter()
        if (
            str(prompt_constraint_pilot_runtime_decision.get("activation_mode", "disabled"))
            == "test_apply"
            and bool(prompt_constraint_pilot_runtime_decision.get("apply_to_writer_prompt", False))
        ):
            draft_answer = await writer_agent.write(
                writer_contract,
                prompt_constraint_decision=prompt_constraint_pilot_runtime_decision,
            )
        else:
            draft_answer = await writer_agent.write(writer_contract)
        t_writer = int((time.perf_counter() - t0) * 1000)
        writer_debug = writer_agent.last_debug if isinstance(writer_agent.last_debug, dict) else {}
        self._record_agent_metric(
            agent_id="writer",
            latency_ms=t_writer,
            user_id=user_id,
            input_preview=query,
            output_preview=draft_answer,
            error=str(writer_debug.get("error")) if writer_debug.get("error") else None,
        )

        t0 = time.perf_counter()
        validation_result = validator_agent.validate(draft_answer, writer_contract)
        t_validator = int((time.perf_counter() - t0) * 1000)
        self._record_agent_metric(
            agent_id="validator",
            latency_ms=t_validator,
            user_id=user_id,
            input_preview=query,
            output_preview=f"blocked={validation_result.is_blocked}; reason={validation_result.block_reason}",
            error=validation_result.block_reason if validation_result.is_blocked else None,
        )
        if validation_result.is_blocked:
            final_answer = validation_result.safe_replacement or draft_answer
        else:
            final_answer = draft_answer

        final_answer_acceptance_gate = build_final_answer_acceptance_gate_v1(
            user_message=query,
            final_answer=final_answer,
            dialogue_act_resolution=dialogue_act_resolution,
            answer_obligation_resolution=answer_obligation_resolution,
            unanswered_question_state_before=unanswered_question_state,
            last_assistant_offer_before=last_assistant_offer,
            dialogue_style_state=dialogue_style_state,
            final_answer_directive=final_answer_directive,
            writer_debug=writer_debug,
            validator_result=validation_result,
            previous_assistant_message=previous_assistant_message,
        )
        acceptance_retry_attempted = False
        first_acceptance_gate = dict(final_answer_acceptance_gate)
        if (
            bool(final_answer_acceptance_gate.get("retry_recommended", False))
            and not bool(getattr(updated_thread, "safety_active", False))
        ):
            acceptance_retry_attempted = True
            retry_directive = dict(final_answer_directive)
            retry_directive["acceptance_gate_feedback"] = {
                "version": str(final_answer_acceptance_gate.get("version", "")),
                "failed_checks": list(final_answer_acceptance_gate.get("failed_checks", []) or []),
                "instruction": (
                    "Rewrite the answer as a real user-facing reply. Address the user's current concrete "
                    "question directly, reuse relevant user anchors, avoid stale generic mechanism phrases, "
                    "and preserve requested markdown/list formatting when requested."
                ),
            }
            writer_contract.final_answer_directive = retry_directive
            t0_retry = time.perf_counter()
            if (
                str(prompt_constraint_pilot_runtime_decision.get("activation_mode", "disabled"))
                == "test_apply"
                and bool(prompt_constraint_pilot_runtime_decision.get("apply_to_writer_prompt", False))
            ):
                retry_draft_answer = await writer_agent.write(
                    writer_contract,
                    prompt_constraint_decision=prompt_constraint_pilot_runtime_decision,
                )
            else:
                retry_draft_answer = await writer_agent.write(writer_contract)
            t_writer += int((time.perf_counter() - t0_retry) * 1000)
            writer_debug = writer_agent.last_debug if isinstance(writer_agent.last_debug, dict) else {}
            validation_result = validator_agent.validate(retry_draft_answer, writer_contract)
            if validation_result.is_blocked:
                final_answer = validation_result.safe_replacement or retry_draft_answer
            else:
                final_answer = retry_draft_answer
            final_answer_acceptance_gate = build_final_answer_acceptance_gate_v1(
                user_message=query,
                final_answer=final_answer,
                dialogue_act_resolution=dialogue_act_resolution,
                answer_obligation_resolution=answer_obligation_resolution,
                unanswered_question_state_before=unanswered_question_state,
                last_assistant_offer_before=last_assistant_offer,
                dialogue_style_state=dialogue_style_state,
                final_answer_directive=retry_directive,
                writer_debug=writer_debug,
                validator_result=validation_result,
                previous_assistant_message=previous_assistant_message,
            )
            final_answer_acceptance_gate["retry"] = {
                "attempted": True,
                "first_status": str(first_acceptance_gate.get("status", "")),
                "first_failed_checks": list(first_acceptance_gate.get("failed_checks", []) or []),
            }
        else:
            final_answer_acceptance_gate["retry"] = {
                "attempted": False,
                "first_status": str(first_acceptance_gate.get("status", "")),
                "first_failed_checks": list(first_acceptance_gate.get("failed_checks", []) or []),
            }

        if bool(final_answer_acceptance_gate.get("can_mark_question_answered", False)):
            updated_unanswered_question_state = update_unanswered_question_state_after_answer_v1(
                current_state=unanswered_question_state,
                answer_obligation_resolution=answer_obligation_resolution,
            )
        else:
            updated_unanswered_question_state = dict(unanswered_question_state)
            should_hold_pending = bool(
                set(final_answer_acceptance_gate.get("failed_checks", []) or [])
                & {
                    "stale_stub_detected",
                    "answer_too_generic_for_concrete_situation",
                    "answer_does_not_address_direct_question",
                    "repair_failed_to_answer_recovered_question",
                }
            )
            if should_hold_pending and not str(
                updated_unanswered_question_state.get("last_direct_user_question", "") or ""
            ).strip():
                updated_unanswered_question_state["last_direct_user_question"] = query
            updated_unanswered_question_state["answer_required"] = bool(
                updated_unanswered_question_state.get("answer_required", False)
                or should_hold_pending
            )
            if updated_unanswered_question_state.get("answer_required"):
                updated_unanswered_question_state["answer_status"] = "pending_quarantined_answer"
            updated_unanswered_question_state["quarantine_reason"] = str(
                final_answer_acceptance_gate.get("quarantine_reason", "")
            )
        updated_dialogue_style_state = finalize_dialogue_style_state_v1(
            current_state=dialogue_style_state,
            turn_index=current_turn_index,
        )
        if bool(final_answer_acceptance_gate.get("can_save_last_assistant_offer", False)):
            updated_last_assistant_offer = update_last_assistant_offer_after_answer_v1(
                final_answer=final_answer,
                turn_index=current_turn_index,
            )
        else:
            updated_last_assistant_offer = dict(last_assistant_offer)
            updated_last_assistant_offer["quarantine_skipped_update"] = True
            updated_last_assistant_offer["quarantine_reason"] = str(
                final_answer_acceptance_gate.get("quarantine_reason", "")
            )
        updated_thread.active_frame = dict(updated_thread.active_frame or {})
        updated_thread.active_frame["dialogue_state"] = {
            "unified_dialogue_profile": dict(unified_dialogue_profile),
            "dialogue_act_resolution": dict(dialogue_act_resolution),
            "last_assistant_offer": dict(updated_last_assistant_offer),
            "unanswered_question_state": dict(updated_unanswered_question_state),
            "dialogue_style_state": dict(updated_dialogue_style_state),
            "answer_obligation_resolution": dict(answer_obligation_resolution),
        }
        updated_thread.active_frame["last_assistant_offer"] = dict(updated_last_assistant_offer)
        updated_thread.active_frame["last_direct_user_question"] = str(
            updated_unanswered_question_state.get("last_direct_user_question", "") or ""
        )
        updated_thread.active_frame["dialogue_style_state"] = dict(updated_dialogue_style_state)
        thread_storage.save_active(updated_thread)

        live_turn_evidence = build_live_turn_evidence_v1(
            query=query,
            user_id=user_id,
            session_id=user_id,
            turn_index=None,
            orchestrator_result={"answer": final_answer},
            writer_contract=writer_contract,
            writer_debug=writer_debug,
            memory_bundle=memory_bundle,
            state_snapshot=state_snapshot,
            thread_state=updated_thread,
            thread_debug=thread_debug,
            diagnostic_card=diagnostic_card,
            active_line_state=active_line_state,
            response_planner_state=response_planner_state,
            dialogue_policy=dialogue_policy,
            dialogue_pragmatics=dialogue_pragmatics,
            contextual_retrieval_decision=retrieval_decision,
            unified_dialogue_profile=unified_dialogue_profile,
            dialogue_act_resolution=dialogue_act_resolution,
            last_assistant_offer=updated_last_assistant_offer,
            unanswered_question_state=updated_unanswered_question_state,
            dialogue_style_state=updated_dialogue_style_state,
            answer_obligation_resolution=answer_obligation_resolution,
            validation_result=validation_result,
            final_answer_acceptance_gate=final_answer_acceptance_gate,
        )

        quality_trace_error = None
        try:
            quality_trace = build_quality_trace(
                final_answer=final_answer,
                writer_contract=writer_contract,
                validation_result=validation_result,
            )
        except Exception as exc:  # noqa: BLE001
            quality_trace = {
                "version": QUALITY_TRACE_VERSION,
                "error": "quality_trace_failed",
            }
            quality_trace_error = f"quality_trace_failed:{exc.__class__.__name__}"
            logger.warning("[MULTIAGENT] quality_trace build failed: %s", exc.__class__.__name__)

        planner_drift_guard_error = None
        planner_drift_guard = {}
        planner_drift_summary = {}
        try:
            planner_drift_guard = build_planner_drift_check(
                response_planner=response_planner_state,
                final_answer=final_answer,
                enabled=True,
            ).to_dict()
            record_planner_drift_check(user_id=user_id, check=planner_drift_guard)
            planner_drift_summary = get_planner_drift_summary()
            rolling_total = int(planner_drift_summary.get("total", 0) or 0)
            rolling_violations = int(
                planner_drift_summary.get("warning_count", 0) or 0
            ) + int(planner_drift_summary.get("critical_count", 0) or 0)
            planner_drift_guard["rolling_window"] = {
                "size": int(planner_drift_summary.get("window_size", 100) or 100),
                "total": rolling_total,
                "violations": rolling_violations,
                "violation_rate": float(planner_drift_summary.get("violation_rate", 0.0) or 0.0),
                "by_flag": dict(planner_drift_summary.get("by_flag", {})),
            }
        except Exception as exc:  # noqa: BLE001
            planner_drift_guard_error = (
                f"planner_drift_guard_failed:{exc.__class__.__name__}"
            )
            logger.warning("[MULTIAGENT] planner drift guard build failed: %s", exc.__class__.__name__)
            planner_drift_guard = {
                "version": PLANNER_DRIFT_GUARD_VERSION,
                "enabled": False,
                "status": "warning",
                "severity": "medium",
                "flags": ["drift_guard_exception"],
                "shape_obedience": False,
                "policy_obedience": False,
                "question_policy_obedience": False,
                "practice_policy_obedience": False,
                "revoicing_policy_obedience": False,
                "answer_length_obedience": False,
                "safety_grounding_obedience": False,
                "short_support_obedience": False,
                "close_obedience": False,
                "final_answer_chars": len(str(final_answer or "")),
                "final_answer_question_count": str(final_answer or "").count("?"),
                "planner_next_move": str(response_planner_state.get("next_move", "") or ""),
                "planner_answer_shape": str(response_planner_state.get("answer_shape", "") or ""),
                "planner_question_policy": str(response_planner_state.get("question_policy", "none") or "none"),
                "planner_practice_policy": str(response_planner_state.get("practice_policy", "forbidden") or "forbidden"),
                "rationale": "drift guard exception fallback",
                "rolling_window": {
                    "size": 100,
                    "total": 0,
                    "violations": 0,
                    "violation_rate": 0.0,
                    "by_flag": {},
                },
            }
            planner_drift_summary = get_planner_drift_summary()

        memory_write_scheduled = False
        if bool(final_answer_acceptance_gate.get("can_save_as_healthy_context", False)):
            asyncio.create_task(
                memory_retrieval_agent.update(
                    user_id=user_id,
                    user_message=query,
                    assistant_response=final_answer,
                    thread_state=updated_thread,
                )
            )
            memory_write_scheduled = True
        total_latency_ms = int(t_state + t_thread + t_memory + t_writer + t_validator)
        semantic_hits_candidates = list(memory_bundle.semantic_hits or [])
        semantic_hits_detail = build_safe_knowledge_debug_detail_v1(
            semantic_hits=semantic_hits_candidates,
            knowledge_policy_trace=dict(memory_bundle.knowledge_policy_trace or {}),
        )
        writer_chunks_candidate_detail: list[dict[str, object]] = []
        for item in list(semantic_hits_detail or []):
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id", "") or "")
            preview = str(item.get("content_preview", "") or "")
            writer_chunks_candidate_detail.append(
                {
                    "chunk_id_hash": (
                        "sha256:"
                        + hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()
                        if chunk_id
                        else ""
                    ),
                    "source": str(item.get("source", "unknown") or "unknown"),
                    "score": float(item.get("score", 0.0) or 0.0),
                    "content_preview": preview,
                    "preview_len": len(preview),
                    "governance": {
                        "policy_action": str(item.get("policy_action", "") or ""),
                        "allowed_for_writer": bool(
                            str(item.get("policy_action", "") or "")
                            == "include_writer_context"
                        ),
                    },
                }
            )
        included_raw = [
            item
            for item in list(retrieval_decision.get("rag_included_for_writer", []) or [])
            if isinstance(item, dict)
        ]
        writer_chunks_included_detail = [
            {
                "chunk_id_hash": (
                    "sha256:"
                    + hashlib.sha256(str(item.get("chunk_id", "")).encode("utf-8")).hexdigest()
                    if str(item.get("chunk_id", ""))
                    else ""
                ),
                "source": str(item.get("source", "unknown") or "unknown"),
                "score": float(item.get("score", 0.0) or 0.0),
                "content_preview": str(item.get("content", "") or "")[:280],
            }
            for item in included_raw
        ]

        return {
            "status": "ok",
            "answer": final_answer,
            "thread_id": updated_thread.thread_id,
            "phase": updated_thread.phase,
            "response_mode": updated_thread.response_mode,
            "relation_to_thread": updated_thread.relation_to_thread,
            "continuity_score": updated_thread.continuity_score,
            "debug": {
                "multiagent_enabled": True,
                "pipeline_version": "multiagent_v1",
                "total_latency_ms": total_latency_ms,
                "thread_manager_model": "heuristic",
                "nervous_state": state_snapshot.nervous_state,
                "intent": state_snapshot.intent,
                "safety_flag": state_snapshot.safety_flag,
                "confidence": state_snapshot.confidence,
                "has_relevant_knowledge": memory_bundle.has_relevant_knowledge,
                "context_turns": memory_bundle.context_turns,
                "semantic_hits_count": len(semantic_hits_candidates),
                "semantic_hits_detail": semantic_hits_detail,
                "writer_chunks_detail": writer_chunks_included_detail,
                "writer_chunks_candidate_detail": writer_chunks_candidate_detail,
                "semantic_hits_raw_redacted": True,
                "rag_retrieval_trace": dict(memory_bundle.rag_retrieval_trace or {}),
                "hybrid_retrieval_planner_version": HYBRID_RETRIEVAL_PLANNER_VERSION,
                "hybrid_retrieval_planner_mode": str(hybrid_retrieval_plan.get("mode", "shadow") or "shadow"),
                "hybrid_retrieval_plan": (
                    dict(hybrid_retrieval_plan.get("plan", {}))
                    if isinstance(hybrid_retrieval_plan.get("plan"), dict)
                    else {}
                ),
                "hybrid_retrieval_plan_valid": bool(hybrid_retrieval_plan.get("valid", False)),
                "hybrid_retrieval_plan_error": hybrid_retrieval_plan.get("error"),
                "hybrid_retrieval_universal_gate": str(hybrid_retrieval_plan.get("universal_gate", "") or ""),
                "hybrid_retrieval_llm_called": bool(hybrid_retrieval_plan.get("llm_called", False)),
                "hybrid_retrieval_llm_reason": str(hybrid_retrieval_plan.get("llm_reason", "") or ""),
                "hybrid_retrieval_fallback_used": bool(hybrid_retrieval_plan.get("fallback_used", False)),
                "planned_composed_query": str(
                    hybrid_retrieval_trace.get("planned_composed_query", "")
                    or ""
                ),
                "executed_rag_query": str(
                    hybrid_retrieval_trace.get("executed_rag_query", "")
                    or ""
                ),
                "legacy_rag_query": str(
                    hybrid_retrieval_trace.get("legacy_rag_query", "")
                    or ""
                ),
                "query_before_rag_proof": bool(
                    hybrid_retrieval_trace.get("query_before_rag_proof", False)
                ),
                "needed_chunk_types": list(
                    dict(hybrid_retrieval_plan.get("plan", {})).get("needed_chunk_types", [])
                    if isinstance(hybrid_retrieval_plan.get("plan"), dict)
                    else []
                ),
                "mechanism_hints": list(
                    dict(hybrid_retrieval_plan.get("plan", {})).get("mechanism_hints", [])
                    if isinstance(hybrid_retrieval_plan.get("plan"), dict)
                    else []
                ),
                "retrieval_gap_reason": str(
                    hybrid_retrieval_trace.get("retrieval_gap_reason", "")
                    or ""
                ),
                "writer_can_ignore_rag": bool(
                    dict(hybrid_retrieval_plan.get("plan", {})).get("writer_can_ignore_rag", True)
                    if isinstance(hybrid_retrieval_plan.get("plan"), dict)
                    else True
                ),
                "knowledge_policy_trace": dict(memory_bundle.knowledge_policy_trace or {}),
                "overlay_shadow": dict(overlay_shadow),
                "dialogue_pragmatics": dict(dialogue_pragmatics),
                "fresh_chat_context_policy_version": FRESH_CHAT_CONTEXT_POLICY_VERSION,
                "fresh_chat_context_policy": dict(fresh_chat_context_policy),
                "retrieval_decision": dict(retrieval_decision),
                "contextual_retrieval_query_composer": dict(contextual_retrieval_query_composer),
                "final_answer_directive": dict(final_answer_directive),
                "final_answer_acceptance_gate": dict(final_answer_acceptance_gate),
                "final_answer_acceptance_retry_attempted": bool(acceptance_retry_attempted),
                "live_turn_evidence": dict(live_turn_evidence),
                "knowledge_answer": dict(knowledge_answer_guard.get("knowledge_answer", {})),
                "practice_gate": dict(knowledge_answer_guard.get("practice_gate", {})),
                "dialogue_policy": dict(dialogue_policy),
                "knowledge_answer_trace": {
                    "schema_version": str(knowledge_answer_guard.get("schema_version", "")),
                    "concept_aliases_version": str(knowledge_answer_guard.get("concept_aliases_version", "")),
                    "knowledge_answer_needed": bool(
                        dict(knowledge_answer_guard.get("knowledge_answer", {})).get("needed", False)
                    ),
                    "kb_grounding_available": bool(
                        dict(knowledge_answer_guard.get("knowledge_answer", {})).get("kb_grounding_available", False)
                    ),
                },
                "philosophy_kernel": {
                    "kernel_version": str(philosophy_kernel_payload.get("kernel_version", "")),
                    "enabled": bool(philosophy_kernel_payload.get("kernel_enabled", True)),
                    "selected_lenses": list(
                        dict(philosophy_kernel_payload.get("selection", {})).get("selected_lenses", [])
                        if isinstance(philosophy_kernel_payload.get("selection"), dict)
                        else []
                    ),
                    "selection_reason": list(
                        dict(philosophy_kernel_payload.get("selection", {})).get("selection_reason", [])
                        if isinstance(philosophy_kernel_payload.get("selection"), dict)
                        else []
                    ),
                    "prompt_block_included": bool(
                        dict(philosophy_kernel_payload.get("selection", {})).get("prompt_block_included", False)
                        if isinstance(philosophy_kernel_payload.get("selection"), dict)
                        else False
                    ),
                    "depth_mode": str(
                        dict(philosophy_kernel_payload.get("selection", {})).get("depth_mode", "guided")
                        if isinstance(philosophy_kernel_payload.get("selection"), dict)
                        else "guided"
                    ),
                    "quote_policy": str(philosophy_kernel_payload.get("quote_policy", "")),
                    "practice_policy": str(philosophy_kernel_payload.get("practice_policy", "")),
                    "prompt_compactness": (
                        dict(philosophy_kernel_payload.get("prompt_compactness", {}))
                        if isinstance(philosophy_kernel_payload.get("prompt_compactness"), dict)
                        else {}
                    ),
                },
                "writer_freedom_contract": {
                    "enabled": bool(
                        dict(philosophy_kernel_payload.get("writer_freedom_contract", {})).get("enabled", False)
                    ),
                    "freedom_level": str(
                        dict(philosophy_kernel_payload.get("writer_freedom_contract", {})).get(
                            "freedom_level", ""
                        )
                    ),
                    "mode_is_hint_not_cage": bool(
                        dict(philosophy_kernel_payload.get("writer_freedom_contract", {})).get(
                            "mode_is_hint_not_cage", False
                        )
                    ),
                    "question_limit": int(
                        dict(philosophy_kernel_payload.get("writer_freedom_contract", {})).get(
                            "question_limit", 1
                        )
                        or 1
                    ),
                    "practice_requires_gate": bool(
                        dict(philosophy_kernel_payload.get("writer_freedom_contract", {})).get(
                            "practice_requires_gate", True
                        )
                    ),
                    "prompt_block_chars": len(
                        str(philosophy_kernel_payload.get("writer_freedom_prompt_block", "") or "")
                    ),
                },
                "active_line": dict(active_line_state),
                "response_planner_version": RESPONSE_PLANNER_VERSION,
                "response_planner": dict(response_planner_state),
                "response_planner_error": response_planner_error,
                "planner_drift_guard_version": PLANNER_DRIFT_GUARD_VERSION,
                "planner_drift_guard": dict(planner_drift_guard),
                "planner_drift_guard_error": planner_drift_guard_error,
                "planner_drift_summary": dict(planner_drift_summary),
                "rag_query": getattr(memory_bundle, "rag_query", "") or "",
                "conversation_context": memory_bundle.conversation_context,
                "user_profile": {
                    "patterns": list(getattr(memory_bundle.user_profile, "patterns", []) or []),
                    "values": list(getattr(memory_bundle.user_profile, "values", []) or []),
                    "progress_notes": list(getattr(memory_bundle.user_profile, "progress_notes", []) or []),
                },
                "thread_id": updated_thread.thread_id,
                "phase": updated_thread.phase,
                "relation_to_thread": updated_thread.relation_to_thread,
                "continuity_score": updated_thread.continuity_score,
                "response_mode": updated_thread.response_mode,
                "dialogue_profile": dialogue_profile,
                "unified_dialogue_profile": dict(unified_dialogue_profile),
                "dialogue_act_resolution": dict(dialogue_act_resolution),
                "last_assistant_offer": dict(updated_last_assistant_offer),
                "unanswered_question_state": dict(updated_unanswered_question_state),
                "dialogue_style_state": dict(updated_dialogue_style_state),
                "answer_obligation_resolution": dict(answer_obligation_resolution),
                "request_type": behavior_request_type,
                "practice_suppressed": practice_suppressed,
                "practice_suppression_reasons": suppression_reasons,
                "pattern_core": updated_thread.pattern_core,
                "active_frame": dict(updated_thread.active_frame),
                "thread_diagnostics_version": THREAD_DIAGNOSTICS_VERSION,
                "thread_diagnostics": thread_debug,
                "context_assembly_trace_version": CONTEXT_ASSEMBLY_TRACE_VERSION,
                "context_assembly_trace": context_package.trace.to_dict(),
                "context_package_summary": {
                    "has_current_user_message": bool(context_package.current_user_message.strip()),
                    "pattern_core_present": bool((context_package.pattern_core or "").strip()),
                    "active_frame_present": bool(context_package.active_frame),
                    "recent_full_count": len(context_package.recent_turns_full),
                    "recent_summarized_count": len(context_package.recent_turns_summarized),
                    "personal_history_count": len(context_package.personal_history_context),
                    "semantic_hits_count": len(context_package.semantic_memory_hits),
                    "knowledge_hits_count": len(context_package.knowledge_rag_hits),
                },
                "diagnostic_card_version": DIAGNOSTIC_CARD_VERSION,
                "diagnostic_card": diagnostic_card.to_dict(),
                "diagnostic_card_trace": diagnostic_card.trace.to_dict(),
                "diagnostic_card_summary": {
                    "present": True,
                    "situation_label": diagnostic_card.situation_label,
                    "suggested_writer_move": diagnostic_card.suggested_writer_move,
                    "current_need": diagnostic_card.current_need,
                    "confidence": float(diagnostic_card.confidence),
                    "risk_flags": list(diagnostic_card.risk_flags),
                    "request_type": behavior_request_type,
                    "practice_suppressed": practice_suppressed,
                    "practice_suppression_reasons": suppression_reasons,
                },
                "creator_live_behavior_guard": {
                    "version": "anti_regulate_loop_v1",
                    "request_type": behavior_request_type,
                    "practice_suppressed": practice_suppressed,
                    "practice_suppression_reasons": suppression_reasons,
                },
                "diagnostic_center_shadow": diagnostic_center_shadow,
                "planner_bridge_candidate": planner_bridge_shadow.get("planner_bridge_candidate", {}),
                "planner_bridge_compliance_shadow": planner_bridge_shadow.get(
                    "planner_bridge_compliance_shadow", {}
                ),
                "planner_bridge_writer_contract_pilot": planner_bridge_writer_contract_pilot,
                "writer_prompt_replay_shadow": writer_prompt_replay_shadow,
                "prompt_constraint_pilot_runtime": prompt_constraint_pilot_runtime_decision,
                "writer_system_prompt": str(writer_debug.get("system_prompt", "") or ""),
                "writer_user_prompt": str(writer_debug.get("user_prompt", "") or ""),
                "writer_llm_response_raw": str(writer_debug.get("llm_response", "") or ""),
                "writer_api_mode": writer_debug.get("api_mode"),
                "writer_error": writer_debug.get("error"),
                "writer_fallback_used": bool(writer_debug.get("fallback_used", False)),
                "writer_kb_payload_enabled": writer_debug.get("writer_kb_payload_enabled"),
                "writer_kb_payload_failed": writer_debug.get("writer_kb_payload_failed"),
                "writer_kb_payload_trace": (
                    dict(writer_debug.get("writer_kb_payload_trace", {}))
                    if isinstance(writer_debug.get("writer_kb_payload_trace"), dict)
                    else {}
                ),
                "future_graduation_notes": (
                    dict(writer_debug.get("writer_kb_payload_future_graduation_notes", {}))
                    if isinstance(writer_debug.get("writer_kb_payload_future_graduation_notes"), dict)
                    else {}
                ),
                "writer_human_like_answer_policy_enabled": writer_debug.get(
                    "human_like_answer_policy_enabled"
                ),
                "writer_explicit_answer_need": writer_debug.get("explicit_answer_need"),
                "writer_repair_user_dissatisfaction": writer_debug.get(
                    "repair_user_dissatisfaction"
                ),
                "writer_sarcasm_or_negative_feedback": writer_debug.get(
                    "sarcasm_or_negative_feedback"
                ),
                "writer_overruled_constraints": writer_debug.get("overruled_constraints"),
                "writer_final_answer_shape": writer_debug.get("final_answer_shape"),
                "writer_question_forced": writer_debug.get("question_forced"),
                "writer_practice_forced": writer_debug.get("practice_forced"),
                "writer_microstep_forced": writer_debug.get("microstep_forced"),
                "tokens_prompt": writer_debug.get("tokens_prompt"),
                "tokens_completion": writer_debug.get("tokens_completion"),
                "tokens_total": writer_debug.get("tokens_total"),
                "tokens_used": writer_debug.get("tokens_total"),
                "estimated_cost_usd": writer_debug.get("estimated_cost_usd"),
                "model_used": str(writer_debug.get("model") or config.LLM_MODEL),
                "model_temperature": writer_debug.get("temperature"),
                "model_max_tokens": writer_debug.get("max_tokens"),
                "state_analyzer_model": state_debug.get("model"),
                "state_analyzer_api_mode": state_debug.get("api_mode"),
                "state_analyzer_error": state_debug.get("error"),
                "state_analyzer_parse_error": state_debug.get("parse_error"),
                "state_analyzer_fallback_used": bool(
                    state_debug.get("error") or state_debug.get("parse_error")
                ),
                "validator_blocked": validation_result.is_blocked,
                "validator_block_reason": validation_result.block_reason,
                "validator_quality_flags": validation_result.quality_flags,
                "quality_trace_version": QUALITY_TRACE_VERSION,
                "quality_trace": quality_trace,
                "quality_trace_error": quality_trace_error,
                "memory_written": {
                    "scheduled": bool(memory_write_scheduled),
                    "healthy_context_allowed": bool(
                        final_answer_acceptance_gate.get("can_save_as_healthy_context", False)
                    ),
                    "user_input": query[:200],
                    "bot_response": final_answer[:200] if memory_write_scheduled else "",
                    "thread_id": updated_thread.thread_id,
                    "phase": updated_thread.phase,
                    "quarantine_reason": (
                        ""
                        if memory_write_scheduled
                        else str(final_answer_acceptance_gate.get("quarantine_reason", ""))
                    ),
                },
                "timings": {
                    "state_analyzer_ms": t_state,
                    "thread_manager_ms": t_thread,
                    "memory_retrieval_ms": t_memory,
                    "writer_ms": t_writer,
                    "validator_ms": t_validator,
                },
            },
        }

    def run_sync(self, *, query: str, user_id: str) -> dict:
        return asyncio.run(self.run(query=query, user_id=user_id))


orchestrator = MultiAgentOrchestrator()
