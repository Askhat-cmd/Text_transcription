"""Repository layer for registration, sessions and access keys."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .models import SessionContext


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat()


class RegistrationRepository:
    """Low-level DB operations for registration package."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return datetime.fromisoformat(text)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    hashed_access_key TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS invite_keys (
                    key_value TEXT PRIMARY KEY,
                    role_grant TEXT NOT NULL DEFAULT 'user',
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_by TEXT,
                    used_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_link_codes (
                    code TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    used_telegram_user_id TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    revoked_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_value TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'test',
                    rate_limit INTEGER NOT NULL DEFAULT 100,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_invite_keys_active_expires ON invite_keys(is_active, expires_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_link_codes_user_id ON telegram_link_codes(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(active)"
            )

    def count_user_profiles(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(1) AS cnt FROM user_profiles").fetchone()
        return int(row["cnt"] if row else 0)

    def get_profile_by_username(self, username: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE username = ? LIMIT 1",
                (username,),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_profile_by_user_id(self, user_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def create_user_profile(
        self,
        *,
        user_id: str,
        username: str,
        hashed_access_key: str,
        role: str = "user",
    ) -> dict[str, Any]:
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, username, hashed_access_key, role,
                    is_active, is_blocked, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, 0, ?, ?)
                """,
                (user_id, username, hashed_access_key, role, now, now),
            )
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row)

    def set_user_role(self, user_id: str, role: str) -> None:
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_profiles SET role = ?, updated_at = ? WHERE user_id = ?",
                (role, now, user_id),
            )

    def create_invite_key(
        self,
        *,
        key_value: str,
        role_grant: str,
        expires_at: datetime,
        created_by: Optional[str] = None,
    ) -> None:
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO invite_keys (
                    key_value, role_grant, created_by, created_at, expires_at, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (key_value, role_grant, created_by, now, expires_at.isoformat()),
            )

    def get_invite_key(self, key_value: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM invite_keys WHERE key_value = ? LIMIT 1",
                (key_value,),
            ).fetchone()
        return dict(row) if row is not None else None

    def consume_invite_key(self, key_value: str, user_id: str) -> bool:
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM invite_keys WHERE key_value = ? LIMIT 1",
                (key_value,),
            ).fetchone()
            if row is None:
                return False
            if int(row["is_active"] or 0) != 1:
                return False
            if row["used_at"]:
                return False
            expires = self._parse_dt(row["expires_at"])
            if expires is None or expires < now:
                return False

            conn.execute(
                """
                UPDATE invite_keys
                SET used_by = ?, used_at = ?, is_active = 0
                WHERE key_value = ? AND used_at IS NULL
                """,
                (user_id, now.isoformat(), key_value),
            )
            updated = conn.execute(
                "SELECT used_by, used_at FROM invite_keys WHERE key_value = ?",
                (key_value,),
            ).fetchone()
            return bool(updated and updated["used_by"] == user_id and updated["used_at"])

    def invalidate_link_codes_for_user(self, user_id: str) -> None:
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE telegram_link_codes
                SET used_at = COALESCE(used_at, ?)
                WHERE user_id = ? AND used_at IS NULL
                """,
                (now, user_id),
            )

    def create_link_code(self, *, user_id: str, ttl_seconds: int = 900, code: str) -> datetime:
        now = _utc_now()
        expires = now + timedelta(seconds=max(60, ttl_seconds))
        self.invalidate_link_codes_for_user(user_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO telegram_link_codes (
                    code, user_id, created_at, expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (code, user_id, now.isoformat(), expires.isoformat()),
            )
        return expires

    def get_link_code_status(self, code: str) -> tuple[str, Optional[dict[str, Any]]]:
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM telegram_link_codes WHERE code = ? LIMIT 1",
                (code,),
            ).fetchone()
        if row is None:
            return "not_found", None
        data = dict(row)
        if data.get("used_at"):
            return "used", data
        expires = self._parse_dt(data.get("expires_at"))
        if expires is None or expires < now:
            return "expired", data
        return "valid", data

    def mark_link_code_used(self, code: str, telegram_user_id: str) -> None:
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE telegram_link_codes
                SET used_at = ?, used_telegram_user_id = ?
                WHERE code = ? AND used_at IS NULL
                """,
                (now, telegram_user_id, code),
            )

    def create_session(
        self,
        *,
        user_id: str,
        username: str,
        role: str,
        ttl_days: int = 30,
    ) -> SessionContext:
        now = _utc_now()
        expires = now + timedelta(days=max(1, ttl_days))
        session_token = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_sessions (
                    session_token, user_id, username, role,
                    created_at, expires_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_token,
                    user_id,
                    username,
                    role,
                    now.isoformat(),
                    expires.isoformat(),
                    now.isoformat(),
                ),
            )
        return SessionContext(
            session_token=session_token,
            user_id=user_id,
            username=username,
            role=role,
            expires_at=expires,
        )

    def get_session(self, session_token: str) -> Optional[SessionContext]:
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_sessions WHERE session_token = ? LIMIT 1",
                (session_token,),
            ).fetchone()
            if row is None:
                return None
            revoked_at = self._parse_dt(row["revoked_at"])
            expires_at = self._parse_dt(row["expires_at"])
            if revoked_at is not None:
                return None
            if expires_at is None or expires_at < now:
                return None
            conn.execute(
                "UPDATE user_sessions SET last_seen_at = ? WHERE session_token = ?",
                (now.isoformat(), session_token),
            )
        return SessionContext(
            session_token=str(row["session_token"]),
            user_id=str(row["user_id"]),
            username=str(row["username"]),
            role=str(row["role"]),
            expires_at=expires_at,
            revoked_at=revoked_at,
        )

    def revoke_session(self, session_token: str) -> None:
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_sessions
                SET revoked_at = COALESCE(revoked_at, ?)
                WHERE session_token = ?
                """,
                (now, session_token),
            )

    def upsert_api_key(
        self,
        *,
        key_value: str,
        name: str,
        role: str,
        rate_limit: int,
        active: bool = True,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO api_keys (key_value, name, role, rate_limit, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key_value) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    rate_limit = excluded.rate_limit,
                    active = excluded.active
                """,
                (
                    key_value,
                    name,
                    role,
                    max(1, rate_limit),
                    1 if active else 0,
                    _utc_iso(),
                ),
            )

    def get_api_key(self, key_value: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_value = ? LIMIT 1",
                (key_value,),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_api_keys(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM api_keys ORDER BY created_at ASC"
            ).fetchall()
        return [dict(row) for row in rows]
