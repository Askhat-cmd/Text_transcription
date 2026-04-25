"""User/session/memory API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from bot_agent.config import config
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.storage import SessionManager

from ..auth import verify_api_key
from ..dependencies import get_identity_context
from ..identity import IdentityContext
from ..models import (
    ArchiveSessionsResponse,
    ChatSessionInfoResponse,
    ConversationTurnResponse,
    CreateSessionRequest,
    DeleteHistoryResponse,
    DeleteSessionResponse,
    SessionInfoResponse,
    UserHistoryResponse,
    UserSessionsResponse,
    UserSummaryResponse,
)
from .common import _session_title, logger

router = APIRouter(prefix="/api/v1", tags=["bot"])


@router.get(
    "/users/{user_id}/sessions",
    response_model=UserSessionsResponse,
    summary="User chat sessions",
    description="Get all chat sessions for user",
)
async def list_user_sessions(
    user_id: str,
    limit: int = 100,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    try:
        canonical_user_id = identity.user_id
        manager = SessionManager(str(config.BOT_DB_PATH))
        raw_sessions = manager.list_user_sessions(user_id=canonical_user_id, limit=limit)

        sessions = [
            ChatSessionInfoResponse(
                session_id=item.get("session_id", ""),
                user_id=canonical_user_id,
                created_at=item.get("created_at") or datetime.now().isoformat(),
                last_active=item.get("last_active") or item.get("created_at") or datetime.now().isoformat(),
                status=item.get("status") or "active",
                title=_session_title(item),
                turns_count=item.get("turns_count") or 0,
                last_user_input=item.get("last_user_input"),
                last_bot_response=item.get("last_bot_response"),
                last_turn_timestamp=item.get("last_turn_timestamp"),
            )
            for item in raw_sessions
        ]

        return UserSessionsResponse(
            user_id=canonical_user_id,
            total_sessions=len(sessions),
            sessions=sessions,
        )
    except Exception as exc:
        logger.error("Error listing user sessions: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/users/{user_id}/sessions",
    response_model=ChatSessionInfoResponse,
    summary="Create user chat session",
    description="Create a new chat session for user",
)
async def create_user_session(
    user_id: str,
    request: Optional[CreateSessionRequest] = None,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    try:
        canonical_user_id = identity.user_id
        manager = SessionManager(str(config.BOT_DB_PATH))
        created = manager.create_user_session(
            user_id=canonical_user_id,
            title=(request.title if request else None),
        )

        return ChatSessionInfoResponse(
            session_id=created.get("session_id", ""),
            user_id=canonical_user_id,
            created_at=created.get("created_at") or datetime.now().isoformat(),
            last_active=created.get("last_active") or datetime.now().isoformat(),
            status=created.get("status") or "active",
            title=_session_title(created),
            turns_count=created.get("turns_count") or 0,
            last_user_input=created.get("last_user_input"),
            last_bot_response=created.get("last_bot_response"),
            last_turn_timestamp=created.get("last_turn_timestamp"),
        )
    except Exception as exc:
        logger.error("Error creating session for %s: %s", user_id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete user chat session",
    description="Delete one chat session of user",
)
async def delete_user_session(
    user_id: str,
    session_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    try:
        canonical_user_id = identity.user_id
        manager = SessionManager(str(config.BOT_DB_PATH))
        payload = manager.load_session(session_id)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        session_info = payload.get("session_info", {})
        session_user_id = session_info.get("user_id")
        if session_user_id and session_user_id != canonical_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to user",
            )

        deleted = manager.delete_session_data(session_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return DeleteSessionResponse(
            status="success",
            message=f"Session {session_id} deleted",
            user_id=canonical_user_id,
            session_id=session_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting session %s: %s", session_id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="User history",
    description="Get user dialogue history",
)
@router.post(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="User history (POST)",
    description="Get user dialogue history (compatibility)",
)
async def get_user_history(
    user_id: str,
    last_n_turns: int = 10,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    logger.info("History requested for user=%s", canonical_user_id)

    try:
        requested_scope = (user_id or "").strip()
        manager = SessionManager(str(config.BOT_DB_PATH))

        # РЎРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ СЃ Web UI:
        # РµСЃР»Рё РІ path РїРµСЂРµРґР°РЅ session_id Р°РєС‚РёРІРЅРѕРіРѕ С‡Р°С‚Р°, РІРѕР·РІСЂР°С‰Р°РµРј РёСЃС‚РѕСЂРёСЋ РёРјРµРЅРЅРѕ СЌС‚РѕР№ СЃРµСЃСЃРёРё.
        if requested_scope and requested_scope != canonical_user_id:
            payload = manager.load_session(requested_scope)
            if payload:
                session_info = payload.get("session_info", {}) or {}
                session_owner = session_info.get("user_id")
                if session_owner and session_owner != canonical_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Session does not belong to user",
                    )

                all_turns = payload.get("conversation_turns", []) or []
                sliced_turns = all_turns[-max(1, int(last_n_turns)) :]
                turns = [
                    ConversationTurnResponse(
                        timestamp=turn.get("timestamp", ""),
                        user_input=turn.get("user_input", ""),
                        user_state=turn.get("user_state"),
                        bot_response=turn.get("bot_response", ""),
                        blocks_used=len(turn.get("chunks_used", []) or []),
                        concepts=[],
                        user_feedback=turn.get("user_feedback"),
                        user_rating=turn.get("user_rating"),
                    )
                    for turn in sliced_turns
                ]
                return UserHistoryResponse(
                    user_id=canonical_user_id,
                    total_turns=len(all_turns),
                    turns=turns,
                    primary_interests=[],
                    average_rating=0.0,
                    last_interaction=(
                        all_turns[-1].get("timestamp") if all_turns else None
                    ),
                )
            # Если явно запрошена сессия, но ее нет в БД — возвращаем пустую историю,
            # чтобы не смешивать новый чат с legacy user-memory.
            return UserHistoryResponse(
                user_id=canonical_user_id,
                total_turns=0,
                turns=[],
                primary_interests=[],
                average_rating=0.0,
                last_interaction=None,
            )


        # РСЃС‚РѕСЂРёСЏ РїРѕ legacy user memory (РѕР±СЂР°С‚РЅР°СЏ СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ).
        memory = get_conversation_memory(canonical_user_id)
        summary = memory.get_summary()
        last_turns = memory.get_last_turns(last_n_turns)

        turns = []
        for turn in last_turns:
            turns.append(
                ConversationTurnResponse(
                    timestamp=turn.timestamp,
                    user_input=turn.user_input,
                    user_state=turn.user_state,
                    bot_response=turn.bot_response or "",
                    blocks_used=turn.blocks_used,
                    concepts=turn.concepts or [],
                    user_feedback=turn.user_feedback,
                    user_rating=turn.user_rating,
                )
            )

        return UserHistoryResponse(
            user_id=canonical_user_id,
            total_turns=len(memory.turns),
            turns=turns,
            primary_interests=summary.get("primary_interests", []),
            average_rating=summary.get("average_rating", 0),
            last_interaction=summary.get("last_interaction"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching user history: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/users/{user_id}/summary",
    response_model=UserSummaryResponse,
    summary="User summary",
    description="Compact user history summary",
)
async def get_user_summary(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    logger.info("Summary requested for user=%s", canonical_user_id)
    try:
        memory = get_conversation_memory(canonical_user_id)
        summary = memory.get_summary()
        return UserSummaryResponse(
            user_id=canonical_user_id,
            total_turns=summary.get("total_turns", len(memory.turns)),
            primary_interests=summary.get("primary_interests", []),
            num_challenges=summary.get("num_challenges", 0),
            num_breakthroughs=summary.get("num_breakthroughs", 0),
            average_rating=summary.get("average_rating", 0),
            last_interaction=summary.get("last_interaction"),
        )
    except Exception as exc:
        logger.error("Error fetching summary: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/users/{user_id}/session",
    response_model=SessionInfoResponse,
    summary="Session storage status",
    description="SQLite persistence status for user",
)
async def get_user_session_info(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    try:
        memory = get_conversation_memory(canonical_user_id)
        manager = memory.session_manager
        if not manager:
            return SessionInfoResponse(user_id=canonical_user_id, enabled=False, exists=False)

        payload = manager.load_session(canonical_user_id)
        if not payload:
            return SessionInfoResponse(user_id=canonical_user_id, enabled=True, exists=False)

        session_info = payload.get("session_info", {})
        turns = payload.get("conversation_turns", [])
        embeddings = payload.get("semantic_embeddings", [])
        return SessionInfoResponse(
            user_id=canonical_user_id,
            enabled=True,
            exists=True,
            status=session_info.get("status"),
            total_turns=len(turns),
            total_embeddings=len(embeddings),
            last_active=session_info.get("last_active"),
            has_working_state=bool(session_info.get("working_state")),
            has_summary=bool(session_info.get("conversation_summary")),
        )
    except Exception as exc:
        logger.error("Error loading session info: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/sessions/archive",
    response_model=ArchiveSessionsResponse,
    summary="Archive old sessions",
    description="Archive old SQLite sessions by retention policy",
)
async def archive_old_sessions(
    active_days: int = 90,
    archive_days: int = 365,
    api_key: str = Depends(verify_api_key),
):
    if active_days < 1 or archive_days < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_days and archive_days must be >= 1",
        )
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        cleanup_result = manager.run_retention_cleanup(
            active_days=active_days,
            archive_days=archive_days,
        )
        return ArchiveSessionsResponse(
            status="success",
            archived_count=cleanup_result["archived_count"],
            deleted_count=cleanup_result["deleted_count"],
            active_days=active_days,
            archive_days=archive_days,
            db_path=str(config.BOT_DB_PATH),
        )
    except Exception as exc:
        logger.error("Error archiving sessions: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/users/{user_id}/semantic-stats",
    summary="Semantic memory stats",
    description="Get semantic memory stats for user",
)
async def get_semantic_stats(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    try:
        memory = get_conversation_memory(canonical_user_id)
        if not memory.semantic_memory:
            return {"enabled": False, "message": "Semantic memory disabled"}
        stats = memory.semantic_memory.get_stats()
        return {"enabled": True, "user_id": canonical_user_id, **stats}
    except Exception as exc:
        logger.error("Error getting semantic stats: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/users/{user_id}/rebuild-semantic-memory",
    summary="Rebuild semantic memory",
    description="Rebuild semantic memory for user",
)
async def rebuild_semantic_memory(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    try:
        memory = get_conversation_memory(canonical_user_id)
        if not memory.semantic_memory:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Semantic memory disabled")
        memory.rebuild_semantic_memory()
        stats = memory.semantic_memory.get_stats()
        return {
            "success": True,
            "message": f"Semantic memory rebuilt for {stats.get('total_embeddings', 0)} turns",
            "stats": stats,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error rebuilding semantic memory: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/users/{user_id}/update-summary",
    summary="Update conversation summary",
    description="Force update conversation summary for user",
)
async def force_update_summary(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    try:
        memory = get_conversation_memory(canonical_user_id)
        if len(memory.turns) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough turns to create summary (minimum 5)",
            )
        memory._update_summary()
        return {
            "success": True,
            "summary": memory.summary,
            "updated_at_turn": memory.summary_updated_at,
            "summary_length": len(memory.summary) if memory.summary else 0,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating summary: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/users/{user_id}/history",
    response_model=DeleteHistoryResponse,
    summary="Delete user history",
    description="Delete dialogue history for user",
)
async def delete_user_history(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    logger.info("History cleanup for user=%s", canonical_user_id)
    try:
        memory = get_conversation_memory(canonical_user_id)
        memory.clear()
        return DeleteHistoryResponse(
            status="success",
            message=f"History for user {canonical_user_id} cleared",
            user_id=canonical_user_id,
        )
    except Exception as exc:
        logger.error("Error deleting history: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/users/{user_id}/gdpr-data",
    response_model=DeleteHistoryResponse,
    summary="GDPR delete user data",
    description="Delete all user data from JSON/semantic cache/SQLite",
)
async def gdpr_delete_user_data(
    user_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    canonical_user_id = identity.user_id
    logger.info("GDPR delete for user=%s", canonical_user_id)
    try:
        memory = get_conversation_memory(canonical_user_id)
        memory.purge_user_data()
        return DeleteHistoryResponse(
            status="success",
            message=f"User data for {canonical_user_id} deleted (GDPR)",
            user_id=canonical_user_id,
        )
    except Exception as exc:
        logger.error("GDPR delete error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
