from __future__ import annotations

import sqlite3
from pathlib import Path

from api.conversations import ConversationRepository


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "migrations"
    / "014_conversation_layer.sql"
)


def _apply_migration(db_path: Path) -> None:
    sql = MIGRATION_FILE.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def _columns(db_path: Path, table_name: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}
    finally:
        conn.close()


def test_migration_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_014.db"
    _apply_migration(db_path)
    _apply_migration(db_path)


def test_conversations_table_created(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_014.db"
    _apply_migration(db_path)
    cols = _columns(db_path, "conversations")
    required = {"id", "user_id", "session_id", "status", "started_at", "last_message_at"}
    assert required.issubset(cols)


def test_memory_items_extended(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_014.db"
    _apply_migration(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, user_id TEXT);
            CREATE TABLE IF NOT EXISTS memory_items (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                content TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    import asyncio

    asyncio.run(ConversationRepository(str(db_path)).ensure_schema())
    cols = _columns(db_path, "memory_items")
    assert {"conversation_id", "status", "valid_from", "valid_to"}.issubset(cols)


def test_migration_on_existing_db_with_data(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_014_existing.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE users (id TEXT PRIMARY KEY);
            CREATE TABLE sessions (session_id TEXT PRIMARY KEY, user_id TEXT);
            CREATE TABLE memory_items (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                content TEXT
            );
            INSERT INTO memory_items (id, user_id, content) VALUES ('m1', 'u1', 'hello');
            """
        )
        conn.commit()
    finally:
        conn.close()

    _apply_migration(db_path)
    import asyncio

    asyncio.run(ConversationRepository(str(db_path)).ensure_schema())

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT id, user_id, content FROM memory_items WHERE id = 'm1'").fetchone()
        assert row is not None
        assert row[2] == "hello"
    finally:
        conn.close()
