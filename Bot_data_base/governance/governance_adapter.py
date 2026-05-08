from __future__ import annotations

import re
from typing import Iterable

from governance.chunking_quality import analyze_mixed_intent_v1
from models.universal_block import UniversalBlock

_ALLOWED_PROFILES = {
    "general_book",
    "practice_manual",
    "architecture_notes",
    "transcript",
}

_PROFILE_DEFAULTS: dict[str, dict[str, list[str]]] = {
    "practice_manual": {
        "allowed_use": ["writer_context", "diagnostic_lens"],
        "safety_flags": ["requires_grounding", "not_for_direct_quote"],
    },
    "architecture_notes": {
        "allowed_use": ["internal_only", "style_guidance", "diagnostic_lens"],
        "safety_flags": ["source_style_not_user_facing", "not_for_direct_quote"],
    },
    "general_book": {
        "allowed_use": ["writer_context"],
        "safety_flags": ["not_for_direct_quote"],
    },
    "transcript": {
        "allowed_use": ["writer_context", "diagnostic_lens"],
        "safety_flags": ["requires_grounding", "not_for_direct_quote"],
    },
}

_PRACTICE_MARKERS = (
    "практика",
    "упражнение",
    "техника",
    "шаг",
    "цель:",
    "время:",
    "минут",
    "дыхание",
    "заземление",
)

_LENS_MARKERS = (
    "избегани",
    "паттерн",
    "сценар",
    "триггер",
    "границ",
    "ценност",
    "самооцен",
    "самоценност",
    "слепая зона",
)

_SAFETY_MARKERS = (
    "кризис",
    "суицид",
    "самоповреждени",
    "не заменяет специалиста",
    "экстренная помощь",
    "безопасность",
)

_STRONG_CLAIM_MARKERS = (
    "всегда",
    "никогда",
    "единственный",
    "гарантированно",
)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _count_any(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)


def normalize_governance_profile(value: str | None, fallback: str = "general_book") -> str:
    candidate = (value or "").strip().lower()
    if candidate in _ALLOWED_PROFILES:
        return candidate
    return fallback if fallback in _ALLOWED_PROFILES else "general_book"


def _extract_line_value(text: str, prefixes: tuple[str, ...]) -> str:
    for line in (text or "").splitlines():
        normalized = line.strip()
        low = normalized.lower()
        for prefix in prefixes:
            if low.startswith(prefix):
                return normalized.split(":", 1)[-1].strip() if ":" in normalized else normalized
    return ""


def _extract_duration_minutes(duration_text: str, lowered: str) -> int | None:
    candidate = duration_text or lowered
    match = re.search(r"(\d{1,3})\s*(мин|minute|min)", candidate)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return None
    return None


def _extract_practice_metadata(text: str) -> dict:
    lowered = (text or "").lower()

    goal = _extract_line_value(text, ("цель:", "goal:"))
    duration = _extract_line_value(text, ("время:", "duration:"))
    if not duration:
        duration_match = re.search(r"(\d{1,3}\s*(?:мин|minute|min))", lowered)
        duration = duration_match.group(1) if duration_match else ""

    steps_count = len(re.findall(r"(?:шаг|step)\s*\d+", lowered))
    if steps_count == 0:
        numbered_steps = re.findall(r"(?m)^\s*(?:\d+[\).]|[-*•])\s+", text or "")
        steps_count = len(numbered_steps)

    requires_journaling = any(m in lowered for m in ("дневник", "запиши", "journal", "письменно"))
    body_based = any(marker in lowered for marker in ("дых", "тело", "телес", "зазем", "ощущ"))

    channel_scores = {
        "body": _count_any(lowered, ("дых", "тело", "зазем", "ощущ")),
        "thinking": _count_any(lowered, ("запиши", "дневник", "ответь письменно", "проанализ")),
        "action": _count_any(lowered, ("сделай", "отправь", "выбери", "начни", "микрошаг")),
        "relationship": _count_any(lowered, ("диалог", "поговори", "отношен", "границ")),
    }
    best_channel = "unknown"
    if any(score > 0 for score in channel_scores.values()):
        sorted_channels = sorted(channel_scores.items(), key=lambda item: item[1], reverse=True)
        if len(sorted_channels) >= 2 and sorted_channels[0][1] == sorted_channels[1][1] and sorted_channels[0][1] > 0:
            best_channel = "mixed"
        else:
            best_channel = sorted_channels[0][0]

    duration_minutes = _extract_duration_minutes(duration, lowered)
    low_resource_safe = bool(
        body_based
        and steps_count > 0
        and steps_count <= 3
        and duration_minutes is not None
        and duration_minutes <= 10
        and not requires_journaling
    )

    return {
        "goal": goal,
        "duration": duration,
        "steps_count": int(steps_count),
        "requires_journaling": requires_journaling,
        "body_based": body_based,
        "low_resource_safe": low_resource_safe,
        "channel": best_channel,
    }


def _resolve_chunk_type(role_hint: str, lowered: str, source_kind_normalized: str, source_title_lower: str) -> str:
    role_map = {
        "safety": "safety",
        "practice": "practice",
        "architecture": "style",
        "lens": "lens",
        "case": "case",
        "quote": "quote",
        "theory": "theory",
    }
    role_value = role_map.get((role_hint or "").strip().lower())
    if role_value:
        return role_value

    if _contains_any(lowered, _SAFETY_MARKERS):
        return "safety"
    if _contains_any(lowered, _PRACTICE_MARKERS):
        return "practice"
    if _contains_any(lowered, _LENS_MARKERS):
        return "lens"

    if source_kind_normalized == "architecture_notes" or "neo mindbot" in source_title_lower:
        return "style"

    return "theory"


