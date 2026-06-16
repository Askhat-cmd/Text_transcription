from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .mechanism_metadata import CONTROLLED_CHUNK_TYPES, CONTROLLED_QUOTE_POLICY
from .offline_enrichment import dedupe, normalize_text, safe_preview, utc_now


PRD_ID = "PRD-047.18"
SOURCE_PRD_ID = "PRD-047.17"
REVIEW_DECISION_SCHEMA_VERSION = "mechanism_metadata_review_decision_v1"
CURATED_OVERLAY_SCHEMA_VERSION = "mechanism_metadata_curated_overlay_preview_v1"
REVIEW_QUEUE_SCHEMA_VERSION = "mechanism_metadata_review_queue_v1"

ALLOWED_REVIEW_STATUS = {
    "pending",
    "accepted",
    "accepted_with_edits",
    "rejected",
    "needs_source_context",
    "deferred",
    "blocked",
}
ALLOWED_FIELD_DECISIONS = {
    "pending",
    "accept",
    "accept_with_edit",
    "reject",
    "defer",
    "needs_source_context",
}
RISK_LEVEL_ORDER = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
FIELD_ORDER = (
    "summary_candidate",
    "core_thesis_candidate",
    "mechanism_hints_candidates",
    "use_when_candidates",
    "avoid_when_candidates",
    "contraindications_candidates",
    "safe_user_translation_candidate",
    "risk_if_exposed_candidate",
    "allowed_writer_use_candidate",
    "recommended_moves_candidates",
    "forbidden_moves_candidates",
    "depth_level_suggestion",
    "quote_policy_suggestion",
    "chunk_type_review_suggestion",
)
FIELD_KIND = {
    "summary_candidate": "str",
    "core_thesis_candidate": "str",
    "mechanism_hints_candidates": "list[str]",
    "use_when_candidates": "list[str]",
    "avoid_when_candidates": "list[str]",
    "contraindications_candidates": "list[str]",
    "safe_user_translation_candidate": "str",
    "risk_if_exposed_candidate": "str",
    "allowed_writer_use_candidate": "str",
    "recommended_moves_candidates": "list[str]",
    "forbidden_moves_candidates": "list[str]",
    "depth_level_suggestion": "int_or_none",
    "quote_policy_suggestion": "str_or_none",
    "chunk_type_review_suggestion": "str_or_none",
}
FORBIDDEN_KEYS = {
    "raw_provider_payload",
    "provider_payload",
    "content_full",
    "raw_full_source_text",
    "full_source_text",
}


def candidate_id_of(candidate: dict[str, Any]) -> str:
    return normalize_text(((candidate.get("source_ref") or {}).get("block_id")))


def candidate_chunk_type(candidate: dict[str, Any]) -> str:
    return normalize_text(((candidate.get("current_metadata_summary") or {}).get("chunk_type"))).lower() or "unknown"


def candidate_risk_level(candidate: dict[str, Any]) -> str:
    return normalize_text(((candidate.get("governance_review") or {}).get("risk_level"))).lower() or "unknown"


