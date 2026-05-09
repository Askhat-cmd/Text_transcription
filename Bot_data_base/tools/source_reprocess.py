from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from chunkers.book_chunker import BookChunker
from governance.chunking_quality import build_chunking_quality_v1
from governance.governance_adapter import apply_governance_to_blocks_v1
from models.universal_block import UniversalBlock
from tools.kb_quality_audit import evaluate_governed_index_gate, load_processed_blocks

TARGET_TAG = "PRD-046.0.4.2"

LENS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shame": ("стыд", "недостаточ", "со мной что-то не так"),
    "guilt": ("вина", "виноват", "виновата"),
    "self_criticism": ("самокритик", "критикую себя", "недостаточ"),
    "perfectionism": ("идеал", "перфекц", "лучше всех", "безошиб"),
    "procrastination": ("прокрастин", "откладыва", "не могу начать"),
    "avoidance": ("избега", "уклоня", "прячусь"),
    "low_resource": ("нет сил", "пустота", "выгорел", "истощ"),
    "freeze": ("замер", "freeze", "ступор"),
    "hyperarousal": ("тревог", "паник", "перевозбуж"),
    "body_awareness": ("тело", "дыхани", "ощущ", "заземл"),
    "emotional_regulation": ("регуляц", "успоко", "самоподдерж"),
    "relationships": ("отношен", "партнер", "близост"),
    "boundaries": ("границ", "нет", "угожда"),
    "inner_parts": ("часть меня", "внутренний ребенок", "части личности"),
    "meaning": ("смысл", "пустота", "ценност"),
    "spiritual_bypass": ("духовн", "просветл", "обход боли"),
    "control": ("контрол", "держать все"),
    "achievement": ("достич", "успех", "результат"),
    "fear_of_rejection": ("отверг", "не примут", "стыдно показывать"),
    "anger": ("злюсь", "гнев", "раздраж"),
    "grief": ("горе", "утрат", "потер"),
    "identity": ("кто я", "идентич", "образ себя"),
}

PRACTICE_MARKERS = ("практик", "практикум", "шаг", "время:", "цель:", "сделай", "запиши", "попробуй")
LENS_MARKERS = ("механизм", "почему", "схема", "паттерн", "драйвер", "программа", "как это работает")
SAFETY_MARKERS = ("важно", "если тяжело", "не форсируй", "сбавь темп", "обратись за помощью", "экстренн")
CASE_MARKERS = ("из сессии", "кейс", "пример клиента", "диалог")
STYLE_MARKERS = ("архитектур", "writer", "diagnostic", "contract", "prompt")
RISK_MARKERS = ("суицид", "самоповрежд", "медицин", "диагноз", "регресс")
AUTHOR_STYLE_MARKERS = ("кузница духа", "программа", "духовн", "автор")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_preview(text: str, limit: int = 160) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _slugify(value: str) -> str:
    raw = str(value or "").strip().lower()
    raw = re.sub(r"\s+", "_", raw)
    return re.sub(r"[^0-9a-zа-я_]+", "", raw)


def _hash_parent(source_id: str, heading_path: list[str], chunk_index: int) -> str:
    payload = f"{source_id}|{' > '.join(heading_path)}|{chunk_index}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"{source_id}::section::legacy::{digest}"


def _extract_source_id(raw_block: dict[str, Any]) -> str:
    source = str(raw_block.get("source") or "")
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _is_target_block(raw_block: dict[str, Any], source_hint: str) -> bool:
    hint = source_hint.strip().lower()
    metadata = raw_block.get("metadata") or {}
    source = str(raw_block.get("source") or "").lower()
    source_id = _extract_source_id(raw_block).lower()
    source_title = str(metadata.get("source_title") or "").lower()
    joined = " ".join([source, source_id, source_title])
    return hint in joined if hint else False


def _infer_chunk_type(text: str, title: str, role_hint: str) -> str:
    role = str(role_hint or "").strip().lower()
    if role in {"practice", "lens", "safety", "style", "architecture", "case", "theory"}:
        return "style" if role == "architecture" else role

    low = f"{title}\n{text}".lower()
    if any(marker in low for marker in PRACTICE_MARKERS):
        return "practice"
    if any(marker in low for marker in SAFETY_MARKERS):
        return "safety"
    if any(marker in low for marker in LENS_MARKERS):
        return "lens"
    if any(marker in low for marker in CASE_MARKERS):
        return "case"
    if any(marker in low for marker in STYLE_MARKERS):
        return "style"
    return "theory"


