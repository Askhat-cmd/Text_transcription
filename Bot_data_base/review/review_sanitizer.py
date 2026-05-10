from __future__ import annotations

import re
from typing import Any


FORBIDDEN_REVIEW_KEYS = {
    "content_full",
    "full_text",
    "raw_text",
    "source_raw",
    "chapter_text",
    "full_chunk_text",
    "text",
    "content",
    "embedding",
    "vector",
    "api_key",
    "secret",
    "password",
    "token",
    ".env",
}

_SECRET_MARKERS = [
    "openai_api_key=",
    "api_key=",
    "password=",
    "token=",
    "secret=",
    ".env",
    "sk-",
]


def sanitize_preview(text: str, limit: int = 240) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def find_forbidden_review_keys(payload: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            key_norm = key_text.strip().lower()
            current_path = f"{path}.{key_text}"
            if key_norm in FORBIDDEN_REVIEW_KEYS:
                hits.append(current_path)
            hits.extend(find_forbidden_review_keys(value, current_path))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            hits.extend(find_forbidden_review_keys(item, f"{path}[{idx}]"))
    return hits


def contains_forbidden_review_key(payload: Any) -> bool:
    return bool(find_forbidden_review_keys(payload))


def contains_secret_like_value(text: str) -> bool:
    normalized = str(text or "").lower()
    return any(marker in normalized for marker in _SECRET_MARKERS)


def _find_secret_like_values(payload: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            hits.extend(_find_secret_like_values(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            hits.extend(_find_secret_like_values(item, f"{path}[{idx}]"))
    elif isinstance(payload, str):
        if contains_secret_like_value(payload):
            hits.append(path)
    return hits


def assert_review_artifact_is_sanitized(payload: Any) -> None:
    forbidden = find_forbidden_review_keys(payload)
    if forbidden:
        raise ValueError(f"forbidden review keys detected: {forbidden}")
    secret_like = _find_secret_like_values(payload)
    if secret_like:
        raise ValueError(f"secret-like values detected at: {secret_like}")

