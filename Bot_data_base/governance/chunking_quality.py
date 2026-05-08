from __future__ import annotations

from models.universal_block import UniversalBlock

_PRACTICE_MARKERS = (
    "практика",
    "упражнение",
    "техника",
    "шаг",
    "цель:",
    "время:",
)

_SAFETY_MARKERS = (
    "безопас",
    "кризис",
    "суицид",
    "самоповрежд",
    "не заменяет специалиста",
    "экстренная помощь",
)

_LENS_MARKERS = (
    "паттерн",
    "избегани",
    "триггер",
    "границ",
    "слепая зона",
)

_ARCHITECTURE_MARKERS = (
    "neo mindbot",
    "архитектур",
    "writer",
    "diagnostic center",
    "prompt",
)

_ROLE_KEYS = ("practice", "safety", "lens", "architecture")


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)


def _safe_practice_reference_in_safety(text: str) -> bool:
    lowered = (text or "").lower()
    if "не заменяет специалиста" in lowered and "практик" in lowered:
        return True
    if "эта практика" in lowered and "экстренн" in lowered:
        return True
    return False


def _normalize_primary_role(value: str) -> str:
    role = (value or "").strip().lower()
    return role if role in {"practice", "safety", "lens", "architecture", "case", "quote", "style", "theory", "unknown"} else "unknown"


def analyze_mixed_intent_v1(*, lowered_text: str, primary_role: str, section_role_hint: str = "") -> dict:
    lowered = (lowered_text or "").lower()
    primary = _normalize_primary_role(primary_role)
    hint = _normalize_primary_role(section_role_hint)
    strong_primary = hint not in {"", "unknown", "theory"} or primary not in {"", "unknown", "theory"}

    role_marker_counts = {
        "practice": _count_markers(lowered, _PRACTICE_MARKERS),
        "safety": _count_markers(lowered, _SAFETY_MARKERS),
        "lens": _count_markers(lowered, _LENS_MARKERS),
        "architecture": _count_markers(lowered, _ARCHITECTURE_MARKERS),
    }

    if primary == "safety" and _safe_practice_reference_in_safety(lowered):
        # "эта практика не заменяет специалиста" не должна давать высокий conflict
        role_marker_counts["practice"] = max(0, role_marker_counts["practice"] - 1)

    competing_roles = [
        role
        for role in _ROLE_KEYS
        if role != primary and role_marker_counts.get(role, 0) > 0
    ]
    secondary_role_markers = sorted(competing_roles)

    if not competing_roles:
        return {
            "mixed_intent_risk": False,
            "mixed_intent_severity": "none",
            "primary_role": primary,
            "secondary_role_markers": [],
            "role_marker_counts": role_marker_counts,
            "mixed_intent_reason": "single_role_markers",
        }

    strongest_secondary = max(role_marker_counts.get(role, 0) for role in competing_roles)
    strong_secondary_roles = [role for role in competing_roles if role_marker_counts.get(role, 0) >= 2]

    # Допустимый кейс: practice + 1 lens word в заголовке/контексте.
    if primary == "practice" and competing_roles == ["lens"] and strongest_secondary <= 1:
        return {
            "mixed_intent_risk": False,
            "mixed_intent_severity": "low",
            "primary_role": primary,
            "secondary_role_markers": secondary_role_markers,
            "role_marker_counts": role_marker_counts,
            "mixed_intent_reason": "practice_with_light_lens_reference",
        }

    # Допустимый кейс: safety section с одноразовым mention практики.
    if primary == "safety" and "practice" in competing_roles and strongest_secondary <= 1:
        return {
            "mixed_intent_risk": False,
            "mixed_intent_severity": "low",
            "primary_role": primary,
            "secondary_role_markers": secondary_role_markers,
            "role_marker_counts": role_marker_counts,
            "mixed_intent_reason": "safety_with_context_reference",
        }

    if len(strong_secondary_roles) >= 2:
        return {
            "mixed_intent_risk": True,
            "mixed_intent_severity": "high",
            "primary_role": primary,
            "secondary_role_markers": secondary_role_markers,
            "role_marker_counts": role_marker_counts,
            "mixed_intent_reason": "multiple_strong_secondary_roles",
        }

    if strong_secondary_roles:
        reason = "substantial_secondary_role_markers"
        if primary == "safety" and "practice" in strong_secondary_roles:
            reason = "safety_practice_mixed"
        return {
            "mixed_intent_risk": True,
            "mixed_intent_severity": "medium",
            "primary_role": primary,
            "secondary_role_markers": secondary_role_markers,
            "role_marker_counts": role_marker_counts,
            "mixed_intent_reason": reason,
        }

    if strong_primary:
        return {
            "mixed_intent_risk": False,
            "mixed_intent_severity": "low",
            "primary_role": primary,
            "secondary_role_markers": secondary_role_markers,
            "role_marker_counts": role_marker_counts,
            "mixed_intent_reason": "weak_secondary_with_strong_primary",
        }

    return {
        "mixed_intent_risk": True,
        "mixed_intent_severity": "medium",
        "primary_role": primary,
        "secondary_role_markers": secondary_role_markers,
        "role_marker_counts": role_marker_counts,
        "mixed_intent_reason": "ambiguous_primary_with_secondary_markers",
    }


