"""Retrieval orchestration stage helpers (Wave 135)."""

from __future__ import annotations

from typing import Dict

from .retrieval_pipeline_helpers import (
    _prepare_hybrid_query_stage,
    _run_retrieval_and_rerank_stage,
)

def _run_retrieval_routing_context_stage(
    *,
    query: str,
    top_k: int,
    config,
    data_loader,
    get_retriever,
    logger,
    debug_trace,
    pipeline_stages,
    use_deterministic_router: bool,
    diagnostics_v1,
    pre_routing_result,
    voyage_reranker_cls,
    detect_routing_signals,
    state_analysis,
    memory,
    conversation_context: str,
    user_stage,
    route_resolver,
    confidence_scorer,
    decision_gate,
    informational_branch_enabled: bool,
    phase8_signals,
    correction_protocol_active: bool,
    practice_selector,
    practice_allowed_routes,
    practice_skip_routes,
    memory_context_bundle,
    mode_prompt_key,
    route_resolution_count: int,
    start_time,
    schedule_summary_task: bool,
    debug_info,
    session_store,
    user_id: str,
    model_used: str,
) -> Dict[str, Any]:
    from ..onboarding_flow import (
        build_first_turn_instruction as _runtime_build_first_turn_instruction,
        build_informational_guardrail_instruction as _runtime_build_informational_guardrail_instruction,
        build_mixed_query_instruction as _runtime_build_mixed_query_instruction,
        build_user_correction_instruction as _runtime_build_user_correction_instruction,
    )
    from .routing_context_helpers import (
        _finalize_routing_context_and_trace as _runtime_finalize_routing_context_and_trace,
        _resolve_routing_and_apply_block_cap as _runtime_resolve_routing_and_apply_block_cap,
    )
    from .trace_helpers import (
        _log_retrieval_pairs as _runtime_log_retrieval_pairs,
        _prepare_adapted_blocks_and_attach_observability as _runtime_prepare_adapted_blocks_and_attach_observability,
        _refresh_context_and_apply_trace_snapshot as _runtime_refresh_context_and_apply_trace_snapshot,
        _truncate_preview as _runtime_truncate_preview,
    )
    from .response_utils import _run_no_retrieval_stage as _runtime_run_no_retrieval_stage
    from .response_utils import _persist_turn as _runtime_persist_turn
    from .pricing_helpers import _estimate_cost as _runtime_estimate_cost
    from .mode_policy_helpers import resolve_mode_prompt as _runtime_resolve_mode_prompt
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .state_helpers import (
        _build_working_state as _runtime_build_working_state,
        _set_working_state_best_effort as _runtime_set_working_state_best_effort,
    )
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from .trace_helpers import _finalize_failure_debug_trace as _runtime_finalize_failure_debug_trace
    from ..decision import build_mode_directive as _runtime_build_mode_directive

    hybrid_query_stage = _prepare_hybrid_query_stage(
        query=query,
        diagnostics_v1=diagnostics_v1,
        state_analysis=state_analysis,
        memory=memory,
        conversation_context=conversation_context,
        config=config,
        logger=logger,
    )
    hybrid_query = hybrid_query_stage["hybrid_query"]

    retrieval_stage = _run_retrieval_and_rerank_stage(
        query=query,
        top_k=top_k,
        config=config,
        data_loader=data_loader,
        get_retriever=get_retriever,
        logger=logger,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        use_deterministic_router=use_deterministic_router,
        diagnostics_v1=diagnostics_v1,
        pre_routing_result=pre_routing_result,
        voyage_reranker_cls=voyage_reranker_cls,
        detect_routing_signals=detect_routing_signals,
        state_analysis=state_analysis,
        memory=memory,
        hybrid_query=hybrid_query,
    )
    retrieved_blocks = retrieval_stage["retrieved_blocks"]
    initial_retrieved_blocks = retrieval_stage["initial_retrieved_blocks"]
    reranked_blocks_for_trace = retrieval_stage["reranked_blocks_for_trace"]
    progressive_rag = retrieval_stage["progressive_rag"]
    should_run_rerank = retrieval_stage["should_run_rerank"]
    rerank_reason = retrieval_stage["rerank_reason"]
    rerank_k = retrieval_stage["rerank_k"]
    rerank_applied = retrieval_stage["rerank_applied"]
    routing_signals = retrieval_stage["routing_signals"]

    current_stage = "rerank" if rerank_applied else "retrieval"

    routing_cap_stage = _runtime_resolve_routing_and_apply_block_cap(
        use_deterministic_router=use_deterministic_router,
        diagnostics_v1=diagnostics_v1,
        user_stage=user_stage,
        route_resolver=route_resolver,
        confidence_scorer=confidence_scorer,
        pre_routing_result=pre_routing_result,
        decision_gate=decision_gate,
        retrieved_blocks=retrieved_blocks,
        informational_branch_enabled=informational_branch_enabled,
        resolve_mode_prompt=_runtime_resolve_mode_prompt,
        config=config,
        log_retrieval_pairs=_runtime_log_retrieval_pairs,
        build_mode_directive=_runtime_build_mode_directive,
        logger=logger,
    )
    routing_result = routing_cap_stage["routing_result"]
    block_cap = routing_cap_stage["block_cap"]
    route_resolution_count += int(routing_cap_stage["route_resolution_increment"])
    informational_mode = routing_cap_stage["informational_mode"]
    mode_prompt_key = routing_cap_stage["mode_prompt_key"]
    mode_prompt_override = routing_cap_stage["mode_prompt_override"]
    retrieved_blocks = routing_cap_stage["retrieved_blocks"]
    capped_retrieved_blocks = routing_cap_stage["capped_retrieved_blocks"]
    mode_directive = routing_cap_stage["mode_directive"]
    state_context_mode_prompt = routing_cap_stage["state_context_mode_prompt"]

    routing_context_stage = _runtime_finalize_routing_context_and_trace(
        informational_branch_enabled=informational_branch_enabled,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        informational_mode=informational_mode,
        build_first_turn_instruction=_runtime_build_first_turn_instruction,
        build_mixed_query_instruction=_runtime_build_mixed_query_instruction,
        build_user_correction_instruction=_runtime_build_user_correction_instruction,
        build_informational_guardrail_instruction=_runtime_build_informational_guardrail_instruction,
        routing_result=routing_result,
        diagnostics_v1=diagnostics_v1,
        query=query,
        memory=memory,
        practice_selector=practice_selector,
        practice_allowed_routes=practice_allowed_routes,
        practice_skip_routes=practice_skip_routes,
        logger=logger,
        debug_trace=debug_trace,
        mode_reason=mode_directive.reason,
        block_cap=block_cap,
        initial_retrieved_blocks=initial_retrieved_blocks,
        hybrid_query=hybrid_query,
        include_full_content=bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True)),
        truncate_preview=_runtime_truncate_preview,
        should_run_rerank=bool(should_run_rerank),
        rerank_reason=rerank_reason,
        rerank_applied=bool(rerank_applied),
        route_resolution_count=route_resolution_count,
        mode_prompt_key=mode_prompt_key,
        conversation_context=conversation_context,
        memory_context_bundle=memory_context_bundle,
        refresh_context_and_apply_trace_snapshot=_runtime_refresh_context_and_apply_trace_snapshot,
    )
    phase8_context_suffix = routing_context_stage["phase8_context_suffix"]
    selected_practice = routing_context_stage["selected_practice"]
    practice_alternatives = routing_context_stage["practice_alternatives"]
    practice_context_suffix = routing_context_stage["practice_context_suffix"]
    conversation_context = routing_context_stage["conversation_context"]

    if not retrieved_blocks:
        return {
            "current_stage": current_stage,
            "early_response": _runtime_run_no_retrieval_stage(
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
                set_working_state_best_effort=lambda **kwargs: _runtime_set_working_state_best_effort(
                    build_working_state=_runtime_build_working_state,
                    logger=logger,
                    **kwargs,
                ),
                persist_turn=_runtime_persist_turn,
                finalize_failure_debug_trace=_runtime_finalize_failure_debug_trace,
                estimate_cost=_runtime_estimate_cost,
                compute_anomalies=_runtime_compute_anomalies,
                attach_trace_schema=_runtime_attach_trace_schema_status,
                build_state_trajectory=_runtime_build_state_trajectory,
                store_blob=_runtime_store_blob,
            ),
        }

    retrieval_observability_stage = _runtime_prepare_adapted_blocks_and_attach_observability(
        retrieved_blocks=retrieved_blocks,
        routing_signals=routing_signals,
        progressive_rag=progressive_rag,
        debug_trace=debug_trace,
        logger=logger,
        debug_info=debug_info,
        hybrid_query=hybrid_query,
        initial_retrieved_blocks=initial_retrieved_blocks,
        reranked_blocks_for_trace=reranked_blocks_for_trace,
        capped_retrieved_blocks=capped_retrieved_blocks,
        rerank_k=rerank_k,
        should_run_rerank=should_run_rerank,
        rerank_reason=rerank_reason,
        rerank_applied=rerank_applied,
        block_cap=block_cap,
        routing_result=routing_result,
        route_resolution_count=route_resolution_count,
    )

    return {
        "current_stage": current_stage,
        "early_response": None,
        "hybrid_query": hybrid_query,
        "initial_retrieved_blocks": initial_retrieved_blocks,
        "reranked_blocks_for_trace": reranked_blocks_for_trace,
        "routing_result": routing_result,
        "block_cap": block_cap,
        "route_resolution_count": route_resolution_count,
        "informational_mode": informational_mode,
        "mode_prompt_key": mode_prompt_key,
        "mode_prompt_override": mode_prompt_override,
        "mode_directive": mode_directive,
        "state_context_mode_prompt": state_context_mode_prompt,
        "phase8_context_suffix": phase8_context_suffix,
        "selected_practice": selected_practice,
        "practice_alternatives": practice_alternatives,
        "practice_context_suffix": practice_context_suffix,
        "conversation_context": conversation_context,
        "blocks": retrieval_observability_stage["blocks"],
        "adapted_blocks": retrieval_observability_stage["adapted_blocks"],
    }
