from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .manual_review import FIELD_KIND, FIELD_ORDER, candidate_id_of
from .mechanism_metadata import adapt_block_to_mechanism_metadata
from .offline_enrichment import normalize_text, safe_preview, utc_now


PRD_ID = "PRD-047.19"
SOURCE_PRD_ID = "PRD-047.18"
APPLY_PREFLIGHT_SCHEMA_VERSION = "mechanism_metadata_apply_preflight_v1"
DRY_RUN_APPLY_PLAN_SCHEMA_VERSION = "mechanism_metadata_dry_run_apply_plan_v1"
OVERLAY_INTAKE_SCHEMA_VERSION = "mechanism_metadata_overlay_intake_report_v1"

FIELD_APPLY_MAP = {
    "summary_candidate": "summary",
    "core_thesis_candidate": "core_thesis",
    "mechanism_hints_candidates": "mechanism_hints",
    "use_when_candidates": "use_when",
    "avoid_when_candidates": "avoid_when",
    "contraindications_candidates": "contraindications",
    "safe_user_translation_candidate": "safe_user_translation",
    "risk_if_exposed_candidate": "risk_if_exposed",
    "allowed_writer_use_candidate": "allowed_writer_use",
    "recommended_moves_candidates": "recommended_moves",
    "forbidden_moves_candidates": "forbidden_moves",
    "depth_level_suggestion": "depth_level",
    "quote_policy_suggestion": "quote_policy",
    "chunk_type_review_suggestion": "chunk_type",
}
FIELD_EXPECTED_TYPE = dict(FIELD_KIND)
SEPARATOR_ONLY_PREVIEWS = {"", "***", "---", "___", "****", "----", "*****"}
EXPECTED_FIXTURE_BLOCKERS = {
    "overlay_fixture_only",
    "no_real_human_reviewed_decisions",
}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    return [normalize_text(value)] if normalize_text(value) else []


def build_processed_block_index(blocks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        normalize_text(block.get("id") or block.get("chunk_id")): block
        for block in blocks
        if normalize_text(block.get("id") or block.get("chunk_id"))
    }


def is_separator_only_preview(value: Any) -> bool:
    normalized = normalize_text(value)
    if normalized in SEPARATOR_ONLY_PREVIEWS:
        return True
    stripped = normalized.replace("*", "").replace("-", "").replace("_", "").strip()
    return normalized != "" and stripped == ""


def _future_target_current_value(*, raw_block: dict[str, Any], target_field: str) -> Any:
    metadata, _ = adapt_block_to_mechanism_metadata(raw_block)
    meta_dict = metadata.to_dict()
    extra = dict(meta_dict.get("extra_metadata") or {})
    if target_field == "summary":
        return normalize_text(raw_block.get("summary"))
    if target_field == "core_thesis":
        return normalize_text(meta_dict.get("core_thesis"))
    if target_field in {
        "mechanism_hints",
        "use_when",
        "avoid_when",
        "contraindications",
        "recommended_moves",
        "forbidden_moves",
    }:
        return list(meta_dict.get(target_field) or [])
    if target_field in {"depth_level"}:
        return meta_dict.get("depth_level")
    if target_field in {"quote_policy", "chunk_type"}:
        return meta_dict.get(target_field)
    if target_field in {"safe_user_translation", "risk_if_exposed", "allowed_writer_use"}:
        return extra.get(target_field, "")
    return None


def _value_kind_matches(field_name: str, value: Any) -> bool:
    expected = FIELD_EXPECTED_TYPE[field_name]
    if expected == "str":
        return isinstance(value, str)
    if expected == "list[str]":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if expected == "int_or_none":
        return value is None or isinstance(value, int)
    if expected == "str_or_none":
        return value is None or isinstance(value, str)
    return True


