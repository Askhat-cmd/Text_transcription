from __future__ import annotations

from datetime import datetime, timedelta, timezone

from api.registration.repository import RegistrationRepository


def test_repository_stores_hashed_key_not_plain(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    repo.create_user_profile(
        user_id="u1",
        username="user1",
        hashed_access_key="$argon2$dummy",
        role="user",
    )
    row = repo.get_profile_by_username("user1")
    assert row is not None
    assert row["hashed_access_key"] == "$argon2$dummy"


def test_repository_consume_invite_key_marks_used(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    key = "BP-INVITE-TEST"
    repo.create_invite_key(
        key_value=key,
        role_grant="user",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        created_by="admin",
    )

    assert repo.consume_invite_key(key, "u1") is True
    assert repo.consume_invite_key(key, "u2") is False


def test_repository_sessions_create_and_revoke(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    session = repo.create_session(user_id="u1", username="user1", role="user")
    assert repo.get_session(session.session_token) is not None
    repo.revoke_session(session.session_token)
    assert repo.get_session(session.session_token) is None
