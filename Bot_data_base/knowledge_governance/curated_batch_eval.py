from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from .manual_review import (
    REVIEW_DECISION_SCHEMA_VERSION,
    build_candidate_index,
    build_curated_overlay_preview,
    build_review_decision_template,
    candidate_id_of,
    candidate_risk_level,
    validate_review_decisions,
)
from .manual_review_preflight import (
    build_apply_preflight_report,
    build_dry_run_apply_plan,
    build_overlay_intake_report,
)
from .offline_enrichment import dedupe, normalize_text, safe_preview, utc_now


PRD_ID = "PRD-047.20"
SOURCE_PRD_ID = "PRD-047.18"
SOURCE_CANDIDATE_PRD_ID = "PRD-047.17"
BATCH_ID = "batch_1"
OFFLINE_CURATOR_ROLE = "offline_curator_batch_1"
OFFLINE_CURATOR_ID = "offline_curator_batch_1"
SELECTION_SCHEMA_VERSION = "mechanism_metadata_curated_batch_selection_v1"
RETRIEVAL_DATASET_SCHEMA_VERSION = "mechanism_metadata_curated_batch_retrieval_eval_dataset_v1"
RETRIEVAL_RESULTS_SCHEMA_VERSION = "mechanism_metadata_curated_batch_retrieval_eval_results_v1"
RETRIEVAL_PLAN_SCHEMA_VERSION = "mechanism_metadata_curated_batch_retrieval_eval_case_result_v1"
EXPECTED_PREFLIGHT_BLOCKERS = {
    "human_final_approval_missing",
    "evaluation_only_overlay",
}
REVIEW_ACCEPT_STATUSES = {"accepted", "accepted_with_edits"}
REVIEW_NON_ACCEPT_STATUSES = {"rejected", "needs_source_context", "deferred"}
SHADOW_TOP_K = 5


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    normalized = normalize_text(value)
    return [normalized] if normalized else []


def _deepcopy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9_-]{3,}", normalize_text(text).lower())


def _accepted_value(field_name: str, candidate: dict[str, Any]) -> Any:
    return _deepcopy_json((candidate.get("candidate_fields") or {}).get(field_name))


def _set_field_decision(
    decision: dict[str, Any],
    *,
    field_name: str,
    field_decision: str,
    value: Any,
    reason: str,
) -> None:
    payload = dict((decision.get("field_decisions") or {}).get(field_name) or {})
    payload["decision"] = field_decision
    payload["value"] = _deepcopy_json(value)
    payload["reason"] = normalize_text(reason)
    decision["field_decisions"][field_name] = payload


def _selection_item(
    *,
    candidate: dict[str, Any],
    selection_role: str,
    selection_group: str,
    intended_review_status: str,
    focus_tags: list[str],
    focus_keywords_ru: list[str],
    rationale: str,
) -> dict[str, Any]:
    source_ref = dict(candidate.get("source_ref") or {})
    chunk_type = normalize_text((candidate.get("current_metadata_summary") or {}).get("chunk_type")).lower()
    return {
        "candidate_id": candidate_id_of(candidate),
        "chunk_type": chunk_type,
        "risk_level": candidate_risk_level(candidate),
        "selection_role": selection_role,
        "selection_group": selection_group,
        "intended_review_status": intended_review_status,
        "focus_tags": dedupe(focus_tags),
        "focus_keywords_ru": dedupe(focus_keywords_ru),
        "heading_path": list(source_ref.get("heading_path") or []),
        "content_preview": safe_preview(source_ref.get("content_preview"), limit=220),
        "rationale": normalize_text(rationale),
    }


