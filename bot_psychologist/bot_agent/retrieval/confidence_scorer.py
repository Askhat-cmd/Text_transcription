"""Confidence scoring utilities for retrieval and routing."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceResult:
    """Calculated confidence value and metadata."""

    score: float
    level: str
    contributions: Dict[str, float]


class ConfidenceScorer:
    """Weighted confidence scorer with configurable thresholds."""

    DEFAULT_WEIGHTS = {
        "local_similarity": 0.25,
        "delta_top1_top2": 0.25,
        "state_match": 0.25,
        "question_clarity": 0.25,
    }

    def __init__(
        self,
        weights: Dict[str, float] | None = None,
        low_threshold: float = 0.4,
        high_threshold: float = 0.75,
    ) -> None:
        self.weights = dict(weights or self.DEFAULT_WEIGHTS)
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

    @staticmethod
    def _clip_01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _normalize_weights(self) -> Dict[str, float]:
        total = sum(self.weights.values())
        if total <= 0:
            return dict(self.DEFAULT_WEIGHTS)
        return {k: v / total for k, v in self.weights.items()}

    def score(self, signals: Dict[str, float]) -> ConfidenceResult:
        """
        Calculate weighted confidence and confidence level.

        Missing signals are treated as 0.0.
        """
        weights = self._normalize_weights()
        contributions: Dict[str, float] = {}
        total = 0.0

        for key, weight in weights.items():
            value = self._clip_01(signals.get(key, 0.0))
            contrib = value * weight
            contributions[key] = contrib
            total += contrib

        total = round(self._clip_01(total), 4)
        if total < self.low_threshold:
            level = "low"
        elif total >= self.high_threshold:
            level = "high"
        else:
            level = "medium"

        logger.info(f"[CONFIDENCE] score={total:.4f} level={level}")

        return ConfidenceResult(
            score=total,
            level=level,
            contributions=contributions,
        )

    def suggest_block_cap(
        self,
        available_blocks: int,
        confidence_level: str,
    ) -> int:
        """
        Suggest how many blocks to keep for answer generation.

        Low confidence -> tighter context to avoid hallucinated synthesis.
        """
        count = max(0, int(available_blocks))
        try:
            from ..config import config

            cap_by_level = {
                "high": int(getattr(config, "CONFIDENCE_CAP_HIGH", 7)),
                "medium": int(getattr(config, "CONFIDENCE_CAP_MEDIUM", 5)),
                "low": int(getattr(config, "CONFIDENCE_CAP_LOW", 3)),
                "zero": int(getattr(config, "CONFIDENCE_CAP_ZERO", 0)),
            }
            level = (confidence_level or "medium").lower()
            cap = max(0, int(cap_by_level.get(level, cap_by_level["medium"])))
            applied = min(count, cap)
            logger.info(
                "[CONFIDENCE] cap applied level=%s cap=%s before=%s after=%s",
                level,
                cap,
                count,
                applied,
            )
            return applied
        except Exception:
            fallback_cap = 5
            applied = min(count, fallback_cap)
            logger.info(
                "[CONFIDENCE] cap applied level=%s cap=%s before=%s after=%s",
                confidence_level,
                fallback_cap,
                count,
                applied,
            )
            return applied
