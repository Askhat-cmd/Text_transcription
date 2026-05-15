from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from knowledge_governance.enrichment_validators import check_forbidden_keys
from tools.kb_quality_audit import load_processed_blocks

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

RUN_TAG = "PRD-046.0.9"
EXPECTED_BLOCKS_COUNT = 247
EXPECTED_SOURCE_ID = "123__кузница_духа"
DEFAULT_BLOCKS_PATH = Path("Bot_data_base/data/processed/all_blocks_merged.json")
DEFAULT_REGISTRY_PATH = Path("Bot_data_base/data/registry.json")
DEFAULT_LOGS_DIR = Path(f"TO_DO_LIST/logs/{RUN_TAG}")
DEFAULT_REPORTS_DIR = Path("TO_DO_LIST/reports")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _safe_preview(text: str, limit: int = 400) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9_]+", str(text or "").lower())


def _source_id(raw: dict[str, Any]) -> str:
    source = str(raw.get("source") or "").strip()
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _block_id(raw: dict[str, Any]) -> str:
    return str(raw.get("id") or raw.get("chunk_id") or "").strip()


def _governance(raw: dict[str, Any]) -> dict[str, Any]:
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    gov = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
    return gov


def _chunking_quality(raw: dict[str, Any]) -> dict[str, Any]:
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    quality = meta.get("chunking_quality") if isinstance(meta.get("chunking_quality"), dict) else {}
    return quality


def _metadata(raw: dict[str, Any]) -> dict[str, Any]:
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return meta


def _looks_like_expected_source(source_ids: list[str]) -> bool:
    if len(source_ids) != 1:
        return False
    value = str(source_ids[0]).lower()
    if value == EXPECTED_SOURCE_ID.lower():
        return True
    return value.startswith("123__") and "кузниц" in value and "дух" in value


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_chroma_count(chroma_reindex_result_path: Path) -> int:
    payload = _load_json(chroma_reindex_result_path, {})
    if isinstance(payload, dict):
        try:
            return int(payload.get("chroma_count_after") or 0)
        except Exception:
            return 0
    return 0


def _read_registry_blocks_count(registry_path: Path, source_ids: list[str]) -> int:
    rows = _load_json(registry_path, [])
    if not isinstance(rows, list):
        return 0
    wanted = {str(x).strip() for x in source_ids if str(x).strip()}
    if not wanted:
        return 0
    candidates = [r for r in rows if isinstance(r, dict) and str(r.get("source_id") or "").strip() in wanted]
    if not candidates:
        return 0
    return max(int(r.get("blocks_count") or 0) for r in candidates)


def evaluate_preflight(
    *,
    blocks_path: Path,
    registry_path: Path,
    chroma_reindex_result_path: Path,
    review_queue_staleness_path: Path,
    review_queue_new_baseline_path: Path,
    retrieval_eval_path: Path,
    legacy_sd_usage_report_path: Path,
) -> dict[str, Any]:
    blocks = load_processed_blocks(blocks_path)
    production_blocks_count = len(blocks)
    active_source_ids = sorted({_source_id(row) for row in blocks if _source_id(row)})
    registry_blocks_count = _read_registry_blocks_count(registry_path, active_source_ids)
    chroma_count = _read_chroma_count(chroma_reindex_result_path)

    staleness_payload = _load_json(review_queue_staleness_path, {})
    old_review_queue_stale = bool(staleness_payload.get("stale")) if isinstance(staleness_payload, dict) else False

    retrieval_payload = _load_json(retrieval_eval_path, {})
    retrieval_eval_status = str(retrieval_payload.get("status") or "missing") if isinstance(retrieval_payload, dict) else "missing"

    legacy_payload = _load_json(legacy_sd_usage_report_path, {})
    legacy_sd_active = bool(legacy_payload.get("legacy_sd_filter_still_active")) if isinstance(legacy_payload, dict) else True

    blockers: list[str] = []
    if production_blocks_count != EXPECTED_BLOCKS_COUNT:
        blockers.append("production_blocks_count_mismatch")
    if registry_blocks_count != EXPECTED_BLOCKS_COUNT:
        blockers.append("registry_blocks_count_mismatch")
    if chroma_count != EXPECTED_BLOCKS_COUNT:
        blockers.append("chroma_count_mismatch")
    if not _looks_like_expected_source(active_source_ids):
        blockers.append("unexpected_active_source_ids")
    if legacy_sd_active:
        blockers.append("legacy_sd_still_active")
    if not old_review_queue_stale:
        blockers.append("old_review_queue_not_stale")
    if not review_queue_new_baseline_path.exists():
        blockers.append("new_review_queue_baseline_missing")
    if retrieval_eval_status != "ok":
        blockers.append("retrieval_eval_not_ok")

    return {
        "schema_version": "post_reprocess_enrichment_preflight_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "passed": not blockers,
        "blockers": blockers,
        "production_blocks_count": production_blocks_count,
        "registry_blocks_count": registry_blocks_count,
        "chroma_count": chroma_count,
        "active_source_ids": active_source_ids,
        "legacy_sd_active": legacy_sd_active,
        "old_review_queue_stale": old_review_queue_stale,
        "new_review_queue_baseline_exists": review_queue_new_baseline_path.exists(),
        "retrieval_eval_status": retrieval_eval_status,
    }


