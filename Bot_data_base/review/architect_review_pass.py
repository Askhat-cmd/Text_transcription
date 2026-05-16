from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .post_reprocess_review_decisions import (
    build_block_index,
    sanitize_runtime_log_lines,
    validate_human_review_decisions,
)
from .review_sanitizer import find_forbidden_review_keys, sanitize_preview


FORBIDDEN_BATCH_KEYS = {
    "text",
    "content",
    "content_full",
    "full_text",
    "raw_text",
    "source_raw",
    "chapter_text",
    "full_chunk_text",
    "embedding",
    "vector",
    "api_key",
    "secret",
    "token",
    "password",
}

ALLOWED_DECISION_VALUES = {"approved", "rejected", "needs_edit", "defer"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _to_governance(block: dict[str, Any]) -> dict[str, Any]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance")
    return governance if isinstance(governance, dict) else {}


def _to_heading_path(block: dict[str, Any]) -> list[str]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    return _normalize_list(metadata.get("heading_path"))


def _to_llm_enrichment(block: dict[str, Any]) -> dict[str, Any]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    enrichment = metadata.get("llm_enrichment")
    return enrichment if isinstance(enrichment, dict) else {}


def _to_source_id(block: dict[str, Any], fallback: str = "") -> str:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    source_id = str(metadata.get("source_id") or "").strip()
    if source_id:
        return source_id
    governance = _to_governance(block)
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    trace_source = str(source_trace.get("source_id") or "").strip()
    if trace_source:
        return trace_source
    source = str(block.get("source") or "").strip()
    if ":" in source:
        return source.split(":", 1)[1]
    return fallback or source


def _queue_items(queue_payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    return [item for item in items if isinstance(item, dict)]


def build_architect_review_items(
    *,
    queue_payload: dict[str, Any],
    blocks_payload: Any,
) -> list[dict[str, Any]]:
    block_index = build_block_index(blocks_payload)
    items = _queue_items(queue_payload)

    result: list[dict[str, Any]] = []
    for item in items:
        review_item_id = str(item.get("review_item_id") or "").strip()
        block_id = str(item.get("block_id") or "").strip()
        block = block_index.get(block_id, {})
        governance = _to_governance(block)
        enrichment = _to_llm_enrichment(block)

        summary = str(enrichment.get("summary") or item.get("advisory_summary_preview") or "").strip()
        tags = _normalize_list(enrichment.get("tags"))
        lens_candidates = _normalize_list(enrichment.get("lens_family_candidates"))
        use_when = _normalize_list(enrichment.get("use_when"))
        avoid_when = _normalize_list(enrichment.get("avoid_when"))

        safe_preview = sanitize_preview(str(item.get("safe_preview") or block.get("text") or ""), limit=240)

        result.append(
            {
                "review_item_id": review_item_id,
                "block_id": block_id,
                "source_id": str(item.get("source_id") or _to_source_id(block, fallback="")).strip(),
                "heading_path": _to_heading_path(block),
                "chunk_type": str(item.get("chunk_type") or governance.get("chunk_type") or "unknown").strip(),
                "allowed_use": _normalize_list(governance.get("allowed_use")),
                "safety_flags": _normalize_list(governance.get("safety_flags")),
                "lens_family": _normalize_list(governance.get("lens_family")),
                "review_priority": str(item.get("review_priority") or "P2"),
                "review_reasons": _normalize_list(item.get("review_reasons")),
                "recommended_action": str(item.get("recommended_action") or "defer"),
                "safe_preview": safe_preview,
                "llm_enrichment": {
                    "summary": sanitize_preview(summary, limit=600),
                    "tags": tags,
                    "lens_family_candidates": lens_candidates,
                    "use_when": use_when,
                    "avoid_when": avoid_when,
                    "self_contained_score": enrichment.get("self_contained_score"),
                    "self_contained_reason": sanitize_preview(str(enrichment.get("self_contained_reason") or ""), limit=500),
                    "confidence": enrichment.get("confidence"),
                },
                "architect_decision_slot": "",
                "architect_reason_slot": "",
                "architect_edits_slot": {},
            }
        )

    return result


def _slice_batches(items: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size < 1:
        batch_size = 11
    return [items[idx : idx + batch_size] for idx in range(0, len(items), batch_size)]


def _render_batch_markdown(*, batch_id: int, items: list[dict[str, Any]], source_prd: str, queue_source_prd: str) -> str:
    lines = [
        f"# Architect Review Batch {batch_id:02d} - {source_prd}",
        "",
        "## Batch Context",
        f"- source_prd: {source_prd}",
        f"- queue_source_prd: {queue_source_prd}",
        f"- items_in_batch: {len(items)}",
        "- decision_values: approved | rejected | needs_edit | defer",
        "",
    ]

    for item in items:
        lines.extend(
            [
                f"## {item.get('review_item_id')} / {item.get('block_id')}",
                f"- source_id: {item.get('source_id')}",
                f"- heading_path: {' > '.join(item.get('heading_path') or [])}",
                f"- chunk_type: {item.get('chunk_type')}",
                f"- allowed_use: {', '.join(item.get('allowed_use') or [])}",
                f"- safety_flags: {', '.join(item.get('safety_flags') or [])}",
                f"- lens_family: {', '.join(item.get('lens_family') or [])}",
                f"- review_priority: {item.get('review_priority')}",
                f"- review_reasons: {', '.join(item.get('review_reasons') or [])}",
                f"- recommended_action: {item.get('recommended_action')}",
                f"- safe_preview: {item.get('safe_preview')}",
                "- llm_enrichment:",
                f"  - summary: {(item.get('llm_enrichment') or {}).get('summary')}",
                f"  - tags: {', '.join((item.get('llm_enrichment') or {}).get('tags') or [])}",
                f"  - lens_family_candidates: {', '.join((item.get('llm_enrichment') or {}).get('lens_family_candidates') or [])}",
                f"  - use_when: {' | '.join((item.get('llm_enrichment') or {}).get('use_when') or [])}",
                f"  - avoid_when: {' | '.join((item.get('llm_enrichment') or {}).get('avoid_when') or [])}",
                f"  - self_contained_score: {(item.get('llm_enrichment') or {}).get('self_contained_score')}",
                f"  - self_contained_reason: {(item.get('llm_enrichment') or {}).get('self_contained_reason')}",
                f"  - confidence: {(item.get('llm_enrichment') or {}).get('confidence')}",
                "- architect_decision_slot:",
                "- architect_reason_slot:",
                "- architect_edits_slot:",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _contains_forbidden_batch_label(markdown_text: str) -> list[str]:
    hits: list[str] = []
    normalized = markdown_text.lower()
    for key in sorted(FORBIDDEN_BATCH_KEYS):
        pattern = rf"(^|\n)\s*[-*]\s*{re.escape(key)}\s*:"
        if re.search(pattern, normalized):
            hits.append(key)
    return hits


def create_architect_batches(
    *,
    items: list[dict[str, Any]],
    source_prd: str,
    queue_source_prd: str,
    out_dir: Path,
    batch_size: int,
) -> dict[str, Any]:
    batches_dir = out_dir / "batches"
    batches = _slice_batches(items, batch_size=batch_size)

    batch_rows: list[dict[str, Any]] = []
    forbidden_hits: list[str] = []

    for idx, batch_items in enumerate(batches, start=1):
        batch_path = batches_dir / f"review_batch_{idx:02d}.md"
        markdown = _render_batch_markdown(
            batch_id=idx,
            items=batch_items,
            source_prd=source_prd,
            queue_source_prd=queue_source_prd,
        )
        write_text(batch_path, markdown)
        forbidden_hits.extend(_contains_forbidden_batch_label(markdown))

        priorities = Counter(str(item.get("review_priority") or "P2") for item in batch_items)
        batch_rows.append(
            {
                "batch_id": idx,
                "path": batch_path.as_posix(),
                "items_count": len(batch_items),
                "review_item_ids": [str(item.get("review_item_id") or "") for item in batch_items],
                "priority_counts": {
                    "P0": int(priorities.get("P0", 0)),
                    "P1": int(priorities.get("P1", 0)),
                    "P2": int(priorities.get("P2", 0)),
                },
            }
        )

    index = {
        "schema_version": "architect_review_batches_index_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "queue_source_prd": queue_source_prd,
        "queue_items_count": len(items),
        "batch_size_requested": batch_size,
        "batches_count": len(batch_rows),
        "batches": batch_rows,
        "forbidden_batch_keys_detected": sorted(set(forbidden_hits)),
        "sanitized": len(set(forbidden_hits)) == 0,
    }
    write_json(out_dir / "architect_review_batches_index.json", index)
    return index


def build_architect_decisions_template(
    *,
    source_prd: str,
    queue_source_prd: str,
    review_queue_hash: str,
    blocks_hash_before: str,
) -> dict[str, Any]:
    return {
        "schema_version": "kb_review_decisions_v1",
        "source_prd": source_prd,
        "source_review_queue_prd": queue_source_prd,
        "review_queue_hash": review_queue_hash,
        "blocks_hash_before": blocks_hash_before,
        "decision_owner": "architect_chatgpt",
        "created_at": utc_now_iso(),
        "ready_for_architect_review": True,
        "apply_ready": False,
        "decisions": [],
    }


def validate_architect_decisions_overlay(
    *,
    queue_payload: dict[str, Any],
    decisions_payload: dict[str, Any],
    blocks_payload: Any,
    source_prd: str,
) -> dict[str, Any]:
    base = validate_human_review_decisions(
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        blocks_payload=blocks_payload,
        source_prd=source_prd,
    )

    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    queue_count = len(queue_items)
    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload.get("decisions"), list) else []

    unique_ids = {
        str(item.get("review_item_id") or "")
        for item in decisions
        if isinstance(item, dict) and str(item.get("review_item_id") or "").strip()
    }

    invalid_decision_values = sorted(
        {
            str(item.get("decision") or "")
            for item in decisions
            if isinstance(item, dict) and str(item.get("decision") or "") not in ALLOWED_DECISION_VALUES
        }
    )

    coverage_decided = len(unique_ids)
    coverage_remaining = max(0, queue_count - coverage_decided)
    coverage_percent = round((coverage_decided / queue_count) * 100, 4) if queue_count > 0 else 0.0

    apply_ready = bool(base.get("valid")) and queue_count > 0 and coverage_decided == queue_count and not invalid_decision_values
    ready_for_architect_review = queue_count > 0 and coverage_decided == 0

    merged = dict(base)
    merged.update(
        {
            "schema_version": "architect_review_decisions_validation_v1",
            "decision_owner": str(decisions_payload.get("decision_owner") or ""),
            "coverage": {
                "queue_items_count": queue_count,
                "decisions_count": len(decisions),
                "unique_review_item_ids_count": coverage_decided,
                "remaining_items_count": coverage_remaining,
                "coverage_percent": coverage_percent,
            },
            "ready_for_architect_review": ready_for_architect_review,
            "apply_ready": apply_ready,
            "invalid_decision_values": invalid_decision_values,
        }
    )
    return merged


def render_architect_validation_markdown(payload: dict[str, Any], source_prd: str) -> str:
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    lines = [
        f"# {source_prd} ARCHITECT DECISIONS VALIDATION REPORT",
        "",
        "## Summary",
        f"- valid: {payload.get('valid')}",
        f"- queue_items_count: {coverage.get('queue_items_count')}",
        f"- decisions_count: {coverage.get('decisions_count')}",
        f"- unique_review_item_ids_count: {coverage.get('unique_review_item_ids_count')}",
        f"- remaining_items_count: {coverage.get('remaining_items_count')}",
        f"- coverage_percent: {coverage.get('coverage_percent')}",
        f"- ready_for_architect_review: {payload.get('ready_for_architect_review')}",
        f"- apply_ready: {payload.get('apply_ready')}",
        "",
        "## Errors",
    ]
    errors = payload.get("errors") or []
    if errors:
        lines.extend([f"- {item}" for item in errors])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    warnings = payload.get("warnings") or []
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety Signals",
            f"- forbidden_key_hits: {payload.get('forbidden_key_hits')}",
            f"- secret_like_hits: {payload.get('secret_like_hits')}",
            f"- duplicate_review_item_ids: {payload.get('duplicate_review_item_ids')}",
            f"- unknown_review_item_ids: {payload.get('unknown_review_item_ids')}",
            f"- block_id_mismatches: {payload.get('block_id_mismatches')}",
            f"- authority_field_mutation_attempts: {payload.get('authority_field_mutation_attempts')}",
            f"- invalid_decision_values: {payload.get('invalid_decision_values')}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_no_mutation_proof(
    *,
    source_prd: str,
    queue_path: Path,
    blocks_path: Path,
    registry_path: Path,
    decisions_overlay_path: Path,
    blocks_hash_before: str,
    registry_hash_before: str,
    chroma_count_before: int | None,
    chroma_count_after: int | None,
) -> dict[str, Any]:
    blocks_hash_after = sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_hash_after = sha256_file(registry_path) if registry_path.exists() else ""
    return {
        "schema_version": "architect_review_no_mutation_proof_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "review_queue_hash": sha256_file(queue_path) if queue_path.exists() else "",
        "decisions_overlay_hash": sha256_file(decisions_overlay_path) if decisions_overlay_path.exists() else "",
        "all_blocks_merged_hash_before": blocks_hash_before,
        "all_blocks_merged_hash_after": blocks_hash_after,
        "registry_hash_before": registry_hash_before,
        "registry_hash_after": registry_hash_after,
        "all_blocks_merged_mutated": blocks_hash_before != blocks_hash_after,
        "registry_mutated": bool(registry_hash_before and registry_hash_after and registry_hash_before != registry_hash_after),
        "chroma_count_before": chroma_count_before,
        "chroma_count_after": chroma_count_after,
        "chroma_mutated": (
            chroma_count_before is not None and chroma_count_after is not None and chroma_count_before != chroma_count_after
        ),
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
    }


def read_optional_chroma_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("dashboard_chroma_count", "registry_chroma_count", "chroma_count", "chroma_count_after", "count"):
        value = payload.get(key)
        try:
            if value is not None:
                return int(value)
        except Exception:
            continue
    return None


def queue_alignment_summary(queue_payload: dict[str, Any], blocks_payload: Any) -> dict[str, Any]:
    block_index = build_block_index(blocks_payload)
    queue = _queue_items(queue_payload)
    block_ids = set(block_index.keys())
    queue_ids = {str(item.get("block_id") or "") for item in queue if str(item.get("block_id") or "")}
    present = len(queue_ids.intersection(block_ids))
    missing = len(queue_ids.difference(block_ids))
    return {
        "blocks_total": len(block_index),
        "queue_items_count": len(queue),
        "queue_block_ids_present": present,
        "queue_block_ids_missing": missing,
    }


def ensure_batch_payload_sanitized(payload: Any) -> list[str]:
    hits = find_forbidden_review_keys(payload)
    return sorted(set(hits))


def render_batches_report(index_payload: dict[str, Any], alignment: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} ARCHITECT REVIEW BATCHES REPORT",
        "",
        "## Summary",
        f"- queue_items_count: {alignment.get('queue_items_count')}",
        f"- blocks_total: {alignment.get('blocks_total')}",
        f"- queue_block_ids_present: {alignment.get('queue_block_ids_present')}",
        f"- queue_block_ids_missing: {alignment.get('queue_block_ids_missing')}",
        f"- batches_count: {index_payload.get('batches_count')}",
        f"- batch_size_requested: {index_payload.get('batch_size_requested')}",
        f"- sanitized: {index_payload.get('sanitized')}",
        "",
        "## Batches",
    ]
    batches = index_payload.get("batches") if isinstance(index_payload.get("batches"), list) else []
    if not batches:
        lines.append("- none")
    else:
        for batch in batches:
            lines.append(
                f"- batch_{int(batch.get('batch_id') or 0):02d}: items={batch.get('items_count')} path={batch.get('path')}"
            )

    return "\n".join(lines).rstrip() + "\n"