def build_overlay_intake_report(
    *,
    overlay_document: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
    processed_block_index: dict[str, dict[str, Any]],
    overlay_file: str,
) -> dict[str, Any]:
    items = list(overlay_document.get("items") or [])
    real_apply_blockers: list[str] = []
    intake_warnings: list[str] = []
    candidate_reference_count = 0
    for item in items:
        candidate_id = normalize_text(item.get("candidate_id"))
        if candidate_id in candidate_index and candidate_id in processed_block_index:
            candidate_reference_count += 1
        else:
            real_apply_blockers.append(f"missing_candidate_or_block_reference:{candidate_id}")
    if bool(overlay_document.get("fixture_only")):
        real_apply_blockers.extend(["overlay_fixture_only", "no_real_human_reviewed_decisions"])
        intake_status = "passed_fixture_only"
    else:
        intake_status = "passed_real_overlay" if not real_apply_blockers else "blocked"
    if overlay_document.get("live_apply_allowed") is not False:
        real_apply_blockers.append("overlay_live_apply_allowed_must_be_false")
    if overlay_document.get("safe_to_apply_to_live_metadata") is not False:
        real_apply_blockers.append("overlay_safe_to_apply_to_live_metadata_must_be_false")
    return {
        "schema_version": OVERLAY_INTAKE_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_overlay_prd": SOURCE_PRD_ID,
        "overlay_file": overlay_file,
        "overlay_schema_version": normalize_text(overlay_document.get("schema_version")),
        "fixture_only": bool(overlay_document.get("fixture_only")),
        "live_apply_allowed": bool(overlay_document.get("live_apply_allowed")),
        "safe_to_apply_to_live_metadata": bool(overlay_document.get("safe_to_apply_to_live_metadata")),
        "accepted_item_count": int(((overlay_document.get("summary") or {}).get("accepted_item_count")) or len(items)),
        "accepted_field_count": int(((overlay_document.get("summary") or {}).get("accepted_field_count")) or 0),
        "candidate_reference_count": candidate_reference_count,
        "intake_status": intake_status,
        "real_apply_blockers": sorted(dict.fromkeys(real_apply_blockers)),
        "warnings": sorted(dict.fromkeys(intake_warnings)),
    }


def build_field_mapping_snapshot() -> dict[str, Any]:
    return {
        "schema_version": "mechanism_metadata_field_apply_map_v1",
        "prd_id": PRD_ID,
        "field_apply_map": FIELD_APPLY_MAP,
        "field_expected_type": FIELD_EXPECTED_TYPE,
        "field_order": list(FIELD_ORDER),
        "notes": [
            "Mapping is preview-only and does not authorize live metadata mutation.",
            "Targets describe future overlay/apply semantics, not current runtime writes.",
        ],
    }


def build_dry_run_apply_plan(
    *,
    overlay_document: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
    processed_block_index: dict[str, dict[str, Any]],
    overlay_file: str,
) -> dict[str, Any]:
    items = list(overlay_document.get("items") or [])
    plan_items: list[dict[str, Any]] = []
    blocked_item_count = 0
    warning_item_count = 0
    total_field_count = 0
    fixture_only = bool(overlay_document.get("fixture_only"))

    for item in items:
        candidate_id = normalize_text(item.get("candidate_id"))
        raw_block = processed_block_index.get(candidate_id)
        candidate = candidate_index.get(candidate_id)
        accepted_fields = dict(item.get("accepted_fields") or {})
        item_blockers: list[str] = []
        item_warnings: list[str] = []
        if raw_block is None:
            item_blockers.append("processed_block_not_found")
        if candidate is None:
            item_blockers.append("candidate_not_found")

        source_preview = normalize_text(((item.get("source_ref") or {}).get("content_preview")))
        if is_separator_only_preview(source_preview):
            if fixture_only:
                item_warnings.append("separator_only_source_preview_fixture_warning")
            else:
                item_blockers.append("separator_only_source_preview_real_overlay_blocker")

        field_mapping: dict[str, str] = {}
        diff_current: dict[str, Any] = {}
        diff_proposed: dict[str, Any] = {}
        for field_name, value in accepted_fields.items():
            total_field_count += 1
            mapped_target = FIELD_APPLY_MAP.get(field_name)
            if not mapped_target:
                item_blockers.append(f"missing_field_mapping:{field_name}")
                continue
            if field_name not in FIELD_ORDER:
                item_blockers.append(f"unknown_accepted_field:{field_name}")
                continue
            if not _value_kind_matches(field_name, value):
                item_blockers.append(f"type_mismatch:{field_name}")
                continue
            field_mapping[field_name] = f"future_metadata.{mapped_target}"
            if raw_block is not None:
                diff_current[mapped_target] = _future_target_current_value(raw_block=raw_block, target_field=mapped_target)
            diff_proposed[mapped_target] = value

        if normalize_text(item.get("chunk_type")).lower() == "practice":
            if "avoid_when_candidates" not in accepted_fields:
                item_blockers.append("practice_missing_accepted_avoid_when")
            if "contraindications_candidates" not in accepted_fields:
                item_blockers.append("practice_missing_accepted_contraindications")

        if item_blockers:
            blocked_item_count += 1
        if item_warnings:
            warning_item_count += 1

        plan_items.append(
            {
                "candidate_id": candidate_id,
                "source_ref": dict(item.get("source_ref") or {}),
                "chunk_type": normalize_text(item.get("chunk_type")).lower(),
                "risk_level": normalize_text(item.get("risk_level")).lower(),
                "accepted_fields": accepted_fields,
                "field_mapping": field_mapping,
                "diff_preview": {
                    "current": diff_current,
                    "proposed": diff_proposed,
                    "operation": "overlay_only_no_write",
                },
                "item_blockers": item_blockers,
                "item_warnings": item_warnings,
            }
        )

    return {
        "schema_version": DRY_RUN_APPLY_PLAN_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_overlay_file": overlay_file,
        "created_at": utc_now(),
        "plan_mode": "fixture_preview" if fixture_only else "real_overlay_preview",
        "apply_allowed": False,
        "live_metadata_mutation_allowed": False,
        "chroma_reindex_allowed": False,
        "items": plan_items,
        "summary": {
            "item_count": len(plan_items),
            "field_count": total_field_count,
            "blocked_item_count": blocked_item_count,
            "warning_item_count": warning_item_count,
            "by_chunk_type": dict(sorted(Counter(item.get("chunk_type") for item in plan_items).items())),
        },
    }


