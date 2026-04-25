from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from api.dependencies import get_identity_context


def _make_request() -> Request:
    async def _receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/api/v1/questions/adaptive",
        "headers": [
            (b"content-type", b"application/json"),
            (b"user-agent", b"pytest"),
        ],
        "client": ("127.0.0.1", 8080),
    }
    return Request(scope, _receive)


@pytest.mark.asyncio
async def test_fallback_uses_uuid_format() -> None:
    request = _make_request()
    identity_service = SimpleNamespace(
        resolve_by_session=AsyncMock(return_value=None),
        resolve_or_create=AsyncMock(side_effect=RuntimeError("db down")),
    )
    conversation_service = SimpleNamespace(
        get_conversation_context=AsyncMock(return_value=None),
        get_or_create_conversation=AsyncMock(),
    )

    ctx = await get_identity_context(
        request=request,
        x_session_id=None,
        x_device_fingerprint=None,
        x_conversation_id=None,
        identity_service=identity_service,  # type: ignore[arg-type]
        conversation_service=conversation_service,  # type: ignore[arg-type]
    )

    assert ctx.user_id.startswith("anon_")
    assert len(ctx.user_id) == 37
    assert ctx.session_id.startswith("fallback_")
    assert ctx.conversation_id.startswith("fallback_")
    assert ctx.is_anonymous is True
