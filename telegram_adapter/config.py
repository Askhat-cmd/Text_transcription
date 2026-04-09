"""Runtime configuration for Telegram adapter."""

from __future__ import annotations

import os


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL = os.getenv("NEO_API_URL", "http://localhost:8000")
API_KEY = os.getenv("NEO_API_KEY", "dev-key-00...")
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "./telegram_sessions.db")
STREAM_TIMEOUT_S = float(os.getenv("STREAM_TIMEOUT_S", "60.0") or 60.0)