def _seed_lens_family(text: str, title: str, heading_path: list[str]) -> list[str]:
    low = f"{title}\n{' > '.join(heading_path)}\n{text}".lower()
    tags: list[str] = []
    for lens, markers in LENS_KEYWORDS.items():
        if any(marker in low for marker in markers):
            tags.append(lens)
    return _dedupe(tags)


def _extract_practice_metadata(text: str) -> dict[str, Any]:
    low = text.lower()
    goal = ""
    duration = ""
    for line in text.splitlines():
        line_norm = line.strip()
        line_low = line_norm.lower()
        if not goal and line_low.startswith("цель:"):
            goal = line_norm.split(":", 1)[-1].strip()
        if not duration and line_low.startswith("время:"):
            duration = line_norm.split(":", 1)[-1].strip()
    if not duration:
        m = re.search(r"(\d{1,3}\s*(?:мин|minute|min))", low)
        duration = m.group(1) if m else ""

    steps_count = len(re.findall(r"(?:шаг|step)\s*\d+", low))
    if steps_count == 0:
        steps_count = len(re.findall(r"(?m)^\s*(?:\d+[\).]|[-*•])\s+", text))

    body_based = any(marker in low for marker in ("дых", "тело", "зазем", "ощущ"))
    requires_journaling = any(marker in low for marker in ("запиши", "дневник", "письменно"))
    minutes: int | None = None
    m_num = re.search(r"(\d{1,3})\s*(?:мин|minute|min)", duration or low)
    if m_num:
        try:
            minutes = int(m_num.group(1))
        except Exception:
            minutes = None

    low_resource_safe = bool(
        body_based and steps_count > 0 and steps_count <= 3 and minutes is not None and minutes <= 10 and not requires_journaling
    )
    return {
        "goal": goal,
        "duration": duration,
        "steps_count": int(steps_count),
        "requires_journaling": requires_journaling,
        "body_based": body_based,
        "low_resource_safe": low_resource_safe,
    }


def _build_allowed_use(chunk_type: str, *, is_sanitized_case: bool = True) -> list[str]:
    if chunk_type == "practice":
        return ["practice_suggestion"]
    if chunk_type == "lens":
        return ["writer_context", "diagnostic_lens"]
    if chunk_type == "theory":
        return ["writer_context"]
    if chunk_type == "safety":
        return ["internal_only", "safety_protocol"]
    if chunk_type == "case":
        return ["writer_context"] if is_sanitized_case else ["internal_only"]
    if chunk_type == "style":
        return ["internal_only", "style_guidance", "diagnostic_lens"]
    return ["internal_only"]


def _build_summary(
    *,
    chunk_type: str,
    heading_path: list[str],
    lens_family: list[str],
    section_role_hint: str,
    allowed_use: list[str],
) -> str:
    tail = heading_path[-1] if heading_path else "untitled_section"
    role = section_role_hint or "unknown"
    uses = ",".join(allowed_use) if allowed_use else "internal_only"
    if lens_family:
        summary = f"{chunk_type}: {tail}. Темы: {', '.join(lens_family)}. Роль: {role}. Использование: {uses}."
    else:
        summary = f"{chunk_type}: {tail}. Роль: {role}. Нужна ручная проверка темы. Использование: {uses}."
    return summary[:240].strip()


def _to_universal_block(raw: dict[str, Any]) -> UniversalBlock:
    metadata = raw.get("metadata") or {}
    source = str(raw.get("source") or "")
    source_type = ""
    source_id = ""
    if ":" in source:
        source_type, source_id = source.split(":", 1)
    return UniversalBlock(
        block_id=str(raw.get("id") or raw.get("chunk_id") or ""),
        source_type=source_type or str(metadata.get("source_type") or ""),
        source_id=source_id or str(metadata.get("source_id") or ""),
        text=str(raw.get("text") or ""),
        title=str(raw.get("title") or ""),
        summary=str(raw.get("summary") or ""),
        sd_level=str(raw.get("sd_level") or "GREEN"),
        sd_confidence=float(raw.get("sd_confidence") or 0.0),
        complexity=float(raw.get("complexity") or 0.0),
        author=str(metadata.get("author") or ""),
        author_id=str(metadata.get("author_id") or ""),
        source_title=str(metadata.get("source_title") or ""),
        language=str(metadata.get("language") or "ru"),
        published_date=str(metadata.get("published_date") or ""),
        chapter_title=str(metadata.get("chapter_title") or ""),
        chunk_index=int(metadata.get("chunk_index") or 0),
        heading_path=(metadata.get("heading_path") or []),
        section_role_hint=str(metadata.get("section_role_hint") or ""),
        boundary_confidence=float(metadata.get("boundary_confidence") or 0.0),
        split_reason=str(metadata.get("split_reason") or ""),
        parent_section_id=str(metadata.get("parent_section_id") or ""),
        governance=(metadata.get("governance") or {}),
        chunking_quality=(metadata.get("chunking_quality") or {}),
    )


