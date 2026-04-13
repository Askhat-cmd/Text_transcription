"""Native async LLM streaming bridge for Neo runtime."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)


def _default_answer_fn() -> Callable[..., dict]:
    from .answer_adaptive import answer_question_adaptive

    return answer_question_adaptive


async def stream_answer_tokens(
    query: str,
    *,
    user_id: str,
    session_store: Any = None,
    include_path: bool = False,
    include_feedback_prompt: bool = False,
    debug: bool = False,
    on_complete: Optional[Callable[[dict], None]] = None,
    answer_fn: Optional[Callable[..., dict]] = None,
) -> AsyncIterator[str]:
    """
    Stream answer text as async tokens without blocking FastAPI event loop.

    Current implementation executes sync runtime in thread pool and yields
    word-split tokens. Native SDK token streaming is a next step (PRD-006).
    """
    loop = asyncio.get_running_loop()
    runtime_fn = answer_fn or _default_answer_fn()

    result: dict = await loop.run_in_executor(
        None,
        lambda: runtime_fn(
            query,
            user_id=user_id,
            include_path_recommendation=include_path,
            include_feedback_prompt=include_feedback_prompt,
            debug=debug,
            session_store=session_store,
            schedule_summary_task=False,
        ),
    )

    if on_complete:
        try:
            on_complete(result)
        except Exception as cb_exc:
            logger.warning("[STREAM] on_complete callback failed: %s", cb_exc)

    answer = str(result.get("answer", "") or "")
    words = answer.split(" ") if answer else []
    for idx, word in enumerate(words):
        token = word + (" " if idx < len(words) - 1 else "")
        if token:
            yield token
            await asyncio.sleep(0.001)
