from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "migrations" / "013_identity_layer.sql"
)


def _apply_migration(db_path: Path) -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def test_migration_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "identity.db"
    _apply_migration(db_path)
    _apply_migration(db_path)


def test_tables_created(tmp_path: Path) -> None:
    db_path = tmp_path / "identity.db"
    _apply_migration(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {row[0] for row in rows}
    finally:
        conn.close()

    assert "users" in names
    assert "linked_identities" in names
    assert "sessions" in names
    assert "link_codes" in names


def test_fk_constraints_active(tmp_path: Path) -> None:
    db_path = tmp_path / "identity.db"
    _apply_migration(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO linked_identities (id, user_id, provider, external_id, created_at, metadata_json)
                VALUES ('id-1', 'missing-user', 'web', 'fingerprint-1', datetime('now'), '{}')
                """
            )
            conn.commit()
    finally:
        conn.close()
