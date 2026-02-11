# 📋 ПРД: Система Логирования для Bot Psychologist

## Product Requirements Document — Минимальная Версия v1.1


***

**Версия:** 1.1 (адаптировано под bot_psychologist)
**Дата:** 10 февраля 2026
**Область:** Фаза 1 — Базовое Логирование
**Срок:** 🚀 **1-2 дня**
**Приоритет:** P0 (Критично)

***

## 🎯 Краткое Описание

### Цель

Внедрить **минимально жизнеспособную систему логирования** для отладки логики AI-бота-психолога, учитывающую специфику проекта (4 фазы обработки запросов, адаптивный pipeline, semantic memory).

### Что Включено (MVP)

✅ Логирование в файлы (app.log, error.log, retrieval.log)
✅ Автоматическая ротация (ежедневно, хранение 30 дней)
✅ Цветной вывод в консоль для разработки
✅ Интеграция в ключевые модули проекта
✅ Логирование retrieval pipeline с диагностикой
✅ Логирование работы с сессиями и памятью
✅ Русские комментарии где возможно

### Что НЕ Включено (Позже)

❌ JSON структурированные логи
❌ Метрики производительности
❌ Отслеживание контекста (user_id в каждой записи)
❌ Отдельные debug логгеры
❌ Мониторинг/алерты
❌ Внешние интеграции (Sentry, DataDog)

### ROI

- **Время реализации:** 3-4 часа
- **Ускорение отладки:** 60-80%
- **Стоимость:** \$0 (только stdlib)

***

## 📊 Цели и Требования

### Обязательно (P0)

| ID | Требование | Усилия |
| :-- | :-- | :-- |
| R1 | Логи в файлы (не теряются при рестарте) | 30 мин |
| R2 | Ротация (ежедневно, 30 дней хранения) | 10 мин |
| R3 | Консоль + Файл одновременно | 10 мин |
| R4 | ERROR логи в отдельный файл | 10 мин |
| R5 | Интеграция в api/main.py | 20 мин |
| R6 | Интеграция в retriever.py | 30 мин |
| R7 | Интеграция в answer_adaptive.py | 40 мин |
| R8 | Интеграция в conversation_memory.py | 20 мин |
| R9 | Интеграция в semantic_memory.py | 20 мин |
| R10 | Логирование retrieval диагностики | 30 мин |

**Итого:** ~3.5 часа работы

***

## 🏗️ План Реализации

### Шаг 1: Создать `logging_config.py` (40 мин)

**Файл:** `bot_psychologist/logging_config.py`

