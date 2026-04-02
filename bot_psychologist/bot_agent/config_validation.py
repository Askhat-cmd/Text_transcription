"""Runtime config validation helpers (Phase 9)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


@dataclass(frozen=True)
class ConfigValidationResult:
    valid: bool
    errors: List[str]


def _as_float(value: Any, field: str, errors: List[str]) -> float:
    try:
        return float(value)
    except Exception:
        errors.append(f"{field}:must_be_number")
        return 0.0


def _as_int(value: Any, field: str, errors: List[str]) -> int:
    try:
        return int(value)
    except Exception:
        errors.append(f"{field}:must_be_int")
        return 0


def validate_runtime_config(cfg: Any) -> ConfigValidationResult:
    errors: List[str] = []

    top_k = _as_int(getattr(cfg, "TOP_K_BLOCKS", 0), "TOP_K_BLOCKS", errors)
    if not 1 <= top_k <= 20:
        errors.append("TOP_K_BLOCKS:range_1_20")

    min_rel = _as_float(getattr(cfg, "MIN_RELEVANCE_SCORE", 0.0), "MIN_RELEVANCE_SCORE", errors)
    if not 0.0 <= min_rel <= 1.0:
        errors.append("MIN_RELEVANCE_SCORE:range_0_1")

    voyage_top_k = _as_int(getattr(cfg, "VOYAGE_TOP_K", 0), "VOYAGE_TOP_K", errors)
    if voyage_top_k < 1:
        errors.append("VOYAGE_TOP_K:min_1")

    max_context = _as_int(getattr(cfg, "MAX_CONTEXT_SIZE", 0), "MAX_CONTEXT_SIZE", errors)
    if max_context < 500:
        errors.append("MAX_CONTEXT_SIZE:min_500")

    llm_model = str(getattr(cfg, "LLM_MODEL", "") or "").strip()
    if not llm_model:
        errors.append("LLM_MODEL:required")

    return ConfigValidationResult(valid=not errors, errors=errors)


def assert_runtime_config(cfg: Any) -> None:
    result = validate_runtime_config(cfg)
    if not result.valid:
        joined = ", ".join(result.errors)
        raise RuntimeError(f"Invalid runtime config: {joined}")
