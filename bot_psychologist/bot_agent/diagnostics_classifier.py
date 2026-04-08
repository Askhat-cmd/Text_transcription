"""Diagnostics v1 classifier for Neo MindBot Phase 4.

This module converts runtime signals into a compact, validated diagnostics
contract that RouteResolver can use deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict

from .state_classifier import StateAnalysis


INTERACTION_MODES = {"coaching", "informational"}
NERVOUS_SYSTEM_STATES = {"hyper", "window", "hypo"}
REQUEST_FUNCTIONS = {
    "discharge",
    "understand",
    "solution",
    "validation",
    "explore",
    "contact",
}
LEGACY_REQUEST_FUNCTION_ALIASES = {
    "directive": "solution",
}
LEGACY_STATE_MAP = {
    "curious": "window",
    "committed": "window",
    "calm": "window",
    "engaged": "window",
    "unaware": "window",
    "practicing": "window",
    "integrated": "window",
    "confused": "hyper",
    "overwhelmed": "hyper",
    "frustrated": "hyper",
    "resistant": "hyper",
    "anxious": "hyper",
    "stagnant": "hypo",
    "flat": "hypo",
    "detached": "hypo",
    "numb": "hypo",
    "exhausted": "hypo",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiagnosticsConfidence:
    interaction_mode: float
    nervous_system_state: float
    request_function: float
    core_theme: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "interaction_mode": round(float(self.interaction_mode), 3),
            "nervous_system_state": round(float(self.nervous_system_state), 3),
            "request_function": round(float(self.request_function), 3),
            "core_theme": round(float(self.core_theme), 3),
        }


@dataclass(frozen=True)
class DiagnosticsV1:
    interaction_mode: str
    nervous_system_state: str
    request_function: str
    core_theme: str
    confidence: DiagnosticsConfidence
    optional: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "interaction_mode": self.interaction_mode,
            "nervous_system_state": self.nervous_system_state,
            "request_function": self.request_function,
            "core_theme": self.core_theme,
            "confidence": self.confidence.as_dict(),
            "optional": dict(self.optional),
        }


class DiagnosticsClassifier:
    """Deterministic diagnostics classifier with safe defaults."""

    _INFORMATIONAL_RE = re.compile(
        r"\b(что такое|объясни|объяснение|в чем разниц|чем отлича|разница между|как работает|термин|поняти|концепц|definition|difference|vs\.?)\b",
        flags=re.IGNORECASE,
    )
    _PERSONAL_RE = re.compile(
        r"\b(я|мне|меня|мой|чувств|пережив|боюсь|тревог|стыд|вина)\b",
        flags=re.IGNORECASE,
    )
    _APPLICATION_RE = re.compile(
        r"\b(у себя|в моей жизни|в реальной жизни|про меня|со мной|для меня)\b",
        flags=re.IGNORECASE,
    )
    _PRACTICE_ENTRY_RE = re.compile(
        r"\b(как начать|как практиковать|как применять|с чего начать|что делать дальше)\b",
        flags=re.IGNORECASE,
    )
    _DIRECTIVE_RE = re.compile(
        r"\b(что делать|как поступить|скажи,? что делать|дай шаги|план действий)\b",
        flags=re.IGNORECASE,
    )
    _VALIDATION_RE = re.compile(
        r"\b(я прав|подтверди|правильно ли|нормально ли)\b",
        flags=re.IGNORECASE,
    )
    _DISCHARGE_RE = re.compile(
        r"\b(хочу выговориться|просто выговориться|нужно выговориться|надо выговориться)\b",
        flags=re.IGNORECASE,
    )
    _CONTACT_RE = re.compile(
        r"\b(привет|ты рядом|просто побудь|побудь со мной|нужна поддержка)\b",
        flags=re.IGNORECASE,
    )
    _EXPLORE_RE = re.compile(
        r"\b(почему|что со мной|как это связано|помоги понять глубже)\b",
        flags=re.IGNORECASE,
    )

    def classify(
        self,
        query: str,
        state_analysis: StateAnalysis | None,
        informational_mode_hint: bool = False,
    ) -> DiagnosticsV1:
        text = (query or "").strip()
        if not text:
            return self.default()

        interaction_mode, interaction_conf = self._detect_interaction_mode(
            text, informational_mode_hint
        )
        nervous_state, nervous_conf = self._detect_nervous_system_state(
            text, state_analysis
        )
        request_function, request_conf = self._detect_request_function(text)
        core_theme, core_theme_conf = self._extract_core_theme(text)

        return DiagnosticsV1(
            interaction_mode=interaction_mode,
            nervous_system_state=nervous_state,
            request_function=request_function,
            core_theme=core_theme,
            confidence=DiagnosticsConfidence(
                interaction_mode=interaction_conf,
                nervous_system_state=nervous_conf,
                request_function=request_conf,
                core_theme=core_theme_conf,
            ),
            optional={
                "distance_to_experience": None,
                "dominant_part": None,
                "active_quadrant": None,
                "readiness_markers": [],
            },
        )

    @staticmethod
    def default() -> DiagnosticsV1:
        return DiagnosticsV1(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="understand",
            core_theme="unspecified_current_issue",
            confidence=DiagnosticsConfidence(
                interaction_mode=0.51,
                nervous_system_state=0.51,
                request_function=0.51,
                core_theme=0.4,
            ),
            optional={
                "distance_to_experience": None,
                "dominant_part": None,
                "active_quadrant": None,
                "readiness_markers": [],
            },
        )

    def sanitize(self, payload: Dict[str, Any]) -> DiagnosticsV1:
        """Build a valid diagnostics object from partial/untrusted payload."""
        defaults = self.default()

        interaction_mode = str(payload.get("interaction_mode") or defaults.interaction_mode).lower()
        if interaction_mode not in INTERACTION_MODES:
            interaction_mode = defaults.interaction_mode

        nervous_state = str(
            payload.get("nervous_system_state") or defaults.nervous_system_state
        ).lower()
        if nervous_state not in NERVOUS_SYSTEM_STATES:
            nervous_state = defaults.nervous_system_state

        request_function = str(
            payload.get("request_function") or defaults.request_function
        ).lower()
        request_function = LEGACY_REQUEST_FUNCTION_ALIASES.get(request_function, request_function)
        if request_function not in REQUEST_FUNCTIONS:
            request_function = defaults.request_function

        core_theme = str(payload.get("core_theme") or defaults.core_theme).strip()
        if not core_theme:
            core_theme = defaults.core_theme

        raw_conf = payload.get("confidence") if isinstance(payload.get("confidence"), dict) else {}
        confidence = DiagnosticsConfidence(
            interaction_mode=self._clamp_confidence(
                raw_conf.get("interaction_mode"), defaults.confidence.interaction_mode
            ),
            nervous_system_state=self._clamp_confidence(
                raw_conf.get("nervous_system_state"), defaults.confidence.nervous_system_state
            ),
            request_function=self._clamp_confidence(
                raw_conf.get("request_function"), defaults.confidence.request_function
            ),
            core_theme=self._clamp_confidence(raw_conf.get("core_theme"), defaults.confidence.core_theme),
        )

        optional = payload.get("optional") if isinstance(payload.get("optional"), dict) else {}
        return DiagnosticsV1(
            interaction_mode=interaction_mode,
            nervous_system_state=nervous_state,
            request_function=request_function,
            core_theme=core_theme,
            confidence=confidence,
            optional={
                "distance_to_experience": optional.get("distance_to_experience"),
                "dominant_part": optional.get("dominant_part"),
                "active_quadrant": optional.get("active_quadrant"),
                "readiness_markers": (
                    optional.get("readiness_markers")
                    if isinstance(optional.get("readiness_markers"), list)
                    else []
                ),
            },
        )

    def _detect_interaction_mode(
        self,
        text: str,
        informational_mode_hint: bool,
    ) -> tuple[str, float]:
        lowered = text.lower()
        informational_match = bool(self._INFORMATIONAL_RE.search(lowered))
        personal_match = bool(self._PERSONAL_RE.search(lowered))
        application_match = bool(self._APPLICATION_RE.search(lowered))
        practice_match = bool(self._PRACTICE_ENTRY_RE.search(lowered))

        has_personal_context = personal_match or application_match or practice_match
        if informational_mode_hint and informational_match and not has_personal_context:
            return "informational", 0.88
        if informational_match and not has_personal_context:
            return "informational", 0.82
        if informational_match and has_personal_context:
            return "coaching", 0.78
        return "coaching", 0.74

    def _detect_nervous_system_state(
        self,
        text: str,
        state_analysis: StateAnalysis | None,
    ) -> tuple[str, float]:
        lowered = text.lower()
        if any(token in lowered for token in ("паник", "срочно", "разрыв", "невыносим", "тревог")):
            return "hyper", 0.8
        if any(token in lowered for token in ("пустот", "апат", "не чувствую", "обессил", "замороз")):
            return "hypo", 0.78
        if state_analysis is None:
            return "window", 0.62

        primary_state = getattr(getattr(state_analysis, "primary_state", None), "value", "")
        tone = (getattr(state_analysis, "emotional_tone", "") or "").lower()
        state_conf = float(getattr(state_analysis, "confidence", 0.5) or 0.5)

        if primary_state in NERVOUS_SYSTEM_STATES:
            return primary_state, max(0.6, min(0.95, state_conf))
        if primary_state:
            mapped = LEGACY_STATE_MAP.get(primary_state)
            if mapped:
                logger.warning("[DIAG] state legacy term '%s' -> '%s'", primary_state, mapped)
                return mapped, max(0.6, min(0.95, state_conf))

        if primary_state in {"overwhelmed", "resistant"} or any(
            token in tone for token in ("panic", "anxiety", "distress", "frustrat")
        ):
            return "hyper", max(0.65, min(0.95, state_conf))
        if primary_state in {"stagnant"} or any(
            token in tone for token in ("apathy", "numb", "shutdown", "flat")
        ):
            return "hypo", max(0.65, min(0.95, state_conf))
        return "window", max(0.6, min(0.9, state_conf))

    def _detect_request_function(self, text: str) -> tuple[str, float]:
        lowered = text.lower()
        if self._DISCHARGE_RE.search(lowered):
            return "discharge", 0.82
        if self._DIRECTIVE_RE.search(lowered):
            return "solution", 0.84
        if self._VALIDATION_RE.search(lowered):
            return "validation", 0.8
        if self._CONTACT_RE.search(lowered):
            return "contact", 0.76
        if self._EXPLORE_RE.search(lowered):
            return "explore", 0.74
        if "?" in lowered:
            return "understand", 0.68
        return "understand", 0.58

    def _extract_core_theme(self, text: str) -> tuple[str, float]:
        tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ]{4,}", text.lower())
        stop_words = {
            "что",
            "как",
            "если",
            "когда",
            "почему",
            "можно",
            "можешь",
            "расскажи",
            "объясни",
            "просто",
            "меня",
            "мне",
            "себя",
            "теперь",
            "хочу",
            "нужно",
            "очень",
        }
        meaningful = [t for t in tokens if t not in stop_words]
        if not meaningful:
            return "unspecified_current_issue", 0.4
        return " ".join(meaningful[:3]), 0.67

    @staticmethod
    def _clamp_confidence(raw: Any, default: float) -> float:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return float(default)
        return max(0.0, min(1.0, value))


diagnostics_classifier = DiagnosticsClassifier()
