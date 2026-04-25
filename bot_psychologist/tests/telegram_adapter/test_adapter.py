from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.telegram_adapter.adapter import TelegramUpdateAdapter


def test_parse_valid_mock_update() -> None:
    adapter = TelegramUpdateAdapter()
    payload = {
        "update_id": 100,
        "telegram_user_id": "tg_user_100",
        "chat_id": "chat_100",
        "message_id": "msg_100",
        "text": "привет",
        "timestamp": "2026-04-25T12:00:00Z",
    }

    model = adapter.parse_payload(payload)

    assert model.telegram_user_id == "tg_user_100"
    assert model.chat_id == "chat_100"


def test_parse_invalid_mock_update() -> None:
    adapter = TelegramUpdateAdapter()
    payload = {
        "update_id": 101,
        "chat_id": "chat_101",
        "message_id": "msg_101",
        "text": "",
        "timestamp": "2026-04-25T12:00:00Z",
    }

    with pytest.raises(ValidationError):
        adapter.parse_payload(payload)
