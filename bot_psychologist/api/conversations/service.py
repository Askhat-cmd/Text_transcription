"""Business logic for conversation layer."""

from __future__ import annotations

import logging
from typing import Optional

from .models import ConversationContext, ConversationSummary
from .repository import ConversationRepository

logger = logging.getLogger(__name__)


class ConversationService:
    """Service facade for create/resume/close/list conversation lifecycle."""

    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    @staticmethod
    def _to_context(record, *, is_new: bool = False) -> ConversationContext:
        return ConversationContext(
            conversation_id=record.id,
            user_id=record.user_id,
            session_id=record.session_id,
            channel=record.channel,
            status=record.status,
            started_at=record.started_at,
            is_new=is_new,
        )

    async def get_or_create_conversation(
        self,
        *,
        user_id: str,
        session_id: str,
        channel: str = "web",
        force_new: bool = False,
    ) -> ConversationContext:
        if force_new:
            created = await self._repo.create_conversation(
                user_id=user_id,
                session_id=session_id,
                channel=channel,
            )
            logger.info(
                "conversation.created",
                extra={"conversation_id": created.id, "user_id": user_id, "channel": channel},
            )
            return self._to_context(created, is_new=True)

        active = await self._repo.get_active_conversation(
            user_id=user_id,
            session_id=session_id,
            channel=channel,
        )
        if active is not None:
            logger.info(
                "conversation.resumed",
                extra={"conversation_id": active.id, "user_id": user_id, "channel": channel},
            )
            return self._to_context(active, is_new=False)

        created = await self._repo.create_conversation(
            user_id=user_id,
            session_id=session_id,
            channel=channel,
        )
        logger.info(
            "conversation.created",
            extra={"conversation_id": created.id, "user_id": user_id, "channel": channel},
        )
        return self._to_context(created, is_new=True)

    async def start_new_conversation(
        self,
        user_id: str,
        session_id: str,
        channel: str = "web",
        title: Optional[str] = None,
    ) -> ConversationContext:
        await self._repo.pause_active_conversations(
            user_id=user_id,
            session_id=session_id,
            channel=channel,
        )
        created = await self._repo.create_conversation(
            user_id=user_id,
            session_id=session_id,
            channel=channel,
            title=title,
        )
        logger.info(
            "conversation.created",
            extra={"conversation_id": created.id, "user_id": user_id, "channel": channel},
        )
        return self._to_context(created, is_new=True)

    async def close_conversation(self, conversation_id: str, user_id: str) -> None:
        record = await self._repo.get_conversation(conversation_id)
        if record is None:
            return
        if record.user_id != user_id:
            raise PermissionError("conversation does not belong to user")
        await self._repo.close_conversation(conversation_id)
        logger.info(
            "conversation.closed",
            extra={"conversation_id": conversation_id, "user_id": user_id},
        )

    async def get_conversation_context(self, conversation_id: str) -> Optional[ConversationContext]:
        record = await self._repo.get_conversation(conversation_id)
        if record is None:
            return None
        return self._to_context(record, is_new=False)

    async def list_conversations(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[ConversationSummary]:
        rows = await self._repo.list_user_conversations(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=0,
        )
        return [
            ConversationSummary(
                conversation_id=row.id,
                status=row.status,
                started_at=row.started_at,
                last_message_at=row.last_message_at,
                title=row.title,
                message_count=row.message_count,
            )
            for row in rows
        ]

    async def touch_conversation(self, conversation_id: str) -> None:
        await self._repo.update_last_message_at(conversation_id)

