from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any


MECHANISM_METADATA_SCHEMA_VERSION = "mechanism_aware_v1"

CONTROLLED_CHUNK_TYPES = {
    "source_fragment",
    "concept",
    "mechanism",
    "diagnostic_lens",
    "dialogue_move",
    "practice",
    "anti_pattern",
    "safety",
    "case_example",
    "style_voice",
}

CONTROLLED_ALLOWED_USE = {
    "direct_to_writer",
    "internal_lens",
    "retrieval_seed",
    "diagnostic_hint",
    "practice_suggestion",
    "not_for_direct_quote",
    "internal_only",
}

CONTROLLED_VISIBILITY = {"writer_allowed", "internal_only", "source_only"}
CONTROLLED_QUOTE_POLICY = {"can_quote_short", "paraphrase_only", "internal_only", "do_not_use"}
CONTROLLED_INTENSITY = {"low", "medium", "high", "unknown"}

LEGACY_CHUNK_TYPE_MAP = {
    "theory": "concept",
    "principle": "concept",
    "protocol": "dialogue_move",
    "practice": "practice",
    "safety": "safety",
    "style": "style_voice",
    "case": "case_example",
    "quote": "source_fragment",
    "excluded": "anti_pattern",
    "architecture": "style_voice",
}

LEGACY_SOURCE_TYPE_MAP = {
    "book": "book",
    "books": "book",
    "youtube": "transcript",
    "manual": "manual",
    "notes": "note",
    "architecture_notes": "architecture_note",
}

