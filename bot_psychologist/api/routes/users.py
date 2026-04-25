"""User/session/memory-роуты API."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from bot_agent.config import config
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.storage import SessionManager

from ..auth import verify_api_key
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
    description="Get all chat sessions for user"
)
async def list_user_sessions(
    user_id: str,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        raw_sessions = manager.list_user_sessions(user_id=user_id, limit=limit)

        sessions = [
            ChatSessionInfoResponse(
                session_id=item.get("session_id", ""),
                user_id=user_id,
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
            user_id=user_id,
            total_sessions=len(sessions),
            sessions=sessions,
        )
    except Exception as e:
        logger.error(f"Error listing user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/users/{user_id}/sessions",
    response_model=ChatSessionInfoResponse,
    summary="Create user chat session",
    description="Create a new chat session for user"
)
async def create_user_session(
    user_id: str,
    request: Optional[CreateSessionRequest] = None,
    api_key: str = Depends(verify_api_key)
):
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        created = manager.create_user_session(
            user_id=user_id,
            title=(request.title if request else None),
        )

        return ChatSessionInfoResponse(
            session_id=created.get("session_id", ""),
            user_id=user_id,
            created_at=created.get("created_at") or datetime.now().isoformat(),
            last_active=created.get("last_active") or datetime.now().isoformat(),
            status=created.get("status") or "active",
            title=_session_title(created),
            turns_count=created.get("turns_count") or 0,
            last_user_input=created.get("last_user_input"),
            last_bot_response=created.get("last_bot_response"),
            last_turn_timestamp=created.get("last_turn_timestamp"),
        )
    except Exception as e:
        logger.error(f"Error creating session for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete user chat session",
    description="Delete one chat session of user"
)
async def delete_user_session(
    user_id: str,
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        payload = manager.load_session(session_id)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        session_info = payload.get("session_info", {})
        session_user_id = session_info.get("user_id")
        if session_user_id and session_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to user"
            )

        deleted = manager.delete_session_data(session_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        return DeleteSessionResponse(
            status="success",
            message=f"Session {session_id} deleted",
            user_id=user_id,
            session_id=session_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="стория пользователя",
    description="Получить историю диалога пользователя"
)
@router.post(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="стория пользователя (POST)",
    description="Получить историю диалога пользователя (совместимость)"
)
async def get_user_history(
    user_id: str,
    last_n_turns: int = 10,
    api_key: str = Depends(verify_api_key)
):
    """
    Получить историю диалога пользователя.
    
    **Параметры:**
    - `user_id`: ID пользователя
    - `last_n_turns`: Последние N оборотов (по умолчанию 10)
    
    **Возвращает:**
    - стория диалогов
    - Основные интересы
    - Средний рейтинг
    - Последнее взаимодействие
    """
    
    logger.info(f"📋 стория для {user_id}")
    
    try:
        memory = get_conversation_memory(user_id)
        summary = memory.get_summary()
        last_turns = memory.get_last_turns(last_n_turns)
        
        turns = []
        for turn in last_turns:
            turns.append(ConversationTurnResponse(
                timestamp=turn.timestamp,
                user_input=turn.user_input,
                user_state=turn.user_state,
                bot_response=turn.bot_response or "",
                blocks_used=turn.blocks_used,
                concepts=turn.concepts or [],
                user_feedback=turn.user_feedback,
                user_rating=turn.user_rating
            ))
        
        return UserHistoryResponse(
            user_id=user_id,
            total_turns=len(memory.turns),
            turns=turns,
            primary_interests=summary.get("primary_interests", []),
            average_rating=summary.get("average_rating", 0),
            last_interaction=summary.get("last_interaction")
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/users/{user_id}/summary",
    response_model=UserSummaryResponse,
    summary="Сводка пользователя",
    description="Краткая сводка по истории диалога пользователя"
)
async def get_user_summary(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"📌 Сводка для {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        summary = memory.get_summary()
        return UserSummaryResponse(
            user_id=user_id,
            total_turns=summary.get("total_turns", len(memory.turns)),
            primary_interests=summary.get("primary_interests", []),
            num_challenges=summary.get("num_challenges", 0),
            num_breakthroughs=summary.get("num_breakthroughs", 0),
            average_rating=summary.get("average_rating", 0),
            last_interaction=summary.get("last_interaction")
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/users/{user_id}/session",
    response_model=SessionInfoResponse,
    summary="Session Storage Status",
    description="Статус SQLite-персистентности для пользователя"
)
async def get_user_session_info(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        manager = memory.session_manager
        if not manager:
            return SessionInfoResponse(
                user_id=user_id,
                enabled=False,
                exists=False,
            )

        payload = manager.load_session(user_id)
        if not payload:
            return SessionInfoResponse(
                user_id=user_id,
                enabled=True,
                exists=False,
            )

        session_info = payload.get("session_info", {})
        turns = payload.get("conversation_turns", [])
        embeddings = payload.get("semantic_embeddings", [])

        return SessionInfoResponse(
            user_id=user_id,
            enabled=True,
            exists=True,
            status=session_info.get("status"),
            total_turns=len(turns),
            total_embeddings=len(embeddings),
            last_active=session_info.get("last_active"),
            has_working_state=bool(session_info.get("working_state")),
            has_summary=bool(session_info.get("conversation_summary")),
        )
    except Exception as e:
        logger.error(f"❌ Error loading session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/sessions/archive",
    response_model=ArchiveSessionsResponse,
    summary="Archive Old Sessions",
    description="Архивировать старые SQLite-сессии старше N дней"
)
async def archive_old_sessions(
    active_days: int = 90,
    archive_days: int = 365,
    api_key: str = Depends(verify_api_key)
):
    if active_days < 1 or archive_days < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_days and archive_days must be >= 1"
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
    except Exception as e:
        logger.error(f"❌ Error archiving sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/users/{user_id}/semantic-stats",
    summary="Semantic Memory Stats",
    description="Get semantic memory stats for user"
)
async def get_semantic_stats(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        if not memory.semantic_memory:
            return {"enabled": False, "message": "Semantic memory disabled"}
        stats = memory.semantic_memory.get_stats()
        return {"enabled": True, "user_id": user_id, **stats}
    except Exception as e:
        logger.error(f"❌ Error getting semantic stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/users/{user_id}/rebuild-semantic-memory",
    summary="Rebuild Semantic Memory",
    description="Rebuild semantic memory for user"
)
async def rebuild_semantic_memory(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        if not memory.semantic_memory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Semantic memory disabled"
            )
        memory.rebuild_semantic_memory()
        stats = memory.semantic_memory.get_stats()
        return {
            "success": True,
            "message": f"Semantic memory rebuilt for {stats.get('total_embeddings', 0)} turns",
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error rebuilding semantic memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/users/{user_id}/update-summary",
    summary="Update Conversation Summary",
    description="Force update conversation summary for user"
)
async def force_update_summary(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        if len(memory.turns) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough turns to create summary (minimum 5)"
            )
        memory._update_summary()
        return {
            "success": True,
            "summary": memory.summary,
            "updated_at_turn": memory.summary_updated_at,
            "summary_length": len(memory.summary) if memory.summary else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete(
    "/users/{user_id}/history",
    response_model=DeleteHistoryResponse,
    summary="Очистить историю пользователя",
    description="Удалить историю диалога пользователя"
)
async def delete_user_history(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"🧹 Очистка истории для {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        memory.clear()
        return DeleteHistoryResponse(
            status="success",
            message=f"стория пользователя {user_id} очищена",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete(
    "/users/{user_id}/gdpr-data",
    response_model=DeleteHistoryResponse,
    summary="GDPR Delete User Data",
    description="Полностью удалить данные пользователя из JSON/semantic cache/SQLite"
)
async def gdpr_delete_user_data(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"🗑️ GDPR delete for {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        memory.purge_user_data()
        return DeleteHistoryResponse(
            status="success",
            message=f"Данные пользователя {user_id} полностью удалены (GDPR)",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"❌ GDPR delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

