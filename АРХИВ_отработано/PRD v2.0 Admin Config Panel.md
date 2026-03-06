<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Отлично! Исходя из всех твоих полезных замечаний, полностью грамотно и профессионально создай новый ПРД для агента ИДЕ, который выполнит эти задачи!

Теперь у меня полная картина реального кода. Пишу финальный PRD с исправленной архитектурой.

***

# PRD v2.0: Admin Config Panel — управление ботом из фронтенда

**Версия:** 2.0 (финальная, исправленная)
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Корень проекта:** `bot_psychologist/`

***

## 1. Цель

Дать разработчику возможность редактировать все параметры бота и тексты промтов прямо из браузера — без входа на сервер, без правки файлов вручную, без рестарта сервера. Изменения применяются горячо — к следующему запросу пользователя.

***

## 2. Контекст: что важно знать о коде

Перед реализацией агент обязан понять два критических факта о текущем `config.py`:

**Факт 1.** Все параметры в `Config` — это **атрибуты уровня класса**, не инстанса:

```python
class Config:
    TOP_K_BLOCKS = 5          # <- class attribute
    LLM_TEMPERATURE = 0.7     # <- class attribute
```

Это означает: `__getattr__` (как в старом PRD) **никогда не сработает** для этих атрибутов, потому что Python находит их через `type(instance).__mro__` — это «нормальный» lookup, не триггерящий `__getattr__`. Нужен **`__getattribute__`** — он перехватывает ЛЮБОЙ доступ к атрибуту.

**Факт 2.** В конце `config.py` стоит `config = Config()`. Все остальные модули делают `from bot_agent.config import config`. Если мы поменяем только последнюю строку `config.py` на `config = RuntimeConfig()` — все уже существующие импорты получат `RuntimeConfig` автоматически, ничего менять в других файлах не нужно.

***

## 3. Архитектура

### 3.1 Двуслойная модель данных

```
Слой 1 — ДЕФОЛТЫ (git, read-only навсегда):
  bot_agent/config.py           ← Config class attributes
  bot_agent/prompt_*.md         ← 10 файлов промтов

Слой 2 — OVERRIDES (вне git, только запись через API):
  bot_psychologist/data/admin_overrides.json
```

Логика: если в `admin_overrides.json` есть значение → использовать его. Нет — использовать дефолт из `config.py` или `.md`. `config.py` и `.md` файлы **никогда не изменяются программно**.

### 3.2 Структура `admin_overrides.json`

```json
{
  "config": {
    "LLM_TEMPERATURE": 0.5,
    "TOP_K_BLOCKS": 7
  },
  "prompts": {
    "prompt_sd_green": "Изменённый текст промта...",
    "prompt_sd_blue": null
  },
  "meta": {
    "last_modified": "2026-02-28T14:00:00",
    "modified_by": "dev"
  },
  "history": [
    {"key": "LLM_TEMPERATURE", "type": "config", "old": 0.7, "new": 0.5, "timestamp": "2026-02-28T14:00:00"}
  ]
}
```

`null` в `prompts` означает «использовать дефолт из .md». `history` хранит последние 20 изменений.

### 3.3 Решение проблемы circular import

Изменяем **только последнюю строку** `config.py`:

```python
# БЫЛО:
config = Config()

# СТАЛО:
from .runtime_config import RuntimeConfig
config = RuntimeConfig()
```

**Почему это НЕ circular import?** Когда Python доходит до этой строки, класс `Config` уже **полностью определён** в памяти. Когда `runtime_config.py` делает `from .config import Config` — Python видит модуль `config` в `sys.modules` как частично загруженный, но `Config` в нём уже есть. Импорт проходит без ошибок. Это документированное поведение Python для взаимных импортов когда импортируемое имя уже объявлено.

### 3.4 Кэширование на основе `mtime` (критично для скорости)

**Не читать файл при каждом обращении к атрибуту!** Файл читается только когда изменилась дата модификации (`os.path.getmtime`). В штатном режиме — только один вызов `os.stat()` (~1 микросекунда) на каждый атрибут. После сохранения из UI — следующий запрос бота автоматически подхватит новые значения.

***

## 4. Бэкенд — полная реализация

### Файл 1: `bot_psychologist/bot_agent/runtime_config.py` — СОЗДАТЬ

