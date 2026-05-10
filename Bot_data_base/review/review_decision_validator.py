from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .review_contracts import normalize_iso8601, validate_review_decision_payload
from .review_sanitizer import (
    contains_secret_like_value,
    find_forbidden_review_keys,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_secret_hits(payload: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            hits.extend(_collect_secret_hits(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            hits.extend(_collect_secret_hits(item, f"{path}[{idx}]"))
    elif isinstance(payload, str):
        if contains_secret_like_value(payload):
            hits.append(path)
    return hits


def validate_decisions_overlay(
    *,
    queue_payload: dict[str, Any],
    decisions_payload: dict[str, Any],
    source_prd: str,
) -> dict[str, Any]:
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    queue_index = {
        str(item.get("review_item_id") or ""): str(item.get("block_id") or "")
        for item in queue_items
    }
    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload.get("decisions"), list) else []

    errors: list[str] = []
    warnings: list[str] = []
    unknown_review_item_ids: list[str] = []

    for idx, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            errors.append(f"decision[{idx}] not an object")
            continue
        normalized = dict(decision)
        normalized["created_at"] = normalize_iso8601(normalized.get("created_at"))
        field_errors = validate_review_decision_payload(normalized)
        errors.extend([f"decision[{idx}] {item}" for item in field_errors])
        review_item_id = str(normalized.get("review_item_id") or "")
        block_id = str(normalized.get("block_id") or "")
        if review_item_id not in queue_index:
            unknown_review_item_ids.append(review_item_id)
            errors.append(f"decision[{idx}] unknown_review_item_id:{review_item_id}")
        elif queue_index[review_item_id] != block_id:
            errors.append(f"decision[{idx}] block_id_mismatch:{review_item_id}")
        if str(normalized.get("source_prd") or "") != source_prd:
            errors.append(f"decision[{idx}] source_prd_mismatch")

    forbidden_key_hits = find_forbidden_review_keys(decisions_payload)
    if forbidden_key_hits:
        errors.append("forbidden_keys_present")
    secret_like_hits = _collect_secret_hits(decisions_payload)
    if secret_like_hits:
        errors.append("secret_like_values_present")

    decision_counts = Counter(
        str(item.get("decision") or "")
        for item in decisions
        if isinstance(item, dict) and str(item.get("decision") or "").strip()
    )

    return {
        "schema_version": "kb_review_decisions_validation_v1",
        "source_prd": source_prd,
        "validated_at": _utc_now(),
        "queue_items_count": len(queue_items),
        "decisions_count": len(decisions),
        "valid": len(errors) == 0,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "forbidden_key_hits": forbidden_key_hits,
        "secret_like_hits": secret_like_hits,
        "unknown_review_item_ids": sorted(set([item for item in unknown_review_item_ids if item])),
        "decision_counts": dict(sorted(decision_counts.items())),
    }

