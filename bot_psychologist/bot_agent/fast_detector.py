"""
Level-0 fast detector for obvious SD/state signals.

Design goal:
- very cheap regex checks (< 1 ms for short texts)
- only high-confidence cases (>= 0.85)
- if nothing obvious is found, classifier continues normal pipeline
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .config import config


@dataclass(frozen=True)
class FastDetection:
    label: str
    confidence: float
    indicator: str
    hits: int


_SD_ORDER = ["BEIGE", "PURPLE", "RED", "BLUE", "ORANGE", "GREEN", "YELLOW", "TURQUOISE"]

_SD_BASE_CONFIDENCE = {
    "BEIGE": 0.91,
    "PURPLE": 0.88,
    "RED": 0.88,
    "BLUE": 0.87,
    "ORANGE": 0.88,
    "GREEN": 0.87,
    "YELLOW": 0.89,
    "TURQUOISE": 0.86,
}

_SD_PATTERNS = {
    "BEIGE": [
        r"\bне могу дышать\b",
        r"\bстрашно умереть\b",
        r"\bфизически плохо\b",
        r"\bтеряю сознание\b",
        r"\bвыживани(?:е|я)\b",
    ],
    "PURPLE": [
        r"\bтак принято\b",
        r"\bв семье\b",
        r"\bпредк",
        r"\bритуал\b",
        r"\bсглаз\b",
        r"\bсудьб",
    ],
    "RED": [
        r"\bбесит\b",
        r"\bненавижу\b",
        r"\bдолжны мне\b",
        r"\bне буду терпеть\b",
        r"\bхочу прямо сейчас\b",
        r"\bне уважа(ют|ет)\b",
    ],
    "BLUE": [
        r"\bдолжен\b",
        r"\bдолжна\b",
        r"\bобязан\b",
        r"\bвина\b",
        r"\bдисциплин",
        r"\bтак нельзя\b",
        r"\bкак положено\b",
    ],
    "ORANGE": [
        r"\bрезультат\b",
        r"\bэффективн",
        r"\bвыгод",
        r"\bкарьер",
        r"\bстратеги",
        r"\bчто это даст\b",
    ],
    "GREEN": [
        r"\bчувств",
        r"\bэмпат",
        r"\bподдержк",
        r"\bприняти",
        r"\bне могу справиться\b",
        r"\bтревог",
    ],
    "YELLOW": [
        r"\bзамечаю паттерн\b",
        r"\bконтекст\b",
        r"\bсистем",
        r"\bметанаблюден",
        r"\bзамечаю что я\b",
    ],
    "TURQUOISE": [
        r"\bединств",
        r"\bцелостност",
        r"\bвс[её] одно\b",
        r"\bтрансцендент",
        r"\bпланетарн",
    ],
}

_SD_NOT_RED_PATTERNS = [
    re.compile(r"\bхочу понять\b", flags=re.IGNORECASE),
    re.compile(r"\bхочу разобраться\b", flags=re.IGNORECASE),
    re.compile(r"\bинтересно\b", flags=re.IGNORECASE),
    re.compile(r"\bобъясни\b", flags=re.IGNORECASE),
]

_STATE_BASE_CONFIDENCE = {
    "OVERWHELMED": 0.91,
    "CURIOUS": 0.86,
    "COMMITTED": 0.86,
    "PRACTICING": 0.86,
    "STAGNANT": 0.87,
    "BREAKTHROUGH": 0.90,
    "INTEGRATED": 0.87,
}

_STATE_PATTERNS = {
    "OVERWHELMED": [
        r"\bне могу дышать\b",
        r"\bслишком много\b",
        r"\bзапутал(?:ся|ась)\b",
        r"\bтеряюсь\b",
        r"\bочень тяжело\b",
    ],
    "CURIOUS": [
        r"\bчто такое\b",
        r"\bкак это работает\b",
        r"\bпочему\b",
        r"\bинтересно\b",
        r"\bхочу узнать\b",
    ],
    "COMMITTED": [
        r"\bготов\b",
        r"\bдавай начнем\b",
        r"\bприступа[юе]м\b",
        r"\bрешил\b",
        r"\bбуду делать\b",
    ],
    "PRACTICING": [
        r"\bпробую\b",
        r"\bпрактику[юе]\b",
        r"\bделаю\b",
        r"\bв процессе\b",
        r"\bзаметил\b",
    ],
    "STAGNANT": [
        r"\bзастрял\b",
        r"\bплато\b",
        r"\bтопчусь на месте\b",
        r"\bнет прогресса\b",
        r"\bничего не меняется\b",
    ],
    "BREAKTHROUGH": [
        r"\bинсайт\b",
        r"\bозарени",
        r"\bпрорыв\b",
        r"\bвсе встало на место\b",
    ],
    "INTEGRATED": [
        r"\bприменяю\b",
        r"\bавтоматически\b",
        r"\bестественно получается\b",
        r"\bчасть меня\b",
    ],
}


def _count_hits(text: str, patterns: Iterable[re.Pattern[str]]) -> int:
    return sum(1 for pattern in patterns if pattern.search(text))


def _compile_patterns(mapping: dict[str, list[str]]) -> dict[str, list[re.Pattern[str]]]:
    compiled: dict[str, list[re.Pattern[str]]] = {}
    for label, patterns in mapping.items():
        compiled[label] = [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns]
    return compiled


_SD_COMPILED = _compile_patterns(_SD_PATTERNS)
_STATE_COMPILED = _compile_patterns(_STATE_PATTERNS)


def _build_confidence(base: float, hits: int) -> float:
    # Small bonus for multiple matched markers.
    return min(0.97, base + min(max(hits - 1, 0) * 0.03, 0.08))


def detect_sd_level(text: str) -> FastDetection | None:
    if not config.FAST_DETECTOR_ENABLED:
        return None

    message = (text or "").strip().lower()
    if not message:
        return None

    not_red = any(pattern.search(message) for pattern in _SD_NOT_RED_PATTERNS)
    scores: dict[str, int] = {}
    for label in _SD_ORDER:
        if label == "RED" and not_red:
            continue
        hits = _count_hits(message, _SD_COMPILED[label])
        if hits > 0:
            scores[label] = hits

    if not scores:
        return None

    # Tie-breaker by SD order (lower/safer level first), then by hits desc.
    best_label = sorted(scores.items(), key=lambda item: (-item[1], _SD_ORDER.index(item[0])))[0][0]
    best_hits = scores[best_label]
    confidence = _build_confidence(_SD_BASE_CONFIDENCE[best_label], best_hits)
    if confidence < float(config.FAST_DETECTOR_CONFIDENCE_THRESHOLD):
        return None
    return FastDetection(
        label=best_label,
        confidence=confidence,
        indicator=f"fast_sd:{best_label.lower()}:{best_hits}",
        hits=best_hits,
    )


def detect_user_state(text: str) -> FastDetection | None:
    if not config.FAST_DETECTOR_ENABLED:
        return None

    message = (text or "").strip().lower()
    if not message:
        return None

    scores: dict[str, int] = {}
    for label, patterns in _STATE_COMPILED.items():
        hits = _count_hits(message, patterns)
        if hits > 0:
            scores[label] = hits

    if not scores:
        return None

    best_label = max(scores.items(), key=lambda item: item[1])[0]
    best_hits = scores[best_label]
    confidence = _build_confidence(_STATE_BASE_CONFIDENCE[best_label], best_hits)
    if confidence < float(config.FAST_DETECTOR_CONFIDENCE_THRESHOLD):
        return None
    return FastDetection(
        label=best_label,
        confidence=confidence,
        indicator=f"fast_state:{best_label.lower()}:{best_hits}",
        hits=best_hits,
    )
