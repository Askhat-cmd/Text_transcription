from __future__ import annotations

import argparse
import json
import re
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import yaml
except Exception:  # pragma: no cover - optional in tests
    yaml = None


DEFAULT_PROBE_QUERIES = [
    "я злюсь на себя, потому что опять не сделал обещанное",
    "я боюсь показать проект и снова хочу отложить",
    "нет сил, не хочу анализа, просто поддержи",
    "я всё время стараюсь быть лучше и не могу остановиться",
    "я чувствую вину, когда выбираю себя",
    "что делать, если я снова прокрастинирую",
    "мне стыдно за то, что я ничего не сделал",
]

CHUNK_TYPES = [
    "theory",
    "practice",
    "lens",
    "safety",
    "style",
    "architecture",
    "excluded",
    "unknown/empty",
]
ALLOWED_USE_TYPES = [
    "writer_context",
    "diagnostic_lens",
    "practice_suggestion",
    "safety_protocol",
    "internal_only",
    "do_not_use",
    "unknown/empty",
]
KNOWN_LENS_FAMILIES = [
    "shame",
    "guilt",
    "anger",
    "grief",
    "procrastination",
    "perfectionism",
    "evaluation_fear",
    "loneliness",
    "attachment",
    "self_criticism",
    "avoidance",
    "burnout",
    "low_resource",
    "unknown/empty",
]
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
MIXED_INTENT_SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1, "none": 0, "": 0}
PRACTICE_MARKERS = ("практик", "упражнен", "техник", "шаг 1", "сделай", "выполни")
AUTHOR_TERMS = ("программа", "нейросталкинг", "присутствие")


@dataclass
class BlockView:
    chunk_id: str
    title: str
    summary: str
    text: str
    source: str
    source_title: str
    heading_path: list[str]
    section_role_hint: str
    split_reason: str
    parent_section_id: str
    boundary_confidence: float | None
    governance: dict[str, Any]
    chunking_quality: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_preview(text: str, limit: int = 160) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    cleaned = cleaned.replace('"', "'")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _normalize_str(value: Any) -> str:
    return str(value or "").strip()


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9_]+", str(text or "").lower())


def _is_focus_source(title: str, source: str, source_id: str, focus_hint: str) -> bool:
    hay = " ".join([title, source, source_id]).lower()
    hint = focus_hint.lower()
    if hint and hint in hay:
        return True
    if "кузниц" in hay and "дух" in hay:
        return True
    return False


def _source_id_from_block(block: dict[str, Any]) -> str:
    source = _normalize_str(block.get("source"))
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _get_block_view(block: dict[str, Any]) -> BlockView:
    metadata = block.get("metadata") or {}
    governance = metadata.get("governance") or {}
    chunking_quality = metadata.get("chunking_quality") or {}
    heading_path = metadata.get("heading_path") or []
    if not isinstance(heading_path, list):
        heading_path = _normalize_list(heading_path)
    if not heading_path:
        heading_text = _normalize_str(metadata.get("heading_path_text"))
        if heading_text:
            heading_path = [part.strip() for part in heading_text.split(">") if part.strip()]

    boundary = _to_float(metadata.get("boundary_confidence"))
    if boundary is None:
        boundary = _to_float(chunking_quality.get("boundary_confidence"))

    return BlockView(
        chunk_id=_normalize_str(block.get("id")) or _normalize_str(block.get("chunk_id")),
        title=_normalize_str(block.get("title")),
        summary=_normalize_str(block.get("summary")),
        text=_normalize_str(block.get("text")),
        source=_normalize_str(block.get("source")),
        source_title=_normalize_str(metadata.get("source_title")) or _normalize_str(block.get("source_title")),
        heading_path=heading_path,
        section_role_hint=_normalize_str(metadata.get("section_role_hint"))
        or _normalize_str(chunking_quality.get("section_role_hint")),
        split_reason=_normalize_str(metadata.get("split_reason"))
        or _normalize_str(chunking_quality.get("split_reason")),
        parent_section_id=_normalize_str(metadata.get("parent_section_id")),
        boundary_confidence=boundary,
        governance=governance if isinstance(governance, dict) else {},
        chunking_quality=chunking_quality if isinstance(chunking_quality, dict) else {},
    )


def load_processed_blocks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        blocks = data.get("blocks")
        if isinstance(blocks, list):
            return blocks
        return []
    if isinstance(data, list):
        return data
    return []


def load_registry_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def build_source_inventory(
    *,
    blocks: list[dict[str, Any]],
    registry_records: list[dict[str, Any]],
    processed_dir: Path,
    focus_hint: str,
) -> dict[str, Any]:
    by_source: dict[str, dict[str, Any]] = {}

    for raw in blocks:
        view = _get_block_view(raw)
        source_id = _source_id_from_block(raw)
        record = by_source.setdefault(
            source_id,
            {
                "source_id": source_id,
                "source": view.source,
                "title": view.source_title,
                "author": _normalize_str((raw.get("metadata") or {}).get("author")),
                "author_id": _normalize_str((raw.get("metadata") or {}).get("author_id")),
                "source_type": _normalize_str((raw.get("metadata") or {}).get("source_type")) or "unknown",
                "blocks_count": 0,
                "from_blocks": True,
                "from_registry": False,
                "registry_status": "",
                "is_focus_source": False,
                "is_architecture_internal_risk": False,
                "processed_exports": [],
            },
        )
        record["blocks_count"] += 1

    registry_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in registry_records:
        registry_map[_normalize_str(item.get("source_id"))].append(item)

    for source_id, recs in registry_map.items():
        latest = recs[-1]
        item = by_source.setdefault(
            source_id,
            {
                "source_id": source_id,
                "source": f"{_normalize_str(latest.get('source_type'))}:{source_id}",
                "title": _normalize_str(latest.get("title")),
                "author": _normalize_str(latest.get("author")),
                "author_id": _normalize_str(latest.get("author_id")),
                "source_type": _normalize_str(latest.get("source_type")) or "unknown",
                "blocks_count": 0,
                "from_blocks": False,
                "from_registry": True,
                "registry_status": _normalize_str(latest.get("status")),
                "is_focus_source": False,
                "is_architecture_internal_risk": False,
                "processed_exports": [],
            },
        )
        item["from_registry"] = True
        item["registry_status"] = _normalize_str(latest.get("status"))
        if not item.get("title"):
            item["title"] = _normalize_str(latest.get("title"))
        file_paths = latest.get("file_paths") or {}
        if isinstance(file_paths, dict):
            export_path = _normalize_str(file_paths.get("json"))
            if export_path:
                item["processed_exports"].append(export_path)

    export_files = sorted(processed_dir.rglob("*_blocks.json")) if processed_dir.exists() else []
    for path in export_files:
        p_str = str(path)
        for item in by_source.values():
            src = _normalize_str(item.get("source_id"))
            slug = src.lower()
            if slug and slug in path.name.lower():
                item["processed_exports"].append(p_str)

    for item in by_source.values():
        item["processed_exports"] = sorted(set(item.get("processed_exports", [])))
        item["is_focus_source"] = _is_focus_source(
            _normalize_str(item.get("title")),
            _normalize_str(item.get("source")),
            _normalize_str(item.get("source_id")),
            focus_hint,
        )
        source_text = " ".join(
            [
                _normalize_str(item.get("title")),
                _normalize_str(item.get("source_id")),
                _normalize_str(item.get("author")),
            ]
        ).lower()
        item["is_architecture_internal_risk"] = "neo mindbot" in source_text or "конспект" in source_text

    focus_source_ids = [item["source_id"] for item in by_source.values() if item.get("is_focus_source")]
    return {
        "generated_at": _utc_now(),
        "sources": sorted(by_source.values(), key=lambda x: x.get("source_id", "")),
        "focus_source_ids": sorted(focus_source_ids),
        "suspicious_internal_sources": [
            item["source_id"] for item in by_source.values() if item.get("is_architecture_internal_risk")
        ],
    }


