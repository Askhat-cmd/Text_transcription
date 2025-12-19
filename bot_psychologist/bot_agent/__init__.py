# bot_agent/__init__.py
"""
Bot Psychologist - Phase 1: Semantic QA Bot
===========================================

AI-бот-психолог на базе данных voice_bot_pipeline (SAG v2.0).
"""

import logging
from pathlib import Path
import sys

# Add parent folder to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Create logs directory
LOG_DIR = Path(__file__).parent.parent / "logs" / "bot_agent"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("bot_agent")

# Version
__version__ = "0.1.0"
__author__ = "Bot Psychologist Team"

# Import main functions
from .answer_basic import answer_question_basic, ask

__all__ = ["answer_question_basic", "ask", "__version__"]

logger.info(f"🚀 Bot Agent v{__version__} initialized (Phase 1)")

