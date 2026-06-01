"""Strict stale regulate-stub detector for runtime/evaluation payloads."""

from __future__ import annotations

from typing import Any

STALE_STUB_PHRASES = (
    "отвечу по сути без навязывания практик",
    "ключевой узел в том, что автоматический контроль может включать внутреннюю перегрузку",
    "сфокусируюсь на разборе, без практик по умолчанию",
)


def detect_stale_stub(text: str) -> dict[str, Any]:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return {
            "detected": False,
            "matched_phrase": "",
        }
    for phrase in STALE_STUB_PHRASES:
        if phrase in lowered:
            return {
                "detected": True,
                "matched_phrase": phrase,
            }
    return {
        "detected": False,
        "matched_phrase": "",
    }


def contains_stale_stub(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return detect_stale_stub(value)
    if isinstance(value, dict):
        for key, item in value.items():
            result = contains_stale_stub(item)
            if result.get("detected"):
                return {
                    "detected": True,
                    "matched_phrase": result.get("matched_phrase", ""),
                    "matched_path": str(key),
                }
        return {"detected": False, "matched_phrase": "", "matched_path": ""}
    if isinstance(value, list):
        for idx, item in enumerate(value):
            result = contains_stale_stub(item)
            if result.get("detected"):
                return {
                    "detected": True,
                    "matched_phrase": result.get("matched_phrase", ""),
                    "matched_path": str(idx),
                }
        return {"detected": False, "matched_phrase": "", "matched_path": ""}
    return {"detected": False, "matched_phrase": "", "matched_path": ""}


__all__ = ["STALE_STUB_PHRASES", "detect_stale_stub", "contains_stale_stub"]