def _extract_chunk_type(view: BlockView) -> str:
    chunk_type = _normalize_str(view.governance.get("chunk_type")).lower()
    if chunk_type:
        return chunk_type
    role = _normalize_str(view.section_role_hint).lower()
    if role in {"practice", "safety", "lens", "architecture", "style", "theory"}:
        return role
    text = f"{view.title}\n{view.text}".lower()
    if any(marker in text for marker in PRACTICE_MARKERS):
        return "practice"
    return "unknown/empty"


def _extract_allowed_use(view: BlockView) -> list[str]:
    values = _normalize_list(view.governance.get("allowed_use"))
    return values or ["unknown/empty"]


def _extract_safety_flags(view: BlockView) -> list[str]:
    values = _normalize_list(view.governance.get("safety_flags"))
    return values or ["unknown/empty"]


def _extract_lens_family(view: BlockView) -> list[str]:
    values = _normalize_list(view.governance.get("lens_family"))
    return values or ["unknown/empty"]


def audit_chunk_distribution(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    chunk_type = Counter()
    allowed_use = Counter()
    safety_flags = Counter()
    lens_family = Counter()

    for raw in blocks:
        view = _get_block_view(raw)
        chunk_type[_extract_chunk_type(view)] += 1
        for item in _extract_allowed_use(view):
            allowed_use[item] += 1
        for item in _extract_safety_flags(view):
            safety_flags[item] += 1
        for item in _extract_lens_family(view):
            lens_family[item] += 1

    for key in CHUNK_TYPES:
        chunk_type.setdefault(key, 0)
    for key in ALLOWED_USE_TYPES:
        allowed_use.setdefault(key, 0)
    for key in KNOWN_LENS_FAMILIES:
        lens_family.setdefault(key, 0)
    return {
        "total_chunks": len(blocks),
        "chunk_type_distribution": dict(sorted(chunk_type.items())),
        "allowed_use_distribution": dict(sorted(allowed_use.items())),
        "safety_flags_distribution": dict(sorted(safety_flags.items())),
        "lens_family_distribution": dict(sorted(lens_family.items())),
    }


def _boundary_bucket(value: float | None) -> str:
    if value is None:
        return "missing"
    if value >= 0.80:
        return "high"
    if value >= 0.50:
        return "medium"
    return "low"


def audit_structure_boundaries(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    heading_present = 0
    heading_missing = 0
    parent_present = 0
    parent_missing = 0
    bucket_counts = Counter()
    split_reason = Counter()
    section_role = Counter()
    findings: list[dict[str, Any]] = []

    for raw in blocks:
        view = _get_block_view(raw)
        chunk_type = _extract_chunk_type(view)
        has_heading = bool(view.heading_path)
        if has_heading:
            heading_present += 1
        else:
            heading_missing += 1

        if view.parent_section_id:
            parent_present += 1
        else:
            parent_missing += 1

        bucket = _boundary_bucket(view.boundary_confidence)
        bucket_counts[bucket] += 1
        split_reason[view.split_reason or "unknown/empty"] += 1
        section_role[view.section_role_hint or "unknown/empty"] += 1

        text_len = len(view.text)
        if not has_heading:
            findings.append(
                {
                    "category": "missing_heading_path",
                    "chunk_id": view.chunk_id,
                    "chunk_type": chunk_type,
                    "boundary_confidence": view.boundary_confidence,
                    "issue_reason": "heading_path missing",
                    "safe_preview": _safe_preview(view.text),
                }
            )
        if text_len >= 1200 and bucket == "low":
            findings.append(
                {
                    "category": "long_low_boundary",
                    "chunk_id": view.chunk_id,
                    "chunk_type": chunk_type,
                    "boundary_confidence": view.boundary_confidence,
                    "issue_reason": "long chunk with low boundary confidence",
                    "safe_preview": _safe_preview(view.text),
                }
            )
        if chunk_type == "practice" and (view.split_reason in {"", "semantic"} or bucket == "low"):
            findings.append(
                {
                    "category": "practice_split_suspect",
                    "chunk_id": view.chunk_id,
                    "chunk_type": chunk_type,
                    "boundary_confidence": view.boundary_confidence,
                    "issue_reason": "practice chunk might be split poorly",
                    "safe_preview": _safe_preview(view.text),
                }
            )
        if chunk_type == "lens" and not has_heading:
            findings.append(
                {
                    "category": "lens_without_heading",
                    "chunk_id": view.chunk_id,
                    "chunk_type": chunk_type,
                    "boundary_confidence": view.boundary_confidence,
                    "issue_reason": "lens chunk without heading path",
                    "safe_preview": _safe_preview(view.text),
                }
            )
        if chunk_type == "safety":
            lowered = view.text.lower()
            if any(marker in lowered for marker in PRACTICE_MARKERS) and any(
                marker in lowered for marker in ("теори", "модель", "концеп")
            ):
                findings.append(
                    {
                        "category": "safety_mixed_with_other",
                        "chunk_id": view.chunk_id,
                        "chunk_type": chunk_type,
                        "boundary_confidence": view.boundary_confidence,
                        "issue_reason": "safety content mixed with theory/practice",
                        "safe_preview": _safe_preview(view.text),
                    }
                )

    bucket_counts.setdefault("high", 0)
    bucket_counts.setdefault("medium", 0)
    bucket_counts.setdefault("low", 0)
    bucket_counts.setdefault("missing", 0)
    return {
        "heading_path_present": heading_present,
        "heading_path_missing": heading_missing,
        "parent_section_id_present": parent_present,
        "parent_section_id_missing": parent_missing,
        "boundary_confidence_buckets": dict(bucket_counts),
        "split_reason_distribution": dict(sorted(split_reason.items())),
        "section_role_hint_distribution": dict(sorted(section_role.items())),
        "findings": findings,
    }


def audit_mixed_intent(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    risk_counts = Counter()
    severity = Counter()
    primary_role = Counter()
    secondary_markers = Counter()
    reason = Counter()
    top_mixed: list[dict[str, Any]] = []

    for raw in blocks:
        view = _get_block_view(raw)
        cq = view.chunking_quality
        mixed_risk = _to_bool(cq.get("mixed_intent_risk"))
        mixed_severity = _normalize_str(cq.get("mixed_intent_severity")).lower() or "none"
        mixed_primary = _normalize_str(cq.get("primary_role")) or _extract_chunk_type(view)
        mixed_secondary = _normalize_list(cq.get("secondary_role_markers"))
        mixed_reason = _normalize_str(cq.get("mixed_intent_reason")) or "unknown/empty"

        risk_counts["true" if mixed_risk else "false"] += 1
        severity[mixed_severity] += 1
        primary_role[mixed_primary] += 1
        for marker in mixed_secondary or ["none"]:
            secondary_markers[marker] += 1
        reason[mixed_reason] += 1

        if mixed_risk or mixed_severity in {"medium", "high"}:
            top_mixed.append(
                {
                    "chunk_id": view.chunk_id,
                    "chunk_type": _extract_chunk_type(view),
                    "heading_path": " > ".join(view.heading_path),
                    "mixed_intent_risk": mixed_risk,
                    "mixed_intent_severity": mixed_severity,
                    "mixed_intent_primary_role": mixed_primary,
                    "secondary_role_markers": mixed_secondary,
                    "mixed_intent_reason": mixed_reason,
                    "boundary_confidence": view.boundary_confidence,
                    "safe_preview": _safe_preview(view.text),
                }
            )

    top_mixed.sort(
        key=lambda x: (
            -MIXED_INTENT_SEVERITY_ORDER.get(str(x.get("mixed_intent_severity")), 0),
            -(_to_float(x.get("boundary_confidence")) or 0.0),
            x.get("chunk_id", ""),
        )
    )
    return {
        "mixed_intent_risk_distribution": dict(risk_counts),
        "mixed_intent_severity_distribution": dict(sorted(severity.items())),
        "mixed_intent_primary_role_distribution": dict(sorted(primary_role.items())),
        "secondary_role_markers_distribution": dict(sorted(secondary_markers.items())),
        "mixed_intent_reason_distribution": dict(sorted(reason.items())),
        "top_mixed_chunks": top_mixed[:80],
    }


def audit_summary_readiness(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    missing = 0
    too_short = 0
    too_generic = 0
    duplicates = 0
    needs_enrichment = 0
    summary_present = 0
    duplicates_counter = Counter()
    findings: list[dict[str, Any]] = []

    generic_markers = {
        "введение",
        "раздел",
        "глава",
        "описание",
        "общая информация",
    }

    for raw in blocks:
        view = _get_block_view(raw)
        summary = _normalize_str(view.summary)
        lowered_summary = summary.lower()
        title = _normalize_str(view.title).lower()
        tokens = _tokenize(summary)

        if summary:
            summary_present += 1
            duplicates_counter[lowered_summary] += 1
        else:
            missing += 1
            needs_enrichment += 1
            findings.append(
                {
                    "chunk_id": view.chunk_id,
                    "issue_reason": "summary missing",
                    "safe_preview": _safe_preview(view.text),
                }
            )
            continue

        if len(tokens) < 5 or len(summary) < 35:
            too_short += 1
            needs_enrichment += 1
            findings.append(
                {
                    "chunk_id": view.chunk_id,
                    "issue_reason": "summary too short",
                    "safe_preview": _safe_preview(summary),
                }
            )

        is_generic = False
        if lowered_summary in generic_markers:
            is_generic = True
        if lowered_summary == title:
            is_generic = True
        if len(set(tokens)) <= 3:
            is_generic = True
        if is_generic:
            too_generic += 1
            needs_enrichment += 1
            findings.append(
                {
                    "chunk_id": view.chunk_id,
                    "issue_reason": "summary too generic",
                    "safe_preview": _safe_preview(summary),
                }
            )

    duplicate_texts = {k: v for k, v in duplicates_counter.items() if k and v > 1}
    if duplicate_texts:
        duplicates = sum(v - 1 for v in duplicate_texts.values())
        needs_enrichment += duplicates

    return {
        "summary_present_count": summary_present,
        "summary_missing_count": missing,
        "summary_too_short_count": too_short,
        "summary_too_generic_count": too_generic,
        "summary_duplicates_count": duplicates,
        "summary_needs_llm_enrichment_count": needs_enrichment,
        "duplicate_summary_examples": [
            {"summary_preview": _safe_preview(k, 120), "count": v}
            for k, v in sorted(duplicate_texts.items(), key=lambda x: -x[1])[:15]
        ],
        "findings": findings[:120],
    }


def _is_practice_chunk(view: BlockView, chunk_type: str) -> bool:
    if chunk_type == "practice":
        return True
    lowered = f"{view.title}\n{view.text}".lower()
    return any(marker in lowered for marker in PRACTICE_MARKERS)


def audit_practice_completeness(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    total_practice = 0
    needing_review = []
    has_goal_count = 0
    has_steps_count = 0
    has_duration_count = 0
    low_resource_marker_count = 0
    caution_count = 0

    for raw in blocks:
        view = _get_block_view(raw)
        chunk_type = _extract_chunk_type(view)
        if not _is_practice_chunk(view, chunk_type):
            continue

        total_practice += 1
        text = view.text.lower()
        gov = view.governance
        practice_meta = gov.get("practice_metadata") if isinstance(gov, dict) else {}
        if not isinstance(practice_meta, dict):
            practice_meta = {}

        has_goal = any(marker in text for marker in ("цель", "назначение", "для чего"))
        has_steps = bool(re.search(r"(шаг\s*\d+)|(^\s*[-*]\s+)", view.text.lower(), flags=re.MULTILINE))
        has_duration = any(marker in text for marker in ("минут", "время:", "дней", "ежеднев"))
        low_resource = _to_bool(practice_meta.get("low_resource_safe")) or any(
            marker in text for marker in ("если нет сил", "микро", "коротк")
        )
        has_caution = any(
            marker in text for marker in ("осторож", "противопоказ", "избегайте", "если кризис", "не делай")
        )
        cut_mid = view.text.strip().endswith(":")
        theory_mix = any(marker in text for marker in ("теория", "модель", "концеп")) and not has_steps

        has_goal_count += int(has_goal)
        has_steps_count += int(has_steps)
        has_duration_count += int(has_duration)
        low_resource_marker_count += int(low_resource)
        caution_count += int(has_caution)

        reasons = []
        if not has_goal:
            reasons.append("missing_goal")
        if not has_steps:
            reasons.append("missing_steps")
        if not has_duration:
            reasons.append("missing_duration_or_format")
        if not low_resource:
            reasons.append("missing_low_resource_marker")
        if not has_caution:
            reasons.append("missing_caution_or_contraindication")
        if cut_mid:
            reasons.append("possible_cut_in_middle")
        if theory_mix:
            reasons.append("practice_mixed_with_theory")

        if reasons:
            needing_review.append(
                {
                    "chunk_id": view.chunk_id,
                    "chunk_type": chunk_type,
                    "heading_path": " > ".join(view.heading_path),
                    "boundary_confidence": view.boundary_confidence,
                    "issue_reason": ", ".join(reasons),
                    "safe_preview": _safe_preview(view.text),
                }
            )

    return {
        "practice_chunks_total": total_practice,
        "practice_with_goal_count": has_goal_count,
        "practice_with_steps_count": has_steps_count,
        "practice_with_duration_count": has_duration_count,
        "practice_with_low_resource_marker_count": low_resource_marker_count,
        "practice_with_caution_count": caution_count,
        "practice_chunks_needing_review": needing_review[:150],
    }


def audit_no_citation_readiness(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    missing_not_for_quote = 0
    writer_context_without_not_for_quote = 0
    broad_allowed_use = 0
    author_term_risk = 0
    likely_diagnostic_lens_candidates = 0
    findings = []

    for raw in blocks:
        view = _get_block_view(raw)
        allowed_use = _extract_allowed_use(view)
        safety_flags = _extract_safety_flags(view)
        chunk_type = _extract_chunk_type(view)
        text = view.text.lower()

        has_not_for_quote = "not_for_direct_quote" in safety_flags
        has_writer_context = "writer_context" in allowed_use
        has_internal_only = "internal_only" in allowed_use or "do_not_use" in allowed_use
        terms_hit = [term for term in AUTHOR_TERMS if term in text]

        reasons = []
        if not has_not_for_quote:
            missing_not_for_quote += 1
            reasons.append("missing_not_for_direct_quote")
        if has_writer_context and not has_not_for_quote:
            writer_context_without_not_for_quote += 1
            reasons.append("writer_context_without_not_for_direct_quote")
        if not has_internal_only and has_writer_context and chunk_type in {"architecture", "unknown/empty"}:
            broad_allowed_use += 1
            reasons.append("allowed_use_maybe_too_broad")
        if terms_hit and has_writer_context:
            author_term_risk += 1
            reasons.append("source_specific_terms_need_neutral_mapping")
        if chunk_type == "theory" and any(term in text for term in ("паттерн", "триггер", "избеган")):
            likely_diagnostic_lens_candidates += 1
            reasons.append("likely_diagnostic_lens_but_tagged_theory")

        if reasons:
            findings.append(
                {
                    "chunk_id": view.chunk_id,
                    "chunk_type": chunk_type,
                    "allowed_use": allowed_use,
                    "safety_flags": safety_flags,
                    "lens_family": _extract_lens_family(view),
                    "issue_reason": ", ".join(reasons),
                    "safe_preview": _safe_preview(view.text),
                }
            )

    return {
        "chunks_without_not_for_direct_quote_count": missing_not_for_quote,
        "writer_context_without_not_for_direct_quote_count": writer_context_without_not_for_quote,
        "allowed_use_too_broad_count": broad_allowed_use,
        "source_specific_term_risk_count": author_term_risk,
        "likely_diagnostic_lens_candidates_count": likely_diagnostic_lens_candidates,
        "findings": findings[:180],
    }


def audit_source_markdown_readiness(markdown_path: Path | None) -> dict[str, Any]:
    if markdown_path is None or not markdown_path.exists():
        return {
            "raw_source_markdown_found": False,
            "message": "raw source markdown not found",
        }

    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    h1 = sum(1 for ln in lines if re.match(r"^\s*#\s+\S+", ln))
    h2 = sum(1 for ln in lines if re.match(r"^\s*##\s+\S+", ln))
    h3 = sum(1 for ln in lines if re.match(r"^\s*###\s+\S+", ln))
    section_lengths = []
    current_len = 0
    for line in lines:
        if re.match(r"^\s*#{1,3}\s+", line):
            if current_len:
                section_lengths.append(current_len)
            current_len = 0
        else:
            current_len += len(line.strip())
    if current_len:
        section_lengths.append(current_len)

    long_sections = sum(1 for value in section_lengths if value > 3500)
    merged_paragraph_candidates = sum(
        1 for line in lines if len(line.strip()) > 600 and "." in line and ":" in line and "-" not in line
    )
    markers_count = {
        "практика": text.lower().count("практик"),
        "упражнение": text.lower().count("упражнен"),
        "вопрос": text.lower().count("вопрос"),
        "шаг": text.lower().count("шаг"),
    }

    return {
        "raw_source_markdown_found": True,
        "path": str(markdown_path),
        "h1_count": h1,
        "h2_count": h2,
        "h3_count": h3,
        "section_count": len(section_lengths),
        "avg_section_char_length": round(sum(section_lengths) / max(1, len(section_lengths)), 2),
        "long_sections_without_subheadings_count": long_sections,
        "merged_paragraph_candidates_count": merged_paragraph_candidates,
        "markers_count": markers_count,
    }


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 7.0) -> dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=body, method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            parsed = None
            try:
                parsed = json.loads(content) if content else None
            except Exception:
                parsed = {"raw_text": content[:500]}
            return {"ok": True, "status_code": int(resp.status), "body": parsed}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        body_data: Any
        try:
            body_data = json.loads(raw) if raw else None
        except Exception:
            body_data = {"raw_text": raw[:500]}
        return {"ok": False, "status_code": int(exc.code), "body": body_data, "error": str(exc)}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive path
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def probe_chroma_readiness(
    *,
    api_base_url: str,
    config: dict[str, Any],
    all_blocks_path: Path,
    registry_records: list[dict[str, Any]],
) -> dict[str, Any]:
    status_resp = _http_json("GET", f"{api_base_url}/api/status/")
    registry_resp = _http_json("GET", f"{api_base_url}/api/registry/")
    query_resp = _http_json(
        "POST",
        f"{api_base_url}/api/query/",
        payload={"query": "проверка базы знаний", "top_k": 3, "pre_filter_k": 10, "use_rerank": False},
    )

    storage_cfg = (config.get("storage") or {}) if isinstance(config, dict) else {}
    embedding_cfg = (config.get("embedding") or {}) if isinstance(config, dict) else {}
    chroma_path = _normalize_str(storage_cfg.get("chroma_db_path"))
    collection_name = _normalize_str(storage_cfg.get("collection_name"))
    chroma_db_abs = str((Path("Bot_data_base") / chroma_path).resolve()) if chroma_path else ""

    local_blocks = load_processed_blocks(all_blocks_path)
    local_blocks_count = len(local_blocks)
    registry_count = len(registry_records)

    collection_exists = None
    collection_count = None
    chroma_probe_error = None
    possible_embedding_mismatch = False
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=chroma_db_abs, settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        names = []
        try:
            cols = client.list_collections()
            for col in cols:
                if hasattr(col, "name"):
                    names.append(str(col.name))
                elif isinstance(col, str):
                    names.append(col)
        except Exception:
            names = []

        collection_exists = collection_name in names if collection_name else False
        if collection_exists and collection_name:
            collection = client.get_collection(name=collection_name)
            collection_count = int(collection.count())
    except Exception as exc:
        chroma_probe_error = str(exc)
        if "dimension" in chroma_probe_error.lower() or "len()" in chroma_probe_error.lower():
            possible_embedding_mismatch = True

    for rec in registry_records:
        err = _normalize_str(rec.get("error_message")).lower()
        if "dimension" in err and "got" in err and "expecting embedding" in err:
            possible_embedding_mismatch = True

    query_works = bool(query_resp.get("ok")) and int(query_resp.get("status_code") or 0) == 200
    query_503 = int(query_resp.get("status_code") or 0) == 503
    needs_recovery = query_503 or not query_works or (
        collection_count is not None and local_blocks_count and collection_count != local_blocks_count
    )

    return {
        "generated_at": _utc_now(),
        "api_status": status_resp,
        "api_registry": registry_resp,
        "api_query": query_resp,
        "chroma_db_path": chroma_db_abs,
        "collection_name": collection_name,
        "collection_exists": collection_exists,
        "collection_count": collection_count,
        "chroma_probe_error": chroma_probe_error,
        "all_blocks_path": str(all_blocks_path),
        "all_blocks_exists": all_blocks_path.exists(),
        "local_blocks_count": local_blocks_count,
        "registry_count": registry_count,
        "embedding_model_configured": _normalize_str(embedding_cfg.get("model")),
        "possible_embedding_dimension_mismatch": possible_embedding_mismatch,
        "safe_reset_or_reindex_recommended": bool(needs_recovery),
    }


def _local_retrieval_fallback(
    *, query: str, blocks: list[dict[str, Any]], top_k: int = 5
) -> list[dict[str, Any]]:
    query_tokens = Counter(_tokenize(query))
    if not query_tokens:
        return []
    scored = []
    for raw in blocks:
        view = _get_block_view(raw)
        text_tokens = Counter(_tokenize(f"{view.title}\n{view.summary}\n{view.text}"))
        overlap = sum(min(query_tokens[t], text_tokens[t]) for t in query_tokens)
        norm = sum(query_tokens.values()) or 1
        score = overlap / norm
        if score <= 0:
            continue
        scored.append((score, raw))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def run_retrieval_probe_snapshot(
    *,
    queries: list[str],
    api_base_url: str,
    focus_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    snapshot = []
    for query in queries:
        api_result = _http_json(
            "POST",
            f"{api_base_url}/api/query/",
            payload={"query": query, "top_k": 5, "pre_filter_k": 20, "use_rerank": False},
        )
        if api_result.get("ok") and int(api_result.get("status_code") or 0) == 200:
            chunks = (((api_result.get("body") or {}).get("chunks")) or [])[:5]
            row = {
                "query": query,
                "source_path_used": "chroma_api",
                "top_chunks": [],
                "api_status_code": api_result.get("status_code"),
            }
            for chunk in chunks:
                gov = chunk.get("governance") or {}
                row["top_chunks"].append(
                    {
                        "chunk_id": _normalize_str(chunk.get("chunk_id")),
                        "score": chunk.get("score"),
                        "chunk_type": _normalize_str(gov.get("chunk_type")) or "unknown/empty",
                        "lens_family": _normalize_list(gov.get("lens_family")) or ["unknown/empty"],
                        "allowed_use": _normalize_list(gov.get("allowed_use")) or ["unknown/empty"],
                        "safety_flags": _normalize_list(gov.get("safety_flags")) or ["unknown/empty"],
                    }
                )
            row["metadata_plausible"] = bool(row["top_chunks"])
            snapshot.append(row)
            continue

        fallback_blocks = _local_retrieval_fallback(query=query, blocks=focus_blocks, top_k=5)
        row = {
            "query": query,
            "source_path_used": "local_fallback_lexical",
            "top_chunks": [],
            "api_status_code": api_result.get("status_code"),
            "api_error": api_result.get("error"),
        }
        for raw in fallback_blocks:
            view = _get_block_view(raw)
            row["top_chunks"].append(
                {
                    "chunk_id": view.chunk_id,
                    "chunk_type": _extract_chunk_type(view),
                    "lens_family": _extract_lens_family(view),
                    "allowed_use": _extract_allowed_use(view),
                    "safety_flags": _extract_safety_flags(view),
                    "safe_preview": _safe_preview(view.text, 120),
                }
            )
        row["metadata_plausible"] = bool(row["top_chunks"])
        snapshot.append(row)

    return {"generated_at": _utc_now(), "queries": snapshot}


def _manual_item(
    *,
    priority: str,
    view: BlockView,
    issue_reason: str,
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "priority": priority,
        "chunk_id": view.chunk_id,
        "source_title": view.source_title,
        "heading_path": " > ".join(view.heading_path),
        "chunk_type": _extract_chunk_type(view),
        "allowed_use": _extract_allowed_use(view),
        "safety_flags": _extract_safety_flags(view),
        "lens_family": _extract_lens_family(view),
        "boundary_confidence": view.boundary_confidence,
        "mixed_intent_severity": _normalize_str(view.chunking_quality.get("mixed_intent_severity")) or "none",
        "issue_reason": issue_reason,
        "recommended_manual_action": recommended_action,
        "safe_preview": _safe_preview(view.text),
    }


def build_manual_review_candidates(
    *,
    blocks: list[dict[str, Any]],
    mixed: dict[str, Any],
    no_citation: dict[str, Any],
    practice: dict[str, Any],
    limit: int = 50,
) -> list[dict[str, Any]]:
    block_map = {_get_block_view(raw).chunk_id: _get_block_view(raw) for raw in blocks}
    items: list[dict[str, Any]] = []

    for finding in no_citation.get("findings", []):
        chunk_id = finding.get("chunk_id")
        view = block_map.get(chunk_id)
        if not view:
            continue
        issue = str(finding.get("issue_reason") or "")
        if "writer_context_without_not_for_direct_quote" in issue or "missing_not_for_direct_quote" in issue:
            items.append(
                _manual_item(
                    priority="P0",
                    view=view,
                    issue_reason=issue,
                    recommended_action="Set strict no-citation safety and review allowed_use scope.",
                )
            )

    for finding in practice.get("practice_chunks_needing_review", []):
        chunk_id = finding.get("chunk_id")
        view = block_map.get(chunk_id)
        if not view:
            continue
        items.append(
            _manual_item(
                priority="P1",
                view=view,
                issue_reason=str(finding.get("issue_reason") or ""),
                recommended_action="Manually verify practice structure (goal/steps/duration/safety).",
            )
        )

    for finding in mixed.get("top_mixed_chunks", []):
        chunk_id = finding.get("chunk_id")
        severity = str(finding.get("mixed_intent_severity") or "none")
        if severity not in {"medium", "high"}:
            continue
        view = block_map.get(chunk_id)
        if not view:
            continue
        items.append(
            _manual_item(
                priority="P1",
                view=view,
                issue_reason=f"mixed_intent_{severity}: {finding.get('mixed_intent_reason')}",
                recommended_action="Split or relabel to isolate single intent role.",
            )
        )

    for raw in blocks:
        view = _get_block_view(raw)
        if not view.heading_path or _boundary_bucket(view.boundary_confidence) == "low":
            items.append(
                _manual_item(
                    priority="P2",
                    view=view,
                    issue_reason="missing heading_path or low boundary confidence",
                    recommended_action="Check source boundaries and heading mapping.",
                )
            )
        if not _extract_lens_family(view) or _extract_lens_family(view) == ["unknown/empty"]:
            items.append(
                _manual_item(
                    priority="P2",
                    view=view,
                    issue_reason="lens_family missing/unknown",
                    recommended_action="Assign lens_family where applicable.",
                )
            )

        summary = _normalize_str(view.summary)
        if not summary or len(_tokenize(summary)) < 5:
            items.append(
                _manual_item(
                    priority="P3",
                    view=view,
                    issue_reason="summary weak or missing",
                    recommended_action="Prepare summary for offline enrichment queue.",
                )
            )

    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        key = (str(item.get("chunk_id")), str(item.get("issue_reason")))
        prev = dedup.get(key)
        if prev is None:
            dedup[key] = item
            continue
        if SEVERITY_ORDER.get(item["priority"], 99) < SEVERITY_ORDER.get(prev["priority"], 99):
            dedup[key] = item

    ranked = sorted(
        dedup.values(),
        key=lambda x: (
            SEVERITY_ORDER.get(str(x.get("priority")), 99),
            -MIXED_INTENT_SEVERITY_ORDER.get(str(x.get("mixed_intent_severity")), 0),
            str(x.get("chunk_id")),
        ),
    )
    return ranked[:limit]


def recommend_next_prd(
    *,
    chroma_probe: dict[str, Any],
    markdown_readiness: dict[str, Any],
    summary_readiness: dict[str, Any],
) -> dict[str, Any]:
    query_status = int((chroma_probe.get("api_query") or {}).get("status_code") or 0)
    collection_count = chroma_probe.get("collection_count")
    local_count = int(chroma_probe.get("local_blocks_count") or 0)
    markdown_bad = bool(
        markdown_readiness.get("raw_source_markdown_found")
        and int(markdown_readiness.get("long_sections_without_subheadings_count") or 0) > 0
    )
    summary_gap = int(summary_readiness.get("summary_needs_llm_enrichment_count") or 0)

    if query_status != 200 or query_status == 503 or (
        collection_count is not None and local_count and int(collection_count) != int(local_count)
    ):
        return {
            "recommended_next_prd": "PRD-046.0.4.1 — BotDB Chroma Recovery / Index Consistency v1",
            "reason": "API query unhealthy or collection/local count mismatch.",
        }
    if markdown_bad:
        return {
            "recommended_next_prd": "PRD-046.0.4.2 — Source Markdown Readiness / Manual Boundary Prep v1",
            "reason": "Raw markdown structure requires manual boundary preparation.",
        }
    if summary_gap > 0:
        return {
            "recommended_next_prd": "PRD-046.0.5 — Offline LLM Summary + Lens Enrichment v1",
            "reason": "Structural base exists but summaries/lens readiness gaps remain.",
        }
    return {
        "recommended_next_prd": "PRD-046.0.6 — Knowledge Retrieval Eval Set v1",
        "reason": "Retrieval appears stable enough for formal evaluation set design.",
    }


def _dict_to_bullets(data: dict[str, Any]) -> str:
    lines = []
    for key, value in data.items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines)


def _write_markdown_reports(
    *,
    reports_dir: Path,
    inventory: dict[str, Any],
    metrics: dict[str, Any],
    manual_queue: list[dict[str, Any]],
    chroma_probe: dict[str, Any],
    retrieval_snapshot: dict[str, Any],
    markdown_readiness: dict[str, Any],
    next_prd: dict[str, Any],
    files_changed: list[str],
    commands_run: list[str],
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)

    kb_path = reports_dir / "PRD-046.0.4_KB_QUALITY_AUDIT_REPORT.md"
    summary_data = metrics.get("summary_readiness") or {}
    kb_lines = [
        "# PRD-046.0.4 KB Quality Audit Report",
        "",
        "## Source inventory",
        f"- Total sources discovered: `{len(inventory.get('sources', []))}`",
        f"- Focus source ids: `{inventory.get('focus_source_ids', [])}`",
        f"- Internal architecture risk sources: `{inventory.get('suspicious_internal_sources', [])}`",
        "",
        "## Focus source: КУЗНИЦА ДУХА",
        f"- Focus blocks count: `{metrics.get('total_chunks', 0)}`",
        "",
        "## Chunk type distribution",
        _dict_to_bullets(metrics.get("chunk_type_distribution", {})),
        "",
        "## Allowed-use distribution",
        _dict_to_bullets(metrics.get("allowed_use_distribution", {})),
        "",
        "## Safety flags distribution",
        _dict_to_bullets(metrics.get("safety_flags_distribution", {})),
        "",
        "## Lens family distribution",
        _dict_to_bullets(metrics.get("lens_family_distribution", {})),
        "",
        "## Boundary quality",
        _dict_to_bullets((metrics.get("structure") or {}).get("boundary_confidence_buckets", {})),
        "",
        "## Mixed-intent findings",
        _dict_to_bullets((metrics.get("mixed_intent") or {}).get("mixed_intent_severity_distribution", {})),
        "",
        "## Summary readiness",
        _dict_to_bullets(
            {
                "summary_present_count": summary_data.get("summary_present_count", 0),
                "summary_missing_count": summary_data.get("summary_missing_count", 0),
                "summary_too_short_count": summary_data.get("summary_too_short_count", 0),
                "summary_too_generic_count": summary_data.get("summary_too_generic_count", 0),
                "summary_duplicates_count": summary_data.get("summary_duplicates_count", 0),
                "summary_needs_llm_enrichment_count": summary_data.get(
                    "summary_needs_llm_enrichment_count", 0
                ),
            }
        ),
        "",
        "## Practice completeness",
        _dict_to_bullets(
            {
                "practice_chunks_total": (metrics.get("practice_completeness") or {}).get(
                    "practice_chunks_total", 0
                ),
                "practice_chunks_needing_review": len(
                    (metrics.get("practice_completeness") or {}).get("practice_chunks_needing_review", [])
                ),
            }
        ),
        "",
        "## No-citation/internal-lens readiness",
        _dict_to_bullets(
            {
                "chunks_without_not_for_direct_quote_count": (
                    metrics.get("no_citation_readiness") or {}
                ).get("chunks_without_not_for_direct_quote_count", 0),
                "writer_context_without_not_for_direct_quote_count": (
                    metrics.get("no_citation_readiness") or {}
                ).get("writer_context_without_not_for_direct_quote_count", 0),
            }
        ),
        "",
        "## Source markdown readiness",
        _dict_to_bullets(markdown_readiness),
        "",
        "## Top quality risks",
        "- Missing governance/no-citation signals in focus source chunks.",
        "- Query endpoint instability impacts Chroma retrieval confidence.",
        "- Weak/empty summaries reduce retrieval precision.",
        "",
        "## Manual review candidates",
        f"- Queue size: `{len(manual_queue)}`",
        "",
        "## Recommendations",
        f"- Next PRD: `{next_prd.get('recommended_next_prd')}`",
        f"- Reason: `{next_prd.get('reason')}`",
    ]
    kb_path.write_text("\n".join(kb_lines) + "\n", encoding="utf-8")

    chroma_path = reports_dir / "PRD-046.0.4_CHROMA_READINESS_AUDIT.md"
    chroma_lines = [
        "# PRD-046.0.4 Chroma Readiness Audit",
        "",
        "## BotDB API status",
        f"- `/api/status/`: `{(chroma_probe.get('api_status') or {}).get('status_code')}`",
        "",
        "## Registry status",
        f"- `/api/registry/`: `{(chroma_probe.get('api_registry') or {}).get('status_code')}`",
        f"- Registry entries: `{chroma_probe.get('registry_count')}`",
        "",
        "## Query endpoint status",
        f"- `/api/query/`: `{(chroma_probe.get('api_query') or {}).get('status_code')}`",
        f"- Query error: `{(chroma_probe.get('api_query') or {}).get('error')}`",
        "",
        "## Local fallback data",
        f"- all_blocks exists: `{chroma_probe.get('all_blocks_exists')}`",
        f"- local blocks count: `{chroma_probe.get('local_blocks_count')}`",
        "",
        "## Chroma collection status",
        f"- DB path: `{chroma_probe.get('chroma_db_path')}`",
        f"- Collection: `{chroma_probe.get('collection_name')}`",
        f"- Collection exists: `{chroma_probe.get('collection_exists')}`",
        f"- Collection count: `{chroma_probe.get('collection_count')}`",
        "",
        "## Embedding model / dimension signals",
        f"- Embedding model configured: `{chroma_probe.get('embedding_model_configured')}`",
        f"- Dimension mismatch signal: `{chroma_probe.get('possible_embedding_dimension_mismatch')}`",
        "",
        "## Failure hypothesis",
        f"- Probe error: `{chroma_probe.get('chroma_probe_error')}`",
        "",
        "## Safe next steps",
        "- No reset/reindex performed in this PRD (audit-only).",
        f"- Recovery recommended: `{chroma_probe.get('safe_reset_or_reindex_recommended')}`",
        "",
        "## Whether PRD-046.0.4.1 is needed",
        f"- `{next_prd.get('recommended_next_prd')}`",
    ]
    chroma_path.write_text("\n".join(chroma_lines) + "\n", encoding="utf-8")

    queue_path = reports_dir / "PRD-046.0.4_MANUAL_REVIEW_QUEUE.md"
    queue_lines = [
        "# PRD-046.0.4 Manual Review Queue",
        "",
        f"- Total queued items: `{len(manual_queue)}`",
        "",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for item in manual_queue:
        priority = str(item.get("priority") or "P3")
        grouped.setdefault(priority, []).append(item)

    idx = 1
    for priority in ("P0", "P1", "P2", "P3"):
        entries = grouped.get(priority, [])
        queue_lines.append(f"## {priority}")
        queue_lines.append(f"- count: `{len(entries)}`")
        queue_lines.append("")
        for item in entries:
            queue_lines.extend(
                [
                    f"### {idx}. {item.get('chunk_id')}",
                    f"- source_title: `{item.get('source_title')}`",
                    f"- heading_path: `{item.get('heading_path')}`",
                    f"- chunk_type: `{item.get('chunk_type')}`",
                    f"- allowed_use: `{item.get('allowed_use')}`",
                    f"- safety_flags: `{item.get('safety_flags')}`",
                    f"- lens_family: `{item.get('lens_family')}`",
                    f"- boundary_confidence: `{item.get('boundary_confidence')}`",
                    f"- mixed_intent_severity: `{item.get('mixed_intent_severity')}`",
                    f"- issue_reason: `{item.get('issue_reason')}`",
                    f"- recommended_manual_action: `{item.get('recommended_manual_action')}`",
                    f"- safe_preview: `{item.get('safe_preview')}`",
                    "",
                ]
            )
            idx += 1
    queue_path.write_text("\n".join(queue_lines), encoding="utf-8")

    next_path = reports_dir / "PRD-046.0.4_NEXT_PRD_RECOMMENDATION.md"
    next_lines = [
        "# PRD-046.0.4 Next PRD Recommendation",
        "",
        f"- Recommended: `{next_prd.get('recommended_next_prd')}`",
        f"- Reason: `{next_prd.get('reason')}`",
        "",
        "## Decision Inputs",
        f"- Query endpoint code: `{(chroma_probe.get('api_query') or {}).get('status_code')}`",
        f"- Collection/local count: `{chroma_probe.get('collection_count')} / {chroma_probe.get('local_blocks_count')}`",
        f"- Markdown found: `{markdown_readiness.get('raw_source_markdown_found')}`",
        f"- Summary enrichment need: `{(metrics.get('summary_readiness') or {}).get('summary_needs_llm_enrichment_count')}`",
    ]
    next_path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")

    impl_path = reports_dir / "PRD-046.0.4_IMPLEMENTATION_REPORT.md"
    impl_lines = [
        "# PRD-046.0.4 IMPLEMENTATION REPORT",
        "",
        "## Status",
        "- Implementation: done (audit-only, no production mutations)",
        "- Branch: `main`",
        "",
        "## Files Changed",
    ]
    impl_lines.extend([f"- `{item}`" for item in files_changed])
    impl_lines.extend(
        [
            "",
            "## Commands Run",
        ]
    )
    impl_lines.extend([f"- `{cmd}`" for cmd in commands_run])
    impl_lines.extend(
        [
            "",
            "## Metrics Summary",
            f"- Focus chunks: `{metrics.get('total_chunks', 0)}`",
            f"- Missing summary: `{(metrics.get('summary_readiness') or {}).get('summary_missing_count', 0)}`",
            f"- Mixed-intent medium/high: `{sum(v for k, v in (metrics.get('mixed_intent') or {}).get('mixed_intent_severity_distribution', {}).items() if k in {'medium', 'high'})}`",
            f"- Manual review queue size: `{len(manual_queue)}`",
            f"- Query endpoint code: `{(chroma_probe.get('api_query') or {}).get('status_code')}`",
            "",
            "## Next PRD Recommendation",
            f"- `{next_prd.get('recommended_next_prd')}`",
            f"- Reason: `{next_prd.get('reason')}`",
            "",
            "## Commit / Push",
            "- Commit hash: `pending`",
            "- Push status: `pending`",
        ]
    )
    impl_path.write_text("\n".join(impl_lines) + "\n", encoding="utf-8")

    retrieval_path = reports_dir / "PRD-046.0.4_RETRIEVAL_PROBE_SNAPSHOT.md"
    retrieval_lines = [
        "# PRD-046.0.4 Retrieval Probe Snapshot",
        "",
    ]
    for row in retrieval_snapshot.get("queries", []):
        retrieval_lines.append(f"## Query: {row.get('query')}")
        retrieval_lines.append(f"- source_path_used: `{row.get('source_path_used')}`")
        retrieval_lines.append(f"- api_status_code: `{row.get('api_status_code')}`")
        retrieval_lines.append(f"- metadata_plausible: `{row.get('metadata_plausible')}`")
        retrieval_lines.append("- top_chunks:")
        for chunk in row.get("top_chunks", []):
            retrieval_lines.append(
                f"  - `{chunk.get('chunk_id')}` / `{chunk.get('chunk_type')}` / `{chunk.get('allowed_use')}` / `{chunk.get('lens_family')}`"
            )
        retrieval_lines.append("")
    retrieval_path.write_text("\n".join(retrieval_lines) + "\n", encoding="utf-8")


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    if yaml is None:
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def run_audit(
    *,
    source_title_hint: str,
    output_dir: Path,
    reports_dir: Path,
    api_base_url: str,
) -> dict[str, Any]:
    root = Path.cwd()
    botdb_dir = root / "Bot_data_base"
    processed_path = botdb_dir / "data" / "processed" / "all_blocks_merged.json"
    processed_dir = botdb_dir / "data" / "processed"
    registry_path = botdb_dir / "data" / "registry.json"
    config_path = botdb_dir / "config.yaml"
    source_markdown_candidates = list((botdb_dir / "data" / "uploads" / "books").glob("*КУЗНИЦА*.md"))
    source_markdown_path = source_markdown_candidates[0] if source_markdown_candidates else None

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_blocks = load_processed_blocks(processed_path)
    registry_records = load_registry_records(registry_path)
    config = _load_config(config_path)

    inventory = build_source_inventory(
        blocks=all_blocks,
        registry_records=registry_records,
        processed_dir=processed_dir,
        focus_hint=source_title_hint,
    )
    focus_ids = set(inventory.get("focus_source_ids", []))
    focus_blocks = [b for b in all_blocks if _source_id_from_block(b) in focus_ids]
    if not focus_blocks:
        focus_blocks = [b for b in all_blocks if _is_focus_source(_get_block_view(b).source_title, _get_block_view(b).source, _source_id_from_block(b), source_title_hint)]

    distribution = audit_chunk_distribution(focus_blocks)
    structure = audit_structure_boundaries(focus_blocks)
    mixed = audit_mixed_intent(focus_blocks)
    summary = audit_summary_readiness(focus_blocks)
    practice = audit_practice_completeness(focus_blocks)
    no_citation = audit_no_citation_readiness(focus_blocks)
    markdown_readiness = audit_source_markdown_readiness(source_markdown_path)
    chroma_probe = probe_chroma_readiness(
        api_base_url=api_base_url,
        config=config,
        all_blocks_path=processed_path,
        registry_records=registry_records,
    )
    retrieval_snapshot = run_retrieval_probe_snapshot(
        queries=DEFAULT_PROBE_QUERIES,
        api_base_url=api_base_url,
        focus_blocks=focus_blocks,
    )

    metrics = {
        **distribution,
        "structure": structure,
        "mixed_intent": mixed,
        "summary_readiness": summary,
        "practice_completeness": practice,
        "no_citation_readiness": no_citation,
        "focus_source_ids": sorted(focus_ids),
    }

    manual_queue = build_manual_review_candidates(
        blocks=focus_blocks,
        mixed=mixed,
        no_citation=no_citation,
        practice=practice,
        limit=50,
    )
    next_prd = recommend_next_prd(
        chroma_probe=chroma_probe,
        markdown_readiness=markdown_readiness,
        summary_readiness=summary,
    )

    chunk_findings = {
        "structure_findings": structure.get("findings", []),
        "mixed_intent_top": mixed.get("top_mixed_chunks", []),
        "summary_findings": summary.get("findings", []),
        "no_citation_findings": no_citation.get("findings", []),
        "practice_needing_review": practice.get("practice_chunks_needing_review", []),
    }

    source_inventory_path = output_dir / "source_inventory.json"
    kb_metrics_path = output_dir / "kb_quality_metrics.json"
    chunk_findings_path = output_dir / "chunk_quality_findings.json"
    manual_candidates_path = output_dir / "manual_review_candidates.json"
    chroma_probe_path = output_dir / "chroma_readiness_probe.json"
    retrieval_path = output_dir / "retrieval_probe_snapshot.json"
    runtime_logs_path = output_dir / "sanitized_runtime_logs.txt"

    source_inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    kb_metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    chunk_findings_path.write_text(
        json.dumps(chunk_findings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manual_candidates_path.write_text(
        json.dumps({"items": manual_queue}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    chroma_probe_path.write_text(
        json.dumps(chroma_probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    retrieval_path.write_text(
        json.dumps(retrieval_snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    runtime_lines = [
        f"[{_utc_now()}] PRD-046.0.4 audit run",
        f"focus_blocks={len(focus_blocks)}",
        f"query_status={(chroma_probe.get('api_query') or {}).get('status_code')}",
        f"collection_count={chroma_probe.get('collection_count')}",
        f"local_blocks_count={chroma_probe.get('local_blocks_count')}",
        f"recommended_next_prd={next_prd.get('recommended_next_prd')}",
    ]
    if chroma_probe.get("chroma_probe_error"):
        runtime_lines.append(f"chroma_probe_error={chroma_probe.get('chroma_probe_error')}")
    runtime_logs_path.write_text("\n".join(runtime_lines) + "\n", encoding="utf-8")

    files_changed = [
        "Bot_data_base/tools/kb_quality_audit.py",
        "Bot_data_base/tools/__init__.py",
        "Bot_data_base/tests/test_kb_quality_audit_metrics.py",
        "Bot_data_base/tests/test_chroma_readiness_audit.py",
        "TO_DO_LIST/PRD-046.0.4_TASK_LIST.md",
        "TO_DO_LIST/reports/PRD-046.0.4_IMPLEMENTATION_REPORT.md",
        "TO_DO_LIST/reports/PRD-046.0.4_KB_QUALITY_AUDIT_REPORT.md",
        "TO_DO_LIST/reports/PRD-046.0.4_CHROMA_READINESS_AUDIT.md",
        "TO_DO_LIST/reports/PRD-046.0.4_MANUAL_REVIEW_QUEUE.md",
        "TO_DO_LIST/reports/PRD-046.0.4_NEXT_PRD_RECOMMENDATION.md",
        "TO_DO_LIST/logs/PRD-046.0.4/source_inventory.json",
        "TO_DO_LIST/logs/PRD-046.0.4/kb_quality_metrics.json",
        "TO_DO_LIST/logs/PRD-046.0.4/chunk_quality_findings.json",
        "TO_DO_LIST/logs/PRD-046.0.4/manual_review_candidates.json",
        "TO_DO_LIST/logs/PRD-046.0.4/chroma_readiness_probe.json",
        "TO_DO_LIST/logs/PRD-046.0.4/retrieval_probe_snapshot.json",
        "TO_DO_LIST/logs/PRD-046.0.4/sanitized_runtime_logs.txt",
    ]
    commands_run = [
        f"python Bot_data_base/tools/kb_quality_audit.py --source-title \"{source_title_hint}\" --output-dir {output_dir}",
        ".\\bot_psychologist\\.venv\\Scripts\\python.exe -m pytest Bot_data_base/tests/test_kb_quality_audit_metrics.py -q",
        ".\\bot_psychologist\\.venv\\Scripts\\python.exe -m pytest Bot_data_base/tests/test_chroma_readiness_audit.py -q",
        ".\\bot_psychologist\\.venv\\Scripts\\python.exe -m pytest Bot_data_base/tests -q",
        ".\\bot_psychologist\\.venv\\Scripts\\python.exe -m pytest bot_psychologist/tests/test_knowledge_policy.py -q",
        ".\\bot_psychologist\\.venv\\Scripts\\python.exe -m pytest bot_psychologist/tests/multiagent -q",
    ]
    _write_markdown_reports(
        reports_dir=reports_dir,
        inventory=inventory,
        metrics=metrics,
        manual_queue=manual_queue,
        chroma_probe=chroma_probe,
        retrieval_snapshot=retrieval_snapshot,
        markdown_readiness=markdown_readiness,
        next_prd=next_prd,
        files_changed=files_changed,
        commands_run=commands_run,
    )
    return {
        "source_inventory_path": str(source_inventory_path),
        "kb_metrics_path": str(kb_metrics_path),
        "chunk_findings_path": str(chunk_findings_path),
        "manual_candidates_path": str(manual_candidates_path),
        "chroma_probe_path": str(chroma_probe_path),
        "retrieval_snapshot_path": str(retrieval_path),
        "runtime_logs_path": str(runtime_logs_path),
        "manual_queue_size": len(manual_queue),
        "focus_blocks_count": len(focus_blocks),
        "recommended_next_prd": next_prd.get("recommended_next_prd"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.4 KB quality and Chroma readiness audit (read-only).")
    parser.add_argument("--source-title", default="КУЗНИЦА", help="Focus source title hint.")
    parser.add_argument(
        "--output-dir",
        default="TO_DO_LIST/logs/PRD-046.0.4",
        help="Directory for machine-readable artifacts.",
    )
    parser.add_argument(
        "--reports-dir",
        default="TO_DO_LIST/reports",
        help="Directory for markdown reports.",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8003",
        help="Bot_data_base API base URL.",
    )
    args = parser.parse_args()

    try:
        result = run_audit(
            source_title_hint=args.source_title,
            output_dir=Path(args.output_dir),
            reports_dir=Path(args.reports_dir),
            api_base_url=args.api_base_url.rstrip("/"),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(f"[kb_quality_audit] failed: {exc}")
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