```python
"""
Минимальная конфигурация логирования для production
Быстрая настройка для разработки и отладки

Создает три лог-файла:
- logs/app/bot.log - все логи INFO+
- logs/retrieval/retrieval.log - логи retrieval pipeline
- logs/error/error.log - только ERROR+
"""

import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# Конфигурация
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"

# Создание директорий
(LOG_DIR / "app").mkdir(parents=True, exist_ok=True)
(LOG_DIR / "retrieval").mkdir(parents=True, exist_ok=True)
(LOG_DIR / "error").mkdir(parents=True, exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Цветной вывод в консоль для разработки"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Голубой
        'INFO': '\033[32m',      # Зеленый
        'WARNING': '\033[33m',   # Желтый
        'ERROR': '\033[31m',     # Красный
        'CRITICAL': '\033[35m',  # Пурпурный
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Раскрасить уровень логирования
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        levelname_colored = f"{color}{record.levelname:8s}{self.COLORS['RESET']}"
        
        # Форматировать время
        time_str = self.formatTime(record, '%H:%M:%S')
        
        # Собрать сообщение
        return f"{time_str} | {levelname_colored} | {record.name:35s} | {record.getMessage()}"


def setup_logging(level=logging.INFO):
    """
    Настройка минимального production логирования
    
    Создает:
    - logs/app/bot.log          - Все INFO+ логи
    - logs/retrieval/retrieval.log - Retrieval pipeline
    - logs/error/error.log      - Только ERROR+
    - Console output (цветной)
    
    Args:
        level: Уровень логирования (по умолчанию: INFO)
    
    Использование:
        from logging_config import setup_logging
        setup_logging()
        
        logger = logging.getLogger(__name__)
        logger.info("Привет мир")
    """
    
    # Получить root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Очистить существующие handlers
    root_logger.handlers.clear()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONSOLE HANDLER (цветной)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # APP LOG (все логи)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    app_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "app" / "bot.log",
        when="midnight",        # Ротация в полночь
        interval=1,
        backupCount=30,         # Хранить 30 дней
        encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    app_handler.suffix = "%Y%m%d"  # bot.log.20260210
    root_logger.addHandler(app_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RETRIEVAL LOG (поиск и retrieval)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    retrieval_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "retrieval" / "retrieval.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    retrieval_handler.setLevel(logging.INFO)
    retrieval_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    retrieval_handler.suffix = "%Y%m%d"
    
    # Добавить фильтр только для retrieval логов
    retrieval_handler.addFilter(lambda record: 'RETRIEVAL' in record.getMessage() or 
                                               'retriever' in record.name.lower() or
                                               'stage_filter' in record.name.lower() or
                                               'confidence_scorer' in record.name.lower())
    root_logger.addHandler(retrieval_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ERROR LOG (только ошибки)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    error_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "error" / "error.log",
        when="midnight",
        interval=1,
        backupCount=90,         # Ошибки хранить дольше
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s\n'
        'Функция: %(funcName)s:%(lineno)d\n'
        'Сообщение: %(message)s\n'
        'Путь: %(pathname)s\n'
        '%(exc_info)s\n'
        '─' * 80 + '\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    error_handler.suffix = "%Y%m%d"
    root_logger.addHandler(error_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ПОДАВИТЬ ШУМНЫЕ ЛОГГЕРЫ
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("voyageai").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ЛОГИРОВАНИЕ СТАРТА
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logging.info("=" * 70)
    logging.info("✅ Система логирования инициализирована")
    logging.info(f"   Директория логов: {LOG_DIR}")
    logging.info(f"   Основной лог: logs/app/bot.log")
    logging.info(f"   Retrieval лог: logs/retrieval/retrieval.log")
    logging.info(f"   Лог ошибок: logs/error/error.log")
    logging.info(f"   Хранение: 30 дней (app), 90 дней (error)")
    logging.info("=" * 70)


def get_logger(name: str) -> logging.Logger:
    """
    Получить экземпляр логгера
    
    Использование:
        logger = get_logger(__name__)
        logger.info("Сообщение")
    """
    return logging.getLogger(name)
```

**Строк кода:** ~160 строк
**Зависимости:** только stdlib (никаких внешних пакетов)

***

### Шаг 2: Интеграция в `api/main.py` (20 мин)

**Файл:** `bot_psychologist/api/main.py`

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ В НАЧАЛО (после импортов)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import sys
from pathlib import Path

# Добавить родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_config import setup_logging, get_logger
import time

# Инициализировать логирование ОДИН РАЗ на уровне модуля
setup_logging()

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ОБНОВИТЬ ИНИЦИАЛИЗАЦИЮ APP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    """События жизненного цикла приложения"""
    # Старт
    logger.info("🚀 API Сервер запускается")
    logger.info(f"   Версия: {app.version}")
    logger.info(f"   Документация: http://localhost:8000/docs")
    
    yield
    
    # Остановка
    logger.info("🛑 API Сервер останавливается")

