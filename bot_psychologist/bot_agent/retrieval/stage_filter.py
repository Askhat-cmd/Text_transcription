"""Stage-aware filter to prevent overly deep interventions."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple


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
            return []

        cap = self.complexity_threshold(user_stage)
        filtered: List[Tuple[object, float]] = []
        for block, score in candidates:
            if self._extract_complexity(block) <= cap:
                filtered.append((block, score))

        return filtered or [candidates[0]]
