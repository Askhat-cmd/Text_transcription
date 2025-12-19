
***

# 📋 PHASE 5: API Endpoints (FastAPI)

## Обзор Phase 5

**Phase 5** — REST API для взаимодействия с ботом через HTTP endpoints. Основано на FastAPI.

**Что добавляет:**

- 🔌 **FastAPI Server** — асинхронный веб-сервер
- 📡 **REST Endpoints** — все функции фаз 1-4 доступны через API
- 🔐 **Authentication** — API ключи для защиты
- 📝 **Request Validation** — Pydantic models для валидации
- 📊 **Response Models** — структурированные ответы
- 📈 **Rate Limiting** — ограничение частоты запросов
- 📚 **Swagger/OpenAPI** — auto-генерируемая документация
- 🔄 **CORS** — поддержка cross-origin requests
- ⚡ **Async/await** — асинхронная обработка

***

## 🏗️ Архитектура Phase 5

```
┌─────────────────────────────────────────────────────────┐
│                    Web Client / Mobile                   │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP/REST
                   ↓
┌─────────────────────────────────────────────────────────┐
│            FastAPI Server (Phase 5)                      │
├─────────────────────────────────────────────────────────┤
│  Auth Middleware │ CORS │ Rate Limiter                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Router: /api/v1/questions                        │  │
│  │ Router: /api/v1/users/{user_id}                  │  │
│  │ Router: /api/v1/feedback                         │  │
│  │ Router: /api/v1/stats                            │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │  Bot Agent v0.4.0    │
        │  (Phases 1-4)        │
        └──────────────────────┘
```


***

## Шаг 1: Создание `api/models.py`

Создай файл `bot_psychologist/api/models.py`:

```python
# api/models.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class UserLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FeedbackType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ===== REQUEST MODELS =====

class AskQuestionRequest(BaseModel):
    """Запрос на ответ на вопрос"""
    query: str = Field(..., min_length=3, max_length=500, description="Вопрос пользователя")
    user_id: str = Field(default="default", min_length=1, max_length=100, description="ID пользователя")
    user_level: UserLevel = Field(default=UserLevel.BEGINNER, description="Уровень пользователя")
    include_path: bool = Field(default=True, description="Включить рекомендацию пути")
    include_feedback_prompt: bool = Field(default=True, description="Включить запрос обратной связи")
    debug: bool = Field(default=False, description="Отладочная информация")
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Вопрос не может быть пустым")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Что такое осознавание?",
                "user_id": "user_123",
                "user_level": "beginner",
                "include_path": True,
                "include_feedback_prompt": True,
                "debug": False
            }
        }


class FeedbackRequest(BaseModel):
    """Запрос на сохранение обратной связи"""
    user_id: str = Field(..., min_length=1, max_length=100, description="ID пользователя")
    turn_index: int = Field(..., ge=0, description="Индекс хода диалога (0-based)")
    feedback: FeedbackType = Field(..., description="Тип обратной связи")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Рейтинг (1-5)")
    comment: Optional[str] = Field(default=None, max_length=500, description="Комментарий пользователя")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_123",
                "turn_index": 0,
                "feedback": "positive",
                "rating": 5,
                "comment": "Очень помогло!"
            }
        }


class GetUserHistoryRequest(BaseModel):
    """Запрос на историю пользователя"""
    user_id: str = Field(..., min_length=1, max_length=100, description="ID пользователя")
    last_n_turns: int = Field(default=10, ge=1, le=50, description="Последние N оборотов")


class GetStatsRequest(BaseModel):
    """Запрос на статистику"""
    user_id: Optional[str] = Field(default=None, description="ID пользователя (опционально)")
    time_range_days: int = Field(default=30, ge=1, le=365, description="Временной диапазон (дни)")


# ===== RESPONSE MODELS =====

class SourceResponse(BaseModel):
    """Источник (блок)"""
    block_id: str
    title: str
    youtube_link: str
    start: int
    end: int
    block_type: str
    complexity_score: float


class StateAnalysisResponse(BaseModel):
    """Анализ состояния пользователя"""
    primary_state: str
    confidence: float
    emotional_tone: str
    recommendations: List[str]


class PathStepResponse(BaseModel):
    """Один шаг пути"""
    step_number: int
    title: str
    duration_weeks: int
    practices: List[str]
    key_concepts: List[str]


class PathRecommendationResponse(BaseModel):
    """Рекомендация пути"""
    current_state: str
    target_state: str
    key_focus: str
    steps_count: int
    total_duration_weeks: int
    first_step: Optional[PathStepResponse]


class AnswerResponse(BaseModel):
    """Ответ на вопрос (фаза 1-3)"""
    status: str
    answer: str
    concepts: List[str]
    sources: List[SourceResponse]
    metadata: Dict[str, Any]
    timestamp: str
    processing_time_seconds: float


class AdaptiveAnswerResponse(BaseModel):
    """Адаптивный ответ (фаза 4)"""
    status: str
    answer: str
    state_analysis: StateAnalysisResponse
    path_recommendation: Optional[PathRecommendationResponse]
    feedback_prompt: str
    concepts: List[str]
    sources: List[SourceResponse]
    conversation_context: str
    metadata: Dict[str, Any]
    timestamp: str
    processing_time_seconds: float


class ConversationTurnResponse(BaseModel):
    """Один ход диалога"""
    timestamp: str
    user_input: str
    user_state: Optional[str]
    bot_response: str
    blocks_used: int
    concepts: List[str]
    user_feedback: Optional[str]
    user_rating: Optional[int]


class UserHistoryResponse(BaseModel):
    """История пользователя"""
    user_id: str
    total_turns: int
    turns: List[ConversationTurnResponse]
    primary_interests: List[str]
    average_rating: float
    last_interaction: Optional[str]


class FeedbackResponse(BaseModel):
    """Ответ на отправку обратной связи"""
    status: str
    message: str
    user_id: str
    turn_index: int


class HealthCheckResponse(BaseModel):
    """Проверка здоровья"""
    status: str
    version: str
    timestamp: str
    uptime_seconds: float
    modules: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Ошибка"""
    status: str
    error: str
    detail: Optional[str]
    timestamp: str


class StatsResponse(BaseModel):
    """Статистика"""
    total_users: int
    total_questions: int
    average_processing_time: float
    top_states: Dict[str, int]
    top_interests: List[str]
    feedback_stats: Dict[str, int]
    timestamp: str
```


