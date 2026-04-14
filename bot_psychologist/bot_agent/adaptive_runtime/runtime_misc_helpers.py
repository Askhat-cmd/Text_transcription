"""Runtime misc helpers extracted from answer_adaptive (Wave 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

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
