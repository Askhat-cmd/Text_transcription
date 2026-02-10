# api/models.py
"""
Pydantic Models for Bot Psychologist API (Phase 5)

Request Рё Response РјРѕРґРµР»Рё РґР»СЏ РІР°Р»РёРґР°С†РёРё РґР°РЅРЅС‹С… API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class UserLevel(str, Enum):
    """РЈСЂРѕРІРµРЅСЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РґР»СЏ Р°РґР°РїС‚Р°С†РёРё РѕС‚РІРµС‚РѕРІ"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FeedbackType(str, Enum):
    """РўРёРї РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ===== REQUEST MODELS =====

class AskQuestionRequest(BaseModel):
    """Р—Р°РїСЂРѕСЃ РЅР° РѕС‚РІРµС‚ РЅР° РІРѕРїСЂРѕСЃ"""
    query: str = Field(..., min_length=3, max_length=500, description="Р’РѕРїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ")
    user_id: str = Field(default="default", min_length=1, max_length=100, description="ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ")
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=100, description="ID chat session")
    user_level: UserLevel = Field(default=UserLevel.BEGINNER, description="РЈСЂРѕРІРµРЅСЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ")
    include_path: bool = Field(default=True, description="Р’РєР»СЋС‡РёС‚СЊ СЂРµРєРѕРјРµРЅРґР°С†РёСЋ РїСѓС‚Рё")
    include_feedback_prompt: bool = Field(default=True, description="Р’РєР»СЋС‡РёС‚СЊ Р·Р°РїСЂРѕСЃ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё")
    debug: bool = Field(default=False, description="РћС‚Р»Р°РґРѕС‡РЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ")
    
    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Р’РѕРїСЂРѕСЃ РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
                "user_id": "user_123",
                "session_id": "chat_abc",
                "user_level": "beginner",
                "include_path": True,
                "include_feedback_prompt": True,
                "debug": False
            }
        }
    }


class FeedbackRequest(BaseModel):
    """Р—Р°РїСЂРѕСЃ РЅР° СЃРѕС…СЂР°РЅРµРЅРёРµ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё"""
    user_id: str = Field(..., min_length=1, max_length=100, description="ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ")
    turn_index: int = Field(..., ge=0, description="РРЅРґРµРєСЃ С…РѕРґР° РґРёР°Р»РѕРіР° (0-based)")
    feedback: FeedbackType = Field(..., description="РўРёРї РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Р РµР№С‚РёРЅРі (1-5)")
    comment: Optional[str] = Field(default=None, max_length=500, description="РљРѕРјРјРµРЅС‚Р°СЂРёР№ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_123",
                "turn_index": 0,
                "feedback": "positive",
                "rating": 5,
                "comment": "РћС‡РµРЅСЊ РїРѕРјРѕРіР»Рѕ!"
            }
        }
    }


class GetUserHistoryRequest(BaseModel):
    """Р—Р°РїСЂРѕСЃ РЅР° РёСЃС‚РѕСЂРёСЋ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    user_id: str = Field(..., min_length=1, max_length=100, description="ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ")
    last_n_turns: int = Field(default=10, ge=1, le=50, description="РџРѕСЃР»РµРґРЅРёРµ N РѕР±РѕСЂРѕС‚РѕРІ")


class GetStatsRequest(BaseModel):
    """Р—Р°РїСЂРѕСЃ РЅР° СЃС‚Р°С‚РёСЃС‚РёРєСѓ"""
    user_id: Optional[str] = Field(default=None, description="ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)")
    time_range_days: int = Field(default=30, ge=1, le=365, description="Р’СЂРµРјРµРЅРЅРѕР№ РґРёР°РїР°Р·РѕРЅ (РґРЅРё)")


# ===== RESPONSE MODELS =====

class SourceResponse(BaseModel):
    """РСЃС‚РѕС‡РЅРёРє (Р±Р»РѕРє)"""
    block_id: str
    title: str
    youtube_link: str
    start: Any  # Can be int (seconds) or str (timecode like '00:08:00')
    end: Any    # Can be int (seconds) or str (timecode like '00:16:00')
    block_type: str
    complexity_score: float


