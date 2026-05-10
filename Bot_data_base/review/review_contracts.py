from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


ALLOWED_CHUNK_TYPES = {
    "lens",
    "practice",
    "case",
    "theory",
    "style",
    "safety",
    "architecture",
    "unknown",
}
ALLOWED_REVIEW_PRIORITIES = {"P0", "P1", "P2"}
ALLOWED_RECOMMENDED_ACTIONS = {"approve", "reject", "needs_edit", "split_merge_review", "defer"}
ALLOWED_DECISIONS = {"approved", "rejected", "needs_edit", "defer"}
ALLOWED_REVIEWERS = {"human", "architect", "admin"}
ADVISORY_FIELDS = {
    "summary",
    "lens_family_candidates",
    "tags",
    "use_when",
    "avoid_when",
    "self_contained_score",
    "self_contained_reason",
    "split_merge_suggestion",
    "confidence",
}

FORBIDDEN_DECISION_FIELD_KEYS = {
    "text",
    "content",
    "content_full",
    "full_text",
    "raw_text",
    "source_raw",
    "chapter_text",
    "full_chunk_text",
    "chunk_type",
    "allowed_use",
    "safety_flags",
    "not_for_direct_quote",
    "source_style_not_user_facing",
    "internal_only",
    "do_not_use",
    "governance",
    "embedding",
    "vector",
    ".env",
    "api_key",
    "secret",
    "token",
    "password",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_iso8601(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return _utc_now()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except Exception:
        return _utc_now()


def build_review_item_id(source_id: str, block_id: str, schema_version: str) -> str:
    base = f"{source_id}|{block_id}|{schema_version}"
    return "kbri_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


@dataclass
class ReviewItem:
    review_item_id: str
    block_id: str
    source_id: str
    source_title: str
    chunk_type: str
    allowed_use: list[str]
    safety_flags: list[str]
    lens_family: list[str]
    content_preview: str
    llm_enrichment: dict[str, Any]
    review_priority: str
    review_reasons: list[str]
    recommended_action: str
    source_prd: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewDecision:
    review_item_id: str
    block_id: str
    decision: str
    reviewer: str
    reason: str
    approved_fields: list[str] = field(default_factory=list)
    rejected_fields: list[str] = field(default_factory=list)
    edited_fields: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)
    source_prd: str = "PRD-046.0.7"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = normalize_iso8601(payload.get("created_at"))
        return payload


def validate_review_item_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in ("review_item_id", "block_id", "source_id", "source_title", "source_prd"):
        if not str(payload.get(field_name) or "").strip():
            errors.append(f"missing_{field_name}")

    chunk_type = str(payload.get("chunk_type") or "").strip()
    if chunk_type not in ALLOWED_CHUNK_TYPES:
        errors.append("invalid_chunk_type")

    priority = str(payload.get("review_priority") or "").strip()
    if priority not in ALLOWED_REVIEW_PRIORITIES:
        errors.append("invalid_review_priority")

    action = str(payload.get("recommended_action") or "").strip()
    if action not in ALLOWED_RECOMMENDED_ACTIONS:
        errors.append("invalid_recommended_action")

    preview = str(payload.get("content_preview") or "")
    if len(preview) > 240:
        errors.append("content_preview_too_long")
    return errors


def validate_review_decision_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in ("review_item_id", "block_id", "decision", "reviewer", "source_prd"):
        if not str(payload.get(field_name) or "").strip():
            errors.append(f"missing_{field_name}")

    if str(payload.get("decision") or "") not in ALLOWED_DECISIONS:
        errors.append("invalid_decision")
    if str(payload.get("reviewer") or "") not in ALLOWED_REVIEWERS:
        errors.append("invalid_reviewer")

    decision = str(payload.get("decision") or "")
    reason = str(payload.get("reason") or "").strip()
    if decision in {"rejected", "needs_edit", "defer"} and not reason:
        errors.append("reason_required_for_decision")

    approved = payload.get("approved_fields") or []
    rejected = payload.get("rejected_fields") or []
    edited = payload.get("edited_fields") or {}

    if not isinstance(approved, list):
        errors.append("approved_fields_must_be_list")
    if not isinstance(rejected, list):
        errors.append("rejected_fields_must_be_list")
    if not isinstance(edited, dict):
        errors.append("edited_fields_must_be_dict")

    for field_name in approved if isinstance(approved, list) else []:
        if str(field_name) not in ADVISORY_FIELDS:
            errors.append(f"approved_field_not_allowed:{field_name}")
    for field_name in rejected if isinstance(rejected, list) else []:
        if str(field_name) not in ADVISORY_FIELDS:
            errors.append(f"rejected_field_not_allowed:{field_name}")
    for field_name in edited.keys() if isinstance(edited, dict) else []:
        if str(field_name) not in ADVISORY_FIELDS:
            errors.append(f"edited_field_not_allowed:{field_name}")
        if str(field_name).strip().lower() in FORBIDDEN_DECISION_FIELD_KEYS:
            errors.append(f"edited_field_forbidden:{field_name}")

    return errors

