"""SQLite session persistence for Telegram adapter."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

import httpx

from ..config import API_BASE_URL, API_KEY, SESSION_DB_PATH


_db_initialized_path: Optional[str] = None


def _resolve_db_path() -> str:
    return os.getenv("SESSION_DB_PATH", SESSION_DB_PATH)


def _init_db() -> None:
    global _db_initialized_path
    db_path = _resolve_db_path()
    if _db_initialized_path == db_path:
        return

    parent = Path(db_path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                telegram_user_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()

    _db_initialized_path = db_path


def _get_cached_session(user_id: str) -> str | None:
    _init_db()
    with sqlite3.connect(_resolve_db_path()) as conn:
        row = conn.execute(
            "SELECT session_id FROM sessions WHERE telegram_user_id = ?",
            (user_id,),
        ).fetchone()
    return str(row[0]) if row else None


def _save_session(user_id: str, session_id: str) -> None:
    _init_db()
    with sqlite3.connect(_resolve_db_path()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (telegram_user_id, session_id) VALUES (?, ?)",
            (user_id, session_id),
        )
        conn.commit()


def _delete_session(user_id: str) -> None:
    _init_db()
    with sqlite3.connect(_resolve_db_path()) as conn:
        conn.execute("DELETE FROM sessions WHERE telegram_user_id = ?", (user_id,))
        conn.commit()


async def get_or_create_session(user_id: str) -> str:
    cached = _get_cached_session(user_id)
    if cached:
        return cached

    api_base_url = os.getenv("NEO_API_URL", API_BASE_URL)
    api_key = os.getenv("NEO_API_KEY", API_KEY)
    url = f"{api_base_url}/api/v1/users/{user_id}/sessions"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers={"X-API-Key": api_key})
        response.raise_for_status()
        payload = response.json()

    session_id = str(payload["session_id"])
    _save_session(user_id, session_id)
    return session_id


async def reset_session(user_id: str) -> None:
    _delete_session(user_id)