def build_candidate_index(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {candidate_id_of(candidate): candidate for candidate in candidates if candidate_id_of(candidate)}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    return [normalize_text(value)] if normalize_text(value) else []


def _empty_template_value(field_name: str) -> Any:
    kind = FIELD_KIND[field_name]
    if kind == "list[str]":
        return []
    return ""


def _decision_value_preview(value: Any) -> Any:
    if isinstance(value, list):
        return [safe_preview(item, limit=140) for item in _string_list(value)][:4]
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return safe_preview(value, limit=180)


def _field_template(field_name: str, candidate_value: Any) -> dict[str, Any]:
    return {
        "decision": "pending",
        "value": _empty_template_value(field_name),
        "reason": "",
        "candidate_value_preview": _decision_value_preview(candidate_value),
    }


def build_review_decision_template(candidate: dict[str, Any]) -> dict[str, Any]:
    source_ref = dict(candidate.get("source_ref") or {})
    candidate_fields = dict(candidate.get("candidate_fields") or {})
    return {
        "schema_version": REVIEW_DECISION_SCHEMA_VERSION,
        "candidate_id": candidate_id_of(candidate),
        "source_ref": {
            "source_id": normalize_text(source_ref.get("source_id")),
            "source_doc": normalize_text(source_ref.get("source_doc")),
            "block_id": normalize_text(source_ref.get("block_id")),
            "heading_path": list(source_ref.get("heading_path") or []),
            "content_preview": safe_preview(source_ref.get("content_preview"), limit=300),
        },
        "review_status": "pending",
        "reviewer_role": "human_required",
        "reviewer_id": "",
        "reviewed_at": "",
        "safe_to_apply_to_live_metadata": False,
        "review_notes": "",
        "field_decisions": {
            field_name: _field_template(field_name, candidate_fields.get(field_name))
            for field_name in FIELD_ORDER
        },
    }


def build_review_decisions_template(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [build_review_decision_template(candidate) for candidate in candidates]
    return {
        "schema_version": REVIEW_DECISION_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "created_at": utc_now(),
        "decision_count": len(decisions),
        "accepted_field_count": 0,
        "fixture_only": False,
        "decisions": decisions,
    }


def _recommended_reviewer_action(candidate: dict[str, Any], review_reasons: list[str]) -> str:
    chunk_type = candidate_chunk_type(candidate)
    risk_level = candidate_risk_level(candidate)
    if chunk_type == "practice" and risk_level == "high":
        return "Проверить timing fit, contraindications, avoid_when и оставить practice deferred без явного основания."
    if chunk_type == "practice":
        return "Проверить, что practice не попадет в Writer без явного запроса, ресурса и ограничений."
    if chunk_type == "diagnostic_lens":
        return "Проверить безопасный пользовательский перевод и убрать диагнозоподобную формулировку."
    if chunk_type == "mechanism":
        return "Проверить, что mechanism_hints не generic и не превращаются в routing authority."
    if chunk_type == "source_fragment":
        return "Решить, нужен ли derived candidate вместо прямого writer-facing использования."
    if "missing_mechanism_hints" in review_reasons:
        return "Решить, нужны ли конкретные mechanism hints или кандидат лучше оставить концептуальным."
    return "Подтвердить low-risk смысл, сократить шум и оставить только полезные preview-only accepted fields."


def _queue_priority(candidate: dict[str, Any], review_reasons: list[str]) -> tuple[int, str]:
    chunk_type = candidate_chunk_type(candidate)
    risk_level = candidate_risk_level(candidate)
    reasons = set(review_reasons)
    if chunk_type == "practice" and risk_level == "high":
        return 1, "P1_high_risk_practice"
    if chunk_type == "practice" and (
        "practice_missing_contraindications" in reasons
        or "practice_current_metadata_missing_contraindications" in reasons
    ):
        return 2, "P2_practice_missing_contraindications"
    if chunk_type == "diagnostic_lens":
        return 3, "P3_diagnostic_lens_safe_translation"
    if chunk_type == "mechanism" and (
        "missing_mechanism_hints" in reasons
        or not _string_list(((candidate.get("candidate_fields") or {}).get("mechanism_hints_candidates")))
    ):
        return 4, "P4_mechanism_missing_hints"
    if chunk_type == "source_fragment":
        return 5, "P5_source_fragment_derived_review"
    return 6, "P6_low_risk_concept_style_case"


def build_review_queue(
    *,
    candidate_run: dict[str, Any],
    manual_review_pack: dict[str, Any],
) -> dict[str, Any]:
    candidates = list(candidate_run.get("candidates") or [])
    candidate_index = build_candidate_index(candidates)
    queue_items: list[dict[str, Any]] = []
    for pack_entry in list(manual_review_pack.get("entries") or []):
        source_ref = dict(pack_entry.get("source_ref") or {})
        candidate_id = normalize_text(source_ref.get("block_id"))
        candidate = candidate_index.get(candidate_id)
        if not candidate:
            continue
        review_reasons = [normalize_text(item) for item in pack_entry.get("manual_review_reasons") or [] if normalize_text(item)]
        priority_value, priority_label = _queue_priority(candidate, review_reasons)
        candidate_fields = dict(candidate.get("candidate_fields") or {})
        queue_items.append(
            {
                "candidate_id": candidate_id,
                "queue_priority": priority_label,
                "queue_priority_rank": priority_value,
                "chunk_type": candidate_chunk_type(candidate),
                "risk_level": candidate_risk_level(candidate),
                "heading_path": list(source_ref.get("heading_path") or []),
                "content_preview": safe_preview(source_ref.get("content_preview"), limit=300),
                "candidate_fields_preview": {
                    "summary_candidate": _decision_value_preview(candidate_fields.get("summary_candidate")),
                    "mechanism_hints_candidates": _decision_value_preview(candidate_fields.get("mechanism_hints_candidates")),
                    "safe_user_translation_candidate": _decision_value_preview(candidate_fields.get("safe_user_translation_candidate")),
                    "allowed_writer_use_candidate": _decision_value_preview(candidate_fields.get("allowed_writer_use_candidate")),
                    "contraindications_candidates": _decision_value_preview(candidate_fields.get("contraindications_candidates")),
                },
                "manual_review_reasons": review_reasons,
                "validation_warnings": [normalize_text(item) for item in pack_entry.get("validation_warnings") or [] if normalize_text(item)],
                "recommended_reviewer_action": _recommended_reviewer_action(candidate, review_reasons),
            }
        )
    queue_items.sort(
        key=lambda item: (
            int(item["queue_priority_rank"]),
            RISK_LEVEL_ORDER.get(str(item["risk_level"]), 9),
            " / ".join(item["heading_path"]),
            item["candidate_id"],
        )
    )
    return {
        "schema_version": REVIEW_QUEUE_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "created_at": utc_now(),
        "candidate_count": len(candidates),
        "queue_count": len(queue_items),
        "by_priority": dict(sorted(Counter(item["queue_priority"] for item in queue_items).items())),
        "by_chunk_type": dict(sorted(Counter(item["chunk_type"] for item in queue_items).items())),
        "by_risk_level": dict(sorted(Counter(item["risk_level"] for item in queue_items).items())),
        "items": queue_items,
    }


def _contains_forbidden_keys(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            next_path = f"{path}.{key}" if path else str(key)
            if str(key) in FORBIDDEN_KEYS:
                hits.append(next_path)
            hits.extend(_contains_forbidden_keys(inner, next_path))
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            hits.extend(_contains_forbidden_keys(inner, f"{path}[{index}]"))
    return hits


def _is_empty_accepted_value(field_name: str, value: Any) -> bool:
    if FIELD_KIND[field_name] == "list[str]":
        return len(_string_list(value)) == 0
    if FIELD_KIND[field_name] == "int_or_none":
        return value is None or str(value).strip() == ""
    if FIELD_KIND[field_name] == "str_or_none":
        return value is None or normalize_text(value) == ""
    return normalize_text(value) == ""


def _is_valid_kind(field_name: str, value: Any) -> bool:
    kind = FIELD_KIND[field_name]
    if kind == "str":
        return isinstance(value, str)
    if kind == "list[str]":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if kind == "int_or_none":
        return value is None or isinstance(value, int)
    if kind == "str_or_none":
        return value is None or isinstance(value, str)
    return True


def _reviewer_is_claimed_human(decision: dict[str, Any]) -> bool:
    return normalize_text(decision.get("reviewer_role")).lower() not in {"", "human_required", "fixture_only"}


def _accepted_field_names(decision: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for field_name, payload in dict(decision.get("field_decisions") or {}).items():
        if normalize_text((payload or {}).get("decision")).lower() in {"accept", "accept_with_edit"}:
            result.append(field_name)
    return result


def validate_review_decisions(
    decision_document: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    decision_reports: list[dict[str, Any]] = []
    accepted_item_count = 0
    accepted_field_count = 0

    if decision_document.get("schema_version") != REVIEW_DECISION_SCHEMA_VERSION:
        errors.append("invalid_document_schema_version")

    decisions = list(decision_document.get("decisions") or [])
    if not isinstance(decisions, list):
        errors.append("decisions_must_be_list")
        decisions = []

    for index, decision in enumerate(decisions):
        decision_errors: list[str] = []
        candidate_id = normalize_text(decision.get("candidate_id"))
        candidate = candidate_index.get(candidate_id)
        if decision.get("schema_version") != REVIEW_DECISION_SCHEMA_VERSION:
            decision_errors.append("invalid_schema_version")
        if not candidate_id:
            decision_errors.append("missing_candidate_id")
        elif candidate is None:
            decision_errors.append("candidate_id_not_found")

        review_status = normalize_text(decision.get("review_status")).lower()
        if review_status not in ALLOWED_REVIEW_STATUS:
            decision_errors.append("invalid_review_status")
        if decision.get("safe_to_apply_to_live_metadata") is not False:
            decision_errors.append("safe_to_apply_to_live_metadata_must_be_false")
        if _reviewer_is_claimed_human(decision) and (
            not normalize_text(decision.get("reviewer_id")) or not normalize_text(decision.get("reviewed_at"))
        ):
            decision_errors.append("human_review_claim_requires_reviewer_id_and_reviewed_at")

        forbidden_hits = _contains_forbidden_keys(decision)
        if forbidden_hits:
            decision_errors.append("forbidden_keys_present")

        field_decisions = dict(decision.get("field_decisions") or {})
        if set(field_decisions) != set(FIELD_ORDER):
            missing = [field for field in FIELD_ORDER if field not in field_decisions]
            extra = [field for field in field_decisions if field not in FIELD_ORDER]
            if missing:
                decision_errors.append(f"missing_field_decisions:{','.join(missing)}")
            if extra:
                decision_errors.append(f"unknown_field_decisions:{','.join(extra)}")

        local_accepted_fields: list[str] = []
        for field_name in FIELD_ORDER:
            payload = dict(field_decisions.get(field_name) or {})
            field_decision = normalize_text(payload.get("decision")).lower()
            if field_decision not in ALLOWED_FIELD_DECISIONS:
                decision_errors.append(f"{field_name}:invalid_field_decision")
                continue
            if field_decision in {"accept", "accept_with_edit"}:
                value = payload.get("value")
                if _is_empty_accepted_value(field_name, value):
                    decision_errors.append(f"{field_name}:accepted_value_empty")
                    continue
                if not _is_valid_kind(field_name, value):
                    decision_errors.append(f"{field_name}:type_mismatch")
                    continue
                if field_name == "depth_level_suggestion" and value not in {0, 1, 2, 3}:
                    decision_errors.append("depth_level_suggestion_out_of_range")
                if field_name == "quote_policy_suggestion" and value not in CONTROLLED_QUOTE_POLICY:
                    decision_errors.append("quote_policy_suggestion_out_of_vocab")
                if field_name == "chunk_type_review_suggestion" and value not in CONTROLLED_CHUNK_TYPES:
                    decision_errors.append("chunk_type_review_suggestion_out_of_vocab")
                if field_name == "summary_candidate" and len(normalize_text(value)) > 300:
                    decision_errors.append("summary_candidate_too_long")
                local_accepted_fields.append(field_name)

        if candidate is not None:
            chunk_type = candidate_chunk_type(candidate)
            risk_level = candidate_risk_level(candidate)
            if chunk_type == "practice" and review_status in {"accepted", "accepted_with_edits"}:
                contra_payload = dict(field_decisions.get("contraindications_candidates") or {})
                avoid_payload = dict(field_decisions.get("avoid_when_candidates") or {})
                if normalize_text(contra_payload.get("decision")).lower() not in {"accept", "accept_with_edit"}:
                    decision_errors.append("accepted_practice_requires_contraindications_decision")
                elif _is_empty_accepted_value("contraindications_candidates", contra_payload.get("value")):
                    decision_errors.append("accepted_practice_contraindications_empty")
                if normalize_text(avoid_payload.get("decision")).lower() not in {"accept", "accept_with_edit"}:
                    decision_errors.append("accepted_practice_requires_avoid_when_decision")
                elif _is_empty_accepted_value("avoid_when_candidates", avoid_payload.get("value")):
                    decision_errors.append("accepted_practice_avoid_when_empty")
                if risk_level == "high" and "contraindications_candidates" not in local_accepted_fields:
                    decision_errors.append("high_risk_practice_missing_accepted_contraindications")

        if review_status in {"accepted", "accepted_with_edits"} and local_accepted_fields:
            accepted_item_count += 1
            accepted_field_count += len(local_accepted_fields)
        elif review_status in {"accepted", "accepted_with_edits"} and not local_accepted_fields:
            warnings.append(f"{candidate_id}:accepted_status_without_accepted_fields")

        decision_reports.append(
            {
                "candidate_id": candidate_id or f"index_{index}",
                "review_status": review_status or "missing",
                "accepted_fields": local_accepted_fields,
                "errors": dedupe(decision_errors),
            }
        )
        errors.extend(decision_errors)

    status = "failed"
    if not errors and accepted_field_count == 0:
        status = "passed_with_no_accepted_fields"
    elif not errors:
        status = "passed"
    return {
        "schema_version": "mechanism_metadata_review_validation_report_v1",
        "prd_id": PRD_ID,
        "status": status,
        "decision_count": len(decisions),
        "accepted_item_count": accepted_item_count,
        "accepted_field_count": accepted_field_count,
        "errors": dedupe(errors),
        "warnings": dedupe(warnings),
        "decision_reports": decision_reports,
    }


def build_curated_overlay_preview(
    *,
    candidate_index: dict[str, dict[str, Any]],
    decision_document: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    accepted_field_count = 0
    for decision in list(decision_document.get("decisions") or []):
        review_status = normalize_text(decision.get("review_status")).lower()
        if review_status not in {"accepted", "accepted_with_edits"}:
            continue
        candidate = candidate_index.get(normalize_text(decision.get("candidate_id")))
        if not candidate:
            continue
        accepted_fields: dict[str, Any] = {}
        for field_name in FIELD_ORDER:
            payload = dict((decision.get("field_decisions") or {}).get(field_name) or {})
            if normalize_text(payload.get("decision")).lower() not in {"accept", "accept_with_edit"}:
                continue
            accepted_fields[field_name] = payload.get("value")
        if not accepted_fields:
            continue
        accepted_field_count += len(accepted_fields)
        source_ref = dict(candidate.get("source_ref") or {})
        items.append(
            {
                "candidate_id": candidate_id_of(candidate),
                "chunk_type": candidate_chunk_type(candidate),
                "risk_level": candidate_risk_level(candidate),
                "review_status": review_status,
                "reviewer_role": normalize_text(decision.get("reviewer_role")),
                "source_ref": {
                    "source_id": normalize_text(source_ref.get("source_id")),
                    "source_doc": normalize_text(source_ref.get("source_doc")),
                    "block_id": normalize_text(source_ref.get("block_id")),
                    "heading_path": list(source_ref.get("heading_path") or []),
                    "content_preview": safe_preview(source_ref.get("content_preview"), limit=300),
                },
                "accepted_fields": accepted_fields,
            }
        )
    items.sort(key=lambda item: (RISK_LEVEL_ORDER.get(item["risk_level"], 9), item["candidate_id"]))
    return {
        "schema_version": CURATED_OVERLAY_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "source_candidate_file": "TO_DO_LIST/logs/PRD-047.17/enrichment_candidates_deterministic.json",
        "decisions_file": "",
        "created_at": utc_now(),
        "fixture_only": bool(decision_document.get("fixture_only")),
        "live_apply_allowed": False,
        "safe_to_apply_to_live_metadata": False,
        "chroma_reindex_required_before_runtime_use": True,
        "items": items,
        "summary": {
            "accepted_item_count": len(items),
            "accepted_field_count": accepted_field_count,
            "by_chunk_type": dict(sorted(Counter(item["chunk_type"] for item in items).items())),
            "by_risk_level": dict(sorted(Counter(item["risk_level"] for item in items).items())),
        },
    }


def build_curation_status_report(
    *,
    queue_document: dict[str, Any],
    validation_report: dict[str, Any],
    decision_document: dict[str, Any],
) -> dict[str, Any]:
    decisions = list(decision_document.get("decisions") or [])
    status_counter = Counter(normalize_text(item.get("review_status")).lower() or "pending" for item in decisions)
    return {
        "schema_version": "mechanism_metadata_curation_status_report_v1",
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "created_at": utc_now(),
        "queue_count": int(queue_document.get("queue_count") or 0),
        "decision_count": len(decisions),
        "review_status_counts": dict(sorted(status_counter.items())),
        "accepted_item_count": int(validation_report.get("accepted_item_count") or 0),
        "accepted_field_count": int(validation_report.get("accepted_field_count") or 0),
        "validation_status": validation_report.get("status"),
        "fixture_only": bool(decision_document.get("fixture_only")),
        "live_apply_allowed": False,
        "notes": [
            "Accepted decisions remain curated overlay preview only.",
            "No live metadata mutation or Chroma reindex is performed in PRD-047.18.",
        ],
    }


def render_review_queue_markdown(queue_document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.18 Review Queue",
        "",
        f"- queue_count: `{queue_document['queue_count']}`",
        f"- candidate_count: `{queue_document['candidate_count']}`",
        f"- by_priority: `{json.dumps(queue_document['by_priority'], ensure_ascii=False)}`",
        "",
        "## Items",
    ]
    for item in queue_document.get("items", []):
        lines.append(
            f"- `{item['queue_priority']}` | `{item['chunk_type']}` | `{item['risk_level']}` | `{item['candidate_id']}`"
        )
        lines.append(f"  heading: {' / '.join(item['heading_path'])}")
        lines.append(f"  preview: {item['content_preview']}")
        lines.append(f"  action: {item['recommended_reviewer_action']}")
    return "\n".join(lines)


def render_review_decisions_template_markdown(document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.18 Review Decisions Template",
        "",
        f"- decision_count: `{document['decision_count']}`",
        "- all decisions start as `pending` and `safe_to_apply_to_live_metadata=false`.",
        "",
        "## Candidates",
    ]
    for decision in document.get("decisions", [])[:20]:
        lines.append(
            f"- `{decision['candidate_id']}` | status=`{decision['review_status']}` | heading=`{' / '.join(decision['source_ref']['heading_path'])}`"
        )
    if len(document.get("decisions", [])) > 20:
        lines.append(f"- ... and `{len(document['decisions']) - 20}` more pending decisions")
    return "\n".join(lines)


def render_validation_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.18 Review Decision Validation Report",
        "",
        f"- status: `{report['status']}`",
        f"- decision_count: `{report['decision_count']}`",
        f"- accepted_item_count: `{report['accepted_item_count']}`",
        f"- accepted_field_count: `{report['accepted_field_count']}`",
        "",
        "## Errors",
    ]
    for item in report.get("errors", []) or ["none"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Warnings"])
    for item in report.get("warnings", []) or ["none"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def render_curation_status_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.18 Curation Status Report",
        "",
        f"- queue_count: `{report['queue_count']}`",
        f"- decision_count: `{report['decision_count']}`",
        f"- validation_status: `{report['validation_status']}`",
        f"- accepted_item_count: `{report['accepted_item_count']}`",
        f"- accepted_field_count: `{report['accepted_field_count']}`",
        f"- fixture_only: `{report['fixture_only']}`",
        f"- live_apply_allowed: `{report['live_apply_allowed']}`",
        "",
        "## Review Status Counts",
    ]
    for key, value in report.get("review_status_counts", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines)


def render_curated_overlay_markdown(document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.18 Curated Overlay Preview",
        "",
        f"- fixture_only: `{document['fixture_only']}`",
        f"- live_apply_allowed: `{document['live_apply_allowed']}`",
        f"- chroma_reindex_required_before_runtime_use: `{document['chroma_reindex_required_before_runtime_use']}`",
        f"- accepted_item_count: `{document['summary']['accepted_item_count']}`",
        f"- accepted_field_count: `{document['summary']['accepted_field_count']}`",
        "",
        "## Items",
    ]
    for item in document.get("items", []):
        lines.append(f"- `{item['candidate_id']}` | `{item['chunk_type']}` | `{item['risk_level']}`")
        lines.append(f"  accepted_fields: `{json.dumps(item['accepted_fields'], ensure_ascii=False)}`")
    if not document.get("items"):
        lines.append("- none")
    return "\n".join(lines)


def render_curated_overlay_summary_markdown(document: dict[str, Any]) -> str:
    summary = document.get("summary") or {}
    lines = [
        "# PRD-047.18 Curated Overlay Summary",
        "",
        f"- accepted_item_count: `{summary.get('accepted_item_count', 0)}`",
        f"- accepted_field_count: `{summary.get('accepted_field_count', 0)}`",
        f"- by_chunk_type: `{json.dumps(summary.get('by_chunk_type', {}), ensure_ascii=False)}`",
        f"- by_risk_level: `{json.dumps(summary.get('by_risk_level', {}), ensure_ascii=False)}`",
        f"- fixture_only: `{document.get('fixture_only')}`",
        f"- live_apply_allowed: `{document.get('live_apply_allowed')}`",
    ]
    return "\n".join(lines)