LEGACY_ALLOWED_USE_MAP = {
    "writer_context": "direct_to_writer",
    "diagnostic_lens": "diagnostic_hint",
    "practice_suggestion": "practice_suggestion",
    "safety_protocol": "diagnostic_hint",
    "style_guidance": "internal_lens",
    "internal_only": "internal_only",
    "do_not_use": "internal_only",
}

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9][a-zA-Zа-яА-ЯёЁ0-9_-]{2,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

MECHANISM_HINT_MARKERS: dict[str, tuple[str, ...]] = {
    "control_as_safety": ("контрол", "держать все", "потеряю контроль"),
    "shame_as_wrong_visibility": ("стыд", "со мной что-то не так", "увидят какой я"),
    "panic_loss_of_control": ("паник", "не могу дышать", "страшно умереть"),
    "avoidance_as_protection": ("избег", "отклады", "не могу начать"),
    "perfectionism_as_safety": ("идеаль", "безошиб", "лучше всех"),
    "self_criticism_as_control": ("самокрит", "ругаю себя", "недостаточ"),
    "parental_gaze": ("мама", "папа", "родител", "смотрят на меня"),
}

EMOTIONAL_MARKERS: tuple[str, ...] = (
    "стыд",
    "вина",
    "страх",
    "тревог",
    "злость",
    "гнев",
    "боль",
    "пустот",
    "грусть",
)

BODY_MARKERS: tuple[str, ...] = (
    "тело",
    "дых",
    "груд",
    "живот",
    "дрож",
    "напряж",
    "замира",
    "сердце",
)

UNDERLYING_NEED_MARKERS: dict[str, tuple[str, ...]] = {
    "safety": ("безопас", "контрол", "опора"),
    "acceptance": ("принят", "стыд", "увидят"),
    "rest": ("нет сил", "устал", "истощ"),
    "autonomy": ("выбрать себя", "не хочу", "границ"),
}

PROTECTIVE_PART_MARKERS: dict[str, tuple[str, ...]] = {
    "controller": ("контрол", "держать все"),
    "critic": ("самокрит", "ругать себя", "обесцен"),
    "avoider": ("избег", "отклады", "не могу начать"),
    "freezer": ("замира", "ступор", "freeze"),
}


def _dedupe(items: list[Any] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in items or []:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe(list(value))
    raw = str(value).strip()
    if not raw:
        return []
    return _dedupe([part.strip() for part in raw.split(",") if part.strip()])


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _safe_preview(text: str, limit: int = 180) -> str:
    cleaned = _normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "..."


def _maybe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _legacy_source_type(metadata: dict[str, Any], source_trace: dict[str, Any]) -> str:
    for candidate in (
        metadata.get("source_type"),
        source_trace.get("source_type"),
        source_trace.get("source_kind"),
    ):
        normalized = str(candidate or "").strip().lower()
        if normalized:
            return LEGACY_SOURCE_TYPE_MAP.get(normalized, normalized)
    return "unknown"


def _legacy_chunk_type(governance: dict[str, Any], metadata: dict[str, Any], chunking_quality: dict[str, Any]) -> str:
    for candidate in (
        governance.get("chunk_type"),
        metadata.get("section_role_hint"),
        chunking_quality.get("primary_role"),
        chunking_quality.get("section_role_hint"),
    ):
        normalized = str(candidate or "").strip().lower()
        if normalized:
            return normalized
    return "unknown"


def _infer_normalized_chunk_type(legacy_chunk_type: str, title: str, text: str) -> str:
    lowered = f"{title} {text}".lower()
    if legacy_chunk_type == "lens":
        if any(token in lowered for token in ("как работает", "механизм", "цикл", "паттерн", "защищает")):
            return "mechanism"
        return "diagnostic_lens"
    if legacy_chunk_type in LEGACY_CHUNK_TYPE_MAP:
        return LEGACY_CHUNK_TYPE_MAP[legacy_chunk_type]
    return "concept"


def _infer_quote_policy(
    *,
    normalized_chunk_type: str,
    legacy_allowed_use: list[str],
    safety_flags: list[str],
) -> str:
    legacy_allowed = {item.lower() for item in legacy_allowed_use}
    safety = {item.lower() for item in safety_flags}
    if "do_not_use" in legacy_allowed:
        return "do_not_use"
    if normalized_chunk_type in {"style_voice", "diagnostic_lens"}:
        return "internal_only"
    if normalized_chunk_type == "source_fragment":
        return "paraphrase_only"
    if "not_for_direct_quote" in safety:
        return "paraphrase_only"
    return "can_quote_short"


def _map_allowed_use(
    *,
    normalized_chunk_type: str,
    legacy_allowed_use: list[str],
    safety_flags: list[str],
    quote_policy: str,
) -> list[str]:
    result: list[str] = []
    for item in legacy_allowed_use:
        mapped = LEGACY_ALLOWED_USE_MAP.get(str(item or "").strip().lower())
        if mapped:
            result.append(mapped)
    if "not_for_direct_quote" in {flag.lower() for flag in safety_flags}:
        result.append("not_for_direct_quote")
    if normalized_chunk_type == "source_fragment":
        result.append("retrieval_seed")
    if normalized_chunk_type == "mechanism":
        result.extend(["internal_lens", "retrieval_seed"])
    if normalized_chunk_type == "diagnostic_lens":
        result.extend(["internal_lens", "diagnostic_hint"])
    if normalized_chunk_type == "dialogue_move":
        result.extend(["direct_to_writer", "retrieval_seed"])
    if normalized_chunk_type == "practice":
        result.extend(["practice_suggestion", "retrieval_seed"])
    if normalized_chunk_type == "anti_pattern":
        result.extend(["internal_lens", "direct_to_writer"])
    if normalized_chunk_type == "safety":
        result.extend(["direct_to_writer", "diagnostic_hint"])
    if normalized_chunk_type == "case_example":
        result.extend(["internal_lens", "retrieval_seed"])
    if normalized_chunk_type == "style_voice":
        result.extend(["internal_lens", "internal_only"])
    if normalized_chunk_type == "concept":
        result.extend(["direct_to_writer", "retrieval_seed"])
    normalized = _dedupe(result)
    if normalized_chunk_type in {"source_fragment", "diagnostic_lens", "style_voice"}:
        normalized = [item for item in normalized if item != "direct_to_writer"]
    if quote_policy == "do_not_use":
        normalized = [item for item in normalized if item != "direct_to_writer"]
        normalized.append("internal_only")
    return normalized


def _infer_visibility(normalized_chunk_type: str, allowed_use: list[str]) -> str:
    allowed = {item.lower() for item in allowed_use}
    if "internal_only" in allowed:
        return "internal_only"
    if normalized_chunk_type == "source_fragment":
        return "source_only"
    return "writer_allowed"


def _infer_depth_level(
    *,
    normalized_chunk_type: str,
    legacy_depth_level: Any,
    text: str,
    quality_flags: list[str],
) -> int:
    try:
        candidate = int(legacy_depth_level)
    except (TypeError, ValueError):
        candidate = -1
    if candidate > 3:
        quality_flags.append("extended_depth_needs_manual_review")
        return 3
    if candidate >= 0:
        return candidate
    lowered = text.lower()
    if normalized_chunk_type == "safety":
        return 0
    if normalized_chunk_type == "practice":
        return 1
    if normalized_chunk_type in {"mechanism", "diagnostic_lens"}:
        return 2
    if any(token in lowered for token in ("внутренний ребенок", "родительский взгляд", "история детства")):
        return 3
    return 1 if normalized_chunk_type in {"concept", "dialogue_move", "anti_pattern"} else 0


def _infer_intensity(
    *,
    normalized_chunk_type: str,
    practice_metadata: dict[str, Any],
    text: str,
) -> str:
    lowered = text.lower()
    if normalized_chunk_type == "safety":
        return "high"
    if normalized_chunk_type == "practice":
        duration = str(practice_metadata.get("duration") or "")
        steps = list(practice_metadata.get("steps_short") or [])
        if any(token in lowered for token in ("глубоко", "травм", "регресс")):
            return "high"
        if len(steps) >= 4 or re.search(r"\b(1[1-9]|[2-9][0-9])\s*(мин|min)\b", duration.lower()):
            return "medium"
        return "low"
    return "unknown"


def _extract_terms(text: str, markers: tuple[str, ...], *, limit: int = 4) -> list[str]:
    lowered = text.lower()
    result: list[str] = []
    for marker in markers:
        if marker in lowered and marker not in result:
            result.append(marker)
        if len(result) >= limit:
            break
    return result


def _extract_labeled_markers(text: str, mapping: dict[str, tuple[str, ...]], *, limit: int = 4) -> list[str]:
    lowered = text.lower()
    result: list[str] = []
    for label, markers in mapping.items():
        if any(marker in lowered for marker in markers):
            result.append(label)
        if len(result) >= limit:
            break
    return result


def _extract_user_markers_examples(text: str, *, limit: int = 3) -> list[str]:
    examples: list[str] = []
    for sentence in _SENTENCE_RE.split(_normalize_text(text)):
        lowered = sentence.lower()
        if "я " in lowered or lowered.startswith("когда я") or lowered.startswith("мне "):
            examples.append(_safe_preview(sentence, limit=90))
        if len(examples) >= limit:
            break
    return examples


def _build_core_thesis(summary: str, text: str) -> str:
    normalized_summary = _normalize_text(summary)
    if normalized_summary:
        return _safe_preview(normalized_summary, limit=200)
    sentences = _SENTENCE_RE.split(_normalize_text(text))
    for sentence in sentences:
        if sentence.strip():
            return _safe_preview(sentence, limit=200)
    return ""


def _default_recommended_moves(chunk_type: str) -> list[str]:
    defaults = {
        "mechanism": ["name_the_protective_function", "translate_pattern_softly"],
        "diagnostic_lens": ["keep_as_internal_lens", "translate_without_diagnosis"],
        "dialogue_move": ["acknowledge_first", "move_one_step_forward"],
        "practice": ["offer_only_if_requested_or_timed", "keep_one_practice_max"],
        "anti_pattern": ["avoid_harmful_language", "replace_with_grounded_move"],
        "safety": ["stabilize_first", "prefer_safe_short_guidance"],
        "case_example": ["paraphrase_case_only", "keep_as_analogy"],
        "concept": ["explain_compactly", "ground_in_user_context"],
    }
    return list(defaults.get(chunk_type, []))


def _default_forbidden_moves(chunk_type: str) -> list[str]:
    defaults = {
        "mechanism": ["diagnose_the_user", "command_obedience"],
        "diagnostic_lens": ["expose_raw_lens", "present_as_fact_about_user"],
        "dialogue_move": ["skip_acknowledgement"],
        "practice": ["drop_deep_practice_without_timing", "stack_multiple_practices"],
        "anti_pattern": ["shame_the_protection"],
        "safety": ["argue_with_panic", "fake_certainty"],
        "style_voice": ["return_as_direct_rag_hit"],
    }
    return list(defaults.get(chunk_type, []))


def _default_response_intent(chunk_type: str) -> list[str]:
    defaults = {
        "mechanism": ["explain_pattern"],
        "diagnostic_lens": ["internal_orientation"],
        "dialogue_move": ["answer_shape"],
        "practice": ["practice_offer"],
        "anti_pattern": ["avoid_harm"],
        "safety": ["stabilization"],
        "case_example": ["analogy_support"],
        "concept": ["concept_explanation"],
    }
    return list(defaults.get(chunk_type, []))


def _default_writer_instruction(chunk_type: str) -> str:
    instructions = {
        "source_fragment": "Use as source trace or paraphrase seed only.",
        "concept": "Explain in your own words and ground it in the user's context.",
        "mechanism": "Treat as an explanatory lens, not as a diagnosis or command.",
        "diagnostic_lens": "Keep internal unless a safe paraphrase is clearly useful.",
        "dialogue_move": "Use as a move suggestion, not as a fixed reply template.",
        "practice": "Offer only when timing is appropriate and keep it bounded.",
        "anti_pattern": "Avoid the harmful move and prefer the safer alternative.",
        "safety": "Safety is higher priority than philosophy or style.",
        "case_example": "Use only as paraphrased analogy, never as direct citation.",
        "style_voice": "Internal style guidance only; do not surface as factual content.",
    }
    return instructions.get(chunk_type, "")


def _build_practice_metadata(governance: dict[str, Any], text: str) -> dict[str, Any]:
    legacy = governance.get("practice_metadata")
    payload = dict(legacy) if isinstance(legacy, dict) else {}
    steps: list[str] = []
    for line in str(text or "").splitlines():
        normalized = line.strip("-* \t")
        lowered = normalized.lower()
        if lowered.startswith("шаг") or re.match(r"^\d+[\).]", normalized):
            steps.append(_safe_preview(normalized, limit=80))
    if steps:
        payload["steps_short"] = steps[:5]
    payload.setdefault("goal", "")
    payload.setdefault("target_mechanisms", [])
    payload.setdefault("duration", str(payload.get("duration") or ""))
    payload.setdefault("preconditions", [])
    payload.setdefault("avoid_when", [])
    payload.setdefault("contraindications", [])
    payload.setdefault("follow_up_question", "")
    payload.setdefault("risk_if_wrong_timing", "")
    payload.setdefault("not_first_response", True)
    payload.setdefault("max_one_practice_per_answer", True)
    return payload


@dataclass
class MechanismAwareChunkMetadata:
    metadata_schema_version: str = MECHANISM_METADATA_SCHEMA_VERSION
    chunk_id: str = ""
    source_id: str = ""
    source_doc: str = ""
    source_type: str = "unknown"
    source_span: str = ""
    heading_path: list[str] = field(default_factory=list)
    parent_section_id: str = ""
    chunk_type: str = "concept"
    title: str = ""
    core_thesis: str = ""
    mechanism_hints: list[str] = field(default_factory=list)
    user_markers_examples: list[str] = field(default_factory=list)
    emotional_markers: list[str] = field(default_factory=list)
    body_markers: list[str] = field(default_factory=list)
    underlying_need: list[str] = field(default_factory=list)
    protective_parts: list[str] = field(default_factory=list)
    use_when: list[str] = field(default_factory=list)
    avoid_when: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    depth_level: int = 0
    intensity: str = "unknown"
    allowed_use: list[str] = field(default_factory=list)
    visibility: str = "writer_allowed"
    quote_policy: str = "paraphrase_only"
    response_intent: list[str] = field(default_factory=list)
    recommended_moves: list[str] = field(default_factory=list)
    forbidden_moves: list[str] = field(default_factory=list)
    writer_instruction: str = ""
    writer_can_ignore: bool = True
    related_chunks: list[str] = field(default_factory=list)
    safety_links: list[str] = field(default_factory=list)
    practice_links: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    confidence: float = 0.0
    quality_flags: list[str] = field(default_factory=list)
    governance_flags: list[str] = field(default_factory=list)
    practice: dict[str, Any] = field(default_factory=dict)
    source_trace: dict[str, Any] = field(default_factory=dict)
    legacy_metadata: dict[str, Any] = field(default_factory=dict)
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "heading_path",
            "mechanism_hints",
            "user_markers_examples",
            "emotional_markers",
            "body_markers",
            "underlying_need",
            "protective_parts",
            "use_when",
            "avoid_when",
            "contraindications",
            "allowed_use",
            "response_intent",
            "recommended_moves",
            "forbidden_moves",
            "related_chunks",
            "safety_links",
            "practice_links",
            "derived_from",
            "quality_flags",
            "governance_flags",
        ):
            payload[key] = _dedupe(payload.get(key, []))
        payload["depth_level"] = int(payload.get("depth_level", 0) or 0)
        payload["confidence"] = round(float(payload.get("confidence", 0.0) or 0.0), 3)
        payload["writer_can_ignore"] = bool(payload.get("writer_can_ignore", True))
        return payload


def build_schema_snapshot() -> dict[str, Any]:
    return {
        "metadata_schema_version": MECHANISM_METADATA_SCHEMA_VERSION,
        "required_fields": [
            "metadata_schema_version",
            "chunk_id",
            "source_id",
            "source_type",
            "chunk_type",
            "title",
            "core_thesis",
            "allowed_use",
            "visibility",
            "quote_policy",
            "depth_level",
        ],
        "quality_warning_fields": [
            "mechanism_hints",
            "use_when",
            "avoid_when",
            "contraindications",
            "writer_instruction",
            "source_trace",
        ],
        "controlled_vocabulary": {
            "chunk_type": sorted(CONTROLLED_CHUNK_TYPES),
            "allowed_use": sorted(CONTROLLED_ALLOWED_USE),
            "visibility": sorted(CONTROLLED_VISIBILITY),
            "quote_policy": sorted(CONTROLLED_QUOTE_POLICY),
            "intensity": sorted(CONTROLLED_INTENSITY),
        },
    }


def validate_mechanism_metadata(metadata: MechanismAwareChunkMetadata) -> dict[str, Any]:
    payload = metadata.to_dict()
    errors: list[str] = []
    warnings: list[str] = []

    if payload["metadata_schema_version"] != MECHANISM_METADATA_SCHEMA_VERSION:
        errors.append("invalid_metadata_schema_version")
    for field_name in ("chunk_id", "source_id", "source_type", "chunk_type", "title", "core_thesis"):
        if not _normalize_text(payload.get(field_name)):
            errors.append(f"missing_required_field:{field_name}")

    if payload["chunk_type"] not in CONTROLLED_CHUNK_TYPES:
        errors.append(f"invalid_chunk_type:{payload['chunk_type']}")
    if payload["visibility"] not in CONTROLLED_VISIBILITY:
        errors.append(f"invalid_visibility:{payload['visibility']}")
    if payload["quote_policy"] not in CONTROLLED_QUOTE_POLICY:
        errors.append(f"invalid_quote_policy:{payload['quote_policy']}")
    if payload["intensity"] not in CONTROLLED_INTENSITY:
        errors.append(f"invalid_intensity:{payload['intensity']}")
    if not 0 <= int(payload["depth_level"]) <= 3:
        errors.append(f"depth_level_out_of_range:{payload['depth_level']}")

    for item in payload["allowed_use"]:
        if item not in CONTROLLED_ALLOWED_USE:
            errors.append(f"invalid_allowed_use:{item}")

    allowed = set(payload["allowed_use"])
    chunk_type = payload["chunk_type"]
    if "practice_suggestion" in allowed and chunk_type != "practice":
        errors.append("practice_suggestion_requires_practice_chunk")
    if "internal_only" in allowed and "direct_to_writer" in allowed:
        errors.append("internal_only_conflicts_with_direct_to_writer")
    if chunk_type == "source_fragment" and "direct_to_writer" in allowed:
        errors.append("source_fragment_direct_to_writer_blocked")
    if chunk_type == "diagnostic_lens" and "direct_to_writer" in allowed:
        errors.append("diagnostic_lens_direct_to_writer_blocked")
    if payload["quote_policy"] == "do_not_use" and "direct_to_writer" in allowed:
        errors.append("quote_policy_do_not_use_blocks_direct_to_writer")
    if chunk_type == "style_voice" and "direct_to_writer" in allowed:
        errors.append("style_voice_cannot_be_direct_to_writer")

    practice_payload = payload.get("practice", {}) if isinstance(payload.get("practice"), dict) else {}
    if chunk_type == "practice":
        steps = list(practice_payload.get("steps_short") or [])
        if not steps:
            warnings.append("practice_missing_steps_short")
        if not list(practice_payload.get("avoid_when") or []):
            warnings.append("practice_missing_avoid_when")
        if payload["intensity"] == "high" and not list(practice_payload.get("contraindications") or []):
            errors.append("high_intensity_practice_requires_contraindications")
        if "direct_to_writer" in allowed and not list(practice_payload.get("preconditions") or []):
            warnings.append("practice_direct_to_writer_without_preconditions")

    if chunk_type == "diagnostic_lens":
        extra = payload.get("extra_metadata", {}) if isinstance(payload.get("extra_metadata"), dict) else {}
        if not _normalize_text(extra.get("safe_user_translation")):
            warnings.append("diagnostic_lens_missing_safe_user_translation")
        if not _normalize_text(extra.get("risk_if_exposed")):
            warnings.append("diagnostic_lens_missing_risk_if_exposed")
        if not _normalize_text(extra.get("allowed_writer_use")):
            warnings.append("diagnostic_lens_missing_allowed_writer_use")

    if payload["derived_from"] and not payload.get("source_trace"):
        errors.append("derived_chunk_requires_source_trace")

    if not payload["mechanism_hints"] and chunk_type in {"mechanism", "practice", "diagnostic_lens"}:
        warnings.append("missing_mechanism_hints")
    if not payload["use_when"] and chunk_type in {"concept", "mechanism", "practice", "dialogue_move"}:
        warnings.append("missing_use_when")
    if not payload["avoid_when"] and chunk_type in {"concept", "mechanism", "practice", "dialogue_move"}:
        warnings.append("missing_avoid_when")

    return {
        "errors": errors,
        "warnings": warnings,
        "status": "passed" if not errors else "failed",
    }


def adapt_block_to_mechanism_metadata(block: dict[str, Any]) -> tuple[MechanismAwareChunkMetadata, dict[str, Any]]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    chunking_quality = metadata.get("chunking_quality") if isinstance(metadata.get("chunking_quality"), dict) else {}
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    raw_text = str(block.get("text") or "")
    text = _normalize_text(raw_text)
    title = _normalize_text(block.get("title"))
    summary = _normalize_text(block.get("summary"))

    legacy_chunk_type = _legacy_chunk_type(governance, metadata, chunking_quality)
    normalized_chunk_type = _infer_normalized_chunk_type(legacy_chunk_type, title, text)
    quality_flags: list[str] = []

    quote_policy = _infer_quote_policy(
        normalized_chunk_type=normalized_chunk_type,
        legacy_allowed_use=_normalize_list(governance.get("allowed_use")),
        safety_flags=_normalize_list(governance.get("safety_flags")),
    )
    practice_payload = _build_practice_metadata(governance, raw_text) if normalized_chunk_type == "practice" else {}
    allowed_use = _map_allowed_use(
        normalized_chunk_type=normalized_chunk_type,
        legacy_allowed_use=_normalize_list(governance.get("allowed_use")),
        safety_flags=_normalize_list(governance.get("safety_flags")),
        quote_policy=quote_policy,
    )
    visibility = _infer_visibility(normalized_chunk_type, allowed_use)
    depth_level = _infer_depth_level(
        normalized_chunk_type=normalized_chunk_type,
        legacy_depth_level=governance.get("depth_level"),
        text=text,
        quality_flags=quality_flags,
    )
    intensity = _infer_intensity(
        normalized_chunk_type=normalized_chunk_type,
        practice_metadata=practice_payload,
        text=text,
    )
    heading_path = _normalize_list(metadata.get("heading_path"))
    parent_section_id = _normalize_text(metadata.get("parent_section_id"))
    source_id = _normalize_text(source_trace.get("source_id")) or _normalize_text(block.get("source")).split(":", 1)[-1]
    source_doc = _normalize_text(source_trace.get("source_title")) or _normalize_text(metadata.get("source_title"))
    source_type = _legacy_source_type(metadata, source_trace)
    if chunking_quality.get("too_short"):
        quality_flags.append("legacy_too_short")
    if not summary:
        quality_flags.append("missing_summary")

    lowered = f"{title} {summary} {text}".lower()
    mechanism_hints = _extract_labeled_markers(lowered, MECHANISM_HINT_MARKERS)
    emotional_markers = _extract_terms(lowered, EMOTIONAL_MARKERS)
    body_markers = _extract_terms(lowered, BODY_MARKERS)
    underlying_need = _extract_labeled_markers(lowered, UNDERLYING_NEED_MARKERS)
    protective_parts = _extract_labeled_markers(lowered, PROTECTIVE_PART_MARKERS)

    extra_metadata = {
        "legacy_chunk_type": legacy_chunk_type,
        "boundary_confidence": chunking_quality.get("boundary_confidence", metadata.get("boundary_confidence")),
        "split_reason": _normalize_text(chunking_quality.get("split_reason") or metadata.get("split_reason")),
        "safe_user_translation": "",
        "risk_if_exposed": "",
        "allowed_writer_use": "",
    }
    if normalized_chunk_type == "diagnostic_lens":
        extra_metadata["safe_user_translation"] = "Translate as a soft explanatory possibility, not as a diagnosis."
        extra_metadata["risk_if_exposed"] = "Raw lens can sound accusatory, definitive, or shaming."
        extra_metadata["allowed_writer_use"] = "Paraphrase gently if it clearly helps the user orient."

    recognized_governance_keys = {
        "schema_version",
        "chunk_type",
        "allowed_use",
        "safety_flags",
        "lens_family",
        "tags",
        "practice_metadata",
        "governance_notes",
        "source_trace",
        "depth_level",
    }
    legacy_metadata = {
        key: value
        for key, value in governance.items()
        if key not in recognized_governance_keys
    }
    if governance.get("lens_family"):
        legacy_metadata["legacy_lens_family"] = _normalize_list(governance.get("lens_family"))

    metadata_obj = MechanismAwareChunkMetadata(
        chunk_id=_normalize_text(block.get("id") or block.get("chunk_id")),
        source_id=source_id,
        source_doc=source_doc,
        source_type=source_type,
        source_span=f"chunk_index:{metadata.get('chunk_index', '')}",
        heading_path=heading_path,
        parent_section_id=parent_section_id,
        chunk_type=normalized_chunk_type,
        title=title or _safe_preview(text, limit=80),
        core_thesis=_build_core_thesis(summary, text),
        mechanism_hints=mechanism_hints,
        user_markers_examples=_extract_user_markers_examples(raw_text),
        emotional_markers=emotional_markers,
        body_markers=body_markers,
        underlying_need=underlying_need,
        protective_parts=protective_parts,
        use_when=[f"Use when chunk_type={normalized_chunk_type} is relevant to the user's context."],
        avoid_when=["Avoid treating this metadata as deterministic routing."],
        contraindications=list(practice_payload.get("contraindications") or []),
        depth_level=depth_level,
        intensity=intensity,
        allowed_use=allowed_use,
        visibility=visibility,
        quote_policy=quote_policy,
        response_intent=_default_response_intent(normalized_chunk_type),
        recommended_moves=_default_recommended_moves(normalized_chunk_type),
        forbidden_moves=_default_forbidden_moves(normalized_chunk_type),
        writer_instruction=_default_writer_instruction(normalized_chunk_type),
        writer_can_ignore=True,
        related_chunks=[],
        safety_links=[],
        practice_links=[],
        derived_from=[],
        confidence=0.66 if summary else 0.54,
        quality_flags=_dedupe(quality_flags),
        governance_flags=_dedupe(_normalize_list(governance.get("safety_flags"))),
        practice=practice_payload,
        source_trace=dict(source_trace),
        legacy_metadata=legacy_metadata,
        extra_metadata=extra_metadata,
    )
    validation = validate_mechanism_metadata(metadata_obj)
    metadata_obj.quality_flags = _dedupe(metadata_obj.quality_flags + validation["warnings"])
    return metadata_obj, validation


def sanitize_metadata_preview(metadata: MechanismAwareChunkMetadata) -> dict[str, Any]:
    payload = metadata.to_dict()
    return {
        "chunk_id": payload["chunk_id"],
        "source_id": payload["source_id"],
        "title": _safe_preview(payload["title"], limit=100),
        "core_thesis": _safe_preview(payload["core_thesis"], limit=180),
        "chunk_type": payload["chunk_type"],
        "mechanism_hints": list(payload["mechanism_hints"]),
        "allowed_use": list(payload["allowed_use"]),
        "visibility": payload["visibility"],
        "quote_policy": payload["quote_policy"],
        "depth_level": payload["depth_level"],
        "intensity": payload["intensity"],
        "quality_flags": list(payload["quality_flags"]),
        "legacy_metadata_keys": sorted(payload["legacy_metadata"].keys()),
    }


def metadata_to_stable_json(metadata: MechanismAwareChunkMetadata) -> str:
    return json.dumps(metadata.to_dict(), ensure_ascii=False, sort_keys=True)
