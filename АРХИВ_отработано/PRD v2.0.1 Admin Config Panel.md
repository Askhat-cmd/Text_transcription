# PRD v2.0.1: Admin Config Panel

**Версия:** 2.0.1 (финальная, исправленная, актуальная)
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Корень проекта:** `bot_psychologist/`
**Дата:** 2026-03-06
**Статус:** Готов к реализации агентом

***

## 1. Цель

Дать разработчику возможность редактировать все управляющие параметры бота и тексты промтов прямо из браузера — без входа на сервер, без ручной правки файлов, без рестарта сервера. Изменения применяются горячо — к следующему запросу пользователя.

***

## 2. Контекст: критически важные факты о коде

Перед реализацией агент **обязан** понять и учесть следующие факты о текущем коде проекта.

### Факт 1. Атрибуты Config — class-level, не instance-level

Файл `bot_psychologist/bot_agent/config.py` содержит:

```python
class Config:
    TOP_K_BLOCKS = 5          # <- class attribute
    LLM_TEMPERATURE = 0.7     # <- class attribute
    LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")  # <- class attribute
```

Это означает: обычный `__getattr__` **никогда не сработает** для этих атрибутов, потому что Python находит их через `type(instance).__mro__` — это «нормальный» lookup. Нужен **`__getattribute__`** — он перехватывает ЛЮБОЙ доступ к атрибуту, включая классовые.

### Факт 2. Последняя строка config.py — точка входа

В самом конце `bot_psychologist/bot_agent/config.py` стоит:

```python
config = Config()
```

Все другие модули делают `from bot_agent.config import config`. Если изменить **только эту строку** — все существующие импорты автоматически получат новый класс `RuntimeConfig`. Больше ничего менять в импортах других файлов не нужно.

### Факт 3. Config содержит class-методы — их нужно исключить из перехвата

В `config.py` есть методы, которые **нельзя перехватывать** в `__getattribute__`, иначе бот сломается:

- `get_token_param_name(cls, model=None)`
- `supports_custom_temperature(cls, model=None)`
- `get_effective_max_tokens(cls, model=None)`
- `get_mode_max_tokens(cls, mode=None)`
- `get_reasoning_effort(cls, model=None)`
- `validate(cls)`
- `info(cls)`

Все они должны быть в `_BYPASS_ATTRS`.

### Факт 4. `MODE_MAX_TOKENS` — словарь, не редактируется через UI

```python
MODE_MAX_TOKENS: dict = {
    "PRESENCE": 3500,
    "CLARIFICATION": 3500,
    ...
}
```

Тип `dict` не поддерживается в текущей архитектуре override-слоя. Этот параметр **не включается** в `EDITABLE_CONFIG` — он остаётся только в `config.py`.

### Факт 5. Reasoning-модели не поддерживают температуру

Параметры `LLM_TEMPERATURE` не применяются к моделям с префиксами `gpt-5`, `o1`, `o3`, `o4`. Метод `supports_custom_temperature()` уже содержит эту логику. UI должен **визуально блокировать** поле температуры при выборе reasoning-модели.

### Факт 6. Актуальный список поддерживаемых моделей

Текущий `SUPPORTED_MODELS` в `config.py`:

```python
SUPPORTED_MODELS: tuple = (
    "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    "gpt-4o-mini",
)
```

**`gpt-4o` и `gpt-4-turbo` отсутствуют** — их нельзя использовать в `options` для select-поля.

### Факт 7. API-сервер регистрирует роутеры в `main.py`

Файл `bot_psychologist/api/main.py` регистрирует роутеры так:

```python
from .routes import router
from .debug_routes import router as debug_router

app.include_router(router)
app.include_router(debug_router)
```

Новый admin-роутер нужно добавить **по этому же паттерну** в `main.py`.

### Факт 8. `routes.py` вырос до 96KB — не трогать его

Вместо добавления кода в конец `routes.py`, нужно создать отдельный файл `bot_psychologist/api/admin_routes.py`.

### Факт 9. Десять промт-файлов присутствуют в `bot_agent/`

Все 10 `.md` файлов существуют в `bot_psychologist/bot_agent/`:

```
prompt_system_base.md
prompt_sd_green.md
prompt_sd_blue.md
prompt_sd_red.md
prompt_sd_orange.md
prompt_sd_yellow.md
prompt_sd_purple.md
prompt_system_level_beginner.md
prompt_system_level_intermediate.md
prompt_system_level_advanced.md
```


### Факт 10. Новые модули в `bot_agent/` — нужно проверить на чтение промтов

Следующие файлы появились после предыдущей версии и **обязательно** должны быть проверены на наличие прямого чтения `.md` файлов:

- `answer_adaptive.py` (~91KB)
- `answer_graph_powered.py`
- `answer_sag_aware.py`
- `path_builder.py`
- `practices_recommender.py`
- `user_level_adapter.py`
- Все файлы в `bot_agent/decision/`
- Все файлы в `bot_agent/response/`
- Все файлы в `bot_agent/retrieval/`
- Все файлы в `bot_agent/storage/`

***

## 3. Архитектура

### 3.1 Двуслойная модель данных

```
Слой 1 — ДЕФОЛТЫ (git, read-only навсегда):
  bot_agent/config.py              ← Config class attributes
  bot_agent/prompt_*.md            ← 10 файлов промтов

Слой 2 — OVERRIDES (вне git, только запись через API):
  bot_psychologist/data/admin_overrides.json
```

**Логика приоритета:** если в `admin_overrides.json` есть значение → использовать его. Нет → использовать дефолт из `config.py` или `.md`. Файлы `config.py` и `.md` **никогда не изменяются программно**.

### 3.2 Структура `admin_overrides.json`

```json
{
  "config": {
    "LLM_TEMPERATURE": 0.5,
    "TOP_K_BLOCKS": 7,
    "CLASSIFIER_MODEL": "gpt-4.1-mini"
  },
  "prompts": {
    "prompt_sd_green": "Изменённый текст промта...",
    "prompt_sd_blue": null
  },
  "meta": {
    "last_modified": "2026-03-06T11:00:00",
    "modified_by": "dev"
  },
  "history": [
    {
      "key": "LLM_TEMPERATURE",
      "type": "config",
      "old": 0.7,
      "new": 0.5,
      "timestamp": "2026-03-06T11:00:00"
    }
  ]
}
```

`null` в `prompts` означает «использовать дефолт из `.md`». `history` хранит последние 50 изменений.

### 3.3 Безопасность circular import

Изменяем **только последнюю строку** `config.py`:

```python
# БЫЛО:
config = Config()

# СТАЛО:
from .runtime_config import RuntimeConfig
config = RuntimeConfig()
```

**Почему это безопасно:** когда Python доходит до этой строки, класс `Config` уже **полностью определён** в памяти (`sys.modules`). Когда `runtime_config.py` делает `from .config import Config` — Python видит модуль `config` как частично загруженный, но имя `Config` в нём уже существует. Импорт проходит без ошибок. Это документированное поведение Python для взаимных импортов.

### 3.4 Thread safety

`RuntimeConfig` используется в конкурентной async-среде FastAPI. Кэш защищён `threading.Lock`. Блокировка удерживается только на время чтения/записи JSON (~мкс), не на время обработки запроса.

### 3.5 Кэширование на основе `mtime`

Файл `admin_overrides.json` не читается при каждом обращении к атрибуту. Вызывается только `os.path.getmtime()` (~1 мкс) — если `mtime` не изменился, возвращается кэш. После сохранения из UI кэш сбрасывается, и следующий запрос бота подхватывает новые значения.

***

## 4. Полный список файлов для создания/изменения

| \# | Файл | Действие |
| :-- | :-- | :-- |
| 1 | `bot_agent/runtime_config.py` | СОЗДАТЬ |
| 2 | `bot_agent/config.py` | ИЗМЕНИТЬ только последнюю строку |
| 3 | `bot_agent/answer_*.py` и новые модули | ПРОВЕРИТЬ и обновить чтение промтов |
| 4 | `api/admin_routes.py` | СОЗДАТЬ |
| 5 | `api/main.py` | ДОБАВИТЬ одну строку регистрации роутера |
| 6 | `data/.gitkeep` | СОЗДАТЬ |
| 7 | `.gitignore` | ДОБАВИТЬ одну строку |
| 8 | `web_ui/src/types/admin.types.ts` | СОЗДАТЬ |
| 9 | `web_ui/src/services/adminConfig.service.ts` | СОЗДАТЬ |
| 10 | `web_ui/src/hooks/useAdminConfig.ts` | СОЗДАТЬ |
| 11 | `web_ui/src/components/admin/ConfigGroupPanel.tsx` | СОЗДАТЬ |
| 12 | `web_ui/src/components/admin/PromptEditorPanel.tsx` | СОЗДАТЬ |
| 13 | `web_ui/src/components/admin/HistoryPanel.tsx` | СОЗДАТЬ |
| 14 | `web_ui/src/components/admin/AdminPanel.tsx` | СОЗДАТЬ |
| 15 | `web_ui/src/App.tsx` или роутинг | ОБНОВИТЬ — добавить маршрут к AdminPanel |


***

## 5. Бэкенд — полная реализация

### Файл 1: `bot_psychologist/bot_agent/runtime_config.py` — СОЗДАТЬ

