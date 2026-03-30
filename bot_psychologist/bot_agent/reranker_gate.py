"""Conditional gate for Voyage reranker."""

from __future__ import annotations

from typing import Any


def should_rerank(
    confidence_score: float,
    routing_mode: str,
    retrieved_block_count: int,
    flags: dict[str, Any],
) -> tuple[bool, str]:
    """
    Decide whether reranker should run for current query.

    Backward compatibility:
    - legacy VOYAGE_ENABLED=True without new conditional flag => always rerank.
    """
    if bool(flags.get("legacy_always_on", False)):
        return True, "legacy_voyage_enabled"

    if not bool(flags.get("RERANKER_ENABLED", False)):
        return False, "reranker_disabled_by_flag"

    threshold = float(flags.get("RERANKER_CONFIDENCE_THRESHOLD", 0.35) or 0.35)
    block_threshold = int(flags.get("RERANKER_BLOCK_THRESHOLD", 8) or 8)
    whitelist_raw = flags.get("RERANKER_MODE_WHITELIST", ["THINKING", "INTERVENTION"])

    if isinstance(whitelist_raw, str):
        whitelist = {item.strip().upper() for item in whitelist_raw.split(",") if item.strip()}
    else:
        whitelist = {str(item).strip().upper() for item in (whitelist_raw or []) if str(item).strip()}

    mode = (routing_mode or "").upper()
    score = float(confidence_score or 0.0)
    blocks = int(retrieved_block_count or 0)

    if score < threshold:
        return True, f"low_confidence={score:.2f}"
    if mode and mode in whitelist:
        return True, f"mode_in_whitelist={mode}"
    if blocks > block_threshold:
        return True, f"high_block_count={blocks}"

    return False, "conditions_not_met"
