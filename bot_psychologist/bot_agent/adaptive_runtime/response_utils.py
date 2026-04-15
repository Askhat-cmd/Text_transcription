"""Shared response helper builders extracted from answer_adaptive."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state_classifier import StateAnalysis, UserState


def _get_feedback_prompt_for_state(state: UserState) -> str:
    """Return feedback follow-up prompt based on detected user state."""
    prompts = {
        UserState.UNAWARE: "Стало ли понятнее, о чём речь? Что осталось непонятным?",
        UserState.CURIOUS: "Хотите узнать что-то ещё по этой теме?",
        UserState.OVERWHELMED: "Не слишком ли много информации? Нужно ли упростить?",
        UserState.RESISTANT: "Есть ли что-то, с чем вы не согласны? Давайте обсудим.",
        UserState.CONFUSED: "Прояснилось ли объяснение? Если нет, какая часть всё ещё непонятна?",
        UserState.COMMITTED: "Готовы ли вы начать практику? Какая поддержка нужна?",
        UserState.PRACTICING: "Как идёт практика? Есть ли сложности?",
        UserState.STAGNANT: "Что, по-вашему, мешает продвижению? Попробуем найти новый подход?",
        UserState.BREAKTHROUGH: "Поздравляю с инсайтом! Как планируете применить это понимание?",
        UserState.INTEGRATED: "Как это знание проявляется в вашей жизни?",
    }
    return prompts.get(state, "Был ли этот ответ полезен? Оцените от 1 до 5.")


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
        "feedback_prompt": "Попробуйте переформулировать вопрос.",
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
                        f"Запрос: {str(query or '')[:140]}",
                        f"Ответ: {str(answer or '')[:140]}",
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
    strip_legacy_runtime_metadata_fn,
    attach_debug_payload_fn,
    debug_info: Optional[Dict[str, Any]],
    memory,
    elapsed_time: float,
    llm_result: Optional[Dict[str, Any]],
    retrieval_details: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    debug_trace: Optional[Dict[str, Any]] = None,
    finalize_success_debug_trace_fn=None,
    finalize_success_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    result["metadata"] = strip_legacy_runtime_metadata_fn(result.get("metadata", {}))
    attach_debug_payload_fn(
        result=result,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        retrieval_details=retrieval_details,
        sources=sources,
    )
    if debug_trace is not None and finalize_success_debug_trace_fn is not None:
        debug_trace = finalize_success_debug_trace_fn(
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
    set_working_state_best_effort_fn,
    persist_turn_fn,
    finalize_failure_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
) -> Dict[str, Any]:
    response = _build_partial_response(
        message,
        state_analysis,
        memory,
        start_time,
        query,
    )
    set_working_state_best_effort_fn(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=routing_result,
        log_prefix="[ADAPTIVE] working_state update failed (partial):",
    )
    persist_turn_fn(
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
        debug_trace = finalize_failure_debug_trace_fn(
            debug_trace,
            memory=memory,
            start_time=start_time,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=model_used,
            estimate_cost_fn=estimate_cost_fn,
            compute_anomalies_fn=compute_anomalies_fn,
            attach_trace_schema_fn=attach_trace_schema_fn,
            build_state_trajectory_fn=build_state_trajectory_fn,
            store_blob_fn=store_blob_fn,
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
    set_working_state_best_effort_fn,
    persist_turn_fn,
    finalize_failure_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
) -> Dict[str, Any]:
    return _handle_no_retrieval_partial_response(
        message=(
            "Рљ СЃРѕР¶Р°Р»РµРЅРёСЋ, СЂРµР»РµРІР°РЅС‚РЅС‹Р№ РјР°С‚РµСЂРёР°Р» "
            "РЅРµ РЅР°Р№РґРµРЅ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРµСЂРµС„РѕСЂРјСѓР»РёСЂРѕРІР°С‚СЊ "
            "РІРѕРїСЂРѕСЃ."
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
                "label": "Р¤РѕСЂРјР°С‚РёСЂРѕРІР°РЅРёРµ",
                "duration_ms": 0,
                "skipped": True,
            },
        ],
        set_working_state_best_effort_fn=set_working_state_best_effort_fn,
        persist_turn_fn=persist_turn_fn,
        finalize_failure_debug_trace_fn=finalize_failure_debug_trace_fn,
        estimate_cost_fn=estimate_cost_fn,
        compute_anomalies_fn=compute_anomalies_fn,
        attach_trace_schema_fn=attach_trace_schema_fn,
        build_state_trajectory_fn=build_state_trajectory_fn,
        store_blob_fn=store_blob_fn,
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
    finalize_failure_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
) -> Dict[str, Any]:
    response = _build_error_response(
        f"РћС€РёР±РєР° РїСЂРё РіРµРЅРµСЂР°С†РёРё РѕС‚РІРµС‚Р°: {llm_error}",
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
        debug_trace = finalize_failure_debug_trace_fn(
            debug_trace,
            memory=memory,
            start_time=start_time,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=model_used,
            estimate_cost_fn=estimate_cost_fn,
            compute_anomalies_fn=compute_anomalies_fn,
            attach_trace_schema_fn=attach_trace_schema_fn,
            build_state_trajectory_fn=build_state_trajectory_fn,
            store_blob_fn=store_blob_fn,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
        )
        response["debug_trace"] = debug_trace

    return response


def _build_fast_path_success_response(
    *,
    answer: str,
    state_analysis: StateAnalysis,
    pre_routing_result,
    mode_directive_reason: str,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    conversation_context: str,
    memory_context_bundle,
    memory_trace_metrics: Dict[str, Any],
    query: str,
    include_feedback_prompt: bool,
    memory,
    schedule_summary_task: bool,
    user_id: str,
    start_time: datetime,
    llm_result: Dict[str, Any],
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    pipeline_stages: List[Dict[str, Any]],
    llm_model_name: str,
    collect_llm_session_metrics_fn,
    update_session_token_metrics_fn,
    persist_turn_fn,
    get_feedback_prompt_for_state_fn,
    build_success_response_fn,
    build_fast_success_metadata_fn,
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    attach_success_observability_fn,
    strip_legacy_runtime_metadata_fn,
    attach_debug_payload_fn,
    finalize_success_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
    strip_legacy_trace_fields_fn,
    logger=None,
) -> Dict[str, Any]:
    llm_metrics = collect_llm_session_metrics_fn(
        memory=memory,
        llm_result=llm_result if isinstance(llm_result, dict) else {},
        fallback_model_name=llm_model_name,
        update_session_token_metrics_fn=update_session_token_metrics_fn,
    )
    tokens_prompt = llm_metrics["tokens_prompt"]
    tokens_completion = llm_metrics["tokens_completion"]
    tokens_total = llm_metrics["tokens_total"]
    model_used = llm_metrics["model_used"]
    session_metrics = llm_metrics["session_metrics"]

    persist_turn_fn(
        memory=memory,
        user_input=query,
        bot_response=answer,
        user_state=state_analysis.primary_state.value,
        blocks_used=0,
        concepts=[],
        schedule_summary_task=schedule_summary_task,
    )

    memory_turns = len(memory.turns)
    summary_length = len(memory.summary) if memory.summary else 0
    summary_last_turn = memory.summary_updated_at
    elapsed_time = (datetime.now() - start_time).total_seconds()
    feedback_prompt = (
        get_feedback_prompt_for_state_fn(state_analysis.primary_state)
        if include_feedback_prompt
        else ""
    )

    result = build_success_response_fn(
        answer=answer,
        state_analysis=state_analysis,
        path_recommendation=None,
        conversation_context=conversation_context,
        feedback_prompt=feedback_prompt,
        sources=[],
        concepts=[],
        metadata=build_fast_success_metadata_fn(
            user_id=user_id,
            state_analysis=state_analysis,
            routing_result=pre_routing_result,
            mode_reason=mode_directive_reason,
            informational_mode=informational_mode,
            mode_prompt_key=mode_prompt_key,
            prompt_stack_v2_enabled=prompt_stack_v2_enabled,
            output_validation_enabled=output_validation_enabled,
            memory_context_mode=(
                "summary"
                if bool(getattr(memory_context_bundle, "summary_used", False))
                else "full"
            ),
            memory_trace_metrics=memory_trace_metrics,
            summary_length=summary_length,
            summary_last_turn=summary_last_turn,
            summary_pending_turn=memory.metadata.get("summary_pending_turn"),
            memory_turns=memory_turns,
            hybrid_query_len=len(query or ""),
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            session_metrics=session_metrics,
        ),
        elapsed_time=elapsed_time,
    )

    if debug_info is not None:
        debug_info["fast_path"] = True
        debug_info["routing"] = {
            "mode": pre_routing_result.mode,
            "track": getattr(pre_routing_result, "track", "direct"),
            "tone": getattr(pre_routing_result, "tone", "minimal"),
            "rule_id": pre_routing_result.decision.rule_id,
            "reason": pre_routing_result.decision.reason,
            "confidence_score": pre_routing_result.confidence_score,
            "confidence_level": pre_routing_result.confidence_level,
        }

    attach_success_observability_fn(
        result=result,
        strip_legacy_runtime_metadata_fn=strip_legacy_runtime_metadata_fn,
        attach_debug_payload_fn=attach_debug_payload_fn,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        debug_trace=debug_trace,
        finalize_success_debug_trace_fn=finalize_success_debug_trace_fn,
        finalize_success_kwargs={
            "elapsed_time": elapsed_time,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "tokens_total": tokens_total,
            "session_metrics": session_metrics,
            "memory": memory,
            "memory_trace_metrics": memory_trace_metrics,
            "start_time": start_time,
            "session_store": session_store,
            "user_id": user_id,
            "pipeline_stages": pipeline_stages,
            "model_used": str(model_used),
            "estimate_cost_fn": estimate_cost_fn,
            "compute_anomalies_fn": compute_anomalies_fn,
            "attach_trace_schema_fn": attach_trace_schema_fn,
            "build_state_trajectory_fn": build_state_trajectory_fn,
            "store_blob_fn": store_blob_fn,
            "strip_legacy_trace_fields_fn": strip_legacy_trace_fields_fn,
            "aggregate_from_llm_calls": False,
            "include_summary_pending": True,
        },
    )

    if logger is not None:
        logger.info("[ADAPTIVE] fast-path response ready in %.2fs", elapsed_time)

    return result


def _build_full_path_success_response(
    *,
    answer: str,
    state_analysis: StateAnalysis,
    path_recommendation: Optional[Dict[str, Any]],
    conversation_context: str,
    feedback_prompt: str,
    concepts: List[str],
    adapted_blocks: List[Any],
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    llm_result: Dict[str, Any],
    memory,
    start_time: datetime,
    user_id: str,
    routing_result,
    mode_directive_reason: str,
    route_resolution_count: int,
    selected_practice: Optional[str],
    practice_alternatives: List[str],
    block_cap: int,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    diagnostics_v1_payload: Optional[Dict[str, Any]],
    contradiction_detected: bool,
    cross_session_context_used: bool,
    memory_context_bundle,
    memory_trace_metrics: Dict[str, Any],
    hybrid_query: str,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    session_metrics: Dict[str, Any],
    model_used: str,
    session_store,
    pipeline_stages: List[Dict[str, Any]],
    build_sources_from_blocks_fn,
    log_blocks_fn,
    build_success_response_fn,
    build_full_success_metadata_fn,
    attach_success_observability_fn,
    strip_legacy_runtime_metadata_fn,
    attach_debug_payload_fn,
    finalize_success_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
    strip_legacy_trace_fields_fn,
    logger=None,
) -> Dict[str, Any]:
    elapsed_time = (datetime.now() - start_time).total_seconds()
    sources = build_sources_from_blocks_fn(adapted_blocks)
    log_blocks_fn("SOURCES", adapted_blocks, limit=10)

    result = build_success_response_fn(
        answer=answer,
        state_analysis=state_analysis,
        path_recommendation=path_recommendation,
        conversation_context=conversation_context,
        feedback_prompt=feedback_prompt,
        sources=sources,
        concepts=concepts,
        metadata=build_full_success_metadata_fn(
            user_id=user_id,
            state_analysis=state_analysis,
            routing_result=routing_result,
            mode_reason=mode_directive_reason,
            route_resolution_count=route_resolution_count,
            blocks_used=len(adapted_blocks),
            selected_practice=selected_practice,
            practice_alternatives=practice_alternatives,
            retrieval_block_cap=block_cap,
            informational_mode=informational_mode,
            mode_prompt_key=mode_prompt_key,
            prompt_stack_v2_enabled=prompt_stack_v2_enabled,
            output_validation_enabled=output_validation_enabled,
            diagnostics_v1_payload=diagnostics_v1_payload,
            contradiction_detected=contradiction_detected,
            cross_session_context_used=cross_session_context_used,
            memory_context_mode=(
                "summary"
                if bool(getattr(memory_context_bundle, "summary_used", False))
                else "full"
            ),
            memory_trace_metrics=memory_trace_metrics,
            summary_length=len(memory.summary) if memory.summary else 0,
            summary_last_turn=memory.summary_updated_at,
            summary_pending_turn=memory.metadata.get("summary_pending_turn"),
            memory_turns=len(memory.turns),
            hybrid_query_len=len(hybrid_query),
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            session_metrics=session_metrics,
        ),
        elapsed_time=elapsed_time,
    )

    attach_success_observability_fn(
        result=result,
        strip_legacy_runtime_metadata_fn=strip_legacy_runtime_metadata_fn,
        attach_debug_payload_fn=attach_debug_payload_fn,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        retrieval_details=(debug_info or {}).get("retrieval_details", {}),
        sources=sources,
        debug_trace=debug_trace,
        finalize_success_debug_trace_fn=finalize_success_debug_trace_fn,
        finalize_success_kwargs={
            "elapsed_time": elapsed_time,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "tokens_total": tokens_total,
            "session_metrics": session_metrics,
            "memory": memory,
            "memory_trace_metrics": memory_trace_metrics,
            "start_time": start_time,
            "session_store": session_store,
            "user_id": user_id,
            "pipeline_stages": pipeline_stages,
            "model_used": str(model_used),
            "estimate_cost_fn": estimate_cost_fn,
            "compute_anomalies_fn": compute_anomalies_fn,
            "attach_trace_schema_fn": attach_trace_schema_fn,
            "build_state_trajectory_fn": build_state_trajectory_fn,
            "store_blob_fn": store_blob_fn,
            "strip_legacy_trace_fields_fn": strip_legacy_trace_fields_fn,
            "aggregate_from_llm_calls": True,
            "include_summary_pending": True,
        },
    )

    if logger is not None:
        logger.info("[ADAPTIVE] response ready in %.2fs", elapsed_time)

    return result


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
    from .runtime_misc_helpers import _estimate_cost as _runtime_estimate_cost
    from .trace_helpers import (
        _finalize_failure_debug_trace as _runtime_finalize_failure_debug_trace,
        _strip_legacy_trace_fields as _runtime_strip_legacy_trace_fields,
    )

    response = _build_error_response(
        f"Произошла ошибка при обработке запроса: {str(exception)}",
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
                estimate_cost_fn=_runtime_estimate_cost,
                compute_anomalies_fn=_runtime_compute_anomalies,
                attach_trace_schema_fn=_runtime_attach_trace_schema_status,
                build_state_trajectory_fn=_runtime_build_state_trajectory,
                store_blob_fn=_runtime_store_blob,
                include_chunks=False,
                include_total_duration=False,
                strip_legacy_trace_fields_fn=_runtime_strip_legacy_trace_fields,
            )
        except Exception:
            pass
        response["debug_trace"] = debug_trace

    return response


def _prepare_full_path_post_llm_artifacts(
    *,
    memory,
    query: str,
    answer: str,
    state_analysis: StateAnalysis,
    routing_result,
    adapted_blocks: List[Any],
    include_path_recommendation: bool,
    include_feedback_prompt: bool,
    user_id: str,
    user_level_enum,
    llm_result: Dict[str, Any],
    fallback_model_name: str,
    schedule_summary_task: bool,
    collect_llm_session_metrics_fn,
    update_session_token_metrics_fn,
    set_working_state_best_effort_fn,
    build_path_recommendation_if_enabled_fn,
    get_feedback_prompt_for_state_fn,
    persist_turn_fn,
    save_session_summary_best_effort_fn,
    semantic_analyzer_cls,
    path_builder,
    logger=None,
) -> Dict[str, Any]:
    semantic_analyzer = semantic_analyzer_cls()
    semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
    concepts = semantic_data.get("primary_concepts", [])

    route_name = str(getattr(routing_result, "route", "") or "").lower()
    path_builder_blocked_routes = {"inform", "reflect", "contact_hold", "regulate"}
    path_recommendation = build_path_recommendation_if_enabled_fn(
        include_path_recommendation=include_path_recommendation,
        state_analysis=state_analysis,
        route_name=route_name,
        path_builder_blocked_routes=path_builder_blocked_routes,
        user_id=user_id,
        user_level_enum=user_level_enum,
        memory=memory,
        path_builder=path_builder,
        logger=logger,
    )

    feedback_prompt = ""
    if include_feedback_prompt:
        feedback_prompt = get_feedback_prompt_for_state_fn(state_analysis.primary_state)

    set_working_state_best_effort_fn(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=routing_result,
        log_prefix="[ADAPTIVE] working_state update failed:",
    )

    llm_metrics = collect_llm_session_metrics_fn(
        memory=memory,
        llm_result=llm_result if isinstance(llm_result, dict) else {},
        fallback_model_name=fallback_model_name,
        update_session_token_metrics_fn=update_session_token_metrics_fn,
    )
    tokens_prompt = llm_metrics["tokens_prompt"]
    tokens_completion = llm_metrics["tokens_completion"]
    tokens_total = llm_metrics["tokens_total"]
    model_used = llm_metrics["model_used"]
    session_metrics = llm_metrics["session_metrics"]

    persist_turn_fn(
        memory=memory,
        user_input=query,
        bot_response=answer,
        user_state=state_analysis.primary_state.value,
        blocks_used=len(adapted_blocks),
        concepts=concepts,
        schedule_summary_task=schedule_summary_task,
    )
    save_session_summary_best_effort_fn(
        memory=memory,
        user_id=user_id,
        query=query,
        answer=answer,
        state_end=state_analysis.primary_state.value,
        concepts=concepts,
        logger=logger,
    )

    return {
        "concepts": concepts,
        "path_recommendation": path_recommendation,
        "feedback_prompt": feedback_prompt,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "model_used": model_used,
        "session_metrics": session_metrics,
    }


def _finalize_full_path_success_stage(
    *,
    prepare_post_llm_fn,
    build_success_response_fn,
) -> Dict[str, Any]:
    post_llm = prepare_post_llm_fn()
    result = build_success_response_fn(
        path_recommendation=post_llm["path_recommendation"],
        feedback_prompt=post_llm["feedback_prompt"],
        concepts=post_llm["concepts"],
        tokens_prompt=post_llm["tokens_prompt"],
        tokens_completion=post_llm["tokens_completion"],
        tokens_total=post_llm["tokens_total"],
        model_used=post_llm["model_used"],
        session_metrics=post_llm["session_metrics"],
    )
    return {
        "result": result,
        "post_llm": post_llm,
    }


def _run_full_path_success_stage(
    *,
    memory,
    query: str,
    answer: str,
    state_analysis: StateAnalysis,
    routing_result,
    adapted_blocks: List[Any],
    include_path_recommendation: bool,
    include_feedback_prompt: bool,
    user_id: str,
    user_level_enum,
    llm_result: Dict[str, Any],
    fallback_model_name: str,
    schedule_summary_task: bool,
    collect_llm_session_metrics_fn,
    update_session_token_metrics_fn,
    set_working_state_best_effort_fn,
    build_path_recommendation_if_enabled_fn,
    get_feedback_prompt_for_state_fn,
    persist_turn_fn,
    save_session_summary_best_effort_fn,
    semantic_analyzer_cls,
    path_builder,
    build_full_path_success_response_fn,
    conversation_context: str,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    start_time: datetime,
    mode_directive_reason: str,
    route_resolution_count: int,
    selected_practice: Optional[Dict[str, Any]],
    practice_alternatives: List[Dict[str, Any]],
    block_cap: int,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    diagnostics_v1_payload: Optional[Dict[str, Any]],
    contradiction_detected: bool,
    cross_session_context_used: bool,
    memory_context_bundle,
    memory_trace_metrics: Dict[str, Any],
    hybrid_query: str,
    session_store,
    pipeline_stages: List[Dict[str, Any]],
    build_sources_from_blocks_fn,
    log_blocks_fn,
    build_success_response_fn,
    build_full_success_metadata_fn,
    attach_success_observability_fn,
    strip_legacy_runtime_metadata_fn,
    attach_debug_payload_fn,
    finalize_success_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
    strip_legacy_trace_fields_fn,
    logger=None,
) -> Dict[str, Any]:
    success_stage = _finalize_full_path_success_stage(
        prepare_post_llm_fn=lambda: _prepare_full_path_post_llm_artifacts(
            memory=memory,
            query=query,
            answer=answer,
            state_analysis=state_analysis,
            routing_result=routing_result,
            adapted_blocks=adapted_blocks,
            include_path_recommendation=include_path_recommendation,
            include_feedback_prompt=include_feedback_prompt,
            user_id=user_id,
            user_level_enum=user_level_enum,
            llm_result=llm_result,
            fallback_model_name=fallback_model_name,
            schedule_summary_task=schedule_summary_task,
            collect_llm_session_metrics_fn=collect_llm_session_metrics_fn,
            update_session_token_metrics_fn=update_session_token_metrics_fn,
            set_working_state_best_effort_fn=set_working_state_best_effort_fn,
            build_path_recommendation_if_enabled_fn=build_path_recommendation_if_enabled_fn,
            get_feedback_prompt_for_state_fn=get_feedback_prompt_for_state_fn,
            persist_turn_fn=persist_turn_fn,
            save_session_summary_best_effort_fn=save_session_summary_best_effort_fn,
            semantic_analyzer_cls=semantic_analyzer_cls,
            path_builder=path_builder,
            logger=logger,
        ),
        build_success_response_fn=lambda path_recommendation, feedback_prompt, concepts, tokens_prompt, tokens_completion, tokens_total, model_used, session_metrics: build_full_path_success_response_fn(
            answer=answer,
            state_analysis=state_analysis,
            path_recommendation=path_recommendation,
            conversation_context=conversation_context,
            feedback_prompt=feedback_prompt,
            concepts=concepts,
            adapted_blocks=adapted_blocks,
            debug_info=debug_info,
            debug_trace=debug_trace,
            llm_result=llm_result,
            memory=memory,
            start_time=start_time,
            user_id=user_id,
            routing_result=routing_result,
            mode_directive_reason=mode_directive_reason,
            route_resolution_count=route_resolution_count,
            selected_practice=selected_practice,
            practice_alternatives=practice_alternatives,
            block_cap=block_cap,
            informational_mode=informational_mode,
            mode_prompt_key=mode_prompt_key,
            prompt_stack_v2_enabled=prompt_stack_v2_enabled,
            output_validation_enabled=output_validation_enabled,
            diagnostics_v1_payload=diagnostics_v1_payload,
            contradiction_detected=contradiction_detected,
            cross_session_context_used=cross_session_context_used,
            memory_context_bundle=memory_context_bundle,
            memory_trace_metrics=memory_trace_metrics,
            hybrid_query=hybrid_query,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            session_metrics=session_metrics,
            model_used=str(model_used),
            session_store=session_store,
            pipeline_stages=pipeline_stages,
            build_sources_from_blocks_fn=build_sources_from_blocks_fn,
            log_blocks_fn=log_blocks_fn,
            build_success_response_fn=build_success_response_fn,
            build_full_success_metadata_fn=build_full_success_metadata_fn,
            attach_success_observability_fn=attach_success_observability_fn,
            strip_legacy_runtime_metadata_fn=strip_legacy_runtime_metadata_fn,
            attach_debug_payload_fn=attach_debug_payload_fn,
            finalize_success_debug_trace_fn=finalize_success_debug_trace_fn,
            estimate_cost_fn=estimate_cost_fn,
            compute_anomalies_fn=compute_anomalies_fn,
            attach_trace_schema_fn=attach_trace_schema_fn,
            build_state_trajectory_fn=build_state_trajectory_fn,
            store_blob_fn=store_blob_fn,
            strip_legacy_trace_fields_fn=strip_legacy_trace_fields_fn,
            logger=logger,
        ),
    )
    return success_stage["result"]
