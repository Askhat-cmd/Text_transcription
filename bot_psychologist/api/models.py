# api/models.py
"""
Pydantic Models for Bot Psychologist API (Phase 5)

Request и Response модели для валидации данных API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class FeedbackType(str, Enum):
    """Тип обратной связи"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ===== REQUEST MODELS =====

class AskQuestionRequest(BaseModel):
    """Запрос на ответ на вопрос"""
    query: str = Field(..., min_length=3, max_length=2000, description="Вопрос пользователя")
    user_id: str = Field(default="default", min_length=1, max_length=100, description="ID пользователя")
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=100, description="ID chat session")
    include_path: bool = Field(default=False, description="Включить рекомендацию пути")
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
                "session_id": "chat_abc",
                "include_path": False,
                "include_feedback_prompt": True,
                "debug": False
            }
        }
    }


class FeedbackRequest(BaseModel):
    """Запрос на сохранение обратной связи"""
    user_id: str = Field(..., min_length=1, max_length=100, description="ID пользователя")
    turn_index: int = Field(..., ge=0, description="ндекс хода диалога (0-based)")
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
    """сточник (блок)"""
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
    recommended_mode: Optional[str] = None
    decision_rule_id: Optional[int] = None
    confidence_level: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any]
    timestamp: str
    processing_time_seconds: float


class ChunkTraceItem(BaseModel):
    """   ChromaDB     ."""
    block_id: str
    title: str
    emotional_tone: str = ""
    score_initial: float
    score_final: float
    passed_filter: bool
    filter_reason: str = ""
    preview: str
    text: Optional[str] = None


class MemoryTurnPreview(BaseModel):
    turn_index: int
    role: str
    text_preview: str
    state: Optional[str] = None


class SemanticHitDetail(BaseModel):
    block_id: str
    score: float
    text_preview: str
    source: Optional[str] = None


class PipelineStage(BaseModel):
    name: str
    label: str
    duration_ms: int
    skipped: bool = False


class AnomalyFlag(BaseModel):
    code: str
    severity: Literal["info", "warn", "error"]
    message: str
    target: Optional[str] = None


class StateTrajectoryPoint(BaseModel):
    turn: int
    state: str
    confidence: Optional[float] = None


class ConfigSnapshot(BaseModel):
    conversation_history_depth: int
    max_context_size: int
    semantic_search_top_k: int
    fast_path_enabled: bool
    rerank_enabled: bool
    model_name: str


class PipelineError(BaseModel):
    stage: str
    exception_type: str
    message: str
    partial_trace_available: bool


class TurnDiffMemoryDelta(BaseModel):
    turns_added: int = 0
    summary_changed: bool = False
    semantic_hits_delta: int = 0


class TurnDiff(BaseModel):
    route_changed: bool = False
    state_changed: bool = False
    config_changed_keys: List[str] = Field(default_factory=list)
    memory_delta: TurnDiffMemoryDelta = Field(default_factory=TurnDiffMemoryDelta)


class LLMCallTrace(BaseModel):
    """  LLM    ."""
    step: str
    model: str
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    duration_ms: Optional[int] = None
    system_prompt_preview: Optional[str] = None
    user_prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None
    blob_error: Optional[str] = None
    tokens_used: Optional[int] = None
    system_prompt_blob_id: Optional[str] = None
    user_prompt_blob_id: Optional[str] = None


