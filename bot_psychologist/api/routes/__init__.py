"""Пакет API-роутов и совместимый фасад для тестовых контрактов."""

from __future__ import annotations

from fastapi import APIRouter

from bot_agent import answer_question_adaptive as _default_answer_question_adaptive
from bot_agent.config import config

from . import chat as _chat
from . import common as _common
from .chat import router as chat_router
from .common import _build_turn_diff
from .feedback import router as feedback_router
from .health import health_check, router as health_router
from .identity_routes import router as identity_router
from .users import router as users_router

# Совместимый экспорт для monkeypatch(routes.answer_question_adaptive)
answer_question_adaptive = _default_answer_question_adaptive
stream_answer_tokens = _chat.stream_answer_tokens

# Совместимые статистические маркеры для старых тест-контрактов.
_STATS_USER_LIMIT = _common._STATS_USER_LIMIT
_stats = _common._stats
_seen_users = _common._seen_users


def _record_user(user_id: str) -> None:
    """Совместимый счетчик пользователей для тест-контрактов."""
    global _seen_users
    if user_id in _seen_users:
        return
    if len(_seen_users) >= _STATS_USER_LIMIT:
        _seen_users.clear()
    _seen_users.add(user_id)
    _stats["total_users_approx"] += 1
    _common._seen_users = _seen_users
    _common._stats = _stats


# Экспортируем оригинальные endpoint-функции с сохранением сигнатур.
ask_adaptive_question = _chat.ask_adaptive_question
ask_adaptive_question_stream = _chat.ask_adaptive_question_stream


router = APIRouter()
router.include_router(chat_router)
router.include_router(users_router)
router.include_router(feedback_router)
router.include_router(identity_router)
router.include_router(health_router)

__all__ = [
    "router",
    "ask_adaptive_question",
    "ask_adaptive_question_stream",
    "answer_question_adaptive",
    "stream_answer_tokens",
    "config",
    "_STATS_USER_LIMIT",
    "_stats",
    "_seen_users",
    "_record_user",
    "health_check",
    "_build_turn_diff",
]