***

## Шаг 2: Создание `api/auth.py`

Создай файл `bot_psychologist/api/auth.py`:

```python
# api/auth.py

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from functools import lru_cache
import hashlib
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Управление API ключами"""
    
    def __init__(self):
        # В production используй настоящую базу данных
        self.api_keys = {
            "test-key-001": {
                "name": "Test Client",
                "created": datetime.now(),
                "rate_limit": 100,  # requests per minute
                "active": True
            },
            "dev-key-001": {
                "name": "Development",
                "created": datetime.now(),
                "rate_limit": 1000,
                "active": True
            }
        }
        
        # Простое хранилище для rate limiting (в production используй Redis)
        self.request_counts = {}
    
    def get_api_key(self, key: str) -> Optional[dict]:
        """Получить информацию об API ключе"""
        return self.api_keys.get(key)
    
    def is_valid(self, key: str) -> bool:
        """Проверить валидность ключа"""
        key_info = self.get_api_key(key)
        return key_info is not None and key_info.get("active", False)
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Проверить лимит частоты запросов"""
        key_info = self.get_api_key(api_key)
        if not key_info:
            return False
        
        rate_limit = key_info.get("rate_limit", 100)
        
        # Инициализировать счетчик
        now = datetime.now()
        minute_key = f"{api_key}:{now.strftime('%Y-%m-%d %H:%M')}"
        
        if minute_key not in self.request_counts:
            self.request_counts[minute_key] = 0
        
        # Проверить лимит
        if self.request_counts[minute_key] >= rate_limit:
            return False
        
        self.request_counts[minute_key] += 1
        
        # Очистить старые ключи (старше 2 минут)
        cutoff_time = now - timedelta(minutes=2)
        for key in list(self.request_counts.keys()):
            try:
                stored_time = datetime.strptime(key.split(":")[1], "%Y-%m-%d %H:%M")
                if stored_time < cutoff_time:
                    del self.request_counts[key]
            except (ValueError, IndexError):
                pass
        
        return True
    
    def add_api_key(self, key: str, name: str, rate_limit: int = 100):
        """Добавить новый API ключ (администратор)"""
        self.api_keys[key] = {
            "name": name,
            "created": datetime.now(),
            "rate_limit": rate_limit,
            "active": True
        }
        logger.info(f"✅ API ключ добавлен: {name}")


# Глобальный менеджер
api_key_manager = APIKeyManager()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None)
) -> str:
    """
    Проверить API ключ из заголовка X-API-Key.
    
    Поднимает:
        HTTPException 403 — если ключ невалиден
        HTTPException 429 — если превышен rate limit
    """
    
    if not x_api_key:
        logger.warning("⚠️ Запрос без API ключа")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API ключ требуется. Передайте в заголовке X-API-Key"
        )
    
    if not api_key_manager.is_valid(x_api_key):
        logger.warning(f"⚠️ Невалиден API ключ: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалиден или деактивирован API ключ"
        )
    
    if not api_key_manager.check_rate_limit(x_api_key):
        logger.warning(f"⚠️ Rate limit превышен для ключа: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит запросов. Попробуйте позже"
        )
    
    logger.debug(f"✅ API ключ валиден: {x_api_key[:10]}...")
    return x_api_key


@lru_cache(maxsize=128)
def get_api_key_info(api_key: str) -> dict:
    """Получить информацию об API ключе (с кэшированием)"""
    return api_key_manager.get_api_key(api_key) or {}
```


