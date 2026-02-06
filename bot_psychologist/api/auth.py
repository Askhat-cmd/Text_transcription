# api/auth.py
"""
API Key Authentication & Rate Limiting for Bot Psychologist API (Phase 5)

Управление API ключами, валидация и ограничение частоты запросов.
"""

import logging
from typing import Optional
from fastapi import HTTPException, status, Header
from functools import lru_cache
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
        self.request_counts: dict = {}
    
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
        self._cleanup_old_counts(now)
        
        return True
    
    def _cleanup_old_counts(self, now: datetime) -> None:
        """Очистить старые записи счетчика"""
        cutoff_time = now - timedelta(minutes=2)
        keys_to_delete = []
        
        for key in self.request_counts.keys():
            try:
                # Извлечь timestamp из ключа (формат: api_key:YYYY-MM-DD HH:MM)
                time_part = key.split(":")[-1]
                # Дополнительно проверяем формат
                if " " in time_part:
                    date_str = key.rsplit(":", 1)[-1]
                    stored_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                    if stored_time < cutoff_time:
                        keys_to_delete.append(key)
            except (ValueError, IndexError):
                # Некорректный формат — пропускаем
                pass
        
        for key in keys_to_delete:
            del self.request_counts[key]
    
    def add_api_key(self, key: str, name: str, rate_limit: int = 100) -> None:
        """Добавить новый API ключ (администратор)"""
        self.api_keys[key] = {
            "name": name,
            "created": datetime.now(),
            "rate_limit": rate_limit,
            "active": True
        }
        logger.info(f"✅ API ключ добавлен: {name}")
    
    def deactivate_api_key(self, key: str) -> bool:
        """Деактивировать API ключ"""
        if key in self.api_keys:
            self.api_keys[key]["active"] = False
            logger.info(f"⚠️ API ключ деактивирован: {key[:10]}...")
            return True
        return False


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
        logger.warning(f"⚠️ Невалидный API ключ: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалидный или деактивированный API ключ"
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


