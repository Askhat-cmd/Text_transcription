# bot_agent/__init__.py
"""
Bot Psychologist - Phase 1 + Phase 2 + Phase 3: Knowledge Graph QA Bot
======================================================================

AI-бот-психолог на базе данных voice_bot_pipeline (SAG v2.0).

Phase 1: Базовый QA с TF-IDF retriever
Phase 2: Адаптация по уровню пользователя, семантический анализ
Phase 3: Knowledge Graph — практики, цепочки, иерархия концептов
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
__version__ = "0.3.0"
__author__ = "Bot Psychologist Team"

# Phase 1: Basic QA
from .answer_basic import answer_question_basic, ask

# Phase 2: SAG v2.0 Aware QA
from .answer_sag_aware import answer_question_sag_aware, ask_sag

# Phase 3: Knowledge Graph Powered QA
from .answer_graph_powered import answer_question_graph_powered, ask_graph

__all__ = [
    # Phase 1
    "answer_question_basic",
    "ask",
    # Phase 2
    "answer_question_sag_aware",
    "ask_sag",
    # Phase 3
    "answer_question_graph_powered",
    "ask_graph",
    # Meta
    "__version__"
]

logger.info(f"🚀 Bot Agent v{__version__} initialized (Phase 1 + Phase 2 + Phase 3)")

