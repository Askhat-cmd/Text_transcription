from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_contracts import ReviewItem, build_review_item_id, validate_review_item_payload
from .review_sanitizer import assert_review_artifact_is_sanitized, sanitize_preview


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split_source_id(source: str) -> str:
    raw = str(source or "").strip()
    if ":" in raw:
        return raw.split(":", 1)[1]
    return raw


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def discover_input_file(explicit_path: Path | None = None) -> Path | None:
    if explicit_path:
        return explicit_path if explicit_path.exists() else None
    candidates = [
        Path("Bot_data_base/data/processed/all_blocks_merged.json"),
    ]
    for pattern in (
        "Bot_data_base/data/processed/*all_blocks*.json",
        "Bot_data_base/data/**/all_blocks_merged.json",
    ):
        candidates.extend(sorted(Path(".").glob(pattern)))
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def _extract_blocks(container: Any) -> list[dict[str, Any]]:
    if isinstance(container, dict):
        blocks = container.get("blocks")
        return blocks if isinstance(blocks, list) else []
    if isinstance(container, list):
        return [item for item in container if isinstance(item, dict)]
    return []


def _review_trigger_reasons(block: dict[str, Any]) -> list[str]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    enrichment = metadata.get("llm_enrichment") if isinstance(metadata.get("llm_enrichment"), dict) else {}
    chunking_quality = metadata.get("chunking_quality") if isinstance(metadata.get("chunking_quality"), dict) else {}

    reasons: list[str] = []
    if bool(enrichment.get("needs_human_review")):
        reasons.append("needs_human_review")
    review_status = str(enrichment.get("review_status") or "").lower()
    if "review" in review_status:
        reasons.append("review_status_requires_review")
    if _to_list(enrichment.get("review_reasons")):
        reasons.append("review_reasons_present")
    if _to_float(enrichment.get("confidence"), 1.0) < 0.80:
        reasons.append("low_confidence")
    if _to_float(enrichment.get("self_contained_score"), 1.0) < 0.75:
        reasons.append("low_self_contained_score")
    split_suggestion = enrichment.get("split_merge_suggestion")
    split_action = ""
    if isinstance(split_suggestion, dict):
        split_action = str(split_suggestion.get("action") or "").strip().lower()
    elif split_suggestion is not None:
        split_action = str(split_suggestion).strip().lower()
    if split_action and split_action != "keep":
        reasons.append("split_merge_suggested")
    if str(chunking_quality.get("mixed_intent_severity") or "").strip().lower() in {"medium", "high"}:
        reasons.append("mixed_intent_medium_or_high")
    return sorted(set(reasons))


def _priority_for_block(block: dict[str, Any], reasons: list[str]) -> str:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    enrichment = metadata.get("llm_enrichment") if isinstance(metadata.get("llm_enrichment"), dict) else {}
    chunking_quality = metadata.get("chunking_quality") if isinstance(metadata.get("chunking_quality"), dict) else {}

    allowed_use = {item.lower() for item in _to_list(governance.get("allowed_use"))}
    safety_flags = {item.lower() for item in _to_list(governance.get("safety_flags"))}
    review_reason_text = " ".join(_to_list(enrichment.get("review_reasons"))).lower()
    split_suggestion = enrichment.get("split_merge_suggestion")
    split_action = ""
    if isinstance(split_suggestion, dict):
        split_action = str(split_suggestion.get("action") or "").strip().lower()
    elif split_suggestion is not None:
        split_action = str(split_suggestion).strip().lower()

    if (
        "safety_protocol" in allowed_use
        or _to_float(enrichment.get("confidence"), 1.0) < 0.65
        or _to_float(enrichment.get("self_contained_score"), 1.0) < 0.60
        or str(chunking_quality.get("mixed_intent_severity") or "").strip().lower() == "high"
        or split_action in {"split", "merge", "split_merge_review"}
        or any(token in review_reason_text for token in ("quote", "safety", "low_resource", "hard_validation"))
        or any(token in safety_flags for token in ("requires_grounding", "source_style_not_user_facing"))
    ):
        return "P0"

    if (
        bool(enrichment.get("needs_human_review"))
        or _to_float(enrichment.get("confidence"), 1.0) < 0.80
        or _to_float(enrichment.get("self_contained_score"), 1.0) < 0.75
        or bool(_to_list(enrichment.get("review_reasons")))
        or not _to_list(enrichment.get("avoid_when"))
        or not _to_list(enrichment.get("use_when"))
    ):
        return "P1"

    return "P2"