```python
# bot_agent/runtime_config.py
"""
RuntimeConfig — горячая конфигурация с override-слоем из admin_overrides.json.

Наследует Config, перехватывает обращения к редактируемым параметрам через
__getattribute__ и возвращает override-значение если оно есть в JSON-файле.
Кэширует JSON по mtime файла — перечитывает только при изменении.
Thread-safe: кэш защищён threading.Lock.
"""

import json
import os
import tempfile
import logging
import threading
from datetime import datetime
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


class RuntimeConfig(Config):
    """
    Расширение Config с поддержкой горячего редактирования из Admin UI.

    ВАЖНО: все атрибуты в Config — class-level. Поэтому для перехвата
    используем __getattribute__ (не __getattr__), который вызывается
    при ЛЮБОМ доступе к атрибуту, включая классовые.

    Thread safety: _lock защищает _cache и _cache_mtime от race conditions
    в async FastAPI окружении.
    """

    OVERRIDES_PATH: Path = Config.PROJECT_ROOT / "data" / "admin_overrides.json"

    # ── Кэш на уровне класса (shared между всеми инстансами) ──
    _cache: dict = {}
    _cache_mtime: float = 0.0
    _lock: threading.Lock = threading.Lock()

    # ════════════════════════════════════════════════════════════
    # МЕТАДАННЫЕ РЕДАКТИРУЕМЫХ ПАРАМЕТРОВ
    # ════════════════════════════════════════════════════════════

    # Ключ — имя атрибута Config; значение — схема для UI и валидации.
    # MODE_MAX_TOKENS (dict) намеренно исключён — тип dict не поддерживается.
    EDITABLE_CONFIG: dict = {
        # ── LLM ──
        "LLM_MODEL": {
            "type": "select",
            "options": [
                "gpt-4o-mini",
                "gpt-4.1-nano",
                "gpt-4.1-mini",
                "gpt-4.1",
                "gpt-5-nano",
                "gpt-5-mini",
                "gpt-5",
                "gpt-5.1",
                "gpt-5.2",
            ],
            "group": "llm",
            "label": "Основная модель GPT",
            "note": "Reasoning-модели (gpt-5*) не поддерживают температуру",
        },
        "CLASSIFIER_MODEL": {
            "type": "select",
            "options": [
                "gpt-4o-mini",
                "gpt-4.1-nano",
                "gpt-4.1-mini",
                "gpt-4.1",
                "gpt-5-nano",
                "gpt-5-mini",
                "gpt-5",
            ],
            "group": "llm",
            "label": "Модель классификатора",
        },
        "LLM_TEMPERATURE": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "llm",
            "label": "Температура (творчество)",
            "note": "Игнорируется для reasoning-моделей (gpt-5*, o1, o3, o4)",
        },
        "LLM_MAX_TOKENS": {
            "type": "int",
            "min": 100,
            "max": 8000,
            "group": "llm",
            "label": "Макс. токенов в ответе",
        },
        "REASONING_EFFORT": {
            "type": "select",
            "options": ["low", "medium", "high"],
            "group": "llm",
            "label": "Глубина рассуждений (reasoning)",
            "note": "Применяется только для reasoning-моделей (gpt-5*, o1, o3, o4)",
        },
        "ENABLE_STREAMING": {
            "type": "bool",
            "group": "llm",
            "label": "Потоковая передача ответа (streaming)",
        },
        # ── Retrieval ──
        "TOP_K_BLOCKS": {
            "type": "int",
            "min": 1,
            "max": 20,
            "group": "retrieval",
            "label": "Кол-во блоков для контекста (TOP-K)",
        },
        "MIN_RELEVANCE_SCORE": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "retrieval",
            "label": "Мин. порог релевантности",
        },
        "VOYAGE_ENABLED": {
            "type": "bool",
            "group": "retrieval",
            "label": "Включить Voyage Rerank",
        },
        "VOYAGE_TOP_K": {
            "type": "int",
            "min": 1,
            "max": 10,
            "group": "retrieval",
            "label": "Voyage: TOP-K после ранжирования",
        },
        "VOYAGE_MODEL": {
            "type": "select",
            "options": ["rerank-2", "rerank-2-lite"],
            "group": "retrieval",
            "label": "Voyage: модель ранжировщика",
        },
        # ── Memory ──
        "CONVERSATION_HISTORY_DEPTH": {
            "type": "int",
            "min": 1,
            "max": 20,
            "group": "memory",
            "label": "Глубина истории диалога (ходов)",
        },
        "MAX_CONTEXT_SIZE": {
            "type": "int",
            "min": 500,
            "max": 8000,
            "group": "memory",
            "label": "Макс. размер контекста (символов)",
        },
        "MAX_CONVERSATION_TURNS": {
            "type": "int",
            "min": 10,
            "max": 5000,
            "group": "memory",
            "label": "Макс. ходов диалога на сессию",
        },
        "ENABLE_SEMANTIC_MEMORY": {
            "type": "bool",
            "group": "memory",
            "label": "Семантическая память",
        },
        "SEMANTIC_SEARCH_TOP_K": {
            "type": "int",
            "min": 1,
            "max": 10,
            "group": "memory",
            "label": "Семантика: TOP-K",
        },
        "SEMANTIC_MIN_SIMILARITY": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "memory",
            "label": "Семантика: мин. сходство",
        },
        "SEMANTIC_MAX_CHARS": {
            "type": "int",
            "min": 100,
            "max": 3000,
            "group": "memory",
            "label": "Семантика: макс. символов",
        },
        "ENABLE_CONVERSATION_SUMMARY": {
            "type": "bool",
            "group": "memory",
            "label": "Суммаризация диалога",
        },
        "SUMMARY_UPDATE_INTERVAL": {
            "type": "int",
            "min": 1,
            "max": 50,
            "group": "memory",
            "label": "Интервал обновления резюме (ходов)",
        },
        "SUMMARY_MAX_CHARS": {
            "type": "int",
            "min": 100,
            "max": 2000,
            "group": "memory",
            "label": "Макс. длина резюме (символов)",
        },
        # ── Storage ──
        "ENABLE_SESSION_STORAGE": {
            "type": "bool",
            "group": "storage",
            "label": "Хранить сессии пользователей",
        },
        "SESSION_RETENTION_DAYS": {
            "type": "int",
            "min": 1,
            "max": 365,
            "group": "storage",
            "label": "Хранить активные сессии (дней)",
        },
        "ARCHIVE_RETENTION_DAYS": {
            "type": "int",
            "min": 1,
            "max": 730,
            "group": "storage",
            "label": "Хранить архивные сессии (дней)",
        },
        "AUTO_CLEANUP_ENABLED": {
            "type": "bool",
            "group": "storage",
            "label": "Авто-очистка старых сессий",
        },
        # ── Runtime ──
        "WARMUP_ON_START": {
            "type": "bool",
            "group": "runtime",
            "label": "Прогрев при старте сервера (warmup)",
            "note": "Применяется только при следующем перезапуске сервера",
        },
        "ENABLE_CACHING": {
            "type": "bool",
            "group": "runtime",
            "label": "Кэширование запросов",
        },
    }

    # Список промтов доступных для редактирования
    EDITABLE_PROMPTS: list = [
        "prompt_system_base",
        "prompt_sd_green",
        "prompt_sd_blue",
        "prompt_sd_red",
        "prompt_sd_orange",
        "prompt_sd_yellow",
        "prompt_sd_purple",
        "prompt_system_level_beginner",
        "prompt_system_level_intermediate",
        "prompt_system_level_advanced",
    ]

    # Читабельные имена промтов для UI
    PROMPT_LABELS: dict = {
        "prompt_system_base":               "🧠 Системный базовый",
        "prompt_sd_green":                  "🟢 Спиральная динамика: Green",
        "prompt_sd_blue":                   "🔵 Спиральная динамика: Blue",
        "prompt_sd_red":                    "🔴 Спиральная динамика: Red",
        "prompt_sd_orange":                 "🟠 Спиральная динамика: Orange",
        "prompt_sd_yellow":                 "🟡 Спиральная динамика: Yellow",
        "prompt_sd_purple":                 "🟣 Спиральная динамика: Purple",
        "prompt_system_level_beginner":     "📗 Уровень пользователя: Начальный",
        "prompt_system_level_intermediate": "📘 Уровень пользователя: Средний",
        "prompt_system_level_advanced":     "📙 Уровень пользователя: Продвинутый",
    }

    # ── Атрибуты ПОЛНОСТЬЮ исключённые из перехвата ──
    # Сюда входят: чувствительные (API-ключи, пути), служебные (методы класса),
    # внутренние атрибуты RuntimeConfig, нередактируемые параметры.
    _BYPASS_ATTRS: frozenset = frozenset({
        "OPENAI_API_KEY", "VOYAGE_API_KEY", "BOT_DB_PATH",
        "EMBEDDING_MODEL", "PROJECT_ROOT", "BOT_AGENT_ROOT",
        "DATA_ROOT", "SAG_FINAL_DIR", "CACHE_DIR", "LOG_DIR",
        "MODE_MAX_TOKENS", "SUPPORTED_MODELS", "_MAX_COMPLETION_TOKENS_PREFIXES",
        "get_token_param_name", "supports_custom_temperature",
        "get_effective_max_tokens", "get_mode_max_tokens",
        "get_reasoning_effort", "validate", "info",
        "OVERRIDES_PATH", "EDITABLE_CONFIG", "EDITABLE_PROMPTS",
        "PROMPT_LABELS", "_BYPASS_ATTRS", "_cache", "_cache_mtime", "_lock",
        "RESPONSE_LANGUAGE",
    })


    # ════════════════════════════════════════════════════════════
    # ГОРЯЧИЙ ПЕРЕХВАТ АТРИБУТОВ
    # ════════════════════════════════════════════════════════════

    def __getattribute__(self, name: str):
        """
        Перехватывает обращения к редактируемым атрибутам конфига.
        Использует object.__getattribute__ чтобы избежать рекурсии
        при доступе к EDITABLE_CONFIG, _BYPASS_ATTRS и методам класса.
        """
        # Никогда не перехватываем приватное и специальные методы
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        # Никогда не перехватываем чувствительные / служебные атрибуты
        bypass = object.__getattribute__(self, "_BYPASS_ATTRS")
        if name in bypass:
            return object.__getattribute__(self, name)

        # Проверяем: является ли имя редактируемым параметром
        editable = object.__getattribute__(self, "EDITABLE_CONFIG")
        if name in editable:
            try:
                loader = object.__getattribute__(self, "_load_overrides")
                overrides = loader()
                cfg_ov = overrides.get("config", {})
                if name in cfg_ov:
                    meta = editable[name]
                    raw = cfg_ov[name]
                    t = meta["type"]
                    if t == "int":
                        return int(raw)
                    elif t == "float":
                        return float(raw)
                    elif t == "bool":
                        return bool(raw)
                    else:  # "select", "string"
                        return str(raw)
            except Exception as exc:
                logger.warning(
                    "[RuntimeConfig] Override read failed for '%s': %s", name, exc
                )

        return object.__getattribute__(self, name)

    # ════════════════════════════════════════════════════════════
    # КЭШИРОВАННОЕ ЧТЕНИЕ ФАЙЛА (mtime-based, thread-safe)
    # ════════════════════════════════════════════════════════════

    def _load_overrides(self) -> dict:
        """
        Читает admin_overrides.json с кэшированием по mtime.
        Перечитывает файл только если он изменился с последнего чтения.
        Thread-safe: использует _lock.
        Производительность: ~1μs (stat) если файл не менялся.
        """
        path = object.__getattribute__(self, "OVERRIDES_PATH")
        lock = object.__getattribute__(self, "_lock")

        try:
            mtime = os.path.getmtime(path)
        except FileNotFoundError:
            return {"config": {}, "prompts": {}, "meta": {}, "history": []}

        with lock:
            if mtime != RuntimeConfig._cache_mtime:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        RuntimeConfig._cache = json.load(f)
                    RuntimeConfig._cache_mtime = mtime
                except Exception as exc:
                    logger.error("[RuntimeConfig] Failed to load overrides: %s", exc)
                    return {"config": {}, "prompts": {}, "meta": {}, "history": []}
            return dict(RuntimeConfig._cache)  # shallow copy для безопасности

    def _save_overrides(self, data: dict) -> None:
        """
        Атомарная запись через tempfile + os.replace.
        Обновляет meta.last_modified, сбрасывает кэш.
        Thread-safe: использует _lock.
        """
        path = object.__getattribute__(self, "OVERRIDES_PATH")
        lock = object.__getattribute__(self, "_lock")
        path.parent.mkdir(parents=True, exist_ok=True)

        data.setdefault("config", {})
        data.setdefault("prompts", {})
        data.setdefault("history", [])
        data["meta"] = {
            "last_modified": datetime.now().isoformat(),
            "modified_by": "dev",
        }

        # Атомарная запись: пишем во временный файл рядом с целевым
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=".admin_overrides_", suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)  # атомарная замена (POSIX и Windows)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Сбрасываем кэш под блокировкой
        with lock:
            RuntimeConfig._cache_mtime = 0.0

    def _append_history(
        self, data: dict, key: str, type_: str, old, new
    ) -> None:
        """Добавляет запись в историю изменений, хранит последние 50."""
        history = data.get("history", [])
        history.append({
            "key": key,
            "type": type_,
            "old": old,
            "new": new,
            "timestamp": datetime.now().isoformat(),
        })
        data["history"] = history[-50:]

    # ════════════════════════════════════════════════════════════
    # CONFIG: PUBLIC API
    # ════════════════════════════════════════════════════════════

    def get_all_config(self) -> dict:
        """
        Возвращает все редактируемые параметры с метаданными, сгруппированные для UI.

        Returns:
            {
                "groups": {
                    "llm": {
                        "label": "🤖 LLM",
                        "params": {
                            "LLM_TEMPERATURE": {
                                "value": 0.5,
                                "default": 0.7,
                                "is_overridden": True,
                                "type": "float",
                                "min": 0.0, "max": 1.0,
                                "group": "llm",
                                "label": "...",
                                "note": "..."  # опционально
                            },
                            ...
                        }
                    },
                    ...
                }
            }
        """
        overrides = self._load_overrides().get("config", {})
        editable = object.__getattribute__(self, "EDITABLE_CONFIG")

        group_labels = {
            "llm":       "🤖 LLM",
            "retrieval": "🔍 Поиск и ретривал",
            "memory":    "🧠 Память и контекст",
            "storage":   "🗄️ Хранилище сессий",
            "runtime":   "⚙️ Runtime-параметры",
        }

        groups: dict = {}
        for key, meta in editable.items():
            group = meta["group"]
            if group not in groups:
                groups[group] = {
                    "label": group_labels.get(group, group),
                    "params": {},
                }
            default_val = getattr(Config, key, None)
            is_overridden = key in overrides
            current_val = self.__getattribute__(key)

            groups[group]["params"][key] = {
                "value": current_val,
                "default": default_val,
                "is_overridden": is_overridden,
                **meta,
            }

        return {"groups": groups}

    def set_config_override(self, key: str, value) -> dict:
        """
        Валидирует и сохраняет override параметра.

        Raises:
            ValueError: если ключ неизвестен или значение вне допустимого диапазона.
        """
        editable = object.__getattribute__(self, "EDITABLE_CONFIG")
        if key not in editable:
            raise ValueError(f"Параметр '{key}' не является редактируемым")

        meta = editable[key]
        t = meta["type"]

        if t == "int":
            value = int(value)
            if not (meta["min"] <= value <= meta["max"]):
                raise ValueError(
                    f"'{key}' должен быть в [{meta['min']}, {meta['max']}], получено {value}"
                )
        elif t == "float":
            value = float(value)
            if not (meta["min"] <= value <= meta["max"]):
                raise ValueError(
                    f"'{key}' должен быть в [{meta['min']:.2f}, {meta['max']:.2f}], "
                    f"получено {value:.2f}"
                )
        elif t == "bool":
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            else:
                value = bool(value)
        elif t == "select":
            value = str(value)
            if value not in meta["options"]:
                raise ValueError(
                    f"'{key}' должен быть одним из {meta['options']}, получено '{value}'"
                )
        else:
            value = str(value)

        data = self._load_overrides()
        old_value = data.get("config", {}).get(key, getattr(Config, key, None))
        data.setdefault("config", {})[key] = value
        self._append_history(data, key, "config", old_value, value)
        self._save_overrides(data)

        return {
            "key": key,
            "value": value,
            "default": getattr(Config, key, None),
            "is_overridden": True,
            **meta,
        }

    def reset_config_override(self, key: str) -> dict:
        """Удаляет override параметра — возвращает к дефолту из Config."""
        editable = object.__getattribute__(self, "EDITABLE_CONFIG")
        if key not in editable:
            raise ValueError(f"Параметр '{key}' не является редактируемым")

        data = self._load_overrides()
        old_value = data.get("config", {}).pop(key, None)
        default_val = getattr(Config, key, None)
        if old_value is not None:
            self._append_history(data, key, "config_reset", old_value, default_val)
        self._save_overrides(data)

        return {
            "key": key,
            "value": default_val,
            "default": default_val,
            "is_overridden": False,
        }

    def reset_all_config_overrides(self) -> None:
        """Сбрасывает все параметры к дефолтам. Промты не трогает."""
        data = self._load_overrides()
        data["config"] = {}
        self._save_overrides(data)

    # ════════════════════════════════════════════════════════════
    # PROMPTS: PUBLIC API
    # ════════════════════════════════════════════════════════════

    def _read_default_prompt(self, name: str) -> str:
        """Читает дефолтный текст промта из .md файла в bot_agent/."""
        bot_agent_root = object.__getattribute__(self, "BOT_AGENT_ROOT")
        md_path = bot_agent_root / f"{name}.md"
        if not md_path.exists():
            raise FileNotFoundError(f"Файл промта не найден: {md_path}")
        return md_path.read_text(encoding="utf-8")

    def get_prompt(self, name: str) -> dict:
        """
        Возвращает текст промта: override если есть, иначе дефолт из .md.

        Returns:
            {
                "name": str,
                "label": str,
                "text": str,           # актуальный текст
                "default_text": str,   # оригинал из .md
                "is_overridden": bool,
                "char_count": int,
            }
        """
        editable_prompts = object.__getattribute__(self, "EDITABLE_PROMPTS")
        if name not in editable_prompts:
            raise ValueError(f"Промт '{name}' не является редактируемым")

        prompt_labels = object.__getattribute__(self, "PROMPT_LABELS")
        default_text = self._read_default_prompt(name)
        overrides = self._load_overrides().get("prompts", {})
        override_text = overrides.get(name)

        active_text = override_text if (override_text is not None) else default_text

        return {
            "name": name,
            "label": prompt_labels.get(name, name),
            "text": active_text,
            "default_text": default_text,
            "is_overridden": override_text is not None,
            "char_count": len(active_text),
        }

    def get_all_prompts(self) -> list:
        """
        Список всех промтов с превью для рендера в UI.
        """
        editable_prompts = object.__getattribute__(self, "EDITABLE_PROMPTS")
        prompt_labels = object.__getattribute__(self, "PROMPT_LABELS")
        overrides = self._load_overrides().get("prompts", {})

        result = []
        for name in editable_prompts:
            try:
                default_text = self._read_default_prompt(name)
            except FileNotFoundError:
                default_text = ""

            override_text = overrides.get(name)
            is_overridden = override_text is not None
            active_text = override_text if is_overridden else default_text

            result.append({
                "name": name,
                "label": prompt_labels.get(name, name),
                "preview": active_text[:150].replace("\n", " "),
                "is_overridden": is_overridden,
                "char_count": len(active_text),
            })
        return result

    def set_prompt_override(self, name: str, text: str) -> dict:
        """Сохраняет новый текст промта как override."""
        editable_prompts = object.__getattribute__(self, "EDITABLE_PROMPTS")
        if name not in editable_prompts:
            raise ValueError(f"Промт '{name}' не является редактируемым")
        if not text.strip():
            raise ValueError("Текст промта не может быть пустым")

        data = self._load_overrides()
        had_override = data.get("prompts", {}).get(name) is not None
        data.setdefault("prompts", {})[name] = text
        self._append_history(data, name, "prompt", had_override, True)
        self._save_overrides(data)
        return self.get_prompt(name)

    def reset_prompt_override(self, name: str) -> dict:
        """Сбрасывает промт к дефолту — удаляет override."""
        editable_prompts = object.__getattribute__(self, "EDITABLE_PROMPTS")
        if name not in editable_prompts:
            raise ValueError(f"Промт '{name}' не является редактируемым")

        data = self._load_overrides()
        data.setdefault("prompts", {})[name] = None
        self._append_history(data, name, "prompt_reset", True, False)
        self._save_overrides(data)
        return self.get_prompt(name)

    def reset_all_prompt_overrides(self) -> None:
        """Сбрасывает все промты к дефолтам. Config не трогает."""
        data = self._load_overrides()
        data["prompts"] = {}
        self._save_overrides(data)

    def reset_all_overrides(self) -> None:
        """Полный сброс — и config, и промты."""
        self._save_overrides({
            "config": {}, "prompts": {}, "history": [], "meta": {}
        })

    def get_history(self) -> list:
        """Последние 50 изменений для отображения в UI."""
        return self._load_overrides().get("history", [])
```


