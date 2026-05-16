from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .architect_review_pass import build_architect_review_items, sanitize_preview, utc_now_iso


POLICY_VERSION = "architect_auto_decision_policy_v1"

SENSITIVE_TERMS = [
    "страх",
    "паник",
    "лоссофоб",
    "лиссофоб",
    "сойти с ума",
    "потерять контроль",
    "травм",
    "насили",
    "стыд",
    "сексуал",
    "диссоци",
    "депресс",
    "суицид",
    "самоповреж",
    "психоз",
    "abuse",
    "trauma",
    "suicid",
    "self-harm",
    "panic",
    "psychosis",
]

GENERIC_SUMMARY_PATTERNS = [
    "может быть использ",
    "важно соблюдать безопасность",
    "важно соблюдать конфиденциаль",
    "обогащен",
    "активное слушание",
    "в целом полез",
    "helpful for counseling",
    "can be used",
]

DIAGNOSTIC_PATTERNS = [
    "диагноз",
    "диагност",
    "шизофрен",
    "биполяр",
    "психоз",
    "расстройство",
]

THERAPEUTIC_PROMISE_PATTERNS = [
    "гарант",
    "исцел",
    "вылеч",
    "полностью избав",
    "навсегда реш",
]

SPIRITUAL_AUTHORITY_PATTERNS = [
    "духовн",
    "истин",
    "просветлен",
    "высшая правда",
]

DIRECTIVE_PATTERNS = [
    "ты должен",
    "нужно",
    "обязан",
    "сделай",
    "перестань",
    "немедленно",
]

ADVISORY_FIELDS = [
    "summary",
    "lens_family_candidates",
    "tags",
    "use_when",
    "avoid_when",
    "self_contained_score",
    "self_contained_reason",
    "split_merge_suggestion",
    "confidence",
]


@dataclass
class DecisionEnvelope:
    payload: dict[str, Any]
    reason_code: str
    sensitive_hit: bool



def _to_text(*parts: Any) -> str:
    return " ".join(str(part or "") for part in parts).lower()



def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)



def _normalize_tags(item: dict[str, Any]) -> list[str]:
    llm = item.get("llm_enrichment") if isinstance(item.get("llm_enrichment"), dict) else {}
    tags = llm.get("tags")
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()][:10]
    return []



def _default_practice_edits(summary: str) -> dict[str, Any]:
    clean_summary = summary.strip()
    if not clean_summary:
        clean_summary = (
            "Внутренняя practice-подсказка для мягкого самонаблюдения; "
            "не является инструкцией, диагнозом или терапевтической интервенцией."
        )
    else:
        clean_summary = sanitize_preview(
            (
                "Внутренняя practice-подсказка для мягкого самонаблюдения. "
                "Не использовать как директивную инструкцию, диагноз или терапевтическую интервенцию. "
                f"Контекст блока: {clean_summary}"
            ),
            limit=500,
        )

    return {
        "summary": clean_summary,
        "use_when": [
            "использовать как мягкую внутреннюю подсказку, когда пользователь в устойчивом состоянии "
            "и явно запрашивает бережное практическое самонаблюдение"
        ],
        "avoid_when": [
            "не предлагать при остром дистрессе, панике, суицидальных мыслях, психозе, выраженной диссоциации "
            "или когда пользователь просит срочную помощь",
            "не подавать как терапевтическую методику, диагноз или замену специалисту",
        ],
    }



def _build_decision(
    *,
    review_item_id: str,
    block_id: str,
    decision: str,
    reason: str,
    source_prd: str,
    approved_fields: list[str] | None = None,
    rejected_fields: list[str] | None = None,
    edited_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "review_item_id": review_item_id,
        "block_id": block_id,
        "decision": decision,
        "reviewer": "architect",
        "reason": reason,
        "approved_fields": approved_fields or [],
        "rejected_fields": rejected_fields or [],
        "edited_fields": edited_fields or {},
        "created_at": utc_now_iso(),
        "source_prd": source_prd,
    }



