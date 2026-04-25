"""State Analyzer agent for NEO multi-agent runtime."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from ...config import config
from ...feature_flags import feature_flags
from ..contracts.state_snapshot import StateSnapshot
from ..contracts.thread_state import ThreadState
from .state_analyzer_prompts import STATE_ANALYZER_SYSTEM, STATE_ANALYZER_USER_TEMPLATE


logger = logging.getLogger(__name__)

_VALID_NERVOUS = {"window", "hyper", "hypo"}
_VALID_INTENT = {"clarify", "vent", "explore", "contact", "solution"}
_VALID_OPENNESS = {"open", "mixed", "defensive", "collapsed"}
_VALID_OK_POSITION = {"I+W+", "I-W+", "I+W-", "I-W-"}

_SAFETY_KEYWORDS = frozenset(
    {
        "суицид",
        "убить себя",
        "убью себя",
        "не хочу жить",
        "все кончено",
        "всё кончено",
        "хочу умереть",
        "лучше бы меня не было",
        "не могу больше терпеть",
        "suicide",
        "kill myself",
        "end it all",
        "hurt myself",
        "i want to die",
    }
)

_HYPER_KEYWORDS = frozenset(
    {
        "паника",
        "паническая",
        "тревога",
        "тревожно",
        "не могу успокоиться",
        "сердце бьется",
        "сердце бьётся",
        "задыхаюсь",
        "срываюсь",
        "panic",
        "anxiety",
        "cant calm",
        "can't calm",
        "freaking out",
    }
)

_HYPO_KEYWORDS = frozenset(
    {
        "ничего не чувствую",
        "пустота",
        "все равно",
        "всё равно",
        "нет сил",
        "не могу встать",
        "апатия",
        "безразличие",
        "numb",
        "emptiness",
        "no energy",
        "dont care",
        "don't care",
    }
)

_CONTACT_PHRASES = frozenset(
    {
        "просто хочу поговорить",
        "не надо советов",
        "не нужно советов",
        "хочу чтобы выслушали",
        "просто выслушай",
        "just want to talk",
        "no advice",
        "just listen",
    }
)

_SOLUTION_PHRASES = frozenset(
    {
        "как мне",
        "что делать",
        "помоги решить",
        "что посоветуешь",
        "дай совет",
        "как справиться",
        "what should i do",
        "how do i",
        "help me fix",
    }
)

_VENT_PHRASES = frozenset(
    {
        "я злюсь",
        "бесит",
        "это несправедливо",
        "ненавижу",
        "так обидно",
        "не могу простить",
        "i am angry",
        "i'm angry",
        "it's unfair",
    }
)

_CLARIFY_PHRASES = frozenset(
    {
        "почему я",
        "как понять",
        "хочу разобраться",
        "что со мной",
        "помоги понять",
        "why do i",
        "help me understand",
    }
)

_EXPLORE_PHRASES = frozenset(
    {
        "а что если",
        "интересно",
        "расскажи",
        "объясни",
        "хочу узнать",
        "what if",
        "tell me more",
    }
)

_DEFENSIVE_PHRASES = frozenset(
    {
        "все равно не поможет",
        "всё равно не поможет",
        "уже пробовал",
        "ничего не изменится",
        "бесполезно",
        "это не работает",
        "won't help",
        "already tried",
    }
)

_OPEN_PHRASES = frozenset(
    {
        "да, понимаю",
        "точно так",
        "согласен",
        "готов попробовать",
        "мне откликается",
        "yes, i get it",
        "that makes sense",
    }
)


def _contains_any(text: str, items: frozenset[str]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in items)


def _is_start_command(message: str) -> bool:
    lowered = (message or "").strip().lower()
    return lowered in {"/start", "start", "начать", "привет", "hello", "hi"}


def _is_empty(message: str) -> bool:
    return not (message or "").strip()


def _is_only_emoji_or_symbols(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE) == ""


def _sanitize_field(value: Any, allowed: set[str], fallback: str) -> str:
    candidate = str(value or "").strip()
    if candidate in allowed:
        return candidate
    lowered = candidate.lower()
    for item in allowed:
        if item.lower() == lowered:
            return item
    return fallback


def _clamp_confidence(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < 0.0:
        return 0.0
    if parsed > 1.0:
        return 1.0
    return parsed


@dataclass(frozen=True)
class _DeterministicResult:
    nervous_state: str
    nervous_conf: float
    intent: Optional[str]
    intent_conf: float
    openness: Optional[str]
    openness_conf: float

    @property
    def aggregate_conf(self) -> float:
        scores = [self.nervous_conf]
        if self.intent is not None:
            scores.append(self.intent_conf)
        if self.openness is not None:
            scores.append(self.openness_conf)
        return sum(scores) / len(scores)


class StateAnalyzerAgent:
    """Analyzes user turn and produces StateSnapshot for Thread Manager."""

    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self._client = client
        self._model = model or feature_flags.value("STATE_ANALYZER_MODEL", "gpt-5-nano")

    async def analyze(
        self,
        user_message: str,
        previous_thread: Optional[ThreadState] = None,
    ) -> StateSnapshot:
        message = (user_message or "").strip()
        try:
            if _is_empty(message):
                return self._default_snapshot()
            if _is_start_command(message):
                return self._onboarding_snapshot()
            if _is_only_emoji_or_symbols(message):
                return StateSnapshot(
                    nervous_state="window",
                    intent="contact",
                    openness="mixed",
                    ok_position="I+W+",
                    safety_flag=False,
                    confidence=0.6,
                )
            if self._detect_safety(message):
                return StateSnapshot(
                    nervous_state="hyper",
                    intent="contact",
                    openness="collapsed",
                    ok_position="I-W-",
                    safety_flag=True,
                    confidence=0.99,
                )

            deterministic = self._deterministic(message)
            if (
                deterministic.aggregate_conf >= 0.75
                and deterministic.intent is not None
                and deterministic.openness is not None
            ):
                return StateSnapshot(
                    nervous_state=deterministic.nervous_state,
                    intent=deterministic.intent,
                    openness=deterministic.openness,
                    ok_position="I+W+",
                    safety_flag=False,
                    confidence=round(deterministic.aggregate_conf, 3),
                )

            return await self._analyze_with_llm(
                message=message,
                previous_thread=previous_thread,
                deterministic=deterministic,
            )
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.error("[STATE_ANALYZER] analyze failed: %s", exc, exc_info=True)
            return self._default_snapshot()

    def _deterministic(self, message: str) -> _DeterministicResult:
        nervous_state, nervous_conf = self._detect_nervous_state(message)
        intent, intent_conf = self._detect_intent(message)
        openness, openness_conf = self._detect_openness(message)
        return _DeterministicResult(
            nervous_state=nervous_state,
            nervous_conf=nervous_conf,
            intent=intent,
            intent_conf=intent_conf,
            openness=openness,
            openness_conf=openness_conf,
        )

    def _detect_safety(self, message: str) -> bool:
        return _contains_any(message, _SAFETY_KEYWORDS)

    def _detect_nervous_state(self, message: str) -> tuple[str, float]:
        if _contains_any(message, _HYPER_KEYWORDS):
            return "hyper", 0.92
        if _contains_any(message, _HYPO_KEYWORDS):
            return "hypo", 0.9
        caps_chars = sum(1 for ch in message if ch.isupper())
        alpha_chars = sum(1 for ch in message if ch.isalpha())
        caps_ratio = caps_chars / max(alpha_chars, 1)
        if caps_ratio >= 0.3 or message.count("!") >= 3:
            return "hyper", 0.8
        words = message.split()
        if len(words) < 5 and not message.endswith("?"):
            return "hypo", 0.65
        return "window", 0.7

    def _detect_intent(self, message: str) -> tuple[Optional[str], float]:
        if _contains_any(message, _CONTACT_PHRASES):
            return "contact", 0.93
        if _contains_any(message, _SOLUTION_PHRASES):
            return "solution", 0.9
        if _contains_any(message, _VENT_PHRASES):
            return "vent", 0.86
        if _contains_any(message, _CLARIFY_PHRASES):
            return "clarify", 0.84
        if _contains_any(message, _EXPLORE_PHRASES):
            return "explore", 0.8
        return None, 0.0

    def _detect_openness(self, message: str) -> tuple[Optional[str], float]:
        if _contains_any(message, _DEFENSIVE_PHRASES):
            return "defensive", 0.85
        if _contains_any(message, _OPEN_PHRASES):
            return "open", 0.8
        return None, 0.0

    async def _analyze_with_llm(
        self,
        *,
        message: str,
        previous_thread: Optional[ThreadState],
        deterministic: _DeterministicResult,
    ) -> StateSnapshot:
        try:
            client = self._get_client()
            if client is None:
                return self._fallback_from_deterministic(deterministic, confidence=0.55)

            previous_context = self._build_previous_context(previous_thread)
            hints = self._build_hints(deterministic)
            user_prompt = STATE_ANALYZER_USER_TEMPLATE.format(
                user_message=message[:1000],
                previous_context=previous_context,
                deterministic_hints=hints,
            )

            response = await client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": STATE_ANALYZER_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=240,
            )
            raw = response.choices[0].message.content or "{}"
            parsed = self._parse_json(raw)
            nervous_state = (
                deterministic.nervous_state
                if deterministic.nervous_conf >= 0.8
                else _sanitize_field(
                    parsed.get("nervous_state"),
                    _VALID_NERVOUS,
                    deterministic.nervous_state,
                )
            )
            intent = (
                deterministic.intent
                if deterministic.intent is not None and deterministic.intent_conf >= 0.8
                else _sanitize_field(
                    parsed.get("intent"),
                    _VALID_INTENT,
                    deterministic.intent or "explore",
                )
            )
            openness = (
                deterministic.openness
                if deterministic.openness is not None and deterministic.openness_conf >= 0.8
                else _sanitize_field(
                    parsed.get("openness"),
                    _VALID_OPENNESS,
                    deterministic.openness or "open",
                )
            )
            result = StateSnapshot(
                nervous_state=nervous_state,
                intent=intent,
                openness=openness,
                ok_position=_sanitize_field(
                    parsed.get("ok_position"),
                    _VALID_OK_POSITION,
                    "I+W+",
                ),
                safety_flag=False,
                confidence=_clamp_confidence(parsed.get("confidence"), 0.75),
            )
            return result
        except Exception as exc:
            logger.error("[STATE_ANALYZER] llm fallback failed: %s", exc, exc_info=True)
            return self._fallback_from_deterministic(deterministic, confidence=0.55)

    def _get_client(self) -> Optional[Any]:
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI

            api_key = getattr(config, "OPENAI_API_KEY", None)
            if not api_key:
                return None
            self._client = AsyncOpenAI(api_key=api_key)
            return self._client
        except Exception:
            return None

    @staticmethod
    def _parse_json(text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        return json.loads(cleaned)

    @staticmethod
    def _build_previous_context(previous_thread: Optional[ThreadState]) -> str:
        if previous_thread is None:
            return "нет"
        return (
            f"Тема нити: {previous_thread.core_direction}\n"
            f"Фаза: {previous_thread.phase}\n"
            f"Открытые петли: {previous_thread.open_loops}\n"
            f"Закрытые петли: {previous_thread.closed_loops}"
        )

    @staticmethod
    def _build_hints(deterministic: _DeterministicResult) -> str:
        parts = [f"nervous_state={deterministic.nervous_state} ({deterministic.nervous_conf:.2f})"]
        if deterministic.intent is not None:
            parts.append(f"intent={deterministic.intent} ({deterministic.intent_conf:.2f})")
        if deterministic.openness is not None:
            parts.append(f"openness={deterministic.openness} ({deterministic.openness_conf:.2f})")
        return "; ".join(parts)

    @staticmethod
    def _fallback_from_deterministic(
        deterministic: _DeterministicResult,
        *,
        confidence: float,
    ) -> StateSnapshot:
        return StateSnapshot(
            nervous_state=deterministic.nervous_state,
            intent=deterministic.intent or "explore",
            openness=deterministic.openness or "open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=_clamp_confidence(confidence, 0.55),
        )

    @staticmethod
    def _default_snapshot() -> StateSnapshot:
        return StateSnapshot(
            nervous_state="window",
            intent="explore",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.5,
        )

    @staticmethod
    def _onboarding_snapshot() -> StateSnapshot:
        return StateSnapshot(
            nervous_state="window",
            intent="contact",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.9,
        )


state_analyzer_agent = StateAnalyzerAgent()