def build_apply_preflight_report(
    *,
    intake_report: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> dict[str, Any]:
    expected_blockers = list(intake_report.get("real_apply_blockers") or [])
    unexpected_blockers: list[str] = []
    warnings: list[str] = []
    for item in list(dry_run_plan.get("items") or []):
        for blocker in item.get("item_blockers") or []:
            if blocker in EXPECTED_FIXTURE_BLOCKERS:
                expected_blockers.append(blocker)
            else:
                unexpected_blockers.append(f"{item.get('candidate_id')}:{blocker}")
        for warning in item.get("item_warnings") or []:
            warnings.append(f"{item.get('candidate_id')}:{warning}")

    expected_blockers = sorted(dict.fromkeys(expected_blockers))
    unexpected_blockers = sorted(dict.fromkeys(unexpected_blockers))
    warnings = sorted(dict.fromkeys(warnings))
    fixture_only = bool(intake_report.get("fixture_only"))
    ready_for_live_apply = False
    ready_for_chroma_reindex = False
    ready_for_runtime_visibility = False
    ready_for_eval_over_real_overlay = (not fixture_only) and not unexpected_blockers and not expected_blockers

    status = "passed"
    if fixture_only and not unexpected_blockers:
        status = "passed_with_expected_blockers"
    elif unexpected_blockers:
        status = "blocked"
    elif expected_blockers:
        status = "warning"

    return {
        "schema_version": APPLY_PREFLIGHT_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "status": status,
        "ready_for_live_apply": ready_for_live_apply,
        "ready_for_chroma_reindex": ready_for_chroma_reindex,
        "ready_for_runtime_visibility": ready_for_runtime_visibility,
        "ready_for_eval_over_real_overlay": ready_for_eval_over_real_overlay,
        "expected_blockers": expected_blockers,
        "unexpected_blockers": unexpected_blockers,
        "warnings": warnings,
        "next_safe_step": "human_curated_review_batch_1_or_eval_after_real_overlay",
    }


def render_overlay_intake_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.19 Overlay Intake Report",
        "",
        f"- intake_status: `{report['intake_status']}`",
        f"- fixture_only: `{report['fixture_only']}`",
        f"- accepted_item_count: `{report['accepted_item_count']}`",
        f"- accepted_field_count: `{report['accepted_field_count']}`",
        f"- candidate_reference_count: `{report['candidate_reference_count']}`",
        "",
        "## Real Apply Blockers",
    ]
    for item in report.get("real_apply_blockers", []) or ["none"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def render_dry_run_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.19 Dry Run Apply Plan",
        "",
        f"- plan_mode: `{plan['plan_mode']}`",
        f"- item_count: `{plan['summary']['item_count']}`",
        f"- field_count: `{plan['summary']['field_count']}`",
        f"- blocked_item_count: `{plan['summary']['blocked_item_count']}`",
        f"- warning_item_count: `{plan['summary']['warning_item_count']}`",
        "",
        "## Items",
    ]
    for item in plan.get("items", []):
        lines.append(f"- `{item['candidate_id']}` | `{item['chunk_type']}` | `{item['risk_level']}`")
        lines.append(f"  mapping: `{json.dumps(item['field_mapping'], ensure_ascii=False)}`")
        lines.append(f"  blockers: `{json.dumps(item['item_blockers'], ensure_ascii=False)}`")
        lines.append(f"  warnings: `{json.dumps(item['item_warnings'], ensure_ascii=False)}`")
    return "\n".join(lines)


def render_apply_preflight_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.19 Apply Preflight Report",
        "",
        f"- status: `{report['status']}`",
        f"- ready_for_live_apply: `{report['ready_for_live_apply']}`",
        f"- ready_for_eval_over_real_overlay: `{report['ready_for_eval_over_real_overlay']}`",
        "",
        "## Expected Blockers",
    ]
    for item in report.get("expected_blockers", []) or ["none"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Unexpected Blockers"])
    for item in report.get("unexpected_blockers", []) or ["none"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Warnings"])
    for item in report.get("warnings", []) or ["none"]:
        lines.append(f"- {item}")
    return "\n".join(lines)