def build_chunking_quality_v1(block: UniversalBlock) -> dict:
    text = (block.text or "").strip()
    title = (block.title or "").strip()
    char_count = len(text)
    approx_token_count = max(1, char_count // 4) if text else 0

    too_short = approx_token_count < 80
    too_long = approx_token_count > 1800
    has_heading = bool(title)
    has_summary = bool((block.summary or "").strip())

    heading_path_present = bool(block.heading_path)
    section_role_hint = (block.section_role_hint or "").strip().lower() or "unknown"
    boundary_confidence = float(block.boundary_confidence or 0.0)
    split_reason = (block.split_reason or "").strip()

    lowered = f"{' > '.join(block.heading_path or [])}\n{title}\n{text}".lower()
    primary_role = block.governance.get("chunk_type") or section_role_hint
    mixed = analyze_mixed_intent_v1(
        lowered_text=lowered,
        primary_role=str(primary_role or "unknown"),
        section_role_hint=section_role_hint,
    )

    possible_practice_split = (
        block.governance.get("chunk_type") == "practice"
        and not any(marker in lowered for marker in ("шаг 2", "шаг 3", "время:", "цель:"))
    )
    possible_context_fragment = char_count < 240 and text.endswith(":")
    practice_steps_preserved = split_reason in {"practice_preserved", "practice_step_split"}

    quality_notes: list[str] = []
    if too_short:
        quality_notes.append("too_short")
    if too_long:
        quality_notes.append("too_long")
    if not has_summary:
        quality_notes.append("missing_summary")
    if possible_practice_split:
        quality_notes.append("possible_practice_split")
    if possible_context_fragment:
        quality_notes.append("possible_context_fragment")
    if not heading_path_present:
        quality_notes.append("missing_heading_path")
    if section_role_hint in {"", "unknown"}:
        quality_notes.append("role_hint_unknown")
    if mixed.get("mixed_intent_risk"):
        quality_notes.append("mixed_intent_risk")
    if boundary_confidence < 0.55:
        quality_notes.append("low_boundary_confidence")
    if block.governance.get("chunk_type") == "practice" and not practice_steps_preserved:
        quality_notes.append("practice_steps_maybe_split")

    return {
        "schema_version": "chunking_quality_v1",
        "char_count": int(char_count),
        "approx_token_count": int(approx_token_count),
        "has_heading": has_heading,
        "has_summary": has_summary,
        "possible_practice_split": possible_practice_split,
        "possible_context_fragment": possible_context_fragment,
        "too_short": too_short,
        "too_long": too_long,
        "heading_path_present": heading_path_present,
        "section_role_hint": section_role_hint,
        "boundary_confidence": boundary_confidence,
        "split_reason": split_reason,
        "mixed_intent_risk": bool(mixed.get("mixed_intent_risk")),
        "mixed_intent_severity": str(mixed.get("mixed_intent_severity") or "none"),
        "primary_role": str(mixed.get("primary_role") or "unknown"),
        "secondary_role_markers": mixed.get("secondary_role_markers") or [],
        "mixed_intent_reason": str(mixed.get("mixed_intent_reason") or ""),
        "practice_steps_preserved": practice_steps_preserved,
        "role_marker_counts": mixed.get("role_marker_counts") or {},
        "quality_notes": quality_notes,
    }
