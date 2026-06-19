"""Unified dialogue act resolution for PRD-047.12."""

from __future__ import annotations

import re
from typing import Any


DIALOGUE_ACT_RESOLVER_VERSION = "dialogue_act_resolver_v1"

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")
_SELF_INTRO_MARKERS = (
    "меня зовут",
    "мое имя",
    "моё имя",
    "my name is",
    "i am ",
    "i'm ",
)
_GREETING_MARKERS = (
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "hello",
    "hi",
    "hey",
)
_CLOSE_ACK_MARKERS = (
    "спасибо",
    "благодарю",
    "спс",
    "thanks",
    "thank you",
)
_AFFIRM_MARKERS = {
    "да",
    "давай",
    "ага",
    "угу",
    "ок",
    "окей",
    "okay",
    "ok",
    "yes",
    "sure",
    "можно",
    "покажи",
}
_REJECTION_MARKERS = ("не надо", "не хочу", "не стоит", "нет, не надо", "не сейчас")
_REPAIR_MARKERS = (
    "ты не ответил",
    "ты опять не ответил",
    "ты снова не ответил",
    "ответь на вопрос",
    "вернись к вопросу",
    "я спрашивал другое",
    "ты ушел не туда",
    "ты ушёл не туда",
    "мимо",
    "это не ответ",
    "не уходи от вопроса",
    "ты усложнил",
    "я просто познакомился",
)
_STYLE_MARKERS = (
    "спокойнее",
    "спокойно",
    "короче",
    "коротко",
    "развернуто",
    "развёрнуто",
    "подробно",
    "проще",
    "без практик",
    "без упражнений",
    "без вопросов",
    "без лекции",
    "без воды",
)
_SUMMARY_MARKERS = (
    "подведи итог",
    "подведи краткий итог",
    "итог разговора",
    "итог нашей беседы",
    "итог нашего разговора",
    "краткий итог",
    "сделай итог",
    "дай итог",
    "сделай резюме",
    "резюмируй",
    "обобщи весь разговор",
    "обобщи наш разговор",
    "обобщи переписку",
    "суммируй",
    "собери кратко",
    "собери все вместе",
    "собери всё вместе",
    "к чему мы пришли",
    "что мы поняли",
    "recap",
    "summary",
    "summarize",
    "summarise",
    "conversation summary",
    "what did we cover",
    "what have we concluded",
)
_SUMMARY_NEGATIVE_MARKERS = (
    "в итоге что делать",
    "в итоге что мне делать",
    "итого ",
    "итого:",
    "сделай вывод из",
    "подведи итог по документу",
    "подведи итог статьи",
    "подведи итог отчета",
    "подведи итог отчёта",
    "summary of this article",
    "summarize this article",
    "summarize this document",
)
_PRACTICE_MARKERS = ("практик", "упражн", "шаг", "что делать", "что сделать")
_ONE_PRACTICE_MARKERS = (
    "одну короткую практику",
    "одну практику",
    "одну короткую микропрактику",
    "одну микропрактику",
    "короткую практику",
    "микропрактик",
)
_CLARIFICATION_MARKERS = ("что именно", "в каком смысле", "уточни", "clarify")
_TOPIC_SHIFT_MARKERS = ("другая тема", "другой вопрос", "сменим тему", "новая тема")
_META_FEEDBACK_MARKERS = ("бот", "система", "ответил как бот", "не как человек")
_KNOWLEDGE_MARKERS = (
    "что такое",
    "что значит",
    "в чем разница",
    "в чём разница",
    "как понять",
    "объясни",
    "расскажи",
    "какие практики",
)
_CONCRETE_SITUATION_MARKERS = (
    "сталкиваюсь",
    "несправедлив",
    "когда ",
    "в разговоре",
    "на работе",
    "дома",
    "с начальником",
    "с партнер",
    "с партнёр",
    "с мужем",
    "с женой",
    "в конфликте",
    "я опять",
    "я быстро",
    "я теряю",
    "я выхожу из себя",
)
_CONTACT_OPEN_MARKERS = ("давай знакомиться", "приятно познакомиться", "будем знакомы")
_CONTINUATION_MARKERS = ("продолжай", "давай дальше", "можешь продолжить", "расскажи дальше")
_SMALLTALK_MARKERS = ("как дела", "что нового", "как ты")
_DIRECT_KNOWLEDGE_OPENERS = (
    "расскажи о",
    "расскажи про",
    "объясни",
    "что такое",
    "что значит",
    "какие",
)
_META_WORD_PATTERNS = (
    re.compile(r"\bбот(?:а|у|ом|е)?\b", re.IGNORECASE),
    re.compile(r"\bсистем(?:а|ы|е|у|ой)\b", re.IGNORECASE),
)
_META_FEEDBACK_PHRASES = (
    "ответил как бот",
    "ответ бота",
    "ответы бота",
    "этот бот",
    "ты как бот",
    "не как человек",
)
_NO_PRACTICE_CAUSE_MARKERS = (
    "не нужна практика",
    "не нужны практики",
    "не хочу практику",
    "не хочу практики",
    "не нужна практик",
    "без практик",
    "хочу понять причину",
    "что с причиной",
    "как быть с причиной",
    "не последствия",
    "не с ее последствиями",
    "не с её последствиями",
    "почему меня так злит",
)
_CAUSE_SITUATION_ANCHORS = (
    "гнев",
    "злит",
    "ненавист",
    "врет",
    "врёт",
    "лож",
    "обман",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _extract_words(text: str) -> list[str]:
    return [part.lower() for part in _WORD_RE.findall(str(text or ""))]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def _is_explicit_one_practice_request(lowered: str) -> bool:
    if not lowered:
        return False
    if _contains_any(lowered, _ONE_PRACTICE_MARKERS):
        return True
    return (
        ("одну" in lowered or "один" in lowered or "коротк" in lowered or "микро" in lowered)
        and _contains_any(lowered, _PRACTICE_MARKERS)
    )


def _is_explicit_direct_knowledge_request(lowered: str) -> bool:
    if not lowered:
        return False
    if _contains_any(lowered, _DIRECT_KNOWLEDGE_OPENERS):
        return True
    return _contains_any(lowered, _KNOWLEDGE_MARKERS) and "?" not in lowered


def _is_offer_rejection_reply(lowered: str, words: list[str]) -> bool:
    if not _contains_any(lowered, _REJECTION_MARKERS):
        return False
    if len(words) <= 6:
        return True
    if _contains_any(lowered, _CONCRETE_SITUATION_MARKERS):
        return False
    if _contains_any(lowered, _KNOWLEDGE_MARKERS):
        return False
    if "?" in lowered:
        return False
    return False


def _contains_meta_feedback_reference(lowered: str) -> bool:
    if not lowered:
        return False
    if any(phrase in lowered for phrase in _META_FEEDBACK_PHRASES):
        return True
    return any(pattern.search(lowered) for pattern in _META_WORD_PATTERNS)


def _is_explicit_no_practice_cause_request(lowered: str) -> bool:
    if not lowered:
        return False
    if not any(marker in lowered for marker in _NO_PRACTICE_CAUSE_MARKERS):
        return False
    return any(
        marker in lowered
        for marker in (
            "причин",
            "гнев",
            "злит",
            "ненавист",
            "последств",
            "как быть",
            "почему",
        )
    )


def detect_summary_request_route_v1(user_message: str) -> dict[str, Any]:
    """Detect explicit current-conversation summary requests without stealing other intents."""

    lowered = _normalize(user_message)
    if not lowered:
        return {
            "is_summary_request": False,
            "reason": "empty_user_message",
            "confidence": 0.0,
        }

    if _contains_any(lowered, _SUMMARY_NEGATIVE_MARKERS):
        return {
            "is_summary_request": False,
            "reason": "summary_negative_marker",
            "confidence": 0.0,
        }
    if re.search(r"\bитого\s*[:=]?\s*\d", lowered):
        return {
            "is_summary_request": False,
            "reason": "arithmetic_or_total_marker",
            "confidence": 0.0,
        }
    if lowered.startswith("итог:"):
        return {
            "is_summary_request": False,
            "reason": "user_statement_not_request",
            "confidence": 0.0,
        }

    marker_hit = _contains_any(lowered, _SUMMARY_MARKERS)
    if not marker_hit:
        return {
            "is_summary_request": False,
            "reason": "no_summary_marker",
            "confidence": 0.0,
        }

    if any(marker in lowered for marker in ("цитат", "стать", "документ", "отчет", "отчёт", "pdf", "url")):
        return {
            "is_summary_request": False,
            "reason": "external_source_summary",
            "confidence": 0.0,
        }

    return {
        "is_summary_request": True,
        "reason": "explicit_current_conversation_summary_request",
        "confidence": 0.92,
        "summary_scope": "current_conversation",
        "should_not_confirm_last_offer": True,
        "no_confirmation_needed": True,
    }


def _is_short_ack(text: str) -> bool:
    words = _extract_words(text)
    return bool(words) and len(words) <= 3 and all(word in _AFFIRM_MARKERS or word in {"понял", "ясно", "ладно"} for word in words)


def build_dialogue_act_resolution_v1(
    *,
    user_message: str,
    dialogue_pragmatics: dict[str, Any] | None = None,
    last_assistant_offer: dict[str, Any] | None = None,
    knowledge_answer_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = str(user_message or "")
    lowered = _normalize(text)
    words = _extract_words(text)
    pragmatics = dict(dialogue_pragmatics or {})
    last_offer = dict(last_assistant_offer or {})
    knowledge_answer = (
        dict((knowledge_answer_guard or {}).get("knowledge_answer", {}))
        if isinstance((knowledge_answer_guard or {}).get("knowledge_answer"), dict)
        else {}
    )
    evidence: list[str] = []

    if _contains_any(lowered, _REPAIR_MARKERS) or bool(pragmatics.get("repair_user_dissatisfaction", False)):
        evidence.append("repair_feedback_markers")
        if _contains_any(lowered, _STYLE_MARKERS):
            evidence.append("style_feedback_markers")
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "repair_complaint",
            "confidence": 0.93,
            "evidence": evidence,
            "not_exact_match_rule": True,
        }

    if _contains_meta_feedback_reference(lowered):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "meta_system_feedback",
            "confidence": 0.84,
            "evidence": ["meta_feedback_markers"],
            "not_exact_match_rule": True,
        }

    summary_route = detect_summary_request_route_v1(lowered)
    if bool(summary_route.get("is_summary_request", False)):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "summary_request",
            "confidence": float(summary_route.get("confidence", 0.92) or 0.92),
            "evidence": ["summary_request_markers"],
            "not_exact_match_rule": True,
            "reason": str(summary_route.get("reason", "explicit_current_conversation_summary_request") or ""),
            "summary_scope": "current_conversation",
            "should_not_confirm_last_offer": True,
            "no_confirmation_needed": True,
        }

    if _contains_any(lowered, _TOPIC_SHIFT_MARKERS):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "topic_shift",
            "confidence": 0.85,
            "evidence": ["topic_shift_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _STYLE_MARKERS):
        evidence.append("style_preference_markers")

    if bool(last_offer.get("is_open")) and (bool(pragmatics.get("is_contextual_followup", False)) or (words and all(word in _AFFIRM_MARKERS for word in words))):
        evidence.extend(["last_assistant_offer_open", "short_affirmative_reply"])
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "confirmation_to_last_offer",
            "confidence": 0.90,
            "evidence": evidence,
            "not_exact_match_rule": True,
        }

    if bool(last_offer.get("is_open")) and _is_offer_rejection_reply(lowered, words):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "rejection_of_last_offer",
            "confidence": 0.82,
            "evidence": ["last_assistant_offer_open", "offer_rejection_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _CLOSE_ACK_MARKERS) and len(words) <= 4 and "?" not in lowered:
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "close_ack",
            "confidence": 0.92,
            "evidence": ["close_ack_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _CONTACT_OPEN_MARKERS):
        if _contains_any(lowered, _SELF_INTRO_MARKERS):
            return {
                "version": DIALOGUE_ACT_RESOLVER_VERSION,
                "dialogue_act": "self_intro",
                "confidence": 0.86,
                "evidence": ["contact_open_markers", "self_intro_markers"],
                "not_exact_match_rule": True,
            }
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "contact_open",
            "confidence": 0.82,
            "evidence": ["contact_open_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _GREETING_MARKERS):
        if _contains_any(lowered, _SELF_INTRO_MARKERS):
            return {
                "version": DIALOGUE_ACT_RESOLVER_VERSION,
                "dialogue_act": "self_intro",
                "confidence": 0.88,
                "evidence": ["greeting_plus_self_intro"],
                "not_exact_match_rule": True,
            }
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "greeting",
            "confidence": 0.85,
            "evidence": ["greeting_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _SELF_INTRO_MARKERS) and len(words) <= 12 and "?" not in lowered:
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "self_intro",
            "confidence": 0.84,
            "evidence": ["self_intro_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _SMALLTALK_MARKERS):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "smalltalk",
            "confidence": 0.70,
            "evidence": ["smalltalk_markers"],
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _CONTINUATION_MARKERS):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "continuation_request",
            "confidence": 0.82,
            "evidence": ["continuation_markers"],
            "not_exact_match_rule": True,
        }

    if _is_explicit_one_practice_request(lowered):
        evidence = ["explicit_one_practice_request"]
        if "драйвер" in lowered:
            evidence.append("driver_anchor_present")
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "practice_request",
            "confidence": 0.95,
            "evidence": evidence,
            "reason": "explicit_bounded_practice_request",
            "source": "practice_request_override",
            "not_exact_match_rule": True,
        }

    if _is_explicit_no_practice_cause_request(lowered):
        dialogue_act = (
            "concrete_situation_question"
            if any(marker in lowered for marker in _CAUSE_SITUATION_ANCHORS)
            else "knowledge_question"
        )
        evidence = ["explicit_no_practice_cause_request", "current_turn_override"]
        if any(marker in lowered for marker in _CAUSE_SITUATION_ANCHORS):
            evidence.append("cause_situation_anchor_present")
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": dialogue_act,
            "confidence": 0.94,
            "evidence": evidence,
            "reason": "explicit_no_practice_cause_understanding_request",
            "source": "explicit_current_turn_override",
            "not_exact_match_rule": True,
        }

    if _is_explicit_direct_knowledge_request(lowered):
        evidence = ["explicit_direct_knowledge_request"]
        if "без встречного вопроса" in lowered:
            evidence.append("no_counter_question_requested")
        if _contains_any(lowered, _STYLE_MARKERS):
            evidence.append("style_preference_markers")
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "knowledge_question",
            "confidence": 0.93,
            "evidence": evidence,
            "reason": "explicit_answer_first_knowledge_request",
            "source": "explicit_direct_question_override",
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _PRACTICE_MARKERS) and "?" in lowered:
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "practice_request",
            "confidence": 0.81,
            "evidence": ["practice_request_markers"],
            "reason": "question_form_practice_request",
            "source": "existing_policy",
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _CLARIFICATION_MARKERS):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "clarification_request",
            "confidence": 0.78,
            "evidence": ["clarification_markers"],
            "not_exact_match_rule": True,
        }

    if "?" in lowered:
        if _contains_any(lowered, _CONCRETE_SITUATION_MARKERS) and any(marker in lowered for marker in ("паник", "контрол")):
            return {
                "version": DIALOGUE_ACT_RESOLVER_VERSION,
                "dialogue_act": "concrete_situation_question",
                "confidence": 0.91,
                "evidence": ["situation_markers", "panic_control_support_question", "question_mark"],
                "reason": "panic_control_support_question",
                "source": "explicit_direct_question_override",
                "not_exact_match_rule": True,
            }
        if _contains_any(lowered, _CONCRETE_SITUATION_MARKERS) and not _contains_any(lowered, _KNOWLEDGE_MARKERS):
            return {
                "version": DIALOGUE_ACT_RESOLVER_VERSION,
                "dialogue_act": "concrete_situation_question",
                "confidence": 0.88,
                "evidence": ["situation_markers", "question_mark"],
                "not_exact_match_rule": True,
            }
        if bool(knowledge_answer.get("needed", False)) or _contains_any(lowered, _KNOWLEDGE_MARKERS):
            evidence.append("knowledge_question_markers")
            if _contains_any(lowered, _STYLE_MARKERS):
                evidence.append("style_preference_markers")
            return {
                "version": DIALOGUE_ACT_RESOLVER_VERSION,
                "dialogue_act": "knowledge_question",
                "confidence": 0.86,
                "evidence": evidence,
                "reason": "question_form_knowledge_request",
                "source": "existing_policy",
                "not_exact_match_rule": True,
            }
        if _contains_any(lowered, _CONCRETE_SITUATION_MARKERS):
            return {
                "version": DIALOGUE_ACT_RESOLVER_VERSION,
                "dialogue_act": "concrete_situation_question",
                "confidence": 0.86,
                "evidence": ["situation_markers", "question_mark"],
                "not_exact_match_rule": True,
            }
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "direct_question",
            "confidence": 0.80,
            "evidence": ["question_mark"],
            "reason": "generic_question_mark_route",
            "source": "fallback",
            "not_exact_match_rule": True,
        }

    if _contains_any(lowered, _CONCRETE_SITUATION_MARKERS):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "concrete_situation_question",
            "confidence": 0.77,
            "evidence": ["situation_markers"],
            "not_exact_match_rule": True,
        }

    if _is_short_ack(text):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "close_ack",
            "confidence": 0.60,
            "evidence": ["short_ack_fallback"],
            "not_exact_match_rule": True,
        }

    if bool(pragmatics.get("is_contextual_followup", False)):
        return {
            "version": DIALOGUE_ACT_RESOLVER_VERSION,
            "dialogue_act": "continuation_request",
            "confidence": 0.72,
            "evidence": ["contextual_followup"],
            "not_exact_match_rule": True,
        }

    return {
        "version": DIALOGUE_ACT_RESOLVER_VERSION,
        "dialogue_act": "unknown",
        "confidence": 0.40,
        "evidence": ["fallback_unknown"],
        "not_exact_match_rule": True,
    }


__all__ = [
    "DIALOGUE_ACT_RESOLVER_VERSION",
    "build_dialogue_act_resolution_v1",
    "detect_summary_request_route_v1",
]
