"""Stage-aware filter to prevent overly deep interventions."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)


class StageFilter:
    """
    Filter allowed modes by user stage.

    Stages grow in depth:
    surface -> awareness -> exploration -> integration
    """

    DEFAULT_ALLOWED: Dict[str, List[str]] = {
        "surface": ["PRESENCE", "CLARIFICATION", "VALIDATION"],
        "awareness": ["PRESENCE", "CLARIFICATION", "VALIDATION", "THINKING"],
        "exploration": ["PRESENCE", "CLARIFICATION", "VALIDATION", "THINKING", "INTERVENTION"],
        "integration": [
            "PRESENCE",
            "CLARIFICATION",
            "VALIDATION",
            "THINKING",
            "INTERVENTION",
            "INTEGRATION",
        ],
    }
    DEFAULT_COMPLEXITY_CAP: Dict[str, float] = {
        "surface": 0.45,
        "awareness": 0.65,
        "exploration": 0.85,
        "integration": 1.00,
    }

    def __init__(
        self,
        allowed_by_stage: Dict[str, List[str]] | None = None,
        complexity_cap: Dict[str, float] | None = None,
    ) -> None:
        self.allowed_by_stage = allowed_by_stage or self.DEFAULT_ALLOWED
        self.complexity_cap = complexity_cap or self.DEFAULT_COMPLEXITY_CAP

    def allowed_modes(self, user_stage: str) -> List[str]:
        return list(self.allowed_by_stage.get(user_stage, self.allowed_by_stage["surface"]))

    def allow(self, user_stage: str, mode: str) -> bool:
        return mode in self.allowed_modes(user_stage)

    def filter_modes(self, user_stage: str, candidate_modes: Iterable[str]) -> List[str]:
        allowed = set(self.allowed_modes(user_stage))
        return [mode for mode in candidate_modes if mode in allowed]

    def complexity_threshold(self, user_stage: str) -> float:
        return float(self.complexity_cap.get(user_stage, self.complexity_cap["surface"]))

    @staticmethod
    def _fallback_keep_count(user_stage: str, available: int) -> int:
        stage = (user_stage or "surface").lower()
        if stage in {"surface", "awareness"}:
            target = 3
        elif stage == "exploration":
            target = 4
        else:
            target = 5
        return max(1, min(int(available), target))

    @staticmethod
    def _extract_complexity(block: object) -> float:
        raw = getattr(block, "complexity_score", None)
        if raw is None:
            return 0.5
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0.5
        return max(0.0, min(1.0, value))

    def filter_retrieval_pairs(
        self,
        user_stage: str,
        candidates: Sequence[Tuple[object, float]],
    ) -> List[Tuple[object, float]]:
        """
        Filter retrieval candidates by stage complexity cap.

        Keeps at least one candidate to avoid emptying the result set.
        """
        if not candidates:
            logger.info(f"[STAGE_FILTER] Input: 0 blocks stage={user_stage}")
            return []

        cap = self.complexity_threshold(user_stage)
        logger.info(
            f"[STAGE_FILTER] Input: {len(candidates)} blocks stage={user_stage} complexity_cap={cap:.2f}"
        )
        for i, (block, score) in enumerate(candidates[:10], start=1):
            block_id = getattr(block, "block_id", "unknown")
            complexity = self._extract_complexity(block)
            logger.info(
                f"  [in:{i}] score={float(score):.4f} complexity={complexity:.2f} block_id={block_id}"
            )
        filtered: List[Tuple[object, float]] = []
        for block, score in candidates:
            if self._extract_complexity(block) <= cap:
                filtered.append((block, score))

        if not filtered:
            keep = self._fallback_keep_count(user_stage, len(candidates))
            logger.info(
                f"[STAGE_FILTER] Output: 0 blocks after filter, fallback to top-{keep} input blocks"
            )
            return list(candidates[:keep])

        fallback_keep = self._fallback_keep_count(user_stage, len(candidates))
        if len(filtered) < fallback_keep:
            filtered_ids = {
                getattr(block, "block_id", id(block))
                for block, _ in filtered
            }
            for block, score in candidates:
                block_id = getattr(block, "block_id", id(block))
                if block_id in filtered_ids:
                    continue
                filtered.append((block, score))
                filtered_ids.add(block_id)
                if len(filtered) >= fallback_keep:
                    break
            logger.info(
                f"[STAGE_FILTER] Backfilled to {len(filtered)} blocks for diversity (target={fallback_keep})"
            )

        logger.info(f"[STAGE_FILTER] Output: {len(filtered)} blocks after filter")
        for i, (block, score) in enumerate(filtered[:10], start=1):
            block_id = getattr(block, "block_id", "unknown")
            complexity = self._extract_complexity(block)
            logger.info(
                f"  [out:{i}] score={float(score):.4f} complexity={complexity:.2f} block_id={block_id}"
            )
        return filtered
