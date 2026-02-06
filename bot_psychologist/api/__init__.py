# api/__init__.py
"""
Bot Psychologist API Module (Phase 5)

REST API для взаимодействия с Bot Agent.
"""

from .main import app
from .models import (
    UserLevel, FeedbackType,
    AskQuestionRequest, FeedbackRequest, GetUserHistoryRequest, GetStatsRequest,
    SourceResponse, StateAnalysisResponse, PathStepResponse, PathRecommendationResponse,
    AnswerResponse, AdaptiveAnswerResponse, ConversationTurnResponse,
    UserHistoryResponse, FeedbackResponse, HealthCheckResponse, ErrorResponse, StatsResponse
)
from .auth import api_key_manager, verify_api_key

__version__ = "0.5.0"

__all__ = [
    # App
    "app",
    # Auth
    "api_key_manager",
    "verify_api_key",
    # Enums
    "UserLevel",
    "FeedbackType",
    # Request Models
    "AskQuestionRequest",
    "FeedbackRequest",
    "GetUserHistoryRequest",
    "GetStatsRequest",
    # Response Models
    "SourceResponse",
    "StateAnalysisResponse",
    "PathStepResponse",
    "PathRecommendationResponse",
    "AnswerResponse",
    "AdaptiveAnswerResponse",
    "ConversationTurnResponse",
    "UserHistoryResponse",
    "FeedbackResponse",
    "HealthCheckResponse",
    "ErrorResponse",
    "StatsResponse",
]


