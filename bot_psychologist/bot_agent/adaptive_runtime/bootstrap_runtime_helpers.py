"""Bootstrap runtime helpers extracted from runtime_misc_helpers (Wave 130)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..onboarding_flow import build_start_message
from .state_helpers import _fallback_state_analysis


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


def _prepare_adaptive_run_context(
    *,
    top_k: Optional[int],
    debug: bool,
    user_id: str,
    config,
    output_validation_enabled_reader,
) -> Dict[str, Any]:
    from .mode_policy_helpers import (
        _deterministic_route_resolver_enabled as _runtime_deterministic_route_resolver_enabled,
        _diagnostics_v1_enabled as _runtime_diagnostics_v1_enabled,
        _informational_branch_enabled as _runtime_informational_branch_enabled,
        _prompt_stack_v2_enabled as _runtime_prompt_stack_v2_enabled,
    )
    from .pipeline_utils import _build_config_snapshot as _runtime_build_config_snapshot
    from .trace_helpers import _init_debug_payloads as _runtime_init_debug_payloads

    resolved_top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    llm_model_name = str(config.LLM_MODEL)
    prompt_stack_enabled = _runtime_prompt_stack_v2_enabled()
    output_validation_enabled = bool(output_validation_enabled_reader())
    informational_branch_enabled = _runtime_informational_branch_enabled()
    diagnostics_v1_enabled = _runtime_diagnostics_v1_enabled()
    deterministic_route_resolver_enabled = _runtime_deterministic_route_resolver_enabled()
    pipeline_stages: List[Dict[str, Any]] = []
    debug_info, debug_trace = _runtime_init_debug_payloads(
        debug=debug,
        user_id=user_id,
        pipeline_stages=pipeline_stages,
        config_snapshot=_runtime_build_config_snapshot(config),
    )
    return {
        "top_k": resolved_top_k,
        "start_time": start_time,
        "llm_model_name": llm_model_name,
        "prompt_stack_enabled": prompt_stack_enabled,
        "output_validation_enabled": output_validation_enabled,
        "informational_branch_enabled": informational_branch_enabled,
        "diagnostics_v1_enabled": diagnostics_v1_enabled,
        "deterministic_route_resolver_enabled": deterministic_route_resolver_enabled,
        "pipeline_stages": pipeline_stages,
        "debug_info": debug_info,
        "debug_trace": debug_trace,
        "conversation_context": "",
        "memory_context_bundle": None,
        "phase8_signals": None,
        "level_adapter": None,
        "current_stage": "init",
    }


def _load_runtime_memory_context(
    *,
    user_id: str,
    query: str,
    data_loader,
    get_conversation_memory,
    memory_updater,
    config,
) -> Dict[str, Any]:
    # Local import to avoid widening module-level coupling.
    from .trace_helpers import _get_memory_trace_metrics

    data_loader.load_all_data()
    memory = get_conversation_memory(user_id)
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
    data_loader,
    get_conversation_memory,
    memory_updater,
    config,
    informational_branch_enabled: bool,
    logger=None,
) -> Dict[str, Any]:
    from ..onboarding_flow import detect_phase8_signals as _runtime_detect_phase8_signals
    from .state_helpers import _resolve_path_user_level as _runtime_resolve_path_user_level
    from .trace_helpers import (
        _apply_memory_debug_info as _runtime_apply_memory_debug_info,
        _truncate_preview as _runtime_truncate_preview,
    )

    stage1 = _load_runtime_memory_context(
        user_id=user_id,
        query=query,
        data_loader=data_loader,
        get_conversation_memory=get_conversation_memory,
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
        debug_trace["cross_session_context"] = _runtime_truncate_preview(cross_session_context, 500)
        debug_trace["memory_strategy"] = (
            memory_context_bundle.strategy if memory_context_bundle else None
        )
        debug_trace["summary_staleness"] = (
            memory_context_bundle.staleness if memory_context_bundle else None
        )
        _runtime_apply_memory_debug_info(debug_trace, memory, memory_trace_metrics)

    phase8_signals = _runtime_detect_phase8_signals(query=query, turns_count=len(memory.turns))
    if debug_trace is not None:
        debug_trace["phase8_signals"] = phase8_signals.as_dict()

    start_command_response = None
    if informational_branch_enabled and phase8_signals.start_command:
        start_command_response = _build_start_command_response(
            user_id=user_id,
            user_level=user_level,
            query=query,
            memory=memory,
            start_time=start_time,
            schedule_summary_task=schedule_summary_task,
            logger=logger,
        )

    path_level_enum = _runtime_resolve_path_user_level(user_level)
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