def _build_allowed_use(
    *,
    base_allowed: list[str],
    chunk_type: str,
    architecture_profile: bool,
    safety_flags: list[str],
) -> list[str]:
    allowed = list(base_allowed)

    if chunk_type == "practice":
        allowed.append("practice_suggestion")
    elif chunk_type == "safety":
        allowed.extend(["safety_protocol", "writer_context"])
    elif chunk_type == "style":
        allowed.append("style_guidance")
        if architecture_profile:
            allowed.append("internal_only")
    elif chunk_type == "lens":
        allowed.append("diagnostic_lens")
    elif chunk_type == "case":
        allowed.extend(["writer_context", "diagnostic_lens"])
    elif chunk_type == "quote":
        if "not_for_direct_quote" in safety_flags:
            allowed.append("writer_context")
    elif chunk_type == "excluded":
        allowed = ["do_not_use"]

    # Precision guard: practice_suggestion only for explicit practice chunks.
    if chunk_type != "practice":
        allowed = [item for item in allowed if item != "practice_suggestion"]

    return _dedupe(allowed)


def apply_governance_to_blocks_v1(
    *,
    blocks: list[UniversalBlock],
    source_id: str,
    source_title: str,
    source_type: str,
    source_kind: str | None = None,
    governance_profile: str | None = None,
    default_allowed_use: list[str] | None = None,
    default_safety_flags: list[str] | None = None,
) -> list[UniversalBlock]:
    """
    Attach deterministic governance metadata to each block.

    Local adapter is intentionally independent from bot_psychologist runtime imports
    to avoid brittle cross-service dependency in production ingestion path.
    """
    profile = normalize_governance_profile(governance_profile, fallback="general_book")
    profile_defaults = _PROFILE_DEFAULTS.get(profile, _PROFILE_DEFAULTS["general_book"])

    profile_allowed = default_allowed_use or profile_defaults["allowed_use"]
    profile_flags = default_safety_flags or profile_defaults["safety_flags"]

    source_kind_normalized = (source_kind or "").strip().lower()
    source_title_lower = (source_title or "").lower()

    for idx, block in enumerate(blocks):
        title = (block.title or "").strip()
        text = (block.text or "").strip()
        heading_text = " > ".join(block.heading_path or [])
        role_hint = (block.section_role_hint or "").strip().lower()

        lowered = f"{heading_text}\n{block.chapter_title}\n{title}\n{text}".lower()

        chunk_type = _resolve_chunk_type(role_hint, lowered, source_kind_normalized, source_title_lower)
        notes: list[str] = []
        safety_flags = list(profile_flags)
        lens_family: list[str] = []
        tags: list[str] = []
        practice_metadata: dict = {}

        architecture_profile = source_kind_normalized == "architecture_notes" or "neo mindbot" in source_title_lower
        if architecture_profile:
            safety_flags.extend(["source_style_not_user_facing", "not_for_direct_quote"])
            notes.append("architecture_profile")
            if chunk_type == "theory":
                chunk_type = "style"

        if chunk_type == "safety":
            notes.append("safety_marker")
            lens_family.append("safety")

        if chunk_type == "practice":
            notes.append("practice_marker")
            lens_family.append("somatic")
            practice_metadata = _extract_practice_metadata(text)
            if not practice_metadata.get("low_resource_safe", False):
                safety_flags.append("practice_requires_low_resource_check")

        if chunk_type == "lens":
            safety_flags.append("requires_grounding")
            notes.append("lens_marker")
            if "избегани" in lowered:
                lens_family.append("avoidance")
            if "ценност" in lowered or "самооцен" in lowered or "самоценност" in lowered:
                lens_family.append("self_worth")

        if _contains_any(lowered, _STRONG_CLAIM_MARKERS):
            safety_flags.append("not_for_direct_quote")
            notes.append("strong_claim_marker")

        safety_flags = _dedupe(safety_flags)
        allowed_use = _build_allowed_use(
            base_allowed=list(profile_allowed),
            chunk_type=chunk_type,
            architecture_profile=architecture_profile,
            safety_flags=safety_flags,
        )

        mixed = analyze_mixed_intent_v1(
            lowered_text=lowered,
            primary_role=chunk_type,
            section_role_hint=role_hint,
        )
        if mixed.get("mixed_intent_risk"):
            notes.append("mixed_intent_risk")
        if chunk_type == "safety" and mixed.get("mixed_intent_reason") == "safety_practice_mixed":
            notes.append("safety_practice_mixed")

        lens_family = _dedupe(lens_family)
        tags = _dedupe(tags + [chunk_type] + lens_family)

        block.governance = {
            "schema_version": "governance_v1",
            "chunk_type": chunk_type,
            "allowed_use": allowed_use,
            "safety_flags": safety_flags,
            "lens_family": lens_family,
            "tags": tags,
            "practice_metadata": practice_metadata,
            "governance_notes": _dedupe(notes),
            "source_trace": {
                "source_id": source_id,
                "source_title": source_title,
                "source_type": source_type,
                "source_kind": source_kind_normalized or profile,
                "chunk_index": int(idx),
                "adapter": "bot_data_base_governance_adapter_v1",
            },
        }

    return blocks