```python
# bot_agent/runtime_config.py
"""
RuntimeConfig — горячая конфигурация с override-слоем из admin_overrides.json.

Наследует Config, перехватывает обращения к редактируемым параметрам через
__getattribute__ и возвращает override-значение если оно есть в JSON-файле.
Кэшует JSON по mtime файла — перечитывает только при изменении.
"""

import json
import os
import tempfile
import logging
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
    """

    OVERRIDES_PATH: Path = Config.PROJECT_ROOT / "data" / "admin_overrides.json"

    # ── Кэш на уровне класса (shared между всеми инстансами, обычно один) ──
    _cache: dict = {}
    _cache_mtime: float = 0.0

    # ── Метаданные редактируемых параметров ──
    # Ключ — имя атрибута Config; значение — схема для UI и валидации
    EDITABLE_CONFIG: dict = {
        # LLM
        "LLM_MODEL": {
            "type": "select",
            "options": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            "group": "llm",
            "label": "Модель GPT"
        },
        "LLM_TEMPERATURE": {
            "type": "float", "min": 0.0, "max": 1.0,
            "group": "llm", "label": "Температура (творчество)"
        },
        "LLM_MAX_TOKENS": {
            "type": "int", "min": 100, "max": 4000,
            "group": "llm", "label": "Макс. токенов в ответе"
        },
        # Retrieval
        "TOP_K_BLOCKS": {
            "type": "int", "min": 1, "max": 20,
            "group": "retrieval", "label": "Кол-во блоков (TOP-K)"
        },
        "MIN_RELEVANCE_SCORE": {
            "type": "float", "min": 0.0, "max": 1.0,
            "group": "retrieval", "label": "Мин. порог релевантности"
        },
        "VOYAGE_ENABLED": {
            "type": "bool",
            "group": "retrieval", "label": "Включить Voyage Rerank"
        },
        "VOYAGE_TOP_K": {
            "type": "int", "min": 1, "max": 10,
            "group": "retrieval", "label": "Voyage TOP-K"
        },
        # Memory
        "CONVERSATION_HISTORY_DEPTH": {
            "type": "int", "min": 1, "max": 20,
            "group": "memory", "label": "Глубина истории диалога"
        },
        "MAX_CONTEXT_SIZE": {
            "type": "int", "min": 500, "max": 8000,
            "group": "memory", "label": "Макс. размер контекста (симв.)"
        },
        "MAX_CONVERSATION_TURNS": {
            "type": "int", "min": 10, "max": 5000,
            "group": "memory", "label": "Макс. ходов диалога"
        },
        "ENABLE_SEMANTIC_MEMORY": {
            "type": "bool",
            "group": "memory", "label": "Семантическая память"
        },
        "SEMANTIC_SEARCH_TOP_K": {
            "type": "int", "min": 1, "max": 10,
            "group": "memory", "label": "Семантика: TOP-K"
        },
        "SEMANTIC_MIN_SIMILARITY": {
            "type": "float", "min": 0.0, "max": 1.0,
            "group": "memory", "label": "Семантика: мин. сходство"
        },
        "SEMANTIC_MAX_CHARS": {
            "type": "int", "min": 100, "max": 3000,
            "group": "memory", "label": "Семантика: макс. символов"
        },
        "ENABLE_CONVERSATION_SUMMARY": {
            "type": "bool",
            "group": "memory", "label": "Суммаризация диалога"
        },
        "SUMMARY_UPDATE_INTERVAL": {
            "type": "int", "min": 1, "max": 50,
            "group": "memory", "label": "Интервал обновления резюме (ходы)"
        },
        "SUMMARY_MAX_CHARS": {
            "type": "int", "min": 100, "max": 2000,
            "group": "memory", "label": "Макс. длина резюме (симв.)"
        },
        # Storage
        "SESSION_RETENTION_DAYS": {
            "type": "int", "min": 1, "max": 365,
            "group": "storage", "label": "Хранить сессии (дней)"
        },
        "ARCHIVE_RETENTION_DAYS": {
            "type": "int", "min": 1, "max": 730,
            "group": "storage", "label": "Хранить архив (дней)"
        },
        "AUTO_CLEANUP_ENABLED": {
            "type": "bool",
            "group": "storage", "label": "Авто-очистка старых сессий"
        },
    }

    # Список промтов доступных для редактирования (совпадает с именами .md файлов без расширения)
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
        "prompt_sd_green":                  "🟢 SD: Green",
        "prompt_sd_blue":                   "🔵 SD: Blue",
        "prompt_sd_red":                    "🔴 SD: Red",
        "prompt_sd_orange":                 "🟠 SD: Orange",
        "prompt_sd_yellow":                 "🟡 SD: Yellow",
        "prompt_sd_purple":                 "🟣 SD: Purple",
        "prompt_system_level_beginner":     "📗 Уровень: Начальный",
        "prompt_system_level_intermediate": "📘 Уровень: Средний",
        "prompt_system_level_advanced":     "📙 Уровень: Продвинутый",
    }

    # ── Имена атрибутов ИСКЛЮЧЁННЫХ из перехвата (чувствительные / требуют рестарта) ──
    _BYPASS_ATTRS: frozenset = frozenset({
        "OPENAI_API_KEY", "VOYAGE_API_KEY", "BOT_DB_PATH",
        "EMBEDDING_MODEL", "PROJECT_ROOT", "BOT_AGENT_ROOT",
        "DATA_ROOT", "SAG_FINAL_DIR", "CACHE_DIR", "LOG_DIR",
        "OVERRIDES_PATH", "EDITABLE_CONFIG", "EDITABLE_PROMPTS",
        "PROMPT_LABELS", "_BYPASS_ATTRS", "_cache", "_cache_mtime",
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
        # Никогда не перехватываем: приватное, системное, спецметоды
        if name.startswith("_") or name.startswith("__"):
            return object.__getattribute__(self, name)

        # Никогда не перехватываем чувствительные / служебные атрибуты
        bypass = object.__getattribute__(self, "_BYPASS_ATTRS")
        if name in bypass:
            return object.__getattribute__(self, name)

        # Проверяем: является ли имя редактируемым параметром?
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
                logger.warning(f"[RuntimeConfig] Override read failed for '{name}': {exc}")

        return object.__getattribute__(self, name)

    # ════════════════════════════════════════════════════════════
    # КЭШИРОВАННОЕ ЧТЕНИЕ ФАЙЛА (mtime-based, ~1μs в штатном режиме)
    # ════════════════════════════════════════════════════════════

    def _load_overrides(self) -> dict:
        """
        Читает admin_overrides.json с кэшированием по mtime.
        Перечитывает файл только если он изменился с последнего чтения.
        Производительность: ~1μs (stat) если файл не менялся.
        """
        path = object.__getattribute__(self, "OVERRIDES_PATH")
        try:
            mtime = os.path.getmtime(path)
            if mtime != RuntimeConfig._cache_mtime:
                with open(path, "r", encoding="utf-8") as f:
                    RuntimeConfig._cache = json.load(f)
                RuntimeConfig._cache_mtime = mtime
            return RuntimeConfig._cache
        except FileNotFoundError:
            return {"config": {}, "prompts": {}, "meta": {}, "history": []}
        except Exception as exc:
            logger.error(f"[RuntimeConfig] Failed to load overrides: {exc}")
            return {"config": {}, "prompts": {}, "meta": {}, "history": []}

    def _save_overrides(self, data: dict) -> None:
        """
        Атомарная запись через temp-файл + rename.
        Обновляет meta.last_modified и сбрасывает кэш.
        """
        path = object.__getattribute__(self, "OVERRIDES_PATH")
        path.parent.mkdir(parents=True, exist_ok=True)

        data.setdefault("config", {})
        data.setdefault("prompts", {})
        data.setdefault("history", [])
        data["meta"] = {
            "last_modified": datetime.now().isoformat(),
            "modified_by": "dev",
        }

        # Атомарная запись: пишем в tmp рядом с целевым файлом
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=".admin_overrides_", suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)  # атомарная замена на POSIX и Windows
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Сбрасываем кэш — следующий _load_overrides() подхватит новый файл
        RuntimeConfig._cache_mtime = 0.0

    def _append_history(self, data: dict, key: str, type_: str, old, new) -> None:
        """Добавляет запись в историю изменений, хранит последние 20."""
        history = data.get("history", [])
        history.append({
            "key": key,
            "type": type_,
            "old": old,
            "new": new,
            "timestamp": datetime.now().isoformat(),
        })
        data["history"] = history[-20:]  # храним последние 20

    # ════════════════════════════════════════════════════════════
    # CONFIG: PUBLIC API
    # ════════════════════════════════════════════════════════════

    def get_all_config(self) -> dict:
        """
        Возвращает все редактируемые параметры с метаданными.
        Сгруппировано для рендера в UI.

        Returns:
            {
                "groups": {
                    "llm": {
                        "label": "🤖 LLM",
                        "params": {
                            "LLM_TEMPERATURE": {
                                "value": 0.5,       # текущее (с override)
                                "default": 0.7,     # из Config class
                                "is_overridden": True,
                                "type": "float",
                                "min": 0.0, "max": 1.0,
                                "group": "llm",
                                "label": "..."
                            }, ...
                        }
                    }, ...
                }
            }
        """
        overrides = self._load_overrides().get("config", {})
        editable = object.__getattribute__(self, "EDITABLE_CONFIG")

        group_labels = {
            "llm":       "🤖 LLM",
            "retrieval": "🔍 Поиск и ретривал",
            "memory":    "🧠 Память",
            "storage":   "🗄️ Хранилище",
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
            current_val = self.__getattribute__(key)  # через наш перехватчик

            param = {
                "value": current_val,
                "default": default_val,
                "is_overridden": is_overridden,
                **meta,
            }
            groups[group]["params"][key] = param

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
                raise ValueError(f"'{key}' должен быть в [{meta['min']}, {meta['max']}], получено {value}")
        elif t == "float":
            value = float(value)
            if not (meta["min"] <= value <= meta["max"]):
                raise ValueError(f"'{key}' должен быть в [{meta['min']:.2f}, {meta['max']:.2f}], получено {value:.2f}")
        elif t == "bool":
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            else:
                value = bool(value)
        elif t == "select":
            value = str(value)
            if value not in meta["options"]:
                raise ValueError(f"'{key}' должен быть одним из {meta['options']}, получено '{value}'")
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

    def reset_config_override(self, key: str) -> None:
        """Удаляет override параметра — возвращает к дефолту из Config."""
        editable = object.__getattribute__(self, "EDITABLE_CONFIG")
        if key not in editable:
            raise ValueError(f"Параметр '{key}' не является редактируемым")

        data = self._load_overrides()
        old_value = data.get("config", {}).pop(key, None)
        if old_value is not None:
            self._append_history(data, key, "config_reset", old_value, getattr(Config, key, None))
        self._save_overrides(data)

    def reset_all_config_overrides(self) -> None:
        """Сбрасывает все параметры к дефолтам (промты не трогает)."""
        data = self._load_overrides()
        data["config"] = {}
        self._save_overrides(data)

    # ════════════════════════════════════════════════════════════
    # PROMPTS: PUBLIC API
    # ════════════════════════════════════════════════════════════

    def _read_default_prompt(self, name: str) -> str:
        """Читает дефолтный текст промта из .md файла."""
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
                "text": str,           # актуальный текст (override или дефолт)
                "default_text": str,   # оригинал из .md
                "is_overridden": bool
            }
        """
        editable_prompts = object.__getattribute__(self, "EDITABLE_PROMPTS")
        if name not in editable_prompts:
            raise ValueError(f"Промт '{name}' не является редактируемым")

        prompt_labels = object.__getattribute__(self, "PROMPT_LABELS")
        default_text = self._read_default_prompt(name)
        overrides = self._load_overrides().get("prompts", {})
        override_text = overrides.get(name)

        return {
            "name": name,
            "label": prompt_labels.get(name, name),
            "text": override_text if (override_text is not None) else default_text,
            "default_text": default_text,
            "is_overridden": override_text is not None,
        }

    def get_all_prompts(self) -> list:
        """
        Список всех промтов с превью (первые 120 символов).
        Используется для рендера списка в UI.
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
                "preview": active_text[:120].replace("\n", " "),
                "is_overridden": is_overridden,
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
        old_text = data.get("prompts", {}).get(name)
        data.setdefault("prompts", {})[name] = text
        self._append_history(data, name, "prompt", bool(old_text), True)
        self._save_overrides(data)
        return self.get_prompt(name)

    def reset_prompt_override(self, name: str) -> dict:
        """Сбрасывает промт к дефолту (удаляет override)."""
        editable_prompts = object.__getattribute__(self, "EDITABLE_PROMPTS")
        if name not in editable_prompts:
            raise ValueError(f"Промт '{name}' не является редактируемым")

        data = self._load_overrides()
        data.setdefault("prompts", {})[name] = None
        self._append_history(data, name, "prompt_reset", True, False)
        self._save_overrides(data)
        return self.get_prompt(name)

    def reset_all_prompt_overrides(self) -> None:
        """Сбрасывает все промты к дефолтам (config не трогает)."""
        data = self._load_overrides()
        data["prompts"] = {}
        self._save_overrides(data)

    def reset_all_overrides(self) -> None:
        """Полный сброс — и config, и промты."""
        data = {"config": {}, "prompts": {}, "history": [], "meta": {}}
        self._save_overrides(data)

    def get_history(self) -> list:
        """Последние 20 изменений для отображения в UI."""
        return self._load_overrides().get("history", [])
```


