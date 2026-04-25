"""Helpers for request identity extraction and masking."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Optional

from fastapi import Request


def build_fingerprint_from_request(request: Request) -> str:
    """Build deterministic fallback fingerprint from request metadata."""
    forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    client_ip = (
        forwarded_for.split(",")[0].strip()
        or real_ip
        or ((request.client.host if request.client else "") or "")
    )
    user_agent = request.headers.get("user-agent", "")
    accept_language = request.headers.get("accept-language", "")
    source = f"{client_ip}|{user_agent}|{accept_language}".strip()
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def resolve_client_ip(request: Request) -> str:
    """Resolve client IP with reverse-proxy priority."""
    forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    return (
        forwarded_for.split(",")[0].strip()
        or real_ip
        or ((request.client.host if request.client else "") or "")
        or "unknown"
    )


def hash_ip(ip: str) -> str:
    """Return short irreversible hash for IP-safe metadata logging/storage."""
    return "ip_sha:" + hashlib.sha256((ip or "").encode("utf-8")).hexdigest()[:16]


def generate_session_id() -> str:
    """Generate deterministic session id prefix with sha seed."""
    return f"sess_{uuid.uuid4().hex}"


def mask_external_id(provider: str, external_id: str) -> str:
    """Mask external identity for admin API surfaces."""
    if provider == "web":
        raw = external_id or ""
        if raw.startswith("sha256:"):
            raw = raw.split("sha256:", 1)[1]
        if len(raw) <= 8:
            return f"sha256:{raw}"
        return f"sha256:{raw[:8]}..."
    if provider == "telegram":
        raw = external_id or ""
        if len(raw) <= 4:
            return "*" * len(raw)
        return f"{raw[:2]}***{raw[-2:]}"
    return external_id


async def extract_legacy_user_id_from_request(request: Request) -> Optional[str]:
    """Try to extract legacy user_id from JSON request body."""
    if request.method not in {"POST", "PUT", "PATCH"}:
        return None
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None
    try:
        payload: Any = await request.json()
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    user_id = payload.get("user_id")
    if not isinstance(user_id, str):
        return None
    user_id = user_id.strip()
    return user_id or None