class DebugTrace(BaseModel):
    """      ."""
    trace_contract_version: str = "v2"
    chunks_retrieved: List[ChunkTraceItem]
    chunks_after_filter: List[ChunkTraceItem] = Field(default_factory=list)
    llm_calls: List[LLMCallTrace]
    context_written_to_memory: str
    context_written: Optional[str] = None
    total_duration_ms: int
    primary_model: Optional[str] = None
    classifier_model: Optional[str] = None
    embedding_model: Optional[str] = None
    reranker_model: Optional[str] = None
    reranker_enabled: bool = False
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    session_tokens_prompt: Optional[int] = None
    session_tokens_completion: Optional[int] = None
    session_tokens_total: Optional[int] = None
    session_cost_usd: Optional[float] = None
    session_turns: Optional[int] = None
    fast_path: Optional[bool] = None
    fast_path_reason: Optional[str] = None
    decision_rule_id: Optional[str] = None
    mode_reason: Optional[str] = None
    block_cap: Optional[int] = None
    blocks_initial: Optional[int] = None
    blocks_after_cap: Optional[int] = None
    hybrid_query_preview: Optional[str] = None
    hybrid_query_text: Optional[str] = None
    hybrid_query_len: Optional[int] = None
    context_mode: Optional[str] = None
    memory_turns: Optional[int] = None
    memory_turns_content: List[MemoryTurnPreview] = Field(default_factory=list)
    summary_text: Optional[str] = None
    summary_length: Optional[int] = None
    summary_last_turn: Optional[int] = None
    summary_pending_turn: Optional[int] = None
    summary_used: Optional[bool] = None
    semantic_hits: Optional[int] = None
    semantic_hits_detail: List[SemanticHitDetail] = Field(default_factory=list)
    state_secondary: List[str] = Field(default_factory=list)
    state_trajectory: List[StateTrajectoryPoint] = Field(default_factory=list)
    pipeline_stages: List[PipelineStage] = Field(default_factory=list)
    anomalies: List[AnomalyFlag] = Field(default_factory=list)
    system_prompt_blob_id: Optional[str] = None
    user_prompt_blob_id: Optional[str] = None
    memory_snapshot_blob_id: Optional[str] = None
    config_snapshot: Optional[ConfigSnapshot] = None
    estimated_cost_usd: Optional[float] = None
    pipeline_error: Optional[PipelineError] = None
    session_id: Optional[str] = None
    turn_number: Optional[int] = None
    user_state: Optional[str] = None
    recommended_mode: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None
    informational_mode: Optional[bool] = None
    applied_mode_prompt: Optional[str] = None
    turn_diff: Optional[TurnDiff] = None


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
    recommended_mode: Optional[str] = None
    decision_rule_id: Optional[int] = None
    confidence_level: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any]
    trace: Optional[DebugTrace] = None
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
    """стория пользователя"""
    user_id: str
    total_turns: int
    turns: List[ConversationTurnResponse]
    primary_interests: List[str]
    average_rating: float
    last_interaction: Optional[str] = None


class UserSummaryResponse(BaseModel):
    """Краткое резюме истории пользователя"""
    user_id: str
    total_turns: int
    primary_interests: List[str]
    num_challenges: int
    num_breakthroughs: int
    average_rating: float
    last_interaction: Optional[str] = None


class DeleteHistoryResponse(BaseModel):
    """Ответ на очистку истории"""
    status: str
    message: str
    user_id: str


class ChatSessionInfoResponse(BaseModel):
    """Lightweight chat session item for sidebar/history."""
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    status: str
    title: str
    turns_count: int = 0
    last_user_input: Optional[str] = None
    last_bot_response: Optional[str] = None
    last_turn_timestamp: Optional[str] = None


class UserSessionsResponse(BaseModel):
    """List of chat sessions for a user."""
    user_id: str
    total_sessions: int
    sessions: List[ChatSessionInfoResponse]


class CreateSessionRequest(BaseModel):
    """Create new chat session request."""
    title: Optional[str] = Field(default=None, max_length=120)


class DeleteSessionResponse(BaseModel):
    """Delete chat session response."""
    status: str
    message: str
    user_id: str
    session_id: str


class SessionInfoResponse(BaseModel):
    """Состояние персистентной сессии пользователя в SQLite."""
    user_id: str
    enabled: bool
    exists: bool
    status: Optional[str] = None
    total_turns: int = 0
    total_embeddings: int = 0
    last_active: Optional[str] = None
    has_working_state: bool = False
    has_summary: bool = False


class ArchiveSessionsResponse(BaseModel):
    """Ответ на архивирование старых сессий."""
    status: str
    archived_count: int
    deleted_count: int
    active_days: int
    archive_days: int
    db_path: str


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


