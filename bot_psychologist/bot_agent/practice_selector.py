"""Deterministic practice selector (Phase 7)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .practice_schema import PracticeEntry, parse_practice_entry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PracticeCandidate:
    entry: PracticeEntry
    score: float
    reasons: List[str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "id": self.entry.id,
            "title": self.entry.title,
            "channel": self.entry.channel,
            "score": round(float(self.score), 3),
            "reasons": list(self.reasons),
            "instruction": self.entry.instruction,
            "micro_tuning": self.entry.micro_tuning,
            "closure": self.entry.closure,
            "time_limit_minutes": int(self.entry.time_limit_minutes),
        }


@dataclass(frozen=True)
class PracticeSelection:
    primary: Optional[PracticeCandidate]
    alternatives: List[PracticeCandidate]
    filtered_total: int
    diagnostics_snapshot: Dict[str, str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "primary": self.primary.as_dict() if self.primary else None,
            "alternatives": [item.as_dict() for item in self.alternatives],
            "filtered_total": int(self.filtered_total),
            "diagnostics": dict(self.diagnostics_snapshot),
        }


class PracticeSelector:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or Path(__file__).resolve().with_name("practices_db.json")
        self._cache: Optional[List[PracticeEntry]] = None

    def _load_entries(self) -> List[PracticeEntry]:
        if self._cache is not None:
            return self._cache
        if not self._db_path.exists():
            logger.warning("[PRACTICE] library not found: %s", self._db_path)
            self._cache = []
            return self._cache

        payload = json.loads(self._db_path.read_text(encoding="utf-8"))
        entries: List[PracticeEntry] = []
        for row in payload if isinstance(payload, list) else []:
            try:
                entries.append(parse_practice_entry(row))
            except Exception as exc:
                logger.warning("[PRACTICE] skip malformed row: %s", exc)
        self._cache = entries
        return entries

    @staticmethod
    def _keywords(text: str) -> List[str]:
        raw = (text or "").lower()
        words = [token.strip(".,!?;:()[]{}\"'") for token in raw.split()]
        return [w for w in words if len(w) >= 4]

    @staticmethod
    def _theme_overlap(theme: str, tags: Iterable[str]) -> int:
        theme_words = set(PracticeSelector._keywords(theme))
        tag_words: set[str] = set()
        for tag in tags:
            tag_words.update(PracticeSelector._keywords(str(tag)))
        return len(theme_words & tag_words)

    def select(
        self,
        *,
        route: str,
        nervous_system_state: str,
        request_function: str,
        core_theme: str,
        last_practice_channel: Optional[str] = None,
        safety_flags: Optional[List[str]] = None,
        max_alternatives: int = 2,
    ) -> PracticeSelection:
        request_fn = "directive" if request_function == "solution" else request_function
        entries = self._load_entries()
        if not entries:
            return PracticeSelection(
                primary=None,
                alternatives=[],
                filtered_total=0,
                diagnostics_snapshot={
                    "route": route,
                    "nervous_system_state": nervous_system_state,
                    "request_function": request_function,
                    "core_theme": core_theme,
                },
            )

        safety = set(safety_flags or [])
        candidates: List[PracticeCandidate] = []
        for entry in entries:
            if safety and any(flag in entry.contraindications for flag in safety):
                continue
            if nervous_system_state not in entry.nervous_system_states:
                continue

            score = 0.0
            reasons: List[str] = []

            if route in entry.triggers:
                score += 2.0
                reasons.append("route_match")
            if request_fn in entry.request_functions or request_function in entry.request_functions:
                score += 2.0
                reasons.append("request_function_match")
            if nervous_system_state in entry.nervous_system_states:
                score += 2.0
                reasons.append("state_match")

            overlap = self._theme_overlap(core_theme, entry.core_themes)
            if overlap > 0:
                score += min(1.5, overlap * 0.5)
                reasons.append("theme_overlap")

            if not reasons:
                continue
            candidates.append(PracticeCandidate(entry=entry, score=score, reasons=reasons))

        candidates.sort(key=lambda c: (-c.score, c.entry.id))
        if not candidates:
            return PracticeSelection(
                primary=None,
                alternatives=[],
                filtered_total=0,
                diagnostics_snapshot={
                    "route": route,
                    "nervous_system_state": nervous_system_state,
                    "request_function": request_function,
                    "core_theme": core_theme,
                },
            )

        primary = candidates[0]
        if last_practice_channel:
            for candidate in candidates[1:]:
                if candidate.entry.channel != last_practice_channel:
                    if abs(candidate.score - primary.score) <= 0.35:
                        primary = candidate
                    break

        alternatives: List[PracticeCandidate] = []
        for candidate in candidates:
            if candidate.entry.id == primary.entry.id:
                continue
            alternatives.append(candidate)
            if len(alternatives) >= max(0, min(2, max_alternatives)):
                break

        return PracticeSelection(
            primary=primary,
            alternatives=alternatives,
            filtered_total=len(candidates),
            diagnostics_snapshot={
                "route": route,
                "nervous_system_state": nervous_system_state,
                "request_function": request_function,
                "core_theme": core_theme,
            },
        )


practice_selector = PracticeSelector()
