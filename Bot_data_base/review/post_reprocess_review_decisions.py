from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_contracts import (
    ADVISORY_FIELDS,
    ALLOWED_DECISIONS,
    ALLOWED_REVIEWERS,
    FORBIDDEN_DECISION_FIELD_KEYS,
    validate_review_decision_payload,
)
from .review_sanitizer import (
    contains_secret_like_value,
    find_forbidden_review_keys,
    sanitize_preview,
)


DECISION_SCHEMA_VERSION = "kb_review_decisions_v1"
VALIDATION_SCHEMA_VERSION = "kb_review_decisions_validation_v1"

AUTHORITY_FIELDS = {
    "text",
    "content",
    "content_full",
    "full_text",
    "source_raw",
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
    "source_id",
    "block_id",
}

WARNING_LIMITS = {
    "summary": 600,
    "tags_items": 20,
    "tags_item_len": 64,
    "lens_items": 10,
    "lens_item_len": 64,
    "use_when_items": 12,
    "use_when_item_len": 180,
    "avoid_when_items": 12,
    "avoid_when_item_len": 180,
    "self_contained_reason": 500,
    "split_merge_suggestion": 500,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _extract_blocks(container: Any) -> list[dict[str, Any]]:
    if isinstance(container, dict):
        blocks = container.get("blocks")
        return [item for item in blocks if isinstance(item, dict)] if isinstance(blocks, list) else []
    if isinstance(container, list):
        return [item for item in container if isinstance(item, dict)]
    return []


def build_block_index(blocks_payload: Any) -> dict[str, dict[str, Any]]:
    blocks = _extract_blocks(blocks_payload)
    index: dict[str, dict[str, Any]] = {}
    for block in blocks:
        block_id = str(block.get("id") or block.get("chunk_id") or "").strip()
        if block_id:
            index[block_id] = block
    return index


def _to_source_id(block: dict[str, Any]) -> str:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    source_id = str(metadata.get("source_id") or "").strip()
    if source_id:
        return source_id
    source = str(block.get("source") or "").strip()
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _to_governance(block: dict[str, Any]) -> dict[str, Any]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance")
    return governance if isinstance(governance, dict) else {}


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


def _read_optional_chroma_count(chroma_snapshot_path: Path) -> int | None:
    if not chroma_snapshot_path.exists():
        return None
    try:
        payload = read_json(chroma_snapshot_path)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    for key in (
        "dashboard_chroma_count",
        "registry_chroma_count",
        "chroma_count",
        "chroma_count_after",
        "count",
    ):
        value = payload.get(key)
        try:
            if value is not None:
                return int(value)
        except Exception:
            continue
    return None


def build_review_source_manifest(
    *,
    queue_payload: dict[str, Any],
    queue_path: Path,
    blocks_path: Path,
    source_prd: str,
    expected_source_prd: str,
    block_index: dict[str, dict[str, Any]],
    registry_path: Path,
    chroma_snapshot_path: Path,
) -> dict[str, Any]:
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    queue_block_ids = [str(item.get("block_id") or "").strip() for item in queue_items if isinstance(item, dict)]
    queue_block_ids = [item for item in queue_block_ids if item]

    missing_block_ids = sorted([block_id for block_id in queue_block_ids if block_id not in block_index])
    present_count = len(queue_block_ids) - len(missing_block_ids)

    priority_counts = queue_payload.get("priority_counts") if isinstance(queue_payload.get("priority_counts"), dict) else {}
    p0 = int(priority_counts.get("P0") or 0)
    p1 = int(priority_counts.get("P1") or 0)
    p2 = int(priority_counts.get("P2") or 0)

    registry_hash = sha256_file(registry_path) if registry_path.exists() else ""
    chroma_count = _read_optional_chroma_count(chroma_snapshot_path)

    return {
        "schema_version": "post_reprocess_human_review_source_manifest_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "review_queue_path": str(queue_path.as_posix()),
        "review_queue_hash": sha256_file(queue_path),
        "review_queue_schema_version": str(queue_payload.get("schema_version") or ""),
        "review_queue_source_prd": str(queue_payload.get("source_prd") or ""),
        "expected_source_review_queue_prd": expected_source_prd,
        "source_review_queue_prd_match": str(queue_payload.get("source_prd") or "") == expected_source_prd,
        "queue_items_count": len(queue_items),
        "priority_counts": {"P0": p0, "P1": p1, "P2": p2},
        "blocks_path": str(blocks_path.as_posix()),
        "blocks_hash_before": sha256_file(blocks_path),
        "blocks_total": len(block_index),
        "queue_block_ids_present_in_blocks_count": present_count,
        "queue_block_ids_missing_in_blocks_count": len(missing_block_ids),
        "queue_block_ids_missing_in_blocks_sample": missing_block_ids[:20],
        "registry_path": str(registry_path.as_posix()) if registry_path.exists() else "",
        "registry_hash_before": registry_hash,
        "chroma_snapshot_path": str(chroma_snapshot_path.as_posix()) if chroma_snapshot_path.exists() else "",
        "chroma_count_before": chroma_count,
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
        "governance_authority_mutated": False,
    }


def build_review_workbench(
    *,
    queue_payload: dict[str, Any],
    block_index: dict[str, dict[str, Any]],
    source_prd: str,
    queue_source_prd: str,
) -> str:
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    priority_counts = queue_payload.get("priority_counts") if isinstance(queue_payload.get("priority_counts"), dict) else {}
    p0 = int(priority_counts.get("P0") or 0)
    p1 = int(priority_counts.get("P1") or 0)
    p2 = int(priority_counts.get("P2") or 0)

    by_priority: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": []}
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        priority = str(item.get("review_priority") or "P2")
        if priority not in by_priority:
            priority = "P2"
        by_priority[priority].append(item)

    lines: list[str] = [
        f"# Human Review Workbench - {source_prd}",
        "",
        "## Summary",
        f"- queue source: {queue_source_prd}",
        f"- items: {len(queue_items)}",
        f"- priorities: P0/P1/P2 = {p0}/{p1}/{p2}",
        "- production mutation: false",
        "",
        "## Review rules",
        "- Check advisory enrichment only.",
        "- Do not mutate governance authority fields.",
        "- Do not quote source directly to end users.",
        "- Do not auto-approve without manual review.",
        "- Use defer when uncertain.",
        "",
        "## Decision values",
        "- approved",
        "- rejected",
        "- needs_edit",
        "- defer",
        "",
        "## Items",
    ]

    for priority in ("P0", "P1", "P2"):
        lines.append("")
        lines.append(f"### {priority}")
        items = by_priority.get(priority) or []
        if not items:
            lines.append("")
            lines.append("- none")
            continue

        for item in items:
            review_item_id = str(item.get("review_item_id") or "").strip()
            block_id = str(item.get("block_id") or "").strip()
            block = block_index.get(block_id, {})
            gov = _to_governance(block)
            source_id = str(item.get("source_id") or _to_source_id(block) or "").strip()
            chunk_type = str(item.get("chunk_type") or gov.get("chunk_type") or "unknown").strip() or "unknown"
            allowed_use = _normalize_list(gov.get("allowed_use"))
            safety_flags = _normalize_list(gov.get("safety_flags"))
            lens_family = _normalize_list(gov.get("lens_family"))
            review_reasons = _normalize_list(item.get("review_reasons"))
            recommended_action = str(item.get("recommended_action") or "defer").strip() or "defer"
            preview = sanitize_preview(str(item.get("safe_preview") or ""), limit=240)
            advisory_preview = sanitize_preview(str(item.get("advisory_summary_preview") or ""), limit=240)

            lines.extend(
                [
                    "",
                    f"#### {review_item_id} / block_id {block_id}",
                    f"- source_id: {source_id}",
                    f"- chunk_type: {chunk_type}",
                    f"- allowed_use: {', '.join(allowed_use) if allowed_use else '-'}",
                    f"- safety_flags: {', '.join(safety_flags) if safety_flags else '-'}",
                    f"- lens_family: {', '.join(lens_family) if lens_family else '-'}",
                    f"- review_reasons: {', '.join(review_reasons) if review_reasons else '-'}",
                    f"- recommended_action: {recommended_action}",
                    f"- content_preview: {preview}",
                    "- llm_enrichment:",
                    f"  - summary: {advisory_preview}",
                    "  - tags:",
                    "  - lens_family_candidates:",
                    "  - use_when:",
                    "  - avoid_when:",
                    "  - confidence:",
                    "- reviewer_notes:",
                    "- suggested_decision_slot:",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def build_review_decisions_template(
    *,
    source_prd: str,
    source_review_queue_prd: str,
    review_queue_hash: str,
    blocks_hash_before: str,
) -> dict[str, Any]:
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "source_prd": source_prd,
        "source_review_queue_prd": source_review_queue_prd,
        "review_queue_hash": review_queue_hash,
        "blocks_hash_before": blocks_hash_before,
        "created_at": utc_now_iso(),
        "decisions": [],
    }


def build_review_decisions_example(
    *,
    queue_payload: dict[str, Any],
    source_prd: str,
) -> dict[str, Any]:
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    decisions: list[dict[str, Any]] = []

    if queue_items:
        first = queue_items[0] if isinstance(queue_items[0], dict) else {}
        decisions.append(
            {
                "review_item_id": str(first.get("review_item_id") or "sample_review_item_1"),
                "block_id": str(first.get("block_id") or "sample_block_1"),
                "decision": "approved",
                "reviewer": "human",
                "reason": "",
                "approved_fields": ["summary", "tags"],
                "rejected_fields": [],
                "edited_fields": {},
                "created_at": utc_now_iso(),
                "source_prd": source_prd,
            }
        )

    if len(queue_items) > 1:
        second = queue_items[1] if isinstance(queue_items[1], dict) else {}
        decisions.append(
            {
                "review_item_id": str(second.get("review_item_id") or "sample_review_item_2"),
                "block_id": str(second.get("block_id") or "sample_block_2"),
                "decision": "needs_edit",
                "reviewer": "admin",
                "reason": "sample edit for contract demonstration",
                "approved_fields": [],
                "rejected_fields": ["avoid_when"],
                "edited_fields": {"avoid_when": ["sample safe rewrite"]},
                "created_at": utc_now_iso(),
                "source_prd": source_prd,
            }
        )

    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "source_prd": source_prd,
        "synthetic_example": True,
        "created_at": utc_now_iso(),
        "decisions": decisions,
    }


def build_review_decisions_summary(
    *,
    queue_payload: dict[str, Any],
    manifest: dict[str, Any],
    template: dict[str, Any],
) -> dict[str, Any]:
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    return {
        "schema_version": "post_reprocess_review_decisions_summary_v1",
        "source_prd": str(manifest.get("source_prd") or ""),
        "generated_at": utc_now_iso(),
        "queue_items_count": len(queue_items),
        "priority_counts": manifest.get("priority_counts") or {"P0": 0, "P1": 0, "P2": 0},
        "queue_block_ids_missing_in_blocks_count": int(manifest.get("queue_block_ids_missing_in_blocks_count") or 0),
        "template_decisions_count": len(template.get("decisions") or []),
        "template_is_empty": len(template.get("decisions") or []) == 0,
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
        "governance_authority_mutated": False,
    }


def validate_human_review_decisions(
    *,
    queue_payload: dict[str, Any],
    decisions_payload: dict[str, Any],
    blocks_payload: Any,
    source_prd: str,
) -> dict[str, Any]:
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    queue_index = {
        str(item.get("review_item_id") or ""): str(item.get("block_id") or "")
        for item in queue_items
        if isinstance(item, dict)
    }
    blocks_index = build_block_index(blocks_payload)
    block_ids = set(blocks_index.keys())

    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload.get("decisions"), list) else []

    errors: list[str] = []
    warnings: list[str] = []
    unknown_review_item_ids: list[str] = []
    block_id_mismatches: list[str] = []
    duplicate_review_item_ids: list[str] = []
    authority_field_mutation_attempts: list[str] = []

    schema_version = str(decisions_payload.get("schema_version") or "")
    if schema_version != DECISION_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")

    if str(decisions_payload.get("source_prd") or "") != source_prd:
        errors.append("source_prd_mismatch")

    if len(decisions) > len(queue_items):
        errors.append("decisions_count_exceeds_queue_items_count")

    forbidden_key_hits = find_forbidden_review_keys(decisions_payload)
    if forbidden_key_hits:
        errors.append("forbidden_keys_present")

    secret_like_hits = _collect_secret_hits(decisions_payload)
    if secret_like_hits:
        errors.append("secret_like_values_present")

    seen_review_item_ids: set[str] = set()
    decision_counts = Counter()

    for idx, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            errors.append(f"decision[{idx}] not_an_object")
            continue

        payload_errors = validate_review_decision_payload(decision)
        for item in payload_errors:
            errors.append(f"decision[{idx}] {item}")

        review_item_id = str(decision.get("review_item_id") or "")
        block_id = str(decision.get("block_id") or "")
        decision_value = str(decision.get("decision") or "")
        reviewer = str(decision.get("reviewer") or "")
        reason = str(decision.get("reason") or "").strip()

        if review_item_id in seen_review_item_ids and review_item_id:
            duplicate_review_item_ids.append(review_item_id)
            errors.append(f"decision[{idx}] duplicate_review_item_id:{review_item_id}")
        if review_item_id:
            seen_review_item_ids.add(review_item_id)

        expected_block_id = queue_index.get(review_item_id)
        if expected_block_id is None:
            if review_item_id:
                unknown_review_item_ids.append(review_item_id)
            errors.append(f"decision[{idx}] unknown_review_item_id:{review_item_id}")
        elif expected_block_id != block_id:
            block_id_mismatches.append(review_item_id)
            errors.append(f"decision[{idx}] block_id_mismatch:{review_item_id}")

        if block_id and block_id not in block_ids:
            block_id_mismatches.append(review_item_id or f"index:{idx}")
            errors.append(f"decision[{idx}] block_id_missing_in_blocks:{block_id}")

        if decision_value not in ALLOWED_DECISIONS:
            errors.append(f"decision[{idx}] invalid_decision:{decision_value}")
        if reviewer not in ALLOWED_REVIEWERS:
            errors.append(f"decision[{idx}] invalid_reviewer:{reviewer}")

        if decision_value in {"rejected", "needs_edit", "defer"} and not reason:
            errors.append(f"decision[{idx}] reason_required_for_decision")

        approved_fields = decision.get("approved_fields") if isinstance(decision.get("approved_fields"), list) else []
        rejected_fields = decision.get("rejected_fields") if isinstance(decision.get("rejected_fields"), list) else []
        edited_fields = decision.get("edited_fields") if isinstance(decision.get("edited_fields"), dict) else {}

        if decision_value == "needs_edit" and not edited_fields and not rejected_fields:
            errors.append(f"decision[{idx}] needs_edit_without_changes")

        if decision_value == "approved" and edited_fields:
            errors.append(f"decision[{idx}] approved_must_not_have_edited_fields")

        for field_name in approved_fields + rejected_fields + list(edited_fields.keys()):
            field_norm = str(field_name).strip()
            if field_norm in AUTHORITY_FIELDS or field_norm in FORBIDDEN_DECISION_FIELD_KEYS:
                authority_field_mutation_attempts.append(f"decision[{idx}] {field_norm}")
                errors.append(f"decision[{idx}] authority_field_mutation_attempt:{field_norm}")

        for field_name in edited_fields.keys():
            if str(field_name) not in ADVISORY_FIELDS:
                errors.append(f"decision[{idx}] edited_field_not_allowed:{field_name}")

        _collect_advisory_warnings(idx=idx, edited_fields=edited_fields, warnings=warnings)
        decision_counts[decision_value] += 1

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "source_prd": source_prd,
        "validated_at": utc_now_iso(),
        "queue_items_count": len(queue_items),
        "decisions_count": len(decisions),
        "valid": len(set(errors)) == 0,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "decision_counts": dict(sorted(decision_counts.items())),
        "forbidden_key_hits": sorted(set(forbidden_key_hits)),
        "secret_like_hits": sorted(set(secret_like_hits)),
        "duplicate_review_item_ids": sorted(set(duplicate_review_item_ids)),
        "unknown_review_item_ids": sorted(set([item for item in unknown_review_item_ids if item])),
        "block_id_mismatches": sorted(set([item for item in block_id_mismatches if item])),
        "authority_field_mutation_attempts": sorted(set(authority_field_mutation_attempts)),
    }


