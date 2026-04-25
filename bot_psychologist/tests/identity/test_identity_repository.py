from __future__ import annotations

import time
from pathlib import Path

from api.identity.repository import IdentityRepository


def test_create_and_get_user(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    created = repo.create_user(metadata_json={"source": "test"})
    loaded = repo.get_user(created.id)
    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.metadata_json.get("source") == "test"


def test_find_by_linked_identity(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    user = repo.create_user()
    repo.create_linked_identity(
        user_id=user.id,
        provider="web",
        external_id="sha256:fingerprint",
    )
    found = repo.find_by_linked_identity(
        provider="web",
        external_id="sha256:fingerprint",
    )
    assert found is not None
    assert found.id == user.id


def test_find_missing_identity_returns_none(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    found = repo.find_by_linked_identity(provider="web", external_id="missing")
    assert found is None


def test_create_linked_identity_unique_constraint(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    user = repo.create_user()
    first = repo.create_linked_identity(
        user_id=user.id,
        provider="web",
        external_id="sha256:dup",
    )
    second = repo.create_linked_identity(
        user_id=user.id,
        provider="web",
        external_id="sha256:dup",
    )
    assert second.id == first.id
    linked = repo.get_linked_identities(user.id)
    assert len([item for item in linked if item.external_id == "sha256:dup"]) == 1


def test_fingerprint_collision_no_merge(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    user_1 = repo.create_user()
    user_2 = repo.create_user()

    first = repo.create_linked_identity(
        user_id=user_1.id,
        provider="web",
        external_id="sha256:shared",
    )
    second = repo.create_linked_identity(
        user_id=user_2.id,
        provider="web",
        external_id="sha256:shared",
    )

    assert first.user_id == user_1.id
    assert second.user_id == user_1.id
    found = repo.find_by_linked_identity(provider="web", external_id="sha256:shared")
    assert found is not None
    assert found.id == user_1.id


def test_session_update_last_seen(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    user = repo.create_user()
    session = repo.upsert_session(
        session_id="session-1",
        user_id=user.id,
        channel="web",
        device_fingerprint="sha256:abc",
    )
    assert session.last_seen_at is not None
    before = session.last_seen_at
    time.sleep(0.01)
    repo.update_session_last_seen("session-1")
    after = repo.get_session("session-1")
    assert after is not None
    assert after.last_seen_at is not None
    assert after.last_seen_at >= before


def test_session_upsert_idempotent(tmp_path: Path) -> None:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    user = repo.create_user()
    repo.upsert_session(session_id="idem-1", user_id=user.id, channel="web")
    repo.upsert_session(session_id="idem-1", user_id=user.id, channel="web")
    with repo._connect() as conn:  # noqa: SLF001 - test-only verification
        count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE session_id = ?",
            ("idem-1",),
        ).fetchone()["cnt"]
    assert int(count) == 1