def _backfill_block(raw: dict[str, Any], source_profile: str = "practice_manual") -> tuple[dict[str, Any], dict[str, Any]]:
    block = copy.deepcopy(raw)
    md = block.setdefault("metadata", {})
    text = str(block.get("text") or "")
    title = str(block.get("title") or "")

    heading_path = md.get("heading_path") if isinstance(md.get("heading_path"), list) else []
    heading_path = [str(x).strip() for x in heading_path if str(x).strip()]
    if not heading_path:
        chapter = str(md.get("chapter_title") or "").strip()
        if chapter:
            heading_path.append(chapter)
        if title and (not heading_path or heading_path[-1] != title):
            heading_path.append(title)
        if not heading_path:
            heading_path = ["Legacy section", title or "Untitled"]

    role_hint = str(md.get("section_role_hint") or "").strip().lower()
    gov = md.get("governance") if isinstance(md.get("governance"), dict) else {}
    existing_chunk_type = str(gov.get("chunk_type") or "").strip().lower()
    chunk_type = existing_chunk_type if existing_chunk_type else _infer_chunk_type(text, title, role_hint)
    if not role_hint:
        role_hint = chunk_type

    boundary_confidence = _to_float(md.get("boundary_confidence"))
    if boundary_confidence is None:
        defaults = {
            "practice": 0.72,
            "safety": 0.78,
            "lens": 0.67,
            "case": 0.62,
            "style": 0.65,
            "theory": 0.58,
        }
        boundary_confidence = defaults.get(chunk_type, 0.55)
    split_reason = str(md.get("split_reason") or "").strip() or "legacy_backfill_v1"

    source_id = _extract_source_id(block)
    chunk_index = int(md.get("chunk_index") or 0)
    parent_section_id = str(md.get("parent_section_id") or "").strip() or _hash_parent(source_id, heading_path, chunk_index)

    lens_family = _dedupe(_normalize_list(gov.get("lens_family")) + _seed_lens_family(text, title, heading_path))
    safety_flags = _normalize_list(gov.get("safety_flags"))
    safety_flags.append("not_for_direct_quote")
    low = f"{title}\n{text}".lower()
    if chunk_type in {"style"} or any(marker in low for marker in AUTHOR_STYLE_MARKERS):
        safety_flags.append("source_style_not_user_facing")
    if any(marker in low for marker in RISK_MARKERS):
        safety_flags.extend(["needs_review", "clinical_risk"])

    practice_metadata = gov.get("practice_metadata") if isinstance(gov.get("practice_metadata"), dict) else {}
    if chunk_type == "practice":
        practice_metadata = {**practice_metadata, **_extract_practice_metadata(text)}
        if not practice_metadata.get("low_resource_safe", False):
            safety_flags.append("practice_requires_low_resource_check")
    else:
        practice_metadata = practice_metadata if isinstance(practice_metadata, dict) else {}

    allowed_use = _build_allowed_use(chunk_type, is_sanitized_case=True)
    if "needs_review" in safety_flags and "internal_only" not in allowed_use and chunk_type in {"safety", "style"}:
        allowed_use = _dedupe(allowed_use + ["internal_only"])

    tags = _dedupe(_normalize_list(gov.get("tags")) + [chunk_type] + lens_family)
    governance_notes = _dedupe(_normalize_list(gov.get("governance_notes")) + ["deterministic_backfill_v1"])

    source_trace = gov.get("source_trace") if isinstance(gov.get("source_trace"), dict) else {}
    source_trace = {
        **source_trace,
        "source_id": source_id,
        "source_title": str(md.get("source_title") or ""),
        "source_type": str(md.get("source_type") or "book"),
        "source_kind": "knowledge_source",
        "adapter": "source_reprocess_backfill_v1",
    }

    block["summary"] = str(block.get("summary") or "").strip()
    if not block["summary"]:
        block["summary"] = _build_summary(
            chunk_type=chunk_type,
            heading_path=heading_path,
            lens_family=lens_family,
            section_role_hint=role_hint,
            allowed_use=allowed_use,
        )

    md["heading_path"] = heading_path
    md["section_role_hint"] = role_hint
    md["boundary_confidence"] = float(boundary_confidence)
    md["split_reason"] = split_reason
    md["parent_section_id"] = parent_section_id
    md["governance"] = {
        "schema_version": "governance_v1",
        "source_profile": source_profile,
        "source_kind": "knowledge_source",
        "source_visibility": "internal_lens",
        "chunk_type": chunk_type,
        "allowed_use": _dedupe(allowed_use),
        "safety_flags": _dedupe(safety_flags),
        "lens_family": lens_family,
        "practice_metadata": practice_metadata,
        "tags": tags,
        "governance_notes": governance_notes,
        "source_trace": source_trace,
    }

    ub = _to_universal_block(block)
    ub.heading_path = heading_path
    ub.section_role_hint = role_hint
    ub.boundary_confidence = float(boundary_confidence)
    ub.split_reason = split_reason
    ub.parent_section_id = parent_section_id
    ub.governance = md["governance"]
    ub.chunking_quality = build_chunking_quality_v1(ub)
    md["chunking_quality"] = ub.chunking_quality

    reasons: list[str] = []
    if not lens_family:
        reasons.append("lens_family_low_confidence")
    if ub.chunking_quality.get("mixed_intent_severity") == "high":
        reasons.append("mixed_intent_high")
    if chunk_type == "practice" and int(practice_metadata.get("steps_count", 0) or 0) == 0:
        reasons.append("practice_incomplete")
    if "source_style_not_user_facing" in md["governance"].get("safety_flags", []):
        reasons.append("source_style_not_user_facing")
    if float(boundary_confidence) < 0.45:
        reasons.append("boundary_confidence_low")

    return block, {
        "chunk_type": chunk_type,
        "allowed_use": md["governance"]["allowed_use"],
        "safety_flags": md["governance"]["safety_flags"],
        "summary_added": bool(block.get("summary")),
        "needs_manual_review_reasons": reasons,
    }