class StateAnalysisResponse(BaseModel):
    """РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    primary_state: str
    confidence: float
    emotional_tone: str
    recommendations: List[str]


class PathStepResponse(BaseModel):
    """РћРґРёРЅ С€Р°Рі РїСѓС‚Рё"""
    step_number: int
    title: str
    duration_weeks: int
    practices: List[str]
    key_concepts: List[str]


class PathRecommendationResponse(BaseModel):
    """Р РµРєРѕРјРµРЅРґР°С†РёСЏ РїСѓС‚Рё"""
    current_state: str
    target_state: str
    key_focus: str
    steps_count: int
    total_duration_weeks: int
    first_step: Optional[PathStepResponse] = None


class AnswerResponse(BaseModel):
    """РћС‚РІРµС‚ РЅР° РІРѕРїСЂРѕСЃ (С„Р°Р·Р° 1-3)"""
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


class AdaptiveAnswerResponse(BaseModel):
    """РђРґР°РїС‚РёРІРЅС‹Р№ РѕС‚РІРµС‚ (С„Р°Р·Р° 4)"""
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
    timestamp: str
    processing_time_seconds: float


class ConversationTurnResponse(BaseModel):
    """РћРґРёРЅ С…РѕРґ РґРёР°Р»РѕРіР°"""
    timestamp: str
    user_input: str
    user_state: Optional[str] = None
    bot_response: str
    blocks_used: int
    concepts: List[str]
    user_feedback: Optional[str] = None
    user_rating: Optional[int] = None


class UserHistoryResponse(BaseModel):
    """РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    user_id: str
    total_turns: int
    turns: List[ConversationTurnResponse]
    primary_interests: List[str]
    average_rating: float
    last_interaction: Optional[str] = None


class UserSummaryResponse(BaseModel):
    """РљСЂР°С‚РєРѕРµ СЂРµР·СЋРјРµ РёСЃС‚РѕСЂРёРё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    user_id: str
    total_turns: int
    primary_interests: List[str]
    num_challenges: int
    num_breakthroughs: int
    average_rating: float
    user_level: str
    last_interaction: Optional[str] = None


class DeleteHistoryResponse(BaseModel):
    """РћС‚РІРµС‚ РЅР° РѕС‡РёСЃС‚РєСѓ РёСЃС‚РѕСЂРёРё"""
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
    """РЎРѕСЃС‚РѕСЏРЅРёРµ РїРµСЂСЃРёСЃС‚РµРЅС‚РЅРѕР№ СЃРµСЃСЃРёРё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РІ SQLite."""
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
    """РћС‚РІРµС‚ РЅР° Р°СЂС…РёРІРёСЂРѕРІР°РЅРёРµ СЃС‚Р°СЂС‹С… СЃРµСЃСЃРёР№."""
    status: str
    archived_count: int
    deleted_count: int
    active_days: int
    archive_days: int
    db_path: str


class FeedbackResponse(BaseModel):
    """РћС‚РІРµС‚ РЅР° РѕС‚РїСЂР°РІРєСѓ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё"""
    status: str
    message: str
    user_id: str
    turn_index: int


class HealthCheckResponse(BaseModel):
    """РџСЂРѕРІРµСЂРєР° Р·РґРѕСЂРѕРІСЊСЏ"""
    status: str
    version: str
    timestamp: str
    uptime_seconds: float
    modules: Dict[str, bool]


class ErrorResponse(BaseModel):
    """РћС€РёР±РєР°"""
    status: str
    error: str
    detail: Optional[str] = None
    timestamp: str


class StatsResponse(BaseModel):
    """РЎС‚Р°С‚РёСЃС‚РёРєР°"""
    total_users: int
    total_questions: int
    average_processing_time: float
    top_states: Dict[str, int]
    top_interests: List[str]
    feedback_stats: Dict[str, int]
    timestamp: str


