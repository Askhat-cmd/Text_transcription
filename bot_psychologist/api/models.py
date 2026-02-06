# api/models.py
"""
Pydantic Models for Bot Psychologist API (Phase 5)

Request и Response модели для валидации данных API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class UserLevel(str, Enum):
    """Уровень пользователя для адаптации ответов"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FeedbackType(str, Enum):
    """Тип обратной связи"""
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
    
    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Вопрос не может быть пустым")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Что такое осознавание?",
                "user_id": "user_123",
                "user_level": "beginner",
                "include_path": True,
                "include_feedback_prompt": True,
                "debug": False
            }
        }
    }


class FeedbackRequest(BaseModel):
    """Запрос на сохранение обратной связи"""
    user_id: str = Field(..., min_length=1, max_length=100, description="ID пользователя")
    turn_index: int = Field(..., ge=0, description="Индекс хода диалога (0-based)")
    feedback: FeedbackType = Field(..., description="Тип обратной связи")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Рейтинг (1-5)")
    comment: Optional[str] = Field(default=None, max_length=500, description="Комментарий пользователя")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_123",
                "turn_index": 0,
                "feedback": "positive",
                "rating": 5,
                "comment": "Очень помогло!"
            }
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
    start: Any  # Can be int (seconds) or str (timecode like '00:08:00')
    end: Any    # Can be int (seconds) or str (timecode like '00:16:00')
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
    first_step: Optional[PathStepResponse] = None


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
    path_recommendation: Optional[PathRecommendationResponse] = None
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
    user_state: Optional[str] = None
    bot_response: str
    blocks_used: int
    concepts: List[str]
    user_feedback: Optional[str] = None
    user_rating: Optional[int] = None


class UserHistoryResponse(BaseModel):
    """История пользователя"""
    user_id: str
    total_turns: int
    turns: List[ConversationTurnResponse]
    primary_interests: List[str]
    average_rating: float
    last_interaction: Optional[str] = None


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
    detail: Optional[str] = None
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