def evaluate_item_policy(item: dict[str, Any], *, source_prd: str) -> DecisionEnvelope:
    review_item_id = str(item.get("review_item_id") or "").strip()
    block_id = str(item.get("block_id") or "").strip()
    chunk_type = str(item.get("chunk_type") or "unknown").strip().lower()
    priority = str(item.get("review_priority") or "P2").strip().upper()
    safety_flags = {str(flag).strip().lower() for flag in (item.get("safety_flags") or [])}
    summary = str(((item.get("llm_enrichment") or {}).get("summary") or "")).strip()
    safe_preview = str(item.get("safe_preview") or "").strip()

    text = _to_text(summary, safe_preview, " ".join(item.get("review_reasons") or []))
    sensitive_hit = _contains_any(text, SENSITIVE_TERMS)

    if priority == "P0":
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="defer",
                reason="P0 priority item requires controlled manual review before apply.",
                source_prd=source_prd,
            ),
            reason_code="p0_priority_defer",
            sensitive_hit=sensitive_hit,
        )

    if chunk_type == "quote":
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="defer",
                reason="Quote chunk kept in conservative defer mode to avoid user-facing doctrine/quotation risk.",
                source_prd=source_prd,
            ),
            reason_code="quote_conservative_defer",
            sensitive_hit=sensitive_hit,
        )

    if sensitive_hit:
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="defer",
                reason="Sensitive theme detected; auto-policy routes to defer for safety-first handling.",
                source_prd=source_prd,
            ),
            reason_code="sensitive_theme_defer",
            sensitive_hit=True,
        )

    if _contains_any(text, DIAGNOSTIC_PATTERNS) or _contains_any(text, THERAPEUTIC_PROMISE_PATTERNS):
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="rejected",
                reason="Unsafe diagnostic or therapeutic-promise signal detected in advisory metadata.",
                source_prd=source_prd,
            ),
            reason_code="unsafe_diagnostic_or_promise_reject",
            sensitive_hit=sensitive_hit,
        )

    if _contains_any(text, SPIRITUAL_AUTHORITY_PATTERNS):
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="defer",
                reason="Potential spiritual-authority framing detected; conservative defer selected.",
                source_prd=source_prd,
            ),
            reason_code="spiritual_authority_defer",
            sensitive_hit=sensitive_hit,
        )

    if chunk_type == "safety":
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="defer",
                reason="Safety chunk kept in defer to avoid accidental directive interpretation.",
                source_prd=source_prd,
            ),
            reason_code="safety_chunk_defer",
            sensitive_hit=sensitive_hit,
        )

    if (
        chunk_type == "practice"
        or chunk_type == "case"
        or "practice_requires_low_resource_check" in safety_flags
    ):
        edits = _default_practice_edits(summary)
        rejected_fields = sorted(edits.keys())
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="needs_edit",
                reason="Practice/case metadata routed through low-resource guardrail edits before controlled apply.",
                source_prd=source_prd,
                rejected_fields=rejected_fields,
                edited_fields=edits,
            ),
            reason_code="practice_guardrails_needs_edit",
            sensitive_hit=sensitive_hit,
        )

    if not summary or len(summary) < 24 or _contains_any(summary.lower(), GENERIC_SUMMARY_PATTERNS):
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="defer",
                reason="Summary is empty/generic/insufficiently grounded; conservative defer selected.",
                source_prd=source_prd,
            ),
            reason_code="generic_or_insufficient_summary_defer",
            sensitive_hit=sensitive_hit,
        )

    if _contains_any(summary.lower(), DIRECTIVE_PATTERNS):
        edited_summary = sanitize_preview(
            "Нейтральная внутренняя линза без директивной подачи; использовать только как мягкий ориентир для рефлексии.",
            limit=500,
        )
        edits = {"summary": edited_summary}
        return DecisionEnvelope(
            payload=_build_decision(
                review_item_id=review_item_id,
                block_id=block_id,
                decision="needs_edit",
                reason="Directive tone in summary softened via advisory-only rewrite.",
                source_prd=source_prd,
                rejected_fields=["summary"],
                edited_fields=edits,
            ),
            reason_code="directive_summary_needs_edit",
            sensitive_hit=sensitive_hit,
        )

    approved_fields = ["summary"]
    tags = _normalize_tags(item)
    if tags:
        approved_fields.append("tags")

    return DecisionEnvelope(
        payload=_build_decision(
            review_item_id=review_item_id,
            block_id=block_id,
            decision="approved",
            reason="Advisory metadata is sufficiently safe and useful for internal lens usage.",
            source_prd=source_prd,
            approved_fields=approved_fields,
        ),
        reason_code="safe_advisory_approved",
        sensitive_hit=sensitive_hit,
    )



def generate_auto_decisions(
    *,
    queue_payload: dict[str, Any],
    blocks_payload: Any,
    source_prd: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items = build_architect_review_items(queue_payload=queue_payload, blocks_payload=blocks_payload)

    decisions: list[dict[str, Any]] = []
    reason_codes: Counter[str] = Counter()
    by_chunk_type: Counter[str] = Counter()
    by_review_priority: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()

    practice_items_count = 0
    quote_items_count = 0
    sensitive_items_count = 0

    for item in items:
        chunk_type = str(item.get("chunk_type") or "unknown").strip().lower() or "unknown"
        priority = str(item.get("review_priority") or "P2").strip().upper() or "P2"
        by_chunk_type[chunk_type] += 1
        by_review_priority[priority] += 1

        if chunk_type == "practice":
            practice_items_count += 1
        if chunk_type == "quote":
            quote_items_count += 1

        envelope = evaluate_item_policy(item, source_prd=source_prd)
        decisions.append(envelope.payload)
        reason_codes[envelope.reason_code] += 1
        decision_counts[str(envelope.payload.get("decision") or "defer")] += 1
        if envelope.sensitive_hit:
            sensitive_items_count += 1

    samples: dict[str, list[dict[str, Any]]] = {
        "approved": [],
        "needs_edit": [],
        "rejected": [],
        "defer": [],
    }
    for decision in decisions:
        key = str(decision.get("decision") or "defer")
        if key not in samples:
            continue
        if len(samples[key]) >= 2:
            continue
        samples[key].append(
            {
                "review_item_id": decision.get("review_item_id"),
                "block_id": decision.get("block_id"),
                "decision": decision.get("decision"),
                "reason": sanitize_preview(str(decision.get("reason") or ""), limit=180),
                "edited_fields_keys": sorted(list((decision.get("edited_fields") or {}).keys())),
            }
        )

    stats = {
        "policy_version": POLICY_VERSION,
        "items_total": len(decisions),
        "approved_count": int(decision_counts.get("approved", 0)),
        "needs_edit_count": int(decision_counts.get("needs_edit", 0)),
        "rejected_count": int(decision_counts.get("rejected", 0)),
        "defer_count": int(decision_counts.get("defer", 0)),
        "by_chunk_type": dict(sorted(by_chunk_type.items())),
        "by_review_priority": dict(sorted(by_review_priority.items())),
        "by_reason_code": dict(sorted(reason_codes.items())),
        "practice_items_count": int(practice_items_count),
        "quote_items_count": int(quote_items_count),
        "sensitive_items_count": int(sensitive_items_count),
        "samples": samples,
    }
    return decisions, stats
