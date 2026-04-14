"""Routing-stage helpers extracted from answer_adaptive orchestration."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _compute_diagnostics_v1(
    *,
    query: str,
    state_analysis,
    informational_mode_hint: bool,
    phase8_signals,
    informational_branch_enabled: bool,
    use_new_diagnostics_v1: bool,
    use_deterministic_router: bool,
    diagnostics_classifier,
    debug_trace: Optional[Dict[str, Any]] = None,
    debug_info: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Any], bool]:
    diagnostics_v1 = None
    correction_protocol_active = False

    if use_new_diagnostics_v1:
        diagnostics_v1 = diagnostics_classifier.classify(
            query=query,
            state_analysis=state_analysis,
            informational_mode_hint=informational_mode_hint,
        )
        correction_protocol_active = bool(
            informational_branch_enabled
            and phase8_signals is not None
            and phase8_signals.user_correction
        )
        if correction_protocol_active:
            recalibrated = diagnostics_v1.as_dict()
            confidence = dict(recalibrated.get("confidence") or {})
            confidence["interaction_mode"] = min(
                float(confidence.get("interaction_mode", 0.6) or 0.6),
                0.6,
            )
            confidence["request_function"] = min(
                float(confidence.get("request_function", 0.6) or 0.6),
                0.6,
            )
            recalibrated["confidence"] = confidence
            recalibrated["request_function"] = "validation"
            diagnostics_v1 = diagnostics_classifier.sanitize(recalibrated)
        if debug_trace is not None:
            debug_trace["diagnostics_v1"] = diagnostics_v1.as_dict()
            debug_trace["route_strategy"] = (
                "deterministic_v1" if use_deterministic_router else "decision_gate_v0"
            )
            debug_trace["user_correction_protocol"] = correction_protocol_active
        if debug_info is not None:
            debug_info["diagnostics_v1"] = diagnostics_v1.as_dict()

    return diagnostics_v1, correction_protocol_active


def _build_contradiction_payload(
    *,
    query: str,
    detect_contradiction_fn,
    debug_trace: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], str]:
    contradiction_info = detect_contradiction_fn(query)
    contradiction_hint = (
        str(contradiction_info.get("suggestion", ""))
        if contradiction_info.get("has_contradiction")
        else ""
    )
    if debug_trace is not None:
        debug_trace["contradiction"] = contradiction_info
    return contradiction_info, contradiction_hint


def _resolve_pre_routing(
    *,
    use_deterministic_router: bool,
    query: str,
    state_analysis,
    memory,
    user_stage: str,
    informational_mode: bool,
    contradiction_info: Dict[str, Any],
    contradiction_hint: str,
    decision_gate_cls,
    detect_routing_signals_fn,
    should_use_fast_path_fn,
    logger,
) -> Tuple[Optional[Any], Optional[Any], bool]:
    decision_gate = None if use_deterministic_router else decision_gate_cls()
    pre_routing_result = None

    if use_deterministic_router:
        fast_path_enabled = False
        logger.info("[ROUTING_V1] deterministic resolver enabled; FAST_PATH disabled")
    else:
        pre_routing_signals = detect_routing_signals_fn(query, [], state_analysis, memory=memory)
        pre_routing_signals["contradiction_detected"] = bool(
            contradiction_info.get("has_contradiction", False)
        )
        pre_routing_signals["contradiction_suggestion"] = contradiction_hint
        pre_routing_result = decision_gate.route(pre_routing_signals, user_stage=user_stage)
        fast_path_enabled = should_use_fast_path_fn(query, pre_routing_result)
        if informational_mode and fast_path_enabled:
            fast_path_enabled = False
            logger.info(
                "[FAST_PATH] disabled for informational route (user_state=%s)",
                state_analysis.primary_state.value,
            )
        logger.info(
            "[CONFIDENCE] score=%.4f level=%s -> FAST_PATH: %s",
            pre_routing_result.confidence_score,
            pre_routing_result.confidence_level,
            "yes" if fast_path_enabled else "no",
        )

    return decision_gate, pre_routing_result, fast_path_enabled


def _apply_fast_path_debug_bootstrap(
    *,
    debug_trace: Optional[Dict[str, Any]],
    query: str,
    pre_routing_result,
    detect_fast_path_reason_fn,
    truncate_preview_fn,
    config,
    pipeline_stages,
) -> None:
    if debug_trace is None:
        return

    debug_trace["fast_path"] = True
    debug_trace["fast_path_reason"] = detect_fast_path_reason_fn(query, pre_routing_result)
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
    debug_trace["hybrid_query_preview"] = truncate_preview_fn(query, 400)
    debug_trace["hybrid_query_len"] = len(query or "")
    debug_trace["hybrid_query_text"] = (
        query
        if bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True))
        else truncate_preview_fn(query, 1200)
    )

    for stage_name, label in [
        ("retrieval", "Retrieval"),
        ("rerank", "Rerank"),
    ]:
        pipeline_stages.append(
            {"name": stage_name, "label": label, "duration_ms": 0, "skipped": True}
        )


def _build_fast_path_mode_directive(
    *,
    pre_routing_result,
    informational_mode: bool,
    build_mode_directive_fn,
) -> Tuple[Any, str]:
    mode_directive = build_mode_directive_fn(
        mode=pre_routing_result.mode,
        confidence_level=pre_routing_result.confidence_level,
        reason=pre_routing_result.decision.reason,
        forbid=pre_routing_result.decision.forbid,
    )
    state_context_mode_prompt = (
        "РЕЖИМ: INFORMATIONAL\nДай полный структурированный ответ по теме."
        if informational_mode
        else mode_directive.prompt
    )
    return mode_directive, state_context_mode_prompt
