"""Routing pre-stage helpers extracted from routing_stage_helpers (Wave 147)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _run_state_analysis_stage(
    *,
    query: str,
    memory,
    config,
    phase8_signals,
    debug_trace: Optional[Dict[str, Any]],
    debug_info: Optional[Dict[str, Any]],
    pipeline_stages: List[Dict[str, Any]],
    state_classifier,
    classify_parallel,
    logger,
) -> Dict[str, Any]:
    from ..decision import resolve_user_stage as _runtime_resolve_user_stage
    from .mode_policy_helpers import (
        _derive_informational_mode_hint as _runtime_derive_informational_mode_hint,
        resolve_mode_prompt as _runtime_resolve_mode_prompt,
    )
    from .pipeline_utils import (
        _run_coroutine_sync as _runtime_run_coroutine_sync,
        _timed as _runtime_timed,
    )
    from .state_helpers import (
        _fallback_sd_result as _runtime_fallback_sd_result,
        _fallback_state_analysis as _runtime_fallback_state_analysis,
    )

    conversation_history = [
        {"role": "user", "content": turn.user_input}
        for turn in memory.get_last_turns(config.CONVERSATION_HISTORY_DEPTH)
    ]

    if debug_trace is not None:
        try:
            state_analysis, stage = _runtime_timed(
                "state_classifier",
                "Р С™Р В»Р В°РЎРѓРЎРѓР С‘РЎвЂћР С‘Р С”Р В°РЎвЂљР С•РЎР‚ РЎРѓР С•РЎРѓРЎвЂљР С•РЎРЏР Р…Р С‘РЎРЏ",
                _runtime_run_coroutine_sync,
                state_classifier.classify(
                    query,
                    conversation_history=conversation_history,
                ),
            )
            pipeline_stages.append(stage)
        except Exception as exc:
            logger.warning(
                "[CLASSIFY] StateClassifier failed: %s. Using fallback.",
                exc,
            )
            state_analysis = _runtime_fallback_state_analysis()
            pipeline_stages.append(
                {
                    "name": "state_classifier",
                    "label": "Р С™Р В»Р В°РЎРѓРЎРѓР С‘РЎвЂћР С‘Р С”Р В°РЎвЂљР С•РЎР‚ РЎРѓР С•РЎРѓРЎвЂљР С•РЎРЏР Р…Р С‘РЎРЏ",
                    "duration_ms": 0,
                    "skipped": False,
                }
            )
        sd_result = _runtime_fallback_sd_result("disabled_by_design")
    else:
        state_analysis, sd_result = _runtime_run_coroutine_sync(
            classify_parallel(
                query,
                conversation_history,
            )
        )

    user_stage = _runtime_resolve_user_stage(memory, state_analysis)
    informational_mode_hint = _runtime_derive_informational_mode_hint(phase8_signals, query)
    informational_mode = informational_mode_hint
    mode_prompt_key, mode_prompt_override = _runtime_resolve_mode_prompt(
        "informational" if informational_mode else "",
        config,
    )

    logger.info("STATE ANALYSIS ready conf=%.2f", float(state_analysis.confidence))

    if debug_info is not None:
        debug_info["state_analysis"] = {
            "primary": state_analysis.primary_state.value,
            "confidence": state_analysis.confidence,
            "secondary": [s.value for s in state_analysis.secondary_states],
            "emotional_tone": state_analysis.emotional_tone,
            "depth": state_analysis.depth,
            "user_stage": user_stage,
        }

    if debug_trace is not None:
        debug_trace["state_secondary"] = [s.value for s in state_analysis.secondary_states]
        debug_trace["user_state"] = state_analysis.primary_state.value
        debug_trace["informational_mode_hint"] = informational_mode_hint
        debug_trace["informational_mode"] = informational_mode
        debug_trace["applied_mode_prompt"] = mode_prompt_key if informational_mode else None

    return {
        "state_analysis": state_analysis,
        "sd_result": sd_result,
        "user_stage": user_stage,
        "informational_mode_hint": informational_mode_hint,
        "informational_mode": informational_mode,
        "mode_prompt_key": mode_prompt_key,
        "mode_prompt_override": mode_prompt_override,
    }


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
    debug_trace: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], str]:
    from ..contradiction_detector import detect_contradiction as _runtime_detect_contradiction

    contradiction_info = _runtime_detect_contradiction(query)
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
    detect_routing_signals,
    should_use_fast_path,
    logger,
) -> Tuple[Optional[Any], Optional[Any], bool]:
    decision_gate = None if use_deterministic_router else decision_gate_cls()
    pre_routing_result = None

    if use_deterministic_router:
        fast_path_enabled = False
        logger.info("[ROUTING_V1] deterministic resolver enabled; FAST_PATH disabled")
    else:
        pre_routing_signals = detect_routing_signals(query, [], state_analysis, memory=memory)
        pre_routing_signals["contradiction_detected"] = bool(
            contradiction_info.get("has_contradiction", False)
        )
        pre_routing_signals["contradiction_suggestion"] = contradiction_hint
        pre_routing_result = decision_gate.route(pre_routing_signals, user_stage=user_stage)
        fast_path_enabled = should_use_fast_path(query, pre_routing_result)
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


def _run_state_and_pre_routing_pipeline(
    *,
    query: str,
    memory,
    config,
    phase8_signals,
    debug_trace: Optional[Dict[str, Any]],
    debug_info: Optional[Dict[str, Any]],
    pipeline_stages: List[Dict[str, Any]],
    state_classifier,
    classify_parallel,
    logger,
    diagnostics_v1_enabled: bool,
    deterministic_route_resolver_enabled: bool,
    informational_branch_enabled: bool,
    diagnostics_classifier,
    decision_gate_cls,
    detect_routing_signals,
    should_use_fast_path,
) -> Dict[str, Any]:
    stage2 = _run_state_analysis_stage(
        query=query,
        memory=memory,
        config=config,
        phase8_signals=phase8_signals,
        debug_trace=debug_trace,
        debug_info=debug_info,
        pipeline_stages=pipeline_stages,
        state_classifier=state_classifier,
        classify_parallel=classify_parallel,
        logger=logger,
    )
    state_analysis = stage2["state_analysis"]
    sd_result = stage2["sd_result"]
    user_stage = stage2["user_stage"]
    informational_mode_hint = stage2["informational_mode_hint"]
    informational_mode = stage2["informational_mode"]
    mode_prompt_key = stage2["mode_prompt_key"]
    mode_prompt_override = stage2["mode_prompt_override"]

    use_new_diagnostics_v1 = diagnostics_v1_enabled
    use_deterministic_router = (
        deterministic_route_resolver_enabled and use_new_diagnostics_v1
    )

    diagnostics_v1, correction_protocol_active = _compute_diagnostics_v1(
        query=query,
        state_analysis=state_analysis,
        informational_mode_hint=informational_mode_hint,
        phase8_signals=phase8_signals,
        informational_branch_enabled=informational_branch_enabled,
        use_new_diagnostics_v1=use_new_diagnostics_v1,
        use_deterministic_router=use_deterministic_router,
        diagnostics_classifier=diagnostics_classifier,
        debug_trace=debug_trace,
        debug_info=debug_info,
    )

    contradiction_info, contradiction_hint = _build_contradiction_payload(
        query=query,
        debug_trace=debug_trace,
    )

    decision_gate, pre_routing_result, fast_path_enabled = _resolve_pre_routing(
        use_deterministic_router=use_deterministic_router,
        query=query,
        state_analysis=state_analysis,
        memory=memory,
        user_stage=user_stage,
        informational_mode=informational_mode,
        contradiction_info=contradiction_info,
        contradiction_hint=contradiction_hint,
        decision_gate_cls=decision_gate_cls,
        detect_routing_signals=detect_routing_signals,
        should_use_fast_path=should_use_fast_path,
        logger=logger,
    )

    return {
        "state_analysis": state_analysis,
        "sd_result": sd_result,
        "user_stage": user_stage,
        "informational_mode_hint": informational_mode_hint,
        "informational_mode": informational_mode,
        "mode_prompt_key": mode_prompt_key,
        "mode_prompt_override": mode_prompt_override,
        "use_new_diagnostics_v1": use_new_diagnostics_v1,
        "use_deterministic_router": use_deterministic_router,
        "diagnostics_v1": diagnostics_v1,
        "correction_protocol_active": correction_protocol_active,
        "contradiction_info": contradiction_info,
        "contradiction_hint": contradiction_hint,
        "decision_gate": decision_gate,
        "pre_routing_result": pre_routing_result,
        "fast_path_enabled": fast_path_enabled,
    }
