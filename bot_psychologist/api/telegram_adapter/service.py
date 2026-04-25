"""Telegram adapter orchestration service."""

from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable, Protocol

from bot_agent import answer_question_adaptive

from api.conversations import ConversationService
from api.identity import IdentityService

from .config import TelegramAdapterSettings, telegram_settings
from .models import TelegramAdapterResponse, TelegramUpdateModel

logger = logging.getLogger(__name__)


class TelegramChatExecutor(Protocol):
    def __call__(
        self,
        query: str,
        *,
        user_id: str,
        session_id: str,
        conversation_id: str,
    ) -> str | dict[str, Any] | Awaitable[str | dict[str, Any]]:
        ...


async def _default_chat_executor(
    query: str,
    *,
    user_id: str,
    session_id: str,
    conversation_id: str,
) -> str | dict[str, Any]:
    _ = (session_id, conversation_id)
    return answer_question_adaptive(
        query,
        user_id=user_id,
        include_path_recommendation=False,
        include_feedback_prompt=False,
        debug=False,
    )


class TelegramAdapterService:
    """Handles Telegram mock update via identity+conversation contracts."""

    def __init__(
        self,
        *,
        identity_service: IdentityService,
        conversation_service: ConversationService,
        chat_executor: TelegramChatExecutor | None = None,
        settings: TelegramAdapterSettings | None = None,
        strict_linking: bool = True,
    ) -> None:
        self.identity_service = identity_service
        self.conversation_service = conversation_service
        self.chat_executor = chat_executor or _default_chat_executor
        self.settings = settings or telegram_settings
        self.strict_linking = strict_linking

    async def handle_update(self, update: TelegramUpdateModel) -> TelegramAdapterResponse:
        if (not self.settings.enabled) or self.settings.mode == "disabled":
            return TelegramAdapterResponse(ok=False, error="telegram_disabled")

        identity = await self.identity_service.resolve_telegram(update.telegram_user_id)
        if identity is None:
            if self.strict_linking:
                return TelegramAdapterResponse(ok=False, error="telegram_not_linked")
            identity = await self.identity_service.resolve_or_create(
                provider="telegram",
                external_id=update.telegram_user_id,
                session_id=f"tg_{update.telegram_user_id}",
                channel="telegram",
                metadata={"source": "telegram_mock"},
            )

        conversation = await self.conversation_service.get_or_create_conversation(
            user_id=identity.user_id,
            session_id=identity.session_id,
            channel="telegram",
        )

        answer_text = await self._run_chat(
            update.text,
            user_id=identity.user_id,
            session_id=identity.session_id,
            conversation_id=conversation.conversation_id,
        )

        await self.conversation_service.touch_conversation(conversation.conversation_id)

        logger.info(
            "telegram.adapter.handled",
            extra={
                "user_id": identity.user_id,
                "conversation_id": conversation.conversation_id,
                "mode": self.settings.mode,
            },
        )

        return TelegramAdapterResponse(
            ok=True,
            user_id=identity.user_id,
            session_id=identity.session_id,
            conversation_id=conversation.conversation_id,
            channel="telegram",
            answer_text=answer_text,
            used_mock_transport=True,
        )

    async def _run_chat(
        self,
        query: str,
        *,
        user_id: str,
        session_id: str,
        conversation_id: str,
    ) -> str:
        result = self.chat_executor(
            query,
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, dict):
            return str(result.get("answer") or "")
        return str(result)
