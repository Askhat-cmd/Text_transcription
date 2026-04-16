"""Full-path stage helpers extracted from runtime_misc_helpers (Wave 131)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .llm_runtime_helpers import (
    _build_prompt_stack_override,
    _collect_llm_session_metrics,
    _format_and_validate_llm_answer,
    _generate_llm_with_trace,
    _run_llm_generation_cycle,
    _run_validation_retry_generation,
)
from .pricing_helpers import _estimate_cost
from .runtime_adapter_helpers import (
    _build_runtime_output_validation_policy_adapter,
    _build_set_working_state_best_effort_adapter,
)


def _run_full_path_llm_stage(
    *,
    query: str,
    adapted_blocks: List[Any],
    conversation_context: str,
    routing_result,
    state_context: str,
    sd_primary: str,
    config,
    session_store,
    user_id: str,
    mode_prompt_override: Optional[str],
    informational_mode: bool,
    diagnostics_payload: Optional[Dict[str, Any]],
    phase8_signals,
    correction_protocol_active: bool,
    prompt_stack_enabled: bool,
    prompt_registry,
    mode_prompt: str,
    debug_trace: Optional[Dict[str, Any]],
    pipeline_stages: List[Dict[str, Any]],
    response_generator_cls,
    response_formatter_cls,
    apply_output_validation_policy,
    state_analysis,
    start_time: datetime,
    memory,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    llm_model_name: str,
    logger,
) -> Dict[str, Any]:
    from .response_failure_helpers import (
        _handle_llm_generation_error_response as _runtime_handle_llm_generation_error_response,
    )
    from .trace_helpers import (
        _apply_output_validation_observability as _runtime_apply_output_validation_observability,
        _build_llm_call_trace as _runtime_build_llm_call_trace,
        _prepare_llm_prompt_previews as _runtime_prepare_llm_prompt_previews,
    )

    llm_result, response_generator, _prompt_stack_meta, system_prompt_override = _run_llm_generation_cycle(
        response_generator_cls=response_generator_cls,
        query=query,
        blocks=adapted_blocks,
        conversation_context=conversation_context,
        mode=routing_result.mode,
        confidence_level=routing_result.confidence_level,
        forbid=routing_result.decision.forbid,
        additional_system_context=state_context,
        sd_level=sd_primary,
        config=config,
        session_store=session_store,
        session_id=user_id,
        mode_prompt_override=mode_prompt_override,
        informational_mode=informational_mode,
        route=getattr(routing_result, "route", ""),
        diagnostics_payload=diagnostics_payload,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        prompt_stack_enabled=prompt_stack_enabled,
        prompt_registry=prompt_registry,
        mode_prompt=mode_prompt,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        build_prompt_stack_override=_build_prompt_stack_override,
        prepare_llm_prompt_previews=_runtime_prepare_llm_prompt_previews,
        generate_llm_with_trace=_generate_llm_with_trace,
        build_llm_call_trace=_runtime_build_llm_call_trace,
    )

    if llm_result.get("error") and llm_result["error"] not in ["no_blocks"]:
        logger.error("[ADAPTIVE] LLM error: %s", llm_result["error"])
        response = _runtime_handle_llm_generation_error_response(
            llm_error=str(llm_result.get("error", "")),
            state_analysis=state_analysis,
            start_time=start_time,
            memory=memory,
            query=query,
            schedule_summary_task=schedule_summary_task,
            debug_info=debug_info,
            debug_trace=debug_trace,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=llm_model_name,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
        )
        return {
            "error_response": response,
            "llm_result": llm_result,
            "answer": "",
        }

    answer = _format_and_validate_llm_answer(
        llm_result=llm_result,
        response_generator=response_generator,
        query=query,
        blocks=adapted_blocks,
        conversation_context=conversation_context,
        mode=routing_result.mode,
        confidence_level=routing_result.confidence_level,
        forbid=routing_result.decision.forbid,
        additional_system_context=state_context,
        sd_level=sd_primary,
        config=config,
        session_store=session_store,
        session_id=user_id,
        mode_prompt_override=mode_prompt_override,
        informational_mode=informational_mode,
        system_prompt_override=system_prompt_override,
        route=getattr(routing_result, "route", ""),
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        fallback_model_name=llm_model_name,
        include_retry_llm_trace=True,
        response_formatter_cls=response_formatter_cls,
        run_validation_retry_generation=_run_validation_retry_generation,
        apply_output_validation_policy=apply_output_validation_policy,
        apply_output_validation_observability=_runtime_apply_output_validation_observability,
    )
    return {
        "error_response": None,
        "llm_result": llm_result,
        "answer": answer,
    }


def _run_generation_and_success_stage(
    *,
    query: str,
    state_analysis,
    routing_result,
    diagnostics_v1,
    contradiction_hint: str,
    cross_session_context: str,
    phase8_context_suffix: str,
    practice_context_suffix: str,
    state_context_mode_prompt: str,
    adapted_blocks,
    sd_primary: str,
    config,
    session_store,
    user_id: str,
    mode_prompt_override: Optional[str],
    informational_mode: bool,
    phase8_signals,
    correction_protocol_active: bool,
    prompt_stack_enabled: bool,
    prompt_registry,
    mode_directive,
    debug_trace,
    pipeline_stages,
    response_generator_cls,
    response_formatter_cls,
    start_time: datetime,
    memory,
    schedule_summary_task: bool,
    debug_info,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    llm_model_name: str,
    logger,
    include_path_recommendation: bool,
    include_feedback_prompt: bool,
    user_level_enum,
    conversation_context: str,
    mode_prompt_key: Optional[str],
    route_resolution_count: int,
    selected_practice,
    practice_alternatives,
    block_cap: int,
    output_validation_enabled: bool,
    memory_context_bundle,
    memory_trace_metrics,
    hybrid_query: str,
    contradiction_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from ..path_builder import path_builder as _runtime_path_builder
    from ..semantic_analyzer import SemanticAnalyzer as _runtime_semantic_analyzer_cls
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .response_success_helpers import (
        _build_full_path_success_response as _runtime_build_full_path_success_response,
        _run_full_path_success_stage as _runtime_run_full_path_success_stage,
    )
    from .response_utils import (
        _attach_debug_payload as _runtime_attach_debug_payload,
        _attach_success_observability as _runtime_attach_success_observability,
        _build_full_success_metadata as _runtime_build_full_success_metadata,
        _build_path_recommendation_if_enabled as _runtime_build_path_recommendation_if_enabled,
        _build_sources_from_blocks as _runtime_build_sources_from_blocks,
        _build_success_response as _runtime_build_success_response,
        _get_feedback_prompt_for_state as _runtime_get_feedback_prompt_for_state,
        _persist_turn as _runtime_persist_turn,
        _save_session_summary_best_effort as _runtime_save_session_summary_best_effort,
    )
    from .state_helpers import (
        _build_state_context as _runtime_build_state_context,
        _build_working_state as _runtime_build_working_state,
        _compose_state_context as _runtime_compose_state_context,
        _set_working_state_best_effort as _runtime_set_working_state_best_effort,
    )
    from .trace_helpers import (
        _finalize_success_debug_trace as _runtime_finalize_success_debug_trace,
        _log_blocks as _runtime_log_blocks,
        _strip_legacy_runtime_metadata as _runtime_strip_legacy_runtime_metadata,
        _strip_legacy_trace_fields as _runtime_strip_legacy_trace_fields,
        _update_session_token_metrics as _runtime_update_session_token_metrics,
    )

    _runtime_apply_output_validation_policy_adapter = _build_runtime_output_validation_policy_adapter(
        force_enabled=output_validation_enabled,
    )

    logger.debug("🤖 Этап 4: Генерация ответа...")

    state_context = _runtime_compose_state_context(
        state_analysis=state_analysis,
        mode_prompt=state_context_mode_prompt,
        nervous_system_state=(
            diagnostics_v1.nervous_system_state if diagnostics_v1 else "window"
        ),
        request_function=(
            diagnostics_v1.request_function if diagnostics_v1 else "understand"
        ),
        contradiction_suggestion=contradiction_hint,
        cross_session_context=cross_session_context,
        phase8_context_suffix=phase8_context_suffix,
        practice_context_suffix=practice_context_suffix,
        build_state_context=_runtime_build_state_context,
    )

    llm_stage = _run_full_path_llm_stage(
        query=query,
        adapted_blocks=adapted_blocks,
        conversation_context=conversation_context,
        routing_result=routing_result,
        state_context=state_context,
        sd_primary=sd_primary,
        config=config,
        session_store=session_store,
        user_id=user_id,
        mode_prompt_override=mode_prompt_override,
        informational_mode=informational_mode,
        diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        prompt_stack_enabled=prompt_stack_enabled,
        prompt_registry=prompt_registry,
        mode_prompt=mode_directive.prompt,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        response_generator_cls=response_generator_cls,
        response_formatter_cls=response_formatter_cls,
        apply_output_validation_policy=_runtime_apply_output_validation_policy_adapter,
        state_analysis=state_analysis,
        start_time=start_time,
        memory=memory,
        schedule_summary_task=schedule_summary_task,
        debug_info=debug_info,
        initial_retrieved_blocks=initial_retrieved_blocks,
        reranked_blocks_for_trace=reranked_blocks_for_trace,
        llm_model_name=llm_model_name,
        logger=logger,
    )
    if llm_stage["error_response"] is not None:
        return {"current_stage": "llm", "result": llm_stage["error_response"]}

    llm_result = llm_stage["llm_result"]
    answer = llm_stage["answer"]

    logger.debug("🔬 Этап 5: Семантический анализ...")
    logger.debug("🛤️ Этап 6: Рекомендация пути...")
    logger.debug("📝 Этап 7: Подготовка обратной связи...")
    logger.debug("💾 Этап 8: Сохранение в память...")

    set_working_state_best_effort = _build_set_working_state_best_effort_adapter(
        set_working_state_best_effort=_runtime_set_working_state_best_effort,
        build_working_state=_runtime_build_working_state,
        logger=logger,
    )

    result = _runtime_run_full_path_success_stage(
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
        fallback_model_name=llm_model_name,
        schedule_summary_task=schedule_summary_task,
        collect_llm_session_metrics=_collect_llm_session_metrics,
        update_session_token_metrics=_runtime_update_session_token_metrics,
        set_working_state_best_effort=set_working_state_best_effort,
        build_path_recommendation_if_enabled=_runtime_build_path_recommendation_if_enabled,
        get_feedback_prompt_for_state=_runtime_get_feedback_prompt_for_state,
        persist_turn=_runtime_persist_turn,
        save_session_summary_best_effort=_runtime_save_session_summary_best_effort,
        semantic_analyzer_cls=_runtime_semantic_analyzer_cls,
        path_builder=_runtime_path_builder,
        build_full_path_success_response=_runtime_build_full_path_success_response,
        conversation_context=conversation_context,
        debug_info=debug_info,
        debug_trace=debug_trace,
        start_time=start_time,
        mode_directive_reason=mode_directive.reason,
        route_resolution_count=route_resolution_count,
        selected_practice=selected_practice,
        practice_alternatives=practice_alternatives,
        block_cap=block_cap,
        informational_mode=informational_mode,
        mode_prompt_key=mode_prompt_key,
        prompt_stack_v2_enabled=prompt_stack_enabled,
        output_validation_enabled=output_validation_enabled,
        diagnostics_v1_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
        contradiction_detected=bool((contradiction_info or {}).get("has_contradiction", False)),
        cross_session_context_used=bool(cross_session_context),
        memory_context_bundle=memory_context_bundle,
        memory_trace_metrics=memory_trace_metrics,
        hybrid_query=hybrid_query,
        session_store=session_store,
        pipeline_stages=pipeline_stages,
        build_sources_from_blocks=_runtime_build_sources_from_blocks,
        log_blocks=_runtime_log_blocks,
        build_success_response=_runtime_build_success_response,
        build_full_success_metadata=_runtime_build_full_success_metadata,
        attach_success_observability=_runtime_attach_success_observability,
        strip_legacy_runtime_metadata=_runtime_strip_legacy_runtime_metadata,
        attach_debug_payload=_runtime_attach_debug_payload,
        finalize_success_debug_trace=_runtime_finalize_success_debug_trace,
        estimate_cost=_estimate_cost,
        compute_anomalies=_runtime_compute_anomalies,
        attach_trace_schema=_runtime_attach_trace_schema_status,
        build_state_trajectory=_runtime_build_state_trajectory,
        store_blob=_runtime_store_blob,
        strip_legacy_trace_fields=_runtime_strip_legacy_trace_fields,
        logger=logger,
    )

    return {"current_stage": "success", "result": result}