***

### Файл 2: `bot_psychologist/bot_agent/config.py` — ИЗМЕНИТЬ ТОЛЬКО ПОСЛЕДНЮЮ СТРОКУ

Найти в самом конце файла строку:

```python
# Глобальный инстанс конфига
config = Config()
```

Заменить на:

```python
# Глобальный инстанс конфига
# RuntimeConfig наследует Config и добавляет горячий override-слой.
# Circular import безопасен: класс Config уже определён выше по файлу,
# поэтому runtime_config.py успешно импортирует его из частично
# загруженного модуля (стандартное поведение Python для cross-imports).
from .runtime_config import RuntimeConfig
config = RuntimeConfig()
```

**Больше в `config.py` ничего не менять.** Все другие модули делают `from bot_agent.config import config` — они автоматически получат `RuntimeConfig`.

***

### Файл 3: Промты в `answer_*.py` — НАЙТИ И ОБНОВИТЬ

**Задача агента:** найти во всех файлах `bot_agent/answer_*.py`, `bot_agent/llm_answerer.py`, `bot_agent/sd_classifier.py`, `bot_agent/state_classifier.py` паттерн чтения `.md` файлов промтов и заменить на вызов `config.get_prompt()`.

**Паттерн для поиска** (все варианты):

```python
# Вариант A
(Path(__file__).parent / "prompt_XXX.md").read_text(encoding="utf-8")

# Вариант B
open(.../ "prompt_XXX.md").read()

# Вариант C
with open(... / f"prompt_{something}.md") as f:
    prompt = f.read()
```

