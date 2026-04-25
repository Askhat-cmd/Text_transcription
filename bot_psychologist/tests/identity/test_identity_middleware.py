from __future__ import annotations

from starlette.requests import Request

import pytest

from api.identity.middleware import (
    build_fingerprint_from_request,
    extract_legacy_user_id_from_request,
    generate_session_id,
    mask_external_id,
)


def _make_request(
    *,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    body: bytes = b"{}",
) -> Request:
    hdrs = headers or {}
    header_items = [(k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in hdrs.items()]
    body_ref = {"value": body}

    async def _receive():
        value = body_ref["value"]
        body_ref["value"] = None
        if value is None:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": value, "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": "/api/v1/questions/adaptive",
        "headers": header_items,
        "client": ("127.0.0.1", 8080),
    }
    return Request(scope, _receive)


def test_build_fingerprint_from_request_is_deterministic() -> None:
    req1 = _make_request(headers={"User-Agent": "A", "Accept-Language": "ru"})
    req2 = _make_request(headers={"User-Agent": "A", "Accept-Language": "ru"})
    fp1 = build_fingerprint_from_request(req1)
    fp2 = build_fingerprint_from_request(req2)
    assert fp1.startswith("sha256:")
    assert fp1 == fp2


def test_fingerprint_reads_forwarded_for() -> None:
    req = _make_request(
        headers={
            "X-Forwarded-For": "1.2.3.4, 10.0.0.1",
            "User-Agent": "A",
            "Accept-Language": "ru",
        }
    )
    fp = build_fingerprint_from_request(req)
    req_same = _make_request(
        headers={
            "X-Forwarded-For": "1.2.3.4",
            "User-Agent": "A",
            "Accept-Language": "ru",
        }
    )
    assert fp == build_fingerprint_from_request(req_same)


def test_fingerprint_reads_real_ip_when_no_forwarded_for() -> None:
    req = _make_request(
        headers={"X-Real-IP": "5.6.7.8", "User-Agent": "A", "Accept-Language": "ru"}
    )
    fp = build_fingerprint_from_request(req)
    req_same = _make_request(
        headers={"X-Real-IP": "5.6.7.8", "User-Agent": "A", "Accept-Language": "ru"}
    )
    assert fp == build_fingerprint_from_request(req_same)


def test_fingerprint_is_sha256_hex() -> None:
    req = _make_request(headers={"User-Agent": "A"})
    fp = build_fingerprint_from_request(req)
    assert fp.startswith("sha256:")
    assert len(fp.replace("sha256:", "")) == 64


def test_generate_session_id_has_prefix() -> None:
    session_id = generate_session_id()
    assert session_id.startswith("sess_")
    assert len(session_id) > 10


def test_mask_external_id_for_web_and_telegram() -> None:
    web = mask_external_id("web", "sha256:abcdef0123456789")
    tg = mask_external_id("telegram", "123456789")
    assert web == "sha256:abcdef01..."
    assert tg == "12***89"


@pytest.mark.asyncio
async def test_extract_legacy_user_id_from_request() -> None:
    req = _make_request(
        headers={"Content-Type": "application/json"},
        body=b'{"query":"hi","user_id":"legacy_42"}',
    )
    user_id = await extract_legacy_user_id_from_request(req)
    assert user_id == "legacy_42"