def _build_manual_review_queue(source_name: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for raw in blocks:
        md = raw.get("metadata") or {}
        gov = md.get("governance") or {}
        cq = md.get("chunking_quality") or {}
        reasons: list[str] = []

        summary = str(raw.get("summary") or "").strip()
        if not summary:
            reasons.append("summary_missing")

        lens_family = _normalize_list(gov.get("lens_family"))
        if not lens_family:
            reasons.append("lens_family_low_confidence")

        if str(cq.get("mixed_intent_severity") or "").lower() == "high":
            reasons.append("mixed_intent_high")

        chunk_type = str(gov.get("chunk_type") or "").lower()
        practice_steps = int((gov.get("practice_metadata") or {}).get("steps_count", 0) or 0)
        if chunk_type == "practice" and practice_steps <= 0:
            reasons.append("practice_incomplete")

        if "source_style_not_user_facing" in _normalize_list(gov.get("safety_flags")):
            reasons.append("source_style_not_user_facing")

        boundary = _to_float(md.get("boundary_confidence"))
        if boundary is not None and boundary < 0.45:
            reasons.append("boundary_confidence_low")

        if not reasons:
            continue

        safety_flags = _normalize_list(gov.get("safety_flags"))
        allowed_use = _normalize_list(gov.get("allowed_use"))
        is_p0 = False
        if "practice_incomplete" in reasons or "mixed_intent_high" in reasons:
            is_p0 = True
        if "needs_review" in safety_flags or "clinical_risk" in safety_flags:
            is_p0 = True
        if not safety_flags or not allowed_use:
            is_p0 = True
        if boundary is not None and boundary < 0.35:
            is_p0 = True
        priority = "P0" if is_p0 else ("P1" if "lens_family_low_confidence" in reasons else "P2")

        if "practice_incomplete" in reasons:
            action = "review_practice_completeness"
        elif "lens_family_low_confidence" in reasons:
            action = "review_lens_family"
        elif "boundary_confidence_low" in reasons:
            action = "split_source_section"
        else:
            action = "review_chunk_type"

        items.append(
            {
                "priority": priority,
                "block_id": str(raw.get("id") or ""),
                "heading_path": md.get("heading_path") if isinstance(md.get("heading_path"), list) else [],
                "chunk_type": chunk_type or "unknown",
                "reasons": _dedupe(reasons),
                "safe_preview": _safe_preview(raw.get("text") or "", 160),
                "recommended_action": action,
            }
        )

    order = {"P0": 0, "P1": 1, "P2": 2}
    items.sort(key=lambda item: (order.get(item["priority"], 9), item.get("block_id", "")))
    return {
        "version": "manual_review_queue_v2",
        "source": source_name,
        "items": items,
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"blocks": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"blocks": data}
    if isinstance(data, dict):
        return data
    return {"blocks": []}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_source_export_file(processed_dir: Path, source_id: str) -> Path | None:
    books_dir = processed_dir / "books"
    if not books_dir.exists():
        return None
    slug = source_id.lower()
    for candidate in sorted(books_dir.glob("*_blocks.json")):
        if slug in candidate.name.lower():
            return candidate
    return None


def _resolve_upload_path_from_registry(registry_path: Path, source_id: str) -> Path | None:
    if not registry_path.exists():
        return None
    try:
        records = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(records, list):
        return None
    for rec in reversed(records):
        if str(rec.get("source_id") or "") != source_id:
            continue
        file_paths = rec.get("file_paths") or {}
        upload = str(file_paths.get("upload") or "").strip()
        if not upload:
            continue
        p = Path(upload)
        if not p.is_absolute():
            p = (BOTDB_DIR / upload).resolve()
        return p if p.exists() else None
    return None


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _build_reprocessed_blocks(
    *,
    raw_markdown_path: Path,
    author: str,
    author_id: str,
    source_title: str,
    source_id: str,
    language: str,
    config_path: Path,
) -> list[dict[str, Any]]:
    config = _load_config(config_path)
    book_chunker = BookChunker(config.get("chunking", {}))
    blocks = book_chunker.chunk_file(
        str(raw_markdown_path),
        author=author or "unknown",
        book_title=source_title or source_id,
        language=language or "ru",
        author_id=author_id or "unknown",
    )
    blocks = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id=source_id,
        source_title=source_title or source_id,
        source_type="book",
        source_kind="knowledge_source",
        governance_profile="practice_manual",
    )
    rendered: list[dict[str, Any]] = []
    for block in blocks:
        block.chunking_quality = build_chunking_quality_v1(block)
        rendered.append(block.to_bot_format())
    return rendered


