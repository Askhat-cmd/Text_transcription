"""Runtime misc helpers extracted from answer_adaptive (Wave 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..onboarding_flow import build_start_message
from .state_helpers import _fallback_state_analysis


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


def _sd_runtime_disabled() -> bool:
    """SD-runtime is intentionally disabled in active Neo runtime."""
    return True


def _build_start_command_response(
    *,
    user_id: str,
    user_level: str,
    query: str,
    memory,
    start_time: datetime,
    schedule_summary_task: bool = True,
    logger=None,
) -> Dict[str, Any]:
    fallback_state = _fallback_state_analysis()
    answer = build_start_message()
    try:
        memory.add_turn(
            user_input=query,
            bot_response=answer,
            user_state=fallback_state.primary_state.value,
            blocks_used=0,
            concepts=[],
            schedule_summary_task=schedule_summary_task,
        )
    except Exception as exc:
        # Keep behavior non-fatal: onboarding answer should still be returned.
        if logger is not None:
            logger.warning("[ONBOARDING] failed to persist /start turn: %s", exc)

    elapsed_time = (datetime.now() - start_time).total_seconds()
    return {
        "status": "success",
        "answer": answer,
        "state_analysis": {
            "primary_state": fallback_state.primary_state.value,
            "confidence": fallback_state.confidence,
            "secondary_states": [s.value for s in fallback_state.secondary_states],
            "emotional_tone": fallback_state.emotional_tone,
            "depth": fallback_state.depth,
            "recommendations": fallback_state.recommendations,
        },
        "path_recommendation": None,
        "conversation_context": "",
        "feedback_prompt": "",
        "sources": [],
        "concepts": [],
        "metadata": {
            "user_id": user_id,
            "onboarding_start_command": True,
            "first_turn": True,
            "resolved_route": "contact_hold",
            "recommended_mode": "PRESENCE",
            "route_resolution_count": 1,
            "informational_mode": False,
            "applied_mode_prompt": None,
        },
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": round(elapsed_time, 2),
    }


def _load_runtime_memory_context(
    *,
    user_id: str,
    query: str,
    data_loader,
    get_conversation_memory_fn,
    memory_updater,
    config,
) -> Dict[str, Any]:
    # Local import to avoid widening module-level coupling.
    from .trace_helpers import _get_memory_trace_metrics

    data_loader.load_all_data()
    memory = get_conversation_memory_fn(user_id)
    memory_update = memory_updater.build_runtime_context(
        memory=memory,
        diagnostics=None,
        route=None,
        max_context_chars=int(getattr(config, "MAX_CONTEXT_SIZE", 2200) or 2200),
    )
    memory_context_bundle = memory_update.context
    conversation_context = (
        memory_context_bundle.context_text
        or memory.get_adaptive_context_text(query)
    )

    cross_session_context = ""
    if hasattr(memory, "load_cross_session_context"):
        cross_session_context = memory.load_cross_session_context(
            getattr(memory, "owner_user_id", user_id),
            limit=3,
        )

    context_turns = len(memory.turns)
    memory_trace_metrics = _get_memory_trace_metrics(memory, context_turns)
    if memory_context_bundle is not None:
        memory_trace_metrics["summary_used"] = bool(memory_context_bundle.summary_used)

    return {
        "memory": memory,
        "memory_context_bundle": memory_context_bundle,
        "conversation_context": conversation_context,
        "cross_session_context": cross_session_context,
        "context_turns": context_turns,
        "memory_trace_metrics": memory_trace_metrics,
    }


def _run_bootstrap_and_onboarding_guard(
    *,
    user_id: str,
    user_level: str,
    query: str,
    start_time: datetime,
    schedule_summary_task: bool,
    debug_trace: Optional[Dict[str, Any]],
    debug_info: Optional[Dict[str, Any]],
    load_runtime_memory_context_fn,
    data_loader,
    get_conversation_memory_fn,
    memory_updater,
    config,
    detect_phase8_signals_fn,
    informational_branch_enabled: bool,
    build_start_command_response_fn,
    truncate_preview_fn,
    apply_memory_debug_info_fn,
    resolve_path_user_level_fn,
) -> Dict[str, Any]:
    stage1 = load_runtime_memory_context_fn(
        user_id=user_id,
        query=query,
        data_loader=data_loader,
        get_conversation_memory_fn=get_conversation_memory_fn,
        memory_updater=memory_updater,
        config=config,
    )
    memory = stage1["memory"]
    memory_context_bundle = stage1["memory_context_bundle"]
    conversation_context = stage1["conversation_context"]
    cross_session_context = stage1["cross_session_context"]
    context_turns = stage1["context_turns"]
    memory_trace_metrics = stage1["memory_trace_metrics"]
    if memory_context_bundle is not None:
        memory_trace_metrics["summary_staleness"] = memory_context_bundle.staleness
        memory_trace_metrics["memory_strategy"] = memory_context_bundle.strategy

    if debug_trace is not None:
        debug_trace["turn_number"] = len(memory.turns) + 1
        debug_trace["cross_session_context"] = truncate_preview_fn(cross_session_context, 500)
        debug_trace["memory_strategy"] = (
            memory_context_bundle.strategy if memory_context_bundle else None
        )
        debug_trace["summary_staleness"] = (
            memory_context_bundle.staleness if memory_context_bundle else None
        )
        apply_memory_debug_info_fn(debug_trace, memory, memory_trace_metrics)

    phase8_signals = detect_phase8_signals_fn(query=query, turns_count=len(memory.turns))
    if debug_trace is not None:
        debug_trace["phase8_signals"] = phase8_signals.as_dict()

    start_command_response = None
    if informational_branch_enabled and phase8_signals.start_command:
        start_command_response = build_start_command_response_fn(
            user_id=user_id,
            user_level=user_level,
            query=query,
            memory=memory,
            start_time=start_time,
            schedule_summary_task=schedule_summary_task,
        )

    path_level_enum = resolve_path_user_level_fn(user_level)
    if debug_info is not None:
        debug_info["user_id"] = user_id
        debug_info["memory_turns"] = len(memory.turns)

    return {
        "memory": memory,
        "memory_context_bundle": memory_context_bundle,
        "conversation_context": conversation_context,
        "cross_session_context": cross_session_context,
        "context_turns": context_turns,
        "memory_trace_metrics": memory_trace_metrics,
        "phase8_signals": phase8_signals,
        "path_level_enum": path_level_enum,
        "start_command_response": start_command_response,
    }


def _generate_llm_with_trace(
    *,
    response_generator,
    query: str,
    blocks: List[Any],
    conversation_context: str,
    mode: str,
    confidence_level: str,
    forbid: List[str],
    additional_system_context: str,
    sd_level: str,
    config,
    session_store,
    session_id: str,
    mode_prompt_override: Optional[str],
    informational_mode: bool,
    system_prompt_override: Optional[str],
    debug_trace: Optional[Dict[str, Any]],
    pipeline_stages: List[Dict[str, Any]],
    llm_system_preview: str,
    llm_user_preview: str,
    system_blob_id: Optional[str],
    user_blob_id: Optional[str],
    build_llm_call_trace_fn: Callable[..., Dict[str, Any]],
) -> Tuple[Dict[str, Any], Optional[str], int]:
    llm_started = datetime.now()
    llm_result: Dict[str, Any] = {}
    llm_error: Optional[str] = None
    duration_ms = 0

    try:
        llm_result = response_generator.generate(
            query,
            blocks,
            conversation_context=conversation_context,
            mode=mode,
            confidence_level=confidence_level,
            forbid=forbid,
            additional_system_context=additional_system_context,
            sd_level=sd_level,
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.get_mode_max_tokens(mode),
            system_prompt_blob_id=system_blob_id,
            user_prompt_blob_id=user_blob_id,
            session_store=session_store,
            session_id=session_id,
            mode_prompt_override=mode_prompt_override,
            mode_overrides_sd=informational_mode,
            system_prompt_override=system_prompt_override,
        )
    except Exception as llm_exc:
        llm_error = str(llm_exc)
        raise
    finally:
        duration_ms = int((datetime.now() - llm_started).total_seconds() * 1000)
        if debug_trace is not None:
            call_info = (
                llm_result.get("llm_call_info")
                if isinstance(llm_result, dict) and isinstance(llm_result.get("llm_call_info"), dict)
                else {}
            )
            debug_trace["system_prompt_blob_id"] = call_info.get("system_prompt_blob_id")
            debug_trace["user_prompt_blob_id"] = call_info.get("user_prompt_blob_id")
            pipeline_stages.append(
                {
                    "name": "llm",
                    "label": "LLM",
                    "duration_ms": duration_ms,
                    "skipped": False,
                }
            )
            debug_trace.setdefault("llm_calls", []).append(
                build_llm_call_trace_fn(
                    llm_result=llm_result if isinstance(llm_result, dict) else {},
                    step="answer",
                    system_prompt_preview=llm_system_preview,
                    user_prompt_preview=llm_user_preview,
                    fallback_error=llm_error,
                    duration_ms=duration_ms,
                    system_prompt_blob_id=system_blob_id,
                    user_prompt_blob_id=user_blob_id,
                )
            )

    return llm_result, llm_error, duration_ms


def _run_validation_retry_generation(
    *,
    response_generator,
    query: str,
    hint: str,
    blocks: List[Any],
    conversation_context: str,
    mode: str,
    confidence_level: str,
    forbid: List[str],
    additional_system_context: str,
    sd_level: str,
    config,
    session_store,
    session_id: str,
    mode_prompt_override: Optional[str],
    informational_mode: bool,
    system_prompt_override: Optional[str],
    format_answer_fn: Callable[[str], str],
) -> Dict[str, Any]:
    retry_query = f"{query}\n\n[VALIDATION_HINT]\n{hint}"
    retry_result = response_generator.generate(
        retry_query,
        blocks,
        conversation_context=conversation_context,
        mode=mode,
        confidence_level=confidence_level,
        forbid=forbid,
        additional_system_context=additional_system_context,
        sd_level=sd_level,
        model=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.get_mode_max_tokens(mode),
        session_store=session_store,
        session_id=session_id,
        mode_prompt_override=mode_prompt_override,
        mode_overrides_sd=informational_mode,
        system_prompt_override=system_prompt_override,
    )
    retry_result["answer"] = format_answer_fn(str(retry_result.get("answer") or ""))
    return retry_result


def _collect_llm_session_metrics(
    *,
    memory,
    llm_result: Dict[str, Any],
    fallback_model_name: str,
    update_session_token_metrics_fn,
) -> Dict[str, Any]:
    tokens_prompt = llm_result.get("tokens_prompt") if isinstance(llm_result, dict) else None
    tokens_completion = llm_result.get("tokens_completion") if isinstance(llm_result, dict) else None
    tokens_total = llm_result.get("tokens_total") if isinstance(llm_result, dict) else None
    model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else fallback_model_name
    session_metrics = update_session_token_metrics_fn(
        memory=memory,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        tokens_total=tokens_total,
        model_name=str(model_used),
    )
    return {
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "model_used": model_used,
        "session_metrics": session_metrics,
    }


def _build_prompt_stack_override(
    *,
    enabled: bool,
    prompt_registry,
    query: str,
    blocks: List[Any],
    conversation_context: str,
    additional_system_context: str,
    route: str,
    mode: str,
    diagnostics_payload: Optional[Dict[str, Any]],
    mode_prompt_override: Optional[str],
    phase8_signals,
    correction_protocol_active: bool,
) -> Tuple[Optional[str], Dict[str, Any]]:
    prompt_stack_meta: Dict[str, Any] = {"enabled": False}
    system_prompt_override: Optional[str] = None
    if not enabled:
        return system_prompt_override, prompt_stack_meta

    prompt_build = prompt_registry.build(
        query=query,
        blocks=blocks,
        conversation_context=conversation_context,
        additional_system_context=additional_system_context,
        route=route,
        mode=mode,
        diagnostics=diagnostics_payload,
        mode_prompt_override=mode_prompt_override,
        first_turn=bool(phase8_signals.first_turn) if phase8_signals else False,
        mixed_query_bridge=bool(phase8_signals.mixed_query) if phase8_signals else False,
        user_correction_protocol=bool(correction_protocol_active),
    )
    system_prompt_override = prompt_build.system_prompt
    prompt_stack_meta = {"enabled": True, **prompt_build.as_dict()}
    return system_prompt_override, prompt_stack_meta


def _run_llm_generation_cycle(
    *,
    response_generator_cls,
    query: str,
    blocks: List[Any],
    conversation_context: str,
    mode: str,
    confidence_level: str,
    forbid: List[str],
    additional_system_context: str,
    sd_level: str,
    config,
    session_store,
    session_id: str,
    mode_prompt: str,
    mode_prompt_override: Optional[str],
    informational_mode: bool,
    route: str,
    diagnostics_payload: Optional[Dict[str, Any]],
    phase8_signals,
    correction_protocol_active: bool,
    prompt_stack_enabled: bool,
    prompt_registry,
    debug_trace: Optional[Dict[str, Any]],
    pipeline_stages: List[Dict[str, Any]],
    build_prompt_stack_override_fn,
    prepare_llm_prompt_previews_fn,
    generate_llm_with_trace_fn,
    build_llm_call_trace_fn,
) -> Tuple[Dict[str, Any], Any, Dict[str, Any], Optional[str]]:
    response_generator = response_generator_cls()

    system_prompt_override, prompt_stack_meta = build_prompt_stack_override_fn(
        enabled=prompt_stack_enabled,
        prompt_registry=prompt_registry,
        query=query,
        blocks=blocks,
        conversation_context=conversation_context,
        additional_system_context=additional_system_context,
        route=route,
        mode=mode,
        diagnostics_payload=diagnostics_payload,
        mode_prompt_override=mode_prompt_override if informational_mode else None,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
    )

    llm_system_preview = ""
    llm_user_preview = ""
    system_blob_id = None
    user_blob_id = None
    if debug_trace is not None:
        llm_system_preview, llm_user_preview = prepare_llm_prompt_previews_fn(
            response_generator=response_generator,
            query=query,
            blocks=blocks,
            conversation_context=conversation_context,
            sd_level=sd_level,
            mode_prompt=mode_prompt,
            additional_system_context=additional_system_context,
            mode_prompt_override=mode_prompt_override,
            mode_overrides_sd=informational_mode,
            system_prompt_override=system_prompt_override,
        )
        debug_trace["prompt_stack_v2"] = prompt_stack_meta

    llm_result, _, _ = generate_llm_with_trace_fn(
        response_generator=response_generator,
        query=query,
        blocks=blocks,
        conversation_context=conversation_context,
        mode=mode,
        confidence_level=confidence_level,
        forbid=forbid,
        additional_system_context=additional_system_context,
        sd_level=sd_level,
        config=config,
        session_store=session_store,
        session_id=session_id,
        mode_prompt_override=mode_prompt_override,
        informational_mode=informational_mode,
        system_prompt_override=system_prompt_override,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        llm_system_preview=llm_system_preview,
        llm_user_preview=llm_user_preview,
        system_blob_id=system_blob_id,
        user_blob_id=user_blob_id,
        build_llm_call_trace_fn=build_llm_call_trace_fn,
    )

    return llm_result, response_generator, prompt_stack_meta, system_prompt_override


def _format_and_validate_llm_answer(
    *,
    llm_result: Dict[str, Any],
    response_generator,
    query: str,
    blocks: List[Any],
    conversation_context: str,
    mode: str,
    confidence_level: str,
    forbid: List[str],
    additional_system_context: str,
    sd_level: str,
    config,
    session_store,
    session_id: str,
    mode_prompt_override: Optional[str],
    informational_mode: bool,
    system_prompt_override: Optional[str],
    route: str,
    debug_trace: Optional[Dict[str, Any]],
    pipeline_stages: List[Dict[str, Any]],
    fallback_model_name: str,
    include_retry_llm_trace: bool,
    response_formatter_cls,
    run_validation_retry_generation_fn,
    apply_output_validation_policy_fn,
    apply_output_validation_observability_fn,
) -> str:
    answer = llm_result.get("answer", "")
    formatter = response_formatter_cls()
    answer = formatter.format_answer(
        answer,
        mode=mode,
        confidence_level=confidence_level,
        user_message=query,
        informational_mode=informational_mode,
    )

    def _retry_validation(hint: str) -> Dict[str, Any]:
        return run_validation_retry_generation_fn(
            response_generator=response_generator,
            query=query,
            hint=hint,
            blocks=blocks,
            conversation_context=conversation_context,
            mode=mode,
            confidence_level=confidence_level,
            forbid=forbid,
            additional_system_context=additional_system_context,
            sd_level=sd_level,
            config=config,
            session_store=session_store,
            session_id=session_id,
            mode_prompt_override=mode_prompt_override,
            informational_mode=informational_mode,
            system_prompt_override=system_prompt_override,
            format_answer_fn=lambda raw_answer: formatter.format_answer(
                raw_answer,
                mode=mode,
                confidence_level=confidence_level,
                user_message=query,
                informational_mode=informational_mode,
            ),
        )

    answer, validation_meta, validation_retry_result = apply_output_validation_policy_fn(
        answer=answer,
        query=query,
        route=route,
        mode=mode,
        generate_retry_fn=_retry_validation,
    )
    apply_output_validation_observability_fn(
        validation_meta=validation_meta,
        validation_retry_result=validation_retry_result,
        llm_result=llm_result,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        fallback_model_name=fallback_model_name,
        include_retry_llm_trace=include_retry_llm_trace,
    )
    return answer


def _execute_full_path_llm_stage(
    *,
    run_generation_fn,
    format_answer_fn,
    handle_llm_error_fn,
    logger,
) -> Dict[str, Any]:
    llm_result, response_generator, _prompt_stack_meta, system_prompt_override = run_generation_fn()

    if llm_result.get("error") and llm_result["error"] not in ["no_blocks"]:
        logger.error("[ADAPTIVE] LLM error: %s", llm_result["error"])
        response = handle_llm_error_fn(str(llm_result.get("error", "")))
        return {
            "error_response": response,
            "llm_result": llm_result,
            "answer": "",
            "response_generator": response_generator,
            "system_prompt_override": system_prompt_override,
        }

    answer = format_answer_fn(
        llm_result=llm_result,
        response_generator=response_generator,
        system_prompt_override=system_prompt_override,
    )

    return {
        "error_response": None,
        "llm_result": llm_result,
        "answer": answer,
        "response_generator": response_generator,
        "system_prompt_override": system_prompt_override,
    }


def _run_fast_path_stage(
    *,
    fast_path_enabled: bool,
    logger,
    pre_routing_result,
    debug_trace: Optional[Dict[str, Any]],
    query: str,
    truncate_preview_fn,
    config,
    pipeline_stages: List[Dict[str, Any]],
    informational_mode: bool,
    memory,
    conversation_context: str,
    memory_context_bundle,
    diagnostics_payload: Optional[Dict[str, Any]],
    refresh_context_and_apply_trace_snapshot_fn,
    build_fast_path_block_fn,
    phase8_signals,
    correction_protocol_active: bool,
    informational_branch_enabled: bool,
    state_analysis,
    contradiction_hint: str,
    cross_session_context: str,
    compose_state_context_fn,
    build_state_context_fn,
    diagnostics_v1,
    response_generator_cls,
    sd_primary: str,
    session_store,
    user_id: str,
    mode_prompt_override: Optional[str],
    prompt_stack_enabled: bool,
    prompt_registry,
    response_formatter_cls,
    apply_output_validation_policy_fn,
    set_working_state_best_effort_fn,
    include_feedback_prompt: bool,
    mode_prompt_key: Optional[str],
    memory_trace_metrics: Dict[str, Any],
    schedule_summary_task: bool,
    start_time: datetime,
    debug_info: Optional[Dict[str, Any]],
    llm_model_name: str,
    collect_llm_session_metrics_fn,
    update_session_token_metrics_fn,
    persist_turn_fn,
    get_feedback_prompt_for_state_fn,
    output_validation_enabled: bool,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
) -> Optional[Dict[str, Any]]:
    from ..decision import build_mode_directive as _runtime_build_mode_directive
    from ..onboarding_flow import (
        build_first_turn_instruction as _runtime_build_first_turn_instruction,
        build_informational_guardrail_instruction as _runtime_build_informational_guardrail_instruction,
        build_mixed_query_instruction as _runtime_build_mixed_query_instruction,
        build_user_correction_instruction as _runtime_build_user_correction_instruction,
    )
    from .routing_stage_helpers import (
        _apply_fast_path_debug_bootstrap as _runtime_apply_fast_path_debug_bootstrap,
        _build_fast_path_mode_directive as _runtime_build_fast_path_mode_directive,
        _build_phase8_context_suffix as _runtime_build_phase8_context_suffix,
    )
    from .state_helpers import _detect_fast_path_reason as _runtime_detect_fast_path_reason
    from .trace_helpers import (
        _apply_output_validation_observability as _runtime_apply_output_validation_observability,
        _build_llm_call_trace as _runtime_build_llm_call_trace,
        _finalize_success_debug_trace as _runtime_finalize_success_debug_trace,
        _prepare_llm_prompt_previews as _runtime_prepare_llm_prompt_previews,
        _strip_legacy_runtime_metadata as _runtime_strip_legacy_runtime_metadata,
        _strip_legacy_trace_fields as _runtime_strip_legacy_trace_fields,
    )
    from .response_utils import (
        _attach_debug_payload as _runtime_attach_debug_payload,
        _attach_success_observability as _runtime_attach_success_observability,
        _build_fast_path_success_response as _runtime_build_fast_path_success_response,
        _build_fast_success_metadata as _runtime_build_fast_success_metadata,
        _build_success_response as _runtime_build_success_response,
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
        detect_fast_path_reason_fn=_runtime_detect_fast_path_reason,
        truncate_preview_fn=truncate_preview_fn,
        config=config,
        pipeline_stages=pipeline_stages,
    )
    mode_directive, state_context_mode_prompt = _runtime_build_fast_path_mode_directive(
        pre_routing_result=pre_routing_result,
        informational_mode=informational_mode,
        build_mode_directive_fn=_runtime_build_mode_directive,
    )
    conversation_context = refresh_context_and_apply_trace_snapshot_fn(
        memory=memory,
        conversation_context=conversation_context,
        memory_context_bundle=memory_context_bundle,
        debug_trace=debug_trace,
        diagnostics_payload=diagnostics_payload,
        route=(getattr(pre_routing_result, "route", None) if pre_routing_result else None),
    )
    fast_block = build_fast_path_block_fn(
        query=query,
        conversation_context=conversation_context,
        state_analysis=state_analysis,
    )
    fast_phase8_suffix = _runtime_build_phase8_context_suffix(
        informational_branch_enabled=informational_branch_enabled,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        informational_mode=informational_mode,
        build_first_turn_instruction_fn=_runtime_build_first_turn_instruction,
        build_mixed_query_instruction_fn=_runtime_build_mixed_query_instruction,
        build_user_correction_instruction_fn=_runtime_build_user_correction_instruction,
        build_informational_guardrail_instruction_fn=_runtime_build_informational_guardrail_instruction,
    )
    state_context = compose_state_context_fn(
        state_analysis=state_analysis,
        mode_prompt=state_context_mode_prompt,
        nervous_system_state=(diagnostics_v1.nervous_system_state if diagnostics_v1 else "window"),
        request_function=(diagnostics_v1.request_function if diagnostics_v1 else "understand"),
        contradiction_suggestion=contradiction_hint,
        cross_session_context=cross_session_context,
        phase8_context_suffix=fast_phase8_suffix,
        practice_context_suffix="",
        build_state_context_fn=build_state_context_fn,
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
        build_prompt_stack_override_fn=_build_prompt_stack_override,
        prepare_llm_prompt_previews_fn=_runtime_prepare_llm_prompt_previews,
        generate_llm_with_trace_fn=_generate_llm_with_trace,
        build_llm_call_trace_fn=_runtime_build_llm_call_trace,
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
        run_validation_retry_generation_fn=_run_validation_retry_generation,
        apply_output_validation_policy_fn=apply_output_validation_policy_fn,
        apply_output_validation_observability_fn=_runtime_apply_output_validation_observability,
    )
    set_working_state_best_effort_fn(
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
        collect_llm_session_metrics_fn=collect_llm_session_metrics_fn,
        update_session_token_metrics_fn=update_session_token_metrics_fn,
        persist_turn_fn=persist_turn_fn,
        get_feedback_prompt_for_state_fn=get_feedback_prompt_for_state_fn,
        build_success_response_fn=_runtime_build_success_response,
        build_fast_success_metadata_fn=_runtime_build_fast_success_metadata,
        prompt_stack_v2_enabled=prompt_stack_enabled,
        output_validation_enabled=output_validation_enabled,
        attach_success_observability_fn=_runtime_attach_success_observability,
        strip_legacy_runtime_metadata_fn=_runtime_strip_legacy_runtime_metadata,
        attach_debug_payload_fn=_runtime_attach_debug_payload,
        finalize_success_debug_trace_fn=_runtime_finalize_success_debug_trace,
        estimate_cost_fn=estimate_cost_fn,
        compute_anomalies_fn=compute_anomalies_fn,
        attach_trace_schema_fn=attach_trace_schema_fn,
        build_state_trajectory_fn=build_state_trajectory_fn,
        store_blob_fn=store_blob_fn,
        strip_legacy_trace_fields_fn=_runtime_strip_legacy_trace_fields,
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
    apply_output_validation_policy_fn,
    state_analysis,
    start_time: datetime,
    memory,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    finalize_failure_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
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
        build_prompt_stack_override_fn=_build_prompt_stack_override,
        prepare_llm_prompt_previews_fn=_runtime_prepare_llm_prompt_previews,
        generate_llm_with_trace_fn=_generate_llm_with_trace,
        build_llm_call_trace_fn=_runtime_build_llm_call_trace,
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
            finalize_failure_debug_trace_fn=finalize_failure_debug_trace_fn,
            estimate_cost_fn=estimate_cost_fn,
            compute_anomalies_fn=compute_anomalies_fn,
            attach_trace_schema_fn=attach_trace_schema_fn,
            build_state_trajectory_fn=build_state_trajectory_fn,
            store_blob_fn=store_blob_fn,
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
        run_validation_retry_generation_fn=_run_validation_retry_generation,
        apply_output_validation_policy_fn=apply_output_validation_policy_fn,
        apply_output_validation_observability_fn=_runtime_apply_output_validation_observability,
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
    build_state_context_fn,
    compose_state_context_fn,
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
    apply_output_validation_policy_fn,
    start_time: datetime,
    memory,
    schedule_summary_task: bool,
    debug_info,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    finalize_failure_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
    llm_model_name: str,
    logger,
    include_path_recommendation: bool,
    include_feedback_prompt: bool,
    user_level_enum,
    fallback_model_name: str,
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
    mode_prompt_key: Optional[str],
    route_resolution_count: int,
    selected_practice,
    practice_alternatives,
    block_cap: int,
    output_validation_enabled: bool,
    memory_context_bundle,
    memory_trace_metrics,
    hybrid_query: str,
    build_sources_from_blocks_fn,
    log_blocks_fn,
    build_success_response_fn,
    build_full_success_metadata_fn,
    attach_success_observability_fn,
    strip_legacy_runtime_metadata_fn,
    attach_debug_payload_fn,
    finalize_success_debug_trace_fn,
    strip_legacy_trace_fields_fn,
    contradiction_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from .response_utils import _run_full_path_success_stage as _runtime_run_full_path_success_stage

    logger.debug("🤖 Этап 4: Генерация ответа...")

    state_context = compose_state_context_fn(
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
        build_state_context_fn=build_state_context_fn,
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
        apply_output_validation_policy_fn=apply_output_validation_policy_fn,
        state_analysis=state_analysis,
        start_time=start_time,
        memory=memory,
        schedule_summary_task=schedule_summary_task,
        debug_info=debug_info,
        initial_retrieved_blocks=initial_retrieved_blocks,
        reranked_blocks_for_trace=reranked_blocks_for_trace,
        finalize_failure_debug_trace_fn=finalize_failure_debug_trace_fn,
        estimate_cost_fn=estimate_cost_fn,
        compute_anomalies_fn=compute_anomalies_fn,
        attach_trace_schema_fn=attach_trace_schema_fn,
        build_state_trajectory_fn=build_state_trajectory_fn,
        store_blob_fn=store_blob_fn,
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
        build_full_path_success_response_fn=build_full_path_success_response_fn,
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
    )

    return {"current_stage": "success", "result": result}