BATCH_1_BLUEPRINT: list[dict[str, Any]] = [
    {
        "candidate_id": "a15d79f8-0ac0-42fc-9bc3-6985a529fb07",
        "selection_role": "mechanism_control_as_safety",
        "selection_group": "mechanism_or_concept",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["control_as_safety", "avoidance_as_protection", "self_criticism_as_control"],
        "focus_keywords_ru": ["контроль", "безопасность", "избегание", "защита", "самокритика"],
        "rationale": "Core mechanism candidate for control-as-safety and avoidance framing.",
    },
    {
        "candidate_id": "5be3f5b0-a073-4c15-8ed6-429ad22c029b",
        "selection_role": "mechanism_shame_visibility",
        "selection_group": "mechanism_or_concept",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["shame_as_wrong_visibility", "self_criticism_as_control"],
        "focus_keywords_ru": ["стыд", "видимость", "ошибка", "неправильный", "самокритика"],
        "rationale": "Mechanism explanation anchor for shame / wrong-visibility language.",
    },
    {
        "candidate_id": "5808a31f-2872-4e48-826c-b318bf0d60b0",
        "selection_role": "mechanism_self_criticism_parental_gaze",
        "selection_group": "mechanism_or_concept",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["self_criticism_as_control", "parental_gaze"],
        "focus_keywords_ru": ["самокритика", "внутренний взгляд", "родительский взгляд", "контроль"],
        "rationale": "Mechanism explanation for internal critic / parental gaze patterns.",
    },
    {
        "candidate_id": "3dfeca39-dbb2-4da0-b12f-15ef07fdad2b",
        "selection_role": "mechanism_avoidance_as_protection",
        "selection_group": "mechanism_or_concept",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["avoidance_as_protection", "parental_gaze"],
        "focus_keywords_ru": ["избегание", "защита", "перегрузка", "стыд"],
        "rationale": "Mechanism explanation for avoidance as protection instead of laziness.",
    },
    {
        "candidate_id": "47928bce-3306-4351-862e-290b3edeea59",
        "selection_role": "diagnostic_control_as_safety",
        "selection_group": "diagnostic_lens",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["control_as_safety"],
        "focus_keywords_ru": ["контроль", "страх", "угроза", "опора", "паника"],
        "rationale": "Safe diagnostic translation for control as a protection strategy.",
    },
    {
        "candidate_id": "d527d369-beb2-4113-b370-cb2738e76b55",
        "selection_role": "diagnostic_shame_visibility",
        "selection_group": "diagnostic_lens",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["shame_as_wrong_visibility"],
        "focus_keywords_ru": ["стыд", "быть увиденным", "неправильный", "видимость"],
        "rationale": "Safe diagnostic translation for shame / exposure language.",
    },
    {
        "candidate_id": "7b61940d-f6ff-46f8-9514-797efaf0ad00",
        "selection_role": "diagnostic_self_criticism_parental_gaze",
        "selection_group": "diagnostic_lens",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["self_criticism_as_control", "parental_gaze"],
        "focus_keywords_ru": ["самокритика", "внутренний голос", "родительский взгляд", "оценка"],
        "rationale": "Diagnostic lens for internal critic and inherited evaluative gaze.",
    },
    {
        "candidate_id": "6db17c5b-638d-452e-8a9c-8384c9ed78a4",
        "selection_role": "diagnostic_survival_drivers",
        "selection_group": "diagnostic_lens",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["survival_drivers"],
        "focus_keywords_ru": ["драйверы", "выживание", "реакции", "автопилот"],
        "rationale": "Diagnostic lens for survival drivers and stable autopilot framing.",
    },
    {
        "candidate_id": "468fb5d0-85f4-45c5-a7c3-5d593f51682e",
        "selection_role": "practice_stop_frame",
        "selection_group": "practice",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["practice_timing", "short_step"],
        "focus_keywords_ru": ["стоп", "кадр", "заметить реакцию", "один шаг"],
        "rationale": "Short practice candidate with explicit guardrails for low-resource timing.",
    },
    {
        "candidate_id": "4ea6de6c-5dd9-4914-9fa6-75ecb70a2457",
        "selection_role": "practice_fact_vs_interpretation",
        "selection_group": "practice",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["fact_vs_interpretation", "conflict_repair"],
        "focus_keywords_ru": ["факт", "интерпретация", "описание", "история"],
        "rationale": "Practice candidate for fact-vs-interpretation repair without overreach.",
    },
    {
        "candidate_id": "88a9ca94-e506-423b-8685-e462b9beaa48",
        "selection_role": "practice_reality_threat_check",
        "selection_group": "practice",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["reality_check", "threat_assessment"],
        "focus_keywords_ru": ["реальная угроза", "тревога", "проверка", "безопасность"],
        "rationale": "Practice candidate for reality-threat checking with explicit contraindications.",
    },
    {
        "candidate_id": "121bdc40-8633-469e-9837-ea9949f73de3",
        "selection_role": "practice_letter_to_program",
        "selection_group": "practice",
        "intended_review_status": "accepted_with_edits",
        "focus_tags": ["imperfect_self_program", "inner_program_contact"],
        "focus_keywords_ru": ["несовершенное я", "программа", "письмо программе", "внутренний критик"],
        "rationale": "Practice candidate for careful contact with the imperfect-self program.",
    },
    {
        "candidate_id": "02967da0-f163-4b5d-a732-6630dfeb0957",
        "selection_role": "source_fragment_control_seed",
        "selection_group": "source_fragment",
        "intended_review_status": "needs_source_context",
        "focus_tags": ["control_as_safety", "source_fragment"],
        "focus_keywords_ru": ["контроль", "семя смысла", "источник", "не цитата"],
        "rationale": "Source fragment example that should stay provenance-only, not writer-facing.",
    },
    {
        "candidate_id": "0d62f141-572d-4386-b02d-d7f9a46fa27f",
        "selection_role": "source_fragment_control_seed_alt",
        "selection_group": "source_fragment",
        "intended_review_status": "deferred",
        "focus_tags": ["control_as_safety", "source_fragment"],
        "focus_keywords_ru": ["контроль", "безопасность", "источник", "контекст"],
        "rationale": "Second source-fragment example kept out of accepted overlay for evaluation-only caution.",
    },
    {
        "candidate_id": "295a3a28-389d-4cc5-9c15-e8bf4010eb3c",
        "selection_role": "source_fragment_shadow_material",
        "selection_group": "source_fragment",
        "intended_review_status": "rejected",
        "focus_tags": ["golden_shadow", "source_fragment"],
        "focus_keywords_ru": ["тень", "источник", "не прямая цитата"],
        "rationale": "Rejected example to prove source-fragment non-acceptance in batch 1.",
    },
    {
        "candidate_id": "316c4af8-c441-4f1e-b606-ca23fce136c1",
        "selection_role": "source_fragment_shame_seed",
        "selection_group": "source_fragment",
        "intended_review_status": "needs_source_context",
        "focus_tags": ["shame_as_wrong_visibility", "source_fragment"],
        "focus_keywords_ru": ["стыд", "видимость", "источник", "контекст"],
        "rationale": "Needs-source-context example for shame-related source fragment handling.",
    },
]


