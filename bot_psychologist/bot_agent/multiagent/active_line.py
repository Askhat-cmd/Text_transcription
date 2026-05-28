"""Active Line / Dialogue Continuity v1 helpers."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


ACTIVE_LINE_VERSION = "active_line_v1"

USER_INTENTS = {
    "understand_mechanism",
    "ask_for_practice",
    "ask_for_direct_step",
    "short_support",
    "known_concept_question",
    "correction_of_bot",
    "thanks_close",
    "unknown",
}

CONTINUITY_MODES = {
    "continue_existing_line",
    "start_new_line",
    "repair_and_continue_line",
    "close_gently",
}

_CORRECTION_RE = re.compile(
    r"(почему\s+ты\s+мне\s+предлагаешь\s+практик\w+|ты\s+не\s+понял\w*|я\s+ведь\s+хочу\s+разобрать\w+|не[тт],?\s+я\s+не\s+это\s+имел)",
    re.IGNORECASE,
)
_UNDERSTAND_RE = re.compile(
    r"(хочу\s+разобрать\w+|помоги\s+понят\w+|в\s+чем\s+механизм|что\s+происход\w+|почему)",
    re.IGNORECASE,
)
_ASK_PRACTICE_RE = re.compile(
    r"(практик\w+|упражн\w+)",
    re.IGNORECASE,
)
_ASK_DIRECT_STEP_RE = re.compile(
    r"(дай\s+один\s+конкретн\w+\s+шаг|что\s+сделать\s+прямо\s+сейчас|что\s+делать\s+прямо\s+сейчас|что\s+делать\??)",
    re.IGNORECASE,
)
_NO_PRACTICE_RE = re.compile(
    r"(не\s+нужн\w+\s+практик\w+|без\s+практик\w+|не\s+предлагай\s+практик\w+)",
    re.IGNORECASE,
)
_SHORT_SUPPORT_RE = re.compile(
    r"(я\s+устал\w*|пару\s+спокойн\w+\s+слов|без\s+анализ\w+|побудь\s+со\s+мной\s+коротк\w+)",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(r"^\s*(спасибо|благодарю|спс|thanks)\s*[!.]?\s*$", re.IGNORECASE)
_KNOWN_CONCEPT_RE = re.compile(r"(нейросталкинг|самореализац\w+)", re.IGNORECASE)
_FORECASTING_WORK_RE = re.compile(
    r"(на\s+работе|слишком\s+много\s+думаю|прежде\s+чем\s+действов\w+|подстелить\s+соломк\w+|прогнозир\w+|откладываю\s+старт|когда\s+начинаю,\s*чувствую\s+что\s+уже\s+устал)",
    re.IGNORECASE,
)
_MECHANICAL_REVOICING_OPENERS = (
    "асхат, похоже",
    "похоже, вы хотите",
    "вы говорите",
    "вы спрашиваете",
    "вы сейчас",
    "мне важно уточнить",
)


@dataclass(frozen=True)
class ActiveLineState:
    version: str
    active_line: str
    user_intent: str
    continuity_mode: str
    next_meaningful_move: str
    should_continue_line: bool
    should_ask_question: bool
    should_offer_practice: bool
    revoicing_allowed: bool
    revoicing_style: str
    repair_mode: str | None
    evidence_turn_ids: list[str]
    confidence: float
    practice_suppression_active: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def classify_user_intent(user_message: str) -> str:
    message = _normalize(user_message)
    if not message:
        return "unknown"
    if _CORRECTION_RE.search(message):
        return "correction_of_bot"
    if _THANKS_RE.match(message):
        return "thanks_close"
    if _NO_PRACTICE_RE.search(message):
        return "understand_mechanism"
    if _ASK_DIRECT_STEP_RE.search(message):
        return "ask_for_direct_step"
    if _ASK_PRACTICE_RE.search(message):
        return "ask_for_practice"
    if _SHORT_SUPPORT_RE.search(message):
        return "short_support"
    if _KNOWN_CONCEPT_RE.search(message) and "?" in message:
        return "known_concept_question"
    if _UNDERSTAND_RE.search(message) or _NO_PRACTICE_RE.search(message):
        return "understand_mechanism"
    return "unknown"


def _build_active_line_text(*, message: str, context: str, intent: str) -> str:
    if intent == "thanks_close":
        return "завершение контакта без нового шага"
    if intent == "correction_of_bot":
        return "возврат к разбору механизма после жалобы на преждевременную практику"
    if _FORECASTING_WORK_RE.search(message) or _FORECASTING_WORK_RE.search(context):
        return (
            "застревание на старте рабочей задачи: прогнозирование и контроль "
            "съедают ресурс до действия"
        )
    if intent == "known_concept_question":
        return "связать известный концепт с текущей линией разговора без перезапуска"
    if intent in {"understand_mechanism", "short_support"}:
        return "помочь увидеть механизм происходящего без ухода в практику"
    if intent in {"ask_for_practice", "ask_for_direct_step"}:
        return "дать один уместный шаг как продолжение уже понятой линии"
    return "продолжить текущую смысловую линию без механического пересказа"


def _build_next_move(*, intent: str, message: str, context: str) -> str:
    if intent == "correction_of_bot":
        return "признать сдвиг и вернуть фокус на механизм, без новой практики"
    if intent == "thanks_close":
        return "кратко закрыть контакт без нового задания"
    if intent == "ask_for_direct_step":
        return "дать один конкретный шаг без списка и лекции"
    if intent == "ask_for_practice":
        return "дать короткую практику только в пределах одного шага"
    if intent == "known_concept_question":
        return "связать смысл концепта с текущим узлом диалога"
    if _FORECASTING_WORK_RE.search(message) or _FORECASTING_WORK_RE.search(context):
        return "показать, как прогнозирование и контроль забирают энергию до старта"
    if intent == "understand_mechanism":
        return "назвать механизм и при необходимости задать один уточняющий вопрос"
    if intent == "short_support":
        return "дать короткий поддерживающий контакт без анализа и практики"
    return "продолжить линию и сделать один смысловой следующий ход"


def _build_continuity_mode(*, intent: str, context: str) -> str:
    if intent == "thanks_close":
        return "close_gently"
    if intent == "correction_of_bot":
        return "repair_and_continue_line"
    if context.strip():
        return "continue_existing_line"
    return "start_new_line"


def build_active_line_state(
    *,
    user_message: str,
    conversation_context: str,
    response_mode: str,
    practice_allowed: bool,
    evidence_turn_ids: list[str] | None = None,
) -> ActiveLineState:
    message = _normalize(user_message)
    context = _normalize(conversation_context)
    intent = classify_user_intent(message)
    if intent == "unknown":
        intent = "understand_mechanism"
    continuity_mode = _build_continuity_mode(intent=intent, context=context)
    practice_forbidden = bool(_NO_PRACTICE_RE.search(message))
    repair_mode = "acknowledge_and_return_to_mechanism" if intent == "correction_of_bot" else None

    should_offer_practice = (
        intent in {"ask_for_practice", "ask_for_direct_step"} and practice_allowed and not practice_forbidden
    )
    if intent in {"understand_mechanism", "correction_of_bot", "thanks_close", "short_support"}:
        should_offer_practice = False
    if response_mode == "safe_override":
        should_offer_practice = True

    should_ask_question = intent in {"understand_mechanism", "known_concept_question"} and not bool(
        _FORECASTING_WORK_RE.search(message)
    )
    if intent in {"thanks_close", "short_support", "correction_of_bot"}:
        should_ask_question = False

    revoicing_allowed = intent == "ask_for_practice" and continuity_mode == "start_new_line"
    if intent in {"understand_mechanism", "known_concept_question", "short_support", "correction_of_bot", "thanks_close"}:
        revoicing_allowed = False
    if continuity_mode in {"continue_existing_line", "repair_and_continue_line"}:
        revoicing_allowed = False

    confidence = 0.55
    if intent != "unknown":
        confidence += 0.15
    if _FORECASTING_WORK_RE.search(message) or _FORECASTING_WORK_RE.search(context):
        confidence += 0.15
    if intent == "correction_of_bot":
        confidence += 0.1
    confidence = max(0.0, min(0.99, confidence))

    return ActiveLineState(
        version=ACTIVE_LINE_VERSION,
        active_line=_build_active_line_text(message=message, context=context, intent=intent),
        user_intent=intent if intent in USER_INTENTS else "unknown",
        continuity_mode=continuity_mode if continuity_mode in CONTINUITY_MODES else "continue_existing_line",
        next_meaningful_move=_build_next_move(intent=intent, message=message, context=context),
        should_continue_line=continuity_mode in {"continue_existing_line", "repair_and_continue_line"},
        should_ask_question=bool(should_ask_question),
        should_offer_practice=bool(should_offer_practice),
        revoicing_allowed=bool(revoicing_allowed),
        revoicing_style="light_mirror" if revoicing_allowed else "suppressed",
        repair_mode=repair_mode,
        evidence_turn_ids=list(evidence_turn_ids or []),
        confidence=round(confidence, 2),
        practice_suppression_active=not bool(should_offer_practice),
    )


def starts_with_mechanical_revoicing(answer_text: str) -> bool:
    lowered = _normalize(answer_text)
    return any(lowered.startswith(marker) for marker in _MECHANICAL_REVOICING_OPENERS)


__all__ = [
    "ACTIVE_LINE_VERSION",
    "ActiveLineState",
    "build_active_line_state",
    "classify_user_intent",
    "starts_with_mechanical_revoicing",
]