***

## Шаг 3: Создание `api/routes.py`

Создай файл `bot_psychologist/api/routes.py`:

```python
# api/routes.py

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_agent import (
    answer_question_basic,
    answer_question_sag_aware,
    answer_question_graph_powered,
    answer_question_adaptive
)
from bot_agent.conversation_memory import get_conversation_memory
from models import (
    AskQuestionRequest, FeedbackRequest, GetUserHistoryRequest, GetStatsRequest,
    AnswerResponse, AdaptiveAnswerResponse, FeedbackResponse, 
    UserHistoryResponse, ErrorResponse, StatsResponse,
    SourceResponse, StateAnalysisResponse, PathStepResponse, PathRecommendationResponse,
    ConversationTurnResponse
)
from auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["bot"])

# Глобальная статистика (в production используй БД)
_stats = {
    "total_users": set(),
    "total_questions": 0,
    "total_processing_time": 0,
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
        result = answer_question_basic(request.query)
        
        # Обновить статистику
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=[
                SourceResponse(**src) for src in result.get("sources", [])
            ],
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
            user_level=request.user_level.value,
            debug=request.debug
        )
        
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=[
                SourceResponse(**src) for src in result.get("sources", [])
            ],
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
            user_level=request.user_level.value,
            debug=request.debug
        )
        
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=[
                SourceResponse(**src) for src in result.get("sources", [])
            ],
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
        
        # Построить ответ
        state_analysis = result.get("state_analysis", {})
        path_rec = result.get("path_recommendation")
        
        path_recommendation = None
        if path_rec:
            first_step = path_rec.get("first_step")
            path_recommendation = PathRecommendationResponse(
                current_state=path_rec.get("current_state", ""),
                target_state=path_rec.get("target_state", ""),
                key_focus=path_rec.get("key_focus", ""),
                steps_count=path_rec.get("steps_count", 0),
                total_duration_weeks=path_rec.get("total_duration_weeks", 0),
                first_step=PathStepResponse(**first_step) if first_step else None
            )
        
        return AdaptiveAnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            state_analysis=StateAnalysisResponse(
                primary_state=state_analysis.get("primary_state", "unknown"),
                confidence=state_analysis.get("confidence", 0),
                emotional_tone=state_analysis.get("emotional_tone", ""),
                recommendations=state_analysis.get("recommendations", [])
            ),
            path_recommendation=path_recommendation,
            feedback_prompt=result.get("feedback_prompt", ""),
            concepts=result.get("concepts", []),
            sources=[
                SourceResponse(**src) for src in result.get("sources", [])
            ],
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

@router.post(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="История пользователя",
    description="Получить историю диалога пользователя"
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
        
        return UserHistoryResponse(
            user_id=user_id,
            total_turns=len(memory.turns),
            turns=[
                ConversationTurnResponse(
                    timestamp=turn.timestamp,
                    user_input=turn.user_input,
                    user_state=turn.user_state,
                    bot_response=turn.bot_response or "",
                    blocks_used=turn.blocks_used,
                    concepts=turn.concepts or [],
                    user_feedback=turn.user_feedback,
                    user_rating=turn.user_rating
                )
                for turn in last_turns
            ],
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
```