def _collect_advisory_warnings(*, idx: int, edited_fields: dict[str, Any], warnings: list[str]) -> None:
    summary = str(edited_fields.get("summary") or "")
    if summary and len(summary) > WARNING_LIMITS["summary"]:
        warnings.append(f"decision[{idx}] summary_length_exceeds_{WARNING_LIMITS['summary']}")

    _warn_list_limit(
        idx=idx,
        name="tags",
        values=edited_fields.get("tags"),
        max_items=WARNING_LIMITS["tags_items"],
        max_item_len=WARNING_LIMITS["tags_item_len"],
        warnings=warnings,
    )
    _warn_list_limit(
        idx=idx,
        name="lens_family_candidates",
        values=edited_fields.get("lens_family_candidates"),
        max_items=WARNING_LIMITS["lens_items"],
        max_item_len=WARNING_LIMITS["lens_item_len"],
        warnings=warnings,
    )
    _warn_list_limit(
        idx=idx,
        name="use_when",
        values=edited_fields.get("use_when"),
        max_items=WARNING_LIMITS["use_when_items"],
        max_item_len=WARNING_LIMITS["use_when_item_len"],
        warnings=warnings,
    )
    _warn_list_limit(
        idx=idx,
        name="avoid_when",
        values=edited_fields.get("avoid_when"),
        max_items=WARNING_LIMITS["avoid_when_items"],
        max_item_len=WARNING_LIMITS["avoid_when_item_len"],
        warnings=warnings,
    )

    self_contained_reason = str(edited_fields.get("self_contained_reason") or "")
    if self_contained_reason and len(self_contained_reason) > WARNING_LIMITS["self_contained_reason"]:
        warnings.append(
            f"decision[{idx}] self_contained_reason_length_exceeds_{WARNING_LIMITS['self_contained_reason']}"
        )

    split_merge_suggestion = edited_fields.get("split_merge_suggestion")
    if isinstance(split_merge_suggestion, dict):
        serialized = json.dumps(split_merge_suggestion, ensure_ascii=False)
    else:
        serialized = str(split_merge_suggestion or "")
    if serialized and len(serialized) > WARNING_LIMITS["split_merge_suggestion"]:
        warnings.append(
            f"decision[{idx}] split_merge_suggestion_length_exceeds_{WARNING_LIMITS['split_merge_suggestion']}"
        )

    for numeric_name in ("confidence", "self_contained_score"):
        if numeric_name not in edited_fields:
            continue
        value = edited_fields.get(numeric_name)
        try:
            numeric = float(value)
        except Exception:
            warnings.append(f"decision[{idx}] {numeric_name}_not_numeric")
            continue
        if numeric < 0 or numeric > 1:
            warnings.append(f"decision[{idx}] {numeric_name}_out_of_range")


