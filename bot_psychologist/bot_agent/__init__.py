# bot_agent/__init__.py
"""Neo MindBot runtime package (PRD 11.0)."""

import logging
from pathlib import Path
import sys
from .config import config

# Add parent folder to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Create logs directory
LOG_DIR = Path(__file__).parent.parent / "logs" / "bot_agent"
LOG_DIR.mkdir(parents=True, exist_ok=True)

try:
    from logging_config import SafeStreamHandler
except Exception:  # pragma: no cover - fallback for direct imports
    SafeStreamHandler = logging.StreamHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot_agent.log", encoding='utf-8'),
        SafeStreamHandler()
    ]
)

logger = logging.getLogger("bot_agent")

# Version
__version__ = "0.11.0"
__author__ = "Bot Psychologist Team"

# Neo runtime entrypoint
from .answer_adaptive import answer_question_adaptive
from .llm_streaming import stream_answer_tokens

__all__ = [
    "answer_question_adaptive",
    "stream_answer_tokens",
    "__version__"
]

logger.info(
    "Bot Agent v%s initialized | pipeline: semantic->rerank->topK->llm | legacy_graph: %s",
    __version__,
    "enabled" if config.ENABLE_KNOWLEDGE_GRAPH else "disabled",
)