**Замена на:**

```python
from bot_agent.config import config
# ...
prompt_text = config.get_prompt("prompt_XXX")["text"]
```

**Если промт читается внутри функции каждый вызов** — это нормально, `get_prompt()` быстрый (mtime-кэш).

**Если промт читается один раз при импорте модуля** (в глобальной области) — оставить как есть, но добавить TODO-комментарий что это не hot-reloadable. Менять только те, что внутри функций.

***

### Файл 4: `bot_psychologist/api/routes.py` — ДОБАВИТЬ в конец файла

Добавить после последнего существующего эндпоинта (`/health`). Новый роутер для admin-эндпоинтов:

```python
# ===== ADMIN CONFIG ENDPOINTS =====
# Все эндпоинты требуют dev-ключ. Используем существующую is_dev_key из auth.py

from fastapi import Header
from typing import Any

def _require_dev(x_api_key: str = Header(..., alias="X-API-Key")):
    """Dependency: доступ только для dev-ключа."""
    from .auth import is_dev_key
    if not is_dev_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Только для режима разработчика"
        )

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─── Config: READ ───

@admin_router.get("/config", summary="Все параметры конфига")
async def admin_get_config(_=Depends(_require_dev)):
    """Возвращает все редактируемые параметры конфига сгруппированными."""
    return config.get_all_config()


# ─── Config: WRITE ───

@admin_router.put("/config", summary="Сохранить один параметр")
async def admin_set_config(body: dict, _=Depends(_require_dev)):
    """
    Body: {"key": "LLM_TEMPERATURE", "value": 0.5}
    Валидирует тип и диапазон, сохраняет override.
    """
    key = body.get("key")
    value = body.get("value")
    if not key:
        raise HTTPException(status_code=422, detail="Поле 'key' обязательно")
    try:
        return config.set_config_override(key, value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.delete("/config/{key}", summary="Сбросить один параметр к дефолту")
async def admin_reset_config_param(key: str, _=Depends(_require_dev)):
    try:
        config.reset_config_override(key)
        return {"status": "reset", "key": key}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.post("/config/reset-all", summary="Сбросить все параметры")
async def admin_reset_all_config(_=Depends(_require_dev)):
    config.reset_all_config_overrides()
    return {"status": "all config overrides reset"}


# ─── Prompts: READ ───

@admin_router.get("/prompts", summary="Список всех промтов")
async def admin_get_prompts(_=Depends(_require_dev)):
    """Возвращает список всех промтов с превью и флагом is_overridden."""
    return config.get_all_prompts()


@admin_router.get("/prompts/{name}", summary="Полный текст промта")
async def admin_get_prompt(name: str, _=Depends(_require_dev)):
    """Возвращает текущий и дефолтный текст промта."""
    try:
        return config.get_prompt(name)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Prompts: WRITE ───

@admin_router.put("/prompts/{name}", summary="Сохранить текст промта")
async def admin_set_prompt(name: str, body: dict, _=Depends(_require_dev)):
    """Body: {"text": "новый текст..."}"""
    text = body.get("text", "")
    try:
        return config.set_prompt_override(name, text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.delete("/prompts/{name}", summary="Сбросить промт к дефолту")
async def admin_reset_prompt(name: str, _=Depends(_require_dev)):
    try:
        return config.reset_prompt_override(name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.post("/prompts/reset-all", summary="Сбросить все промты")
async def admin_reset_all_prompts(_=Depends(_require_dev)):
    config.reset_all_prompt_overrides()
    return {"status": "all prompt overrides reset"}


# ─── History ───

@admin_router.get("/history", summary="История изменений (последние 20)")
async def admin_get_history(_=Depends(_require_dev)):
    return {"history": config.get_history()}


# ─── Export / Import ───

@admin_router.get("/export", summary="Скачать admin_overrides.json")
async def admin_export_overrides(_=Depends(_require_dev)):
    """Возвращает полный JSON для резервного копирования / переноса."""
    return config._load_overrides()


@admin_router.post("/import", summary="Загрузить admin_overrides.json")
async def admin_import_overrides(body: dict, _=Depends(_require_dev)):
    """
    Загружает overrides из тела запроса.
    Валидирует структуру перед сохранением.
    """
    if not isinstance(body.get("config"), dict):
        raise HTTPException(status_code=422, detail="Поле 'config' должно быть объектом")
    if not isinstance(body.get("prompts"), dict):
        raise HTTPException(status_code=422, detail="Поле 'prompts' должно быть объектом")
    try:
        config._save_overrides(body)
        return {"status": "imported", "keys_count": len(body.get("config", {}))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**После добавления эндпоинтов**, найти в `routes.py` место где регистрируется основной роутер (скорее всего в `app.py` или `main.py`), и добавить туда:

```python
from api.routes import admin_router
app.include_router(admin_router)
```


***

### Файл 5: `bot_psychologist/data/.gitkeep` — СОЗДАТЬ

Создать пустой файл `bot_psychologist/data/.gitkeep`.

Добавить в `.gitignore` проекта:

```
bot_psychologist/data/admin_overrides.json
```


***

## 5. Фронтенд — полная реализация

### Файл 6: `web_ui/src/types/admin.types.ts` — СОЗДАТЬ

```typescript
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
}