def _warn_list_limit(
    *,
    idx: int,
    name: str,
    values: Any,
    max_items: int,
    max_item_len: int,
    warnings: list[str],
) -> None:
    if values is None:
        return
    if not isinstance(values, list):
        warnings.append(f"decision[{idx}] {name}_must_be_list_for_length_checks")
        return
    if len(values) > max_items:
        warnings.append(f"decision[{idx}] {name}_items_exceed_{max_items}")
    for pos, item in enumerate(values):
        text = str(item)
        if len(text) > max_item_len:
            warnings.append(f"decision[{idx}] {name}[{pos}]_length_exceeds_{max_item_len}")


def render_validation_markdown(validation_payload: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} HUMAN REVIEW DECISIONS VALIDATION REPORT",
        "",
        "## Summary",
        f"- valid: {validation_payload.get('valid')}",
        f"- queue_items_count: {validation_payload.get('queue_items_count')}",
        f"- decisions_count: {validation_payload.get('decisions_count')}",
        f"- errors_count: {len(validation_payload.get('errors') or [])}",
        f"- warnings_count: {len(validation_payload.get('warnings') or [])}",
        "",
        "## Errors",
    ]
    errors = validation_payload.get("errors") or []
    if errors:
        for item in errors:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    warnings = validation_payload.get("warnings") or []
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety Signals",
            f"- forbidden_key_hits: {validation_payload.get('forbidden_key_hits')}",
            f"- secret_like_hits: {validation_payload.get('secret_like_hits')}",
            f"- duplicate_review_item_ids: {validation_payload.get('duplicate_review_item_ids')}",
            f"- unknown_review_item_ids: {validation_payload.get('unknown_review_item_ids')}",
            f"- block_id_mismatches: {validation_payload.get('block_id_mismatches')}",
            f"- authority_field_mutation_attempts: {validation_payload.get('authority_field_mutation_attempts')}",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def build_no_mutation_proof(
    *,
    source_prd: str,
    blocks_path: Path,
    registry_path: Path,
    queue_path: Path,
    decisions_template_path: Path,
    blocks_hash_before: str,
    registry_hash_before: str,
    chroma_count_before: int | None,
    chroma_count_after: int | None,
) -> dict[str, Any]:
    blocks_hash_after = sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_hash_after = sha256_file(registry_path) if registry_path.exists() else ""
    queue_hash = sha256_file(queue_path) if queue_path.exists() else ""
    template_hash = sha256_file(decisions_template_path) if decisions_template_path.exists() else ""

    return {
        "schema_version": "post_reprocess_review_no_mutation_proof_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "all_blocks_merged_hash_before": blocks_hash_before,
        "all_blocks_merged_hash_after": blocks_hash_after,
        "registry_hash_before": registry_hash_before,
        "registry_hash_after": registry_hash_after,
        "review_queue_hash": queue_hash,
        "decisions_template_hash": template_hash,
        "chroma_count_before": chroma_count_before,
        "chroma_count_after": chroma_count_after,
        "all_blocks_merged_mutated": blocks_hash_before != blocks_hash_after,
        "registry_mutated": bool(registry_hash_before and registry_hash_after and registry_hash_before != registry_hash_after),
        "chroma_mutated": (
            chroma_count_before is not None and chroma_count_after is not None and chroma_count_before != chroma_count_after
        ),
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
        "registry_mutated_by_apply": False,
    }


def find_fresh_review_queue(default_path: Path) -> Path:
    if default_path.exists():
        return default_path
    candidates = sorted(default_path.parent.glob("review_queue*.json"))
    if not candidates:
        raise FileNotFoundError(f"review_queue_not_found:{default_path.as_posix()}")
    ranked = [
        path
        for path in candidates
        if "real_enrichment" in path.name or "after_real" in path.name
    ]
    return ranked[0] if ranked else candidates[0]


def sanitize_runtime_log_lines(lines: list[str]) -> list[str]:
    sanitized: list[str] = []
    for line in lines:
        raw = re.sub(r"\s+", " ", str(line or "").strip())
        if not raw:
            continue
        if contains_secret_like_value(raw):
            sanitized.append("[redacted_secret_like_line]")
            continue
        sanitized.append(raw)
    return sanitized
