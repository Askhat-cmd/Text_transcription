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
from dotenv import load_dotenv

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
        "MAX_TOKENS": {
            "type": "int_or_null",
            "min": 256,
            "max": 16000,
            "group": "llm",
            "label": "Лимит токенов (null = без ограничений)",
        },
        "MAX_TOKENS_SOFT_CAP": {
            "type": "int",
            "min": 256,
            "max": 16000,
            "group": "llm",
            "label": "Мягкий лимит токенов (FREE mode)",
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
        "CONFIDENCE_CAP_HIGH": {
            "type": "int",
            "min": 0,
            "max": 20,
            "group": "retrieval",
            "label": "Cap блоков: confidence=high",
        },
        "CONFIDENCE_CAP_MEDIUM": {
            "type": "int",
            "min": 0,
            "max": 20,
            "group": "retrieval",
            "label": "Cap блоков: confidence=medium",
        },
        "CONFIDENCE_CAP_LOW": {
            "type": "int",
            "min": 0,
            "max": 20,
            "group": "retrieval",
            "label": "Cap блоков: confidence=low",
        },
        "CONFIDENCE_CAP_ZERO": {
            "type": "int",
            "min": 0,
            "max": 20,
            "group": "retrieval",
            "label": "Cap блоков: confidence=zero",
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
        "FREE_CONVERSATION_MODE": {
            "type": "bool",
            "group": "routing",
            "label": "Режим свободного собеседника",
        },
        "FAST_DETECTOR_ENABLED": {
            "type": "bool",
            "group": "routing",
            "label": "Fast detector включен",
        },
        "FAST_DETECTOR_CONFIDENCE_THRESHOLD": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "routing",
            "label": "Порог fast detector",
        },
        "STATE_CLASSIFIER_ENABLED": {
            "type": "bool",
            "group": "routing",
            "label": "State classifier включен",
        },
        "STATE_CLASSIFIER_CONFIDENCE_THRESHOLD": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "routing",
            "label": "Порог state classifier",
        },
        "SD_CLASSIFIER_ENABLED": {
            "type": "bool",
            "group": "routing",
            "label": "SD classifier включен",
        },
        "SD_CLASSIFIER_CONFIDENCE_THRESHOLD": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "routing",
            "label": "Порог SD classifier",
        },
        "DECISION_GATE_RULE_THRESHOLD": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "group": "routing",
            "label": "Порог Decision Gate",
        },
        "DECISION_GATE_LLM_ROUTER_ENABLED": {
            "type": "bool",
            "group": "routing",
            "label": "Decision Gate LLM Router",
        },
        "PROMPT_SD_OVERRIDES_BASE": {
            "type": "bool",
            "group": "routing",
            "label": "SD перекрывает base",
        },
        "PROMPT_MODE_OVERRIDES_SD": {
            "type": "bool",
            "group": "routing",
            "label": "Mode перекрывает SD",
        },
        "ENABLE_KNOWLEDGE_GRAPH": {
            "type": "bool",
            "group": "runtime",
            "label": "Knowledge Graph",
            "note": "Рекомендуется выключенным; включает графовый слой при следующем рестарте",
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
        "prompt_mode_informational",
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
        "prompt_mode_informational":        "Mode: Informational (curious)",
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
                    elif t == "int_or_null":
                        return None if raw is None else int(raw)
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
        meta = dict(data.get("meta", {}))
        meta["last_modified"] = datetime.now().isoformat()
        meta["modified_by"] = "dev"
        meta.setdefault("schema_family", "admin_overrides")
        meta.setdefault("schema_version", "10.4")
        data["meta"] = meta

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
            "routing":   "🧭 Маршрутизация",
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
        elif t == "int_or_null":
            if value is None or (isinstance(value, str) and value.strip().lower() in ("", "null", "none")):
                value = None
            else:
                value = int(value)
                if not (meta["min"] <= value <= meta["max"]):
                    raise ValueError(
                        f"'{key}' должен быть в [{meta['min']}, {meta['max']}] или null, получено {value}"
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
            # FIX B2: None может остаться от старых записей до фикса — игнорируем
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
        # FIX B2: удаляем ключ, не записываем null
        data.setdefault("prompts", {}).pop(name, None)
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

    def reload(self) -> None:
        """
        Backward-compatible config reload for tests/tools.

        Перечитывает .env и обновляет основные runtime-поля без рестарта процесса.
        """
        env_path = Config.PROJECT_ROOT / ".env"
        load_dotenv(env_path, override=True)

        self.KNOWLEDGE_SOURCE = os.getenv("KNOWLEDGE_SOURCE", "json")
        self.BOT_DB_URL = os.getenv("BOT_DB_URL", "http://localhost:8003")
        self.BOT_DB_TIMEOUT = float(os.getenv("BOT_DB_TIMEOUT", "10.0"))
        self.CHROMA_API_URL = os.getenv("CHROMA_API_URL", "http://localhost:8004")
        self.CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "bot_knowledge")
        self.ALL_BLOCKS_MERGED_PATH = os.getenv("ALL_BLOCKS_MERGED_PATH", "")
        self.DB_JSON_DIR = os.getenv("DB_JSON_DIR", "")
        self.DB_EXPORT_FILE = os.getenv("DB_EXPORT_FILE", "")

        self.RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
        self.TOP_K_BLOCKS = self.RETRIEVAL_TOP_K
        self.MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.1"))
        max_tokens_raw = os.getenv("MAX_TOKENS", "").strip().lower()
        self.MAX_TOKENS = None if max_tokens_raw in ("", "none", "null") else int(max_tokens_raw)
        self.MAX_TOKENS_SOFT_CAP = int(os.getenv("MAX_TOKENS_SOFT_CAP", "8192"))
        self.FREE_CONVERSATION_MODE = os.getenv("FREE_CONVERSATION_MODE", "false").lower() == "true"

        self.CONFIDENCE_CAP_HIGH = int(os.getenv("CONFIDENCE_CAP_HIGH", "7"))
        self.CONFIDENCE_CAP_MEDIUM = int(os.getenv("CONFIDENCE_CAP_MEDIUM", "5"))
        self.CONFIDENCE_CAP_LOW = int(os.getenv("CONFIDENCE_CAP_LOW", "3"))
        self.CONFIDENCE_CAP_ZERO = int(os.getenv("CONFIDENCE_CAP_ZERO", "0"))

        self.FAST_DETECTOR_ENABLED = os.getenv("FAST_DETECTOR_ENABLED", "true").lower() == "true"
        self.FAST_DETECTOR_CONFIDENCE_THRESHOLD = float(
            os.getenv("FAST_DETECTOR_CONFIDENCE_THRESHOLD", "0.80")
        )
        self.FAST_DETECTOR_SKIP_DOWNSTREAM = os.getenv(
            "FAST_DETECTOR_SKIP_DOWNSTREAM", "true"
        ).lower() == "true"
        self.STATE_CLASSIFIER_ENABLED = os.getenv("STATE_CLASSIFIER_ENABLED", "true").lower() == "true"
        self.STATE_CLASSIFIER_CONFIDENCE_THRESHOLD = float(
            os.getenv("STATE_CLASSIFIER_CONFIDENCE_THRESHOLD", "0.65")
        )
        self.SD_CLASSIFIER_ENABLED = os.getenv("SD_CLASSIFIER_ENABLED", "true").lower() == "true"
        self.SD_CLASSIFIER_CONFIDENCE_THRESHOLD = float(
            os.getenv("SD_CLASSIFIER_CONFIDENCE_THRESHOLD", "0.65")
        )
        self.DECISION_GATE_RULE_THRESHOLD = float(os.getenv("DECISION_GATE_RULE_THRESHOLD", "0.75"))
        self.DECISION_GATE_LLM_ROUTER_ENABLED = os.getenv(
            "DECISION_GATE_LLM_ROUTER_ENABLED", "true"
        ).lower() == "true"
        self.PROMPT_SD_OVERRIDES_BASE = os.getenv("PROMPT_SD_OVERRIDES_BASE", "true").lower() == "true"
        self.PROMPT_MODE_OVERRIDES_SD = os.getenv("PROMPT_MODE_OVERRIDES_SD", "true").lower() == "true"

        self.DATA_SOURCE = os.getenv("DATA_SOURCE", "unknown")
        self.DEGRADED_MODE = os.getenv("DEGRADED_MODE", "false").lower() == "true"

        with self._lock:
            RuntimeConfig._cache_mtime = 0.0

        logger.info("[RuntimeConfig] reload complete")
