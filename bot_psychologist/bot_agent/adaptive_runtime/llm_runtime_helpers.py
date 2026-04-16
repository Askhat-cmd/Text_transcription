"""LLM runtime helpers extracted from runtime_misc_helpers (Wave 128)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple


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
    build_llm_call_trace: Callable[..., Dict[str, Any]],
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
                build_llm_call_trace(
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
    format_answer: Callable[[str], str],
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
    retry_result["answer"] = format_answer(str(retry_result.get("answer") or ""))
    return retry_result


def _collect_llm_session_metrics(
    *,
    memory,
    llm_result: Dict[str, Any],
    fallback_model_name: str,
    update_session_token_metrics,
) -> Dict[str, Any]:
    tokens_prompt = llm_result.get("tokens_prompt") if isinstance(llm_result, dict) else None
    tokens_completion = llm_result.get("tokens_completion") if isinstance(llm_result, dict) else None
    tokens_total = llm_result.get("tokens_total") if isinstance(llm_result, dict) else None
    model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else fallback_model_name
    session_metrics = update_session_token_metrics(
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
    build_prompt_stack_override,
    prepare_llm_prompt_previews,
    generate_llm_with_trace,
    build_llm_call_trace,
) -> Tuple[Dict[str, Any], Any, Dict[str, Any], Optional[str]]:
    response_generator = response_generator_cls()

    system_prompt_override, prompt_stack_meta = build_prompt_stack_override(
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
        llm_system_preview, llm_user_preview = prepare_llm_prompt_previews(
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

    llm_result, _, _ = generate_llm_with_trace(
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
        build_llm_call_trace=build_llm_call_trace,
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
    run_validation_retry_generation,
    apply_output_validation_policy,
    apply_output_validation_observability,
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
        return run_validation_retry_generation(
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
            format_answer=lambda raw_answer: formatter.format_answer(
                raw_answer,
                mode=mode,
                confidence_level=confidence_level,
                user_message=query,
                informational_mode=informational_mode,
            ),
        )

    answer, validation_meta, validation_retry_result = apply_output_validation_policy(
        answer=answer,
        query=query,
        route=route,
        mode=mode,
        generate_retry=_retry_validation,
    )
    apply_output_validation_observability(
        validation_meta=validation_meta,
        validation_retry_result=validation_retry_result,
        llm_result=llm_result,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        fallback_model_name=fallback_model_name,
        include_retry_llm_trace=include_retry_llm_trace,
    )
    return answer
