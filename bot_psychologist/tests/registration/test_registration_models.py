from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.registration.models import LoginResponse, RegisterRequest


def test_register_request_rejects_invalid_username() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username="User Name!", invite_key="INV")


def test_register_request_accepts_valid_username() -> None:
    model = RegisterRequest(username="user_42", invite_key="INVITE-KEY-1")
    assert model.username == "user_42"


def test_login_response_has_required_fields() -> None:
    payload = {
        "user_id": "u1",
        "session_token": "s1",
        "role": "user",
        "username": "name",
        "expires_at": "2030-01-01T00:00:00+00:00",
    }
    model = LoginResponse.model_validate(payload)
    assert model.user_id == "u1"
