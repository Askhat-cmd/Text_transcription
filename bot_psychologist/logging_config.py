"""
Minimal production logging configuration for bot_psychologist.

Creates three rotating log files:
- logs/app/bot.log (INFO+)
- logs/retrieval/retrieval.log (retrieval diagnostics)
- logs/error/error.log (ERROR+)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for local development."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def __init__(self) -> None:
        super().__init__()
        self._use_color = bool(getattr(sys.stdout, "isatty", lambda: False)()) and os.getenv(
            "NO_COLOR"
        ) is None

    def format(self, record: logging.LogRecord) -> str:
        time_str = self.formatTime(record, "%H:%M:%S")
        level = f"{record.levelname:8s}"
        if self._use_color:
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            level = f"{color}{level}{self.COLORS['RESET']}"
        return f"{time_str} | {level} | {record.name:35s} | {record.getMessage()}"


class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that tolerates terminal encoding limitations."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            try:
                msg = self.format(record)
                stream = self.stream
                encoding = getattr(stream, "encoding", None) or "utf-8"
                safe_msg = msg.encode(encoding, errors="backslashreplace").decode(
                    encoding, errors="ignore"
                )
                stream.write(safe_msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)


class RetrievalFilter(logging.Filter):
    """Pass only retrieval-related records to retrieval.log."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        logger_name = record.name.lower()
        return (
            "[retrieval]" in msg
            or "retriever" in logger_name
            or "stage_filter" in logger_name
            or "confidence_scorer" in logger_name
            or "voyage_reranker" in logger_name
            or "hybrid_query_builder" in logger_name
        )


def _ensure_dirs() -> None:
    (LOG_DIR / "app").mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "retrieval").mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "error").mkdir(parents=True, exist_ok=True)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger for console + rotating files."""
    _ensure_dirs()

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)

    app_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "app" / "bot.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    app_handler.suffix = "%Y%m%d"
    root_logger.addHandler(app_handler)

    retrieval_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "retrieval" / "retrieval.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    retrieval_handler.setLevel(logging.INFO)
    retrieval_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    retrieval_handler.addFilter(RetrievalFilter())
    retrieval_handler.suffix = "%Y%m%d"
    root_logger.addHandler(retrieval_handler)

    error_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "error" / "error.log",
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    error_handler.suffix = "%Y%m%d"
    root_logger.addHandler(error_handler)

    # Reduce noisy third-party loggers.
    for noisy in (
        "httpx",
        "httpcore",
        "asyncio",
        "urllib3",
        "openai",
        "voyageai",
        "sentence_transformers",
        "transformers",
        "torch",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.info("=" * 70)
    logging.info("Logging initialized")
    logging.info("Log directory: %s", LOG_DIR)
    logging.info("App log: logs/app/bot.log")
    logging.info("Retrieval log: logs/retrieval/retrieval.log")
    logging.info("Error log: logs/error/error.log")
    logging.info("=" * 70)


def get_logger(name: str) -> logging.Logger:
    """Small wrapper for consistent logger creation."""
    return logging.getLogger(name)