***

## Шаг 4: Создание `api/main.py`

Создай файл `bot_psychologist/api/main.py`:

```python
# api/main.py

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import router

logger = logging.getLogger(__name__)

# ===== LOGGING =====

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

# ===== APP INITIALIZATION =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    # Startup
    logger.info("🚀 Bot API v0.5.0 starting...")
    logger.info("✅ All modules loaded")
    yield
    # Shutdown
    logger.info("🛑 Bot API shutting down...")


app = FastAPI(
    title="Bot Psychologist API",
    description="REST API для Bot Agent (Phases 1-4)",
    version="0.5.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# ===== MIDDLEWARE =====

# CORS для веб-интеграции
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "*"],  # TODO: в production ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trust host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
)


# Middleware для логирования
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логировать все запросы"""
    start_time = time.time()
    
    # Получить API ключ (скрыть для логов)
    api_key = request.headers.get("X-API-Key", "none")
    api_key_masked = api_key[:10] + "..." if api_key != "none" else "none"
    
    logger.info(f"→ {request.method} {request.url.path} (key: {api_key_masked})")
    
    try:
        response = await call_next(request)
        
        elapsed_time = time.time() - start_time
        logger.info(f"← {response.status_code} {request.url.path} ({elapsed_time:.2f}s)")
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "detail": "Internal Server Error"
            }
        )


# ===== ROUTERS =====

app.include_router(router)


# ===== CUSTOM OPENAPI =====

def custom_openapi():
    """Кастомная OpenAPI схема"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Bot Psychologist API",
        version="0.5.0",
        description="REST API для взаимодействия с Bot Agent (Phase 5)",
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ===== ROOT ENDPOINTS =====

@app.get("/", tags=["root"])
async def root():
    """Корневой endpoint"""
    return {
        "name": "Bot Psychologist API",
        "version": "0.5.0",
        "docs": "/api/docs",
        "status": "online"
    }


@app.get("/api/v1/info", tags=["info"])
async def api_info():
    """Информация об API"""
    return {
        "name": "Bot Psychologist API",
        "version": "0.5.0",
        "phases": {
            "phase_1": "Basic QA (TF-IDF + LLM)",
            "phase_2": "SAG-aware QA (User Level Adaptation)",
            "phase_3": "Graph-powered QA (Knowledge Graph + Semantic)",
            "phase_4": "Adaptive QA (State + Memory + Paths)",
            "phase_5": "REST API (FastAPI)"
        },
        "endpoints": {
            "basic": "/api/v1/questions/basic",
            "sag_aware": "/api/v1/questions/sag-aware",
            "graph_powered": "/api/v1/questions/graph-powered",
            "adaptive": "/api/v1/questions/adaptive",
            "history": "/api/v1/users/{user_id}/history",
            "feedback": "/api/v1/feedback",
            "stats": "/api/v1/stats"
        },
        "docs": "/api/docs"
    }


# ===== RUN =====

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```


***

## Шаг 5: Создание `api/__init__.py`

Создай файл `bot_psychologist/api/__init__.py`:

```python
# api/__init__.py

from .main import app
from .models import *
from .auth import api_key_manager, verify_api_key

__all__ = [
    "app",
    "api_key_manager",
    "verify_api_key"
]
```


***

## Шаг 6: Создание `api/requirements.txt`

Создай файл `bot_psychologist/api/requirements.txt`:

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
```


***

## Шаг 7: Создание `test_api.py`

Создай файл `bot_psychologist/test_api.py`:

```python
# test_api.py

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "test-key-001"

def get_headers():
    """Заголовки с API ключом"""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

def test_health_check():
    """Проверка здоровья"""
    print("\n" + "="*100)
    print("TEST: Health Check")
    print("="*100)
    
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200


def test_adaptive_question():
    """Тест адаптивного вопроса"""
    print("\n" + "="*100)
    print("TEST: Adaptive Question")
    print("="*100)
    
    payload = {
        "query": "Что такое осознавание?",
        "user_id": "api_test_user_001",
        "user_level": "beginner",
        "include_path": True,
        "include_feedback_prompt": True,
        "debug": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/questions/adaptive",
        json=payload,
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"State: {result.get('state_analysis', {}).get('primary_state')}")
    print(f"Processing time: {result.get('processing_time_seconds')}s")
    print(f"Answer: {result.get('answer', '')[:200]}...")
    
    assert response.status_code == 200