def _recommended_action(block: dict[str, Any], reasons: list[str]) -> str:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    enrichment = metadata.get("llm_enrichment") if isinstance(metadata.get("llm_enrichment"), dict) else {}
    chunking_quality = metadata.get("chunking_quality") if isinstance(metadata.get("chunking_quality"), dict) else {}
    review_reason_text = " ".join(_to_list(enrichment.get("review_reasons"))).lower()

    split_suggestion = enrichment.get("split_merge_suggestion")
    split_action = ""
    if isinstance(split_suggestion, dict):
        split_action = str(split_suggestion.get("action") or "").strip().lower()
    elif split_suggestion is not None:
        split_action = str(split_suggestion).strip().lower()

    if split_action in {"split", "merge", "split_merge_review"} or str(
        chunking_quality.get("mixed_intent_severity") or ""
    ).strip().lower() == "high":
        return "split_merge_review"

    if any(token in review_reason_text for token in ("quote", "unsafe", "direct")):
        return "reject"

    if reasons:
        return "needs_edit"

    confidence = _to_float(enrichment.get("confidence"), 0.0)
    if confidence >= 0.80:
        return "approve"
    return "defer"


def _build_review_item(block: dict[str, Any], source_prd: str) -> ReviewItem:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    enrichment = metadata.get("llm_enrichment") if isinstance(metadata.get("llm_enrichment"), dict) else {}

    source = str(block.get("source") or "").strip()
    source_id = str(metadata.get("source_id") or "").strip() or _split_source_id(source)
    block_id = str(block.get("id") or block.get("chunk_id") or "").strip()
    schema_version = str(enrichment.get("schema_version") or "kb_llm_enrichment_v1")
    reasons = _review_trigger_reasons(block)
    review_item = ReviewItem(
        review_item_id=build_review_item_id(source_id, block_id, schema_version),
        block_id=block_id,
        source_id=source_id,
        source_title=str(metadata.get("source_title") or block.get("title") or "").strip(),
        chunk_type=str(governance.get("chunk_type") or "unknown").strip() or "unknown",
        allowed_use=_to_list(governance.get("allowed_use")),
        safety_flags=_to_list(governance.get("safety_flags")),
        lens_family=_to_list(governance.get("lens_family")),
        content_preview=sanitize_preview(str(block.get("text") or ""), limit=240),
        llm_enrichment={
            "schema_version": str(enrichment.get("schema_version") or "").strip(),
            "summary": str(enrichment.get("summary") or "").strip(),
            "lens_family_candidates": _to_list(enrichment.get("lens_family_candidates")),
            "tags": _to_list(enrichment.get("tags")),
            "use_when": _to_list(enrichment.get("use_when")),
            "avoid_when": _to_list(enrichment.get("avoid_when")),
            "self_contained_score": _to_float(enrichment.get("self_contained_score"), 0.0),
            "self_contained_reason": str(enrichment.get("self_contained_reason") or "").strip(),
            "split_merge_suggestion": enrichment.get("split_merge_suggestion"),
            "confidence": _to_float(enrichment.get("confidence"), 0.0),
            "needs_human_review": bool(enrichment.get("needs_human_review")),
            "review_status": str(enrichment.get("review_status") or "").strip(),
            "review_reasons": _to_list(enrichment.get("review_reasons")),
            "llm_metadata": enrichment.get("llm_metadata") if isinstance(enrichment.get("llm_metadata"), dict) else {},
        },
        review_priority=_priority_for_block(block, reasons),
        review_reasons=reasons,
        recommended_action=_recommended_action(block, reasons),
        source_prd=source_prd,
    )
    return review_item


def build_review_queue(*, input_path: Path, max_items: int, source_prd: str) -> dict[str, Any]:
    before_sha = _sha256_file(input_path)
    container = json.loads(input_path.read_text(encoding="utf-8"))
    blocks = _extract_blocks(container)

    items: list[dict[str, Any]] = []
    for block in blocks:
        reasons = _review_trigger_reasons(block)
        if not reasons:
            continue
        item = _build_review_item(block, source_prd=source_prd)
        payload = item.to_dict()
        errors = validate_review_item_payload(payload)
        if errors:
            continue
        items.append(payload)

    items.sort(key=lambda row: (row.get("review_priority", "P2"), row.get("review_item_id", "")))
    if max_items > 0:
        items = items[:max_items]

    after_sha = _sha256_file(input_path)
    source_mutated = before_sha != after_sha
    priority_counts = Counter(row.get("review_priority", "P2") for row in items)
    action_counts = Counter(row.get("recommended_action", "defer") for row in items)

    payload = {
        "schema_version": "kb_review_queue_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "input_file": str(input_path.as_posix()),
        "input_file_sha256_before": before_sha,
        "input_file_sha256_after": after_sha,
        "source_mutated": source_mutated,
        "total_blocks_scanned": len(blocks),
        "review_items_count": len(items),
        "priority_counts": {
            "P0": int(priority_counts.get("P0", 0)),
            "P1": int(priority_counts.get("P1", 0)),
            "P2": int(priority_counts.get("P2", 0)),
        },
        "recommended_action_counts": {
            "approve": int(action_counts.get("approve", 0)),
            "reject": int(action_counts.get("reject", 0)),
            "needs_edit": int(action_counts.get("needs_edit", 0)),
            "split_merge_review": int(action_counts.get("split_merge_review", 0)),
            "defer": int(action_counts.get("defer", 0)),
        },
        "items": items,
    }

    assert_review_artifact_is_sanitized(payload)
    return payload