export interface PromptDetail extends PromptMeta {
  text: string;
  default_text: string;
}

export interface HistoryEntry {
  key: string;
  type: 'config' | 'config_reset' | 'prompt' | 'prompt_reset';
  old: unknown;
  new: unknown;
  timestamp: string;
}
```


***

### Файл 7: `web_ui/src/services/adminConfig.service.ts` — СОЗДАТЬ

```typescript
import { apiService } from './api.service';
import type {
  AdminConfigResponse, ConfigParam,
  PromptMeta, PromptDetail, HistoryEntry
} from '../types/admin.types';

const BASE = '/api/admin';

function devHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': apiService.getAPIKey() ?? '',
  };
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: devHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const adminConfigService = {
  // Config
  getConfig: () => request<AdminConfigResponse>('GET', '/config'),
  setConfigParam: (key: string, value: unknown) =>
    request<ConfigParam>('PUT', '/config', { key, value }),
  resetConfigParam: (key: string) => request<void>('DELETE', `/config/${key}`),
  resetAllConfig: () => request<void>('POST', '/config/reset-all'),

  // Prompts
  getPrompts: () => request<PromptMeta[]>('GET', '/prompts'),
  getPrompt: (name: string) => request<PromptDetail>('GET', `/prompts/${name}`),
  setPrompt: (name: string, text: string) =>
    request<PromptDetail>('PUT', `/prompts/${name}`, { text }),
  resetPrompt: (name: string) => request<PromptDetail>('DELETE', `/prompts/${name}`),
  resetAllPrompts: () => request<void>('POST', '/prompts/reset-all'),

  // History & Export
  getHistory: () => request<{ history: HistoryEntry[] }>('GET', '/history'),
  exportOverrides: () => request<object>('GET', '/export'),
  importOverrides: (data: object) => request<void>('POST', '/import', data),
};
```


***

### Файл 8: `web_ui/src/hooks/useAdminConfig.ts` — СОЗДАТЬ

```typescript
import { useState, useCallback } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type { AdminConfigResponse, PromptMeta, PromptDetail } from '../types/admin.types';

