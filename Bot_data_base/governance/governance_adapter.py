from __future__ import annotations

from typing import Iterable

from models.universal_block import UniversalBlock

_ALLOWED_PROFILES = {
    "general_book",
    "practice_manual",
    "architecture_notes",
    "transcript",
}

_PROFILE_DEFAULTS: dict[str, dict[str, list[str]]] = {
    "practice_manual": {
        "allowed_use": ["diagnostic_lens", "writer_context", "practice_suggestion"],
        "safety_flags": ["requires_grounding", "not_for_direct_quote"],
    },
    "architecture_notes": {
        "allowed_use": ["internal_only", "style_guidance", "safety_protocol", "diagnostic_lens"],
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


def normalize_governance_profile(value: str | None, fallback: str = "general_book") -> str:
    candidate = (value or "").strip().lower()
    if candidate in _ALLOWED_PROFILES:
        return candidate
    return fallback if fallback in _ALLOWED_PROFILES else "general_book"


def _extract_practice_metadata(text: str) -> dict:
    lowered = text.lower()
    steps_count = lowered.count("шаг ")
    body_based = any(marker in lowered for marker in ("дых", "тело", "телес", "зазем"))
    low_resource_safe = body_based and steps_count <= 3 and len(text) <= 1800
    return {
        "goal": "",
        "duration": "",
        "steps_count": int(steps_count),
        "requires_journaling": any(m in lowered for m in ("дневник", "запиши", "journal")),
        "body_based": body_based,
        "low_resource_safe": low_resource_safe,
    }


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
        lowered = f"{title}\n{text}".lower()

        chunk_type = "theory"
        notes: list[str] = []
        allowed_use = list(profile_allowed)
        safety_flags = list(profile_flags)
        lens_family: list[str] = []
        tags: list[str] = []
        practice_metadata: dict = {}

        if _contains_any(lowered, _SAFETY_MARKERS):
            chunk_type = "safety"
            allowed_use.append("safety_protocol")
            notes.append("safety_marker")
            lens_family.append("safety")

        if _contains_any(lowered, _PRACTICE_MARKERS):
            chunk_type = "practice"
            allowed_use.append("practice_suggestion")
            notes.append("practice_marker")
            lens_family.append("somatic")
            practice_metadata = _extract_practice_metadata(text)
            if not practice_metadata.get("low_resource_safe", False):
                safety_flags.append("practice_requires_low_resource_check")

        if chunk_type == "theory" and _contains_any(lowered, _LENS_MARKERS):
            chunk_type = "lens"
            allowed_use.append("diagnostic_lens")
            safety_flags.append("requires_grounding")
            notes.append("lens_marker")
            if "избегани" in lowered:
                lens_family.append("avoidance")
            if "ценност" in lowered or "самооцен" in lowered or "самоценност" in lowered:
                lens_family.append("self_worth")

        if source_kind_normalized == "architecture_notes" or "neo mindbot" in source_title_lower:
            allowed_use.extend(["internal_only", "style_guidance"])
            safety_flags.extend(["source_style_not_user_facing", "not_for_direct_quote"])
            notes.append("architecture_profile")
            if chunk_type == "theory":
                chunk_type = "style"
            lens_family.append("architecture")

        if _contains_any(lowered, _STRONG_CLAIM_MARKERS):
            safety_flags.append("not_for_direct_quote")
            notes.append("strong_claim_marker")

        if chunk_type == "safety":
            allowed_use.append("writer_context")

        allowed_use = _dedupe(allowed_use)
        safety_flags = _dedupe(safety_flags)
        lens_family = _dedupe(lens_family)
        tags = _dedupe(tags + [chunk_type] + lens_family)
        if chunk_type == "practice" and "practice_suggestion" not in allowed_use:
            allowed_use.append("practice_suggestion")

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