app = FastAPI(
    title="Bot Psychologist API",
    version="1.0.0",
    lifespan=lifespan
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ MIDDLEWARE ДЛЯ ЛОГИРОВАНИЯ ЗАПРОСОВ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов с замером времени"""
    start_time = time.time()
    
    # Логировать входящий запрос
    logger.info(f"→ {request.method} {request.url.path}")
    
    # Обработать запрос
    try:
        response = await call_next(request)
        
        # Вычислить задержку
        latency_ms = (time.time() - start_time) * 1000
        
        # Логировать ответ
        logger.info(
            f"← {request.method} {request.url.path} | "
            f"Статус: {response.status_code} | "
            f"Время: {latency_ms:.1f}ms"
        )
        
        return response
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(
            f"✗ {request.method} {request.url.path} упал после {latency_ms:.1f}ms",
            exc_info=True
        )
        raise

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Перехватить и залогировать все необработанные исключения"""
    logger.error(
        f"Необработанное исключение на {request.method} {request.url.path}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )

# ... остальной существующий код ...
```


***

### Шаг 3: Интеграция в `bot_agent/retriever.py` (30 мин)

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ В НАЧАЛО
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from logging_config import get_logger

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ОБНОВИТЬ метод retrieve()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def retrieve(self, query: str, top_k: int = 5) -> List[Block]:
    """Retrieval релевантных блоков с логированием"""
    
    # Логировать начало
    logger.info(f"[RETRIEVAL] Старт retrieval")
    logger.info(f"[RETRIEVAL]   Запрос: '{query[:80]}...'")
    logger.info(f"[RETRIEVAL]   top_k: {top_k}")
    
    try:
        # TF-IDF поиск
        logger.info("[RETRIEVAL] Запуск TF-IDF поиска...")
        tfidf_results = self._tfidf_search(query, top_k=top_k)
        
        logger.info(
            f"[RETRIEVAL] TF-IDF нашел {len(tfidf_results)} кандидатов"
        )
        
        # Логировать топ результатов со скорами
        for i, block in enumerate(tfidf_results[:3], 1):
            logger.info(
                f"[RETRIEVAL]   #{i}: score={block.score:.3f}, "
                f"block_id={block.metadata.get('block_id', 'unknown')}"
            )
        
        # Voyage rerank (с fallback)
        if self.voyage_reranker and self.voyage_reranker.enabled:
            logger.info("[RETRIEVAL] Попытка Voyage rerank...")
            try:
                reranked = self.voyage_reranker.rerank(query, tfidf_results, top_k=top_k)
                logger.info(
                    f"[RETRIEVAL] ✅ Voyage rerank успешен: {len(reranked)} блоков"
                )
                return reranked
                
            except Exception as voyage_error:
                logger.warning(
                    f"[RETRIEVAL] ⚠️  Voyage rerank упал: {voyage_error}"
                )
                logger.warning(
                    f"[RETRIEVAL] ⚠️  Fallback на TF-IDF результаты"
                )
                return tfidf_results
        else:
            logger.info("[RETRIEVAL] Voyage rerank отключен, используем TF-IDF")
            return tfidf_results
        
    except Exception as e:
        logger.error(
            f"[RETRIEVAL] ❌ Retrieval упал: {e}",
            exc_info=True
        )
        raise
```


***

### Шаг 4: Интеграция в `bot_agent/answer_adaptive.py` (40 мин)

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ В НАЧАЛО
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from logging_config import get_logger

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ОБНОВИТЬ метод answer_adaptive()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def answer_adaptive(
    self,
    user_query: str,
    user_id: str,
    session_id: str = None
) -> dict:
    """Генерация адаптивного ответа с полным логированием"""
    
    logger.info("=" * 70)
    logger.info(f"[ADAPTIVE] Новый запрос")
    logger.info(f"[ADAPTIVE]   user_id: {user_id}")
    logger.info(f"[ADAPTIVE]   session_id: {session_id}")
    logger.info(f"[ADAPTIVE]   запрос: '{user_query[:80]}...'")
    logger.info("=" * 70)
    
    try:
        # Фаза 1: Query augmentation
        logger.info("🎯 Фаза 1: Query Augmentation")
        augmented = self._augment_query(user_query, user_id, session_id)
        logger.info(f"   Расширенный запрос: '{augmented[:80]}...'")
        
        # Фаза 2: Retrieval
        logger.info("🎯 Фаза 2: Retrieval")
        blocks = self.retriever.retrieve(augmented, top_k=10)
        logger.info(f"   Получено {len(blocks)} блоков")
        
        # Фаза 3: Stage filter
        logger.info("🎯 Фаза 3: Stage Filter")
        working_state = self.get_working_state(user_id, session_id)
        filtered = self.stage_filter.filter(blocks, working_state)
        logger.info(f"   После фильтра: {len(filtered)} блоков")
        
        if len(filtered) == 0:
            logger.warning("   ⚠️  Нет блоков после фильтра! Fallback на топ-3")
            filtered = blocks[:3]
        
        # Фаза 4: Decision gate
        logger.info("🎯 Фаза 4: Decision Gate")
        decision_result = self.decision_gate.decide(user_query, filtered, working_state)
        logger.info(f"   Режим: {decision_result['recommended_mode']}")
        logger.info(f"   Правило: {decision_result.get('decision_rule_id', 'N/A')}")
        logger.info(f"   Уверенность: {decision_result.get('confidence_score', 0):.2f}")
        
        # Фаза 5: Confidence cap
        logger.info("🎯 Фаза 5: Confidence Cap")
        final_blocks = self.confidence_scorer.cap(filtered, decision_result['confidence_score'])
        logger.info(f"   Финальных блоков: {len(final_blocks)}")
        
        # Логировать детали финальных блоков
        for i, block in enumerate(final_blocks, 1):
            logger.info(
                f"   Блок #{i}: confidence={getattr(block, 'confidence', 1.0):.2f}, "
                f"block_id={block.metadata.get('block_id', 'unknown')}"
            )
        
        # Фаза 6: Генерация ответа
        logger.info("🎯 Фаза 6: Генерация Ответа")
        response = self._generate_response(
            user_query, 
            final_blocks, 
            user_id, 
            session_id,
            decision_result
        )
        
        logger.info(f"[ADAPTIVE] ✅ Ответ сгенерирован ({len(response.get('answer', ''))} символов)")
        logger.info("=" * 70)
        
        return response
        
    except Exception as e:
        logger.error(
            f"[ADAPTIVE] ❌ Не удалось сгенерировать ответ",
            exc_info=True
        )
        raise
```


***

### Шаг 5: Интеграция в `bot_agent/conversation_memory.py` (20 мин)

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ В НАЧАЛО
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from logging_config import get_logger

logger = get_logger(__name__)

# Обновить методы save_turn, load_history, clear_history

def save_turn(self, user_id: str, user_msg: str, bot_msg: str):
    """Сохранить ход диалога с логированием"""
    logger.info(f"[MEMORY] Сохранение хода для user_id={user_id}")
    try:
        # ... существующий код ...
        logger.info(f"[MEMORY] ✅ Ход сохранен (всего: {len(history)} ходов)")
    except Exception as e:
        logger.error(f"[MEMORY] ❌ Ошибка сохранения: {e}", exc_info=True)
        raise

def load_history(self, user_id: str, last_n: int = None) -> List[dict]:
    """Загрузить историю с логированием"""
    logger.info(f"[MEMORY] Загрузка истории для user_id={user_id}, last_n={last_n}")
    try:
        history = # ... существующий код ...
        logger.info(f"[MEMORY] ✅ Загружено {len(history)} ходов")
        return history
    except Exception as e:
        logger.error(f"[MEMORY] ❌ Ошибка загрузки: {e}", exc_info=True)
        return []

def clear_history(self, user_id: str):
    """Очистить историю с логированием"""
    logger.info(f"[MEMORY] Очистка истории для user_id={user_id}")
    try:
        # ... существующий код ...
        logger.info(f"[MEMORY] ✅ История очищена")
    except Exception as e:
        logger.error(f"[MEMORY] ❌ Ошибка очистки: {e}", exc_info=True)
        raise
```


***

### Шаг 6: Интеграция в `bot_agent/semantic_memory.py` (20 мин)

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ДОБАВИТЬ В НАЧАЛО
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from logging_config import get_logger

logger = get_logger(__name__)

# Обновить методы search, add_turn, rebuild

def search(self, user_id: str, query: str, top_k: int = 3) -> List[dict]:
    """Поиск релевантных обменов с логированием"""
    logger.info(f"[SEMANTIC] Поиск для user_id={user_id}, query='{query[:50]}...'")
    try:
        results = # ... существующий код ...
        logger.info(f"[SEMANTIC] ✅ Найдено {len(results)} релевантных обменов")
        for i, r in enumerate(results, 1):
            logger.info(f"[SEMANTIC]   #{i}: similarity={r['similarity']:.3f}")
        return results
    except Exception as e:
        logger.error(f"[SEMANTIC] ❌ Ошибка поиска: {e}", exc_info=True)
        return []

def add_turn(self, user_id: str, user_msg: str, bot_msg: str):
    """Добавить ход в семантическую память с логированием"""
    logger.info(f"[SEMANTIC] Добавление хода для user_id={user_id}")
    try:
        # ... существующий код ...
        logger.info(f"[SEMANTIC] ✅ Ход добавлен")
    except Exception as e:
        logger.error(f"[SEMANTIC] ❌ Ошибка добавления: {e}", exc_info=True)
```


***

### Шаг 7: Добавить `.gitignore` (5 мин)

**Файл:** `bot_psychologist/.gitignore` (добавить)

```bash
# Логи
logs/*.log
logs/**/*.log
logs/**/*.log.*

# Сохранить структуру директорий
!logs/.gitkeep
!logs/app/.gitkeep
!logs/retrieval/.gitkeep
!logs/error/.gitkeep
```

**Создать .gitkeep файлы:**

```bash
touch bot_psychologist/logs/.gitkeep
touch bot_psychologist/logs/app/.gitkeep
touch bot_psychologist/logs/retrieval/.gitkeep
touch bot_psychologist/logs/error/.gitkeep
```


***

## 🧪 Тестирование

### Ручное тестирование (15 мин)

```bash
# 1. Запустить сервер
cd bot_psychologist
python -m uvicorn api.main:app --reload --port 8000

# Ожидаемый вывод:
# ======================================================================
# ✅ Система логирования инициализирована
#    Директория логов: /path/to/bot_psychologist/logs
#    Основной лог: logs/app/bot.log
#    Retrieval лог: logs/retrieval/retrieval.log
#    Лог ошибок: logs/error/error.log
#    Хранение: 30 дней (app), 90 дней (error)
# ======================================================================
# 🚀 API Сервер запускается
#    Версия: 1.0.0
#    Документация: http://localhost:8000/docs

# 2. Отправить тестовый запрос
curl -X POST http://localhost:8000/api/v1/questions/adaptive \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "что такое осознанность?", "user_id": "test_user"}'

# 3. Проверить логи
tail -f logs/app/bot.log

# Ожидается:
# 2026-02-10 17:00:01 | INFO     | api.main                            | → POST /api/v1/questions/adaptive
# 2026-02-10 17:00:01 | INFO     | bot_agent.answer_adaptive           | [ADAPTIVE] Новый запрос
# 2026-02-10 17:00:01 | INFO     | bot_agent.retriever                 | [RETRIEVAL] Старт retrieval
# ...

# 4. Проверить retrieval лог
tail -f logs/retrieval/retrieval.log

# 5. Вызвать ошибку для теста error.log
# (сделать невалидный запрос)

tail -f logs/error/error.log
```


### Чек-лист валидации

```
✅ Появляется сообщение инициализации логирования
✅ Консоль показывает цветной вывод
✅ logs/app/bot.log создан и содержит записи
✅ logs/retrieval/retrieval.log создан
✅ logs/error/error.log создан
✅ Запросы логируются (→ POST /path)
✅ Ответы логируются (← POST /path | Статус: 200)
✅ Шаги retrieval видны
✅ Ошибки попадают в error.log со stack traces
✅ Старые логи ротируются (тест: touch -t 202601010000 logs/app/bot.log)
```


***

## 📁 Структура Файлов

### Новые файлы

```
bot_psychologist/
├── logging_config.py          ← НОВЫЙ (~160 строк)
├── logs/                       ← НОВЫЙ
│   ├── .gitkeep
│   ├── app/
│   │   ├── .gitkeep
│   │   └── bot.log            ← Создается при первом запуске
│   ├── retrieval/
│   │   ├── .gitkeep
│   │   └── retrieval.log      ← Создается при первом retrieval
│   └── error/
│       ├── .gitkeep
│       └── error.log          ← Создается при первой ошибке
```


### Измененные файлы

```
bot_psychologist/
├── api/
│   └── main.py                ← Изменен (+50 строк)
├── bot_agent/
│   ├── retriever.py           ← Изменен (+35 строк)
│   ├── answer_adaptive.py     ← Изменен (+50 строк)
│   ├── conversation_memory.py ← Изменен (+15 строк)
│   └── semantic_memory.py     ← Изменен (+15 строк)
└── .gitignore                 ← Изменен (+10 строк)
```

**Всего изменений:**

- Новое: 160 строк (logging_config.py)
- Изменено: 175 строк (6 файлов)
- **Итого: 335 строк кода**

***

## ✅ Критерии Приемки

### Обязательно Пройти

- [ ] ✅ `logging_config.py` существует и импортируется
- [ ] ✅ `setup_logging()` выполняется без ошибок
- [ ] ✅ `logs/app/bot.log` создается после первого запроса
- [ ] ✅ `logs/retrieval/retrieval.log` создается после retrieval
- [ ] ✅ `logs/error/error.log` создается после первой ошибки
- [ ] ✅ Консоль показывает цветные логи
- [ ] ✅ Файловые логи включают timestamp, level, logger name, message
- [ ] ✅ Ротация работает (файлы именуются `bot.log.YYYYMMDD`)
- [ ] ✅ API запросы логируются (входящие + исходящие с latency)
- [ ] ✅ Шаги retrieval видны в логах
- [ ] ✅ Работа с памятью логируется
- [ ] ✅ Ошибки логируются со stack traces
- [ ] ✅ Нет деградации производительности (<5% overhead)


### Метрики успеха

```python
# После 1 дня использования:
{
    "logs_created": True,
    "log_entries_count": ">200",
    "retrieval_logs_count": ">50",
    "errors_caught": ">0",
    "debug_time_reduction": ">60%",
    "developer_satisfaction": "😊👍",
}
```


***

## 🚀 Быстрый Старт

### Команды для реализации (готовы к копированию)

```bash
# 1. Создать logging_config.py
cd bot_psychologist
cat > logging_config.py << 'EOF'
# ... (скопировать код из Шага 1 выше)
EOF

# 2. Создать директории логов
mkdir -p logs/app logs/retrieval logs/error
touch logs/.gitkeep logs/app/.gitkeep logs/retrieval/.gitkeep logs/error/.gitkeep

# 3. Обновить .gitignore
cat >> .gitignore << 'EOF'
# Логи
logs/*.log
logs/**/*.log
logs/**/*.log.*
!logs/.gitkeep
!logs/app/.gitkeep
!logs/retrieval/.gitkeep
!logs/error/.gitkeep
EOF

# 4. Обновить файлы (вручную - см. шаги 2-6 выше)
# - api/main.py
# - bot_agent/retriever.py
# - bot_agent/answer_adaptive.py
# - bot_agent/conversation_memory.py
# - bot_agent/semantic_memory.py

# 5. Тест
python -m uvicorn api.main:app --reload --port 8000

# 6. Проверить логи
tail -f logs/app/bot.log
tail -f logs/retrieval/retrieval.log
```


***

## 📊 Сравнение: Минимальный vs Полный ПРД

| Функция | Минимальный ПРД | Полный ПРД |
| :-- | :-- | :-- |
| **Время реализации** | 3-4 часа | 4-6 дней |
| **Строк кода** | ~335 | ~2000 |
| **Файловые логи** | app, retrieval, error | app, api, retrieval, memory, error, debug |
| **Ротация** | Ежедневно | Ежедневно + По размеру |
| **Вывод в консоль** | Цветной | Цветной + JSON |
| **Отслеживание контекста** | ❌ | ✅ user_id, session_id |
| **Логи производительности** | ❌ | ✅ Latency, метрики |
| **JSON формат** | ❌ | ✅ Опционально |
| **Debug логгеры** | ❌ | ✅ retrieval, conversation, decision |
| **Скрипты мониторинга** | ❌ | ✅ Анализ ошибок, алерты |
| **Документация** | Этот ПРД | Полная документация + runbook |


***

## 🎯 Следующие Шаги (Будущее)

После стабилизации логики бота (1-2 недели), можно расширить до полного ПРД:

### Фаза 2 (Позже)

- JSON структурированное логирование
- Отслеживание контекста (user_id, session_id)
- Метрики производительности
- Debug логгеры (отдельные файлы)


### Фаза 3 (Будущее)

- Скрипты мониторинга
- Интеграция алертов (Slack/Telegram)
- Агрегация ошибок
- Dashboard в реальном времени

**Но СЕЙЧАС:** Минимальной версии достаточно для эффективной отладки! 🚀

***

## 📞 Поддержка

**Вопросы?**

- Ротация не работает? → Проверьте права на запись в `logs/`
- Логи не появляются? → Проверьте, что `setup_logging()` вызван
- Ошибки импорта? → Проверьте `sys.path.insert()`
- Retrieval логи пусты? → Проверьте фильтр в retrieval_handler

**Готовы начать?** Копируйте код и внедряйте! Всё готово к использованию.

***

**Статус:** ✅ Готово к реализации
**Расчетное время:** 3-4 часа
**Риск:** Низкий
**Влияние:** Высокое

🚀 **ВПЕРЕД!**
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: Minimal-PRD_-Production-Logging-Quick-Start.md

