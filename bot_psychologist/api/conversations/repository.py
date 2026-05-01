"""Repository layer for conversation entities."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .models import ConversationRecord


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    """Low-level CRUD for table conversations."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._schema_ready = False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return bool(row)

    def _table_columns(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    @staticmethod
    def _load_json(value: Any) -> dict[str, Any]:
        raw = value or "{}"
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(str(raw))
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {}

    @staticmethod
    def _to_record(row: sqlite3.Row) -> ConversationRecord:
        return ConversationRecord(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            session_id=str(row["session_id"]),
            channel=str(row["channel"] or "web"),  # type: ignore[arg-type]
            status=str(row["status"] or "active"),  # type: ignore[arg-type]
            title=row["title"],
            started_at=datetime.fromisoformat(str(row["started_at"])),
            last_message_at=datetime.fromisoformat(str(row["last_message_at"])),
            ended_at=(
                datetime.fromisoformat(str(row["ended_at"]))
                if row["ended_at"]
                else None
            ),
            metadata_json=ConversationRepository._load_json(row["metadata_json"]),
            message_count=int(row["message_count"] or 0),
        )

    @staticmethod
    def _is_recent(last_message_at: datetime, *, hours: int = 24) -> bool:
        """Check recency window for fallback conversation resume."""
        value = last_message_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
        return value >= cutoff

    async def ensure_schema(self) -> None:
        """Ensure schema required by conversation layer is present."""
        if self._schema_ready:
            return
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                    channel TEXT NOT NULL DEFAULT 'web'
                        CHECK(channel IN ('web', 'telegram', 'api')),
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active', 'paused', 'closed', 'archived')),
                    title TEXT,
                    started_at TEXT NOT NULL,
                    last_message_at TEXT NOT NULL,
                    ended_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    message_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_status_user ON conversations(status, user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC)"
            )

            if self._table_exists(conn, "memory_items"):
                columns = self._table_columns(conn, "memory_items")
                if "conversation_id" not in columns:
                    conn.execute("ALTER TABLE memory_items ADD COLUMN conversation_id TEXT")
                if "status" not in columns:
                    conn.execute(
                        "ALTER TABLE memory_items ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                    )
                if "valid_from" not in columns:
                    conn.execute("ALTER TABLE memory_items ADD COLUMN valid_from TEXT")
                if "valid_to" not in columns:
                    conn.execute("ALTER TABLE memory_items ADD COLUMN valid_to TEXT")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_items_conversation_id ON memory_items(conversation_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_items_status_user ON memory_items(status, user_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_items_validity ON memory_items(valid_from, valid_to)"
                )

        self._schema_ready = True

    async def create_conversation(
        self,
        *,
        user_id: str,
        session_id: str,
        channel: str = "web",
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ConversationRecord:
        await self.ensure_schema()
        conversation_id = str(uuid.uuid4())
        now = _utc_now_iso()
        payload = json.dumps(metadata or {}, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT INTO conversations (
                    id, user_id, session_id, channel, status,
                    title, started_at, last_message_at, metadata_json, message_count
                ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, 0)
                """,
                (
                    conversation_id,
                    user_id,
                    session_id,
                    channel,
                    title,
                    now,
                    now,
                    payload,
                ),
            )
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            conn.commit()
        return self._to_record(row)

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationRecord]:
        await self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ? LIMIT 1",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return self._to_record(row)

    async def get_active_conversation(
        self,
        user_id: str,
        session_id: str,
        channel: str = "web",
    ) -> Optional[ConversationRecord]:
        record, _lookup = await self.get_active_conversation_with_lookup(
            user_id=user_id,
            session_id=session_id,
            channel=channel,
        )
        return record

    async def get_active_conversation_with_lookup(
        self,
        *,
        user_id: str,
        session_id: str,
        channel: str = "web",
    ) -> tuple[Optional[ConversationRecord], Optional[str]]:
        await self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM conversations
                WHERE user_id = ? AND session_id = ? AND channel = ? AND status = 'active'
                ORDER BY last_message_at DESC
                LIMIT 1
                """,
                (user_id, session_id, channel),
            ).fetchone()
            if row is not None:
                return self._to_record(row), "session_id"

            # Fallback для web: если session_id технически сменился,
            # пробуем последнюю активную conversation пользователя в том же канале.
            fallback_row = conn.execute(
                """
                SELECT *
                FROM conversations
                WHERE user_id = ? AND channel = ? AND status = 'active'
                ORDER BY last_message_at DESC
                LIMIT 1
                """,
                (user_id, channel),
            ).fetchone()

        if fallback_row is None:
            return None, None

        fallback_record = self._to_record(fallback_row)
        if not self._is_recent(fallback_record.last_message_at, hours=24):
            return None, None
        return fallback_record, "user_fallback"

    async def pause_active_conversations(
        self,
        *,
        user_id: str,
        session_id: str,
        channel: str = "web",
    ) -> int:
        await self.ensure_schema()
        now = _utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE conversations
                SET status = 'paused', ended_at = COALESCE(ended_at, ?)
                WHERE user_id = ? AND session_id = ? AND channel = ? AND status = 'active'
                """,
                (now, user_id, session_id, channel),
            )
        return int(cursor.rowcount or 0)

    async def update_last_message_at(self, conversation_id: str) -> None:
        await self.ensure_schema()
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET last_message_at = ?, message_count = COALESCE(message_count, 0) + 1
                WHERE id = ?
                """,
                (now, conversation_id),
            )

    async def close_conversation(self, conversation_id: str) -> None:
        await self.ensure_schema()
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET status = 'closed', ended_at = COALESCE(ended_at, ?)
                WHERE id = ?
                """,
                (now, conversation_id),
            )

    async def list_user_conversations(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ConversationRecord]:
        await self.ensure_schema()
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM conversations
                    WHERE user_id = ? AND status = ?
                    ORDER BY last_message_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, status, safe_limit, safe_offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM conversations
                    WHERE user_id = ?
                    ORDER BY last_message_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, safe_limit, safe_offset),
                ).fetchall()
        return [self._to_record(row) for row in rows]

    async def archive_old_conversations(
        self,
        user_id: str,
        days_threshold: int = 30,
    ) -> int:
        await self.ensure_schema()
        now = _utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE conversations
                SET status = 'archived', ended_at = COALESCE(ended_at, ?)
                WHERE user_id = ?
                  AND status IN ('closed', 'paused')
                  AND datetime(last_message_at) <= datetime('now', '-' || ? || ' days')
                """,
                (now, user_id, max(0, days_threshold)),
            )
        return int(cursor.rowcount or 0)
