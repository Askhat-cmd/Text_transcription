from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class CallLLMSlice12ResponseUnpackAndCostResult:
    llm_response: Any
    last_debug_patch: dict[str, Any]


def _apply_call_llm_slice12_response_unpack_cost_and_bookkeeping(
    *,
    result: Any,
    runtime_settings: dict[str, Any],
    start_ts: float,
    estimate_cost: Callable[..., Any],
) -> CallLLMSlice12ResponseUnpackAndCostResult:
    llm_response = result.text
    tokens_prompt, tokens_completion, tokens_total = (
        result.tokens_prompt,
        result.tokens_completion,
        result.tokens_total,
    )
    estimated_cost = estimate_cost(
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
    )
    duration_ms = int((time.perf_counter() - start_ts) * 1000)
    last_debug_patch: dict[str, Any] = {
        "model": runtime_settings["model"],
        "api_mode": result.api_mode,
        "temperature": runtime_settings["temperature"],
        "max_tokens": runtime_settings["max_tokens"],
        "timeout": runtime_settings["timeout"],
        "llm_response": llm_response,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "estimated_cost_usd": estimated_cost,
        "duration_ms": duration_ms,
        "error": None,
        "fallback_used": False,
    }
    return CallLLMSlice12ResponseUnpackAndCostResult(
        llm_response=llm_response,
        last_debug_patch=last_debug_patch,
    )
