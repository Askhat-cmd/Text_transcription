from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.identity.models import IdentityContext


def test_identity_context_serialization() -> None:
    ctx = IdentityContext(
        user_id="u-1",
        session_id="s-1",
        conversation_id="c-1",
        channel="web",
        is_anonymous=True,
        created_new_user=True,
        provider="web",
        external_id="sha256:abc",
    )
    raw = ctx.model_dump_json()
    restored = IdentityContext.model_validate_json(raw)
    assert restored.user_id == "u-1"
    assert restored.session_id == "s-1"
    assert restored.provider == "web"


def test_identity_context_required_fields() -> None:
    with pytest.raises(ValidationError):
        IdentityContext(session_id="s-1", conversation_id="c-1")

    with pytest.raises(ValidationError):
        IdentityContext(user_id="u-1", conversation_id="c-1")


def test_channel_enum_validation() -> None:
    with pytest.raises(ValidationError):
        IdentityContext(
            user_id="u-1",
            session_id="s-1",
            conversation_id="c-1",
            channel="desktop",  # type: ignore[arg-type]
            provider="web",
        )
