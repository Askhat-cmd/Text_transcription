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
