"""Rule-based governance classification for knowledge chunks."""

from __future__ import annotations

import re
from typing import Any

from .contracts import KnowledgeSourceManifest


_LENS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "act": ("приняти", "acceptance", "commitment"),
    "ifs": ("части", "self", "inner family"),
    "somatic": ("тело", "дыхани", "телес", "body", "breath"),
    "aqal": ("aqal", "интеграл", "квадрант"),
    "mct": ("metacognitive", "метакогнит"),
    "neurobiology": ("нейрохим", "нейроби", "нервн"),
    "instincts": ("инстинкт", "instinct"),
    "fear": ("страх", "fear"),
    "avoidance": ("избеган", "avoid"),
    "inner_program": ("программ", "сценар", "установка"),
    "self_worth": ("ценность", "достоинство", "самооцен"),
    "dopamine": ("дофамин", "dopamine"),
    "attention": ("вниман", "attention", "focus"),
    "values": ("ценност", "values"),
    "boundaries": ("границ", "boundar"),
    "relationship": ("отношен", "relationship"),
    "safety": ("безопас", "кризис", "safety"),
    "style": ("стиль", "tone", "language"),
    "architecture": ("architecture", "архитектур", "contract", "pipeline"),
}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _first_match(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _extract_practice_metadata(text: str) -> dict[str, Any]:
    lowered = text.lower()
    goal_match = re.search(r"(?:цель|goal)\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
    duration_match = re.search(r"(?:время|duration)\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
    steps_count = len(re.findall(r"(?m)^\s*(?:шаг\s*\d+|\d+[\.)])", lowered))
    requires_journaling = any(marker in lowered for marker in ("запиши", "дневник", "journal"))
    body_based = any(marker in lowered for marker in ("дых", "тело", "телес", "body", "breath"))
    long_reflective = len(text) > 1200 or requires_journaling
    low_resource_safe = body_based and steps_count <= 3 and not long_reflective
    return {
        "goal": goal_match.group(1).strip()[:220] if goal_match else "",
        "duration": duration_match.group(1).strip()[:120] if duration_match else "",
        "steps_count": int(steps_count),
        "requires_journaling": bool(requires_journaling),
        "body_based": bool(body_based),
        "low_resource_safe": bool(low_resource_safe),
    }


def classify_chunk_governance_v1(
    chunk_text: str,
    heading_path: list[str],
    manifest: KnowledgeSourceManifest,
) -> dict[str, Any]:
    """Classify one chunk into governance fields using deterministic rules."""
    heading = " / ".join(heading_path).strip()
    lowered = f"{heading}\n{chunk_text}".lower()
    source_title = (manifest.title or "").lower()
    source_kind = (manifest.source_kind or "other").lower()

    chunk_type = "theory"
    governance_notes: list[str] = []
    if _first_match(lowered, ("не использовать", "do not use", "excluded")):
        chunk_type = "excluded"
        governance_notes.append("explicit_exclusion_marker")
    elif _first_match(lowered, ("безопас", "кризис", "экстрен", "safety", "суицид")):
        chunk_type = "safety"
        governance_notes.append("safety_marker")
    elif _first_match(lowered, ("протокол", "protocol", "алгоритм действия")):
        chunk_type = "protocol"
        governance_notes.append("protocol_marker")
    elif _first_match(lowered, ("практик", "упражнен", "exercise", "шаг 1", "цель:", "время:")):
        chunk_type = "practice"
        governance_notes.append("practice_marker")
    elif _first_match(lowered, ("кейс", "случай", "пример", "case")):
        chunk_type = "case"
        governance_notes.append("case_marker")
    elif _first_match(lowered, ("цитат", "quote", "«")):
        chunk_type = "quote"
        governance_notes.append("quote_marker")
    elif _first_match(lowered, ("линз", "lens", "перспектив", "модель")):
        chunk_type = "lens"
        governance_notes.append("lens_marker")
    elif _first_match(lowered, ("принцип", "principle", "архитектур")):
        chunk_type = "principle"
        governance_notes.append("principle_marker")
    elif _first_match(lowered, ("стиль", "tone", "язык ответа", "формулировк")):
        chunk_type = "style"
        governance_notes.append("style_marker")

    safety_flags: list[str] = list(manifest.default_safety_flags or [])
    if _first_match(lowered, ("депресс", "диагноз", "расстройств", "биполяр", "птср", "нарцисс")):
        safety_flags.append("clinical_risk")
    if _first_match(lowered, ("должен", "обязан", "только так", "делай", "немедленно")):
        safety_flags.append("directive_risk")
    if _first_match(lowered, ("истинный путь", "духовн", "просветлен", "высшая истина", "абсолют")):
        safety_flags.append("spiritual_authority_risk")
    if _first_match(lowered, ("всегда", "никогда", "единственный", "гарантированно")):
        safety_flags.append("too_strong_claim")
    if _first_match(lowered, ("программа", "инстинкт", "нейрохим", "дофамин", "зависим", "dopamine")):
        safety_flags.append("requires_grounding")
    if source_kind == "architecture_notes" or "конспект" in source_title:
        safety_flags.append("source_style_not_user_facing")
    if any(flag in safety_flags for flag in ("clinical_risk", "spiritual_authority_risk", "too_strong_claim")):
        safety_flags.append("not_for_direct_quote")

    practice_metadata: dict[str, Any] = {}
    if chunk_type == "practice":
        practice_metadata = _extract_practice_metadata(chunk_text)
        if not practice_metadata.get("low_resource_safe", False):
            safety_flags.append("practice_requires_low_resource_check")
        if _first_match(lowered, ("задержка дыхания", "интенсив", "глубокая травма", "провокац")):
            safety_flags.append("practice_requires_contraindication_note")

    allowed_use = list(manifest.allowed_global_use or [])
    if source_kind == "architecture_notes" or "конспект" in source_title:
        allowed_use.extend(["internal_only", "style_guidance", "diagnostic_lens"])
    if chunk_type in {"safety", "protocol"}:
        allowed_use.extend(["safety_protocol", "writer_context"])
    elif chunk_type == "practice":
        allowed_use.extend(["practice_suggestion", "writer_context"])
    elif chunk_type in {"lens", "principle", "theory"}:
        allowed_use.extend(["diagnostic_lens", "writer_context"])
    elif chunk_type == "style":
        allowed_use.extend(["style_guidance", "internal_only"])
    elif chunk_type == "excluded":
        allowed_use = ["do_not_use"]

    if "source_style_not_user_facing" in safety_flags:
        allowed_use = [item for item in allowed_use if item != "practice_suggestion"]
        allowed_use.append("internal_only")
    if "not_for_direct_quote" in safety_flags:
        governance_notes.append("direct_quote_not_allowed")

    tags: list[str] = []
    lens_family: list[str] = []
    for lens, markers in _LENS_KEYWORDS.items():
        if _first_match(lowered, markers):
            lens_family.append(lens)
            tags.append(lens)
    if chunk_type:
        tags.append(chunk_type)

    return {
        "chunk_type": chunk_type,
        "allowed_use": _dedupe(allowed_use) or ["internal_only"],
        "safety_flags": _dedupe(safety_flags),
        "tags": _dedupe(tags),
        "lens_family": _dedupe(lens_family),
        "practice_metadata": practice_metadata,
        "governance_notes": _dedupe(governance_notes),
    }
