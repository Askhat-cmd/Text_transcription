from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.llm_streaming import stream_answer_tokens


def _slow_answer(*_args, **_kwargs) -> dict:
    time.sleep(0.2)
    return {"answer": "parallel check", "processing_time_seconds": 0.2}


@pytest.mark.asyncio
async def test_concurrent_streams_dont_block() -> None:
    async def _run_stream(user_id: str) -> tuple[float, str]:
        start = time.monotonic()
        tokens = [
            token
            async for token in stream_answer_tokens(
                "test",
                user_id=user_id,
                user_level="beginner",
                answer_fn=_slow_answer,
            )
        ]
        return time.monotonic() - start, "".join(tokens)

    global_start = time.monotonic()
    results = await asyncio.gather(
        _run_stream("user_1"),
        _run_stream("user_2"),
    )
    total = time.monotonic() - global_start

    durations = [item[0] for item in results]
    answers = [item[1] for item in results]

    assert answers == ["parallel check", "parallel check"]
    assert total < max(durations) * 1.8, (
        f"Streams look sequential: total={total:.3f}s max_individual={max(durations):.3f}s"
    )
