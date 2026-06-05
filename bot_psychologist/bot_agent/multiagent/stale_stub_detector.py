"""Stale stub / bad phrase detector used by eval + runtime audits."""

from __future__ import annotations

import re
from typing import Any

# Canonical bad phrases from PRD-047.11-AUDIT.
STALE_STUB_PHRASES = (
    "сейчас полезнее прямое объяснение механизма",
    "сейчас полезнее не упражнение, а прямое объяснение",
    "отвечу по сути без навязывания практик",
    "ключевой узел в том, что",
    "ключевой узел в том, что автоматический контроль может включать внутреннюю перегрузку еще до действия",
    "ключевой узел в том, что автоматический контроль может включать внутреннюю перегрузку ещё до действия",
    "ключевой узел в том, как автоматический контроль включает перегруз",
    "сфокусируюсь на разборе, без практик по умолчанию",
)

# Keep compatibility with historical mojibake artifacts so old payloads
# are still detectable in audit scans.
_HISTORICAL_BAD_PHRASES = (
    "РѕС‚РІРµС‡Сѓ РїРѕ СЃСѓС‚Рё Р±РµР· РЅР°РІСЏР·С‹РІР°РЅРёСЏ РїСЂР°РєС‚РёРє",
    "РєР»СЋС‡РµРІРѕР№ СѓР·РµР» РІ С‚РѕРј",
    "СЃС„РѕРєСѓСЃРёСЂСѓСЋСЃСЊ РЅР° СЂР°Р·Р±РѕСЂРµ",
)

_SEMANTIC_PATTERNS = (
    re.compile(
        r"сейчас\s+полезн\w+.{0,40}прям\w+\s+объяснен\w+\s+механизм\w+",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"автоматическ\w+\s+контрол\w+.{0,80}внутренн\w+\s+перегруз\w+.{0,80}до\s+действ",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"сфокусир\w+.{0,40}разбор\w+.{0,40}без\s+практик\s+по\s+умолч",
        re.IGNORECASE | re.DOTALL,
    ),
)

_SEMANTIC_KEYWORD_SETS = (
    ("сейчас полезн", "прям", "объяснен", "механизм"),
    ("автоматическ", "контрол", "внутренн", "перегруз", "действ"),
    ("сфокусир", "разбор", "без практик", "по умолч"),
)


def _normalize(text: str) -> str:
    lowered = str(text or "").lower().replace("ё", "е")
    normalized = re.sub(r"\s+", " ", lowered)
    return normalized.strip()


def detect_stale_stub(text: str) -> dict[str, Any]:
    normalized = _normalize(text)
    if not normalized:
        return {
            "detected": False,
            "matched_phrase": "",
            "detector_kind": "",
        }
    for phrase in STALE_STUB_PHRASES:
        if _normalize(phrase) in normalized:
            return {
                "detected": True,
                "matched_phrase": phrase,
                "detector_kind": "exact",
            }
    for phrase in _HISTORICAL_BAD_PHRASES:
        if phrase in normalized:
            return {
                "detected": True,
                "matched_phrase": phrase,
                "detector_kind": "historical_exact",
            }
    for pattern in _SEMANTIC_PATTERNS:
        matched = pattern.search(normalized)
        if matched:
            return {
                "detected": True,
                "matched_phrase": matched.group(0),
                "detector_kind": "semantic",
            }
    for keywords in _SEMANTIC_KEYWORD_SETS:
        if all(token in normalized for token in keywords):
            return {
                "detected": True,
                "matched_phrase": ", ".join(keywords),
                "detector_kind": "semantic",
            }
    return {
        "detected": False,
        "matched_phrase": "",
        "detector_kind": "",
    }


def contains_stale_stub(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        payload = detect_stale_stub(value)
        payload.setdefault("matched_path", "")
        return payload
    if isinstance(value, dict):
        for key, item in value.items():
            result = contains_stale_stub(item)
            if result.get("detected"):
                return {
                    "detected": True,
                    "matched_phrase": result.get("matched_phrase", ""),
                    "detector_kind": result.get("detector_kind", ""),
                    "matched_path": str(key),
                }
        return {"detected": False, "matched_phrase": "", "detector_kind": "", "matched_path": ""}
    if isinstance(value, list):
        for idx, item in enumerate(value):
            result = contains_stale_stub(item)
            if result.get("detected"):
                return {
                    "detected": True,
                    "matched_phrase": result.get("matched_phrase", ""),
                    "detector_kind": result.get("detector_kind", ""),
                    "matched_path": str(idx),
                }
        return {"detected": False, "matched_phrase": "", "detector_kind": "", "matched_path": ""}
    return {"detected": False, "matched_phrase": "", "detector_kind": "", "matched_path": ""}


__all__ = ["STALE_STUB_PHRASES", "detect_stale_stub", "contains_stale_stub"]