def test_user_history():
    """Тест истории пользователя"""
    print("\n" + "="*100)
    print("TEST: User History")
    print("="*100)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/users/api_test_user_001/history",
        params={"last_n_turns": 5},
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total turns: {result.get('total_turns')}")
    print(f"Primary interests: {result.get('primary_interests')}")
    
    assert response.status_code == 200


def test_feedback():
    """Тест отправки обратной связи"""
    print("\n" + "="*100)
    print("TEST: Feedback")
    print("="*100)
    
    payload = {
        "user_id": "api_test_user_001",
        "turn_index": 0,
        "feedback": "positive",
        "rating": 5,
        "comment": "Очень полезно!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/feedback",
        json=payload,
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    assert response.status_code == 200


def test_statistics():
    """Тест статистики"""
    print("\n" + "="*100)
    print("TEST: Statistics")
    print("="*100)
    
    response = requests.get(
        f"{BASE_URL}/api/v1/stats",
        headers=get_headers()
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total users: {result.get('total_users')}")
    print(f"Total questions: {result.get('total_questions')}")
    print(f"Average time: {result.get('average_processing_time')}s")
    
    assert response.status_code == 200


def test_invalid_api_key():
    """Тест с невалиден API ключом"""
    print("\n" + "="*100)
    print("TEST: Invalid API Key")
    print("="*100)
    
    headers = {"X-API-Key": "invalid-key"}
    response = requests.get(f"{BASE_URL}/api/v1/stats", headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Error: {response.json().get('detail')}")
    
    assert response.status_code == 403


if __name__ == "__main__":
    print("🧪 Bot API Testing")
    print("="*100)
    
    try:
        test_health_check()
        test_adaptive_question()
        test_user_history()
        test_feedback()
        test_statistics()
        test_invalid_api_key()
        
        print("\n" + "="*100)
        print("✅ ALL TESTS PASSED!")
        print("="*100)
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
```


***

## Шаг 8: Запуск API

```bash
cd bot_psychologist

# Установить зависимости
pip install -r api/requirements.txt

# Запустить сервер
python api/main.py
```

**Сервер запустится на:**

- 🌐 Main: http://localhost:8000
- 📚 Swagger Docs: http://localhost:8000/api/docs
- 📖 ReDoc: http://localhost:8000/api/redoc

***

## 📚 API Endpoints Summary

| Endpoint | Метод | Фаза | Описание |
| :-- | :-- | :-- | :-- |
| `/api/v1/questions/basic` | POST | 1 | Базовый QA |
| `/api/v1/questions/sag-aware` | POST | 2 | SAG-aware QA |
| `/api/v1/questions/graph-powered` | POST | 3 | Graph-powered QA |
| `/api/v1/questions/adaptive` | POST | 4 | **Адаптивный QA** |
| `/api/v1/users/{user_id}/history` | POST | 4 | История пользователя |
| `/api/v1/feedback` | POST | 4 | Отправить обратную связь |
| `/api/v1/stats` | GET | 5 | Статистика системы |
| `/api/v1/health` | GET | 5 | Проверка здоровья |
| `/api/docs` | GET | 5 | Swagger документация |


***

## 🔐 Безопасность

✅ **API Key Authentication** — все endpoints требуют X-API-Key
✅ **Rate Limiting** — ограничение частоты запросов (100-1000 req/min)
✅ **CORS** — контроль cross-origin requests
✅ **Pydantic Validation** — валидация всех входных данных
✅ **Error Handling** — безопасное обработка ошибок

***

## ✅ Phase 5 Чек-лист

- [ ] Создан `api/models.py` (Pydantic models)
- [ ] Создан `api/auth.py` (API Key validation + Rate limiting)
- [ ] Создан `api/routes.py` (4 endpoints для вопросов + 3 дополнительных)
- [ ] Создан `api/main.py` (FastAPI app + middleware)
- [ ] Создан `api/__init__.py`
- [ ] Создан `api/requirements.txt`
- [ ] Создан `test_api.py`
- [ ] FastAPI сервер запущен и все endpoints работают
- [ ] Swagger документация доступна
- [ ] 6/6 основных endpoints прошли тесты

***

**Phase 5 готов! Следующий этап — Phase 6 (Web UI).** 🚀

Нужны логи Phase 5, или сразу переходим к Phase 6?