***

### Файл 2: `bot_psychologist/bot_agent/config.py` — ИЗМЕНИТЬ ТОЛЬКО ПОСЛЕДНЮЮ СТРОКУ

Найти в самом конце файла:

```python
config = Config()
```

Заменить на:

```python
# RuntimeConfig наследует Config и добавляет горячий override-слой.
# Circular import безопасен: класс Config уже полностью определён выше,
# runtime_config.py успешно импортирует его из частично загруженного
# модуля — стандартное поведение Python для взаимных импортов.
from .runtime_config import RuntimeConfig
config = RuntimeConfig()
```

**Больше в `config.py` ничего не менять.**

***

### Файл 3: Промты в модулях `bot_agent/` — НАЙТИ И ОБНОВИТЬ

#### Задача агента

Найти во **всех** следующих файлах паттерны прямого чтения `.md` файлов промтов:

**Файлы для сканирования:**

```
bot_agent/answer_basic.py
bot_agent/answer_adaptive.py
bot_agent/answer_graph_powered.py
bot_agent/answer_sag_aware.py
bot_agent/llm_answerer.py
bot_agent/sd_classifier.py
bot_agent/state_classifier.py
bot_agent/path_builder.py
bot_agent/practices_recommender.py
bot_agent/user_level_adapter.py
bot_agent/decision/*.py       (все файлы)
bot_agent/response/*.py       (все файлы)
bot_agent/retrieval/*.py      (все файлы)
bot_agent/storage/*.py        (все файлы)
```


