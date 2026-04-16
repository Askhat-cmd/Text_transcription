"""Fast-path stage helpers extracted from runtime_misc_helpers (Wave 131)."""

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
