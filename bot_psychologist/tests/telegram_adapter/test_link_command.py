from __future__ import annotations

from datetime import datetime, timezone

import asyncio

from api.conversations import ConversationContext
from api.identity import IdentityContext
from api.telegram_adapter.config import TelegramAdapterSettings
from api.telegram_adapter.models import TelegramUpdateModel
from api.telegram_adapter.service import TelegramAdapterService


class _StubIdentityService:
    async def resolve_telegram(self, _telegram_user_id: str):
        return None

    async def resolve_or_create(self, **_kwargs):
        return IdentityContext(
            user_id="u1",
            session_id="s1",
            conversation_id="c1",
            channel="telegram",
            is_anonymous=False,
            created_new_user=False,
            provider="telegram",
            external_id="tg",
        )


class _StubConversationService:
    async def get_or_create_conversation(self, **_kwargs):
        return ConversationContext(
            conversation_id="c1",
            user_id="u1",
            session_id="s1",
            channel="telegram",
            status="active",
            started_at=datetime.now(timezone.utc),
            is_new=True,
        )

    async def touch_conversation(self, _conversation_id: str):
        return None


class _StubRegistrationService:
    def __init__(self, ok: bool = True):
        self.ok = ok

    async def confirm_telegram_link(self, *, code: str, telegram_user_id: str):
        from api.registration.models import ConfirmLinkResponse

        if self.ok:
            return ConfirmLinkResponse(ok=True, user_id="u1", username="user1")
        return ConfirmLinkResponse(ok=False, error_message="Код истёк")


async def _stub_chat_executor(query: str, **kwargs):
    return f"ok:{query}:{kwargs['user_id']}"


def _update(text: str) -> TelegramUpdateModel:
    return TelegramUpdateModel(
        update_id=1,
        telegram_user_id="tg_user_1",
        chat_id="chat_1",
        message_id="msg_1",
        text=text,
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
    )


def test_link_command_triggers_confirm_flow_success() -> None:
    service = TelegramAdapterService(
        identity_service=_StubIdentityService(),
        conversation_service=_StubConversationService(),
        registration_service=_StubRegistrationService(ok=True),
        chat_executor=_stub_chat_executor,
        settings=TelegramAdapterSettings(enabled=True, mode="mock"),
    )

    result = asyncio.run(service.handle_update(_update("/link A1B2C3")))
    assert result.ok is True
    assert "@user1" in result.answer_text


def test_link_command_triggers_confirm_flow_error() -> None:
    service = TelegramAdapterService(
        identity_service=_StubIdentityService(),
        conversation_service=_StubConversationService(),
        registration_service=_StubRegistrationService(ok=False),
        chat_executor=_stub_chat_executor,
        settings=TelegramAdapterSettings(enabled=True, mode="mock"),
    )

    result = asyncio.run(service.handle_update(_update("/link A1B2C3")))
    assert result.ok is False
    assert result.error == "link_failed"