#### Паттерны для поиска (все варианты):

```python
# Вариант A
(Path(__file__).parent / "prompt_XXX.md").read_text(encoding="utf-8")

# Вариант B
open(... / "prompt_XXX.md").read()

# Вариант C
with open(... / f"prompt_{something}.md") as f:
    prompt = f.read()

# Вариант D — любое упоминание prompt_*.md через pathlib или os.path
Path(...).read_text(...)  # если путь содержит "prompt_"
```


#### Правило замены

**Если промт читается внутри функции или метода:**

```python
# БЫЛО:
prompt_text = (Path(__file__).parent / "prompt_sd_green.md").read_text(encoding="utf-8")

# СТАЛО:
from bot_agent.config import config
prompt_text = config.get_prompt("prompt_sd_green")["text"]
```

**Если промт читается в глобальной области модуля (при импорте):**
Не менять. Добавить комментарий:

```python
# TODO(admin-panel): чтение промта на уровне модуля — не hot-reloadable.
# Для горячей замены перенести в функцию и использовать config.get_prompt().
PROMPT_TEXT = (Path(__file__).parent / "prompt_sd_green.md").read_text(encoding="utf-8")
```


***

### Файл 4: `bot_psychologist/api/admin_routes.py` — СОЗДАТЬ

```python
# api/admin_routes.py
"""
Admin Config Panel — API endpoints.

Все эндпоинты требуют dev-ключ в заголовке X-API-Key.
Роутер регистрируется в main.py через app.include_router(admin_router).
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import Any

from bot_agent.config import config
from .auth import is_dev_key


# ─── Auth dependency ───────────────────────────────────────────────────────────

def require_dev_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI Dependency: доступ только для dev-ключа."""
    if not is_dev_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Доступ запрещён: требуется dev-ключ",
        )
    return x_api_key


# ─── Router ────────────────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/api/admin",
    tags=["⚙️ Admin Config"],
    dependencies=[Depends(require_dev_key)],
)


# ══════════════════════════════════════════════════════════════════════
# CONFIG ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/config",
    summary="Все параметры конфига (сгруппированные)",
    response_description="Параметры разбиты по группам: llm, retrieval, memory, storage, runtime",
)
async def admin_get_config():
    """
    Возвращает все редактируемые параметры конфига с метаданными.
    Для каждого параметра: текущее значение, дефолт, флаг is_overridden.
    """
    return config.get_all_config()


@admin_router.put(
    "/config",
    summary="Сохранить значение одного параметра",
)
async def admin_set_config(body: dict):
    """
    Сохраняет override одного параметра конфига.

    Body: `{"key": "LLM_TEMPERATURE", "value": 0.5}`

    Валидирует тип и диапазон перед сохранением.
    Изменение применяется к следующему запросу бота без рестарта.
    """
    key = body.get("key")
    value = body.get("value")
    if not key:
        raise HTTPException(status_code=422, detail="Поле 'key' обязательно")
    if value is None:
        raise HTTPException(status_code=422, detail="Поле 'value' обязательно")
    try:
        return config.set_config_override(key, value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.delete(
    "/config/{key}",
    summary="Сбросить один параметр к дефолту",
)
async def admin_reset_config_param(key: str):
    """Удаляет override параметра. Параметр вернётся к дефолту из config.py."""
    try:
        return config.reset_config_override(key)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.post(
    "/config/reset-all",
    summary="Сбросить ВСЕ параметры конфига к дефолтам",
)
async def admin_reset_all_config():
    """Удаляет все config-overrides. Промты не затрагивает."""
    config.reset_all_config_overrides()
    return {"status": "ok", "message": "Все параметры конфига сброшены к дефолтам"}


# ══════════════════════════════════════════════════════════════════════
# PROMPT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/prompts",
    summary="Список всех промтов с превью",
)
async def admin_get_prompts():
    """
    Возвращает список всех 10 редактируемых промтов.
    Для каждого: label, превью 150 символов, флаг is_overridden, char_count.
    """
    return config.get_all_prompts()


@admin_router.get(
    "/prompts/{name}",
    summary="Полный текст промта",
)
async def admin_get_prompt(name: str):
    """
    Возвращает полный текст промта: актуальный (с override) и дефолтный (из .md).
    """
    try:
        return config.get_prompt(name)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@admin_router.put(
    "/prompts/{name}",
    summary="Сохранить новый текст промта",
)
async def admin_set_prompt(name: str, body: dict):
    """
    Сохраняет override текста промта.

    Body: `{"text": "Новый текст промта..."}`

    Изменение применяется к следующему запросу бота без рестарта
    (только если промт читается внутри функции, а не на уровне модуля).
    """
    text = body.get("text", "")
    try:
        return config.set_prompt_override(name, text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.delete(
    "/prompts/{name}",
    summary="Сбросить промт к дефолту (из .md файла)",
)
async def admin_reset_prompt(name: str):
    """Удаляет override промта. Бот вернётся к тексту из .md файла."""
    try:
        return config.reset_prompt_override(name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.post(
    "/prompts/reset-all",
    summary="Сбросить ВСЕ промты к дефолтам",
)
async def admin_reset_all_prompts():
    """Удаляет все prompt-overrides. Config не затрагивает."""
    config.reset_all_prompt_overrides()
    return {"status": "ok", "message": "Все промты сброшены к дефолтам"}


# ══════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/history",
    summary="История изменений (последние 50)",
)
async def admin_get_history():
    """
    Возвращает хронологический список последних 50 изменений конфига и промтов.
    Каждая запись: key, type, old, new, timestamp.
    """
    return {"history": config.get_history()}


# ══════════════════════════════════════════════════════════════════════
# EXPORT / IMPORT
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/export",
    summary="Экспортировать все overrides (backup)",
)
async def admin_export_overrides():
    """
    Возвращает полный JSON-файл admin_overrides.json.
    Используется для резервного копирования или переноса между окружениями.
    """
    return config._load_overrides()


@admin_router.post(
    "/import",
    summary="Импортировать overrides из JSON (restore)",
)
async def admin_import_overrides(body: dict):
    """
    Загружает overrides из тела запроса.
    Полностью заменяет текущий admin_overrides.json.
    Валидирует структуру перед сохранением.

    Body: содержимое admin_overrides.json (полученное через /export).
    """
    if not isinstance(body.get("config"), dict):
        raise HTTPException(
            status_code=422, detail="Поле 'config' должно быть объектом"
        )
    if not isinstance(body.get("prompts"), dict):
        raise HTTPException(
            status_code=422, detail="Поле 'prompts' должно быть объектом"
        )
    try:
        config._save_overrides(body)
        return {
            "status": "ok",
            "config_keys": len(body.get("config", {})),
            "prompt_overrides": sum(
                1 for v in body.get("prompts", {}).values() if v is not None
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# FULL RESET
# ══════════════════════════════════════════════════════════════════════

@admin_router.post(
    "/reset-all",
    summary="Полный сброс — и конфиг, и промты",
)
async def admin_reset_everything():
    """Удаляет ВСЕ overrides. Бот вернётся к состоянию 'из коробки'."""
    config.reset_all_overrides()
    return {"status": "ok", "message": "Все overrides удалены. Восстановлены дефолты."}
```


