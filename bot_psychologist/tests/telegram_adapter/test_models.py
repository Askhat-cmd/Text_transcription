from __future__ import annotations

from datetime import datetime, timezone

from api.telegram_adapter.models import TelegramAdapterResponse, TelegramUpdateModel


def test_telegram_update_model_serializes_json() -> None:
    model = TelegramUpdateModel(
        update_id=1,
        telegram_user_id="tg_user_1",
        chat_id="chat_1",
        message_id="msg_1",
        text="hello",
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
    )
    payload = model.model_dump(mode="json")
    assert payload["telegram_user_id"] == "tg_user_1"
    assert payload["timestamp"].endswith("Z") or payload["timestamp"].endswith("+00:00")


def test_adapter_response_serializes_json() -> None:
    model = TelegramAdapterResponse(
        ok=True,
        user_id="u1",
        session_id="s1",
        conversation_id="c1",
        answer_text="answer",
    )
    payload = model.model_dump(mode="json")
    assert payload["ok"] is True
    assert payload["channel"] == "telegram"
