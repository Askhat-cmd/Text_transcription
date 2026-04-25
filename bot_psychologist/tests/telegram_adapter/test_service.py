from __future__ import annotations

from datetime import datetime, timezone

import asyncio

from api.conversations import ConversationContext
from api.identity import IdentityContext
from api.telegram_adapter.config import TelegramAdapterSettings
from api.telegram_adapter.models import TelegramUpdateModel
from api.telegram_adapter.service import TelegramAdapterService


class StubIdentityService:
    def __init__(self, resolved: IdentityContext | None):
        self.resolved = resolved
        self.called_with: list[str] = []

    async def resolve_telegram(self, telegram_user_id: str):
        self.called_with.append(telegram_user_id)
        return self.resolved

    async def resolve_or_create(self, **_kwargs):
        return None


class StubConversationService:
    def __init__(self, context: ConversationContext):
        self.context = context
        self.calls: list[dict] = []
        self.touched: list[str] = []

    async def get_or_create_conversation(self, **kwargs):
        self.calls.append(kwargs)
        return self.context

    async def touch_conversation(self, conversation_id: str):
        self.touched.append(conversation_id)


async def _stub_chat_executor(query: str, **kwargs):
    return f"stub:{query}:{kwargs['user_id']}"


def _update() -> TelegramUpdateModel:
    return TelegramUpdateModel(
        update_id=1,
        telegram_user_id="tg_user_1",
        chat_id="chat_1",
        message_id="msg_1",
        text="hello",
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
    )


def test_service_returns_not_linked_for_unlinked_user() -> None:
    conv_ctx = ConversationContext(
        conversation_id="conv-x",
        user_id="user-x",
        session_id="sess-x",
        channel="telegram",
        status="active",
        started_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        is_new=False,
    )
    identity_service = StubIdentityService(None)
    conv_service = StubConversationService(conv_ctx)

    service = TelegramAdapterService(
        identity_service=identity_service,
        conversation_service=conv_service,
        chat_executor=_stub_chat_executor,
        settings=TelegramAdapterSettings(enabled=True, mode="mock"),
    )

    result = asyncio.run(service.handle_update(_update()))

    assert result.ok is False
    assert result.error == "telegram_not_linked"


def test_service_uses_existing_linked_identity() -> None:
    identity = IdentityContext(
        user_id="user-linked",
        session_id="sess-linked",
        conversation_id="conv-linked",
        channel="telegram",
        is_anonymous=False,
        created_new_user=False,
        provider="telegram",
        external_id="tg_user_1",
    )
    conv_ctx = ConversationContext(
        conversation_id="conv-new",
        user_id="user-linked",
        session_id="sess-linked",
        channel="telegram",
        status="active",
        started_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        is_new=True,
    )
    identity_service = StubIdentityService(identity)
    conv_service = StubConversationService(conv_ctx)

    service = TelegramAdapterService(
        identity_service=identity_service,
        conversation_service=conv_service,
        chat_executor=_stub_chat_executor,
        settings=TelegramAdapterSettings(enabled=True, mode="mock"),
    )

    result = asyncio.run(service.handle_update(_update()))

    assert result.ok is True
    assert result.user_id == "user-linked"
    assert result.session_id == "sess-linked"


def test_service_creates_or_resumes_telegram_conversation() -> None:
    identity = IdentityContext(
        user_id="user-2",
        session_id="sess-2",
        conversation_id="conv-2",
        channel="telegram",
        is_anonymous=False,
        created_new_user=False,
        provider="telegram",
        external_id="tg_user_2",
    )
    conv_ctx = ConversationContext(
        conversation_id="conv-telegram-2",
        user_id="user-2",
        session_id="sess-2",
        channel="telegram",
        status="active",
        started_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        is_new=False,
    )
    identity_service = StubIdentityService(identity)
    conv_service = StubConversationService(conv_ctx)

    service = TelegramAdapterService(
        identity_service=identity_service,
        conversation_service=conv_service,
        chat_executor=_stub_chat_executor,
        settings=TelegramAdapterSettings(enabled=True, mode="mock"),
    )

    result = asyncio.run(service.handle_update(_update()))

    assert result.ok is True
    assert result.conversation_id == "conv-telegram-2"
    assert conv_service.calls
    assert conv_service.calls[0]["channel"] == "telegram"
