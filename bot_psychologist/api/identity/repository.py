"""Repository layer for identity tables in SQLite."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import LinkedIdentity, SessionRecord, UserRecord


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IdentityRepository:
    """Low-level CRUD operations for identity entities."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
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

    def ensure_schema(self) -> None:
        """Create/extend identity schema in idempotent mode."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    canonical_name TEXT,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    language TEXT NOT NULL DEFAULT 'ru',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS linked_identities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    verified_at TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(provider, external_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_linked_identities_user_id ON linked_identities(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_linked_identities_provider_external ON linked_identities(provider, external_id)"
            )

            if not self._table_exists(conn, "sessions"):
                conn.execute(
                    """
                    CREATE TABLE sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        created_at TEXT NOT NULL,
                        last_active TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active',
                        working_state TEXT,
                        conversation_summary TEXT,
                        metadata TEXT,
                        channel TEXT DEFAULT 'web',
                        device_fingerprint TEXT,
                        last_seen_at TEXT,
                        expires_at TEXT,
                        metadata_json TEXT
                    )
                    """
                )
            else:
                columns = self._table_columns(conn, "sessions")
                if "channel" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN channel TEXT DEFAULT 'web'")
                if "device_fingerprint" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN device_fingerprint TEXT")
                if "last_seen_at" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN last_seen_at TEXT")
                if "expires_at" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")
                if "metadata_json" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN metadata_json TEXT")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_last_seen_at ON sessions(last_seen_at)"
            )

    @staticmethod
    def _dt_or_none(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        return datetime.fromisoformat(raw)

    @staticmethod
    def _load_json(value: Any) -> dict[str, Any]:
        raw = value or "{}"
        if isinstance(raw, (dict, list)):
            return raw if isinstance(raw, dict) else {"value": raw}
        try:
            parsed = json.loads(str(raw))
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {}

    def create_user(self, *, metadata_json: Optional[dict[str, Any]] = None) -> UserRecord:
        user_id = str(uuid.uuid4())
        now = _utc_now_iso()
        metadata = json.dumps(metadata_json or {}, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, now, now, metadata),
            )
        return self.get_user(user_id)  # type: ignore[return-value]

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None
        return UserRecord(
            id=str(row["id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            status=str(row["status"] or "active"),
            canonical_name=row["canonical_name"],
            timezone=str(row["timezone"] or "UTC"),
            language=str(row["language"] or "ru"),
            metadata_json=self._load_json(row["metadata_json"]),
        )

    def find_user_by_identity(self, *, provider: str, external_id: str) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.*
                FROM users u
                JOIN linked_identities li ON li.user_id = u.id
                WHERE li.provider = ? AND li.external_id = ?
                LIMIT 1
                """,
                (provider, external_id),
            ).fetchone()
        if row is None:
            return None
        return UserRecord(
            id=str(row["id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            status=str(row["status"] or "active"),
            canonical_name=row["canonical_name"],
            timezone=str(row["timezone"] or "UTC"),
            language=str(row["language"] or "ru"),
            metadata_json=self._load_json(row["metadata_json"]),
        )

    def add_linked_identity(
        self,
        *,
        user_id: str,
        provider: str,
        external_id: str,
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> LinkedIdentity:
        identity_id = str(uuid.uuid4())
        now = _utc_now_iso()
        payload = json.dumps(metadata_json or {}, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO linked_identities (
                    id, user_id, provider, external_id, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, external_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    metadata_json = COALESCE(linked_identities.metadata_json, excluded.metadata_json)
                """,
                (identity_id, user_id, provider, external_id, now, payload),
            )
            row = conn.execute(
                """
                SELECT * FROM linked_identities
                WHERE provider = ? AND external_id = ?
                LIMIT 1
                """,
                (provider, external_id),
            ).fetchone()
        return LinkedIdentity(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            provider=str(row["provider"]),
            external_id=str(row["external_id"]),
            verified_at=(
                self._dt_or_none(row["verified_at"])
            ),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            metadata_json=self._load_json(row["metadata_json"]),
        )

    def get_linked_identities(self, user_id: str) -> list[LinkedIdentity]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM linked_identities
                WHERE user_id = ?
                ORDER BY created_at ASC
                """,
                (user_id,),
            ).fetchall()
        result: list[LinkedIdentity] = []
        for row in rows:
            result.append(
                LinkedIdentity(
                    id=str(row["id"]),
                    user_id=str(row["user_id"]),
                    provider=str(row["provider"]),
                    external_id=str(row["external_id"]),
                    verified_at=(
                        self._dt_or_none(row["verified_at"])
                    ),
                    created_at=datetime.fromisoformat(str(row["created_at"])),
                    metadata_json=self._load_json(row["metadata_json"]),
                )
            )
        return result

    # Compatibility aliases for PRD contract naming.
    def create_linked_identity(
        self,
        *,
        user_id: str,
        provider: str,
        external_id: str,
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> LinkedIdentity:
        return self.add_linked_identity(
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            metadata_json=metadata_json,
        )

    def find_by_linked_identity(self, *, provider: str, external_id: str) -> Optional[UserRecord]:
        return self.find_user_by_identity(provider=provider, external_id=external_id)

    def get_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        return self.get_user(user_id)

    def upsert_session(
        self,
        *,
        session_id: str,
        user_id: str,
        channel: str = "web",
        device_fingerprint: Optional[str] = None,
        metadata_json: Optional[dict[str, Any]] = None,
        expires_at: Optional[str] = None,
    ) -> SessionRecord:
        now = _utc_now_iso()
        payload = json.dumps(metadata_json or {}, ensure_ascii=False)
        with self._connect() as conn:
            columns = self._table_columns(conn, "sessions")
            last_seen_value = now
            if "last_seen_at" in columns:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, user_id, created_at, last_active, last_seen_at,
                        status, channel, device_fingerprint, expires_at, metadata_json, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        user_id = excluded.user_id,
                        last_active = excluded.last_active,
                        last_seen_at = excluded.last_seen_at,
                        channel = COALESCE(excluded.channel, sessions.channel),
                        device_fingerprint = COALESCE(excluded.device_fingerprint, sessions.device_fingerprint),
                        expires_at = COALESCE(excluded.expires_at, sessions.expires_at),
                        metadata_json = COALESCE(excluded.metadata_json, sessions.metadata_json),
                        metadata = COALESCE(excluded.metadata, sessions.metadata)
                    """,
                    (
                        session_id,
                        user_id,
                        now,
                        now,
                        now,
                        channel,
                        device_fingerprint,
                        expires_at,
                        payload,
                        payload,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, user_id, created_at, last_active,
                        status, channel, device_fingerprint, expires_at, metadata_json, metadata
                    )
                    VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        user_id = excluded.user_id,
                        last_active = excluded.last_active,
                        channel = COALESCE(excluded.channel, sessions.channel),
                        device_fingerprint = COALESCE(excluded.device_fingerprint, sessions.device_fingerprint),
                        expires_at = COALESCE(excluded.expires_at, sessions.expires_at),
                        metadata_json = COALESCE(excluded.metadata_json, sessions.metadata_json),
                        metadata = COALESCE(excluded.metadata, sessions.metadata)
                    """,
                    (
                        session_id,
                        user_id,
                        now,
                        now,
                        channel,
                        device_fingerprint,
                        expires_at,
                        payload,
                        payload,
                    ),
                )
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return SessionRecord(
            session_id=str(row["session_id"]),
            user_id=str(row["user_id"]),
            channel=str(row["channel"] or "web"),
            device_fingerprint=row["device_fingerprint"],
            created_at=(
                datetime.fromisoformat(str(row["created_at"]))
                if row["created_at"]
                else None
            ),
            last_seen_at=(
                self._dt_or_none(row["last_seen_at"])
                if "last_seen_at" in row.keys()
                else self._dt_or_none(row["last_active"])
            ),
            expires_at=self._dt_or_none(row["expires_at"]) if "expires_at" in row.keys() else None,
            metadata_json=self._load_json(
                row["metadata_json"] if "metadata_json" in row.keys() else (row["metadata"] if "metadata" in row.keys() else "{}")
            ),
        )

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return SessionRecord(
            session_id=str(row["session_id"]),
            user_id=str(row["user_id"] or ""),
            channel=str(row["channel"] or "web"),
            device_fingerprint=row["device_fingerprint"],
            created_at=(
                datetime.fromisoformat(str(row["created_at"]))
                if row["created_at"]
                else None
            ),
            last_seen_at=(
                self._dt_or_none(row["last_seen_at"])
                if "last_seen_at" in row.keys()
                else self._dt_or_none(row["last_active"])
            ),
            expires_at=self._dt_or_none(row["expires_at"]) if "expires_at" in row.keys() else None,
            metadata_json=self._load_json(
                row["metadata_json"] if "metadata_json" in row.keys() else (row["metadata"] if "metadata" in row.keys() else "{}")
            ),
        )

    def list_active_sessions(self, user_id: str, limit: int = 20) -> list[SessionRecord]:
        safe_limit = max(1, min(limit, 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sessions
                WHERE user_id = ?
                ORDER BY COALESCE(last_seen_at, last_active) DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
        sessions: list[SessionRecord] = []
        for row in rows:
            sessions.append(
                SessionRecord(
                    session_id=str(row["session_id"]),
                    user_id=str(row["user_id"]),
                    channel=str(row["channel"] or "web"),
                    device_fingerprint=row["device_fingerprint"],
                    created_at=(
                        datetime.fromisoformat(str(row["created_at"]))
                        if row["created_at"]
                        else None
                    ),
                    last_seen_at=(
                        self._dt_or_none(row["last_seen_at"])
                        if "last_seen_at" in row.keys()
                        else self._dt_or_none(row["last_active"])
                    ),
                    expires_at=self._dt_or_none(row["expires_at"]) if "expires_at" in row.keys() else None,
                    metadata_json=self._load_json(
                        row["metadata_json"] if "metadata_json" in row.keys() else (row["metadata"] if "metadata" in row.keys() else "{}")
                    ),
                )
            )
        return sessions

    def update_session_last_seen(self, session_id: str) -> None:
        now = _utc_now_iso()
        with self._connect() as conn:
            columns = self._table_columns(conn, "sessions")
            if "last_seen_at" in columns:
                conn.execute(
                    "UPDATE sessions SET last_seen_at = ?, last_active = ? WHERE session_id = ?",
                    (now, now, session_id),
                )
            else:
                conn.execute(
                    "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                    (now, session_id),
                )
