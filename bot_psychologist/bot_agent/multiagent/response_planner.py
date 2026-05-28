"""Deterministic response planner for next meaningful move selection."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


RESPONSE_PLANNER_VERSION = "response_planner_v1"

NEXT_MOVES = {
    "answer_known_concept",
    "deepen_mechanism",
    "repair_misalignment",
    "give_direct_step",
    "give_practice",
    "give_short_support",
    "close_gently",
    "stabilize_safety",
    "clarify_one_point",
    "continue_active_line",
}

ANSWER_SHAPES = {
    "compact_direct",
    "mechanism_explanation",
    "repair_acknowledgement",
    "one_step",
    "short_support",
    "gentle_close",
    "safety_grounding",
    "one_question",
}

RESPONSE_DEPTHS = {"very_short", "short", "medium"}
QUESTION_POLICIES = {"none", "max_one_if_needed", "required_one_clarifying"}
PRACTICE_POLICIES = {
    "forbidden",
    "allowed_if_explicit",
    "one_micro_step_allowed",
    "required_for_safety_or_grounding",
}
REVOICING_POLICIES = {"suppressed", "minimal_allowed", "allowed"}
CONTINUITY_POLICIES = {
    "continue_active_line",
    "start_new_line",
    "repair_and_continue",
    "close_without_new_loop",
}

_EXPLICIT_PRACTICE_RE = re.compile(r"(практик|упражн|сделай шаг|шаг\b)", re.IGNORECASE)
_EXPLICIT_STEP_RE = re.compile(r"(один шаг|что делать сейчас|что сделать сейчас)", re.IGNORECASE)
_LOW_RESOURCE_RE = re.compile(
    r"(устал|без анализа|пару спокойных слов|просто поддержи|без советов)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResponsePlannerDecision:
    version: str
    enabled: bool
    next_move: str
    answer_shape: str
    response_depth: str
    target_micro_shift: str
    should_answer_directly: bool
    question_policy: str
    practice_policy: str
    revoicing_policy: str
    continuity_policy: str
    safety_priority: bool
    must_include: list[str]
    must_avoid: list[str]
    source_signals: dict[str, Any]
    confidence: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _coerce_text(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _safe_confidence(value: float) -> float:
    return max(0.0, min(0.99, round(float(value), 2)))


def _build_decision(
    *,
    next_move: str,
    answer_shape: str,
    response_depth: str,
    target_micro_shift: str,
    should_answer_directly: bool,
    question_policy: str,
    practice_policy: str,
    revoicing_policy: str,
    continuity_policy: str,
    safety_priority: bool,
    must_include: list[str],
    must_avoid: list[str],
    source_signals: dict[str, Any],
    confidence: float,
    rationale: str,
) -> ResponsePlannerDecision:
    return ResponsePlannerDecision(
        version=RESPONSE_PLANNER_VERSION,
        enabled=True,
        next_move=next_move if next_move in NEXT_MOVES else "continue_active_line",
        answer_shape=answer_shape if answer_shape in ANSWER_SHAPES else "compact_direct",
        response_depth=response_depth if response_depth in RESPONSE_DEPTHS else "short",
        target_micro_shift=str(target_micro_shift or ""),
        should_answer_directly=bool(should_answer_directly),
        question_policy=question_policy if question_policy in QUESTION_POLICIES else "none",
        practice_policy=practice_policy if practice_policy in PRACTICE_POLICIES else "forbidden",
        revoicing_policy=revoicing_policy if revoicing_policy in REVOICING_POLICIES else "suppressed",
        continuity_policy=continuity_policy if continuity_policy in CONTINUITY_POLICIES else "continue_active_line",
        safety_priority=bool(safety_priority),
        must_include=[str(item) for item in must_include if str(item).strip()],
        must_avoid=[str(item) for item in must_avoid if str(item).strip()],
        source_signals=dict(source_signals or {}),
        confidence=_safe_confidence(confidence),
        rationale=str(rationale or ""),
    )


def build_response_planner_fallback_decision(
    *,
    reason: str,
    source_signals: dict[str, Any],
) -> ResponsePlannerDecision:
    return _build_decision(
        next_move="continue_active_line",
        answer_shape="compact_direct",
        response_depth="short",
        target_micro_shift="дать один ясный ответ без лишнего расширения",
        should_answer_directly=True,
        question_policy="none",
        practice_policy="forbidden",
        revoicing_policy="suppressed",
        continuity_policy="continue_active_line",
        safety_priority=False,
        must_include=["один ясный ход", "связать с текущей линией"],
        must_avoid=["не предлагать практику по умолчанию", "не открывать новую теорию"],
        source_signals=source_signals,
        confidence=0.5,
        rationale=f"fallback: {reason}",
    )


def build_response_planner_decision(
    *,
    user_message: str,
    state_snapshot: Any,
    thread_state: Any,
    diagnostic_card: Any | None,
    active_line: dict[str, Any],
    knowledge_answer_guard: dict[str, Any],
    philosophy_kernel: dict[str, Any],
    context_package: Any | None = None,
) -> ResponsePlannerDecision:
    del context_package, diagnostic_card, philosophy_kernel

    message = _normalize(user_message)
    response_mode = _coerce_text(_get(thread_state, "response_mode", "reflect"), "reflect")
    safety_active = bool(_get(thread_state, "safety_active", False))
    safety_flag = bool(_get(state_snapshot, "safety_flag", False))
    nervous_state = _normalize(_coerce_text(_get(state_snapshot, "nervous_state", ""), ""))

    intent = _coerce_text(active_line.get("user_intent", "unknown"), "unknown")
    continuity_mode = _coerce_text(
        active_line.get("continuity_mode", "continue_existing_line"),
        "continue_existing_line",
    )
    repair_mode = active_line.get("repair_mode")
    should_ask_question = bool(active_line.get("should_ask_question", False))
    should_offer_practice = bool(active_line.get("should_offer_practice", False))
    revoicing_allowed = bool(active_line.get("revoicing_allowed", False))

    knowledge_answer = (
        dict(knowledge_answer_guard.get("knowledge_answer", {}))
        if isinstance(knowledge_answer_guard.get("knowledge_answer"), dict)
        else {}
    )
    practice_gate = (
        dict(knowledge_answer_guard.get("practice_gate", {}))
        if isinstance(knowledge_answer_guard.get("practice_gate"), dict)
        else {}
    )

    practice_allowed = bool(practice_gate.get("practice_allowed", True))
    should_answer_directly = bool(knowledge_answer.get("should_answer_directly", False))
    knowledge_needed = bool(knowledge_answer.get("needed", False))

    safety_priority = bool(safety_active or safety_flag or response_mode == "safe_override")
    revoicing_policy = "allowed" if revoicing_allowed else "suppressed"
    question_policy = "none" if not should_ask_question else "max_one_if_needed"
    practice_policy = "allowed_if_explicit" if practice_allowed else "forbidden"

    source_signals = {
        "active_line_user_intent": intent,
        "active_line_continuity_mode": continuity_mode,
        "active_line_should_ask_question": should_ask_question,
        "practice_gate_allowed": practice_allowed,
        "knowledge_answer_needed": knowledge_needed,
        "knowledge_answer_should_answer_directly": should_answer_directly,
        "response_mode": response_mode,
        "safety_active": safety_active,
        "safety_flag": safety_flag,
        "nervous_state": nervous_state,
    }

    if safety_priority:
        return _build_decision(
            next_move="stabilize_safety",
            answer_shape="safety_grounding",
            response_depth="short",
            target_micro_shift="снизить риск и стабилизировать контакт здесь-и-сейчас",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="required_for_safety_or_grounding",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=True,
            must_include=["короткая стабилизация", "приоритет безопасности"],
            must_avoid=["не уходить в философскую глубину", "не расширять анализ"],
            source_signals=source_signals,
            confidence=0.95,
            rationale="Safety имеет приоритет над обычной логикой planner.",
        )

    if intent == "correction_of_bot" or continuity_mode == "repair_and_continue_line" or repair_mode:
        return _build_decision(
            next_move="repair_misalignment",
            answer_shape="repair_acknowledgement",
            response_depth="short",
            target_micro_shift="признать сдвиг и вернуть ответ к активной линии",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="forbidden",
            revoicing_policy="suppressed",
            continuity_policy="repair_and_continue",
            safety_priority=False,
            must_include=["признать сдвиг", "вернуться к active_line"],
            must_avoid=["не предлагать новую практику", "не начинать новую теорию"],
            source_signals=source_signals,
            confidence=0.92,
            rationale="Correction/repair сигнал требует короткого repair-хода без практики.",
        )

    if intent == "thanks_close":
        return _build_decision(
            next_move="close_gently",
            answer_shape="gentle_close",
            response_depth="very_short",
            target_micro_shift="закрыть контакт без нового цикла задач",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="forbidden",
            revoicing_policy="minimal_allowed",
            continuity_policy="close_without_new_loop",
            safety_priority=False,
            must_include=["краткое закрытие контакта"],
            must_avoid=["не открывать новый шаг", "не давать практику"],
            source_signals=source_signals,
            confidence=0.94,
            rationale="Thanks/close сигнал: нужен мягкий выход без нового loop.",
        )

    if intent == "short_support" or _LOW_RESOURCE_RE.search(message) or nervous_state == "hypo":
        return _build_decision(
            next_move="give_short_support",
            answer_shape="short_support",
            response_depth="very_short",
            target_micro_shift="дать короткий поддерживающий контакт без перегруза",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="forbidden",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["коротко", "без давления"],
            must_avoid=["без лекции", "без практики и таймеров"],
            source_signals=source_signals,
            confidence=0.88,
            rationale="Low-resource или short-support: предпочтителен сверхкороткий контакт.",
        )

    if should_answer_directly:
        return _build_decision(
            next_move="answer_known_concept",
            answer_shape="compact_direct",
            response_depth="short",
            target_micro_shift="дать прямой смысл по известному концепту без встречных барьеров",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="forbidden",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["дать определение/смысл сразу", "связать с текущей линией"],
            must_avoid=["не просить пользователя определять термин", "без внешнего surveillance-фрейма"],
            source_signals=source_signals,
            confidence=0.91,
            rationale="Knowledge-answer direct path активен: ответ сначала, без уточняющего барьера.",
        )

    explicit_step_requested = bool(_EXPLICIT_STEP_RE.search(message))
    explicit_practice_requested = bool(_EXPLICIT_PRACTICE_RE.search(message))
    explicit_action_requested = intent in {"ask_for_direct_step", "ask_for_practice"} or explicit_step_requested

    if explicit_action_requested and practice_allowed and should_offer_practice:
        move = "give_direct_step" if (intent == "ask_for_direct_step" or explicit_step_requested) else "give_practice"
        return _build_decision(
            next_move=move,
            answer_shape="one_step",
            response_depth="short",
            target_micro_shift="дать один исполнимый микро-шаг без списка",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="one_micro_step_allowed",
            revoicing_policy=revoicing_policy,
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["один конкретный шаг"],
            must_avoid=["без списка шагов", "без новой теории"],
            source_signals=source_signals,
            confidence=0.87,
            rationale="Пользователь явно просит действие и practice gate разрешает единичный шаг.",
        )

    if explicit_practice_requested and not practice_allowed:
        return _build_decision(
            next_move="clarify_one_point",
            answer_shape="one_question",
            response_depth="short",
            target_micro_shift="удержать линию без практики и уточнить один нужный фокус",
            should_answer_directly=False,
            question_policy="required_one_clarifying",
            practice_policy="forbidden",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["один уточняющий вопрос по контексту"],
            must_avoid=["не давать практику вопреки gate"],
            source_signals=source_signals,
            confidence=0.84,
            rationale="Запрос на практику есть, но gate запрещает практический ход.",
        )

    if intent == "understand_mechanism":
        return _build_decision(
            next_move="deepen_mechanism",
            answer_shape="mechanism_explanation",
            response_depth="medium",
            target_micro_shift="показать один механизм, который продвигает понимание",
            should_answer_directly=True,
            question_policy=question_policy if should_ask_question else "none",
            practice_policy="forbidden",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["назвать один механизм", "связать с active_line"],
            must_avoid=["не предлагать практику", "не начинать механический пересказ"],
            source_signals=source_signals,
            confidence=0.9,
            rationale="Mechanism intent: нужен объяснительный ход без разворота в практику.",
        )

    if _coerce_text(_get(thread_state, "ok_position", ""), "").upper() == "I+W-":
        return _build_decision(
            next_move="clarify_one_point",
            answer_shape="one_question",
            response_depth="short",
            target_micro_shift="снять defensive-поляризацию через один decenter-вопрос",
            should_answer_directly=False,
            question_policy="required_one_clarifying",
            practice_policy="forbidden",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["один вопрос для декентрации"],
            must_avoid=["не входить в коалицию против мира", "без длинной лекции"],
            source_signals=source_signals,
            confidence=0.81,
            rationale="I+W- defensive контур: лучше один точный вопрос, чем длинный ответ.",
        )

    return _build_decision(
        next_move="continue_active_line",
        answer_shape="compact_direct",
        response_depth="short",
        target_micro_shift="продолжить текущую смысловую линию одним точным ходом",
        should_answer_directly=True,
        question_policy="none" if not should_ask_question else "max_one_if_needed",
        practice_policy=practice_policy,
        revoicing_policy="suppressed" if not revoicing_allowed else "minimal_allowed",
        continuity_policy="continue_active_line",
        safety_priority=False,
        must_include=["держать continuity", "один следующий ход"],
        must_avoid=["не расползаться в несколько направлений"],
        source_signals=source_signals,
        confidence=0.75,
        rationale="Default path: continuity-first один компактный ход без unsolicited практики.",
    )


__all__ = [
    "RESPONSE_PLANNER_VERSION",
    "ResponsePlannerDecision",
    "build_response_planner_decision",
    "build_response_planner_fallback_decision",
]
