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

