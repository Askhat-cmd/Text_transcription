"""Routing context helpers extracted from routing_stage_helpers (Wave 147)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


INFORMATIONAL_MODE_PROMPT = (
    "Р Р•Р–РРњ: INFORMATIONAL\n"
    "Р”Р°Р№ РїРѕР»РЅС‹Р№ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅС‹Р№ РѕС‚РІРµС‚ РїРѕ С‚РµРјРµ."
)


def _apply_fast_path_debug_bootstrap(
    *,
    debug_trace: Optional[Dict[str, Any]],
    query: str,
    pre_routing_result,
    detect_fast_path_reason,
    truncate_preview,
    config,
    pipeline_stages,
) -> None:
    if debug_trace is None:
        return

    debug_trace["fast_path"] = True
    debug_trace["fast_path_reason"] = detect_fast_path_reason(query, pre_routing_result)
    debug_trace["recommended_mode"] = pre_routing_result.mode
    debug_trace["route_track"] = getattr(pre_routing_result, "track", "direct")
    debug_trace["route_tone"] = getattr(pre_routing_result, "tone", "minimal")
    debug_trace["routing_result"] = {
        "mode": pre_routing_result.mode,
        "track": getattr(pre_routing_result, "track", "direct"),
        "tone": getattr(pre_routing_result, "tone", "minimal"),
    }
    debug_trace["decision_rule_id"] = pre_routing_result.decision.rule_id
    debug_trace["confidence_score"] = pre_routing_result.confidence_score
    debug_trace["confidence_level"] = pre_routing_result.confidence_level
    debug_trace["mode_reason"] = pre_routing_result.decision.reason
    debug_trace["block_cap"] = 0
    debug_trace["blocks_initial"] = 0
    debug_trace["blocks_after_cap"] = 0
    debug_trace["hybrid_query_preview"] = truncate_preview(query, 400)
    debug_trace["hybrid_query_len"] = len(query or "")
    debug_trace["hybrid_query_text"] = (
        query
        if bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True))
        else truncate_preview(query, 1200)
    )

    for stage_name, label in [
        ("retrieval", "Retrieval"),
        ("rerank", "Rerank"),
    ]:
        pipeline_stages.append(
            {"name": stage_name, "label": label, "duration_ms": 0, "skipped": True}
        )


def _build_state_context_mode_prompt(
    *,
    informational_mode: bool,
    fallback_prompt: str,
) -> str:
    if informational_mode:
        return INFORMATIONAL_MODE_PROMPT
    return fallback_prompt


def _build_phase8_context_suffix(
    *,
    informational_branch_enabled: bool,
    phase8_signals,
    correction_protocol_active: bool,
    informational_mode: bool,
    build_first_turn_instruction: Callable[[], str],
    build_mixed_query_instruction: Callable[[], str],
    build_user_correction_instruction: Callable[[], str],
    build_informational_guardrail_instruction: Callable[[], str],
) -> str:
    if not informational_branch_enabled:
        return ""

    parts = []
    if phase8_signals is not None and phase8_signals.first_turn:
        parts.append(build_first_turn_instruction())
    if phase8_signals is not None and phase8_signals.mixed_query:
        parts.append(build_mixed_query_instruction())
    if correction_protocol_active:
        parts.append(build_user_correction_instruction())
    if informational_mode:
        parts.append(build_informational_guardrail_instruction())

    return "\n\n".join(part for part in parts if part and part.strip())


def _build_fast_path_mode_directive(
    *,
    pre_routing_result,
    informational_mode: bool,
    build_mode_directive,
) -> Tuple[Any, str]:
    mode_directive = build_mode_directive(
        mode=pre_routing_result.mode,
        confidence_level=pre_routing_result.confidence_level,
        reason=pre_routing_result.decision.reason,
        forbid=pre_routing_result.decision.forbid,
    )
    state_context_mode_prompt = _build_state_context_mode_prompt(
        informational_mode=informational_mode,
        fallback_prompt=mode_directive.prompt,
    )
    return mode_directive, state_context_mode_prompt


def _resolve_routing_and_apply_block_cap(
    *,
    use_deterministic_router: bool,
    diagnostics_v1,
    user_stage: str,
    route_resolver,
    confidence_scorer,
    pre_routing_result,
    decision_gate,
    retrieved_blocks,
    informational_branch_enabled: bool,
    resolve_mode_prompt,
    config,
    log_retrieval_pairs,
    build_mode_directive,
    logger,
) -> Dict[str, Any]:
    route_resolution_increment = 0
    if use_deterministic_router and diagnostics_v1 is not None:
        practice_candidate_score = (
            0.75 if diagnostics_v1.request_function == "solution" else 0.0
        )
        routing_result = route_resolver.resolve(
            diagnostics=diagnostics_v1,
            safety_override=False,
            practice_candidate_score=practice_candidate_score,
            user_stage=user_stage,
        )
        route_resolution_increment = 1
        block_cap = confidence_scorer.suggest_block_cap(
            len(retrieved_blocks),
            routing_result.confidence_level,
        )
    else:
        # Non-deterministic path uses one DecisionGate result per turn.
        if pre_routing_result is None:
            raise RuntimeError("pre_routing_result is missing in non-deterministic routing flow")
        routing_result = pre_routing_result
        block_cap = decision_gate.scorer.suggest_block_cap(
            len(retrieved_blocks),
            routing_result.confidence_level,
        )

    informational_mode = (
        informational_branch_enabled
        and str(getattr(routing_result, "route", "") or "").lower() == "inform"
    )
    mode_prompt_key, mode_prompt_override = resolve_mode_prompt(
        "informational" if informational_mode else "",
        config,
    )

    stage_count_before_cap = len(retrieved_blocks)
    retrieved_blocks = retrieved_blocks[:block_cap]
    capped_retrieved_blocks = list(retrieved_blocks)
    logger.info(
        "[RETRIEVAL] confidence_cap=%s (before=%s)",
        block_cap,
        stage_count_before_cap,
    )
    log_retrieval_pairs("After confidence cap", retrieved_blocks, limit=10)

    mode_directive = build_mode_directive(
        mode=routing_result.mode,
        confidence_level=routing_result.confidence_level,
        reason=routing_result.decision.reason,
        forbid=routing_result.decision.forbid,
    )
    logger.info(
        "ROUTING nss=%s fn=%s route=%s",
        diagnostics_v1.nervous_system_state if diagnostics_v1 else "window",
        diagnostics_v1.request_function if diagnostics_v1 else "understand",
        getattr(routing_result, "route", "reflect"),
    )
    state_context_mode_prompt = _build_state_context_mode_prompt(
        informational_mode=informational_mode,
        fallback_prompt=mode_directive.prompt,
    )

    return {
        "routing_result": routing_result,
        "block_cap": block_cap,
        "route_resolution_increment": route_resolution_increment,
        "informational_mode": informational_mode,
        "mode_prompt_key": mode_prompt_key,
        "mode_prompt_override": mode_prompt_override,
        "retrieved_blocks": retrieved_blocks,
        "capped_retrieved_blocks": capped_retrieved_blocks,
        "mode_directive": mode_directive,
        "state_context_mode_prompt": state_context_mode_prompt,
    }


def _resolve_practice_selection_context(
    *,
    routing_result,
    diagnostics_v1,
    query: str,
    memory,
    practice_selector,
    practice_allowed_routes,
    practice_skip_routes,
    logger,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], str]:
    selected_practice: Optional[Dict[str, Any]] = None
    practice_alternatives: List[Dict[str, Any]] = []
    practice_context_suffix = ""

    resolved_route = str(getattr(routing_result, "route", "") or "").strip().lower()
    practice_routing_enabled = (
        resolved_route in practice_allowed_routes
        and resolved_route not in practice_skip_routes
    )

    if practice_routing_enabled:
        try:
            diagnostics_payload = diagnostics_v1.as_dict() if diagnostics_v1 else {}
            selection = practice_selector.select(
                route=resolved_route,
                nervous_system_state=str(
                    diagnostics_payload.get("nervous_system_state") or "window"
                ),
                request_function=str(
                    diagnostics_payload.get("request_function") or "understand"
                ),
                core_theme=str(diagnostics_payload.get("core_theme") or query),
                last_practice_channel=str(memory.metadata.get("last_practice_channel") or ""),
                safety_flags=[],
            )
            if selection.primary is not None:
                selected_practice = selection.primary.as_dict()
                practice_alternatives = [item.as_dict() for item in selection.alternatives]
                memory.metadata["last_practice_channel"] = selection.primary.entry.channel
                practice_context_suffix = (
                    "\n\nPRACTICE_SUGGESTION:\n"
                    f"- title: {selection.primary.entry.title}\n"
                    f"- channel: {selection.primary.entry.channel}\n"
                    f"- instruction: {selection.primary.entry.instruction}\n"
                    f"- micro_tuning: {selection.primary.entry.micro_tuning}\n"
                    f"- closure: {selection.primary.entry.closure}\n"
                    f"- time_limit_minutes: {selection.primary.entry.time_limit_minutes}"
                )
        except Exception as exc:  # pragma: no cover - guarded side-effect path
            logger.warning("[PRACTICE] selection skipped: %s", exc)
    elif resolved_route in practice_skip_routes:
        logger.info("[PRACTICE] skipped by route policy for route=%s", resolved_route)
    else:
        logger.info("[PRACTICE] skipped for route=%s", resolved_route or "unknown")

    return selected_practice, practice_alternatives, practice_context_suffix


def _attach_routing_stage_debug_trace(
    *,
    debug_trace: Optional[Dict[str, Any]],
    routing_result,
    mode_reason: str,
    block_cap: int,
    initial_retrieved_blocks,
    hybrid_query: str,
    include_full_content: bool,
    truncate_preview,
    should_run_rerank: bool,
    rerank_reason: str,
    rerank_applied: bool,
    route_resolution_count: int,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    phase8_context_suffix: str,
    correction_protocol_active: bool,
    selected_practice: Optional[Dict[str, Any]],
    practice_alternatives: List[Dict[str, Any]],
) -> None:
    if debug_trace is None:
        return

    debug_trace["recommended_mode"] = routing_result.mode
    debug_trace["route_track"] = getattr(routing_result, "track", "direct")
    debug_trace["route_tone"] = getattr(routing_result, "tone", "minimal")
    debug_trace["routing_result"] = {
        "mode": routing_result.mode,
        "track": getattr(routing_result, "track", "direct"),
        "tone": getattr(routing_result, "tone", "minimal"),
    }
    debug_trace["resolved_route"] = getattr(routing_result, "route", None)
    debug_trace["decision_rule_id"] = routing_result.decision.rule_id
    debug_trace["confidence_score"] = routing_result.confidence_score
    debug_trace["confidence_level"] = routing_result.confidence_level
    debug_trace["mode_reason"] = mode_reason
    debug_trace["block_cap"] = block_cap
    debug_trace["blocks_initial"] = len(initial_retrieved_blocks or [])
    debug_trace["hybrid_query_preview"] = truncate_preview(hybrid_query, 400)
    debug_trace["hybrid_query_len"] = len(hybrid_query or "")
    debug_trace["hybrid_query_text"] = (
        hybrid_query
        if include_full_content
        else truncate_preview(hybrid_query, 1200)
    )
    debug_trace["rerank_should_run"] = bool(should_run_rerank)
    debug_trace["rerank_reason"] = rerank_reason
    debug_trace["rerank_applied"] = bool(rerank_applied)
    debug_trace["route_resolution_count"] = route_resolution_count
    debug_trace["informational_mode"] = informational_mode
    debug_trace["applied_mode_prompt"] = mode_prompt_key if informational_mode else None
    debug_trace["phase8_context_suffix"] = phase8_context_suffix
    debug_trace["user_correction_protocol"] = correction_protocol_active
    debug_trace["selected_practice"] = selected_practice
    debug_trace["practice_alternatives"] = practice_alternatives


def _finalize_routing_context_and_trace(
    *,
    informational_branch_enabled: bool,
    phase8_signals,
    correction_protocol_active: bool,
    informational_mode: bool,
    build_first_turn_instruction: Callable[[], str],
    build_mixed_query_instruction: Callable[[], str],
    build_user_correction_instruction: Callable[[], str],
    build_informational_guardrail_instruction: Callable[[], str],
    routing_result,
    diagnostics_v1,
    query: str,
    memory,
    practice_selector,
    practice_allowed_routes,
    practice_skip_routes,
    logger,
    debug_trace: Optional[Dict[str, Any]],
    mode_reason: str,
    block_cap: int,
    initial_retrieved_blocks,
    hybrid_query: str,
    include_full_content: bool,
    truncate_preview,
    should_run_rerank: bool,
    rerank_reason: str,
    rerank_applied: bool,
    route_resolution_count: int,
    mode_prompt_key: Optional[str],
    conversation_context: str,
    memory_context_bundle,
    refresh_context_and_apply_trace_snapshot,
) -> Dict[str, Any]:
    phase8_context_suffix = _build_phase8_context_suffix(
        informational_branch_enabled=informational_branch_enabled,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        informational_mode=informational_mode,
        build_first_turn_instruction=build_first_turn_instruction,
        build_mixed_query_instruction=build_mixed_query_instruction,
        build_user_correction_instruction=build_user_correction_instruction,
        build_informational_guardrail_instruction=build_informational_guardrail_instruction,
    )

    selected_practice, practice_alternatives, practice_context_suffix = (
        _resolve_practice_selection_context(
            routing_result=routing_result,
            diagnostics_v1=diagnostics_v1,
            query=query,
            memory=memory,
            practice_selector=practice_selector,
            practice_allowed_routes=practice_allowed_routes,
            practice_skip_routes=practice_skip_routes,
            logger=logger,
        )
    )

    _attach_routing_stage_debug_trace(
        debug_trace=debug_trace,
        routing_result=routing_result,
        mode_reason=mode_reason,
        block_cap=block_cap,
        initial_retrieved_blocks=initial_retrieved_blocks,
        hybrid_query=hybrid_query,
        include_full_content=include_full_content,
        truncate_preview=truncate_preview,
        should_run_rerank=should_run_rerank,
        rerank_reason=rerank_reason,
        rerank_applied=rerank_applied,
        route_resolution_count=route_resolution_count,
        informational_mode=informational_mode,
        mode_prompt_key=mode_prompt_key,
        phase8_context_suffix=phase8_context_suffix,
        correction_protocol_active=correction_protocol_active,
        selected_practice=selected_practice,
        practice_alternatives=practice_alternatives,
    )

    updated_conversation_context = refresh_context_and_apply_trace_snapshot(
        memory=memory,
        conversation_context=conversation_context,
        memory_context_bundle=memory_context_bundle,
        debug_trace=debug_trace,
        diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
        route=getattr(routing_result, "route", None),
    )

    return {
        "phase8_context_suffix": phase8_context_suffix,
        "selected_practice": selected_practice,
        "practice_alternatives": practice_alternatives,
        "practice_context_suffix": practice_context_suffix,
        "conversation_context": updated_conversation_context,
    }
