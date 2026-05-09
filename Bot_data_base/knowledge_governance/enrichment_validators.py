from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .enrichment_contracts import EnrichmentCandidate


LENS_FAMILY_ALLOWLIST = {
    "shame",
    "guilt",
    "anger",
    "grief",
    "fear_of_rejection",
    "self_criticism",
    "avoidance",
    "procrastination",
    "perfectionism",
    "achievement",
    "boundaries",
    "relationships",
    "attachment",
    "loneliness",
    "body_awareness",
    "hyperarousal",
    "hypoarousal",
    "low_resource",
    "burnout",
    "control",
    "inner_parts",
    "identity",
    "meaning",
    "values",
    "rumination",
    "anxiety",
    "freeze",
    "safety",
    "practice_integration",
}

SUMMARY_BANNED_PREFIXES = (
    "в данном тексте",
    "автор говорит",
    "книга рассказывает",
    "согласно кузнице",
)
FORBIDDEN_ARTIFACT_KEYS = (
    "content_full",
    "raw_full_text",
    "full_chunk_text",
    "raw_llm_prompt_with_text",
    "api_key",
    "openai_api_key",
    "dotenv",
)

_LOW_RESOURCE_TERMS = ("low resource", "мало сил", "нет сил", "кризис", "нестабил")
SUMMARY_DIRECT_QUOTE_PREFIX_CHARS = 80
SUMMARY_DIRECT_QUOTE_MIN_LENGTH = 80


@dataclass
class ValidationResult:
    passed: bool
    reasons: list[str]
    warnings: list[str]
    reason_details: dict[str, str] = field(default_factory=dict)


def _normalize_tag(value: str) -> str:
    raw = str(value or "").strip().lower()
    raw = re.sub(r"\s+", "_", raw)
    raw = re.sub(r"[^a-z0-9а-я_]+", "", raw)
    return raw


def _looks_like_long_quote(candidate_summary: str, source_text: str) -> tuple[bool, str]:
    summary = " ".join(str(candidate_summary or "").split())
    if len(summary) < SUMMARY_DIRECT_QUOTE_MIN_LENGTH:
        return False, ""
    source = " ".join(str(source_text or "").split())
    if summary[:SUMMARY_DIRECT_QUOTE_PREFIX_CHARS] in source:
        return True, "prefix_overlap"
    return False, ""


def validate_candidate(
    *,
    candidate: EnrichmentCandidate,
    source_text: str,
) -> ValidationResult:
    reasons: list[str] = []
    warnings: list[str] = []
    reason_details: dict[str, str] = {}

    summary = str(candidate.summary_candidate or "").strip()
    if not summary:
        reasons.append("summary_empty")
    if len(summary) < 120:
        warnings.append("summary_too_short")
    if len(summary) > 500:
        warnings.append("summary_too_long")
    summary_lower = summary.lower()
    if any(summary_lower.startswith(prefix) for prefix in SUMMARY_BANNED_PREFIXES):
        reasons.append("summary_generic_prefix")
    has_quote_risk, quote_risk_detail = _looks_like_long_quote(summary, source_text)
    if has_quote_risk:
        reasons.append("summary_direct_quote_risk")
        reason_details["summary_direct_quote_risk"] = quote_risk_detail or "detected"

    unknown_lens = [x for x in candidate.lens_family_candidates if x not in LENS_FAMILY_ALLOWLIST]
    if unknown_lens:
        reasons.append("unknown_lens_candidate")

    normalized_tags = [_normalize_tag(tag) for tag in candidate.tags if str(tag).strip()]
    if len(normalized_tags) > 12:
        warnings.append("too_many_tags")
    if any(len(tag) > 42 for tag in normalized_tags):
        warnings.append("tag_too_long")
    candidate.tags = [tag for tag in normalized_tags if tag]

    if not 1 <= len(candidate.use_when) <= 4:
        warnings.append("use_when_size_out_of_range")
    if not 1 <= len(candidate.avoid_when) <= 4:
        warnings.append("avoid_when_size_out_of_range")

    flags = set(candidate.safety_flags_original)
    if "practice_requires_low_resource_check" in flags:
        avoid_joined = " ".join(candidate.avoid_when).lower()
        if not any(term in avoid_joined for term in _LOW_RESOURCE_TERMS):
            reasons.append("low_resource_avoid_when_missing")

    if candidate.chunk_type_original not in {"case", "lens", "practice", "safety", "style", "theory"}:
        warnings.append("chunk_type_original_unexpected")

    passed = len(reasons) == 0
    return ValidationResult(passed=passed, reasons=reasons, warnings=warnings, reason_details=reason_details)


def validate_governance_invariants(
    *,
    candidate: EnrichmentCandidate,
    source_block: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    metadata = source_block.get("metadata") if isinstance(source_block, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}

    chunk_type = str(governance.get("chunk_type") or "")
    if chunk_type != candidate.chunk_type_original:
        violations.append("chunk_type_original_mismatch")

    allowed_use = governance.get("allowed_use") or []
    allowed_use = [str(item).strip() for item in allowed_use if str(item).strip()]
    if sorted(allowed_use) != sorted(candidate.allowed_use_original):
        violations.append("allowed_use_original_mismatch")

    safety_flags = governance.get("safety_flags") or []
    safety_flags = [str(item).strip() for item in safety_flags if str(item).strip()]
    if sorted(safety_flags) != sorted(candidate.safety_flags_original):
        violations.append("safety_flags_original_mismatch")

    if "not_for_direct_quote" not in safety_flags:
        violations.append("not_for_direct_quote_missing")
    if "source_style_not_user_facing" in candidate.safety_flags_original and "source_style_not_user_facing" not in safety_flags:
        violations.append("source_style_not_user_facing_missing")
    return violations


def check_forbidden_keys(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lower_key = str(key).lower()
            if any(token == lower_key for token in FORBIDDEN_ARTIFACT_KEYS):
                found.append(lower_key)
            found.extend(check_forbidden_keys(value))
        return found
    if isinstance(obj, list):
        for item in obj:
            found.extend(check_forbidden_keys(item))
    return found
