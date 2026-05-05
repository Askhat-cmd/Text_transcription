from __future__ import annotations

from typing import Any

import pytest

from api.telegram_adapter import service as telegram_service


@pytest.mark.asyncio
async def test_default_chat_executor_uses_multiagent_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_runtime(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"answer": "multiagent reply"}

    monkeypatch.setattr(
        telegram_service,
        "run_multiagent_adaptive_sync",
        _fake_runtime,
        raising=True,
    )

    result = await telegram_service._default_chat_executor(
        "hello from telegram",
        user_id="u-telegram",
        session_id="s-telegram",
        conversation_id="c-telegram",
    )

    assert isinstance(result, dict)
    assert result["answer"] == "multiagent reply"
    assert captured["query"] == "hello from telegram"
    assert captured["user_id"] == "u-telegram"
    assert captured["include_path_recommendation"] is False
    assert captured["include_feedback_prompt"] is False
    assert captured["debug"] is False
