"""Validation helpers for governed knowledge chunks."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .contracts import (
    ALLOWED_USE_VALUES,
    CHUNK_TYPE_VALUES,
    SAFETY_FLAG_VALUES,
    GovernedKnowledgeChunk,
)


def _has_secret_like_pattern(text: str) -> bool:
    lowered = text.lower()
    if "api_key" in lowered or "secret=" in lowered or "token=" in lowered:
        return True
    if re.search(r"[A-Za-z0-9]{24,}\.[A-Za-z0-9_-]{20,}", text):
        return True
    return False


def validate_governed_chunks_v1(chunks: list[GovernedKnowledgeChunk]) -> dict[str, Any]:
    """Validate chunk contracts and return aggregated governance report."""
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    count_type: Counter[str] = Counter()
    count_use: Counter[str] = Counter()
    count_flag: Counter[str] = Counter()

    for idx, chunk in enumerate(chunks):
        label = f"chunk[{idx}]<{chunk.chunk_id}>"
        if not chunk.chunk_id:
            errors.append(f"{label}: empty_chunk_id")
        elif chunk.chunk_id in seen_ids:
            errors.append(f"{label}: duplicate_chunk_id")
        else:
            seen_ids.add(chunk.chunk_id)

        if not chunk.text.strip():
            errors.append(f"{label}: empty_text")
        if not chunk.summary.strip():
            errors.append(f"{label}: empty_summary")

        if chunk.chunk_type not in CHUNK_TYPE_VALUES:
            errors.append(f"{label}: invalid_chunk_type={chunk.chunk_type}")
        count_type[chunk.chunk_type] += 1

        if not chunk.allowed_use:
            errors.append(f"{label}: empty_allowed_use")
        for use in chunk.allowed_use:
            count_use[use] += 1
            if use not in ALLOWED_USE_VALUES:
                errors.append(f"{label}: invalid_allowed_use={use}")

        for flag in chunk.safety_flags:
            count_flag[flag] += 1
            if flag not in SAFETY_FLAG_VALUES:
                errors.append(f"{label}: invalid_safety_flag={flag}")

        if chunk.chunk_type == "practice" and not isinstance(chunk.practice_metadata, dict):
            errors.append(f"{label}: practice_missing_metadata_dict")
        if chunk.chunk_type == "practice" and isinstance(chunk.practice_metadata, dict):
            if not chunk.practice_metadata:
                errors.append(f"{label}: practice_empty_metadata")
            if "practice_suggestion" in chunk.allowed_use:
                low_resource_safe = bool(chunk.practice_metadata.get("low_resource_safe"))
                has_guard = "practice_requires_low_resource_check" in chunk.safety_flags
                if not low_resource_safe and not has_guard:
                    errors.append(f"{label}: practice_suggestion_without_low_resource_guard")

        has_high_risk = any(
            flag in chunk.safety_flags for flag in ("clinical_risk", "spiritual_authority_risk")
        )
        if has_high_risk and "do_not_use" not in chunk.allowed_use:
            if "not_for_direct_quote" not in chunk.safety_flags:
                warnings.append(f"{label}: high_risk_chunk_without_not_for_direct_quote")

        text_for_scan = "\n".join([chunk.text, chunk.summary])
        if _has_secret_like_pattern(text_for_scan):
            warnings.append(f"{label}: possible_secret_pattern_detected")
        if ".env" in text_for_scan.lower():
            warnings.append(f"{label}: possible_path_leak_env_reference")

    return {
        "chunks_total": len(chunks),
        "errors": errors,
        "warnings": warnings,
        "counts_by_type": dict(sorted(count_type.items())),
        "counts_by_allowed_use": dict(sorted(count_use.items())),
        "counts_by_safety_flag": dict(sorted(count_flag.items())),
    }
