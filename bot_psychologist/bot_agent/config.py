# bot_agent/config.py
"""
Configuration for Phase 1 QA Bot
================================

Конфигурация путей к данным, параметров поиска и LLM.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)


class Config:
    """Конфигурация для Phase 1 QA-бота"""
    
    # === Пути к данным ===
    PROJECT_ROOT = Path(__file__).parent.parent  # bot_psychologist/
    BOT_AGENT_ROOT = Path(__file__).parent       # bot_psychologist/bot_agent/
    
    # Путь к данным voice_bot_pipeline
    DATA_ROOT = Path(os.getenv("DATA_ROOT", "../voice_bot_pipeline/data"))
    if not DATA_ROOT.is_absolute():
        DATA_ROOT = PROJECT_ROOT / DATA_ROOT
    
    SAG_FINAL_DIR = DATA_ROOT / "sag_final"  # где лежат обработанные JSON
    
    # === Параметры поиска ===
    TOP_K_BLOCKS = 5          # сколько релевантных блоков брать
    MIN_RELEVANCE_SCORE = 0.1  # минимальный порог релевантности (0-1)
    
    # === LLM параметры ===
    LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE = 0.7     # 0-1, для стабильности ответов
    LLM_MAX_TOKENS = 1500     # максимальная длина ответа
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # === Язык ===
    RESPONSE_LANGUAGE = "russian"
    
    # === Кэширование ===
    ENABLE_CACHING = True
    CACHE_DIR = PROJECT_ROOT / ".cache_bot_agent"

    # === Память диалога ===
    CONVERSATION_HISTORY_DEPTH = int(os.getenv("CONVERSATION_HISTORY_DEPTH", "3"))
    MAX_CONTEXT_SIZE = int(os.getenv("MAX_CONTEXT_SIZE", "2000"))
    MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "1000"))

    # === Semantic Memory (NEW) ===
    ENABLE_SEMANTIC_MEMORY = os.getenv("ENABLE_SEMANTIC_MEMORY", "True").lower() == "true"
    SEMANTIC_SEARCH_TOP_K = int(os.getenv("SEMANTIC_SEARCH_TOP_K", "3"))
    SEMANTIC_MIN_SIMILARITY = float(os.getenv("SEMANTIC_MIN_SIMILARITY", "0.7"))
    SEMANTIC_MAX_CHARS = int(os.getenv("SEMANTIC_MAX_CHARS", "1000"))

    # Модель для эмбеддингов
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL",
        "paraphrase-multilingual-MiniLM-L12-v2"
    )

    # === Conversation Summary (NEW) ===
    ENABLE_CONVERSATION_SUMMARY = os.getenv("ENABLE_CONVERSATION_SUMMARY", "True").lower() == "true"
    SUMMARY_UPDATE_INTERVAL = int(os.getenv("SUMMARY_UPDATE_INTERVAL", "5"))
    SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", "500"))
    
    # === Отладка ===
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # === Логи ===
    LOG_DIR = PROJECT_ROOT / "logs" / "bot_agent"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Проверить что все необходимые настройки установлены.
        
        Returns:
            bool: True если конфигурация валидна
            
        Raises:
            ValueError: если отсутствуют критические настройки
        """
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY не установлен в .env")
        
        if not cls.SAG_FINAL_DIR.exists():
            errors.append(f"Директория данных не найдена: {cls.SAG_FINAL_DIR}")
        
        if errors:
            raise ValueError("❌ Ошибки конфигурации:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True
    
    @classmethod
    def info(cls) -> str:
        """Вернуть информацию о текущей конфигурации"""
        return f"""
╭─────────────────────────────────────────────╮
│ Bot Psychologist - Configuration            │
├─────────────────────────────────────────────┤
│ PROJECT_ROOT: {cls.PROJECT_ROOT}
│ DATA_ROOT:    {cls.DATA_ROOT}
│ SAG_FINAL:    {cls.SAG_FINAL_DIR}
│ LLM_MODEL:    {cls.LLM_MODEL}
│ TOP_K:        {cls.TOP_K_BLOCKS}
│ DEBUG:        {cls.DEBUG}
│ API_KEY:      {'✓ Set' if cls.OPENAI_API_KEY else '✗ Missing'}
╰─────────────────────────────────────────────╯
"""


# Глобальный инстанс конфига
config = Config()
