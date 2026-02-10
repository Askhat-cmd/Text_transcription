"""SQLite-backed persistence for bot sessions."""

from __future__ import annotations

import json
import pickle
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class SessionManager:
    """Persistent store for session metadata, turns and semantic embeddings."""

    def __init__(self, db_path: str = "data/bot_sessions.db"):
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path != ":memory:":
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON")
        self._init_database()

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_dumps(data: Optional[Dict[str, Any]]) -> Optional[str]:
        if data is None:
            return None
        return json.dumps(data, ensure_ascii=False)

    def _connect(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    working_state TEXT,
                    conversation_summary TEXT,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    user_input TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence REAL,
                    chunks_used TEXT,
                    reasoning TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    UNIQUE (session_id, turn_number)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    embedding BLOB NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    UNIQUE (session_id, turn_number)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_turns_session_id ON conversation_turns(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_session_id ON semantic_embeddings(session_id)"
            )
            self._migrate_schema(conn)

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        """Add non-breaking columns for existing DBs."""
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(conversation_turns)").fetchall()
        }
        if "user_state" not in columns:
            conn.execute("ALTER TABLE conversation_turns ADD COLUMN user_state TEXT")
        if "user_feedback" not in columns:
            conn.execute("ALTER TABLE conversation_turns ADD COLUMN user_feedback TEXT")
        if "user_rating" not in columns:
            conn.execute("ALTER TABLE conversation_turns ADD COLUMN user_rating INTEGER")

    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = self._utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, user_id, created_at, last_active, status, metadata
                ) VALUES (?, ?, ?, ?, 'active', ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_active = excluded.last_active,
                    user_id = COALESCE(sessions.user_id, excluded.user_id),
                    metadata = COALESCE(sessions.metadata, excluded.metadata)
                """,
                (session_id, user_id, now, now, self._json_dumps(metadata)),
            )

    def save_turn(
        self,
        session_id: str,
        turn_number: int,
        user_input: str,
        bot_response: str,
        mode: str,
        timestamp: Optional[str] = None,
        confidence: Optional[float] = None,
        chunks_used: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
        user_state: Optional[str] = None,
        user_feedback: Optional[str] = None,
        user_rating: Optional[int] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> None:
        if timestamp is None:
            timestamp = self._utc_now_iso()

        self.create_session(session_id=session_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_turns (
                    session_id, turn_number, user_input, bot_response, mode, timestamp,
                    confidence, chunks_used, reasoning, user_state, user_feedback, user_rating
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, turn_number) DO UPDATE SET
                    user_input = excluded.user_input,
                    bot_response = excluded.bot_response,
                    mode = excluded.mode,
                    timestamp = excluded.timestamp,
                    confidence = excluded.confidence,
                    chunks_used = excluded.chunks_used,
                    reasoning = excluded.reasoning,
                    user_state = excluded.user_state,
                    user_feedback = excluded.user_feedback,
                    user_rating = excluded.user_rating
                """,
                (
                    session_id,
                    turn_number,
                    user_input,
                    bot_response,
                    mode,
                    timestamp,
                    confidence,
                    json.dumps(chunks_used or [], ensure_ascii=False),
                    reasoning,
                    user_state,
                    user_feedback,
                    user_rating,
                ),
            )

            if embedding is not None:
                arr = np.asarray(embedding, dtype=np.float32)
                embedding_blob = pickle.dumps(arr, protocol=pickle.HIGHEST_PROTOCOL)
                conn.execute(
                    """
                    INSERT INTO semantic_embeddings (session_id, turn_number, embedding)
                    VALUES (?, ?, ?)
                    ON CONFLICT(session_id, turn_number) DO UPDATE SET
                        embedding = excluded.embedding
                    """,
                    (session_id, turn_number, embedding_blob),
                )

            conn.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (self._utc_now_iso(), session_id),
            )

    def update_working_state(self, session_id: str, working_state: Dict[str, Any]) -> None:
        self.create_session(session_id=session_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET working_state = ?, last_active = ?
                WHERE session_id = ?
                """,
                (self._json_dumps(working_state), self._utc_now_iso(), session_id),
            )

    def update_summary(self, session_id: str, summary: str) -> None:
        self.create_session(session_id=session_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET conversation_summary = ?, last_active = ?
                WHERE session_id = ?
                """,
                (summary, self._utc_now_iso(), session_id),
            )

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            session = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not session:
                return None

            turns = conn.execute(
                """
                SELECT
                    turn_number, user_input, bot_response, mode, timestamp, confidence,
                    chunks_used, reasoning, user_state, user_feedback, user_rating
                FROM conversation_turns
                WHERE session_id = ?
                ORDER BY turn_number ASC
                """,
                (session_id,),
            ).fetchall()

            embeddings = conn.execute(
                """
                SELECT turn_number, embedding
                FROM semantic_embeddings
                WHERE session_id = ?
                ORDER BY turn_number ASC
                """,
                (session_id,),
            ).fetchall()

        parsed_turns: List[Dict[str, Any]] = []
        for turn in turns:
            chunks_raw = turn["chunks_used"]
            parsed_turns.append(
                {
                    "turn_number": turn["turn_number"],
                    "user_input": turn["user_input"],
                    "bot_response": turn["bot_response"],
                    "mode": turn["mode"],
                    "timestamp": turn["timestamp"],
                    "confidence": turn["confidence"],
                    "chunks_used": json.loads(chunks_raw) if chunks_raw else [],
                    "reasoning": turn["reasoning"],
                    "user_state": turn["user_state"],
                    "user_feedback": turn["user_feedback"],
                    "user_rating": turn["user_rating"],
                }
            )

        parsed_embeddings: List[Dict[str, Any]] = []
        for item in embeddings:
            parsed_embeddings.append(
                {
                    "turn_number": item["turn_number"],
                    "embedding": pickle.loads(item["embedding"]),
                }
            )

        return {
            "session_info": {
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "created_at": session["created_at"],
                "last_active": session["last_active"],
                "status": session["status"],
                "working_state": (
                    json.loads(session["working_state"]) if session["working_state"] else None
                ),
                "conversation_summary": session["conversation_summary"],
                "metadata": json.loads(session["metadata"]) if session["metadata"] else None,
            },
            "conversation_turns": parsed_turns,
            "semantic_embeddings": parsed_embeddings,
        }

    def archive_old_sessions(self, days: int = 90) -> int:
        threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET status = 'archived'
                WHERE status = 'active' AND last_active < ?
                """,
                (threshold,),
            )
            return cursor.rowcount

    def delete_archived_sessions(self, days: int = 365) -> int:
        threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM sessions
                WHERE status = 'archived' AND last_active < ?
                """,
                (threshold,),
            )
            return cursor.rowcount

    def run_retention_cleanup(
        self,
        active_days: int = 90,
        archive_days: int = 365,
    ) -> Dict[str, int]:
        archived = self.archive_old_sessions(days=active_days)
        deleted = self.delete_archived_sessions(days=archive_days)
        return {
            "archived_count": archived,
            "deleted_count": deleted,
        }

    def delete_session_data(self, session_id: str) -> bool:
        with self._connect() as conn:
            deleted = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            ).rowcount
        return deleted > 0

    def list_user_sessions(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return active sessions for a user with lightweight stats."""
        safe_limit = max(1, min(limit, 500))

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.session_id,
                    s.user_id,
                    s.created_at,
                    s.last_active,
                    s.status,
                    s.metadata,
                    COUNT(t.id) AS turns_count
                FROM sessions s
                LEFT JOIN conversation_turns t ON t.session_id = s.session_id
                WHERE (s.user_id = ? OR s.session_id = ?) AND s.status != 'archived'
                GROUP BY s.session_id
                ORDER BY s.last_active DESC
                LIMIT ?
                """,
                (user_id, user_id, safe_limit),
            ).fetchall()

            last_turns_by_session: Dict[str, Dict[str, Any]] = {}
            if rows:
                session_ids = [row["session_id"] for row in rows]
                placeholders = ",".join("?" for _ in session_ids)
                last_turn_rows = conn.execute(
                    f"""
                    SELECT t.session_id, t.user_input, t.bot_response, t.timestamp
                    FROM conversation_turns t
                    INNER JOIN (
                        SELECT session_id, MAX(turn_number) AS turn_number
                        FROM conversation_turns
                        WHERE session_id IN ({placeholders})
                        GROUP BY session_id
                    ) latest
                    ON t.session_id = latest.session_id AND t.turn_number = latest.turn_number
                    """,
                    session_ids,
                ).fetchall()
                for turn in last_turn_rows:
                    last_turns_by_session[turn["session_id"]] = {
                        "last_user_input": turn["user_input"],
                        "last_bot_response": turn["bot_response"],
                        "last_turn_timestamp": turn["timestamp"],
                    }

        result: List[Dict[str, Any]] = []
        for row in rows:
            metadata_raw = row["metadata"]
            metadata = json.loads(metadata_raw) if metadata_raw else {}
            turn_data = last_turns_by_session.get(row["session_id"], {})
            result.append(
                {
                    "session_id": row["session_id"],
                    "user_id": row["user_id"],
                    "created_at": row["created_at"],
                    "last_active": row["last_active"],
                    "status": row["status"],
                    "metadata": metadata,
                    "turns_count": row["turns_count"] or 0,
                    "last_user_input": turn_data.get("last_user_input"),
                    "last_bot_response": turn_data.get("last_bot_response"),
                    "last_turn_timestamp": turn_data.get("last_turn_timestamp"),
                }
            )
        return result

    def create_user_session(
        self,
        user_id: str,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a dedicated chat session for a user."""
        now = self._utc_now_iso()
        session_id = str(uuid.uuid4())
        metadata: Dict[str, Any] = {
            "source": "web_ui",
            "title": title or "New chat",
            "owner_user_id": user_id,
        }
        self.create_session(session_id=session_id, user_id=user_id, metadata=metadata)
        return {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "last_active": now,
            "status": "active",
            "metadata": metadata,
            "turns_count": 0,
            "last_user_input": None,
            "last_bot_response": None,
            "last_turn_timestamp": None,
        }
