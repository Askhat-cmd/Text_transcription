"""Service health/statistics-роуты API."""

from datetime import datetime

from fastapi import APIRouter, Depends

from bot_agent.config import config
from bot_agent.data_loader import data_loader

from ..auth import verify_api_key
from ..models import StatsResponse
from .common import _stats, logger

router = APIRouter(prefix="/api/v1", tags=["bot"])

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
        total_users=_stats["total_users_approx"],
        total_questions=_stats["total_questions"],
        average_processing_time=round(avg_time, 2),
        top_states=_stats["states_count"],
        top_interests=[],
        feedback_stats={},
        timestamp=datetime.now().isoformat()
    )

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
    
    data_source = str(getattr(config, "DATA_SOURCE", "unknown") or "unknown")
    degraded_mode = bool(getattr(config, "DEGRADED_MODE", False))
    blocks_loaded = len(getattr(data_loader, "all_blocks", []) or [])

    if degraded_mode:
        status_value = "degraded"
    elif data_source == "json_fallback":
        status_value = "degraded_fallback"
    else:
        status_value = "healthy"

    if data_source == "api":
        bot_db_api_status = "available"
    elif data_source in {"json_fallback", "degraded"}:
        bot_db_api_status = "unavailable"
    else:
        bot_db_api_status = "unknown"

    return {
        "status": status_value,
        "version": "0.6.1",
        "timestamp": datetime.now().isoformat(),
        "data_source": data_source,
        "blocks_loaded": blocks_loaded,
        "bot_data_base_api": bot_db_api_status,
        "modules": {
            "bot_agent": True,
            "conversation_memory": True,
            "state_classifier": True,
            "path_builder": True,
            "api": True,
        },
    }

