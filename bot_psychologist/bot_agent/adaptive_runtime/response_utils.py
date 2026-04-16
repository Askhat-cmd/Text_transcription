"""Shared response helper builders extracted from answer_adaptive."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state_classifier import StateAnalysis, UserState

from .response_success_helpers import (
    _build_fast_path_success_response,
    _build_full_path_success_response,
    _finalize_full_path_success_stage,
    _prepare_full_path_post_llm_artifacts,
    _run_full_path_success_stage,
)

def _get_feedback_prompt_for_state(state: UserState) -> str:
    """Return feedback follow-up prompt based on detected user state."""
    prompts = {
        UserState.UNAWARE: "РЎС‚Р°Р»Рѕ Р»Рё РїРѕРЅСЏС‚РЅРµРµ, Рѕ С‡С‘Рј СЂРµС‡СЊ? Р§С‚Рѕ РѕСЃС‚Р°Р»РѕСЃСЊ РЅРµРїРѕРЅСЏС‚РЅС‹Рј?",
        UserState.CURIOUS: "РҐРѕС‚РёС‚Рµ СѓР·РЅР°С‚СЊ С‡С‚Рѕ-С‚Рѕ РµС‰С‘ РїРѕ СЌС‚РѕР№ С‚РµРјРµ?",
        UserState.OVERWHELMED: "РќРµ СЃР»РёС€РєРѕРј Р»Рё РјРЅРѕРіРѕ РёРЅС„РѕСЂРјР°С†РёРё? РќСѓР¶РЅРѕ Р»Рё СѓРїСЂРѕСЃС‚РёС‚СЊ?",
        UserState.RESISTANT: "Р•СЃС‚СЊ Р»Рё С‡С‚Рѕ-С‚Рѕ, СЃ С‡РµРј РІС‹ РЅРµ СЃРѕРіР»Р°СЃРЅС‹? Р”Р°РІР°Р№С‚Рµ РѕР±СЃСѓРґРёРј.",
        UserState.CONFUSED: "РџСЂРѕСЏСЃРЅРёР»РѕСЃСЊ Р»Рё РѕР±СЉСЏСЃРЅРµРЅРёРµ? Р•СЃР»Рё РЅРµС‚, РєР°РєР°СЏ С‡Р°СЃС‚СЊ РІСЃС‘ РµС‰С‘ РЅРµРїРѕРЅСЏС‚РЅР°?",
        UserState.COMMITTED: "Р“РѕС‚РѕРІС‹ Р»Рё РІС‹ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєСѓ? РљР°РєР°СЏ РїРѕРґРґРµСЂР¶РєР° РЅСѓР¶РЅР°?",
        UserState.PRACTICING: "РљР°Рє РёРґС‘С‚ РїСЂР°РєС‚РёРєР°? Р•СЃС‚СЊ Р»Рё СЃР»РѕР¶РЅРѕСЃС‚Рё?",
        UserState.STAGNANT: "Р§С‚Рѕ, РїРѕ-РІР°С€РµРјСѓ, РјРµС€Р°РµС‚ РїСЂРѕРґРІРёР¶РµРЅРёСЋ? РџРѕРїСЂРѕР±СѓРµРј РЅР°Р№С‚Рё РЅРѕРІС‹Р№ РїРѕРґС…РѕРґ?",
        UserState.BREAKTHROUGH: "РџРѕР·РґСЂР°РІР»СЏСЋ СЃ РёРЅСЃР°Р№С‚РѕРј! РљР°Рє РїР»Р°РЅРёСЂСѓРµС‚Рµ РїСЂРёРјРµРЅРёС‚СЊ СЌС‚Рѕ РїРѕРЅРёРјР°РЅРёРµ?",
        UserState.INTEGRATED: "РљР°Рє СЌС‚Рѕ Р·РЅР°РЅРёРµ РїСЂРѕСЏРІР»СЏРµС‚СЃСЏ РІ РІР°С€РµР№ Р¶РёР·РЅРё?",
    }
    return prompts.get(state, "Р‘С‹Р» Р»Рё СЌС‚РѕС‚ РѕС‚РІРµС‚ РїРѕР»РµР·РµРЅ? РћС†РµРЅРёС‚Рµ РѕС‚ 1 РґРѕ 5.")


def _build_partial_response(
    message: str,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
) -> Dict:
    """Build partial response payload when no blocks are retrieved."""
    return {
        "status": "partial",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value,
            "confidence": state_analysis.confidence,
            "emotional_tone": state_analysis.emotional_tone,
            "recommendations": state_analysis.recommendations,
        }
        if state_analysis
        else None,
        "path_recommendation": None,
        "conversation_context": memory.get_adaptive_context_text(query) if memory else "",
        "feedback_prompt": "РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРµСЂРµС„РѕСЂРјСѓР»РёСЂРѕРІР°С‚СЊ РІРѕРїСЂРѕСЃ.",
        "sources": [],
        "concepts": [],
        "metadata": {"conversation_turns": len(memory.turns) if memory else 0},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
    }


def _build_error_response(
    message: str,
    state_analysis: StateAnalysis,
    start_time: datetime,
) -> Dict:
    """Build error response payload for safe failure mode."""
    return {
        "status": "error",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value if state_analysis else "unknown",
            "confidence": state_analysis.confidence if state_analysis else 0,
        }
        if state_analysis
        else None,
        "path_recommendation": None,
        "conversation_context": "",
        "feedback_prompt": "",
        "sources": [],
        "concepts": [],
        "metadata": {},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
    }


def _serialize_state_analysis(state_analysis: Optional[StateAnalysis]) -> Optional[Dict[str, Any]]:
    if state_analysis is None:
        return None
    return {
        "primary_state": state_analysis.primary_state.value,
        "confidence": state_analysis.confidence,
        "secondary_states": [s.value for s in state_analysis.secondary_states],
        "emotional_tone": state_analysis.emotional_tone,
        "depth": state_analysis.depth,
        "recommendations": state_analysis.recommendations,
    }


def _build_success_response(
    *,
    answer: str,
    state_analysis: StateAnalysis,
    path_recommendation: Optional[Dict[str, Any]],
    conversation_context: str,
    feedback_prompt: str,
    sources: List[Dict[str, Any]],
    concepts: List[str],
    metadata: Dict[str, Any],
    elapsed_time: float,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "answer": answer,
        "state_analysis": _serialize_state_analysis(state_analysis),
        "path_recommendation": path_recommendation,
        "conversation_context": conversation_context,
        "feedback_prompt": feedback_prompt,
        "sources": sources,
        "concepts": concepts,
        "metadata": metadata,
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": round(elapsed_time, 2),
    }


def _build_fast_success_metadata(
    *,
    user_id: str,
    state_analysis: StateAnalysis,
    routing_result,
    mode_reason: str,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    memory_context_mode: str,
    memory_trace_metrics: Dict[str, Any],
    summary_length: int,
    summary_last_turn: Optional[int],
    summary_pending_turn: Optional[int],
    memory_turns: int,
    hybrid_query_len: int,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    session_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "blocks_used": 0,
        "state": state_analysis.primary_state.value,
        "conversation_turns": memory_turns,
        "recommended_mode": routing_result.mode,
        "route_track": getattr(routing_result, "track", "direct"),
        "route_tone": getattr(routing_result, "tone", "minimal"),
        "decision_rule_id": routing_result.decision.rule_id,
        "confidence_score": routing_result.confidence_score,
        "confidence_level": routing_result.confidence_level,
        "mode_reason": mode_reason,
        "prompt_stack_v2_enabled": prompt_stack_v2_enabled,
        "output_validation_enabled": output_validation_enabled,
        "retrieval_block_cap": 0,
        "fast_path": True,
        "informational_mode": informational_mode,
        "applied_mode_prompt": mode_prompt_key if informational_mode else None,
        "summary_used": memory_trace_metrics["summary_used"],
        "summary_length": summary_length,
        "summary_last_turn": summary_last_turn,
        "context_mode": memory_context_mode,
        "summary_pending_turn": summary_pending_turn,
        "semantic_hits": memory_trace_metrics["semantic_hits"],
        "memory_turns": memory_turns,
        "hybrid_query_len": hybrid_query_len,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "session_tokens_prompt": session_metrics.get("session_tokens_prompt"),
        "session_tokens_completion": session_metrics.get("session_tokens_completion"),
        "session_tokens_total": session_metrics.get("session_tokens_total"),
        "session_cost_usd": session_metrics.get("session_cost_usd"),
        "session_turns": session_metrics.get("session_turns"),
    }


def _build_full_success_metadata(
    *,
    user_id: str,
    state_analysis: StateAnalysis,
    routing_result,
    mode_reason: str,
    route_resolution_count: int,
    blocks_used: int,
    selected_practice: Optional[str],
    practice_alternatives: List[str],
    retrieval_block_cap: int,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    diagnostics_v1_payload: Optional[Dict[str, Any]],
    contradiction_detected: bool,
    cross_session_context_used: bool,
    memory_context_mode: str,
    memory_trace_metrics: Dict[str, Any],
    summary_length: int,
    summary_last_turn: Optional[int],
    summary_pending_turn: Optional[int],
    memory_turns: int,
    hybrid_query_len: int,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    session_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "blocks_used": blocks_used,
        "state": state_analysis.primary_state.value,
        "conversation_turns": memory_turns,
        "recommended_mode": routing_result.mode,
        "route_track": getattr(routing_result, "track", "direct"),
        "route_tone": getattr(routing_result, "tone", "minimal"),
        "resolved_route": getattr(routing_result, "route", None),
        "decision_rule_id": routing_result.decision.rule_id,
        "confidence_score": routing_result.confidence_score,
        "confidence_level": routing_result.confidence_level,
        "mode_reason": mode_reason,
        "route_resolution_count": route_resolution_count,
        "prompt_stack_v2_enabled": prompt_stack_v2_enabled,
        "output_validation_enabled": output_validation_enabled,
        "selected_practice": selected_practice,
        "practice_alternatives": practice_alternatives,
        "retrieval_block_cap": retrieval_block_cap,
        "informational_mode": informational_mode,
        "applied_mode_prompt": mode_prompt_key if informational_mode else None,
        "diagnostics_v1": diagnostics_v1_payload,
        "contradiction_detected": contradiction_detected,
        "cross_session_context_used": cross_session_context_used,
        "summary_used": memory_trace_metrics["summary_used"],
        "summary_length": summary_length,
        "summary_last_turn": summary_last_turn,
        "context_mode": memory_context_mode,
        "summary_pending_turn": summary_pending_turn,
        "semantic_hits": memory_trace_metrics["semantic_hits"],
        "memory_turns": memory_turns,
        "hybrid_query_len": hybrid_query_len,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "session_tokens_prompt": session_metrics.get("session_tokens_prompt"),
        "session_tokens_completion": session_metrics.get("session_tokens_completion"),
        "session_tokens_total": session_metrics.get("session_tokens_total"),
        "session_cost_usd": session_metrics.get("session_cost_usd"),
        "session_turns": session_metrics.get("session_turns"),
    }


def _build_path_recommendation_if_enabled(
    *,
    include_path_recommendation: bool,
    state_analysis: StateAnalysis,
    route_name: str,
    path_builder_blocked_routes,
    user_id: str,
    user_level_enum,
    memory,
    path_builder,
    logger,
) -> Optional[Dict[str, Any]]:
    should_build_path = (
        include_path_recommendation
        and state_analysis.primary_state != UserState.INTEGRATED
        and route_name not in path_builder_blocked_routes
    )
    if not should_build_path:
        return None

    try:
        personal_path = path_builder.build_path(
            user_id=user_id,
            state_analysis=state_analysis,
            user_level=user_level_enum,
            memory=memory,
        )
        if not personal_path:
            return None
        return {
            "current_state": personal_path.current_state.value,
            "target_state": personal_path.target_state.value,
            "key_focus": personal_path.key_focus,
            "steps_count": len(personal_path.path_steps),
            "total_duration_weeks": personal_path.total_duration_weeks,
            "adaptation_notes": personal_path.adaptation_notes,
            "first_step": {
                "title": personal_path.path_steps[0].title if personal_path.path_steps else "",
                "duration_weeks": (
                    personal_path.path_steps[0].duration_weeks if personal_path.path_steps else 0
                ),
                "practices": (
                    personal_path.path_steps[0].practices[:3] if personal_path.path_steps else []
                ),
            }
            if personal_path.path_steps
            else None,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("[PATH_BUILDER] recommendation skipped: %s", exc)
        return None


def _persist_turn_best_effort(
    *,
    memory,
    user_input: str,
    bot_response: str,
    user_state: Optional[str] = None,
    blocks_used: int = 0,
    concepts: Optional[List[str]] = None,
    schedule_summary_task: bool = True,
) -> None:
    try:
        memory.add_turn(
            user_input=user_input,
            bot_response=bot_response,
            user_state=user_state,
            blocks_used=blocks_used,
            concepts=concepts or [],
            schedule_summary_task=schedule_summary_task,
        )
    except Exception:
        pass


def _persist_turn(
    *,
    memory,
    user_input: str,
    bot_response: str,
    user_state: Optional[str] = None,
    blocks_used: int = 0,
    concepts: Optional[List[str]] = None,
    schedule_summary_task: bool = True,
) -> None:
    memory.add_turn(
        user_input=user_input,
        bot_response=bot_response,
        user_state=user_state,
        blocks_used=blocks_used,
        concepts=concepts or [],
        schedule_summary_task=schedule_summary_task,
    )


def _save_session_summary_best_effort(
    *,
    memory,
    user_id: str,
    query: str,
    answer: str,
    state_end: str,
    concepts: Optional[List[str]] = None,
    logger=None,
) -> None:
    try:
        primary_interests = memory.get_primary_interests()
        key_themes: List[str] = []
        for item in (concepts or []) + primary_interests:
            text = str(item).strip()
            if text and text not in key_themes:
                key_themes.append(text)

        if hasattr(memory, "save_session_summary"):
            memory.save_session_summary(
                user_id=getattr(memory, "owner_user_id", user_id),
                summary={
                    "session_id": user_id,
                    "date": datetime.now().date().isoformat(),
                    "key_themes": key_themes[:3],
                    "state_end": state_end,
                    "notable_moments": [
                        f"Р—Р°РїСЂРѕСЃ: {str(query or '')[:140]}",
                        f"РћС‚РІРµС‚: {str(answer or '')[:140]}",
                    ],
                },
            )
    except Exception as exc:
        if logger is not None:
            logger.warning("[MEMORY] save_session_summary skipped: %s", exc)


def _build_sources_from_blocks(blocks: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "block_id": b.block_id,
            "title": b.title,
            "document_title": b.document_title,
            "youtube_link": b.youtube_link,
            "start": b.start,
            "end": b.end,
            "block_type": getattr(b, "block_type", "unknown"),
            "complexity_score": getattr(b, "complexity_score", 0),
        }
        for b in blocks
    ]


def _attach_debug_payload(
    *,
    result: Dict[str, Any],
    debug_info: Optional[Dict[str, Any]],
    memory,
    elapsed_time: float,
    llm_result: Optional[Dict[str, Any]] = None,
    retrieval_details: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> None:
    if debug_info is None:
        return
    debug_info["memory_summary"] = memory.get_summary()
    debug_info["total_time"] = elapsed_time
    debug_info["llm_tokens"] = (llm_result or {}).get("tokens_used", 0)
    if retrieval_details is not None:
        result.setdefault("metadata", {})["retrieval_details"] = retrieval_details
    if sources is not None:
        result.setdefault("metadata", {})["sources"] = sources
    result["debug"] = debug_info


def _attach_success_observability(
    *,
    result: Dict[str, Any],
    strip_legacy_runtime_metadata,
    attach_debug_payload,
    debug_info: Optional[Dict[str, Any]],
    memory,
    elapsed_time: float,
    llm_result: Optional[Dict[str, Any]],
    retrieval_details: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    debug_trace: Optional[Dict[str, Any]] = None,
    finalize_success_debug_trace=None,
    finalize_success_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    result["metadata"] = strip_legacy_runtime_metadata(result.get("metadata", {}))
    attach_debug_payload(
        result=result,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        retrieval_details=retrieval_details,
        sources=sources,
    )
    if debug_trace is not None and finalize_success_debug_trace is not None:
        debug_trace = finalize_success_debug_trace(
            debug_trace,
            **(finalize_success_kwargs or {}),
        )
        result["debug_trace"] = debug_trace
    return debug_trace


def _handle_no_retrieval_partial_response(
    *,
    message: str,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
    routing_result,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    user_id: str,
    pipeline_stages: List[Dict[str, Any]],
    model_used: str,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    append_stages: List[Dict[str, Any]],
    set_working_state_best_effort,
    persist_turn,
    finalize_failure_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
) -> Dict[str, Any]:
    response = _build_partial_response(
        message,
        state_analysis,
        memory,
        start_time,
        query,
    )
    set_working_state_best_effort(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=routing_result,
        log_prefix="[ADAPTIVE] working_state update failed (partial):",
    )
    persist_turn(
        memory=memory,
        user_input=query,
        bot_response=response.get("answer", ""),
        user_state=state_analysis.primary_state.value if state_analysis else None,
        blocks_used=0,
        concepts=[],
        schedule_summary_task=schedule_summary_task,
    )
    if debug_info is not None:
        debug_info["memory_summary"] = memory.get_summary()
        debug_info["total_time"] = (datetime.now() - start_time).total_seconds()
        response["debug"] = debug_info
    if debug_trace is not None:
        debug_trace = finalize_failure_debug_trace(
            debug_trace,
            memory=memory,
            start_time=start_time,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=model_used,
            estimate_cost=estimate_cost,
            compute_anomalies=compute_anomalies,
            attach_trace_schema=attach_trace_schema,
            build_state_trajectory=build_state_trajectory,
            store_blob=store_blob,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
            blocks_after_cap=0,
            append_stages=append_stages,
        )
        response["debug_trace"] = debug_trace
    return response


def _run_no_retrieval_stage(
    *,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
    routing_result,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    user_id: str,
    pipeline_stages: List[Dict[str, Any]],
    model_used: str,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    set_working_state_best_effort,
    persist_turn,
    finalize_failure_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
) -> Dict[str, Any]:
    return _handle_no_retrieval_partial_response(
        message=(
            "Р С™ РЎРѓР С•Р В¶Р В°Р В»Р ВµР Р…Р С‘РЎР‹, РЎР‚Р ВµР В»Р ВµР Р†Р В°Р Р…РЎвЂљР Р…РЎвЂ№Р в„– Р СР В°РЎвЂљР ВµРЎР‚Р С‘Р В°Р В» "
            "Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…. Р СџР С•Р С—РЎР‚Р С•Р В±РЎС“Р в„–РЎвЂљР Вµ Р С—Р ВµРЎР‚Р ВµРЎвЂћР С•РЎР‚Р СРЎС“Р В»Р С‘РЎР‚Р С•Р Р†Р В°РЎвЂљРЎРЉ "
            "Р Р†Р С•Р С—РЎР‚Р С•РЎРѓ."
        ),
        state_analysis=state_analysis,
        memory=memory,
        start_time=start_time,
        query=query,
        routing_result=routing_result,
        schedule_summary_task=schedule_summary_task,
        debug_info=debug_info,
        debug_trace=debug_trace,
        session_store=session_store,
        user_id=user_id,
        pipeline_stages=pipeline_stages,
        model_used=model_used,
        initial_retrieved_blocks=initial_retrieved_blocks,
        reranked_blocks_for_trace=reranked_blocks_for_trace,
        append_stages=[
            {"name": "llm", "label": "LLM", "duration_ms": 0, "skipped": True},
            {
                "name": "format",
                "label": "Р В¤Р С•РЎР‚Р СР В°РЎвЂљР С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С‘Р Вµ",
                "duration_ms": 0,
                "skipped": True,
            },
        ],
        set_working_state_best_effort=set_working_state_best_effort,
        persist_turn=persist_turn,
        finalize_failure_debug_trace=finalize_failure_debug_trace,
        estimate_cost=estimate_cost,
        compute_anomalies=compute_anomalies,
        attach_trace_schema=attach_trace_schema,
        build_state_trajectory=build_state_trajectory,
        store_blob=store_blob,
    )


def _handle_llm_generation_error_response(
    *,
    llm_error: str,
    state_analysis: StateAnalysis,
    start_time: datetime,
    memory,
    query: str,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    user_id: str,
    pipeline_stages: List[Dict[str, Any]],
    model_used: str,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
) -> Dict[str, Any]:
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .pricing_helpers import _estimate_cost as _runtime_estimate_cost
    from .trace_helpers import _finalize_failure_debug_trace as _runtime_finalize_failure_debug_trace

    response = _build_error_response(
        f"Р С›РЎв‚¬Р С‘Р В±Р С”Р В° Р С—РЎР‚Р С‘ Р С–Р ВµР Р…Р ВµРЎР‚Р В°РЎвЂ Р С‘Р С‘ Р С•РЎвЂљР Р†Р ВµРЎвЂљР В°: {llm_error}",
        state_analysis,
        start_time,
    )

    _persist_turn_best_effort(
        memory=memory,
        user_input=query,
        bot_response=response.get("answer", ""),
        user_state=state_analysis.primary_state.value if state_analysis else None,
        blocks_used=0,
        concepts=[],
        schedule_summary_task=schedule_summary_task,
    )

    if debug_info is not None:
        debug_info["memory_summary"] = memory.get_summary()
        debug_info["total_time"] = (datetime.now() - start_time).total_seconds()
        response["debug"] = debug_info

    if debug_trace is not None:
        debug_trace = _runtime_finalize_failure_debug_trace(
            debug_trace,
            memory=memory,
            start_time=start_time,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=model_used,
            estimate_cost=_runtime_estimate_cost,
            compute_anomalies=_runtime_compute_anomalies,
            attach_trace_schema=_runtime_attach_trace_schema_status,
            build_state_trajectory=_runtime_build_state_trajectory,
            store_blob=_runtime_store_blob,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
        )
        response["debug_trace"] = debug_trace

    return response


def _build_unhandled_exception_response(
    *,
    exception: Exception,
    state_analysis: Optional[StateAnalysis],
    start_time: datetime,
    user_id: str,
    query: str,
    schedule_summary_task: bool,
    debug_trace: Optional[Dict[str, Any]],
    current_stage: str,
    session_store,
    pipeline_stages: List[Dict[str, Any]],
    llm_model_name: str,
) -> Dict[str, Any]:
    from ..conversation_memory import get_conversation_memory as _runtime_get_conversation_memory
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .pricing_helpers import _estimate_cost as _runtime_estimate_cost
    from .trace_helpers import (
        _finalize_failure_debug_trace as _runtime_finalize_failure_debug_trace,
        _strip_legacy_trace_fields as _runtime_strip_legacy_trace_fields,
    )

    response = _build_error_response(
        f"РџСЂРѕРёР·РѕС€Р»Р° РѕС€РёР±РєР° РїСЂРё РѕР±СЂР°Р±РѕС‚РєРµ Р·Р°РїСЂРѕСЃР°: {str(exception)}",
        state_analysis,
        start_time,
    )
    response["metadata"] = {"user_id": user_id}

    try:
        memory = _runtime_get_conversation_memory(user_id)
        _persist_turn_best_effort(
            memory=memory,
            user_input=query,
            bot_response=response["answer"],
            blocks_used=0,
            schedule_summary_task=schedule_summary_task,
        )
    except Exception:
        pass

    if debug_trace is not None:
        debug_trace["pipeline_error"] = {
            "stage": str(current_stage),
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "partial_trace_available": True,
        }
        try:
            memory = _runtime_get_conversation_memory(user_id)
            debug_trace = _runtime_finalize_failure_debug_trace(
                debug_trace,
                memory=memory,
                start_time=start_time,
                session_store=session_store,
                user_id=user_id,
                pipeline_stages=pipeline_stages,
                model_used=llm_model_name,
                estimate_cost=_runtime_estimate_cost,
                compute_anomalies=_runtime_compute_anomalies,
                attach_trace_schema=_runtime_attach_trace_schema_status,
                build_state_trajectory=_runtime_build_state_trajectory,
                store_blob=_runtime_store_blob,
                include_chunks=False,
                include_total_duration=False,
                strip_legacy_trace_fields=_runtime_strip_legacy_trace_fields,
            )
        except Exception:
            pass
        response["debug_trace"] = debug_trace

    return response