def build_inventory(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in sorted(blocks, key=lambda x: _block_id(x)):
        meta = _metadata(row)
        gov = _governance(row)
        quality = _chunking_quality(row)
        llm_enrichment = meta.get("llm_enrichment") if isinstance(meta.get("llm_enrichment"), dict) else {}
        text = str(row.get("text") or "")
        has_existing = bool(
            str(llm_enrichment.get("summary") or "").strip()
            or _normalize_list(llm_enrichment.get("tags"))
            or _normalize_list(llm_enrichment.get("use_when"))
            or _normalize_list(llm_enrichment.get("avoid_when"))
        )
        reason = "refresh_post_reprocess_boundary_change" if has_existing else "missing_llm_enrichment"
        items.append(
            {
                "block_id": _block_id(row),
                "source_id": _source_id(row),
                "source_title": str(meta.get("source_title") or "").strip(),
                "chunk_type": str(gov.get("chunk_type") or "").strip(),
                "allowed_use": _normalize_list(gov.get("allowed_use")),
                "safety_flags": _normalize_list(gov.get("safety_flags")),
                "lens_family": _normalize_list(gov.get("lens_family")),
                "heading_path": _normalize_list(meta.get("heading_path")),
                "mixed_intent_severity": str(quality.get("mixed_intent_severity") or "none").strip().lower(),
                "chunking_quality": {
                    "boundary_confidence": quality.get("boundary_confidence"),
                    "mixed_intent_risk": bool(quality.get("mixed_intent_risk")),
                    "primary_role": str(quality.get("primary_role") or "").strip(),
                },
                "has_existing_llm_enrichment": has_existing,
                "enrichment_needed_reason": reason,
                "safe_preview": _safe_preview(text, limit=400),
                "raw_text_hash": _sha256_text(text),
            }
        )

    return {
        "schema_version": "post_reprocess_enrichment_inventory_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "blocks_total": len(items),
        "items": items,
    }


def _provider_available() -> bool:
    if OpenAI is None:
        return False
    return bool(str(os.getenv("OPENAI_API_KEY") or "").strip())


def _build_real_prompt(item: dict[str, Any]) -> str:
    return (
        "Сформируй безопасный advisory enrichment JSON без цитирования. "
        "Нельзя менять governance authority и нельзя давать директивные указания. "
        "JSON ключи: summary,tags,lens_family_candidates,use_when,avoid_when,user_state_fit,retrieval_queries,"
        "not_for_direct_quote_reason,writer_guidance,confidence,self_contained_score,needs_human_review,review_reasons. "
        f"Контекст блока: chunk_type={item.get('chunk_type')}, allowed_use={item.get('allowed_use')}, "
        f"safety_flags={item.get('safety_flags')}, preview={item.get('safe_preview')}"
    )


def _call_provider(item: dict[str, Any], model: str, timeout_seconds: float) -> dict[str, Any]:
    if OpenAI is None:
        raise RuntimeError("openai_package_unavailable")
    client = OpenAI(timeout=timeout_seconds)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты возвращаешь только JSON. Без markdown. Без raw full text. Без прямых цитат. "
                    "Фокус на безопасном internal advisory enrichment."
                ),
            },
            {"role": "user", "content": _build_real_prompt(item)},
        ],
    )
    content = str(response.choices[0].message.content or "{}").strip()
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise RuntimeError("provider_response_not_object")
    return parsed


def _empty_advisory() -> dict[str, Any]:
    return {
        "summary": "",
        "tags": [],
        "lens_family_candidates": [],
        "use_when": [],
        "avoid_when": [],
        "user_state_fit": [],
        "retrieval_queries": [],
        "not_for_direct_quote_reason": "",
        "writer_guidance": "",
    }


def _overlay_item_template(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "block_id": item.get("block_id"),
        "source_id": item.get("source_id"),
        "input_text_hash": item.get("raw_text_hash"),
        "chunk_type": item.get("chunk_type"),
        "advisory": _empty_advisory(),
        "quality": {
            "confidence": 0.0,
            "self_contained_score": 0.0,
            "needs_human_review": True,
            "review_reasons": ["missing_real_provider_output"],
        },
    }


