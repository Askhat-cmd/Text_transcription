from __future__ import annotations

from typing import Any


POLICY_VERSION = "retrieval_governance_safety_v1"

_SAFETY_MARKERS = [
    "мне очень плохо",
    "страшно оставаться одному",
    "я на грани",
    "не хочу жить",
    "хочу исчезнуть",
    "не выдерживаю",
    "опасно",
    "кризис",
    "паника",
    "самоповреждение",
    "причинить вред себе",
    "причинить вред другому",
    "суицид",
]


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("ё", "е").split())


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def is_safety_context_query(query: str, metadata: dict[str, Any] | None = None) -> bool:
    payload = metadata or {}
    intent = str(payload.get("intent") or "").strip().lower()
    if intent == "safety":
        return True
    if _parse_bool(payload.get("include_internal")):
        return True

    normalized_query = _normalize_text(query)
    for marker in _SAFETY_MARKERS:
        if marker in normalized_query:
            return True
    return False


def _extract_allowed_use(hit: dict[str, Any]) -> list[str]:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    value = metadata.get("governance_allowed_use")
    return _split_csv(value)


def apply_retrieval_governance_policy(
    query: str,
    hits: list[dict[str, Any]],
    *,
    top_k: int,
    safety_context: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    safety = is_safety_context_query(query, metadata=metadata) if safety_context is None else bool(safety_context)
    raw_hits_count = len(hits)

    filtered: list[dict[str, Any]] = []
    filtered_internal_only = 0
    for hit in hits:
        allowed_use = {item.lower() for item in _extract_allowed_use(hit)}
        if (not safety) and ("internal_only" in allowed_use):
            filtered_internal_only += 1
            continue
        filtered.append(hit)

    returned_hits = filtered[: max(1, int(top_k))]
    filter_reasons: list[str] = []
    if filtered_internal_only > 0 and not safety:
        filter_reasons.append("internal_only_non_safety_query")

    trace = {
        "policy_version": POLICY_VERSION,
        "safety_context": safety,
        "raw_hits_count": raw_hits_count,
        "internal_only_filtered_count": filtered_internal_only,
        "returned_hits_count": len(returned_hits),
        "filter_reasons": filter_reasons,
    }
    return returned_hits, trace