***

### Файл 5: `bot_psychologist/api/main.py` — ДОБАВИТЬ ДВЕ СТРОКИ

Найти в файле блок регистрации роутеров:

```python
# ===== ROUTERS =====

app.include_router(router)
app.include_router(debug_router)
```

Добавить после него:

```python
from .admin_routes import admin_router
app.include_router(admin_router)
```

Итоговый блок должен выглядеть так:

```python
# ===== ROUTERS =====

app.include_router(router)
app.include_router(debug_router)

from .admin_routes import admin_router  # Admin Config Panel
app.include_router(admin_router)
```


***

### Файл 6: `bot_psychologist/data/.gitkeep` — СОЗДАТЬ

Создать пустой файл, чтобы директория `data/` попала в git:

```
bot_psychologist/data/.gitkeep
```


***

### Файл 7: `bot_psychologist/.gitignore` — ДОБАВИТЬ СТРОКУ

Открыть существующий `bot_psychologist/.gitignore` и добавить:

```
# Admin Config Panel — хранится только на сервере
data/admin_overrides.json
```


***

## 6. Фронтенд — полная реализация

### Файл 8: `web_ui/src/types/admin.types.ts` — СОЗДАТЬ

```typescript
// types/admin.types.ts

export type ParamType = 'int' | 'float' | 'bool' | 'select' | 'string';

export interface ConfigParam {
  value: number | boolean | string;
  default: number | boolean | string;
  is_overridden: boolean;
  type: ParamType;
  min?: number;
  max?: number;
  options?: string[];
  group: string;
  label: string;
  note?: string;  // подсказка под полем
}

export interface ConfigGroup {
  label: string;
  params: Record<string, ConfigParam>;
}

export interface AdminConfigResponse {
  groups: Record<string, ConfigGroup>;
}

export interface PromptMeta {
  name: string;
  label: string;
  preview: string;
  is_overridden: boolean;
  char_count: number;
}

export interface PromptDetail extends PromptMeta {
  text: string;
  default_text: string;
}

export type HistoryEntryType =
  | 'config'
  | 'config_reset'
  | 'prompt'
  | 'prompt_reset';

export interface HistoryEntry {
  key: string;
  type: HistoryEntryType;
  old: unknown;
  new: unknown;
  timestamp: string;
}

export interface AdminOverridesExport {
  config: Record<string, unknown>;
  prompts: Record<string, string | null>;
  meta: { last_modified: string; modified_by: string };
  history: HistoryEntry[];
}
```


***

### Файл 9: `web_ui/src/services/adminConfig.service.ts` — СОЗДАТЬ

```typescript
// services/adminConfig.service.ts

import type {
  AdminConfigResponse,
  ConfigParam,
  PromptMeta,
  PromptDetail,
  HistoryEntry,
  AdminOverridesExport,
} from '../types/admin.types';

// Получаем API-ключ из того же источника, что и остальные запросы приложения.
// Если в проекте уже есть apiService.getAPIKey() — использовать его.
// Если ключ хранится в localStorage:
function getDevApiKey(): string {
  return localStorage.getItem('devApiKey') ?? '';
}

const BASE = '/api/admin';

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': getDevApiKey(),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const adminConfigService = {
  // Config
  getConfig: () =>
    request<AdminConfigResponse>('GET', '/config'),
  setConfigParam: (key: string, value: unknown) =>
    request<ConfigParam>('PUT', '/config', { key, value }),
  resetConfigParam: (key: string) =>
    request<{ key: string; value: unknown; is_overridden: false }>(
      'DELETE', `/config/${key}`
    ),
  resetAllConfig: () =>
    request<{ status: string }>('POST', '/config/reset-all'),

  // Prompts
  getPrompts: () =>
    request<PromptMeta[]>('GET', '/prompts'),
  getPrompt: (name: string) =>
    request<PromptDetail>('GET', `/prompts/${name}`),
  setPrompt: (name: string, text: string) =>
    request<PromptDetail>('PUT', `/prompts/${name}`, { text }),
  resetPrompt: (name: string) =>
    request<PromptDetail>('DELETE', `/prompts/${name}`),
  resetAllPrompts: () =>
    request<{ status: string }>('POST', '/prompts/reset-all'),

  // History
  getHistory: () =>
    request<{ history: HistoryEntry[] }>('GET', '/history'),

  // Export / Import
  exportOverrides: () =>
    request<AdminOverridesExport>('GET', '/export'),
  importOverrides: (data: AdminOverridesExport) =>
    request<{ status: string; config_keys: number; prompt_overrides: number }>(
      'POST', '/import', data
    ),

  // Full reset
  resetAll: () =>
    request<{ status: string }>('POST', '/reset-all'),
};
```


***

### Файл 10: `web_ui/src/hooks/useAdminConfig.ts` — СОЗДАТЬ

```typescript
// hooks/useAdminConfig.ts

import { useState, useCallback } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type {
  AdminConfigResponse,
  PromptMeta,
  PromptDetail,
} from '../types/admin.types';

export const useAdminConfig = () => {
  const [configData, setConfigData] = useState<AdminConfigResponse | null>(null);
  const [prompts, setPrompts] = useState<PromptMeta[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const showSuccess = useCallback((msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 2500);
  }, []);

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null);
    setIsLoading(true);
    try {
      return await fn();
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setIsLoading(false);
    }
  };

  const withSaving = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null);
    setIsSaving(true);
    try {
      return await fn();
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setIsSaving(false);
    }
  };

  // ── Config ──────────────────────────────────────────────────────────

  const loadConfig = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getConfig());
    if (data) setConfigData(data);
  }, []);

  const saveConfigParam = useCallback(
    async (key: string, value: unknown) => {
      await withSaving(() => adminConfigService.setConfigParam(key, value));
      await loadConfig();
      showSuccess(`✓ ${key} сохранён`);
    },
    [loadConfig, showSuccess]
  );

  const resetConfigParam = useCallback(
    async (key: string) => {
      await withSaving(() => adminConfigService.resetConfigParam(key));
      await loadConfig();
      showSuccess(`↩ ${key} сброшен к дефолту`);
    },
    [loadConfig, showSuccess]
  );

  const resetAllConfig = useCallback(async () => {
    if (!window.confirm('Сбросить ВСЕ параметры конфига к дефолтам?')) return;
    await withSaving(() => adminConfigService.resetAllConfig());
    await loadConfig();
    showSuccess('↩ Все параметры конфига сброшены');
  }, [loadConfig, showSuccess]);

  // ── Prompts ─────────────────────────────────────────────────────────

  const loadPrompts = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getPrompts());
    if (data) setPrompts(data);
  }, []);

  const loadPromptDetail = useCallback(async (name: string) => {
    const data = await withLoading(() => adminConfigService.getPrompt(name));
    if (data) setSelectedPrompt(data);
  }, []);

  const savePrompt = useCallback(
    async (name: string, text: string) => {
      const updated = await withSaving(() =>
        adminConfigService.setPrompt(name, text)
      );
      if (updated) {
        setSelectedPrompt(updated);
        await loadPrompts();
        showSuccess('✓ Промт сохранён');
      }
    },
    [loadPrompts, showSuccess]
  );

  const resetPrompt = useCallback(
    async (name: string) => {
      if (!window.confirm('Сбросить промт к оригиналу из .md файла?')) return;
      const updated = await withSaving(() =>
        adminConfigService.resetPrompt(name)
      );
      if (updated) {
        setSelectedPrompt(updated);
        await loadPrompts();
        showSuccess('↩ Промт сброшен к дефолту');
      }
    },
    [loadPrompts, showSuccess]
  );

  const resetAllPrompts = useCallback(async () => {
    if (!window.confirm('Сбросить ВСЕ промты к оригиналам?')) return;
    await withSaving(() => adminConfigService.resetAllPrompts());
    await loadPrompts();
    if (selectedPrompt) await loadPromptDetail(selectedPrompt.name);
    showSuccess('↩ Все промты сброшены');
  }, [loadPrompts, selectedPrompt, loadPromptDetail, showSuccess]);

  // ── Export / Import ─────────────────────────────────────────────────

  const exportOverrides = useCallback(async () => {
    const data = await adminConfigService.exportOverrides();
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `admin_overrides_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showSuccess('✓ Файл скачан');
  }, [showSuccess]);

  const importOverrides = useCallback(
    async (file: File) => {
      const text = await file.text();
      const data = JSON.parse(text);
      await withSaving(() => adminConfigService.importOverrides(data));
      await loadConfig();
      await loadPrompts();
      showSuccess('✓ Настройки импортированы');
    },
    [loadConfig, loadPrompts, showSuccess]
  );

  return {
    configData,
    prompts,
    selectedPrompt,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadConfig,
    loadPrompts,
    loadPromptDetail,
    saveConfigParam,
    resetConfigParam,
    resetAllConfig,
    savePrompt,
    resetPrompt,
    resetAllPrompts,
    exportOverrides,
    importOverrides,
  };
};
```


***

### Файл 11: `web_ui/src/components/admin/ConfigGroupPanel.tsx` — СОЗДАТЬ

```tsx
// components/admin/ConfigGroupPanel.tsx

import React, { useState, useEffect } from 'react';
import type { ConfigGroup } from '../../types/admin.types';

interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
  currentLLMModel?: string; // для блокировки температуры при reasoning-моделях
}