export const useAdminConfig = () => {
  const [configGroups, setConfigGroups] = useState<AdminConfigResponse | null>(null);
  const [prompts, setPrompts] = useState<PromptMeta[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = (msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 2500);
  };

  const loadConfig = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminConfigService.getConfig();
      setConfigGroups(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadPrompts = useCallback(async () => {
    try {
      const data = await adminConfigService.getPrompts();
      setPrompts(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const loadPromptDetail = useCallback(async (name: string) => {
    try {
      const data = await adminConfigService.getPrompt(name);
      setSelectedPrompt(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const saveConfigParam = useCallback(async (key: string, value: unknown) => {
    setIsSaving(true);
    try {
      await adminConfigService.setConfigParam(key, value);
      await loadConfig();
      showSuccess(`✓ ${key} сохранён`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [loadConfig]);

  const resetConfigParam = useCallback(async (key: string) => {
    setIsSaving(true);
    try {
      await adminConfigService.resetConfigParam(key);
      await loadConfig();
      showSuccess(`↩ ${key} сброшен к дефолту`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [loadConfig]);

  const resetAllConfig = useCallback(async () => {
    if (!confirm('Сбросить ВСЕ параметры к дефолтам?')) return;
    setIsSaving(true);
    try {
      await adminConfigService.resetAllConfig();
      await loadConfig();
      showSuccess('↩ Все параметры сброшены');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [loadConfig]);

  const savePrompt = useCallback(async (name: string, text: string) => {
    setIsSaving(true);
    try {
      const updated = await adminConfigService.setPrompt(name, text);
      setSelectedPrompt(updated);
      await loadPrompts();
      showSuccess('✓ Промт сохранён');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [loadPrompts]);

  const resetPrompt = useCallback(async (name: string) => {
    if (!confirm('Сбросить промт к дефолту?')) return;
    setIsSaving(true);
    try {
      const updated = await adminConfigService.resetPrompt(name);
      setSelectedPrompt(updated);
      await loadPrompts();
      showSuccess('↩ Промт сброшен к дефолту');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [loadPrompts]);

  const resetAllPrompts = useCallback(async () => {
    if (!confirm('Сбросить ВСЕ промты к дефолтам?')) return;
    setIsSaving(true);
    try {
      await adminConfigService.resetAllPrompts();
      await loadPrompts();
      if (selectedPrompt) await loadPromptDetail(selectedPrompt.name);
      showSuccess('↩ Все промты сброшены');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [loadPrompts, selectedPrompt, loadPromptDetail]);

  return {
    configGroups, prompts, selectedPrompt,
    isLoading, isSaving, error, successMessage,
    loadConfig, loadPrompts, loadPromptDetail,
    saveConfigParam, resetConfigParam, resetAllConfig,
    savePrompt, resetPrompt, resetAllPrompts,
  };
};
```


***

### Файл 9: `web_ui/src/components/admin/ConfigGroupPanel.tsx` — СОЗДАТЬ

```tsx
import React, { useState, useEffect } from 'react';
import type { ConfigGroup } from '../../types/admin.types';

interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
}

export const ConfigGroupPanel: React.FC<Props> = ({
  groupKey, group, onSave, onReset, isSaving
}) => {
  // Локальные черновики значений (до нажатия Сохранить)
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set());

  // Инициализируем черновики из текущих значений
  useEffect(() => {
    const init: Record<string, unknown> = {};
    Object.entries(group.params).forEach(([key, param]) => {
      init[key] = param.value;
    });
    setDrafts(init);
    setDirtyKeys(new Set());
  }, [group]);

  const handleChange = (key: string, value: unknown) => {
    setDrafts(prev => ({ ...prev, [key]: value }));
    setDirtyKeys(prev => new Set(prev).add(key));
  };

  const handleSaveOne = async (key: string) => {
    await onSave(key, drafts[key]);
    setDirtyKeys(prev => {
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

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">{group.label}</h2>
        <div className="flex gap-2">
          {dirtyKeys.size > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={isSaving}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              💾 Сохранить изменения ({dirtyKeys.size})
            </button>
          )}
        </div>
      </div>

      {Object.entries(group.params).map(([key, param]) => {
        const isDirty = dirtyKeys.has(key);
        const draftVal = drafts[key] ?? param.value;

        return (
          <div
            key={key}
            className={`p-3 rounded border ${
              param.is_overridden
                ? 'border-l-4 border-l-blue-500 border-gray-200 bg-blue-50'
                : 'border-gray-200'
            }`}
          >
            <div className="flex justify-between items-start mb-1">
              <label className="text-sm font-medium text-gray-700">
                {param.label}
                {param.is_overridden && (
                  <span className="ml-2 text-xs text-blue-600 font-bold">● изменено</span>
                )}
                {isDirty && (
                  <span className="ml-2 text-xs text-yellow-600">● несохранено</span>
                )}
              </label>
              <div className="flex gap-1">
                {isDirty && (
                  <button
                    onClick={() => handleSaveOne(key)}
                    disabled={isSaving}
                    className="text-xs px-2 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    💾
                  </button>
                )}
                {param.is_overridden && (
                  <button
                    onClick={() => onReset(key)}
                    disabled={isSaving}
                    className="text-xs px-2 py-0.5 bg-gray-200 text-gray-600 rounded hover:bg-gray-300 disabled:opacity-50"
                    title="Сбросить к дефолту"
                  >
                    ↩
                  </button>
                )}
              </div>
            </div>

            {/* Инпут в зависимости от типа */}
            {param.type === 'bool' && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={Boolean(draftVal)}
                  onChange={e => handleChange(key, e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">{draftVal ? 'Включено' : 'Выключено'}</span>
              </label>
            )}

            {param.type === 'select' && (
              <select
                value={String(draftVal)}
                onChange={e => handleChange(key, e.target.value)}
                className="w-full text-sm border rounded px-2 py-1"
              >
                {param.options?.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            )}

            {param.type === 'int' && (
              <input
                type="number"
                min={param.min}
                max={param.max}
                step={1}
                value={Number(draftVal)}
                onChange={e => handleChange(key, parseInt(e.target.value, 10))}
                className="w-full text-sm border rounded px-2 py-1"
              />
            )}

            {param.type === 'float' && (
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={param.min}
                  max={param.max}
                  step={0.01}
                  value={Number(draftVal)}
                  onChange={e => handleChange(key, parseFloat(e.target.value))}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={param.min}
                  max={param.max}
                  step={0.01}
                  value={Number(draftVal).toFixed(2)}
                  onChange={e => handleChange(key, parseFloat(e.target.value))}
                  className="w-20 text-sm border rounded px-2 py-1"
                />
              </div>
            )}

            <p className="text-xs text-gray-400 mt-1">
              По умолчанию: <code>{String(param.default)}</code>
              {param.type !== 'bool' && param.type !== 'select' && param.min !== undefined && (
                <> · Диапазон: [{param.min}, {param.max}]</>
              )}
            </p>
          </div>
        );
      })}
    </div>
  );
};
```


***

### Файл 10: `web_ui/src/components/admin/PromptsPanel.tsx` — СОЗДАТЬ

```tsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { PromptMeta, PromptDetail } from '../../types/admin.types';

interface Props {
  prompts: PromptMeta[];
  selectedPrompt: PromptDetail | null;
  onSelect: (name: string) => void;
  onSave: (name: string, text: string) => Promise<void>;
  onReset: (name: string) => Promise<void>;
  onResetAll: () => Promise<void>;
  isSaving: boolean;
}

export const PromptsPanel: React.FC<Props> = ({
  prompts, selectedPrompt, onSelect, onSave, onReset, onResetAll, isSaving
}) => {
  const [draftText, setDraftText] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [showDefault, setShowDefault] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (selectedPrompt) {
      setDraftText(selectedPrompt.text);
      setIsDirty(false);
      setShowDefault(false);
    }
  }, [selectedPrompt]);

  const handleTextChange = (val: string) => {
    setDraftText(val);
    setIsDirty(val !== selectedPrompt?.text);
  };

  const handleSave = useCallback(async () => {
    if (!selectedPrompt || !isDirty) return;
    await onSave(selectedPrompt.name, draftText);
    setIsDirty(false);
  }, [selectedPrompt, draftText, isDirty, onSave]);

  // Ctrl+S для сохранения
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSave]);

  return (
    <div className="flex gap-4 h-full">
      {/* Левая колонка — список промтов */}
      <div className="w-64 flex-shrink-0 border-r pr-3">
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-sm">Промты</h3>
          <button
            onClick={onResetAll}
            disabled={isSaving}
            className="text-xs text-gray-500 hover:text-red-600"
          >
            ↩ Все к дефолту
          </button>
        </div>
        <div className="space-y-1">
          {prompts.map(p => (
            <button
              key={p.name}
              onClick={() => onSelect(p.name)}
              className={`w-full text-left px-2 py-2 rounded text-sm ${
                selectedPrompt?.name === p.name
                  ? 'bg-blue-100 text-blue-800'
                  : 'hover:bg-gray-100'
              }`}
            >
              <div className="flex justify-between items-center">
                <span>{p.label}</span>
                {p.is_overridden && (
                  <span className="text-xs text-blue-600">●</span>
                )}
              </div>
              <p className="text-xs text-gray-400 truncate mt-0.5">{p.preview}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Правая панель — редактор */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedPrompt ? (
          <>
            <div className="flex justify-between items-center mb-2">
              <div>
                <h3 className="font-semibold">{selectedPrompt.label}</h3>
                {selectedPrompt.is_overridden && (
                  <span className="text-xs text-blue-600 font-bold">● ИЗМЕНЁН</span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDefault(v => !v)}
                  className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-50"
                >
                  👁 {showDefault ? 'Скрыть дефолт' : 'Показать дефолт'}
                </button>
                <button
                  onClick={() => onReset(selectedPrompt.name)}
                  disabled={isSaving || !selectedPrompt.is_overridden}
                  className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                >
                  ↩ Сбросить
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving || !isDirty}
                  className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
                >
                  💾 Сохранить {isDirty && '(Ctrl+S)'}
                </button>
              </div>
            </div>

            {isDirty && (
              <div className="mb-2 px-3 py-1.5 bg-yellow-50 border border-yellow-300 rounded text-xs text-yellow-700">
                ⚠ Есть несохранённые изменения
              </div>
            )}

            <textarea
              ref={textareaRef}
              value={draftText}
              onChange={e => handleTextChange(e.target.value)}
              className="flex-1 w-full font-mono text-sm border rounded p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
              style={{ minHeight: '300px' }}
              placeholder="Текст промта..."
              spellCheck={false}
            />

            {showDefault && (
              <div className="mt-3">
                <p className="text-xs text-gray-500 mb-1">Оригинал из файла (read-only):</p>
                <pre className="text-xs font-mono bg-gray-50 border rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
                  {selectedPrompt.default_text}
                </pre>
              </div>
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

### Файл 11: `web_ui/src/pages/AdminSettingsPage.tsx` — СОЗДАТЬ

```tsx
import React, { useEffect, useState } from 'react';
import { useAdminConfig } from '../hooks/useAdminConfig';
import { ConfigGroupPanel } from '../components/admin/ConfigGroupPanel';
import { PromptsPanel } from '../components/admin/PromptsPanel';
import { apiService } from '../services/api.service';

type Tab = 'llm' | 'retrieval' | 'memory' | 'storage' | 'prompts' | 'history';

const TAB_ORDER: Tab[] = ['llm', 'retrieval', 'memory', 'storage', 'prompts', 'history'];

const TAB_LABELS: Record<Tab, string> = {
  llm:       '🤖 LLM',
  retrieval: '🔍 Поиск',
  memory:    '🧠 Память',
  storage:   '🗄️ Хранилище',
  prompts:   '📝 Промты',
  history:   '📋 История',
};

export const AdminSettingsPage: React.FC = () => {
  const isDevMode = apiService.getAPIKey() === 'dev-key-001';

  const [activeTab, setActiveTab] = useState<Tab>(() => {
    return (localStorage.getItem('admin_settings_tab') as Tab) || 'llm';
  });
  const [historyData, setHistoryData] = useState<unknown[]>([]);

  const {
    configGroups, prompts, selectedPrompt,
    isLoading, isSaving, error, successMessage,
    loadConfig, loadPrompts, loadPromptDetail,
    saveConfigParam, resetConfigParam, resetAllConfig,
    savePrompt, resetPrompt, resetAllPrompts,
  } = useAdminConfig();

  useEffect(() => {
    if (!isDevMode) return;
    loadConfig();
    loadPrompts();
  }, []);

  useEffect(() => {
    localStorage.setItem('admin_settings_tab', activeTab);
    if (activeTab === 'history') {
      import('../services/adminConfig.service').then(({ adminConfigService }) => {
        adminConfigService.getHistory().then(r => setHistoryData(r.history));
      });
    }
  }, [activeTab]);

  if (!isDevMode) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-3">🔒</div>
          <p className="font-semibold">Только для режима разработчика</p>
          <p className="text-sm">Введите dev-ключ для доступа к настройкам</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-44 flex-shrink-0 border-r bg-gray-50 p-3">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-3">Настройки бота</p>
        {TAB_ORDER.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`w-full text-left px-3 py-2 rounded text-sm mb-1 ${
              activeTab === tab
                ? 'bg-blue-600 text-white'
                : 'text-gray-700 hover:bg-gray-200'
            }`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 p-5 overflow-auto">
        {/* Toast сообщения */}
        {successMessage && (
          <div className="mb-3 px-4 py-2 bg-green-100 border border-green-300 rounded text-green-700 text-sm">
            {successMessage}
          </div>
        )}
        {error && (
          <div className="mb-3 px-4 py-2 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
            ❌ {error}
          </div>
        )}

        {isLoading ? (
          <div className="text-gray-400 text-sm">Загрузка...</div>
        ) : activeTab === 'prompts' ? (
          <PromptsPanel
            prompts={prompts}
            selectedPrompt={selectedPrompt}
            onSelect={loadPromptDetail}
            onSave={savePrompt}
            onReset={resetPrompt}
            onResetAll={resetAllPrompts}
            isSaving={isSaving}
          />
        ) : activeTab === 'history' ? (
          <div>
            <h2 className="text-lg font-semibold mb-4">📋 История изменений</h2>
            {historyData.length === 0 ? (
              <p className="text-gray-400 text-sm">Изменений пока нет</p>
            ) : (
              <div className="space-y-2">
                {[...historyData].reverse().map((entry: any, i) => (
                  <div key={i} className="flex gap-3 text-sm border-b pb-2">
                    <span className="text-gray-400 text-xs w-36 flex-shrink-0">
                      {new Date(entry.timestamp).toLocaleString('ru')}
                    </span>
                    <span className={`w-20 text-xs font-mono ${
                      entry.type.includes('reset') ? 'text-gray-500' : 'text-blue-600'
                    }`}>
                      {entry.type}
                    </span>
                    <span className="font-mono text-xs text-gray-700">{entry.key}</span>
                    <span className="text-gray-500 text-xs">
                      {String(entry.old)} → {String(entry.new)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          configGroups?.groups[activeTab] ? (
            <ConfigGroupPanel
              groupKey={activeTab}
              group={configGroups.groups[activeTab]}
              onSave={saveConfigParam}
              onReset={resetConfigParam}
              isSaving={isSaving}
            />
          ) : (
            <div className="text-gray-400 text-sm">Нет данных для этой группы</div>
          )
        )}
      </div>
    </div>
  );
};
```


***

### Файл 12: `web_ui/src/App.tsx` — ДОБАВИТЬ роут

Найти файл `App.tsx`. Добавить:

```tsx
// В блок импортов:
import { AdminSettingsPage } from './pages/AdminSettingsPage';

// В блок Routes (внутри <Routes>...</Routes>):
<Route path="/admin/settings" element={<AdminSettingsPage />} />
```


***

### Файл 13: `Sidebar.tsx` (или компонент навигации) — ДОБАВИТЬ ссылку

Найти компонент сайдбара/навигации. Добавить ссылку видимую только в dev-режиме:

```tsx
import { apiService } from '../../services/api.service';
// ...
const isDevMode = apiService.getAPIKey() === 'dev-key-001';
// ...
{isDevMode && (
  <NavLink
    to="/admin/settings"
    className={({ isActive }) =>
      `flex items-center gap-2 px-3 py-2 rounded text-sm ${
        isActive ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
      }`
    }
  >
    ⚙️ Настройки бота
  </NavLink>
)}
```


***

## 6. Безопасность

- Все `/api/admin/*` эндпоинты проверяют `X-API-Key` через `_require_dev` dependency.
- Страница `/admin/settings` не отображается без dev-ключа.
- Параметры `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `BOT_DB_PATH`, `EMBEDDING_MODEL` **не включены** в `EDITABLE_CONFIG` и не могут быть изменены через UI.
- `admin_overrides.json` добавлен в `.gitignore` — никогда не попадёт в репозиторий.

***

## 7. Порядок выполнения для агента (строго последовательно)

1. Создать `bot_psychologist/data/.gitkeep` и добавить строку в `.gitignore`
2. Создать `bot_psychologist/bot_agent/runtime_config.py` (полный код из раздела 4, Файл 1)
3. Изменить последние 2 строки `bot_psychologist/bot_agent/config.py` (Файл 2)
4. Найти все чтения `.md` файлов промтов в `answer_*.py` и заменить на `config.get_prompt()` (Файл 3)
5. Добавить admin-эндпоинты в конец `bot_psychologist/api/routes.py` (Файл 4)
6. Найти файл `main.py` / `app.py` где создаётся FastAPI app и добавить `app.include_router(admin_router)`
7. Создать `web_ui/src/types/admin.types.ts` (Файл 6)
8. Создать `web_ui/src/services/adminConfig.service.ts` (Файл 7)
9. Создать `web_ui/src/hooks/useAdminConfig.ts` (Файл 8)
10. Создать `web_ui/src/components/admin/ConfigGroupPanel.tsx` (Файл 9)
11. Создать `web_ui/src/components/admin/PromptsPanel.tsx` (Файл 10)
12. Создать `web_ui/src/pages/AdminSettingsPage.tsx` (Файл 11)
13. Обновить `App.tsx` — добавить роут (Файл 12)
14. Обновить компонент Sidebar/навигации — добавить ссылку (Файл 13)
15. Проверить что TypeScript компилируется без ошибок: `cd web_ui && npx tsc --noEmit`
16. Запустить бэкенд и выполнить smoke-test (раздел 8)

***

## 8. Критерии готовности (smoke-тест)

```bash
# 1. Конфиг читается
curl -H "X-API-Key: dev-key-001" http://localhost:8000/api/admin/config

# 2. Изменить температуру
curl -X PUT -H "X-API-Key: dev-key-001" \
  -H "Content-Type: application/json" \
  -d '{"key":"LLM_TEMPERATURE","value":0.3}' \
  http://localhost:8000/api/admin/config

# 3. Следующий запрос бота должен использовать 0.3 (проверить в dev trace)

# 4. Сброс
curl -X DELETE -H "X-API-Key: dev-key-001" \
  http://localhost:8000/api/admin/config/LLM_TEMPERATURE

# 5. Промты читаются
curl -H "X-API-Key: dev-key-001" http://localhost:8000/api/admin/prompts

# 6. Без ключа — 401
curl http://localhost:8000/api/admin/config
# Ожидается: {"detail":"Только для режима разработчика"}
```

**Реализация завершена когда:** открыв `/admin/settings` с dev-ключом, все 4 группы параметров видны со значениями; изменение `LLM_TEMPERATURE` и нажатие «Сохранить» приводит к тому, что следующий запрос бота использует новое значение без перезапуска сервера.

***

## 9. Чего НЕ делать

- **Не изменять** `config.py` (кроме последних 2 строк) и `.md` файлы промтов из кода
- **Не кэшировать** `RuntimeConfig._cache` без проверки mtime — данные устареют
- **Не использовать** `__getattr__` вместо `__getattribute__` — для class-level атрибутов `__getattr__` никогда не вызывается
- **Не добавлять** новые npm-пакеты — использовать только React, TypeScript, Tailwind (уже в проекте)
- **Не перезапускать** сервер после изменений — всё работает hot
- **Не включать** `EMBEDDING_MODEL` в `EDITABLE_CONFIG` — требует рестарта (пересчёт эмбеддингов)