def build_batch_1_selection(*, candidate_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    missing_candidates: list[str] = []
    for blueprint in BATCH_1_BLUEPRINT:
        candidate = candidate_index.get(blueprint["candidate_id"])
        if candidate is None:
            missing_candidates.append(blueprint["candidate_id"])
            continue
        items.append(
            _selection_item(
                candidate=candidate,
                selection_role=blueprint["selection_role"],
                selection_group=blueprint["selection_group"],
                intended_review_status=blueprint["intended_review_status"],
                focus_tags=list(blueprint["focus_tags"]),
                focus_keywords_ru=list(blueprint["focus_keywords_ru"]),
                rationale=blueprint["rationale"],
            )
        )
    counts_by_group = Counter(item["selection_group"] for item in items)
    status = "passed" if not missing_candidates else "blocked"
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "source_candidate_prd": SOURCE_CANDIDATE_PRD_ID,
        "batch_id": BATCH_ID,
        "created_at": utc_now(),
        "status": status,
        "selection_count": len(items),
        "counts_by_group": dict(sorted(counts_by_group.items())),
        "selection_rules": {
            "target_total_range": [10, 20],
            "selected_total": len(items),
            "mechanism_or_concept": counts_by_group.get("mechanism_or_concept", 0),
            "diagnostic_lens": counts_by_group.get("diagnostic_lens", 0),
            "practice": counts_by_group.get("practice", 0),
            "source_fragment": counts_by_group.get("source_fragment", 0),
            "high_risk_practice_accept_limit": 2,
        },
        "missing_candidates": missing_candidates,
        "items": items,
    }


def render_batch_selection_markdown(selection_document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.20 Batch 1 Selection",
        "",
        f"- status: `{selection_document['status']}`",
        f"- selection_count: `{selection_document['selection_count']}`",
        f"- counts_by_group: `{json.dumps(selection_document['counts_by_group'], ensure_ascii=False)}`",
        "",
        "## Items",
    ]
    for item in selection_document.get("items", []):
        lines.append(
            f"- `{item['selection_role']}` | `{item['chunk_type']}` | `{item['risk_level']}` | `{item['candidate_id']}` | intended=`{item['intended_review_status']}`"
        )
        lines.append(f"  tags: `{json.dumps(item['focus_tags'], ensure_ascii=False)}`")
        lines.append(f"  rationale: {item['rationale']}")
    if selection_document.get("missing_candidates"):
        lines.extend(["", "## Missing Candidates"])
        for candidate_id in selection_document["missing_candidates"]:
            lines.append(f"- `{candidate_id}`")
    return "\n".join(lines)


def _decision_fields_for_accepted_item(selection_role: str, candidate: dict[str, Any]) -> list[tuple[str, str, Any, str]]:
    chunk_type = normalize_text((candidate.get("current_metadata_summary") or {}).get("chunk_type")).lower()
    common_reason = f"Curated for {selection_role} as evaluation-only overlay metadata."
    accepted_fields: list[tuple[str, str, Any, str]] = [
        ("summary_candidate", "accept_with_edit", _accepted_value("summary_candidate", candidate), common_reason),
        ("core_thesis_candidate", "accept_with_edit", _accepted_value("core_thesis_candidate", candidate), common_reason),
        ("use_when_candidates", "accept_with_edit", _accepted_value("use_when_candidates", candidate), common_reason),
        ("avoid_when_candidates", "accept_with_edit", _accepted_value("avoid_when_candidates", candidate), common_reason),
        ("allowed_writer_use_candidate", "accept_with_edit", _accepted_value("allowed_writer_use_candidate", candidate), common_reason),
        ("quote_policy_suggestion", "accept", _accepted_value("quote_policy_suggestion", candidate), common_reason),
        ("depth_level_suggestion", "accept", _accepted_value("depth_level_suggestion", candidate), common_reason),
    ]
    if _string_list(_accepted_value("mechanism_hints_candidates", candidate)):
        accepted_fields.append(
            (
                "mechanism_hints_candidates",
                "accept_with_edit",
                _accepted_value("mechanism_hints_candidates", candidate),
                "Mechanism hints retained for shadow retrieval and writer metadata only.",
            )
        )
    if normalize_text(_accepted_value("safe_user_translation_candidate", candidate)):
        accepted_fields.append(
            (
                "safe_user_translation_candidate",
                "accept_with_edit",
                _accepted_value("safe_user_translation_candidate", candidate),
                "Safe translation retained for user-readable framing without diagnosis language.",
            )
        )
    if normalize_text(_accepted_value("risk_if_exposed_candidate", candidate)):
        accepted_fields.append(
            (
                "risk_if_exposed_candidate",
                "accept_with_edit",
                _accepted_value("risk_if_exposed_candidate", candidate),
                "Risk framing retained for writer caution and offline eval only.",
            )
        )
    if _string_list(_accepted_value("recommended_moves_candidates", candidate)):
        accepted_fields.append(
            (
                "recommended_moves_candidates",
                "accept_with_edit",
                _accepted_value("recommended_moves_candidates", candidate),
                "Recommended moves retained as metadata-only writer constraints.",
            )
        )
    if _string_list(_accepted_value("forbidden_moves_candidates", candidate)):
        accepted_fields.append(
            (
                "forbidden_moves_candidates",
                "accept_with_edit",
                _accepted_value("forbidden_moves_candidates", candidate),
                "Forbidden moves retained as metadata-only writer constraints.",
            )
        )
    if chunk_type == "practice":
        accepted_fields.append(
            (
                "contraindications_candidates",
                "accept_with_edit",
                _accepted_value("contraindications_candidates", candidate),
                "Practice stays evaluation-only and must keep explicit contraindications.",
            )
        )
    return accepted_fields


def _apply_non_accept_template(decision: dict[str, Any], *, review_status: str, reason: str) -> None:
    decision["review_status"] = review_status
    decision["review_notes"] = normalize_text(reason)
    for field_name in list((decision.get("field_decisions") or {}).keys()):
        _set_field_decision(
            decision,
            field_name=field_name,
            field_decision="needs_source_context" if review_status == "needs_source_context" else "defer",
            value=[] if isinstance((decision["field_decisions"][field_name] or {}).get("value"), list) else "",
            reason=reason,
        )
    if review_status == "rejected":
        for field_name in list((decision.get("field_decisions") or {}).keys()):
            _set_field_decision(
                decision,
                field_name=field_name,
                field_decision="reject",
                value=[] if isinstance((decision["field_decisions"][field_name] or {}).get("value"), list) else "",
                reason=reason,
            )