// Reasoning-модели не поддерживают температуру
const REASONING_PREFIXES = ['gpt-5', 'o1', 'o3', 'o4'];
const isReasoningModel = (model: string) =>
  REASONING_PREFIXES.some((p) => model.startsWith(p));

export const ConfigGroupPanel: React.FC<Props> = ({
  groupKey,
  group,
  onSave,
  onReset,
  isSaving,
  currentLLMModel = '',
}) => {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    const init: Record<string, unknown> = {};
    Object.entries(group.params).forEach(([key, param]) => {
      init[key] = param.value;
    });
    setDrafts(init);
    setDirtyKeys(new Set());
  }, [group]);

  const handleChange = (key: string, value: unknown) => {
    setDrafts((prev) => ({ ...prev, [key]: value }));
    setDirtyKeys((prev) => new Set(prev).add(key));
  };

  const handleSave = async (key: string) => {
    await onSave(key, drafts[key]);
    setDirtyKeys((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  };

  const handleSaveAll = async () => {
    for (const key of Array.from(dirtyKeys)) {
      await onSave(key, drafts[key]);
    }
    setDirtyKeys(new Set());
  };

  const renderInput = (key: string, param: ConfigGroup['params'][string]) => {
    const draft = drafts[key];
    const isTemperatureBlocked =
      key === 'LLM_TEMPERATURE' && isReasoningModel(currentLLMModel);

    const baseClass =
      'w-full px-3 py-1.5 rounded border text-sm ' +
      (param.is_overridden && !dirtyKeys.has(key)
        ? 'border-amber-400 bg-amber-50'
        : 'border-gray-300 bg-white');

    if (isTemperatureBlocked) {
      return (
        <div className="flex items-center gap-2">
          <input
            className={`${baseClass} opacity-40 cursor-not-allowed`}
            value={String(draft)}
            disabled
          />
          <span className="text-xs text-gray-400 italic">
            н/п для reasoning-модели
          </span>
        </div>
      );
    }

    if (param.type === 'bool') {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(draft)}
            onChange={(e) => handleChange(key, e.target.checked)}
            className="w-4 h-4 rounded accent-blue-600"
          />
          <span className="text-sm text-gray-600">
            {Boolean(draft) ? 'Включено' : 'Выключено'}
          </span>
        </label>
      );
    }

    if (param.type === 'select' && param.options) {
      return (
        <select
          className={baseClass}
          value={String(draft)}
          onChange={(e) => handleChange(key, e.target.value)}
        >
          {param.options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );
    }

    if (param.type === 'int' || param.type === 'float') {
      return (
        <div className="flex items-center gap-2">
          <input
            type="number"
            className={baseClass}
            value={String(draft)}
            min={param.min}
            max={param.max}
            step={param.type === 'float' ? 0.05 : 1}
            onChange={(e) =>
              handleChange(
                key,
                param.type === 'float'
                  ? parseFloat(e.target.value)
                  : parseInt(e.target.value, 10)
              )
            }
          />
          <span className="text-xs text-gray-400 whitespace-nowrap">
            [{param.min} – {param.max}]
          </span>
        </div>
      );
    }

    return (
      <input
        type="text"
        className={baseClass}
        value={String(draft)}
        onChange={(e) => handleChange(key, e.target.value)}
      />
    );
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      {/* Заголовок группы */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-gray-800 text-base">{group.label}</h3>
        <div className="flex gap-2">
          {dirtyKeys.size > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={isSaving}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Сохранить все ({dirtyKeys.size})
            </button>
          )}
          <button
            onClick={() => onReset('__all__')}
            disabled={isSaving}
            className="px-3 py-1 bg-gray-100 text-gray-600 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
          >
            ↩ Сбросить группу
          </button>
        </div>
      </div>

      {/* Список параметров */}
      <div className="space-y-4">
        {Object.entries(group.params).map(([key, param]) => (
          <div key={key} className="grid grid-cols-[1fr_auto] gap-x-3 items-start">
            {/* Левая колонка: лейбл + инпут + подсказки */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <label className="text-sm font-medium text-gray-700">
                  {param.label}
                </label>
                {param.is_overridden && !dirtyKeys.has(key) && (
                  <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                    override
                  </span>
                )}
                {dirtyKeys.has(key) && (
                  <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                    изменено
                  </span>
                )}
              </div>
              {renderInput(key, param)}
              {param.note && (
                <p className="text-xs text-gray-400 mt-1 italic">{param.note}</p>
              )}
              {param.is_overridden && (
                <p className="text-xs text-gray-400 mt-0.5">
                  Дефолт:{' '}
                  <span className="font-mono">{String(param.default)}</span>
                </p>
              )}
            </div>

            {/* Правая колонка: кнопки */}
            <div className="flex flex-col gap-1 pt-6">
              {dirtyKeys.has(key) && (
                <button
                  onClick={() => handleSave(key)}
                  disabled={isSaving}
                  className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50"
                >
                  ✓
                </button>
              )}
              {param.is_overridden && (
                <button
                  onClick={() => onReset(key)}
                  disabled={isSaving}
                  className="px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs hover:bg-gray-200 disabled:opacity-50"
                  title="Сбросить к дефолту"
                >
                  ↩
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```


***

### Файл 12: `web_ui/src/components/admin/PromptEditorPanel.tsx` — СОЗДАТЬ

```tsx
// components/admin/PromptEditorPanel.tsx

import React, { useState, useEffect } from 'react';
import type { PromptDetail, PromptMeta } from '../../types/admin.types';

interface Props {
  prompts: PromptMeta[];
  selectedPrompt: PromptDetail | null;
  onSelect: (name: string) => void;
  onSave: (name: string, text: string) => Promise<void>;
  onReset: (name: string) => Promise<void>;
  onResetAll: () => Promise<void>;
  isSaving: boolean;
}

export const PromptEditorPanel: React.FC<Props> = ({
  prompts,
  selectedPrompt,
  onSelect,
  onSave,
  onReset,
  onResetAll,
  isSaving,
}) => {
  const [draftText, setDraftText] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  useEffect(() => {
    if (selectedPrompt) {
      setDraftText(selectedPrompt.text);
      setIsDirty(false);
      setShowDiff(false);
    }
  }, [selectedPrompt]);

  const handleTextChange = (value: string) => {
    setDraftText(value);
    setIsDirty(value !== selectedPrompt?.text);
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;
    await onSave(selectedPrompt.name, draftText);
    setIsDirty(false);
  };

  const handleReset = async () => {
    if (!selectedPrompt) return;
    await onReset(selectedPrompt.name);
  };

  return (
    <div className="flex h-full gap-4">
      {/* Левая панель: список промтов */}
      <div className="w-64 flex-shrink-0">
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-gray-800 text-sm">Промты</h3>
          <button
            onClick={onResetAll}
            disabled={isSaving}
            className="text-xs text-gray-500 hover:text-red-500 disabled:opacity-50"
          >
            ↩ Все к дефолту
          </button>
        </div>
        <div className="space-y-1">
          {prompts.map((p) => (
            <button
              key={p.name}
              onClick={() => onSelect(p.name)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selectedPrompt?.name === p.name
                  ? 'bg-blue-50 border border-blue-200 text-blue-800'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium truncate">{p.label}</span>
                {p.is_overridden && (
                  <span className="ml-1 w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                )}
              </div>
              <div className="text-xs text-gray-400 truncate mt-0.5">
                {p.char_count} симв.
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Правая панель: редактор */}
      <div className="flex-1 flex flex-col">
        {selectedPrompt ? (
          <>
            {/* Заголовок редактора */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-800">
                  {selectedPrompt.label}
                </h3>
                <p className="text-xs text-gray-400">
                  {draftText.length} символов
                  {selectedPrompt.is_overridden && (
                    <span className="ml-2 text-amber-600 font-medium">
                      • override активен
                    </span>
                  )}
                  {isDirty && (
                    <span className="ml-2 text-blue-600 font-medium">
                      • не сохранено
                    </span>
                  )}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDiff(!showDiff)}
                  className={`px-3 py-1.5 rounded text-sm border transition-colors ${
                    showDiff
                      ? 'bg-gray-800 text-white border-gray-800'
                      : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {showDiff ? 'Скрыть оригинал' : 'Показать оригинал'}
                </button>
                {selectedPrompt.is_overridden && (
                  <button
                    onClick={handleReset}
                    disabled={isSaving}
                    className="px-3 py-1.5 rounded text-sm border border-amber-300 text-amber-700 hover:bg-amber-50 disabled:opacity-50"
                  >
                    ↩ Вернуть оригинал
                  </button>
                )}
                <button
                  onClick={handleSave}
                  disabled={isSaving || !isDirty}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {isSaving ? 'Сохранение...' : '✓ Сохранить'}
                </button>
              </div>
            </div>

            {/* Режим diff: два блока рядом */}
            {showDiff ? (
              <div className="flex gap-3 flex-1 min-h-0">
                <div className="flex-1 flex flex-col">
                  <p className="text-xs text-gray-500 mb-1 font-medium">
                    Оригинал (.md файл)
                  </p>
                  <textarea
                    readOnly
                    value={selectedPrompt.default_text}
                    className="flex-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono bg-gray-50 text-gray-500 resize-none"
                  />
                </div>
                <div className="flex-1 flex flex-col">
                  <p className="text-xs text-blue-600 mb-1 font-medium">
                    Текущая версия (редактирование)
                  </p>
                  <textarea
                    value={draftText}
                    onChange={(e) => handleTextChange(e.target.value)}
                    className="flex-1 w-full px-3 py-2 border border-blue-300 rounded-lg text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
              </div>
            ) : (
              /* Обычный режим: один редактор */
              <textarea
                value={draftText}
                onChange={(e) => handleTextChange(e.target.value)}
                className="flex-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="Текст промта..."
              />
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Выберите промт из списка слева
          </div>
        )}
      </div>
    </div>
  );
};
```


***

### Файл 13: `web_ui/src/components/admin/HistoryPanel.tsx` — СОЗДАТЬ

```tsx
// components/admin/HistoryPanel.tsx

import React from 'react';
import type { HistoryEntry } from '../../types/admin.types';

interface Props {
  history: HistoryEntry[];
}

const typeLabel: Record<string, { text: string; color: string }> = {
  config:       { text: 'config изменён',  color: 'bg-blue-100 text-blue-700' },
  config_reset: { text: 'config сброшен',  color: 'bg-gray-100 text-gray-600' },
  prompt:       { text: 'промт изменён',   color: 'bg-amber-100 text-amber-700' },
  prompt_reset: { text: 'промт сброшен',   color: 'bg-gray-100 text-gray-600' },
};

export const HistoryPanel: React.FC<Props> = ({ history }) => {
  const sorted = [...history].reverse(); // последние сверху

  if (sorted.length === 0) {
    return (
      <div className="text-center text-gray-400 text-sm py-12">
        История изменений пуста
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sorted.map((entry, i) => {
        const badge = typeLabel[entry.type] ?? {
          text: entry.type,
          color: 'bg-gray-100 text-gray-600',
        };
        return (
          <div
            key={i}
            className="flex items-start gap-3 px-4 py-3 bg-white rounded-lg border border-gray-100 hover:border-gray-200"
          >
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 mt-0.5 ${badge.color}`}
            >
              {badge.text}
            </span>
            <div className="flex-1 min-w-0">
              <span className="font-mono text-sm font-semibold text-gray-800">
                {entry.key}
              </span>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
                <span className="font-mono bg-red-50 text-red-600 px-1 rounded">
                  {String(entry.old)}
                </span>
                <span>→</span>
                <span className="font-mono bg-green-50 text-green-700 px-1 rounded">
                  {String(entry.new)}
                </span>
              </div>
            </div>
            <span className="text-xs text-gray-400 flex-shrink-0 whitespace-nowrap">
              {new Date(entry.timestamp).toLocaleString('ru-RU')}
            </span>
          </div>
        );
      })}
    </div>
  );
};
```


***

### Файл 14: `web_ui/src/components/admin/AdminPanel.tsx` — СОЗДАТЬ

```tsx
// components/admin/AdminPanel.tsx
// Главный компонент Admin Config Panel. Подключается к роутингу web_ui.

import React, { useState, useEffect, useRef } from 'react';
import { useAdminConfig } from '../../hooks/useAdminConfig';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { PromptEditorPanel } from './PromptEditorPanel';
import { HistoryPanel } from './HistoryPanel';
import type { HistoryEntry } from '../../types/admin.types';

type Tab = 'llm' | 'retrieval' | 'memory' | 'storage' | 'runtime' | 'prompts' | 'history';

const TABS: { key: Tab; label: string }[] = [
  { key: 'llm',       label: '🤖 LLM' },
  { key: 'retrieval', label: '🔍 Поиск' },
  { key: 'memory',    label: '🧠 Память' },
  { key: 'storage',   label: '🗄️ Хранилище' },
  { key: 'runtime',   label: '⚙️ Runtime' },
  { key: 'prompts',   label: '📝 Промты' },
  { key: 'history',   label: '🕐 История' },
];

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('llm');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData,
    prompts,
    selectedPrompt,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadConfig,
    loadPrompts,
    loadPromptDetail,
    saveConfigParam,
    resetConfigParam,
    resetAllConfig,
    savePrompt,
    resetPrompt,
    resetAllPrompts,
    exportOverrides,
    importOverrides,
  } = useAdminConfig();

  // Получаем текущее значение LLM_MODEL для блокировки температуры
  const currentLLMModel =
    (configData?.groups?.llm?.params?.LLM_MODEL?.value as string) ?? '';

  useEffect(() => {
    loadConfig();
    loadPrompts();
  }, []);

  useEffect(() => {
    if (activeTab === 'history') {
      // Загружаем историю из уже закэшированных данных или делаем отдельный запрос
      import('../../services/adminConfig.service').then(({ adminConfigService }) => {
        adminConfigService.getHistory().then((data) => setHistory(data.history));
      });
    }
  }, [activeTab]);

  const handleResetConfigParam = async (key: string) => {
    if (key === '__all__') {
      await resetAllConfig();
    } else {
      await resetConfigParam(key);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await importOverrides(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              ⚙️ Admin Config Panel
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Горячее управление параметрами бота без рестарта сервера
            </p>
          </div>
          {/* Export / Import / Full Reset */}
          <div className="flex items-center gap-2">
            <button
              onClick={exportOverrides}
              className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              ↓ Экспорт
            </button>
            <label className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50 cursor-pointer">
              ↑ Импорт
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImportFile}
              />
            </label>
            <button
              onClick={async () => {
                if (
                  window.confirm(
                    'Полный сброс: удалить ВСЕ overrides (и конфиг, и промты)?'
                  )
                ) {
                  const { adminConfigService } = await import(
                    '../../services/adminConfig.service'
                  );
                  await adminConfigService.resetAll();
                  await loadConfig();
                  await loadPrompts();
                }
              }}
              className="px-3 py-1.5 border border-red-200 rounded text-sm text-red-600 hover:bg-red-50"
            >
              🗑 Полный сброс
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="max-w-6xl mx-auto flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications */}
      <div className="max-w-6xl mx-auto px-6 pt-3">
        {error && (
          <div className="flex items-center justify-between px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
            <span>⚠ {error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">
              ✕
            </button>
          </div>
        )}
        {successMessage && (
          <div className="px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 mb-3">
            {successMessage}
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-6 pb-10">
        {isLoading && (
        {isLoading && (
          <div className="text-center text-gray-400 py-12 text-sm">
            Загрузка...
          </div>
        )}

        {!isLoading && configData && (
          <>
            {/* ── Config tabs ── */}
            {(['llm', 'retrieval', 'memory', 'storage', 'runtime'] as const).includes(
              activeTab as any
            ) && (
              <div className="mt-4 space-y-4">
                {Object.entries(configData.groups)
                  .filter(([groupKey]) => groupKey === activeTab)
                  .map(([groupKey, group]) => (
                    <ConfigGroupPanel
                      key={groupKey}
                      groupKey={groupKey}
                      group={group}
                      onSave={saveConfigParam}
                      onReset={handleResetConfigParam}
                      isSaving={isSaving}
                      currentLLMModel={currentLLMModel}
                    />
                  ))}
              </div>
            )}

            {/* ── Prompts tab ── */}
            {activeTab === 'prompts' && (
              <div className="mt-4 bg-white rounded-xl border border-gray-200 p-5 shadow-sm h-[70vh]">
                <PromptEditorPanel
                  prompts={prompts}
                  selectedPrompt={selectedPrompt}
                  onSelect={loadPromptDetail}
                  onSave={savePrompt}
                  onReset={resetPrompt}
                  onResetAll={resetAllPrompts}
                  isSaving={isSaving}
                />
              </div>
            )}

            {/* ── History tab ── */}
            {activeTab === 'history' && (
              <div className="mt-4">
                <HistoryPanel history={history} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
```


***

### Файл 15: Регистрация маршрута в роутинге `web_ui` — ОБНОВИТЬ

Агент должен найти файл роутинга приложения (скорее всего `web_ui/src/App.tsx`, `web_ui/src/router.tsx` или аналогичный) и добавить маршрут к `AdminPanel`.

**Паттерн для поиска в `App.tsx`:**

```tsx
// Найти импорты роутов и список <Route> компонентов.
// Добавить:
import { AdminPanel } from './components/admin/AdminPanel';

// В блоке роутов добавить:
<Route path="/admin" element={<AdminPanel />} />
```

**Если в проекте используется отдельный файл роутера** (`router.tsx`, `routes.tsx`):

```tsx
import { AdminPanel } from './components/admin/AdminPanel';

{
  path: '/admin',
  element: <AdminPanel />,
}
```

**Если в проекте есть навигационное меню** (sidebar, navbar) — добавить пункт:

```tsx
<NavLink to="/admin">⚙️ Admin</NavLink>
```

Ссылку на `/admin` показывать **только если** пользователь авторизован как dev (проверить через существующую логику авторизации в `web_ui`).

***

## 7. Порядок реализации — пошаговый план

Агент должен выполнять шаги **строго в указанном порядке**. Каждый шаг заканчивается проверкой.

### Шаг 1 — Создать файл `data/.gitkeep` и обновить `.gitignore`

```
СОЗДАТЬ:   bot_psychologist/data/.gitkeep   (пустой файл)
ИЗМЕНИТЬ:  bot_psychologist/.gitignore      (добавить строку)
```

Добавить в `.gitignore`:

```
# Admin Config Panel runtime overrides
data/admin_overrides.json
```

**Проверка:** `git status` показывает `data/.gitkeep` как новый файл; `data/admin_overrides.json` — в игноре.

***

### Шаг 2 — Создать `runtime_config.py`

```
СОЗДАТЬ: bot_psychologist/bot_agent/runtime_config.py
```

Скопировать полный код из Секции 5, Файл 1 настоящего ПРД.

**Проверка:** запустить в Python-интерпретаторе (из директории `bot_psychologist`):

```python
from bot_agent.runtime_config import RuntimeConfig
rc = RuntimeConfig()
print(rc.LLM_TEMPERATURE)   # должно вернуть 0.7 (дефолт из Config)
print(rc.TOP_K_BLOCKS)      # должно вернуть 5
print(type(rc))             # <class 'bot_agent.runtime_config.RuntimeConfig'>
```


***

### Шаг 3 — Изменить последнюю строку `config.py`

```
ИЗМЕНИТЬ: bot_psychologist/bot_agent/config.py  (только последняя строка)
```

Найти в конце файла `config = Config()` и заменить согласно Секции 5, Файл 2.

**Проверка:** запустить:

```python
from bot_agent.config import config
print(type(config))          # <class 'bot_agent.runtime_config.RuntimeConfig'>
print(config.LLM_TEMPERATURE)  # 0.7
```


***

### Шаг 4 — Проверить и обновить чтение промтов в модулях

```
СКАНИРОВАТЬ: все файлы из списка в Секции 5, Файл 3
```

Для каждого найденного паттерна прямого чтения `.md`:

- Если внутри функции — заменить на `config.get_prompt(name)["text"]`
- Если в глобальной области — добавить TODO-комментарий

**Проверка:** grep по проекту не должен находить незакомментированных `"prompt_*.md").read_text` внутри функций:

```bash
grep -rn "prompt_.*\.md.*read_text" bot_psychologist/bot_agent/ --include="*.py"
```


***

### Шаг 5 — Создать `api/admin_routes.py`

```
СОЗДАТЬ: bot_psychologist/api/admin_routes.py
```

Скопировать полный код из Секции 5, Файл 4.

**Проверка:** импорт без ошибок:

```python
from api.admin_routes import admin_router
print(admin_router.prefix)   # /api/admin
```


***

### Шаг 6 — Зарегистрировать роутер в `main.py`

```
ИЗМЕНИТЬ: bot_psychologist/api/main.py
```

Добавить две строки согласно Секции 5, Файл 5.

**Проверка:** запустить сервер и открыть `http://localhost:8000/api/docs`. В документации Swagger должна появиться секция `⚙️ Admin Config` с эндпоинтами.

***

### Шаг 7 — Smoke-тесты бэкенда через curl

Выполнить все команды последовательно. `DEV_KEY` — актуальный dev-ключ из `.env`.

```bash
export DEV_KEY="your_dev_api_key_here"
export BASE="http://localhost:8000/api/admin"
```

**7.1 — Получить конфиг:**

```bash
curl -s -H "X-API-Key: $DEV_KEY" $BASE/config | python3 -m json.tool | head -30
# Ожидаем: JSON с полем "groups" содержащим "llm", "retrieval", etc.
```

**7.2 — Изменить температуру:**

```bash
curl -s -X PUT -H "X-API-Key: $DEV_KEY" -H "Content-Type: application/json" \
  -d '{"key": "LLM_TEMPERATURE", "value": 0.3}' $BASE/config
# Ожидаем: {"key": "LLM_TEMPERATURE", "value": 0.3, "is_overridden": true, ...}
```

**7.3 — Проверить, что override подхватился:**

```bash
curl -s -H "X-API-Key: $DEV_KEY" $BASE/config | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  print(d['groups']['llm']['params']['LLM_TEMPERATURE']['value'])"
# Ожидаем: 0.3
```

**7.4 — Сбросить температуру:**

```bash
curl -s -X DELETE -H "X-API-Key: $DEV_KEY" $BASE/config/LLM_TEMPERATURE
# Ожидаем: {"key": "LLM_TEMPERATURE", "value": 0.7, "is_overridden": false}
```

**7.5 — Получить список промтов:**

```bash
curl -s -H "X-API-Key: $DEV_KEY" $BASE/prompts | python3 -m json.tool | head -20
# Ожидаем: массив из 10 объектов с полями name, label, preview, is_overridden
```

**7.6 — Изменить промт:**

```bash
curl -s -X PUT -H "X-API-Key: $DEV_KEY" -H "Content-Type: application/json" \
  -d '{"text": "Тестовый текст промта для проверки override"}' \
  $BASE/prompts/prompt_sd_green
# Ожидаем: объект с is_overridden: true
```

**7.7 — Проверить is_overridden:**

```bash
curl -s -H "X-API-Key: $DEV_KEY" $BASE/prompts | \
  python3 -c "import sys,json; \
  d=json.load(sys.stdin); \
  [print(p['name'], p['is_overridden']) for p in d]"
# Ожидаем: prompt_sd_green True, остальные False
```

**7.8 — Сбросить промт:**

```bash
curl -s -X DELETE -H "X-API-Key: $DEV_KEY" $BASE/prompts/prompt_sd_green
# Ожидаем: is_overridden: false
```

**7.9 — Получить историю:**

```bash
curl -s -H "X-API-Key: $DEV_KEY" $BASE/history
# Ожидаем: {"history": [...]} — должны быть записи из шагов 7.2, 7.4, 7.6, 7.8
```

**7.10 — Экспорт/Импорт:**

```bash
# Экспорт
curl -s -H "X-API-Key: $DEV_KEY" $BASE/export > /tmp/overrides_backup.json
cat /tmp/overrides_backup.json

# Импорт обратно
curl -s -X POST -H "X-API-Key: $DEV_KEY" -H "Content-Type: application/json" \
  -d @/tmp/overrides_backup.json $BASE/import
# Ожидаем: {"status": "ok", "config_keys": N, "prompt_overrides": M}
```

**7.11 — Проверка авторизации (негативный тест):**

```bash
curl -s -H "X-API-Key: wrong_key" $BASE/config
# Ожидаем: 401 Unauthorized
```


***

### Шаг 8 — Создать файлы фронтенда

```
СОЗДАТЬ: web_ui/src/types/admin.types.ts
СОЗДАТЬ: web_ui/src/services/adminConfig.service.ts
СОЗДАТЬ: web_ui/src/hooks/useAdminConfig.ts
СОЗДАТЬ: web_ui/src/components/admin/ConfigGroupPanel.tsx
СОЗДАТЬ: web_ui/src/components/admin/PromptEditorPanel.tsx
СОЗДАТЬ: web_ui/src/components/admin/HistoryPanel.tsx
СОЗДАТЬ: web_ui/src/components/admin/AdminPanel.tsx
```

Скопировать код из Секции 6 настоящего ПРД в соответствующие файлы.

**Проверка:** TypeScript-компиляция без ошибок:

```bash
cd bot_psychologist/web_ui
npx tsc --noEmit
# Ожидаем: 0 ошибок
```


***

### Шаг 9 — Зарегистрировать маршрут в роутинге `web_ui`

```
ИЗМЕНИТЬ: web_ui/src/App.tsx (или роутер проекта)
```

Добавить маршрут `/admin` → `<AdminPanel />` согласно Секции 6, Файл 15.

**Проверка:** открыть браузер, перейти на `http://localhost:3000/admin` (или соответствующий порт). Должна отобразиться Admin Config Panel с вкладками.

***

### Шаг 10 — Финальный end-to-end тест

1. Открыть `http://localhost:3000/admin`
2. На вкладке **🤖 LLM** изменить `LLM_TEMPERATURE` на `0.3` → нажать ✓
3. Убедиться, что поле подсвечивается оранжевым бейджем «override»
4. Отправить тестовый запрос к боту через основной UI
5. Открыть вкладку **🕐 История** — должна появиться запись об изменении
6. Нажать ↩ рядом с `LLM_TEMPERATURE` — бейдж должен исчезнуть, значение вернуться к `0.7`
7. На вкладке **📝 Промты** выбрать `🟢 SD: Green` → изменить текст → Сохранить
8. Нажать «Показать оригинал» — слева оригинал из `.md`, справа изменённый текст
9. Нажать ↩ Вернуть оригинал → промт возвращается к дефолту

***

## 8. Definition of Done

Задача считается **полностью выполненной** при соблюдении всех условий:

**Бэкенд:**

- [ ] `RuntimeConfig` наследует `Config`, `__getattribute__` корректно перехватывает только параметры из `EDITABLE_CONFIG`
- [ ] Все class-методы Config (`get_token_param_name`, `supports_custom_temperature` и др.) работают без изменений
- [ ] `admin_overrides.json` создаётся атомарно, корректен при конкурентных запросах
- [ ] Все 11 эндпоинтов `/api/admin/*` возвращают корректные ответы
- [ ] Эндпоинты возвращают `401` при отсутствии или неверном `X-API-Key`
- [ ] Smoke-тесты шагов 7.1–7.11 проходят без ошибок
- [ ] `admin_overrides.json` находится в `.gitignore`, `data/.gitkeep` — в git

**Промты:**

- [ ] Все паттерны прямого чтения `.md` внутри функций заменены на `config.get_prompt(name)["text"]`
- [ ] Глобальные чтения промтов помечены TODO-комментарием
- [ ] Горячая замена промта работает: изменение через UI подхватывается без рестарта

**Фронтенд:**

- [ ] `npx tsc --noEmit` проходит без ошибок TypeScript
- [ ] Все 5 групп конфига (llm, retrieval, memory, storage, runtime) отображаются на соответствующих вкладках
- [ ] Поле `LLM_TEMPERATURE` блокируется при выборе reasoning-модели (gpt-5*, o1, o3, o4)
- [ ] Изменённые параметры подсвечиваются бейджем «override» с отображением дефолтного значения
- [ ] Редактор промтов показывает diff «оригинал / текущая версия» по кнопке
- [ ] Экспорт скачивает JSON-файл, импорт восстанавливает состояние
- [ ] Маршрут `/admin` доступен только при валидном dev-ключе

***

## 9. Что НЕ входит в scope

Следующее намеренно **не реализуется** в этой версии:

- **Редактирование `MODE_MAX_TOKENS`** — тип `dict` требует отдельной UI-логики; оставить на следующую версию
- **Ролевой доступ** — сейчас одна роль `dev`; расширение до нескольких ролей — следующая итерация
- **Версионирование промтов** — история хранит только 50 последних изменений; полный git-like версионинг промтов — отдельная задача
- **Уведомления в реальном времени** (WebSocket/SSE) о применении изменений — следующая итерация
- **Редактирование `OPENAI_API_KEY` и других секретов** — принципиально исключено из UI по соображениям безопасности