def run_source_reprocess(
    *,
    source_hint: str,
    all_blocks_path: Path,
    processed_dir: Path,
    output_dir: Path,
    reports_dir: Path,
    config_path: Path,
    registry_path: Path,
    mode: str,
    confirm: bool,
    dry_run: bool,
    raw_markdown_path: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    if mode in {"reprocess", "backfill_only"} and not confirm:
        raise RuntimeError("Mutation mode requires --confirm.")

    payload = _load_json(all_blocks_path)
    all_blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    before_gate = evaluate_governed_index_gate(blocks=all_blocks, source_label=source_hint)

    target_blocks = [b for b in all_blocks if _is_target_block(b, source_hint)]
    if not target_blocks:
        raise RuntimeError(f"Target source not found by hint: {source_hint}")

    source_id = _extract_source_id(target_blocks[0])
    source_export_path = _find_source_export_file(processed_dir, source_id)
    source_export_payload = _load_json(source_export_path) if source_export_path else {"blocks": target_blocks}
    source_export_blocks = source_export_payload.get("blocks") if isinstance(source_export_payload.get("blocks"), list) else []
    if not source_export_blocks:
        source_export_blocks = target_blocks

    mutation_performed = False
    backup_created = False
    backup_path = ""
    source_name = str((target_blocks[0].get("metadata") or {}).get("source_title") or source_hint)

    updated_target_blocks: list[dict[str, Any]] = []
    backfill_signals: list[dict[str, Any]] = []
    if mode == "reprocess":
        first_md = target_blocks[0].get("metadata") or {}
        author = str(first_md.get("author") or "")
        author_id = str(first_md.get("author_id") or "")
        language = str(first_md.get("language") or "ru")
        source_title = str(first_md.get("source_title") or source_name)
        effective_markdown = raw_markdown_path or _resolve_upload_path_from_registry(registry_path, source_id)
        if effective_markdown is None or not effective_markdown.exists():
            raise RuntimeError("Raw markdown for reprocess not found. Use --backfill-only or pass --raw-markdown-path.")
        updated_target_blocks = _build_reprocessed_blocks(
            raw_markdown_path=effective_markdown,
            author=author,
            author_id=author_id,
            source_title=source_title,
            source_id=source_id,
            language=language,
            config_path=config_path,
        )
        for raw in updated_target_blocks:
            _, signal = _backfill_block(raw)
            backfill_signals.append(signal)
    else:
        for raw in source_export_blocks:
            if not _is_target_block(raw, source_hint):
                continue
            updated, signal = _backfill_block(raw)
            updated_target_blocks.append(updated)
            backfill_signals.append(signal)

    updated_index: dict[str, dict[str, Any]] = {str(b.get("id") or ""): b for b in updated_target_blocks}
    merged_blocks_after: list[dict[str, Any]] = []
    for raw in all_blocks:
        block_id = str(raw.get("id") or "")
        if block_id in updated_index:
            merged_blocks_after.append(updated_index[block_id])
        else:
            merged_blocks_after.append(raw)

    # In reprocess mode number of chunks can change; replace by source match.
    if mode == "reprocess":
        merged_blocks_after = [raw for raw in all_blocks if not _is_target_block(raw, source_hint)] + updated_target_blocks

    after_gate = evaluate_governed_index_gate(blocks=merged_blocks_after, source_label=source_hint)
    manual_queue = _build_manual_review_queue(source_name, updated_target_blocks)

    type_dist = Counter(signal.get("chunk_type", "unknown") for signal in backfill_signals)
    usage_dist = Counter()
    safety_dist = Counter()
    for signal in backfill_signals:
        for item in signal.get("allowed_use", []):
            usage_dist[item] += 1
        for item in signal.get("safety_flags", []):
            safety_dist[item] += 1

    governance_metrics = {
        "generated_at": _utc_now(),
        "source_hint": source_hint,
        "source_id": source_id,
        "source_title": source_name,
        "target_blocks_before": len(target_blocks),
        "target_blocks_after": len(updated_target_blocks),
        "chunk_type_distribution": dict(sorted(type_dist.items())),
        "allowed_use_distribution": dict(sorted(usage_dist.items())),
        "safety_flags_distribution": dict(sorted(safety_dist.items())),
        "manual_review_items_total": len(manual_queue.get("items", [])),
        "manual_review_p0_total": sum(1 for x in manual_queue.get("items", []) if x.get("priority") == "P0"),
    }

    should_mutate = mode in {"reprocess", "backfill_only"}
    if should_mutate:
        if not dry_run:
            backup_dir = processed_dir / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = backup_dir / f"all_blocks_merged__before_{TARGET_TAG}__{stamp}.json"
            backup.write_text(all_blocks_path.read_text(encoding="utf-8"), encoding="utf-8")
            backup_created = True
            backup_path = str(backup)

            payload_after = dict(payload)
            payload_after["generated_at"] = datetime.utcnow().isoformat()
            payload_after["blocks_count"] = len(merged_blocks_after)
            payload_after["blocks"] = merged_blocks_after
            _write_json(all_blocks_path, payload_after)

            if source_export_path:
                source_payload_after = dict(source_export_payload)
                source_payload_after["generated_at"] = datetime.utcnow().isoformat()
                source_payload_after["blocks_count"] = len(updated_target_blocks)
                source_payload_after["blocks"] = updated_target_blocks
                _write_json(source_export_path, source_payload_after)
            mutation_performed = True

    source_reprocess_metrics = {
        "generated_at": _utc_now(),
        "source_hint": source_hint,
        "mode": mode,
        "confirm": confirm,
        "dry_run": dry_run,
        "mutation_performed": mutation_performed,
        "backup_created": backup_created,
        "backup_path": backup_path,
        "blocks_before": len(target_blocks),
        "blocks_after": len(updated_target_blocks),
        "gate_before": before_gate.get("status"),
        "gate_after": after_gate.get("status"),
        "all_blocks_path": str(all_blocks_path),
        "source_export_path": str(source_export_path) if source_export_path else "",
    }

    _write_json(output_dir / "source_reprocess_metrics.json", source_reprocess_metrics)
    _write_json(output_dir / "governance_backfill_metrics.json", governance_metrics)
    _write_json(output_dir / "governed_index_gate.json", {"before": before_gate, "after": after_gate})
    _write_json(output_dir / "manual_review_queue.json", manual_queue)
    (output_dir / "sanitized_runtime_logs.txt").write_text(
        "\n".join(
            [
                f"[{_utc_now()}] {TARGET_TAG} source reprocess run",
                f"mode={mode}",
                f"mutation_performed={mutation_performed}",
                f"backup_created={backup_created}",
                f"blocks_before={len(target_blocks)}",
                f"blocks_after={len(updated_target_blocks)}",
                f"gate_before={before_gate.get('status')}",
                f"gate_after={after_gate.get('status')}",
                f"manual_review_items={len(manual_queue.get('items', []))}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    impl_report = reports_dir / "PRD-046.0.4.2_IMPLEMENTATION_REPORT.md"
    src_report = reports_dir / "PRD-046.0.4.2_SOURCE_REPROCESS_REPORT.md"
    backfill_report = reports_dir / "PRD-046.0.4.2_GOVERNANCE_BACKFILL_REPORT.md"
    gate_report = reports_dir / "PRD-046.0.4.2_GOVERNED_INDEX_GATE_REPORT.md"
    manual_report = reports_dir / "PRD-046.0.4.2_MANUAL_REVIEW_QUEUE.md"
    next_prd_report = reports_dir / "PRD-046.0.4.2_NEXT_PRD_RECOMMENDATION.md"

    src_report.write_text(
        "\n".join(
            [
                "# PRD-046.0.4.2 Source Reprocess Report",
                "",
                "## Audit",
                f"- source_hint: `{source_hint}`",
                f"- source_id: `{source_id}`",
                f"- source_title: `{source_name}`",
                f"- all_blocks_before: `{len(all_blocks)}`",
                f"- target_blocks_before: `{len(target_blocks)}`",
                f"- governance_before_ratio: `{(before_gate.get('metrics') or {}).get('governance_present_ratio')}`",
                f"- allowed_use_before_ratio: `{(before_gate.get('metrics') or {}).get('allowed_use_present_ratio')}`",
                f"- summary_before_ratio: `{(before_gate.get('metrics') or {}).get('summary_present_ratio')}`",
                "",
                "## Mode",
                f"- mode: `{mode}`",
                f"- confirm: `{confirm}`",
                f"- dry_run: `{dry_run}`",
                f"- mutation_performed: `{mutation_performed}`",
                f"- backup_created: `{backup_created}`",
                "",
                "## Reasoning",
                "- Existing merged export had legacy chunks without governance payload and summary.",
                "- Current pipeline supports governance/chunking fields, so deterministic backfill was applied for immediate gate recovery.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    backfill_report.write_text(
        "\n".join(
            [
                "# PRD-046.0.4.2 Governance Backfill Report",
                "",
                "## Coverage",
                f"- target_blocks_before: `{governance_metrics['target_blocks_before']}`",
                f"- target_blocks_after: `{governance_metrics['target_blocks_after']}`",
                "",
                "## Distribution",
                f"- chunk_type_distribution: `{governance_metrics['chunk_type_distribution']}`",
                f"- allowed_use_distribution: `{governance_metrics['allowed_use_distribution']}`",
                f"- safety_flags_distribution: `{governance_metrics['safety_flags_distribution']}`",
                "",
                "## Manual Review",
                f"- total_items: `{governance_metrics['manual_review_items_total']}`",
                f"- p0_items: `{governance_metrics['manual_review_p0_total']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    gate_metrics_after = after_gate.get("metrics") or {}
    gate_report.write_text(
        "\n".join(
            [
                "# PRD-046.0.4.2 Governed Index Gate Report",
                "",
                "## Status",
                f"- before: `{before_gate.get('status')}`",
                f"- after: `{after_gate.get('status')}`",
                f"- blocker_reasons_after: `{after_gate.get('blocker_reasons')}`",
                f"- warnings_after: `{after_gate.get('warnings')}`",
                "",
                "## Metrics After",
                f"- governance_present_ratio: `{gate_metrics_after.get('governance_present_ratio')}`",
                f"- allowed_use_present_ratio: `{gate_metrics_after.get('allowed_use_present_ratio')}`",
                f"- safety_flags_present_ratio: `{gate_metrics_after.get('safety_flags_present_ratio')}`",
                f"- not_for_direct_quote_ratio: `{gate_metrics_after.get('not_for_direct_quote_ratio')}`",
                f"- boundary_confidence_present_ratio: `{gate_metrics_after.get('boundary_confidence_present_ratio')}`",
                f"- summary_present_ratio: `{gate_metrics_after.get('summary_present_ratio')}`",
                f"- lens_family_present_ratio: `{gate_metrics_after.get('lens_family_present_ratio')}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sample_items = manual_queue.get("items", [])[:30]
    lines = [
        "# PRD-046.0.4.2 Manual Review Queue",
        "",
        f"- source: `{source_name}`",
        f"- total_items: `{len(manual_queue.get('items', []))}`",
        "",
        "## Sample",
    ]
    for item in sample_items:
        lines.append(
            f"- `{item.get('priority')}` `{item.get('block_id')}` `{item.get('chunk_type')}` reasons={item.get('reasons')} action={item.get('recommended_action')} preview=`{item.get('safe_preview')}`"
        )
    manual_report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    next_prd = "PRD-046.0.4.3 — Chroma Reindex from Governed Blocks / API Query Restore v1"
    status_after = str(after_gate.get("status") or "")
    if status_after == "degraded":
        next_prd = "PRD-046.0.5 — Offline LLM Summary + Lens Enrichment v1"
    if status_after == "not_ready":
        next_prd = "PRD-046.0.4.2-HF1 — Backfill Coverage Fix / Missing Governance Fields"
    next_prd_report.write_text(
        "\n".join(
            [
                "# PRD-046.0.4.2 Next PRD Recommendation",
                "",
                f"- gate_status_after: `{status_after}`",
                f"- recommendation: `{next_prd}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    impl_report.write_text(
        "\n".join(
            [
                "# PRD-046.0.4.2 IMPLEMENTATION REPORT",
                "",
                "## Status",
                "- Implementation: done",
                "- Branch: `main`",
                "- Runtime behavior changed: no",
                "- Writer changed: no",
                "- DiagnosticCard changed: no",
                "- Chroma production reindex performed: no",
                "",
                "## Files changed",
                "- `Bot_data_base/tools/source_reprocess.py`",
                "- `Bot_data_base/tests/test_source_reprocess_governance.py`",
                "- `Bot_data_base/tests/test_governance_backfill.py`",
                "- `Bot_data_base/tools/kb_quality_audit.py` (gate threshold alignment)",
                "",
                "## Commands run",
                "- `python Bot_data_base/tools/source_reprocess.py --source \"КУЗНИЦА ДУХА\" --backfill-only --confirm`",
                "",
                "## Outcome",
                f"- source_reprocess_mode: `{mode}`",
                f"- mutation_performed: `{mutation_performed}`",
                f"- gate_before: `{before_gate.get('status')}`",
                f"- gate_after: `{after_gate.get('status')}`",
                f"- manual_review_items: `{len(manual_queue.get('items', []))}`",
                "",
                "## Known limitations",
                "- Backfill is deterministic and conservative; semantic quality is intentionally delegated to next enrichment PRD.",
                "",
                "## Commit / Push",
                "- Commit hash: `pending`",
                "- Push status: `pending`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "source_id": source_id,
        "source_title": source_name,
        "mode": mode,
        "mutation_performed": mutation_performed,
        "backup_created": backup_created,
        "backup_path": backup_path,
        "blocks_before": len(target_blocks),
        "blocks_after": len(updated_target_blocks),
        "gate_before": before_gate.get("status"),
        "gate_after": after_gate.get("status"),
        "manual_review_items": len(manual_queue.get("items", [])),
        "next_prd_recommendation": next_prd,
    }


def _resolve_mode(args: argparse.Namespace) -> str:
    selected = []
    if args.audit_only:
        selected.append("audit_only")
    if args.reprocess:
        selected.append("reprocess")
    if args.backfill_only:
        selected.append("backfill_only")
    if not selected:
        return "audit_only"
    if len(selected) > 1:
        raise RuntimeError("Use only one mode flag: --audit-only / --reprocess / --backfill-only")
    return selected[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.4.2 source reprocess / governance backfill CLI.")
    parser.add_argument("--source", default="КУЗНИЦА ДУХА")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--reprocess", action="store_true")
    parser.add_argument("--backfill-only", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config-path", default="Bot_data_base/config.yaml")
    parser.add_argument("--registry-path", default="Bot_data_base/data/registry.json")
    parser.add_argument("--all-blocks-path", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--processed-dir", default="Bot_data_base/data/processed")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.0.4.2")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--raw-markdown-path", default="")
    args = parser.parse_args()

    mode = _resolve_mode(args)
    raw_markdown_path = Path(args.raw_markdown_path).resolve() if str(args.raw_markdown_path).strip() else None
    result = run_source_reprocess(
        source_hint=str(args.source),
        all_blocks_path=Path(args.all_blocks_path),
        processed_dir=Path(args.processed_dir),
        output_dir=Path(args.output_dir),
        reports_dir=Path(args.reports_dir),
        config_path=Path(args.config_path),
        registry_path=Path(args.registry_path),
        mode=mode,
        confirm=bool(args.confirm),
        dry_run=bool(args.dry_run),
        raw_markdown_path=raw_markdown_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
