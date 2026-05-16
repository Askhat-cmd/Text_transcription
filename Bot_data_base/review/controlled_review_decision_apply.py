from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .architect_review_pass import validate_architect_decisions_overlay
from .review_sanitizer import contains_secret_like_value, find_forbidden_review_keys


ALLOWED_ADVISORY_FIELDS = {
    "summary",
    "tags",
    "lens_family_candidates",
    "use_when",
    "avoid_when",
    "self_contained_score",
    "self_contained_reason",
    "split_merge_suggestion",
    "confidence",
}

SENSITIVE_QUERY_TERMS = ["страх", "тень", "границ", "практик", "quote"]


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


def load_blocks_payload(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid_blocks_payload:{path.as_posix()}")
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        raise RuntimeError(f"invalid_blocks_payload_blocks_missing:{path.as_posix()}")
    return payload


def load_review_queue_payload(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid_review_queue_payload:{path.as_posix()}")
    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"invalid_review_queue_payload_items_missing:{path.as_posix()}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(payload: Any) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _extract_blocks(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("blocks")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _block_id(block: dict[str, Any]) -> str:
    return str(block.get("id") or block.get("chunk_id") or "").strip()


def _source_id(block: dict[str, Any]) -> str:
    meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    source_id = str(meta.get("source_id") or "").strip()
    if source_id:
        return source_id
    source = str(block.get("source") or "").strip()
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_and_compare_decisions_overlays(primary_path: Path, fallback_path: Path) -> tuple[dict[str, Any], bool]:
    primary = read_json(primary_path)
    fallback = read_json(fallback_path)
    if not isinstance(primary, dict) or not isinstance(fallback, dict):
        raise RuntimeError("decisions_overlay_payload_invalid")
    return primary, sha256_json(primary) == sha256_json(fallback)


def discover_authoritative_run1_enrichment_source(
    *, logs_root: Path, expected_source_prd: str, expected_items: int
) -> tuple[list[dict[str, Any]], list[str]]:
    candidates: list[dict[str, Any]] = []
    reasons: list[str] = []
    for overlay_path in logs_root.rglob("real_enrichment_candidate_overlay.json"):
        try:
            overlay = read_json(overlay_path)
        except Exception:
            reasons.append(f"overlay_unreadable:{overlay_path.as_posix()}")
            continue
        items = overlay.get("items") if isinstance(overlay, dict) and isinstance(overlay.get("items"), list) else []
        if len(items) != expected_items:
            reasons.append(f"overlay_items_unexpected:{overlay_path.as_posix()}:{len(items)}")
            continue
        if not all(isinstance(row, dict) and str(row.get("block_id") or "").strip() for row in items):
            reasons.append(f"overlay_block_id_missing:{overlay_path.as_posix()}")
            continue

        validation_path = overlay_path.parent / "real_enrichment_validation.json"
        if not validation_path.exists():
            reasons.append(f"validation_missing:{validation_path.as_posix()}")
            continue
        try:
            validation = read_json(validation_path)
        except Exception:
            reasons.append(f"validation_unreadable:{validation_path.as_posix()}")
            continue
        if not isinstance(validation, dict):
            reasons.append(f"validation_invalid:{validation_path.as_posix()}")
            continue
        if str(validation.get("source_prd") or "") != expected_source_prd:
            reasons.append(f"validation_source_prd_mismatch:{validation_path.as_posix()}")
            continue
        if int(validation.get("items_completed") or 0) != expected_items:
            reasons.append(f"validation_items_completed_mismatch:{validation_path.as_posix()}")
            continue
        if int(validation.get("validation_errors_count") or 0) != 0:
            reasons.append(f"validation_errors_present:{validation_path.as_posix()}")
            continue

        candidates.append(
            {
                "overlay_path": overlay_path.as_posix(),
                "validation_path": validation_path.as_posix(),
                "overlay_schema_version": str(overlay.get("schema_version") or ""),
                "overlay_source_prd": str(overlay.get("source_prd") or ""),
                "validation_source_prd": str(validation.get("source_prd") or ""),
                "items_count": len(items),
                "items_completed": int(validation.get("items_completed") or 0),
                "validation_errors_count": int(validation.get("validation_errors_count") or 0),
            }
        )
    return candidates, sorted(set(reasons))


def build_run1_enrichment_index(overlay_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = overlay_payload.get("items") if isinstance(overlay_payload.get("items"), list) else []
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        block_id = str(row.get("block_id") or "").strip()
        if not block_id:
            continue
        advisory = row.get("advisory") if isinstance(row.get("advisory"), dict) else {}
        quality = row.get("quality") if isinstance(row.get("quality"), dict) else {}
        payload: dict[str, Any] = {}
        if str(advisory.get("summary") or "").strip():
            payload["summary"] = str(advisory.get("summary") or "").strip()
        if _normalize_list(advisory.get("tags")):
            payload["tags"] = _normalize_list(advisory.get("tags"))
        if _normalize_list(advisory.get("lens_family_candidates")):
            payload["lens_family_candidates"] = _normalize_list(advisory.get("lens_family_candidates"))
        if _normalize_list(advisory.get("use_when")):
            payload["use_when"] = _normalize_list(advisory.get("use_when"))
        if _normalize_list(advisory.get("avoid_when")):
            payload["avoid_when"] = _normalize_list(advisory.get("avoid_when"))
        if quality.get("self_contained_score") is not None:
            payload["self_contained_score"] = quality.get("self_contained_score")
        if quality.get("confidence") is not None:
            payload["confidence"] = quality.get("confidence")
        if str(advisory.get("not_for_direct_quote_reason") or "").strip():
            payload["self_contained_reason"] = str(advisory.get("not_for_direct_quote_reason") or "").strip()
        index[block_id] = payload
    return index


def build_preflight_report(
    *,
    source_prd: str,
    blocks_payload: dict[str, Any],
    queue_payload: dict[str, Any],
    decisions_payload: dict[str, Any],
    overlays_equal: bool,
    run1_candidates: list[dict[str, Any]],
    run1_discovery_warnings: list[str],
    expected_blocks_total: int,
    expected_review_items: int,
    expected_decisions_count: int,
    expected_queue_source_prd: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings = list(run1_discovery_warnings)

    blocks = _extract_blocks(blocks_payload)
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload.get("decisions"), list) else []

    block_ids = {_block_id(block) for block in blocks if _block_id(block)}
    queue_block_ids = {
        str(item.get("block_id") or "").strip() for item in queue_items if isinstance(item, dict) and str(item.get("block_id") or "").strip()
    }
    missing_queue_block_ids = sorted(queue_block_ids.difference(block_ids))

    if len(blocks) != expected_blocks_total:
        blockers.append("blocks_total_mismatch")
    if len(queue_items) != expected_review_items:
        blockers.append("queue_items_count_mismatch")
    if len(decisions) != expected_decisions_count:
        blockers.append("decisions_count_mismatch")
    if str(queue_payload.get("source_prd") or "") != expected_queue_source_prd:
        blockers.append("review_queue_source_prd_mismatch")
    if not overlays_equal:
        blockers.append("overlay_primary_fallback_mismatch")
    if missing_queue_block_ids:
        blockers.append("queue_block_ids_missing")

    validation = validate_architect_decisions_overlay(
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        blocks_payload=blocks_payload,
        source_prd=str(decisions_payload.get("source_prd") or ""),
    )
    if not bool(validation.get("valid")):
        blockers.append("overlay_validation_invalid")
    if not bool(validation.get("apply_ready")):
        blockers.append("overlay_apply_ready_false")
    coverage = validation.get("coverage") if isinstance(validation.get("coverage"), dict) else {}
    if float(coverage.get("coverage_percent") or 0.0) < 100.0:
        blockers.append("overlay_coverage_not_full")
    if int(coverage.get("remaining_items_count") or 0) != 0:
        blockers.append("overlay_remaining_items_present")

    for key in (
        "forbidden_key_hits",
        "secret_like_hits",
        "duplicate_review_item_ids",
        "unknown_review_item_ids",
        "block_id_mismatches",
        "authority_field_mutation_attempts",
        "invalid_decision_values",
    ):
        if validation.get(key):
            blockers.append(f"overlay_{key}_not_empty")

    if len(run1_candidates) != 1:
        blockers.append("authoritative_run1_enrichment_not_unique")

    return {
        "schema_version": "controlled_review_decision_apply_preflight_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "preflight_passed": len(blockers) == 0,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "blocks_total": len(blocks),
        "queue_items_count": len(queue_items),
        "decisions_count": len(decisions),
        "overlay_primary_fallback_equal": overlays_equal,
        "queue_block_ids_present": len(queue_block_ids.intersection(block_ids)),
        "queue_block_ids_missing": len(missing_queue_block_ids),
        "overlay_validation": validation,
        "run1_authoritative_candidates": run1_candidates,
    }


def _filter_allowed_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items() if str(key) in ALLOWED_ADVISORY_FIELDS}


def build_apply_plan(
    *,
    source_prd: str,
    blocks_payload: dict[str, Any],
    queue_payload: dict[str, Any],
    decisions_payload: dict[str, Any],
    run1_index: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blocks = _extract_blocks(blocks_payload)
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload.get("decisions"), list) else []

    queue_by_block_id = {
        str(item.get("block_id") or "").strip(): item
        for item in queue_items
        if isinstance(item, dict) and str(item.get("block_id") or "").strip()
    }
    decision_by_review_item_id: dict[str, dict[str, Any]] = {}
    dup_ids: list[str] = []
    for item in decisions:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("review_item_id") or "").strip()
        if not rid:
            continue
        if rid in decision_by_review_item_id:
            dup_ids.append(rid)
            continue
        decision_by_review_item_id[rid] = item

    counters = Counter()
    plan_warnings: list[str] = []
    actions: list[dict[str, Any]] = []

    for block in blocks:
        block_id = _block_id(block)
        if not block_id:
            continue
        run1_payload = _filter_allowed_fields(run1_index.get(block_id) or {})
        queue_item = queue_by_block_id.get(block_id)
        if queue_item:
            counters["review_items_total"] += 1
            rid = str(queue_item.get("review_item_id") or "").strip()
            decision = decision_by_review_item_id.get(rid)
            if not decision:
                counters["review_missing_decision"] += 1
                plan_warnings.append(f"missing_decision:{rid}")
                continue
            decision_value = str(decision.get("decision") or "").strip()
            if decision_value == "approved":
                counters["review_approved_apply_candidates"] += 1
                approved_fields = [x for x in _normalize_list(decision.get("approved_fields")) if x in ALLOWED_ADVISORY_FIELDS]
                payload = {field: run1_payload[field] for field in approved_fields if field in run1_payload}
                if payload:
                    actions.append(
                        {"block_id": block_id, "route": "review_approved_apply", "decision": decision_value, "fields": sorted(payload.keys()), "payload": payload}
                    )
                else:
                    counters["review_approved_no_payload_skip"] += 1
            elif decision_value == "needs_edit":
                counters["review_needs_edit_apply_candidates"] += 1
                edited_fields = decision.get("edited_fields") if isinstance(decision.get("edited_fields"), dict) else {}
                payload = _filter_allowed_fields(edited_fields)
                if payload:
                    actions.append(
                        {"block_id": block_id, "route": "review_needs_edit_apply", "decision": decision_value, "fields": sorted(payload.keys()), "payload": payload}
                    )
                else:
                    counters["review_needs_edit_no_payload_skip"] += 1
            elif decision_value == "rejected":
                counters["review_rejected_skip"] += 1
            elif decision_value == "defer":
                counters["review_defer_skip"] += 1
            else:
                counters["review_unknown_decision_skip"] += 1
                plan_warnings.append(f"unknown_decision:{rid}:{decision_value}")
        else:
            counters["safe_non_review_total"] += 1
            if run1_payload:
                counters["safe_non_review_apply_candidates"] += 1
                actions.append(
                    {"block_id": block_id, "route": "safe_non_review_apply", "decision": "safe_non_review", "fields": sorted(run1_payload.keys()), "payload": run1_payload}
                )
            else:
                counters["safe_non_review_no_payload_skip"] += 1

    total_blocks = len(blocks)
    review_items_count = counters["review_items_total"]
    expected_safe_non_review = max(0, total_blocks - review_items_count)
    plan = {
        "schema_version": "controlled_review_decision_apply_plan_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "total_blocks": total_blocks,
        "review_items_count": review_items_count,
        "safe_non_review_apply_candidates": counters["safe_non_review_apply_candidates"],
        "review_approved_apply_candidates": counters["review_approved_apply_candidates"],
        "review_needs_edit_apply_candidates": counters["review_needs_edit_apply_candidates"],
        "review_rejected_skip": counters["review_rejected_skip"],
        "review_defer_skip": counters["review_defer_skip"],
        "max_expected_apply_candidates": expected_safe_non_review + counters["review_approved_apply_candidates"] + counters["review_needs_edit_apply_candidates"],
        "actual_apply_candidates": len(actions),
        "authority_mutation_planned": False,
        "text_mutation_planned": False,
        "governance_mutation_planned": False,
        "expected_safe_non_review_candidates": expected_safe_non_review,
        "duplicate_decision_ids": sorted(set(dup_ids)),
        "plan_warnings": sorted(set(plan_warnings)),
        "counters": dict(sorted(counters.items())),
    }
    return plan, actions


def validate_apply_plan(*, plan: dict[str, Any], actions: list[dict[str, Any]], expected_total_blocks: int, expected_review_items: int, expected_decisions_count: int) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if int(plan.get("total_blocks") or 0) != expected_total_blocks:
        errors.append("total_blocks_mismatch")
    if int(plan.get("review_items_count") or 0) != expected_review_items:
        errors.append("review_items_count_mismatch")
    if plan.get("authority_mutation_planned") or plan.get("text_mutation_planned") or plan.get("governance_mutation_planned"):
        errors.append("unallowed_mutation_planned")
    if plan.get("duplicate_decision_ids"):
        errors.append("duplicate_decision_ids_present")

    route_counts = Counter(str(action.get("route") or "") for action in actions)
    if route_counts.get("review_rejected_apply", 0) > 0:
        errors.append("rejected_items_planned_for_apply")
    if route_counts.get("review_defer_apply", 0) > 0:
        errors.append("defer_items_planned_for_apply")

    forbidden_hits: list[str] = []
    secret_hits: list[str] = []
    authority_hits: list[str] = []
    for idx, action in enumerate(actions):
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        for key in payload.keys():
            if str(key) not in ALLOWED_ADVISORY_FIELDS:
                authority_hits.append(f"actions[{idx}]::{key}")
        if find_forbidden_review_keys(payload):
            forbidden_hits.append(f"actions[{idx}]")
        for key, value in payload.items():
            if isinstance(value, str) and contains_secret_like_value(value):
                secret_hits.append(f"actions[{idx}].{key}")

    if authority_hits:
        errors.append("authority_field_in_action_payload")
    if forbidden_hits:
        errors.append("forbidden_keys_in_action_payload")
    if secret_hits:
        errors.append("secret_like_values_in_action_payload")
    if int(plan.get("review_approved_apply_candidates") or 0) + int(plan.get("review_needs_edit_apply_candidates") or 0) > expected_decisions_count:
        errors.append("review_apply_candidates_exceed_decisions")
    if int(plan.get("actual_apply_candidates") or 0) > int(plan.get("max_expected_apply_candidates") or 0):
        errors.append("actual_apply_candidates_exceed_max_expected")
    if int(plan.get("safe_non_review_apply_candidates") or 0) > int(plan.get("expected_safe_non_review_candidates") or 0):
        errors.append("safe_non_review_apply_candidates_exceed_expected")
    for warning in plan.get("plan_warnings") or []:
        warnings.append(f"plan_warning:{warning}")
    return {
        "schema_version": "controlled_review_decision_apply_plan_validation_v1",
        "validated_at": utc_now_iso(),
        "valid": len(errors) == 0,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "forbidden_key_hits": sorted(set(forbidden_hits)),
        "secret_like_hits": sorted(set(secret_hits)),
        "authority_field_hits": sorted(set(authority_hits)),
        "route_counts": dict(sorted(route_counts.items())),
    }


def _authority_snapshot(block: dict[str, Any]) -> dict[str, Any]:
    meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    gov = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
    return {
        "text": str(block.get("text") or ""),
        "chunk_type": str(gov.get("chunk_type") or ""),
        "allowed_use": list(gov.get("allowed_use") or []),
        "safety_flags": list(gov.get("safety_flags") or []),
        "source_id": str(meta.get("source_id") or _source_id(block)),
        "block_id": _block_id(block),
        "governance": copy.deepcopy(gov),
    }


def apply_actions_to_blocks(*, blocks_payload: dict[str, Any], actions: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    blocks = _extract_blocks(blocks_payload)
    idx = {_block_id(block): i for i, block in enumerate(blocks) if _block_id(block)}
    before = {block_id: _authority_snapshot(blocks[position]) for block_id, position in idx.items()}
    out_blocks = copy.deepcopy(blocks)
    applied = Counter()
    changed_block_ids: set[str] = set()

    for action in actions:
        block_id = str(action.get("block_id") or "").strip()
        position = idx.get(block_id)
        if position is None:
            continue
        block = out_blocks[position]
        if not isinstance(block.get("metadata"), dict):
            block["metadata"] = {}
        metadata = block["metadata"]
        current = metadata.get("llm_enrichment") if isinstance(metadata.get("llm_enrichment"), dict) else {}
        nxt = dict(current)
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        for key, value in payload.items():
            nxt[str(key)] = value
        if nxt != current:
            metadata["llm_enrichment"] = nxt
            changed_block_ids.add(block_id)
            applied[str(action.get("route") or "unknown")] += 1

    after = {block_id: _authority_snapshot(out_blocks[position]) for block_id, position in idx.items()}
    summary = {
        "updated_blocks": len(changed_block_ids),
        "changed_block_ids_sample": sorted(changed_block_ids)[:30],
        "applied_route_counts": dict(sorted(applied.items())),
        "text_changed_count": sum(1 for key in before if before[key]["text"] != after.get(key, {}).get("text")),
        "chunk_type_changed_count": sum(1 for key in before if before[key]["chunk_type"] != after.get(key, {}).get("chunk_type")),
        "allowed_use_changed_count": sum(1 for key in before if before[key]["allowed_use"] != after.get(key, {}).get("allowed_use")),
        "safety_flags_changed_count": sum(1 for key in before if before[key]["safety_flags"] != after.get(key, {}).get("safety_flags")),
        "source_id_changed_count": sum(1 for key in before if before[key]["source_id"] != after.get(key, {}).get("source_id")),
        "block_id_changed_count": sum(1 for key in before if before[key]["block_id"] != after.get(key, {}).get("block_id")),
        "governance_invariant_violations": sum(1 for key in before if before[key]["governance"] != after.get(key, {}).get("governance")),
    }
    result = copy.deepcopy(blocks_payload)
    if isinstance(result, dict):
        result["blocks"] = out_blocks
    else:
        result = {"blocks": out_blocks}
    return result, summary


def build_no_authority_mutation_proof(*, source_prd: str, blocks_hash_before: str, blocks_hash_after: str, registry_hash_before: str, registry_hash_after: str, apply_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "controlled_review_decision_no_authority_mutation_proof_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "all_blocks_merged_hash_before": blocks_hash_before,
        "all_blocks_merged_hash_after": blocks_hash_after,
        "registry_hash_before": registry_hash_before,
        "registry_hash_after": registry_hash_after,
        "text_changed_count": int(apply_summary.get("text_changed_count") or 0),
        "chunk_type_changed_count": int(apply_summary.get("chunk_type_changed_count") or 0),
        "allowed_use_changed_count": int(apply_summary.get("allowed_use_changed_count") or 0),
        "safety_flags_changed_count": int(apply_summary.get("safety_flags_changed_count") or 0),
        "source_id_changed_count": int(apply_summary.get("source_id_changed_count") or 0),
        "block_id_changed_count": int(apply_summary.get("block_id_changed_count") or 0),
        "governance_invariant_violations": int(apply_summary.get("governance_invariant_violations") or 0),
        "authority_mutation_detected": any(
            int(apply_summary.get(key) or 0) > 0
            for key in (
                "chunk_type_changed_count",
                "allowed_use_changed_count",
                "safety_flags_changed_count",
                "source_id_changed_count",
                "block_id_changed_count",
                "governance_invariant_violations",
            )
        ),
        "production_apply_performed": True,
        "chroma_reindex_performed": False,
    }


def build_chroma_refresh_report(*, source_prd: str, chroma_count_before: int | None, chroma_count_after: int | None, reindex_performed: bool) -> dict[str, Any]:
    return {
        "schema_version": "controlled_review_decision_chroma_refresh_report_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "reindex_performed": reindex_performed,
        "chroma_count_before": chroma_count_before,
        "chroma_count_after": chroma_count_after,
        "count_unchanged": chroma_count_before == chroma_count_after,
        "rationale": "No Chroma reindex performed: apply changed advisory metadata only, without text/id/governance changes.",
    }


def build_retrieval_smoke_report(*, source_prd: str, blocks_payload: dict[str, Any], queue_payload: dict[str, Any], decisions_payload: dict[str, Any], expected_source_id: str) -> dict[str, Any]:
    blocks = _extract_blocks(blocks_payload)
    source_ids = sorted({_source_id(block) for block in blocks if _source_id(block)})
    queue_items = queue_payload.get("items") if isinstance(queue_payload.get("items"), list) else []
    queue_by_block_id = {str(item.get("block_id") or "").strip(): item for item in queue_items if isinstance(item, dict)}
    decisions = decisions_payload.get("decisions") if isinstance(decisions_payload.get("decisions"), list) else []
    decisions_by_rid = {
        str(item.get("review_item_id") or "").strip(): item
        for item in decisions
        if isinstance(item, dict) and str(item.get("review_item_id") or "").strip()
    }

    quote_violation_ids: list[str] = []
    practice_guardrail_missing_ids: list[str] = []
    forbidden_key_hits: list[str] = []
    secret_like_hits: list[str] = []
    internal_only_unsafe_exposure_count = 0
    query_results: dict[str, dict[str, Any]] = {}

    for term in SENSITIVE_QUERY_TERMS:
        hits = []
        for block in blocks:
            text = str(block.get("text") or "")
            if term.lower() in text.lower():
                hits.append(_block_id(block))
            if len(hits) >= 20:
                break
        query_results[term] = {"hits_count": len(hits), "block_ids_sample": [item for item in hits[:10] if item]}

    for block in blocks:
        block_id = _block_id(block)
        meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        gov = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
        llm = meta.get("llm_enrichment") if isinstance(meta.get("llm_enrichment"), dict) else {}
        if llm:
            for hit in find_forbidden_review_keys(llm):
                forbidden_key_hits.append(f"{block_id}:{hit}")
            for key, value in llm.items():
                if isinstance(value, str) and contains_secret_like_value(value):
                    secret_like_hits.append(f"{block_id}:{key}")

        allowed_use = [str(item).strip().lower() for item in (gov.get("allowed_use") or []) if str(item).strip()]
        if "internal_only" in allowed_use and isinstance(llm.get("summary"), str):
            if re.search(r"(ты должен|обязан|немедленно)", llm.get("summary").lower()):
                internal_only_unsafe_exposure_count += 1

        queue_item = queue_by_block_id.get(block_id)
        if not queue_item:
            continue
        rid = str(queue_item.get("review_item_id") or "").strip()
        decision = decisions_by_rid.get(rid) or {}
        decision_value = str(decision.get("decision") or "").strip()
        chunk_type = str(queue_item.get("chunk_type") or gov.get("chunk_type") or "").strip().lower()

        if chunk_type == "quote" and decision_value in {"rejected", "defer"} and llm:
            quote_violation_ids.append(block_id)
        if chunk_type == "practice" and decision_value in {"approved", "needs_edit"}:
            avoid_when = _normalize_list(llm.get("avoid_when"))
            joined = " ".join(avoid_when).lower()
            if not any(marker in joined for marker in ("дистресс", "паник", "суиц", "психоз", "специалист")):
                practice_guardrail_missing_ids.append(block_id)

    retrieval_smoke_passed = (
        source_ids == [expected_source_id]
        and not forbidden_key_hits
        and not secret_like_hits
        and not quote_violation_ids
        and not practice_guardrail_missing_ids
        and internal_only_unsafe_exposure_count == 0
    )
    return {
        "schema_version": "controlled_review_decision_retrieval_smoke_v1",
        "source_prd": source_prd,
        "generated_at": utc_now_iso(),
        "source_ids": source_ids,
        "query_results": query_results,
        "quote_violation_ids": sorted(set(quote_violation_ids)),
        "practice_guardrail_missing_ids": sorted(set(practice_guardrail_missing_ids)),
        "internal_only_unsafe_exposure_count": internal_only_unsafe_exposure_count,
        "forbidden_key_hits": sorted(set(forbidden_key_hits)),
        "secret_like_hits": sorted(set(secret_like_hits)),
        "retrieval_smoke_passed": retrieval_smoke_passed,
    }


def _http_json(url: str, timeout: float = 6.0) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw else None
            return {"ok": True, "status_code": int(resp.status), "body": body, "error": None}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def build_admin_consistency_report(
    *,
    blocks_payload: dict[str, Any],
    registry_payload: Any,
    expected_source_id: str,
    chroma_count_after: int | None,
    api_base_url: str,
    expected_blocks_total: int = 247,
) -> dict[str, Any]:
    blocks = _extract_blocks(blocks_payload)
    records = registry_payload if isinstance(registry_payload, list) else []
    focus_rows = [
        row
        for row in records
        if isinstance(row, dict)
        and str(row.get("source_id") or "").strip() == expected_source_id
        and str(row.get("status") or "").strip() == "done"
    ]
    registry_focus_blocks = int((focus_rows[0].get("blocks_count") if focus_rows else 0) or 0)
    base = api_base_url.rstrip("/")
    api_checks = {
        "/api/status": _http_json(f"{base}/api/status"),
        "/api/registry": _http_json(f"{base}/api/registry"),
        "/api/dashboard": _http_json(f"{base}/api/dashboard"),
        "/api/dashboard/": _http_json(f"{base}/api/dashboard/"),
    }
    return {
        "schema_version": "controlled_review_decision_admin_consistency_v1",
        "generated_at": utc_now_iso(),
        "blocks_total": len(blocks),
        "registry_focus_blocks": registry_focus_blocks,
        "chroma_count_after": chroma_count_after,
        "api_checks": api_checks,
        "admin_consistency_passed": (
            len(blocks) == expected_blocks_total
            and registry_focus_blocks == expected_blocks_total
            and (chroma_count_after is None or int(chroma_count_after) == expected_blocks_total)
        ),
    }


def build_runtime_log_lines(values: dict[str, Any]) -> list[str]:
    lines = []
    for key, value in values.items():
        line = re.sub(r"\s+", " ", f"{key}={value}".strip())
        if not line:
            continue
        lines.append("[redacted_secret_like_line]" if contains_secret_like_value(line) else line)
    return lines


def render_markdown_report(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines]).rstrip() + "\n"
