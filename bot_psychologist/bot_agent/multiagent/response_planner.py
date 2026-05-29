"""Deterministic response planner for next meaningful move selection."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .dialogue_policy import (
    DIALOGUE_PROFILE_MVP_FREE,
    detect_expansion_request,
    detect_repair_and_expand_request,
    detect_short_support_request,
    normalize_dialogue_profile,
)

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
    "concept_explanation_full",
    "expanded_explanation",
    "example_driven_explanation",
    "repair_and_expand",
}

RESPONSE_DEPTHS = {"very_short", "short", "medium", "long", "deep"}
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

_LOW_RESOURCE_MARKERS = (
    "схлопнул",
    "пустой",
    "не тяну длинные",
    "нет сил",
    "не могу думать",
    "очень устал",
    "без анализа",
    "пару спокойных слов",
    "просто поддержи",
    "не грузи",
    "коротко",
)
_SOFT_DISTRESS_MARKERS = (
    "очень плохо",
    "не выдерживаю",
    "не вывожу",
    "мне страшно",
    "разваливаюсь",
    "не справляюсь",
)
_WORLD_BLAME_MARKERS = (
    "все тупят",
    "люди тормозят",
    "они идиоты",
    "мир не понимает",
    "мне надо всех дожать",
    "почему они такие",
    "все вокруг неадекватные",
)
_NO_QUESTION_MARKERS = (
    "без вопросов",
    "не задавай вопросов",
    "просто продолжи мысль",
    "ответь без вопроса",
)
_MECHANISM_MARKERS = (
    "механизм",
    "разбор механизма",
    "почему я застреваю",
    "почему застреваю",
    "как это работает",
)
_CLOSE_MARKERS = (
    "спасибо",
    "благодарю",
    "понял, спасибо",
    "ок, спасибо",
)
_EXPLICIT_STEP_MARKERS = (
    "один шаг",
    "что сделать прямо сейчас",
    "что делать прямо сейчас",
    "хочу действие",
    "дай шаг",
)
_EXPLICIT_PRACTICE_MARKERS = (
    "практик",
    "упражн",
    "дай практику",
)
_NEGATED_PRACTICE_PATTERNS = (
    r"\bбез\s+(?:перехода\s+в\s+)?практик\w*",
    r"\bбез\s+упражнен\w*",
    r"\bне\s+дава(?:й|йте|ть)\s+практик\w*",
)
_REPAIR_TEXT_MARKERS = (
    "ты ушел не туда",
    "вернись к сути",
    "снова предлагаешь практику",
    "я просил разбор механизма",
    "это не то, чего я просил",
)
_SELF_HARM_MARKERS = (
    "хочу умер",
    "убить себя",
    "суицид",
    "покончить с собой",
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


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def detect_low_resource_text(user_message: str) -> bool:
    return _contains_any(user_message, _LOW_RESOURCE_MARKERS)


def detect_soft_distress_text(user_message: str) -> bool:
    return _contains_any(user_message, _SOFT_DISTRESS_MARKERS)


def detect_world_blame_defensive_text(user_message: str) -> bool:
    return _contains_any(user_message, _WORLD_BLAME_MARKERS)


def detect_no_question_request(user_message: str) -> bool:
    return _contains_any(user_message, _NO_QUESTION_MARKERS)


def detect_close_text(user_message: str) -> bool:
    message = _normalize(user_message)
    compact = re.sub(r"[.!?,;:]+", "", message).strip()
    if compact in {"спасибо", "благодарю"}:
        return True
    return _contains_any(message, _CLOSE_MARKERS)


def detect_mechanism_request_text(user_message: str) -> bool:
    return _contains_any(user_message, _MECHANISM_MARKERS)


def detect_practice_suppression_text(user_message: str) -> bool:
    text = _normalize(user_message)
    return any(re.search(pattern, text) for pattern in _NEGATED_PRACTICE_PATTERNS)


def detect_explicit_practice_or_step_request(user_message: str) -> dict[str, bool]:
    text = _normalize(user_message)
    wants_step = _contains_any(text, _EXPLICIT_STEP_MARKERS)
    has_practice_marker = _contains_any(text, _EXPLICIT_PRACTICE_MARKERS)
    practice_negated = any(re.search(pattern, text) for pattern in _NEGATED_PRACTICE_PATTERNS)
    wants_practice = has_practice_marker and not practice_negated
    wants_action = wants_step or wants_practice
    return {
        "wants_step": wants_step,
        "wants_practice": wants_practice,
        "wants_action": wants_action,
    }


def detect_repair_misalignment_text(user_message: str) -> bool:
    return _contains_any(user_message, _REPAIR_TEXT_MARKERS)


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
    dialogue_policy: dict[str, Any] | None = None,
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

    low_resource_text = detect_low_resource_text(message)
    soft_distress_text = detect_soft_distress_text(message)
    defensive_text = detect_world_blame_defensive_text(message)
    no_question_text = detect_no_question_request(message)
    close_text = detect_close_text(message)
    mechanism_text = detect_mechanism_request_text(message)
    practice_suppression_text = detect_practice_suppression_text(message)
    explicit_action = detect_explicit_practice_or_step_request(message)
    repair_text = detect_repair_misalignment_text(message)
    explicit_action_requested = bool(explicit_action.get("wants_action", False))
    explicit_step_requested = bool(explicit_action.get("wants_step", False))
    explicit_practice_requested = bool(explicit_action.get("wants_practice", False))
    has_self_harm_marker = _contains_any(message, _SELF_HARM_MARKERS)
    dialogue_policy_payload = dict(dialogue_policy or {})
    dialogue_profile = normalize_dialogue_profile(dialogue_policy_payload.get("profile", "safe_guided"))
    expansion_requested = bool(dialogue_policy_payload.get("expansion_requested", False)) or detect_expansion_request(message)
    repair_and_expand_requested = bool(
        dialogue_policy_payload.get("repair_and_expand_requested", False)
    ) or detect_repair_and_expand_request(message)
    active_concept = str(dialogue_policy_payload.get("active_concept", "") or "").strip().lower()
    explicit_short_support = detect_short_support_request(message)

    safety_priority = bool(safety_active or safety_flag or response_mode == "safe_override")
    revoicing_policy = "allowed" if revoicing_allowed else "suppressed"
    question_policy = "none" if not should_ask_question else "max_one_if_needed"
    if no_question_text:
        question_policy = "none"
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
        "low_resource_text": low_resource_text,
        "soft_distress_text": soft_distress_text,
        "defensive_text": defensive_text,
        "no_question_text": no_question_text,
        "close_text": close_text,
        "mechanism_text": mechanism_text,
        "practice_suppression_text": practice_suppression_text,
        "repair_text": repair_text,
        "explicit_action_requested": explicit_action_requested,
        "explicit_step_requested": explicit_step_requested,
        "explicit_practice_requested": explicit_practice_requested,
        "dialogue_profile": dialogue_profile,
        "expansion_requested": expansion_requested,
        "repair_and_expand_requested": repair_and_expand_requested,
        "active_concept": active_concept,
        "explicit_short_support": explicit_short_support,
    }

    if (
        dialogue_profile == DIALOGUE_PROFILE_MVP_FREE
        and expansion_requested
        and not safety_priority
        and not soft_distress_text
        and not explicit_short_support
    ):
        if repair_and_expand_requested:
            return _build_decision(
                next_move="repair_misalignment",
                answer_shape="repair_and_expand",
                response_depth="long",
                target_micro_shift="исправить непонятность и дать полноценное объяснение",
                should_answer_directly=True,
                question_policy="none",
                practice_policy="allowed_if_explicit",
                revoicing_policy="suppressed",
                continuity_policy="repair_and_continue",
                safety_priority=False,
                must_include=["дать ясное объяснение", "дать пример", "показать применение"],
                must_avoid=["не повторять прежнюю короткую формулировку"],
                source_signals=source_signals,
                confidence=0.93,
                rationale="MVP free dialogue: repair+expand запрос приоритетен.",
            )
        if should_answer_directly or active_concept:
            return _build_decision(
                next_move="answer_known_concept",
                answer_shape="concept_explanation_full",
                response_depth="deep",
                target_micro_shift="дать полноценное объяснение known concept в несколько смысловых блоков",
                should_answer_directly=True,
                question_policy="none",
                practice_policy="allowed_if_explicit",
                revoicing_policy="suppressed",
                continuity_policy="continue_active_line",
                safety_priority=False,
                must_include=["дать ясное объяснение", "дать пример", "показать применение"],
                must_avoid=["не сводить ответ к одной короткой фразе"],
                source_signals=source_signals,
                confidence=0.94,
                rationale="MVP free dialogue: expansion follow-up inherits active concept and allows deep answer.",
            )
        return _build_decision(
            next_move="deepen_mechanism",
            answer_shape="expanded_explanation",
            response_depth="long",
            target_micro_shift="дать развёрнутое объяснение по текущей линии без укорачивания",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="allowed_if_explicit",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=False,
            must_include=["дать ясное объяснение", "дать пример", "показать применение"],
            must_avoid=["не уходить в short_support без явного запроса"],
            source_signals=source_signals,
            confidence=0.9,
            rationale="MVP free dialogue: explicit expansion request overrides short-support tendencies.",
        )

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

    if soft_distress_text and not has_self_harm_marker:
        return _build_decision(
            next_move="stabilize_safety",
            answer_shape="safety_grounding",
            response_depth="short",
            target_micro_shift="дать короткую опору здесь-и-сейчас без углубления в теорию",
            should_answer_directly=True,
            question_policy="none",
            practice_policy="required_for_safety_or_grounding",
            revoicing_policy="suppressed",
            continuity_policy="continue_active_line",
            safety_priority=True,
            must_include=["короткая стабилизация", "простая опора", "здесь-и-сейчас"],
            must_avoid=["не уходить в философскую глубину", "не расширять анализ"],
            source_signals=source_signals,
            confidence=0.9,
            rationale="Текст указывает на мягкий distress: нужен короткий стабилизирующий ход.",
        )

    if intent == "correction_of_bot" or continuity_mode == "repair_and_continue_line" or repair_mode or repair_text:
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

    if intent == "thanks_close" or close_text:
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
            must_avoid=["не открывать новый шаг", "не давать практику", "не задавать вопрос"],
            source_signals=source_signals,
            confidence=0.95,
            rationale="Thanks/close сигнал: нужен мягкий выход без нового loop.",
        )

    if low_resource_text or intent == "short_support" or (
        dialogue_profile != DIALOGUE_PROFILE_MVP_FREE
        and nervous_state == "hypo"
        and not explicit_action_requested
    ):
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
            must_avoid=["без лекции", "без практики", "без глубокого анализа"],
            source_signals=source_signals,
            confidence=0.9,
            rationale="Low-resource контур: предпочтителен сверхкороткий контакт.",
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

    if explicit_action_requested:
        if practice_allowed and (should_offer_practice or explicit_step_requested or explicit_practice_requested):
            return _build_decision(
                next_move="give_direct_step",
                answer_shape="one_step",
                response_depth="short",
                target_micro_shift="дать один исполнимый микро-шаг без списка",
                should_answer_directly=True,
                question_policy="none",
                practice_policy="one_micro_step_allowed",
                revoicing_policy="suppressed",
                continuity_policy="continue_active_line",
                safety_priority=False,
                must_include=["один конкретный шаг"],
                must_avoid=["без списка шагов", "без новой теории"],
                source_signals=source_signals,
                confidence=0.9,
                rationale="Явный запрос на действие и gate разрешает единичный шаг.",
            )
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
            confidence=0.86,
            rationale="Запрос на действие есть, но gate запрещает практический ход.",
        )

    if defensive_text or _coerce_text(_get(thread_state, "ok_position", ""), "").upper() == "I+W-":
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
            confidence=0.84,
            rationale="Defensive контур: лучше один точный вопрос, чем длинный ответ.",
        )

    mechanism_override = mechanism_text and (no_question_text or practice_suppression_text)
    if intent == "understand_mechanism" or mechanism_override:
        mechanism_question_policy = question_policy if should_ask_question else "none"
        if mechanism_override and not no_question_text:
            mechanism_question_policy = "max_one_if_needed"
        return _build_decision(
            next_move="deepen_mechanism",
            answer_shape="mechanism_explanation",
            response_depth="medium",
            target_micro_shift="показать один механизм, который продвигает понимание",
            should_answer_directly=True,
            question_policy=mechanism_question_policy,
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

    return _build_decision(
        next_move="continue_active_line",
        answer_shape="compact_direct",
        response_depth="short",
        target_micro_shift="продолжить текущую смысловую линию одним точным ходом",
        should_answer_directly=True,
        question_policy=question_policy,
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
