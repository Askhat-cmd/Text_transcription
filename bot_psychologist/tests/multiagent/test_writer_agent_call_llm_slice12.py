from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice12 as slice12_module


EXPECTED_PATCH_KEYS = [
    "model",
    "api_mode",
    "temperature",
    "max_tokens",
    "timeout",
    "llm_response",
    "tokens_prompt",
    "tokens_completion",
    "tokens_total",
    "estimated_cost_usd",
    "duration_ms",
    "error",
    "fallback_used",
]


def _build_result() -> SimpleNamespace:
    return SimpleNamespace(
        text={"answer": "ok"},
        api_mode="responses",
        tokens_prompt=111,
        tokens_completion=222,
        tokens_total=333,
    )


def test_apply_call_llm_slice12_unpacks_response_and_preserves_identity() -> None:
    estimate_cost = Mock(return_value=0.123)
    result = _build_result()

    extracted = slice12_module._apply_call_llm_slice12_response_unpack_cost_and_bookkeeping(
        result=result,
        runtime_settings={
            "model": "gpt-5",
            "temperature": 0.7,
            "max_tokens": 1200,
            "timeout": 45,
        },
        start_ts=100.0,
        estimate_cost=estimate_cost,
    )

    assert extracted.llm_response is result.text
    assert list(extracted.last_debug_patch.keys()) == EXPECTED_PATCH_KEYS
    assert extracted.last_debug_patch["api_mode"] == "responses"
    assert extracted.last_debug_patch["tokens_prompt"] == 111
    assert extracted.last_debug_patch["tokens_completion"] == 222
    assert extracted.last_debug_patch["tokens_total"] == 333
    assert extracted.last_debug_patch["llm_response"] is result.text
    assert extracted.last_debug_patch["error"] is None
    assert extracted.last_debug_patch["fallback_used"] is False
    estimate_cost.assert_called_once_with(
        tokens_prompt=111,
        tokens_completion=222,
    )


def test_apply_call_llm_slice12_uses_module_time_perf_counter(monkeypatch) -> None:
    estimate_cost = Mock(return_value=None)
    result = _build_result()
    monkeypatch.setattr(slice12_module.time, "perf_counter", lambda: 100.123)

    extracted = slice12_module._apply_call_llm_slice12_response_unpack_cost_and_bookkeeping(
        result=result,
        runtime_settings={
            "model": "gpt-5-mini",
            "temperature": 0.2,
            "max_tokens": 900,
            "timeout": 30,
        },
        start_ts=100.0,
        estimate_cost=estimate_cost,
    )

    assert extracted.last_debug_patch["duration_ms"] == 123
    assert extracted.last_debug_patch["estimated_cost_usd"] is None
    estimate_cost.assert_called_once_with(
        tokens_prompt=111,
        tokens_completion=222,
    )


def test_apply_call_llm_slice12_preserves_runtime_settings_index_access_values() -> None:
    estimate_cost = Mock(return_value=9.99)
    result = _build_result()

    extracted = slice12_module._apply_call_llm_slice12_response_unpack_cost_and_bookkeeping(
        result=result,
        runtime_settings={
            "model": "gpt-5-nano",
            "temperature": 0.55,
            "max_tokens": 777,
            "timeout": 12,
        },
        start_ts=50.0,
        estimate_cost=estimate_cost,
    )

    assert extracted.last_debug_patch["model"] == "gpt-5-nano"
    assert extracted.last_debug_patch["temperature"] == 0.55
    assert extracted.last_debug_patch["max_tokens"] == 777
    assert extracted.last_debug_patch["timeout"] == 12
