from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.llm_streaming import stream_answer_tokens


@pytest.mark.asyncio
async def test_stream_answer_tokens_yields_answer_and_callback() -> None:
    captured: dict = {}

    def _on_complete(result: dict) -> None:
        captured.update(result)

    def _fake_answer(*_args, **_kwargs) -> dict:
        return {"answer": "alpha beta", "processing_time_seconds": 0.1}

    tokens = [
        token
        async for token in stream_answer_tokens(
            "q",
            user_id="u1",
            on_complete=_on_complete,
            answer_fn=_fake_answer,
        )
    ]

    assert "".join(tokens) == "alpha beta"
    assert captured["answer"] == "alpha beta"


@pytest.mark.asyncio
async def test_stream_answer_tokens_forwards_runtime_arguments() -> None:
    captured_kwargs: dict = {}

    def _fake_answer(*_args, **kwargs) -> dict:
        captured_kwargs.update(kwargs)
        return {"answer": "ok"}

    _ = [
        token
        async for token in stream_answer_tokens(
            "query text",
            user_id="session_42",
            user_level="advanced",
            session_store=object(),
            include_path=True,
            include_feedback_prompt=True,
            debug=True,
            answer_fn=_fake_answer,
        )
    ]

    assert captured_kwargs["user_id"] == "session_42"
    assert captured_kwargs["user_level"] == "advanced"
    assert captured_kwargs["include_path_recommendation"] is True
    assert captured_kwargs["include_feedback_prompt"] is True
    assert captured_kwargs["debug"] is True
    assert captured_kwargs["schedule_summary_task"] is False


@pytest.mark.asyncio
async def test_stream_answer_tokens_handles_empty_answer() -> None:
    def _fake_answer(*_args, **_kwargs) -> dict:
        return {"answer": "", "processing_time_seconds": 0.01}

    tokens = [
        token
        async for token in stream_answer_tokens(
            "q",
            user_id="u2",
            answer_fn=_fake_answer,
        )
    ]

    assert tokens == []


@pytest.mark.asyncio
async def test_stream_answer_tokens_callback_failure_does_not_break_stream() -> None:
    def _fake_answer(*_args, **_kwargs) -> dict:
        return {"answer": "safe output"}

    def _broken_callback(_result: dict) -> None:
        raise RuntimeError("callback failed")

    tokens = [
        token
        async for token in stream_answer_tokens(
            "q",
            user_id="u3",
            on_complete=_broken_callback,
            answer_fn=_fake_answer,
        )
    ]

    assert "".join(tokens) == "safe output"
