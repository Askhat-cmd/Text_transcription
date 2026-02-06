# api/routes.py
"""
API Routes for Bot Psychologist API (Phase 5)

REST endpoints для всех функций Phase 1-4.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Добавить путь к bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_agent import (
    answer_question_basic,
    answer_question_sag_aware,
    answer_question_graph_powered,
    answer_question_adaptive
)
from bot_agent.conversation_memory import get_conversation_memory

from .models import (
    AskQuestionRequest, FeedbackRequest,
    AnswerResponse, AdaptiveAnswerResponse, FeedbackResponse, 
    UserHistoryResponse, UserSummaryResponse, DeleteHistoryResponse, StatsResponse,
    SourceResponse, StateAnalysisResponse, PathStepResponse, PathRecommendationResponse,
    ConversationTurnResponse
)
from .auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["bot"])

# Глобальная статистика (в production используй БД)
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
    summary="Phase 1: Базовый QA",
    description="Базовый вопрос-ответ (Phase 1)"
)
async def ask_basic_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 1:** Базовый QA без адаптации.
    
    Использует:
    - TF-IDF retrieval
    - GPT LLM
    - Простой ответ
    
    **Пример:**
    ```
    {
      "query": "Что такое осознавание?",
      "user_id": "user_123"
    }
    ```
    """
    
    logger.info(f"📝 Basic question: {request.query[:50]}... (user: {request.user_id})")
    
    try:
        result = answer_question_basic(
            request.query,
            user_id=request.user_id
        )
        
        # Обновить статистику
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        # Преобразовать sources
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
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/sag-aware",
    response_model=AnswerResponse,
    summary="Phase 2: SAG-aware QA",
    description="QA с учетом SAG v2.0 и уровня пользователя"
)
async def ask_sag_aware_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 2:** SAG-aware QA с адаптацией по уровню.
    
    Использует:
    - TF-IDF retrieval
    - User level adaptation (beginner/intermediate/advanced)
    - Semantic analysis
    - Адаптивные ответы
    """
    
    logger.info(f"🧠 SAG-aware question: {request.query[:50]}... (level: {request.user_level})")
    
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
        
        # Преобразовать sources
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
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/graph-powered",
    response_model=AnswerResponse,
    summary="Phase 3: Knowledge Graph QA",
    description="QA с использованием Knowledge Graph"
)
async def ask_graph_powered_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 3:** Graph-powered QA с использованием Knowledge Graph.
    
    Использует:
    - TF-IDF retrieval
    - Knowledge Graph (95 узлов, 2182 связи)
    - Concept hierarchy
    - Практики из графа
    """
    
    logger.info(f"📊 Graph-powered question: {request.query[:50]}...")
    
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
        
        # Преобразовать sources
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
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/adaptive",
    response_model=AdaptiveAnswerResponse,
    summary="Phase 4: Adaptive QA",
    description="Полностью адаптивный QA с анализом состояния и персональными путями"
)
async def ask_adaptive_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 4:** Полностью адаптивный QA.
    
    Использует:
    - State Classification (10 состояний)
    - Conversation Memory (история диалога)
    - Personal Path Building (персональные пути)
    - Все возможности Phase 1-3
    
    **Возвращает:**
    - Адаптивный ответ
    - Анализ состояния пользователя
    - Рекомендацию персонального пути
    - Адаптивный запрос обратной связи
    """
    
    logger.info(f"🎯 Adaptive question: {request.query[:50]}... (user: {request.user_id})")
    
    try:
        result = answer_question_adaptive(
            request.query,
            user_id=request.user_id,
            user_level=request.user_level.value,
            include_path_recommendation=request.include_path,
            include_feedback_prompt=request.include_feedback_prompt,
            debug=request.debug
        )
        
        # Обновить статистику
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        state = result.get("state_analysis", {}).get("primary_state", "unknown")
        _stats["states_count"][state] = _stats["states_count"].get(state, 0) + 1
        
        # Преобразовать sources
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
        
        # Построить state_analysis
        state_analysis_data = result.get("state_analysis", {})
        state_analysis = StateAnalysisResponse(
            primary_state=state_analysis_data.get("primary_state", "unknown"),
            confidence=state_analysis_data.get("confidence", 0),
            emotional_tone=state_analysis_data.get("emotional_tone", ""),
            recommendations=state_analysis_data.get("recommendations", [])
        )
        
        # Построить path_recommendation
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
        
        return AdaptiveAnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            state_analysis=state_analysis,
            path_recommendation=path_recommendation,
            feedback_prompt=result.get("feedback_prompt", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            conversation_context=result.get("conversation_context", ""),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== USER HISTORY ENDPOINTS =====

@router.get(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="История пользователя",
    description="Получить историю диалога пользователя"
)
@router.post(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="История пользователя (POST)",
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
    - История диалогов
    - Основные интересы
    - Средний рейтинг
    - Последнее взаимодействие
    """
    
    logger.info(f"📋 История для {user_id}")
    
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
            user_level=summary.get("user_level", "beginner"),
            last_interaction=summary.get("last_interaction")
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
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
            message=f"История пользователя {user_id} очищена",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== FEEDBACK ENDPOINTS =====

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Отправить обратную связь",
    description="Отправить обратную связь на ответ"
)
async def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Отправить обратную связь на ответ.
    
    **Типы обратной связи:**
    - `positive`: Ответ был полезен ✅
    - `negative`: Ответ не помог ❌
    - `neutral`: Нейтральная оценка 🤷
    
    **Рейтинг:** 1-5 звезд
    """
    
    logger.info(f"👍 Обратная связь от {request.user_id}: {request.feedback}")
    
    try:
        memory = get_conversation_memory(request.user_id)
        memory.add_feedback(
            turn_index=request.turn_index,
            feedback=request.feedback.value,
            rating=request.rating
        )
        
        return FeedbackResponse(
            status="success",
            message="Обратная связь сохранена",
            user_id=request.user_id,
            turn_index=request.turn_index
        )
    
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ход #{request.turn_index} не найден"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== STATISTICS ENDPOINTS =====

@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Общая статистика",
    description="Получить общую статистику системы"
)
async def get_statistics(
    api_key: str = Depends(verify_api_key)
):
    """
    Получить общую статистику системы.
    
    **Возвращает:**
    - Всего пользователей
    - Всего вопросов
    - Среднее время обработки
    - Топ состояний
    - Топ интересов
    - Статистика обратной связи
    """
    
    logger.info("📊 Запрос статистики")
    
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
    summary="Проверка здоровья",
    description="Проверить статус сервера"
)
async def health_check():
    """
    Проверить статус сервера.
    
    **Возвращает:**
    - Статус (healthy/unhealthy)
    - Версию API
    - Статус каждого модуля
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


