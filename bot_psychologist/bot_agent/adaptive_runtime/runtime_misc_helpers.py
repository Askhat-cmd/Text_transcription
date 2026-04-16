"""Runtime misc helpers extracted from answer_adaptive (Wave 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .bootstrap_runtime_helpers import (
    _prepare_adaptive_run_context,
    _run_bootstrap_and_onboarding_guard,
)
from .llm_runtime_helpers import (
    _build_prompt_stack_override,
    _collect_llm_session_metrics,
    _format_and_validate_llm_answer,
    _generate_llm_with_trace,
    _run_llm_generation_cycle,
    _run_validation_retry_generation,
)
from .runtime_adapter_helpers import (
    _build_runtime_output_validation_policy_adapter,
    _build_set_working_state_best_effort_adapter,
)


COST_PER_1K_TOKENS = {
    "gpt-5.2": {"input": 0.00175, "output": 0.01400},
    "gpt-5.1": {"input": 0.00125, "output": 0.01000},
    "gpt-5": {"input": 0.00125, "output": 0.01000},
    "gpt-5-mini": {"input": 0.00025, "output": 0.00200},
    "gpt-5-nano": {"input": 0.00005, "output": 0.00040},
    "gpt-4.1": {"input": 0.00200, "output": 0.00800},
    "gpt-4.1-mini": {"input": 0.00040, "output": 0.00160},
    "gpt-4.1-nano": {"input": 0.00010, "output": 0.00040},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "default": {"input": 0.00125, "output": 0.01000},
}


def _estimate_cost(llm_calls: List[Dict], model_name: str) -> float:
    rates = COST_PER_1K_TOKENS.get((model_name or "").lower(), COST_PER_1K_TOKENS["default"])
    total = 0.0
    for call in llm_calls or []:
        # Support explicit 0 values by avoiding plain `or` fallback.
        input_tokens = (
            call.get("tokens_prompt")
            if call.get("tokens_prompt") is not None
            else call.get("prompt_tokens")
            if call.get("prompt_tokens") is not None
            else 0
        )
        output_tokens = (
            call.get("tokens_completion")
            if call.get("tokens_completion") is not None
            else call.get("completion_tokens")
            if call.get("completion_tokens") is not None
            else 0
        )
        try:
            input_tokens = float(input_tokens)
            output_tokens = float(output_tokens)
        except (TypeError, ValueError):
            input_tokens = 0.0
            output_tokens = 0.0
        total += (input_tokens / 1000) * rates["input"]
        total += (output_tokens / 1000) * rates["output"]
    return round(total, 6)


def _run_fast_path_stage(
    *,
    fast_path_enabled: bool,
    logger,
    pre_routing_result,
    debug_trace: Optional[Dict[str, Any]],
    query: str,
    config,
    pipeline_stages: List[Dict[str, Any]],
    informational_mode: bool,
    memory,
    conversation_context: str,
    memory_context_bundle,
    diagnostics_payload: Optional[Dict[str, Any]],
    phase8_signals,
    correction_protocol_active: bool,
    informational_branch_enabled: bool,
    state_analysis,
    contradiction_hint: str,
    cross_session_context: str,
    diagnostics_v1,
    response_generator_cls,
    sd_primary: str,
    session_store,
    user_id: str,
    mode_prompt_override: Optional[str],
    prompt_stack_enabled: bool,
    prompt_registry,
    response_formatter_cls,
    include_feedback_prompt: bool,
    mode_prompt_key: Optional[str],
    memory_trace_metrics: Dict[str, Any],
    schedule_summary_task: bool,
    start_time: datetime,
    debug_info: Optional[Dict[str, Any]],
    llm_model_name: str,
    output_validation_enabled: bool,
) -> Optional[Dict[str, Any]]:
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from ..decision import build_mode_directive as _runtime_build_mode_directive
    from ..onboarding_flow import (
        build_first_turn_instruction as _runtime_build_first_turn_instruction,
        build_informational_guardrail_instruction as _runtime_build_informational_guardrail_instruction,
        build_mixed_query_instruction as _runtime_build_mixed_query_instruction,
        build_user_correction_instruction as _runtime_build_user_correction_instruction,
    )
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .routing_stage_helpers import (
        _apply_fast_path_debug_bootstrap as _runtime_apply_fast_path_debug_bootstrap,
        _build_fast_path_mode_directive as _runtime_build_fast_path_mode_directive,
        _build_phase8_context_suffix as _runtime_build_phase8_context_suffix,
    )
    from .state_helpers import _detect_fast_path_reason as _runtime_detect_fast_path_reason
    from .state_helpers import (
        _build_fast_path_block as _runtime_build_fast_path_block,
        _build_state_context as _runtime_build_state_context,
        _build_working_state as _runtime_build_working_state,
        _compose_state_context as _runtime_compose_state_context,
        _set_working_state_best_effort as _runtime_set_working_state_best_effort,
    )
    from .trace_helpers import (
        _apply_output_validation_observability as _runtime_apply_output_validation_observability,
        _build_llm_call_trace as _runtime_build_llm_call_trace,
        _finalize_success_debug_trace as _runtime_finalize_success_debug_trace,
        _prepare_llm_prompt_previews as _runtime_prepare_llm_prompt_previews,
        _refresh_context_and_apply_trace_snapshot as _runtime_refresh_context_and_apply_trace_snapshot,
        _strip_legacy_runtime_metadata as _runtime_strip_legacy_runtime_metadata,
        _strip_legacy_trace_fields as _runtime_strip_legacy_trace_fields,
        _truncate_preview as _runtime_truncate_preview,
        _update_session_token_metrics as _runtime_update_session_token_metrics,
    )
    from .response_utils import (
        _attach_debug_payload as _runtime_attach_debug_payload,
        _attach_success_observability as _runtime_attach_success_observability,
        _build_fast_path_success_response as _runtime_build_fast_path_success_response,
        _build_fast_success_metadata as _runtime_build_fast_success_metadata,
        _get_feedback_prompt_for_state as _runtime_get_feedback_prompt_for_state,
        _persist_turn as _runtime_persist_turn,
        _build_success_response as _runtime_build_success_response,
    )

    _runtime_apply_output_validation_policy_adapter = _build_runtime_output_validation_policy_adapter(
        force_enabled=output_validation_enabled,
    )

    if not fast_path_enabled:
        return None

    logger.info(
        "[FAST_PATH] enabled mode=%s reason=%s",
        pre_routing_result.mode,
        pre_routing_result.decision.reason,
    )
    _runtime_apply_fast_path_debug_bootstrap(
        debug_trace=debug_trace,
        query=query,
        pre_routing_result=pre_routing_result,
        detect_fast_path_reason=_runtime_detect_fast_path_reason,
        truncate_preview=_runtime_truncate_preview,
        config=config,
        pipeline_stages=pipeline_stages,
    )
    mode_directive, state_context_mode_prompt = _runtime_build_fast_path_mode_directive(
        pre_routing_result=pre_routing_result,
        informational_mode=informational_mode,
        build_mode_directive=_runtime_build_mode_directive,
    )
    conversation_context = _runtime_refresh_context_and_apply_trace_snapshot(
        memory=memory,
        conversation_context=conversation_context,
        memory_context_bundle=memory_context_bundle,
        debug_trace=debug_trace,
        diagnostics_payload=diagnostics_payload,
        route=(getattr(pre_routing_result, "route", None) if pre_routing_result else None),
    )
    fast_block = _runtime_build_fast_path_block(
        query=query,
        conversation_context=conversation_context,
        state_analysis=state_analysis,
    )
    fast_phase8_suffix = _runtime_build_phase8_context_suffix(
        informational_branch_enabled=informational_branch_enabled,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        informational_mode=informational_mode,
        build_first_turn_instruction=_runtime_build_first_turn_instruction,
        build_mixed_query_instruction=_runtime_build_mixed_query_instruction,
        build_user_correction_instruction=_runtime_build_user_correction_instruction,
        build_informational_guardrail_instruction=_runtime_build_informational_guardrail_instruction,
    )
    state_context = _runtime_compose_state_context(
        state_analysis=state_analysis,
        mode_prompt=state_context_mode_prompt,
        nervous_system_state=(diagnostics_v1.nervous_system_state if diagnostics_v1 else "window"),
        request_function=(diagnostics_v1.request_function if diagnostics_v1 else "understand"),
        contradiction_suggestion=contradiction_hint,
        cross_session_context=cross_session_context,
        phase8_context_suffix=fast_phase8_suffix,
        practice_context_suffix="",
        build_state_context=_runtime_build_state_context,
    )
    llm_result, response_generator, _prompt_stack_meta, system_prompt_override = _run_llm_generation_cycle(
        response_generator_cls=response_generator_cls,
        query=query,
        blocks=[fast_block],
        conversation_context=conversation_context,
        mode=pre_routing_result.mode,
        confidence_level=pre_routing_result.confidence_level,
        forbid=pre_routing_result.decision.forbid,
        additional_system_context=state_context,
        sd_level=sd_primary,
        config=config,
        session_store=session_store,
        session_id=user_id,
        mode_prompt_override=mode_prompt_override,
        informational_mode=informational_mode,
        route=getattr(pre_routing_result, "route", "") if pre_routing_result else "",
        diagnostics_payload=diagnostics_payload,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        prompt_stack_enabled=prompt_stack_enabled,
        prompt_registry=prompt_registry,
        mode_prompt=mode_directive.prompt,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        build_prompt_stack_override=_build_prompt_stack_override,
        prepare_llm_prompt_previews=_runtime_prepare_llm_prompt_previews,
        generate_llm_with_trace=_generate_llm_with_trace,
        build_llm_call_trace=_runtime_build_llm_call_trace,
    )
    answer = _format_and_validate_llm_answer(
        llm_result=llm_result,
        response_generator=response_generator,
        query=query,
        blocks=[fast_block],
        conversation_context=conversation_context,
        mode=pre_routing_result.mode,
        confidence_level=pre_routing_result.confidence_level,
        forbid=pre_routing_result.decision.forbid,
        additional_system_context=state_context,
        sd_level=sd_primary,
        config=config,
        session_store=session_store,
        session_id=user_id,
        mode_prompt_override=mode_prompt_override,
        informational_mode=informational_mode,
        system_prompt_override=system_prompt_override,
        route=getattr(pre_routing_result, "route", ""),
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        fallback_model_name=llm_model_name,
        include_retry_llm_trace=False,
        response_formatter_cls=response_formatter_cls,
        run_validation_retry_generation=_run_validation_retry_generation,
        apply_output_validation_policy=_runtime_apply_output_validation_policy_adapter,
        apply_output_validation_observability=_runtime_apply_output_validation_observability,
    )
    set_working_state_best_effort = _build_set_working_state_best_effort_adapter(
        set_working_state_best_effort=_runtime_set_working_state_best_effort,
        build_working_state=_runtime_build_working_state,
        logger=logger,
    )
    set_working_state_best_effort(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=pre_routing_result,
        log_prefix="[FAST_PATH] working_state update failed:",
    )
    result = _runtime_build_fast_path_success_response(
        answer=answer,
        state_analysis=state_analysis,
        pre_routing_result=pre_routing_result,
        mode_directive_reason=mode_directive.reason,
        informational_mode=informational_mode,
        mode_prompt_key=mode_prompt_key,
        conversation_context=conversation_context,
        memory_context_bundle=memory_context_bundle,
        memory_trace_metrics=memory_trace_metrics,
        query=query,
        include_feedback_prompt=include_feedback_prompt,
        memory=memory,
        schedule_summary_task=schedule_summary_task,
        user_id=user_id,
        start_time=start_time,
        llm_result=llm_result,
        debug_info=debug_info,
        debug_trace=debug_trace,
        session_store=session_store,
        pipeline_stages=pipeline_stages,
        llm_model_name=llm_model_name,
        collect_llm_session_metrics=_collect_llm_session_metrics,
        update_session_token_metrics=_runtime_update_session_token_metrics,
        persist_turn=_runtime_persist_turn,
        get_feedback_prompt_for_state=_runtime_get_feedback_prompt_for_state,
        build_success_response=_runtime_build_success_response,
        build_fast_success_metadata=_runtime_build_fast_success_metadata,
        prompt_stack_v2_enabled=prompt_stack_enabled,
        output_validation_enabled=output_validation_enabled,
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
    return {
        "result": result,
        "conversation_context": conversation_context,
    }


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
    from .response_utils import (
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
    from .response_utils import (
        _attach_debug_payload as _runtime_attach_debug_payload,
        _attach_success_observability as _runtime_attach_success_observability,
        _build_full_path_success_response as _runtime_build_full_path_success_response,
        _build_full_success_metadata as _runtime_build_full_success_metadata,
        _build_path_recommendation_if_enabled as _runtime_build_path_recommendation_if_enabled,
        _build_sources_from_blocks as _runtime_build_sources_from_blocks,
        _build_success_response as _runtime_build_success_response,
        _get_feedback_prompt_for_state as _runtime_get_feedback_prompt_for_state,
        _persist_turn as _runtime_persist_turn,
        _run_full_path_success_stage as _runtime_run_full_path_success_stage,
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
