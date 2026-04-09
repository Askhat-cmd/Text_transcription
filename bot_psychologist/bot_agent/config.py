# bot_agent/config.py
"""
Configuration for QA Bot
========================

Centralized project settings: paths, retrieval parameters, LLM settings,
memory, and runtime toggles.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from project root
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)
logger = logging.getLogger(__name__)


def _parse_optional_int_env(name: str, default: Optional[int] = None) -> Optional[int]:
    """Parse optional int env var supporting '', 'null', 'none'."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in ("", "none", "null"):
        return None
    return int(value)


class Config:
    """Application config."""

    # === Paths ===
    PROJECT_ROOT = Path(__file__).parent.parent
    BOT_AGENT_ROOT = Path(__file__).parent

    DATA_ROOT = Path(os.getenv("DATA_ROOT", "../voice_bot_pipeline/data"))
    if not DATA_ROOT.is_absolute():
        DATA_ROOT = PROJECT_ROOT / DATA_ROOT

    SAG_FINAL_DIR = DATA_ROOT / "sag_final"

    # === Knowledge Source ===
    # "json"     → SAG v2.0 JSON (voice_bot_pipeline/sag_final) — legacy режим
    # "db_json"  → Bot_data_base exported *_blocks.json (без запущенного сервера)
    # "chromadb" → Bot_data_base через HTTP API (рекомендуется для production)
    # "api"      → Bot_data_base через HTTP API (явный режим)
    KNOWLEDGE_SOURCE: str = os.getenv("KNOWLEDGE_SOURCE", "json")

    # === Bot_data_base HTTP connection ===
    CHROMA_API_URL: str = os.getenv("CHROMA_API_URL", "http://localhost:8004")
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "bot_knowledge")
    BOT_DB_URL: str = os.getenv("BOT_DB_URL", "http://localhost:8003")
    BOT_DB_TIMEOUT: float = float(os.getenv("BOT_DB_TIMEOUT", "10.0"))

    # === Direct merged JSON path (CRITICAL for CHUNKS fix) ===
    # Абсолютный путь к all_blocks_merged.json (Bot_data_base/data/processed/books/)
    # Если задан — блоки читаются напрямую с диска (быстрее, без HTTP)
    # Если пустой — используется API fallback
    ALL_BLOCKS_MERGED_PATH: str = os.getenv("ALL_BLOCKS_MERGED_PATH", "")
    DEGRADED_MODE: bool = os.getenv("DEGRADED_MODE", "False").lower() == "true"
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "unknown")

    # === db_json mode paths ===
    DB_JSON_DIR: str = os.getenv("DB_JSON_DIR", "")
    DB_EXPORT_FILE: str = os.getenv("DB_EXPORT_FILE", "")

    # === Retrieval ===
    RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    TOP_K_BLOCKS = RETRIEVAL_TOP_K
    MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.1"))
    AUTHOR_BLEND_MODE: str = os.getenv("AUTHOR_BLEND_MODE", "all")
    CONFIDENCE_CAP_HIGH = int(os.getenv("CONFIDENCE_CAP_HIGH", "7"))
    CONFIDENCE_CAP_MEDIUM = int(os.getenv("CONFIDENCE_CAP_MEDIUM", "5"))
    CONFIDENCE_CAP_LOW = int(os.getenv("CONFIDENCE_CAP_LOW", "3"))
    CONFIDENCE_CAP_ZERO = int(os.getenv("CONFIDENCE_CAP_ZERO", "0"))

    # === LLM ===
    LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
    CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE = 0.7
    LLM_MAX_TOKENS = 2000
    MAX_TOKENS: Optional[int] = _parse_optional_int_env("MAX_TOKENS", None)
    MAX_TOKENS_SOFT_CAP: int = int(os.getenv("MAX_TOKENS_SOFT_CAP", "8192"))
    FREE_CONVERSATION_MODE: bool = os.getenv("FREE_CONVERSATION_MODE", "False").lower() == "true"
    # Token limits per response mode (aligned with ResponseFormatter char_limits)
    # Formula: char_limit × 1.7 (ru tokens/char) × 1.2 (safety margin)
    MODE_MAX_TOKENS: dict = {
        "PRESENCE": 3500,
        "CLARIFICATION": 3500,
        "VALIDATION": 4200,
        "THINKING": 7000,
        "INTERVENTION": 5500,
        "INTEGRATION": 4200,
    }
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    SUPPORTED_MODELS: tuple = (
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4o-mini",
    )

    _MAX_COMPLETION_TOKENS_PREFIXES: tuple = (
        "gpt-5",
        "o1",
        "o3",
        "o4",
    )
    REASONING_EFFORT = os.getenv("REASONING_EFFORT", "low")

    # === Language ===
    RESPONSE_LANGUAGE = "russian"

    # === Caching ===
    ENABLE_CACHING = True
    CACHE_DIR = PROJECT_ROOT / ".cache_bot_agent"

    # === Speed layer ===
    WARMUP_ON_START = os.getenv("WARMUP_ON_START", "True").lower() == "true"
    ENABLE_STREAMING = os.getenv("ENABLE_STREAMING", "True").lower() == "true"
    ENABLE_KNOWLEDGE_GRAPH = os.getenv("ENABLE_KNOWLEDGE_GRAPH", "False").lower() == "true"

    # === Routing pipeline controls ===
    FAST_DETECTOR_ENABLED: bool = os.getenv("FAST_DETECTOR_ENABLED", "True").lower() == "true"
    FAST_DETECTOR_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("FAST_DETECTOR_CONFIDENCE_THRESHOLD", "0.80")
    )
    FAST_DETECTOR_SKIP_DOWNSTREAM: bool = os.getenv(
        "FAST_DETECTOR_SKIP_DOWNSTREAM", "True"
    ).lower() == "true"
    STATE_CLASSIFIER_ENABLED: bool = os.getenv("STATE_CLASSIFIER_ENABLED", "True").lower() == "true"
    STATE_CLASSIFIER_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("STATE_CLASSIFIER_CONFIDENCE_THRESHOLD", "0.65")
    )
    SD_CLASSIFIER_ENABLED: bool = os.getenv("SD_CLASSIFIER_ENABLED", "True").lower() == "true"
    SD_CLASSIFIER_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("SD_CLASSIFIER_CONFIDENCE_THRESHOLD", "0.65")
    )
    DECISION_GATE_RULE_THRESHOLD: float = float(os.getenv("DECISION_GATE_RULE_THRESHOLD", "0.75"))
    DECISION_GATE_LLM_ROUTER_ENABLED: bool = os.getenv(
        "DECISION_GATE_LLM_ROUTER_ENABLED", "True"
    ).lower() == "true"
    PROMPT_SD_OVERRIDES_BASE: bool = os.getenv("PROMPT_SD_OVERRIDES_BASE", "True").lower() == "true"
    PROMPT_MODE_OVERRIDES_SD: bool = os.getenv("PROMPT_MODE_OVERRIDES_SD", "True").lower() == "true"

    # === Conversation memory ===
    CONVERSATION_HISTORY_DEPTH = int(os.getenv("CONVERSATION_HISTORY_DEPTH", "3"))
    MAX_CONTEXT_SIZE = int(os.getenv("MAX_CONTEXT_SIZE", "2000"))
    MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "1000"))

    # === Semantic memory ===
    ENABLE_SEMANTIC_MEMORY = os.getenv("ENABLE_SEMANTIC_MEMORY", "True").lower() == "true"
    SEMANTIC_SEARCH_TOP_K = int(os.getenv("SEMANTIC_SEARCH_TOP_K", "3"))
    SEMANTIC_MIN_SIMILARITY = float(os.getenv("SEMANTIC_MIN_SIMILARITY", "0.6"))
    SEMANTIC_MAX_CHARS = int(os.getenv("SEMANTIC_MAX_CHARS", "1000"))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
    EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "auto")

    # === Voyage rerank ===
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
    VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "rerank-2")
    VOYAGE_TOP_K = int(os.getenv("VOYAGE_TOP_K", "5"))
    VOYAGE_ENABLED = os.getenv("VOYAGE_ENABLED", "False").lower() == "true"
    RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "False").lower() == "true"
    RERANKER_CONFIDENCE_THRESHOLD = float(os.getenv("RERANKER_CONFIDENCE_THRESHOLD", "0.35"))
    RERANKER_MODE_WHITELIST = os.getenv("RERANKER_MODE_WHITELIST", "THINKING,INTERVENTION")
    RERANKER_BLOCK_THRESHOLD = int(os.getenv("RERANKER_BLOCK_THRESHOLD", "8"))

    # === Conversation summary ===
    ENABLE_CONVERSATION_SUMMARY = os.getenv("ENABLE_CONVERSATION_SUMMARY", "True").lower() == "true"
    SUMMARY_UPDATE_INTERVAL = int(os.getenv("SUMMARY_UPDATE_INTERVAL", "3"))
    SUMMARY_WINDOW_SIZE = int(os.getenv("SUMMARY_WINDOW_SIZE", "5"))
    RECENT_WINDOW = int(os.getenv("RECENT_WINDOW", "4"))
    SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "300"))
    SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini")
    SUMMARIZER_REASONING_EFFORT = os.getenv("SUMMARIZER_REASONING_EFFORT", "low")
    SUMMARIZER_MIN_TURNS = int(os.getenv("SUMMARIZER_MIN_TURNS", "3"))
    SUMMARIZER_FALLBACK_ON_EMPTY = os.getenv("SUMMARIZER_FALLBACK_ON_EMPTY", "True").lower() == "true"
    SUMMARIZER_FALLBACK_RETRIES = int(os.getenv("SUMMARIZER_FALLBACK_RETRIES", "2"))

    # === Session storage ===
    ENABLE_SESSION_STORAGE = os.getenv("ENABLE_SESSION_STORAGE", "True").lower() == "true"
    BOT_DB_PATH = Path(os.getenv("BOT_DB_PATH", "data/bot_sessions.db"))
    if not BOT_DB_PATH.is_absolute():
        BOT_DB_PATH = PROJECT_ROOT / BOT_DB_PATH
    SESSION_RETENTION_DAYS = int(os.getenv("SESSION_RETENTION_DAYS", "90"))
    ARCHIVE_RETENTION_DAYS = int(os.getenv("ARCHIVE_RETENTION_DAYS", "365"))
    AUTO_CLEANUP_ENABLED = os.getenv("AUTO_CLEANUP_ENABLED", "True").lower() == "true"

    # === Debug/logging ===
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_DIR = PROJECT_ROOT / "logs" / "bot_agent"
    LLM_PAYLOAD_INCLUDE_FULL_CONTENT = os.getenv(
        "LLM_PAYLOAD_INCLUDE_FULL_CONTENT",
        "True",
    ).lower() == "true"

    @classmethod
    def get_token_param_name(cls, model: Optional[str] = None) -> str:
        """Return token limit parameter name for selected model."""
        target = (model or cls.LLM_MODEL).lower()
        for prefix in cls._MAX_COMPLETION_TOKENS_PREFIXES:
            if target.startswith(prefix):
                return "max_completion_tokens"
        return "max_tokens"

    @classmethod
    def supports_custom_temperature(cls, model: Optional[str] = None) -> bool:
        """Whether selected model supports non-default temperature values."""
        target = (model or cls.LLM_MODEL).lower()
        for prefix in cls._MAX_COMPLETION_TOKENS_PREFIXES:
            if target.startswith(prefix):
                return False
        return True

    @classmethod
    def get_effective_max_tokens(cls, model: Optional[str] = None) -> int:
        """Return effective token limit, accounting for reasoning models."""
        target = (model or cls.LLM_MODEL).lower()
        for prefix in cls._MAX_COMPLETION_TOKENS_PREFIXES:
            if target.startswith(prefix):
                return 16000
        return cls.LLM_MAX_TOKENS

    @classmethod
    def get_mode_max_tokens(cls, mode: Optional[str] = None) -> int:
        """Return token limit for given response mode.

        Falls back to LLM_MAX_TOKENS if mode is unknown.
        For reasoning models, always returns get_effective_max_tokens().
        """
        if not cls.supports_custom_temperature():
            return cls.get_effective_max_tokens()
        normalized = (mode or "").upper()
        return cls.MODE_MAX_TOKENS.get(normalized, cls.LLM_MAX_TOKENS)

    @classmethod
    def get_reasoning_effort(cls, model: Optional[str] = None) -> Optional[str]:
        """Return reasoning_effort for reasoning models, else None."""
        if not cls.supports_custom_temperature(model):
            return cls.REASONING_EFFORT
        return None

    @classmethod
    def validate(cls) -> bool:
        """Validate critical runtime config."""
        errors = []

        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set in .env")

        if cls.KNOWLEDGE_SOURCE == "json" and not cls.SAG_FINAL_DIR.exists():
            errors.append(f"SAG data directory not found: {cls.SAG_FINAL_DIR}")
        elif cls.KNOWLEDGE_SOURCE == "db_json":
            db_dir = Path(cls.DB_JSON_DIR) if cls.DB_JSON_DIR else None
            db_file = Path(cls.DB_EXPORT_FILE) if cls.DB_EXPORT_FILE else None
            if not (db_dir and db_dir.exists()) and not (db_file and db_file.exists()):
                errors.append(
                    f"db_json mode: ни DB_JSON_DIR, ни DB_EXPORT_FILE не заданы или не существуют"
                )
        elif cls.KNOWLEDGE_SOURCE in ("chromadb", "api"):
            pass  # health check выполняется в ChromaLoader при первом запросе

        if cls.LLM_MODEL not in cls.SUPPORTED_MODELS:
            errors.append(
                f"Unknown model '{cls.LLM_MODEL}' set in PRIMARY_MODEL. "
                f"Allowed values: {', '.join(cls.SUPPORTED_MODELS)}"
            )
        if cls.CLASSIFIER_MODEL not in cls.SUPPORTED_MODELS:
            errors.append(
                f"Unknown model '{cls.CLASSIFIER_MODEL}' set in CLASSIFIER_MODEL. "
                f"Allowed values: {', '.join(cls.SUPPORTED_MODELS)}"
            )
        if cls.MAX_TOKENS_SOFT_CAP < 256:
            errors.append("MAX_TOKENS_SOFT_CAP must be >= 256")

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {error}" for error in errors))

        return True

    @classmethod
    def info(cls) -> str:
        """Return printable config diagnostics."""
        token_param = cls.get_token_param_name()
        return f"""
+---------------------------------------------+
| Bot Psychologist - Configuration            |
+---------------------------------------------+
| PROJECT_ROOT: {cls.PROJECT_ROOT}
| DATA_ROOT:    {cls.DATA_ROOT}
| SAG_FINAL:    {cls.SAG_FINAL_DIR}
| KNOWLEDGE_SOURCE: {cls.KNOWLEDGE_SOURCE}
| CHROMA_API_URL:   {cls.CHROMA_API_URL}
| CHROMA_COLLECTION:{cls.CHROMA_COLLECTION}
| BOT_DB_URL:  {cls.BOT_DB_URL}
| LLM_MODEL:    {cls.LLM_MODEL}
| CLASSIFIER:   {cls.CLASSIFIER_MODEL}
| TOKEN_PARAM:  {token_param}
| FREE_MODE:    {cls.FREE_CONVERSATION_MODE}
| MAX_TOKENS:   {cls.MAX_TOKENS}
| SOFT_CAP:     {cls.MAX_TOKENS_SOFT_CAP}
| TOP_K:        {cls.TOP_K_BLOCKS}
| GRAPH:        {'enabled' if cls.ENABLE_KNOWLEDGE_GRAPH else 'disabled'}
| DEBUG:        {cls.DEBUG}
| API_KEY:      {'Set' if cls.OPENAI_API_KEY else 'Missing'}
+---------------------------------------------+
"""


# RuntimeConfig наследует Config и добавляет горячий override-слой.
# Circular import безопасен: класс Config уже полностью определён выше,
# runtime_config.py успешно импортирует его из частично загруженного
# модуля — стандартное поведение Python для взаимных импортов.
from .runtime_config import RuntimeConfig
config = RuntimeConfig()

# Авто-определение ALL_BLOCKS_MERGED_PATH если не задан явно
if not config.ALL_BLOCKS_MERGED_PATH:
    _repo_root = Path(__file__).resolve().parents[3]  # Text_transcription/
    _candidate = _repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json"
    if _candidate.exists():
        config.ALL_BLOCKS_MERGED_PATH = str(_candidate)
        logger.info(f"[CONFIG] Auto-detected ALL_BLOCKS_MERGED_PATH: {_candidate}")