def _sanitize_real_advisory(parsed: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    summary = _safe_preview(str(parsed.get("summary") or ""), limit=500)
    tags = _normalize_list(parsed.get("tags"))[:8]
    lens = _normalize_list(parsed.get("lens_family_candidates"))[:6]
    use_when = _normalize_list(parsed.get("use_when"))[:4]
    avoid_when = _normalize_list(parsed.get("avoid_when"))[:4]
    user_state_fit = _normalize_list(parsed.get("user_state_fit"))[:4]
    retrieval_queries = _normalize_list(parsed.get("retrieval_queries"))[:4]

    low_resource_needed = "practice_requires_low_resource_check" in set(_normalize_list(item.get("safety_flags")))
    avoid_joined = " ".join(avoid_when).lower()
    if low_resource_needed and not any(x in avoid_joined for x in ("low resource", "мало сил", "кризис", "нестабил")):
        avoid_when = [*avoid_when, "when low resource, overload, or acute instability is present"][:4]

    confidence = parsed.get("confidence")
    self_contained = parsed.get("self_contained_score")
    try:
        confidence_f = float(confidence)
    except Exception:
        confidence_f = 0.0
    try:
        self_contained_f = float(self_contained)
    except Exception:
        self_contained_f = 0.0

    needs_human_review = bool(parsed.get("needs_human_review"))
    review_reasons = _normalize_list(parsed.get("review_reasons"))
    if not review_reasons:
        if confidence_f < 0.8 or self_contained_f < 0.75:
            review_reasons = ["low_confidence"]
        elif not summary:
            review_reasons = ["summary_missing"]

    return {
        "summary": summary,
        "tags": tags,
        "lens_family_candidates": lens,
        "use_when": use_when,
        "avoid_when": avoid_when,
        "user_state_fit": user_state_fit,
        "retrieval_queries": retrieval_queries,
        "not_for_direct_quote_reason": _safe_preview(str(parsed.get("not_for_direct_quote_reason") or ""), limit=220),
        "writer_guidance": _safe_preview(str(parsed.get("writer_guidance") or ""), limit=320),
        "quality": {
            "confidence": max(0.0, min(1.0, confidence_f)),
            "self_contained_score": max(0.0, min(1.0, self_contained_f)),
            "needs_human_review": needs_human_review,
            "review_reasons": review_reasons,
        },
    }


def generate_overlay(
    *,
    inventory: dict[str, Any],
    mode: str,
    overlay_path_for_validation: Path | None,
    batch_size: int,
    resume: bool,
    model: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    items = inventory.get("items") if isinstance(inventory.get("items"), list) else []
    provider_status = "not_requested"

    if mode == "validate-existing":
        if overlay_path_for_validation is None or not overlay_path_for_validation.exists():
            raise RuntimeError("validate-existing requires existing --overlay-input")
        overlay = _load_json(overlay_path_for_validation, {})
        if not isinstance(overlay, dict):
            raise RuntimeError("overlay_input_invalid")
        return overlay, {"provider_status": "not_called", "mode": mode}

    overlay_items: list[dict[str, Any]] = []
    existing_by_id: dict[str, dict[str, Any]] = {}
    if resume and overlay_path_for_validation and overlay_path_for_validation.exists():
        existing = _load_json(overlay_path_for_validation, {})
        if isinstance(existing, dict) and isinstance(existing.get("items"), list):
            for row in existing.get("items", []):
                if isinstance(row, dict) and str(row.get("block_id") or ""):
                    existing_by_id[str(row.get("block_id"))] = row

    if mode == "dry-run":
        provider_status = "not_called"
        for item in items:
            overlay_items.append(_overlay_item_template(item))

    elif mode == "real":
        if not _provider_available():
            provider_status = "provider_unavailable"
            for item in items:
                row = _overlay_item_template(item)
                row["quality"]["review_reasons"] = ["provider_unavailable"]
                overlay_items.append(row)
        else:
            provider_status = "ok"
            for index, item in enumerate(items):
                block_id = str(item.get("block_id") or "")
                if block_id in existing_by_id and str(existing_by_id[block_id].get("input_text_hash") or "") == str(item.get("raw_text_hash") or ""):
                    overlay_items.append(existing_by_id[block_id])
                    continue

                base = _overlay_item_template(item)
                try:
                    parsed = _call_provider(item, model=model, timeout_seconds=timeout_seconds)
                    advisory = _sanitize_real_advisory(parsed, item)
                    base["advisory"] = {
                        "summary": advisory["summary"],
                        "tags": advisory["tags"],
                        "lens_family_candidates": advisory["lens_family_candidates"],
                        "use_when": advisory["use_when"],
                        "avoid_when": advisory["avoid_when"],
                        "user_state_fit": advisory["user_state_fit"],
                        "retrieval_queries": advisory["retrieval_queries"],
                        "not_for_direct_quote_reason": advisory["not_for_direct_quote_reason"],
                        "writer_guidance": advisory["writer_guidance"],
                    }
                    base["quality"] = advisory["quality"]
                except Exception as exc:
                    base["quality"]["review_reasons"] = [f"provider_error:{type(exc).__name__}"]
                overlay_items.append(base)

                if (index + 1) % max(1, batch_size) == 0:
                    partial_payload = {
                        "schema_version": "post_reprocess_llm_enrichment_overlay_v1",
                        "source_prd": RUN_TAG,
                        "generated_at": _utc_now(),
                        "source_blocks_count": len(items),
                        "items": overlay_items,
                    }
                    if overlay_path_for_validation:
                        _write_json(overlay_path_for_validation, partial_payload)
    else:
        raise RuntimeError(f"unsupported_mode:{mode}")

    payload = {
        "schema_version": "post_reprocess_llm_enrichment_overlay_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "source_blocks_count": len(items),
        "items": overlay_items,
    }
    return payload, {"provider_status": provider_status, "mode": mode}


def _is_direct_quote_risk(summary: str, source_preview: str) -> bool:
    normalized = " ".join(str(summary or "").split())
    preview = " ".join(str(source_preview or "").split())
    if len(normalized) < 90:
        return False
    return normalized[:80] in preview


def validate_overlay(
    *,
    overlay: dict[str, Any],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    inv_items = inventory.get("items") if isinstance(inventory.get("items"), list) else []
    overlay_items = overlay.get("items") if isinstance(overlay.get("items"), list) else []

    inv_by_id = {str(x.get("block_id") or ""): x for x in inv_items if str(x.get("block_id") or "")}
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if len(overlay_items) != len(inv_items):
        errors.append({"code": "item_count_mismatch", "expected": len(inv_items), "actual": len(overlay_items)})

    forbidden_hits = check_forbidden_keys(overlay)
    if forbidden_hits:
        errors.append({"code": "forbidden_keys_detected", "keys": sorted(set(forbidden_hits))})

    diagnosis_re = re.compile(r"\b(диагноз|биполяр|расстройство личности|клиническая депрессия)\b", re.IGNORECASE)
    directive_re = re.compile(r"\b(ты должен|вы должны|обязательно сделай|немедленно сделай)\b", re.IGNORECASE)
    spiritual_re = re.compile(r"\b(единственно верный путь|высшая истина|духовный закон требует)\b", re.IGNORECASE)
    bypass_help_re = re.compile(r"\b(не обращайся к врачу|не нужна помощь специалистов|обойдись без психолога)\b", re.IGNORECASE)

    low_resource_terms = ("low resource", "мало сил", "кризис", "нестабил")

    seen_ids: set[str] = set()
    for row in overlay_items:
        if not isinstance(row, dict):
            errors.append({"code": "overlay_item_not_object"})
            continue
        block_id = str(row.get("block_id") or "")
        if not block_id:
            errors.append({"code": "missing_block_id"})
            continue
        if block_id in seen_ids:
            errors.append({"code": "duplicate_block_id", "block_id": block_id})
        seen_ids.add(block_id)

        inv = inv_by_id.get(block_id)
        if inv is None:
            errors.append({"code": "unknown_block_id", "block_id": block_id})
            continue

        if str(row.get("input_text_hash") or "") != str(inv.get("raw_text_hash") or ""):
            errors.append({"code": "input_text_hash_mismatch", "block_id": block_id})

        advisory = row.get("advisory") if isinstance(row.get("advisory"), dict) else {}
        quality = row.get("quality") if isinstance(row.get("quality"), dict) else {}

        summary = str(advisory.get("summary") or "").strip()
        if summary and len(summary) > 500:
            errors.append({"code": "summary_too_long", "block_id": block_id, "length": len(summary)})
        if summary and _is_direct_quote_risk(summary, str(inv.get("safe_preview") or "")):
            warnings.append({"code": "summary_direct_quote_risk", "block_id": block_id})
        if diagnosis_re.search(summary):
            errors.append({"code": "clinical_diagnosis_claim", "block_id": block_id})
        if directive_re.search(summary):
            errors.append({"code": "directive_life_advice", "block_id": block_id})
        if spiritual_re.search(summary):
            errors.append({"code": "unsafe_spiritual_authority", "block_id": block_id})
        if bypass_help_re.search(summary):
            errors.append({"code": "bypass_professional_help", "block_id": block_id})

        for forbidden_field in ("allowed_use", "safety_flags", "chunk_type", "governance"):
            if forbidden_field in advisory:
                errors.append({"code": "governance_authority_mutation_attempt", "block_id": block_id, "field": forbidden_field})

        avoid_when = _normalize_list(advisory.get("avoid_when"))
        use_when = _normalize_list(advisory.get("use_when"))
        if not use_when:
            warnings.append({"code": "missing_use_when", "block_id": block_id})
        if not avoid_when:
            warnings.append({"code": "missing_avoid_when", "block_id": block_id})

        safety_flags = set(_normalize_list(inv.get("safety_flags")))
        need_low_resource = "practice_requires_low_resource_check" in safety_flags
        avoid_joined = " ".join(avoid_when).lower()
        if need_low_resource and not any(term in avoid_joined for term in low_resource_terms):
            warnings.append({"code": "low_resource_avoid_when_missing", "block_id": block_id})

        confidence = quality.get("confidence")
        self_score = quality.get("self_contained_score")
        try:
            confidence_f = float(confidence)
            if confidence_f < 0.0 or confidence_f > 1.0:
                raise ValueError("out_of_range")
        except Exception:
            errors.append({"code": "invalid_confidence", "block_id": block_id})
        try:
            self_score_f = float(self_score)
            if self_score_f < 0.0 or self_score_f > 1.0:
                raise ValueError("out_of_range")
        except Exception:
            errors.append({"code": "invalid_self_contained_score", "block_id": block_id})

        if not isinstance(quality.get("needs_human_review"), bool):
            errors.append({"code": "missing_review_status", "block_id": block_id})

    return {
        "schema_version": "post_reprocess_enrichment_validation_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "expected_items": len(inv_items),
        "overlay_items": len(overlay_items),
        "errors": errors,
        "warnings": warnings,
        "validation_errors_count": len(errors),
        "validation_warnings_count": len(warnings),
        "passed": len(errors) == 0,
        "raw_full_text_leak_detected": any(e.get("code") == "forbidden_keys_detected" for e in errors),
        "governance_authority_mutated": any(e.get("code") == "governance_authority_mutation_attempt" for e in errors),
    }


def build_review_queue_rebaseline(
    *,
    overlay: dict[str, Any],
    inventory: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    inv_by_id = {str(x.get("block_id") or ""): x for x in (inventory.get("items") or []) if isinstance(x, dict)}
    warning_map: dict[str, list[str]] = {}
    for row in validation.get("warnings") or []:
        if not isinstance(row, dict):
            continue
        bid = str(row.get("block_id") or "")
        if not bid:
            continue
        warning_map.setdefault(bid, []).append(str(row.get("code") or "warning"))

    queue_items: list[dict[str, Any]] = []
    for row in overlay.get("items") or []:
        if not isinstance(row, dict):
            continue
        block_id = str(row.get("block_id") or "")
        inv = inv_by_id.get(block_id)
        if inv is None:
            continue

        advisory = row.get("advisory") if isinstance(row.get("advisory"), dict) else {}
        quality = row.get("quality") if isinstance(row.get("quality"), dict) else {}

        summary = str(advisory.get("summary") or "").strip()
        use_when = _normalize_list(advisory.get("use_when"))
        avoid_when = _normalize_list(advisory.get("avoid_when"))
        lens = _normalize_list(advisory.get("lens_family_candidates"))
        review_reasons = _normalize_list(quality.get("review_reasons"))
        confidence = float(quality.get("confidence") or 0.0)
        self_score = float(quality.get("self_contained_score") or 0.0)
        needs_review = bool(quality.get("needs_human_review"))

        auto_reasons: list[str] = []
        if needs_review:
            auto_reasons.append("needs_human_review")
        if confidence < 0.75:
            auto_reasons.append("low_confidence")
        if self_score < 0.75:
            auto_reasons.append("low_self_contained_score")
        if not summary:
            auto_reasons.append("missing_summary")
        if len(use_when) < 1:
            auto_reasons.append("generic_or_missing_use_when")
        if len(avoid_when) < 1:
            auto_reasons.append("generic_or_missing_avoid_when")
        if not lens:
            auto_reasons.append("lens_family_uncertain")
        if str(inv.get("chunk_type") or "") in {"practice", "case", "quote"} and len(lens) < 1:
            auto_reasons.append("practice_case_quote_ambiguity")
        if "source_style_not_user_facing" in set(_normalize_list(inv.get("safety_flags"))):
            auto_reasons.append("possible_source_style_user_facing_risk")

        auto_reasons.extend(warning_map.get(block_id, []))
        merged_reasons = sorted(set(review_reasons + auto_reasons))
        if not merged_reasons:
            continue

        priority = "P2"
        if "low_confidence" in merged_reasons or "low_self_contained_score" in merged_reasons:
            priority = "P1"
        if "provider_unavailable" in merged_reasons or "missing_summary" in merged_reasons:
            priority = "P0"

        queue_items.append(
            {
                "review_item_id": f"post_reprocess::{block_id}",
                "block_id": block_id,
                "source_id": inv.get("source_id"),
                "source_title": inv.get("source_title"),
                "chunk_type": inv.get("chunk_type"),
                "review_priority": priority,
                "review_reasons": merged_reasons,
                "recommended_action": "needs_edit" if priority in {"P0", "P1"} else "defer",
                "safe_preview": inv.get("safe_preview"),
                "advisory_summary_preview": _safe_preview(summary, limit=220),
            }
        )

    queue_items.sort(key=lambda x: (x.get("review_priority", "P2"), x.get("review_item_id", "")))
    p0 = sum(1 for x in queue_items if x.get("review_priority") == "P0")
    p1 = sum(1 for x in queue_items if x.get("review_priority") == "P1")
    p2 = sum(1 for x in queue_items if x.get("review_priority") == "P2")

    return {
        "schema_version": "post_reprocess_review_queue_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "review_items_count": len(queue_items),
        "priority_counts": {"P0": p0, "P1": p1, "P2": p2},
        "items": queue_items,
    }


def build_scorecard(
    *,
    overlay: dict[str, Any],
    validation: dict[str, Any],
    review_queue: dict[str, Any],
) -> dict[str, Any]:
    items = overlay.get("items") if isinstance(overlay.get("items"), list) else []
    total = len(items)
    confidences: list[float] = []
    self_scores: list[float] = []
    summary_count = 0
    tags_count = 0
    use_when_count = 0
    avoid_when_count = 0
    lens_count = 0
    needs_human_count = 0

    for row in items:
        if not isinstance(row, dict):
            continue
        advisory = row.get("advisory") if isinstance(row.get("advisory"), dict) else {}
        quality = row.get("quality") if isinstance(row.get("quality"), dict) else {}
        if str(advisory.get("summary") or "").strip():
            summary_count += 1
        if _normalize_list(advisory.get("tags")):
            tags_count += 1
        if _normalize_list(advisory.get("use_when")):
            use_when_count += 1
        if _normalize_list(advisory.get("avoid_when")):
            avoid_when_count += 1
        if _normalize_list(advisory.get("lens_family_candidates")):
            lens_count += 1
        if bool(quality.get("needs_human_review")):
            needs_human_count += 1
        try:
            confidences.append(float(quality.get("confidence") or 0.0))
        except Exception:
            confidences.append(0.0)
        try:
            self_scores.append(float(quality.get("self_contained_score") or 0.0))
        except Exception:
            self_scores.append(0.0)

    avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
    avg_self = (sum(self_scores) / len(self_scores)) if self_scores else 0.0

    def _rate(count: int) -> float:
        if total <= 0:
            return 0.0
        return round(count / total, 4)

    return {
        "schema_version": "post_reprocess_enrichment_scorecard_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "blocks_total": total,
        "enrichment_items_total": total,
        "validated_items_total": total,
        "validation_errors_count": int(validation.get("validation_errors_count") or 0),
        "validation_warnings_count": int(validation.get("validation_warnings_count") or 0),
        "needs_human_review_count": needs_human_count,
        "review_queue_items_count": int(review_queue.get("review_items_count") or 0),
        "avg_confidence": round(avg_confidence, 4),
        "avg_self_contained_score": round(avg_self, 4),
        "summary_present_rate": _rate(summary_count),
        "tags_present_rate": _rate(tags_count),
        "use_when_present_rate": _rate(use_when_count),
        "avoid_when_present_rate": _rate(avoid_when_count),
        "lens_family_candidates_present_rate": _rate(lens_count),
        "raw_full_text_leak_detected": bool(validation.get("raw_full_text_leak_detected")),
        "governance_authority_mutated": bool(validation.get("governance_authority_mutated")),
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
    }


def build_retrieval_preview(
    *,
    overlay: dict[str, Any],
    retrieval_eval_after_reprocess_path: Path,
) -> dict[str, Any]:
    overlay_items = overlay.get("items") if isinstance(overlay.get("items"), list) else []
    overlay_by_id = {
        str(x.get("block_id") or ""): x
        for x in overlay_items
        if isinstance(x, dict) and str(x.get("block_id") or "")
    }

    payload = _load_json(retrieval_eval_after_reprocess_path, {})
    cases = (((payload.get("results") or {}).get("cases")) if isinstance(payload, dict) else []) or []

    queries_total = 0
    queries_ok = 0
    top_k_before_summary_available = 0
    top_k_overlay_summary_available = 0
    useful = 0
    noise = 0
    examples: list[dict[str, Any]] = []

    for case in cases:
        if not isinstance(case, dict):
            continue
        queries_total += 1
        if str(case.get("status") or "") == "ok":
            queries_ok += 1

        query = str(case.get("query") or "")
        query_tokens = set(_tokenize(query))
        for hit in case.get("top_hits") or []:
            if not isinstance(hit, dict):
                continue
            block_id = str(hit.get("id") or "")
            if not block_id:
                continue

            before_summary = str(hit.get("llm_enrichment_summary") or "").strip()
            if before_summary:
                top_k_before_summary_available += 1

            overlay_item = overlay_by_id.get(block_id)
            if overlay_item is None:
                continue
            advisory = overlay_item.get("advisory") if isinstance(overlay_item.get("advisory"), dict) else {}
            summary = str(advisory.get("summary") or "").strip()
            if not summary:
                continue

            top_k_overlay_summary_available += 1
            evidence_text = " ".join(
                [
                    summary,
                    " ".join(_normalize_list(advisory.get("tags"))),
                    " ".join(_normalize_list(advisory.get("use_when"))),
                ]
            )
            overlap = query_tokens.intersection(set(_tokenize(evidence_text)))
            if overlap:
                useful += 1
            else:
                noise += 1

            if len(examples) < 5:
                examples.append(
                    {
                        "case_id": case.get("id"),
                        "query_preview": _safe_preview(query, limit=180),
                        "block_id": block_id,
                        "overlay_summary_preview": _safe_preview(summary, limit=180),
                        "overlap_terms": sorted(list(overlap))[:8],
                    }
                )

    return {
        "schema_version": "post_reprocess_enrichment_retrieval_preview_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "queries_total": queries_total,
        "queries_ok": queries_ok,
        "top_k_before_summary_available": top_k_before_summary_available,
        "top_k_overlay_summary_available": top_k_overlay_summary_available,
        "overlay_candidate_useful_count": useful,
        "overlay_candidate_noise_count": noise,
        "examples": examples,
    }


def _write_reports(
    *,
    reports_dir: Path,
    mode: str,
    provider_status: str,
    preflight: dict[str, Any],
    inventory: dict[str, Any],
    validation: dict[str, Any],
    review_queue: dict[str, Any],
    scorecard: dict[str, Any],
    retrieval_preview: dict[str, Any],
    no_mutation: dict[str, Any],
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)

    impl_status = "done" if provider_status in {"ok", "not_called"} else "blocked_by_provider"
    next_prd = "PRD-046.0.9.1"
    if provider_status == "provider_unavailable":
        next_prd = "PRD-046.0.9-RUN1"
    elif int(review_queue.get("review_items_count") or 0) == 0:
        next_prd = "PRD-046.0.9.2"

    impl_path = reports_dir / "PRD-046.0.9_IMPLEMENTATION_REPORT.md"
    impl_lines = [
        "# PRD-046.0.9 IMPLEMENTATION REPORT",
        "",
        "## Status",
        f"- Implementation: {impl_status}",
        "- Branch: `main`",
        "- Runtime behavior changed: false",
        "- Writer changed: false",
        "- DiagnosticCard changed: false",
        "- Thread Manager changed: false",
        "- State Analyzer changed: false",
        "- Context Assembly changed: false",
        "- Production knowledge blocks mutated: false",
        "- Registry mutated: false",
        "- Chroma reindex performed: false",
        "- Production enrichment apply performed: false",
        "",
        "## Preflight",
        f"- passed: `{preflight.get('passed')}`",
        f"- production_blocks_count: `{preflight.get('production_blocks_count')}`",
        f"- registry_blocks_count: `{preflight.get('registry_blocks_count')}`",
        f"- chroma_count: `{preflight.get('chroma_count')}`",
        f"- active_source_ids: `{preflight.get('active_source_ids')}`",
        f"- old_review_queue_stale: `{preflight.get('old_review_queue_stale')}`",
        f"- retrieval_eval_status: `{preflight.get('retrieval_eval_status')}`",
        "",
        "## Enrichment",
        f"- mode: `{mode}`",
        f"- provider_status: `{provider_status}`",
        f"- blocks_total: `{inventory.get('blocks_total')}`",
        f"- enrichment_items_total: `{scorecard.get('enrichment_items_total')}`",
        f"- validated_items_total: `{scorecard.get('validated_items_total')}`",
        f"- validation_errors_count: `{scorecard.get('validation_errors_count')}`",
        f"- validation_warnings_count: `{scorecard.get('validation_warnings_count')}`",
        f"- raw_full_text_leak_detected: `{scorecard.get('raw_full_text_leak_detected')}`",
        "",
        "## Review Queue",
        f"- review_queue_items_count: `{review_queue.get('review_items_count')}`",
        f"- P0: `{(review_queue.get('priority_counts') or {}).get('P0', 0)}`",
        f"- P1: `{(review_queue.get('priority_counts') or {}).get('P1', 0)}`",
        f"- P2: `{(review_queue.get('priority_counts') or {}).get('P2', 0)}`",
        "",
        "## Scorecard",
        f"- avg_confidence: `{scorecard.get('avg_confidence')}`",
        f"- avg_self_contained_score: `{scorecard.get('avg_self_contained_score')}`",
        f"- summary_present_rate: `{scorecard.get('summary_present_rate')}`",
        f"- tags_present_rate: `{scorecard.get('tags_present_rate')}`",
        f"- use_when_present_rate: `{scorecard.get('use_when_present_rate')}`",
        f"- avoid_when_present_rate: `{scorecard.get('avoid_when_present_rate')}`",
        f"- lens_family_candidates_present_rate: `{scorecard.get('lens_family_candidates_present_rate')}`",
        "",
        "## No Mutation",
        f"- all_blocks_merged_mutated: `{no_mutation.get('all_blocks_merged_mutated')}`",
        f"- registry_mutated: `{no_mutation.get('registry_mutated')}`",
        f"- chroma_mutated: `{no_mutation.get('chroma_mutated')}`",
        "",
        "## Tests",
        "- summary: see `TO_DO_LIST/logs/PRD-046.0.9/test_command_output.txt`",
        "",
        "## Commit / Push",
        "- Commit hash: `pending`",
        "- Push status: `pending`",
        "- Report sync: `pending`",
    ]
    impl_path.write_text("\n".join(impl_lines) + "\n", encoding="utf-8")

    preflight_path = reports_dir / "PRD-046.0.9_PREFLIGHT_REPORT.md"
    preflight_path.write_text(
        "\n".join(
            [
                "# PRD-046.0.9 PREFLIGHT REPORT",
                "",
                f"- passed: `{preflight.get('passed')}`",
                f"- blockers: `{preflight.get('blockers')}`",
                f"- production_blocks_count: `{preflight.get('production_blocks_count')}`",
                f"- registry_blocks_count: `{preflight.get('registry_blocks_count')}`",
                f"- chroma_count: `{preflight.get('chroma_count')}`",
                f"- active_source_ids: `{preflight.get('active_source_ids')}`",
                f"- retrieval_eval_status: `{preflight.get('retrieval_eval_status')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    inventory_path = reports_dir / "PRD-046.0.9_ENRICHMENT_INVENTORY_REPORT.md"
    inventory_path.write_text(
        "\n".join(
            [
                "# PRD-046.0.9 ENRICHMENT INVENTORY REPORT",
                "",
                f"- blocks_total: `{inventory.get('blocks_total')}`",
                f"- sample_first_block: `{((inventory.get('items') or [{}])[0]).get('block_id', '') if inventory.get('items') else ''}`",
                "- raw full text persisted: `false`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    validation_path = reports_dir / "PRD-046.0.9_ENRICHMENT_VALIDATION_REPORT.md"
    validation_path.write_text(
        "\n".join(
            [
                "# PRD-046.0.9 ENRICHMENT VALIDATION REPORT",
                "",
                f"- passed: `{validation.get('passed')}`",
                f"- validation_errors_count: `{validation.get('validation_errors_count')}`",
                f"- validation_warnings_count: `{validation.get('validation_warnings_count')}`",
                f"- raw_full_text_leak_detected: `{validation.get('raw_full_text_leak_detected')}`",
                f"- governance_authority_mutated: `{validation.get('governance_authority_mutated')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    queue_path = reports_dir / "PRD-046.0.9_REVIEW_QUEUE_REBASELINE_REPORT.md"
    queue_path.write_text(
        "\n".join(
            [
                "# PRD-046.0.9 REVIEW QUEUE REBASELINE REPORT",
                "",
                f"- review_queue_items_count: `{review_queue.get('review_items_count')}`",
                f"- priority_counts: `{review_queue.get('priority_counts')}`",
                "- stale PRD-046.0.7 queue reused: `false`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    preview_path = reports_dir / "PRD-046.0.9_ENRICHMENT_RETRIEVAL_PREVIEW_REPORT.md"
    preview_path.write_text(
        "\n".join(
            [
                "# PRD-046.0.9 ENRICHMENT RETRIEVAL PREVIEW REPORT",
                "",
                f"- queries_total: `{retrieval_preview.get('queries_total')}`",
                f"- queries_ok: `{retrieval_preview.get('queries_ok')}`",
                f"- top_k_before_summary_available: `{retrieval_preview.get('top_k_before_summary_available')}`",
                f"- top_k_overlay_summary_available: `{retrieval_preview.get('top_k_overlay_summary_available')}`",
                f"- overlay_candidate_useful_count: `{retrieval_preview.get('overlay_candidate_useful_count')}`",
                f"- overlay_candidate_noise_count: `{retrieval_preview.get('overlay_candidate_noise_count')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    next_path = reports_dir / "PRD-046.0.9_NEXT_PRD_RECOMMENDATION.md"
    next_path.write_text(
        "\n".join(
            [
                "# PRD-046.0.9 NEXT PRD RECOMMENDATION",
                "",
                f"- Recommended: `{next_prd}`",
                f"- provider_status: `{provider_status}`",
                f"- review_queue_items_count: `{review_queue.get('review_items_count')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_post_reprocess_enrichment(
    *,
    mode: str,
    blocks_path: Path,
    registry_path: Path,
    logs_dir: Path,
    reports_dir: Path,
    overlay_input_path: Path | None,
    batch_size: int,
    resume: bool,
    model: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    logs_dir.mkdir(parents=True, exist_ok=True)

    all_blocks_before = _sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_before = _sha256_file(registry_path) if registry_path.exists() else ""

    preflight = evaluate_preflight(
        blocks_path=blocks_path,
        registry_path=registry_path,
        chroma_reindex_result_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/chroma_reindex_result.json"),
        review_queue_staleness_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/review_queue_staleness_report.json"),
        review_queue_new_baseline_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/review_queue_new_baseline.json"),
        retrieval_eval_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/retrieval_eval_after_reprocess.json"),
        legacy_sd_usage_report_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/post_apply_legacy_sd_usage_report.json"),
    )
    _write_json(logs_dir / "enrichment_preflight.json", preflight)

    if not preflight.get("passed"):
        result = {
            "status": "blocked",
            "reason": "preflight_failed",
            "blockers": preflight.get("blockers", []),
        }
        _write_json(logs_dir / "run_result.json", result)
        return result

    blocks = load_processed_blocks(blocks_path)
    inventory = build_inventory(blocks)
    _write_json(logs_dir / "enrichment_inventory.json", inventory)

    overlay_output_path = logs_dir / "enrichment_candidate_overlay.json"
    overlay, overlay_meta = generate_overlay(
        inventory=inventory,
        mode=mode,
        overlay_path_for_validation=overlay_input_path if mode == "validate-existing" else overlay_output_path,
        batch_size=max(1, int(batch_size)),
        resume=resume,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    _write_json(overlay_output_path, overlay)

    validation = validate_overlay(overlay=overlay, inventory=inventory)
    _write_json(logs_dir / "enrichment_validation.json", validation)

    review_queue = build_review_queue_rebaseline(overlay=overlay, inventory=inventory, validation=validation)
    _write_json(logs_dir / "review_queue_rebaseline.json", review_queue)

    scorecard = build_scorecard(overlay=overlay, validation=validation, review_queue=review_queue)
    _write_json(logs_dir / "enrichment_scorecard.json", scorecard)

    retrieval_preview = build_retrieval_preview(
        overlay=overlay,
        retrieval_eval_after_reprocess_path=Path("TO_DO_LIST/logs/PRD-046.0.8.1/retrieval_eval_after_reprocess.json"),
    )
    _write_json(logs_dir / "enrichment_retrieval_preview.json", retrieval_preview)

    all_blocks_after = _sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_after = _sha256_file(registry_path) if registry_path.exists() else ""

    no_mutation = {
        "schema_version": "post_reprocess_no_mutation_check_v1",
        "source_prd": RUN_TAG,
        "generated_at": _utc_now(),
        "all_blocks_merged_mutated": all_blocks_before != all_blocks_after,
        "registry_mutated": registry_before != registry_after,
        "chroma_mutated": False,
        "all_blocks_sha_before": all_blocks_before,
        "all_blocks_sha_after": all_blocks_after,
        "registry_sha_before": registry_before,
        "registry_sha_after": registry_after,
    }
    _write_json(logs_dir / "no_mutation_check.json", no_mutation)

    _write_reports(
        reports_dir=reports_dir,
        mode=mode,
        provider_status=str(overlay_meta.get("provider_status") or "unknown"),
        preflight=preflight,
        inventory=inventory,
        validation=validation,
        review_queue=review_queue,
        scorecard=scorecard,
        retrieval_preview=retrieval_preview,
        no_mutation=no_mutation,
    )

    runtime_lines = [
        f"[{_utc_now()}] {RUN_TAG} post-reprocess enrichment run",
        f"mode={mode}",
        f"provider_status={overlay_meta.get('provider_status')}",
        f"production_blocks_mutated={no_mutation.get('all_blocks_merged_mutated')}",
        f"registry_mutated={no_mutation.get('registry_mutated')}",
        "chroma_reindex_performed=false",
        "production_apply_performed=false",
    ]
    (logs_dir / "sanitized_runtime_logs.txt").write_text("\n".join(runtime_lines) + "\n", encoding="utf-8")

    status = "done"
    if str(overlay_meta.get("provider_status")) == "provider_unavailable":
        status = "blocked_by_provider"

    return {
        "status": status,
        "mode": mode,
        "provider_status": overlay_meta.get("provider_status"),
        "preflight_passed": preflight.get("passed"),
        "blocks_total": inventory.get("blocks_total"),
        "validation_errors_count": validation.get("validation_errors_count"),
        "review_queue_items_count": review_queue.get("review_items_count"),
        "scorecard_path": str((logs_dir / "enrichment_scorecard.json").as_posix()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.9 post-reprocess enrichment + review rebaseline tool.")
    parser.add_argument("--mode", choices=["dry-run", "real", "validate-existing"], default="dry-run")
    parser.add_argument("--blocks-path", default=str(DEFAULT_BLOCKS_PATH))
    parser.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--overlay-input", default="")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    result = run_post_reprocess_enrichment(
        mode=str(args.mode),
        blocks_path=Path(args.blocks_path),
        registry_path=Path(args.registry_path),
        logs_dir=Path(args.logs_dir),
        reports_dir=Path(args.reports_dir),
        overlay_input_path=Path(args.overlay_input) if str(args.overlay_input).strip() else None,
        batch_size=max(1, int(args.batch_size)),
        resume=bool(args.resume),
        model=str(args.model),
        timeout_seconds=max(1.0, float(args.timeout_seconds)),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"done", "blocked_by_provider"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