def build_batch_1_decisions_pack(
    *,
    selection_document: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    high_risk_practice_accepted_fields = 0
    for item in selection_document.get("items", []):
        candidate = candidate_index[item["candidate_id"]]
        decision = build_review_decision_template(candidate)
        decision["review_status"] = item["intended_review_status"]
        decision["reviewer_role"] = OFFLINE_CURATOR_ROLE
        decision["reviewer_id"] = OFFLINE_CURATOR_ID
        decision["reviewed_at"] = utc_now()
        decision["safe_to_apply_to_live_metadata"] = False
        decision["review_notes"] = normalize_text(
            f"PRD-047.20 curated batch 1 item for {item['selection_role']}; evaluation-only and not human-final-approved."
        )
        decision["human_final_approval"] = False
        decision["evaluation_only"] = True
        decision["live_apply_allowed"] = False
        decision["selection_role"] = item["selection_role"]
        decision["focus_tags"] = list(item["focus_tags"])
        decision["focus_keywords_ru"] = list(item["focus_keywords_ru"])

        if item["intended_review_status"] in REVIEW_NON_ACCEPT_STATUSES:
            if item["intended_review_status"] == "rejected":
                reason = "Kept outside accepted overlay to avoid source-fragment leakage into writer-facing metadata."
            elif item["intended_review_status"] == "needs_source_context":
                reason = "Requires more source context before any accepted metadata field can be trusted."
            else:
                reason = "Deferred from accepted overlay; useful as review evidence only."
            _apply_non_accept_template(decision, review_status=item["intended_review_status"], reason=reason)
        else:
            for field_name, field_decision, value, reason in _decision_fields_for_accepted_item(item["selection_role"], candidate):
                _set_field_decision(
                    decision,
                    field_name=field_name,
                    field_decision=field_decision,
                    value=value,
                    reason=reason,
                )
            for field_name in list((decision.get("field_decisions") or {}).keys()):
                if normalize_text((decision["field_decisions"][field_name] or {}).get("decision")).lower() == "pending":
                    _set_field_decision(
                        decision,
                        field_name=field_name,
                        field_decision="defer",
                        value=[] if isinstance((decision["field_decisions"][field_name] or {}).get("value"), list) else "",
                        reason="Not needed for batch 1 accepted overlay preview.",
                    )
            if item["chunk_type"] == "practice" and item["risk_level"] == "high":
                high_risk_practice_accepted_fields += sum(
                    1
                    for payload in (decision.get("field_decisions") or {}).values()
                    if normalize_text((payload or {}).get("decision")).lower() in {"accept", "accept_with_edit"}
                )
        decisions.append(decision)

    document = {
        "schema_version": REVIEW_DECISION_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "source_candidate_prd": SOURCE_CANDIDATE_PRD_ID,
        "batch_id": BATCH_ID,
        "created_at": utc_now(),
        "decision_count": len(decisions),
        "fixture_only": False,
        "human_final_approval": False,
        "evaluation_only": True,
        "live_apply_allowed": False,
        "reviewer_role": OFFLINE_CURATOR_ROLE,
        "reviewer_id": OFFLINE_CURATOR_ID,
        "high_risk_practice_accepted_fields": high_risk_practice_accepted_fields,
        "decisions": decisions,
    }
    validation_report = validate_review_decisions(document, candidate_index)
    document["accepted_field_count"] = int(validation_report.get("accepted_field_count") or 0)
    document["accepted_item_count"] = int(validation_report.get("accepted_item_count") or 0)
    document["validation_status"] = validation_report.get("status")
    return document


def render_batch_decisions_markdown(decision_document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.20 Batch 1 Decisions Pack",
        "",
        f"- decision_count: `{decision_document['decision_count']}`",
        f"- accepted_item_count: `{decision_document['accepted_item_count']}`",
        f"- accepted_field_count: `{decision_document['accepted_field_count']}`",
        f"- validation_status: `{decision_document['validation_status']}`",
        f"- human_final_approval: `{decision_document['human_final_approval']}`",
        f"- evaluation_only: `{decision_document['evaluation_only']}`",
        f"- live_apply_allowed: `{decision_document['live_apply_allowed']}`",
        "",
        "## Decisions",
    ]
    for decision in decision_document.get("decisions", []):
        lines.append(
            f"- `{decision['selection_role']}` | `{decision['review_status']}` | `{decision['candidate_id']}`"
        )
        accepted_fields = [
            field_name
            for field_name, payload in (decision.get("field_decisions") or {}).items()
            if normalize_text((payload or {}).get("decision")).lower() in {"accept", "accept_with_edit"}
        ]
        lines.append(f"  accepted_fields: `{json.dumps(accepted_fields, ensure_ascii=False)}`")
        lines.append(f"  review_notes: {decision['review_notes']}")
    return "\n".join(lines)


def build_batch_1_overlay_preview(
    *,
    candidate_index: dict[str, dict[str, Any]],
    decision_document: dict[str, Any],
    decisions_file: str,
) -> dict[str, Any]:
    overlay = build_curated_overlay_preview(
        candidate_index=candidate_index,
        decision_document=decision_document,
    )
    overlay["prd_id"] = PRD_ID
    overlay["source_prd"] = SOURCE_PRD_ID
    overlay["source_candidate_prd"] = SOURCE_CANDIDATE_PRD_ID
    overlay["batch_id"] = BATCH_ID
    overlay["fixture_only"] = False
    overlay["human_final_approval"] = False
    overlay["evaluation_only"] = True
    overlay["live_apply_allowed"] = False
    overlay["safe_to_apply_to_live_metadata"] = False
    overlay["allowed_for_retrieval_eval"] = True
    overlay["decisions_file"] = decisions_file
    return overlay


def render_batch_overlay_markdown(overlay_document: dict[str, Any]) -> str:
    summary = overlay_document.get("summary") or {}
    lines = [
        "# PRD-047.20 Batch 1 Accepted Overlay Preview",
        "",
        f"- accepted_item_count: `{summary.get('accepted_item_count', 0)}`",
        f"- accepted_field_count: `{summary.get('accepted_field_count', 0)}`",
        f"- human_final_approval: `{overlay_document['human_final_approval']}`",
        f"- evaluation_only: `{overlay_document['evaluation_only']}`",
        f"- live_apply_allowed: `{overlay_document['live_apply_allowed']}`",
        "",
        "## Accepted Items",
    ]
    for item in overlay_document.get("items", []):
        lines.append(f"- `{item['candidate_id']}` | `{item['chunk_type']}` | `{item['risk_level']}`")
        lines.append(f"  accepted_fields: `{json.dumps(sorted(item['accepted_fields'].keys()), ensure_ascii=False)}`")
    return "\n".join(lines)


def build_batch_1_preflight_bundle(
    *,
    overlay_document: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
    processed_block_index: dict[str, dict[str, Any]],
    overlay_file: str,
) -> dict[str, Any]:
    intake_report = build_overlay_intake_report(
        overlay_document=overlay_document,
        candidate_index=candidate_index,
        processed_block_index=processed_block_index,
        overlay_file=overlay_file,
    )
    intake_report["prd_id"] = PRD_ID
    intake_report["source_overlay_prd"] = SOURCE_PRD_ID
    intake_report["batch_id"] = BATCH_ID
    intake_report["human_final_approval"] = False
    intake_report["evaluation_only"] = True
    intake_report["real_apply_blockers"] = sorted(
        dict.fromkeys(list(intake_report.get("real_apply_blockers") or []) + sorted(EXPECTED_PREFLIGHT_BLOCKERS))
    )
    dry_run_apply_plan = build_dry_run_apply_plan(
        overlay_document=overlay_document,
        candidate_index=candidate_index,
        processed_block_index=processed_block_index,
        overlay_file=overlay_file,
    )
    dry_run_apply_plan["prd_id"] = PRD_ID
    dry_run_apply_plan["batch_id"] = BATCH_ID
    apply_preflight_report = build_apply_preflight_report(
        intake_report=intake_report,
        dry_run_plan=dry_run_apply_plan,
    )
    apply_preflight_report["prd_id"] = PRD_ID
    apply_preflight_report["batch_id"] = BATCH_ID
    expected_blockers = sorted(
        dict.fromkeys(list(apply_preflight_report.get("expected_blockers") or []) + sorted(EXPECTED_PREFLIGHT_BLOCKERS))
    )
    unexpected_blockers = list(apply_preflight_report.get("unexpected_blockers") or [])
    apply_preflight_report["status"] = "passed_with_expected_blockers" if not unexpected_blockers else "blocked"
    apply_preflight_report["expected_blockers"] = expected_blockers
    apply_preflight_report["ready_for_live_apply"] = False
    apply_preflight_report["ready_for_chroma_reindex"] = False
    apply_preflight_report["ready_for_runtime_visibility"] = False
    apply_preflight_report["ready_for_eval_over_real_overlay"] = not unexpected_blockers
    apply_preflight_report["next_safe_step"] = "offline_retrieval_eval_over_accepted_overlay"
    return {
        "overlay_intake_report": intake_report,
        "dry_run_apply_plan": dry_run_apply_plan,
        "apply_preflight_report": apply_preflight_report,
    }


def render_batch_preflight_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.20 Batch 1 Apply Preflight",
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
    return "\n".join(lines)


def build_retrieval_eval_dataset(
    *,
    selection_document: dict[str, Any],
) -> dict[str, Any]:
    selected = {item["selection_role"]: item for item in selection_document.get("items", [])}
    cases = [
        {
            "id": "B1-001",
            "query": "Когда человек все держит под контролем, потому что иначе страшно, как это понять?",
            "theme": "control_as_safety",
            "expected_candidate_ids": [
                selected["mechanism_control_as_safety"]["candidate_id"],
                selected["diagnostic_control_as_safety"]["candidate_id"],
            ],
            "expected_focus_tags": ["control_as_safety"],
            "expected_chunk_types": ["mechanism", "diagnostic_lens"],
        },
        {
            "id": "B1-002",
            "query": "Паника и страх потерять контроль: какой здесь безопасный смысл, а не просто слабость?",
            "theme": "control_as_safety_panic",
            "expected_candidate_ids": [
                selected["diagnostic_control_as_safety"]["candidate_id"],
                selected["mechanism_control_as_safety"]["candidate_id"],
            ],
            "expected_focus_tags": ["control_as_safety"],
            "expected_chunk_types": ["diagnostic_lens", "mechanism"],
        },
        {
            "id": "B1-003",
            "query": "Почему так стыдно быть увиденным и показаться неправильным?",
            "theme": "shame_visibility",
            "expected_candidate_ids": [
                selected["diagnostic_shame_visibility"]["candidate_id"],
                selected["mechanism_shame_visibility"]["candidate_id"],
            ],
            "expected_focus_tags": ["shame_as_wrong_visibility"],
            "expected_chunk_types": ["diagnostic_lens", "mechanism"],
        },
        {
            "id": "B1-004",
            "query": "Самокритика будто держит меня в узде. Это про контроль?",
            "theme": "self_criticism_as_control",
            "expected_candidate_ids": [
                selected["mechanism_self_criticism_parental_gaze"]["candidate_id"],
                selected["diagnostic_self_criticism_parental_gaze"]["candidate_id"],
                selected["mechanism_control_as_safety"]["candidate_id"],
            ],
            "expected_focus_tags": ["self_criticism_as_control"],
            "expected_chunk_types": ["mechanism", "diagnostic_lens"],
        },
        {
            "id": "B1-005",
            "query": "Объясни механизм избегания как защиты, а не как лени.",
            "theme": "avoidance_as_protection",
            "expected_candidate_ids": [
                selected["mechanism_avoidance_as_protection"]["candidate_id"],
                selected["mechanism_control_as_safety"]["candidate_id"],
            ],
            "expected_focus_tags": ["avoidance_as_protection"],
            "expected_chunk_types": ["mechanism"],
        },
        {
            "id": "B1-006",
            "query": "Я все время вижу не факты, а свои истории. Есть короткая практика?",
            "theme": "fact_vs_interpretation",
            "expected_candidate_ids": [selected["practice_fact_vs_interpretation"]["candidate_id"]],
            "expected_focus_tags": ["fact_vs_interpretation"],
            "expected_chunk_types": ["practice"],
        },
        {
            "id": "B1-007",
            "query": "Нужен один бережный шаг, чтобы остановиться и заметить реакцию.",
            "theme": "short_step_stop_frame",
            "expected_candidate_ids": [selected["practice_stop_frame"]["candidate_id"]],
            "expected_focus_tags": ["practice_timing", "short_step"],
            "expected_chunk_types": ["practice"],
        },
        {
            "id": "B1-008",
            "query": "Как проверить, реальная ли это угроза, а не только тревога?",
            "theme": "threat_check",
            "expected_candidate_ids": [selected["practice_reality_threat_check"]["candidate_id"]],
            "expected_focus_tags": ["reality_check", "threat_assessment"],
            "expected_chunk_types": ["practice"],
        },
        {
            "id": "B1-009",
            "query": "Как разговаривать с этой внутренней программой несовершенного я?",
            "theme": "imperfect_self_program",
            "expected_candidate_ids": [
                selected["practice_letter_to_program"]["candidate_id"],
                selected["mechanism_self_criticism_parental_gaze"]["candidate_id"],
            ],
            "expected_focus_tags": ["imperfect_self_program", "inner_program_contact"],
            "expected_chunk_types": ["practice", "mechanism"],
        },
        {
            "id": "B1-010",
            "query": "Объясни нормально, без диагнозов, почему программа так устойчива.",
            "theme": "diagnostic_translation",
            "expected_candidate_ids": [
                selected["diagnostic_shame_visibility"]["candidate_id"],
                selected["diagnostic_survival_drivers"]["candidate_id"],
            ],
            "expected_focus_tags": ["shame_as_wrong_visibility", "survival_drivers"],
            "expected_chunk_types": ["diagnostic_lens"],
        },
        {
            "id": "B1-011",
            "query": "Какие здесь вообще есть несколько практических направлений, если я хочу это замечать?",
            "theme": "practice_overview",
            "expected_candidate_ids": [
                selected["practice_stop_frame"]["candidate_id"],
                selected["practice_fact_vs_interpretation"]["candidate_id"],
                selected["practice_reality_threat_check"]["candidate_id"],
                selected["practice_letter_to_program"]["candidate_id"],
            ],
            "expected_focus_tags": ["practice_timing", "fact_vs_interpretation", "reality_check", "imperfect_self_program"],
            "expected_chunk_types": ["practice"],
            "expected_min_practice_hits": 2,
        },
        {
            "id": "B1-012",
            "query": "Нужен короткий ответ для состояния, где ресурса почти нет.",
            "theme": "low_resource_answer",
            "expected_candidate_ids": [
                selected["diagnostic_control_as_safety"]["candidate_id"],
                selected["diagnostic_survival_drivers"]["candidate_id"],
            ],
            "expected_focus_tags": ["control_as_safety", "survival_drivers"],
            "expected_chunk_types": ["diagnostic_lens", "mechanism"],
            "avoid_chunk_types": ["source_fragment"],
        },
        {
            "id": "B1-013",
            "query": "Что такое пять драйверов выживания простым языком?",
            "theme": "survival_drivers",
            "expected_candidate_ids": [selected["diagnostic_survival_drivers"]["candidate_id"]],
            "expected_focus_tags": ["survival_drivers"],
            "expected_chunk_types": ["diagnostic_lens"],
        },
        {
            "id": "B1-014",
            "query": "Это похоже на родительский взгляд внутри меня?",
            "theme": "parental_gaze",
            "expected_candidate_ids": [
                selected["mechanism_self_criticism_parental_gaze"]["candidate_id"],
                selected["diagnostic_self_criticism_parental_gaze"]["candidate_id"],
                selected["mechanism_avoidance_as_protection"]["candidate_id"],
            ],
            "expected_focus_tags": ["parental_gaze"],
            "expected_chunk_types": ["mechanism", "diagnostic_lens"],
        },
        {
            "id": "B1-015",
            "query": "Мне хочется прямую цитату из книги про это.",
            "theme": "source_fragment_guard",
            "expected_candidate_ids": [selected["mechanism_shame_visibility"]["candidate_id"]],
            "expected_focus_tags": ["shame_as_wrong_visibility"],
            "expected_chunk_types": ["mechanism"],
            "avoid_chunk_types": ["source_fragment"],
        },
        {
            "id": "B1-016",
            "query": "Стоит ли сразу давать глубокую практику, если человек в перегрузе?",
            "theme": "practice_guardrails",
            "expected_candidate_ids": [
                selected["practice_stop_frame"]["candidate_id"],
                selected["practice_letter_to_program"]["candidate_id"],
            ],
            "expected_focus_tags": ["practice_timing", "inner_program_contact"],
            "expected_chunk_types": ["practice"],
            "avoid_chunk_types": ["source_fragment"],
        },
        {
            "id": "B1-017",
            "query": "Хочу различать факт и интерпретацию в конфликте.",
            "theme": "fact_vs_interpretation_conflict",
            "expected_candidate_ids": [selected["practice_fact_vs_interpretation"]["candidate_id"]],
            "expected_focus_tags": ["fact_vs_interpretation", "conflict_repair"],
            "expected_chunk_types": ["practice"],
        },
        {
            "id": "B1-018",
            "query": "Если избегание защищает, с чего начать без перегруза?",
            "theme": "avoidance_low_resource",
            "expected_candidate_ids": [
                selected["mechanism_avoidance_as_protection"]["candidate_id"],
                selected["practice_stop_frame"]["candidate_id"],
            ],
            "expected_focus_tags": ["avoidance_as_protection", "short_step"],
            "expected_chunk_types": ["mechanism", "practice"],
        },
    ]
    return {
        "schema_version": RETRIEVAL_DATASET_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "batch_id": BATCH_ID,
        "created_at": utc_now(),
        "case_count": len(cases),
        "cases": cases,
    }


def render_retrieval_eval_dataset_markdown(dataset_document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.20 Retrieval Eval Dataset",
        "",
        f"- case_count: `{dataset_document['case_count']}`",
        "",
        "## Cases",
    ]
    for case in dataset_document.get("cases", []):
        lines.append(f"- `{case['id']}` | `{case['theme']}`")
        lines.append(f"  query: {case['query']}")
        lines.append(f"  expected_candidate_ids: `{json.dumps(case['expected_candidate_ids'], ensure_ascii=False)}`")
    return "\n".join(lines)


def build_shadow_lookup_index(
    *,
    overlay_document: dict[str, Any],
    selection_document: dict[str, Any],
) -> list[dict[str, Any]]:
    selection_map = {item["candidate_id"]: item for item in selection_document.get("items", [])}
    index_rows: list[dict[str, Any]] = []
    for item in overlay_document.get("items", []):
        selection_item = selection_map.get(item["candidate_id"], {})
        accepted_fields = dict(item.get("accepted_fields") or {})
        parts: list[str] = []
        for value in accepted_fields.values():
            if isinstance(value, list):
                parts.extend(_string_list(value))
            else:
                normalized = normalize_text(value)
                if normalized:
                    parts.append(normalized)
        parts.extend(_string_list(selection_item.get("focus_keywords_ru")))
        search_text = " ".join(parts)
        index_rows.append(
            {
                "candidate_id": item["candidate_id"],
                "chunk_type": normalize_text(item.get("chunk_type")).lower(),
                "risk_level": normalize_text(item.get("risk_level")).lower(),
                "selection_role": normalize_text(selection_item.get("selection_role")),
                "focus_tags": list(selection_item.get("focus_tags") or []),
                "focus_keywords_ru": list(selection_item.get("focus_keywords_ru") or []),
                "search_text": search_text,
                "accepted_fields": accepted_fields,
            }
        )
    return index_rows


def shadow_lookup(*, query: str, overlay_index: list[dict[str, Any]], top_k: int = SHADOW_TOP_K) -> list[dict[str, Any]]:
    query_tokens = set(_tokenize(query))
    hits: list[dict[str, Any]] = []
    for row in overlay_index:
        search_tokens = set(_tokenize(row["search_text"]))
        overlap = sorted(query_tokens.intersection(search_tokens))
        if not overlap:
            continue
        score = float(len(overlap))
        if row["focus_tags"]:
            score += min(1.0, 0.2 * len(row["focus_tags"]))
        if row["chunk_type"] == "practice" and "практик" in normalize_text(query).lower():
            score += 0.5
        hits.append(
            {
                "candidate_id": row["candidate_id"],
                "chunk_type": row["chunk_type"],
                "risk_level": row["risk_level"],
                "selection_role": row["selection_role"],
                "focus_tags": list(row["focus_tags"]),
                "score": round(score, 3),
                "matched_terms": overlap[:8],
                "practice_has_safety": bool(
                    _string_list((row["accepted_fields"] or {}).get("avoid_when_candidates"))
                    and _string_list((row["accepted_fields"] or {}).get("contraindications_candidates"))
                ),
                "summary_preview": safe_preview((row["accepted_fields"] or {}).get("summary_candidate"), limit=180),
                "safe_user_translation_preview": safe_preview(
                    (row["accepted_fields"] or {}).get("safe_user_translation_candidate"),
                    limit=180,
                ),
            }
        )
    hits.sort(key=lambda item: (-item["score"], item["candidate_id"]))
    return hits[: max(1, top_k)]


def _baseline_hit_id(hit: dict[str, Any]) -> str:
    return normalize_text(hit.get("candidate_id") or hit.get("id") or hit.get("chunk_id"))


def _shadow_hit_pass(case: dict[str, Any], shadow_hits: list[dict[str, Any]]) -> bool:
    expected_ids = set(case.get("expected_candidate_ids") or [])
    top_ids = {_baseline_hit_id(hit) for hit in shadow_hits[:3]}
    if expected_ids.intersection(top_ids):
        return True
    expected_min_practice_hits = int(case.get("expected_min_practice_hits") or 0)
    if expected_min_practice_hits:
        practice_hits = [hit for hit in shadow_hits[:5] if normalize_text(hit.get("chunk_type")).lower() == "practice"]
        if len(practice_hits) >= expected_min_practice_hits:
            return True
    return False


def _baseline_hit_pass(case: dict[str, Any], baseline_hits: list[dict[str, Any]]) -> bool:
    expected_ids = set(case.get("expected_candidate_ids") or [])
    top_ids = {_baseline_hit_id(hit) for hit in baseline_hits[:3]}
    return bool(expected_ids.intersection(top_ids))


def build_retrieval_eval_results(
    *,
    dataset_document: dict[str, Any],
    overlay_document: dict[str, Any],
    selection_document: dict[str, Any],
    baseline_results: dict[str, list[dict[str, Any]]],
    baseline_available: bool,
    baseline_warning: str,
) -> dict[str, Any]:
    overlay_index = build_shadow_lookup_index(
        overlay_document=overlay_document,
        selection_document=selection_document,
    )
    cases: list[dict[str, Any]] = []
    overlay_hit_count = 0
    baseline_hit_count = 0
    combined_hit_count = 0
    unsafe_overlay_hit_count = 0
    overlay_source_fragment_violations = 0

    for case in dataset_document.get("cases", []):
        shadow_hits = shadow_lookup(query=str(case.get("query") or ""), overlay_index=overlay_index)
        baseline_hits = list(baseline_results.get(str(case.get("id") or ""), []))
        shadow_pass = _shadow_hit_pass(case, shadow_hits)
        baseline_pass = _baseline_hit_pass(case, baseline_hits) if baseline_available else False
        combined_pass = shadow_pass or baseline_pass
        avoid_chunk_types = {normalize_text(item).lower() for item in case.get("avoid_chunk_types") or []}
        avoided_hits = [
            hit
            for hit in shadow_hits[:3]
            if normalize_text(hit.get("chunk_type")).lower() in avoid_chunk_types
        ]
        if avoided_hits:
            overlay_source_fragment_violations += len(avoided_hits)
        unsafe_hits = [
            hit
            for hit in shadow_hits[:3]
            if normalize_text(hit.get("chunk_type")).lower() == "practice" and not bool(hit.get("practice_has_safety"))
        ]
        unsafe_overlay_hit_count += len(unsafe_hits)
        overlay_hit_count += 1 if shadow_pass else 0
        baseline_hit_count += 1 if baseline_pass else 0
        combined_hit_count += 1 if combined_pass else 0
        cases.append(
            {
                "schema_version": RETRIEVAL_PLAN_SCHEMA_VERSION,
                "id": case["id"],
                "theme": case["theme"],
                "query": case["query"],
                "shadow_hit": shadow_pass,
                "baseline_hit": baseline_pass if baseline_available else None,
                "combined_hit": combined_pass,
                "shadow_hits": shadow_hits,
                "baseline_hits": baseline_hits,
                "avoid_chunk_types": list(case.get("avoid_chunk_types") or []),
                "avoided_shadow_hits": avoided_hits,
                "unsafe_shadow_hits": unsafe_hits,
            }
        )

    accepted_overlay_items = list(overlay_document.get("items") or [])
    separator_preview_accepted_count = sum(
        1 for item in accepted_overlay_items if normalize_text(((item.get("source_ref") or {}).get("content_preview"))) in {"", "***", "---"}
    )
    practice_without_safety_count = sum(
        1
        for item in accepted_overlay_items
        if normalize_text(item.get("chunk_type")).lower() == "practice"
        and (
            not _string_list((item.get("accepted_fields") or {}).get("avoid_when_candidates"))
            or not _string_list((item.get("accepted_fields") or {}).get("contraindications_candidates"))
        )
    )
    case_total = max(1, len(cases))
    overlay_rate = round(overlay_hit_count / case_total, 4)
    baseline_rate = round(baseline_hit_count / case_total, 4) if baseline_available else None
    combined_rate = round(combined_hit_count / case_total, 4)
    status = "passed"
    warnings: list[str] = []
    if not baseline_available and baseline_warning:
        warnings.append(baseline_warning)
        status = "warning"
    if overlay_rate < 0.75:
        warnings.append("overlay_shadow_hit_rate_below_0_75")
        status = "warning"
    if unsafe_overlay_hit_count > 0 or practice_without_safety_count > 0 or separator_preview_accepted_count > 0:
        status = "blocked"
    return {
        "schema_version": RETRIEVAL_RESULTS_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "batch_id": BATCH_ID,
        "created_at": utc_now(),
        "status": status,
        "baseline_available": baseline_available,
        "baseline_warning": baseline_warning,
        "cases_total": len(cases),
        "baseline_hit_rate": baseline_rate,
        "overlay_shadow_hit_rate": overlay_rate,
        "combined_expected_help_rate": combined_rate,
        "unsafe_overlay_hit_count": unsafe_overlay_hit_count,
        "overlay_source_fragment_violations": overlay_source_fragment_violations,
        "separator_preview_accepted_count": separator_preview_accepted_count,
        "practice_without_safety_count": practice_without_safety_count,
        "accepted_overlay_item_count": len(accepted_overlay_items),
        "warnings": warnings,
        "cases": cases,
    }


def render_retrieval_eval_results_markdown(results_document: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.20 Retrieval Eval Results",
        "",
        f"- status: `{results_document['status']}`",
        f"- baseline_available: `{results_document['baseline_available']}`",
        f"- baseline_hit_rate: `{results_document['baseline_hit_rate']}`",
        f"- overlay_shadow_hit_rate: `{results_document['overlay_shadow_hit_rate']}`",
        f"- combined_expected_help_rate: `{results_document['combined_expected_help_rate']}`",
        f"- unsafe_overlay_hit_count: `{results_document['unsafe_overlay_hit_count']}`",
        f"- separator_preview_accepted_count: `{results_document['separator_preview_accepted_count']}`",
        f"- practice_without_safety_count: `{results_document['practice_without_safety_count']}`",
        "",
        "## Case Summary",
    ]
    for case in results_document.get("cases", []):
        lines.append(
            f"- `{case['id']}` | shadow=`{case['shadow_hit']}` | baseline=`{case['baseline_hit']}` | combined=`{case['combined_hit']}`"
        )
    if results_document.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in results_document["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def build_candidate_index_from_run(candidate_run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return build_candidate_index(list(candidate_run.get("candidates") or []))
