# api/routes.py
"""
API Routes for Bot Psychologist API (Phase 5)

REST endpoints РґР»СЏ РІСЃРµС… С„СѓРЅРєС†РёР№ Phase 1-4.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Р”РѕР±Р°РІРёС‚СЊ РїСѓС‚СЊ Рє bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_agent import (
    answer_question_basic,
    answer_question_sag_aware,
    answer_question_graph_powered,
    answer_question_adaptive
)
from bot_agent.config import config
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.storage import SessionManager

from .models import (
    AskQuestionRequest, FeedbackRequest,
    AnswerResponse, AdaptiveAnswerResponse, FeedbackResponse,
    UserHistoryResponse, UserSummaryResponse, DeleteHistoryResponse, StatsResponse,
    SessionInfoResponse, ArchiveSessionsResponse,
    ChatSessionInfoResponse, UserSessionsResponse, CreateSessionRequest, DeleteSessionResponse,
    SourceResponse, StateAnalysisResponse, PathStepResponse, PathRecommendationResponse,
    ConversationTurnResponse
)
from .auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["bot"])

# Р“Р»РѕР±Р°Р»СЊРЅР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР° (РІ production РёСЃРїРѕР»СЊР·СѓР№ Р‘Р”)
_stats = {
    "total_users": set(),
    "total_questions": 0,
    "total_processing_time": 0.0,
    "states_count": {},
    "interests_count": {}
}


# ===== QUESTIONS ENDPOINTS =====

@router.post(
    "/questions/basic",
    response_model=AnswerResponse,
    summary="Phase 1: Р‘Р°Р·РѕРІС‹Р№ QA",
    description="Р‘Р°Р·РѕРІС‹Р№ РІРѕРїСЂРѕСЃ-РѕС‚РІРµС‚ (Phase 1)"
)
async def ask_basic_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 1:** Р‘Р°Р·РѕРІС‹Р№ QA Р±РµР· Р°РґР°РїС‚Р°С†РёРё.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - GPT LLM
    - РџСЂРѕСЃС‚РѕР№ РѕС‚РІРµС‚
    
    **РџСЂРёРјРµСЂ:**
    ```
    {
      "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
      "user_id": "user_123"
    }
    ```
    """
    
    logger.info(f"рџ“ќ Basic question: {request.query[:50]}... (user: {request.user_id})")
    
    try:
        result = answer_question_basic(
            request.query,
            user_id=request.user_id,
            use_semantic_memory=False
        )
        
        # РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        # РџСЂРµРѕР±СЂР°Р·РѕРІР°С‚СЊ sources
        sources = []
        for src in result.get("sources", []):
            sources.append(SourceResponse(
                block_id=src.get("block_id", ""),
                title=src.get("title", ""),
                youtube_link=src.get("youtube_link", ""),
                start=src.get("start", 0),
                end=src.get("end", 0),
                block_type=src.get("block_type", "unknown"),
                complexity_score=src.get("complexity_score", 0.0)
            ))
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/basic-with-semantic",
    response_model=AnswerResponse,
    summary="Phase 1: QA + Semantic Memory",
    description="Basic QA with semantic memory and summary"
)
async def ask_basic_question_with_semantic(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Phase 1 enhanced: basic QA with memory.
    """
    logger.info(f"рџ§  Basic+Semantic question: {request.query[:50]}... (user: {request.user_id})")

    try:
        result = answer_question_basic(
            request.query,
            user_id=request.user_id,
            debug=request.debug,
            use_semantic_memory=True
        )

        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)

        sources = []
        for src in result.get("sources", []):
            sources.append(SourceResponse(
                block_id=src.get("block_id", ""),
                title=src.get("title", ""),
                youtube_link=src.get("youtube_link", ""),
                start=src.get("start", 0),
                end=src.get("end", 0),
                block_type=src.get("block_type", "unknown"),
                complexity_score=src.get("complexity_score", 0.0)
            ))

        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/sag-aware",
    response_model=AnswerResponse,
    summary="Phase 2: SAG-aware QA",
    description="QA СЃ СѓС‡РµС‚РѕРј SAG v2.0 Рё СѓСЂРѕРІРЅСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def ask_sag_aware_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 2:** SAG-aware QA СЃ Р°РґР°РїС‚Р°С†РёРµР№ РїРѕ СѓСЂРѕРІРЅСЋ.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - User level adaptation (beginner/intermediate/advanced)
    - Semantic analysis
    - РђРґР°РїС‚РёРІРЅС‹Рµ РѕС‚РІРµС‚С‹
    """
    
    logger.info(f"рџ§  SAG-aware question: {request.query[:50]}... (level: {request.user_level})")
    
    try:
        result = answer_question_sag_aware(
            request.query,
            user_id=request.user_id,
            user_level=request.user_level.value,
            debug=request.debug
        )
        
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        # РџСЂРµРѕР±СЂР°Р·РѕРІР°С‚СЊ sources
        sources = []
        for src in result.get("sources", []):
            sources.append(SourceResponse(
                block_id=src.get("block_id", ""),
                title=src.get("title", ""),
                youtube_link=src.get("youtube_link", ""),
                start=src.get("start", 0),
                end=src.get("end", 0),
                block_type=src.get("block_type", "unknown"),
                complexity_score=src.get("complexity_score", 0.0)
            ))
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/graph-powered",
    response_model=AnswerResponse,
    summary="Phase 3: Knowledge Graph QA",
    description="QA СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј Knowledge Graph"
)
async def ask_graph_powered_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 3:** Graph-powered QA СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј Knowledge Graph.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - Knowledge Graph (95 СѓР·Р»РѕРІ, 2182 СЃРІСЏР·Рё)
    - Concept hierarchy
    - РџСЂР°РєС‚РёРєРё РёР· РіСЂР°С„Р°
    """
    
    logger.info(f"рџ“Љ Graph-powered question: {request.query[:50]}...")
    
    try:
        result = answer_question_graph_powered(
            request.query,
            user_id=request.user_id,
            user_level=request.user_level.value,
            debug=request.debug
        )
        
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        # РџСЂРµРѕР±СЂР°Р·РѕРІР°С‚СЊ sources
        sources = []
        for src in result.get("sources", []):
            sources.append(SourceResponse(
                block_id=src.get("block_id", ""),
                title=src.get("title", ""),
                youtube_link=src.get("youtube_link", ""),
                start=src.get("start", 0),
                end=src.get("end", 0),
                block_type=src.get("block_type", "unknown"),
                complexity_score=src.get("complexity_score", 0.0)
            ))
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/adaptive",
    response_model=AdaptiveAnswerResponse,
    summary="Phase 4: Adaptive QA",
    description="РџРѕР»РЅРѕСЃС‚СЊСЋ Р°РґР°РїС‚РёРІРЅС‹Р№ QA СЃ Р°РЅР°Р»РёР·РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ Рё РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹РјРё РїСѓС‚СЏРјРё"
)
async def ask_adaptive_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 4:** РџРѕР»РЅРѕСЃС‚СЊСЋ Р°РґР°РїС‚РёРІРЅС‹Р№ QA.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - State Classification (10 СЃРѕСЃС‚РѕСЏРЅРёР№)
    - Conversation Memory (РёСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіР°)
    - Personal Path Building (РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ РїСѓС‚Рё)
    - Р’СЃРµ РІРѕР·РјРѕР¶РЅРѕСЃС‚Рё Phase 1-3
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - РђРґР°РїС‚РёРІРЅС‹Р№ РѕС‚РІРµС‚
    - РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    - Р РµРєРѕРјРµРЅРґР°С†РёСЋ РїРµСЂСЃРѕРЅР°Р»СЊРЅРѕРіРѕ РїСѓС‚Рё
    - РђРґР°РїС‚РёРІРЅС‹Р№ Р·Р°РїСЂРѕСЃ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
    """
    
    logger.info(f"[ADAPTIVE] Adaptive question: {request.query[:50]}... (user: {request.user_id})")

    try:
        session_key = request.session_id or request.user_id

        if request.session_id:
            try:
                session_manager = SessionManager(str(config.BOT_DB_PATH))
                session_manager.create_session(
                    session_id=session_key,
                    user_id=request.user_id,
                    metadata={
                        "source": "api",
                        "owner_user_id": request.user_id,
                    },
                )
            except Exception as exc:
                logger.warning(f"⚠️ Failed to pre-create session {session_key}: {exc}")

        result = answer_question_adaptive(
            request.query,
            user_id=session_key,
            user_level=request.user_level.value,
            include_path_recommendation=request.include_path,
            include_feedback_prompt=request.include_feedback_prompt,
            debug=request.debug
        )
        
        # РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        state = result.get("state_analysis", {}).get("primary_state", "unknown")
        _stats["states_count"][state] = _stats["states_count"].get(state, 0) + 1
        
        # РџСЂРµРѕР±СЂР°Р·РѕРІР°С‚СЊ sources
        sources = []
        for src in result.get("sources", []):
            sources.append(SourceResponse(
                block_id=src.get("block_id", ""),
                title=src.get("title", ""),
                youtube_link=src.get("youtube_link", ""),
                start=src.get("start", 0),
                end=src.get("end", 0),
                block_type=src.get("block_type", "unknown"),
                complexity_score=src.get("complexity_score", 0.0)
            ))
        
        # РџРѕСЃС‚СЂРѕРёС‚СЊ state_analysis
        state_analysis_data = result.get("state_analysis", {})
        state_analysis = StateAnalysisResponse(
            primary_state=state_analysis_data.get("primary_state", "unknown"),
            confidence=state_analysis_data.get("confidence", 0),
            emotional_tone=state_analysis_data.get("emotional_tone", ""),
            recommendations=state_analysis_data.get("recommendations", [])
        )
        
        # РџРѕСЃС‚СЂРѕРёС‚СЊ path_recommendation
        path_rec = result.get("path_recommendation")
        path_recommendation = None
        if path_rec:
            first_step = path_rec.get("first_step")
            first_step_response = None
            if first_step:
                first_step_response = PathStepResponse(
                    step_number=first_step.get("step_number", 1),
                    title=first_step.get("title", ""),
                    duration_weeks=first_step.get("duration_weeks", 1),
                    practices=first_step.get("practices", []),
                    key_concepts=first_step.get("key_concepts", [])
                )
            path_recommendation = PathRecommendationResponse(
                current_state=path_rec.get("current_state", ""),
                target_state=path_rec.get("target_state", ""),
                key_focus=path_rec.get("key_focus", ""),
                steps_count=path_rec.get("steps_count", 0),
                total_duration_weeks=path_rec.get("total_duration_weeks", 0),
                first_step=first_step_response
            )
        
        response_metadata = dict(result.get("metadata", {}))
        response_metadata["user_id"] = request.user_id
        response_metadata["session_id"] = session_key

        return AdaptiveAnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            state_analysis=state_analysis,
            path_recommendation=path_recommendation,
            feedback_prompt=result.get("feedback_prompt", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            conversation_context=result.get("conversation_context", ""),
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=response_metadata,
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



# ===== USER SESSIONS ENDPOINTS =====

def _session_title(item: dict) -> str:
    metadata = item.get("metadata") or {}
    raw_title = metadata.get("title")
    if isinstance(raw_title, str) and raw_title.strip():
        return raw_title.strip()

    last_user_input = (item.get("last_user_input") or "").strip()
    if not last_user_input:
        return "New chat"
    if len(last_user_input) <= 42:
        return last_user_input
    return f"{last_user_input[:42]}..."


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
# ===== USER HISTORY ENDPOINTS =====

@router.get(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ",
    description="РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
@router.post(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (POST)",
    description="РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ)"
)
async def get_user_history(
    user_id: str,
    last_n_turns: int = 10,
    api_key: str = Depends(verify_api_key)
):
    """
    РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
    
    **РџР°СЂР°РјРµС‚СЂС‹:**
    - `user_id`: ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    - `last_n_turns`: РџРѕСЃР»РµРґРЅРёРµ N РѕР±РѕСЂРѕС‚РѕРІ (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 10)
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - РСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіРѕРІ
    - РћСЃРЅРѕРІРЅС‹Рµ РёРЅС‚РµСЂРµСЃС‹
    - РЎСЂРµРґРЅРёР№ СЂРµР№С‚РёРЅРі
    - РџРѕСЃР»РµРґРЅРµРµ РІР·Р°РёРјРѕРґРµР№СЃС‚РІРёРµ
    """
    
    logger.info(f"рџ“‹ РСЃС‚РѕСЂРёСЏ РґР»СЏ {user_id}")
    
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
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/users/{user_id}/summary",
    response_model=UserSummaryResponse,
    summary="РЎРІРѕРґРєР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ",
    description="РљСЂР°С‚РєР°СЏ СЃРІРѕРґРєР° РїРѕ РёСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def get_user_summary(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"рџ“Њ РЎРІРѕРґРєР° РґР»СЏ {user_id}")
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
            user_level=summary.get("user_level", "beginner"),
            last_interaction=summary.get("last_interaction")
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/users/{user_id}/session",
    response_model=SessionInfoResponse,
    summary="Session Storage Status",
    description="РЎС‚Р°С‚СѓСЃ SQLite-РїРµСЂСЃРёСЃС‚РµРЅС‚РЅРѕСЃС‚Рё РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
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
        logger.error(f"вќЊ Error loading session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/sessions/archive",
    response_model=ArchiveSessionsResponse,
    summary="Archive Old Sessions",
    description="РђСЂС…РёРІРёСЂРѕРІР°С‚СЊ СЃС‚Р°СЂС‹Рµ SQLite-СЃРµСЃСЃРёРё СЃС‚Р°СЂС€Рµ N РґРЅРµР№"
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
        logger.error(f"вќЊ Error archiving sessions: {e}")
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
        logger.error(f"вќЊ Error getting semantic stats: {e}")
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
        logger.error(f"вќЊ Error rebuilding semantic memory: {e}")
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
        logger.error(f"вќЊ Error updating summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/users/{user_id}/history",
    response_model=DeleteHistoryResponse,
    summary="РћС‡РёСЃС‚РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ",
    description="РЈРґР°Р»РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def delete_user_history(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"рџ§№ РћС‡РёСЃС‚РєР° РёСЃС‚РѕСЂРёРё РґР»СЏ {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        memory.clear()
        return DeleteHistoryResponse(
            status="success",
            message=f"РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id} РѕС‡РёС‰РµРЅР°",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/users/{user_id}/gdpr-data",
    response_model=DeleteHistoryResponse,
    summary="GDPR Delete User Data",
    description="РџРѕР»РЅРѕСЃС‚СЊСЋ СѓРґР°Р»РёС‚СЊ РґР°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РёР· JSON/semantic cache/SQLite"
)
async def gdpr_delete_user_data(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"рџ—‘пёЏ GDPR delete for {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        memory.purge_user_data()
        return DeleteHistoryResponse(
            status="success",
            message=f"Р”Р°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id} РїРѕР»РЅРѕСЃС‚СЊСЋ СѓРґР°Р»РµРЅС‹ (GDPR)",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"вќЊ GDPR delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== FEEDBACK ENDPOINTS =====

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ",
    description="РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ РЅР° РѕС‚РІРµС‚"
)
async def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ РЅР° РѕС‚РІРµС‚.
    
    **РўРёРїС‹ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё:**
    - `positive`: РћС‚РІРµС‚ Р±С‹Р» РїРѕР»РµР·РµРЅ вњ…
    - `negative`: РћС‚РІРµС‚ РЅРµ РїРѕРјРѕРі вќЊ
    - `neutral`: РќРµР№С‚СЂР°Р»СЊРЅР°СЏ РѕС†РµРЅРєР° рџ¤·
    
    **Р РµР№С‚РёРЅРі:** 1-5 Р·РІРµР·Рґ
    """
    
    logger.info(f"рџ‘Ќ РћР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ РѕС‚ {request.user_id}: {request.feedback}")
    
    try:
        memory = get_conversation_memory(request.user_id)
        memory.add_feedback(
            turn_index=request.turn_index,
            feedback=request.feedback.value,
            rating=request.rating
        )
        
        return FeedbackResponse(
            status="success",
            message="РћР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ СЃРѕС…СЂР°РЅРµРЅР°",
            user_id=request.user_id,
            turn_index=request.turn_index
        )
    
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"РҐРѕРґ #{request.turn_index} РЅРµ РЅР°Р№РґРµРЅ"
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== STATISTICS ENDPOINTS =====

@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="РћР±С‰Р°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР°",
    description="РџРѕР»СѓС‡РёС‚СЊ РѕР±С‰СѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ СЃРёСЃС‚РµРјС‹"
)
async def get_statistics(
    api_key: str = Depends(verify_api_key)
):
    """
    РџРѕР»СѓС‡РёС‚СЊ РѕР±С‰СѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ СЃРёСЃС‚РµРјС‹.
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - Р’СЃРµРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№
    - Р’СЃРµРіРѕ РІРѕРїСЂРѕСЃРѕРІ
    - РЎСЂРµРґРЅРµРµ РІСЂРµРјСЏ РѕР±СЂР°Р±РѕС‚РєРё
    - РўРѕРї СЃРѕСЃС‚РѕСЏРЅРёР№
    - РўРѕРї РёРЅС‚РµСЂРµСЃРѕРІ
    - РЎС‚Р°С‚РёСЃС‚РёРєР° РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
    """
    
    logger.info("рџ“Љ Р—Р°РїСЂРѕСЃ СЃС‚Р°С‚РёСЃС‚РёРєРё")
    
    avg_time = (
        _stats["total_processing_time"] / _stats["total_questions"]
        if _stats["total_questions"] > 0 else 0
    )
    
    return StatsResponse(
        total_users=len(_stats["total_users"]),
        total_questions=_stats["total_questions"],
        average_processing_time=round(avg_time, 2),
        top_states=_stats["states_count"],
        top_interests=[],
        feedback_stats={},
        timestamp=datetime.now().isoformat()
    )


# ===== HEALTH CHECK =====

@router.get(
    "/health",
    summary="РџСЂРѕРІРµСЂРєР° Р·РґРѕСЂРѕРІСЊСЏ",
    description="РџСЂРѕРІРµСЂРёС‚СЊ СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРµСЂР°"
)
async def health_check():
    """
    РџСЂРѕРІРµСЂРёС‚СЊ СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРµСЂР°.
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - РЎС‚Р°С‚СѓСЃ (healthy/unhealthy)
    - Р’РµСЂСЃРёСЋ API
    - РЎС‚Р°С‚СѓСЃ РєР°Р¶РґРѕРіРѕ РјРѕРґСѓР»СЏ
    """
    
    return {
        "status": "healthy",
        "version": "0.5.0",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "bot_agent": True,
            "conversation_memory": True,
            "state_classifier": True,
            "path_builder": True,
            "api": True
        }
    }








