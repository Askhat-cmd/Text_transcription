"""Response success-stage helpers extracted from response_utils (Wave 136)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state_classifier import StateAnalysis

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
    collect_llm_session_metrics,
    update_session_token_metrics,
    persist_turn,
    get_feedback_prompt_for_state,
    build_success_response,
    build_fast_success_metadata,
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    attach_success_observability,
    strip_legacy_runtime_metadata,
    attach_debug_payload,
    finalize_success_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
    strip_legacy_trace_fields,
    logger=None,
) -> Dict[str, Any]:
    llm_metrics = collect_llm_session_metrics(
        memory=memory,
        llm_result=llm_result if isinstance(llm_result, dict) else {},
        fallback_model_name=llm_model_name,
        update_session_token_metrics=update_session_token_metrics,
    )
    tokens_prompt = llm_metrics["tokens_prompt"]
    tokens_completion = llm_metrics["tokens_completion"]
    tokens_total = llm_metrics["tokens_total"]
    model_used = llm_metrics["model_used"]
    session_metrics = llm_metrics["session_metrics"]

    persist_turn(
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
        get_feedback_prompt_for_state(state_analysis.primary_state)
        if include_feedback_prompt
        else ""
    )

    result = build_success_response(
        answer=answer,
        state_analysis=state_analysis,
        path_recommendation=None,
        conversation_context=conversation_context,
        feedback_prompt=feedback_prompt,
        sources=[],
        concepts=[],
        metadata=build_fast_success_metadata(
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

    attach_success_observability(
        result=result,
        strip_legacy_runtime_metadata=strip_legacy_runtime_metadata,
        attach_debug_payload=attach_debug_payload,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        debug_trace=debug_trace,
        finalize_success_debug_trace=finalize_success_debug_trace,
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
            "estimate_cost": estimate_cost,
            "compute_anomalies": compute_anomalies,
            "attach_trace_schema": attach_trace_schema,
            "build_state_trajectory": build_state_trajectory,
            "store_blob": store_blob,
            "strip_legacy_trace_fields": strip_legacy_trace_fields,
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
    build_sources_from_blocks,
    log_blocks,
    build_success_response,
    build_full_success_metadata,
    attach_success_observability,
    strip_legacy_runtime_metadata,
    attach_debug_payload,
    finalize_success_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
    strip_legacy_trace_fields,
    logger=None,
) -> Dict[str, Any]:
    elapsed_time = (datetime.now() - start_time).total_seconds()
    sources = build_sources_from_blocks(adapted_blocks)
    log_blocks("SOURCES", adapted_blocks, limit=10)

    result = build_success_response(
        answer=answer,
        state_analysis=state_analysis,
        path_recommendation=path_recommendation,
        conversation_context=conversation_context,
        feedback_prompt=feedback_prompt,
        sources=sources,
        concepts=concepts,
        metadata=build_full_success_metadata(
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

    attach_success_observability(
        result=result,
        strip_legacy_runtime_metadata=strip_legacy_runtime_metadata,
        attach_debug_payload=attach_debug_payload,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        retrieval_details=(debug_info or {}).get("retrieval_details", {}),
        sources=sources,
        debug_trace=debug_trace,
        finalize_success_debug_trace=finalize_success_debug_trace,
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
            "estimate_cost": estimate_cost,
            "compute_anomalies": compute_anomalies,
            "attach_trace_schema": attach_trace_schema,
            "build_state_trajectory": build_state_trajectory,
            "store_blob": store_blob,
            "strip_legacy_trace_fields": strip_legacy_trace_fields,
            "aggregate_from_llm_calls": True,
            "include_summary_pending": True,
        },
    )

    if logger is not None:
        logger.info("[ADAPTIVE] response ready in %.2fs", elapsed_time)

    return result

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
    collect_llm_session_metrics,
    update_session_token_metrics,
    set_working_state_best_effort,
    build_path_recommendation_if_enabled,
    get_feedback_prompt_for_state,
    persist_turn,
    save_session_summary_best_effort,
    semantic_analyzer_cls,
    path_builder,
    logger=None,
) -> Dict[str, Any]:
    semantic_analyzer = semantic_analyzer_cls()
    semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
    concepts = semantic_data.get("primary_concepts", [])

    route_name = str(getattr(routing_result, "route", "") or "").lower()
    path_builder_blocked_routes = {"inform", "reflect", "contact_hold", "regulate"}
    path_recommendation = build_path_recommendation_if_enabled(
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
        feedback_prompt = get_feedback_prompt_for_state(state_analysis.primary_state)

    set_working_state_best_effort(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=routing_result,
        log_prefix="[ADAPTIVE] working_state update failed:",
    )

    llm_metrics = collect_llm_session_metrics(
        memory=memory,
        llm_result=llm_result if isinstance(llm_result, dict) else {},
        fallback_model_name=fallback_model_name,
        update_session_token_metrics=update_session_token_metrics,
    )
    tokens_prompt = llm_metrics["tokens_prompt"]
    tokens_completion = llm_metrics["tokens_completion"]
    tokens_total = llm_metrics["tokens_total"]
    model_used = llm_metrics["model_used"]
    session_metrics = llm_metrics["session_metrics"]

    persist_turn(
        memory=memory,
        user_input=query,
        bot_response=answer,
        user_state=state_analysis.primary_state.value,
        blocks_used=len(adapted_blocks),
        concepts=concepts,
        schedule_summary_task=schedule_summary_task,
    )
    save_session_summary_best_effort(
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
    prepare_post_llm,
    build_success_response,
) -> Dict[str, Any]:
    post_llm = prepare_post_llm()
    result = build_success_response(
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
    collect_llm_session_metrics,
    update_session_token_metrics,
    set_working_state_best_effort,
    build_path_recommendation_if_enabled,
    get_feedback_prompt_for_state,
    persist_turn,
    save_session_summary_best_effort,
    semantic_analyzer_cls,
    path_builder,
    build_full_path_success_response,
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
    build_sources_from_blocks,
    log_blocks,
    build_success_response,
    build_full_success_metadata,
    attach_success_observability,
    strip_legacy_runtime_metadata,
    attach_debug_payload,
    finalize_success_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
    strip_legacy_trace_fields,
    logger=None,
) -> Dict[str, Any]:
    success_stage = _finalize_full_path_success_stage(
        prepare_post_llm=lambda: _prepare_full_path_post_llm_artifacts(
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
            collect_llm_session_metrics=collect_llm_session_metrics,
            update_session_token_metrics=update_session_token_metrics,
            set_working_state_best_effort=set_working_state_best_effort,
            build_path_recommendation_if_enabled=build_path_recommendation_if_enabled,
            get_feedback_prompt_for_state=get_feedback_prompt_for_state,
            persist_turn=persist_turn,
            save_session_summary_best_effort=save_session_summary_best_effort,
            semantic_analyzer_cls=semantic_analyzer_cls,
            path_builder=path_builder,
            logger=logger,
        ),
        build_success_response=lambda path_recommendation, feedback_prompt, concepts, tokens_prompt, tokens_completion, tokens_total, model_used, session_metrics: build_full_path_success_response(
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
            build_sources_from_blocks=build_sources_from_blocks,
            log_blocks=log_blocks,
            build_success_response=build_success_response,
            build_full_success_metadata=build_full_success_metadata,
            attach_success_observability=attach_success_observability,
            strip_legacy_runtime_metadata=strip_legacy_runtime_metadata,
            attach_debug_payload=attach_debug_payload,
            finalize_success_debug_trace=finalize_success_debug_trace,
            estimate_cost=estimate_cost,
            compute_anomalies=compute_anomalies,
            attach_trace_schema=attach_trace_schema,
            build_state_trajectory=build_state_trajectory,
            store_blob=store_blob,
            strip_legacy_trace_fields=strip_legacy_trace_fields,
            logger=logger,
        ),
    )
    return success_stage["result"]

