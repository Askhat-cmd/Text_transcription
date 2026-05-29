from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


PLANNER_DRIFT_GUARD_VERSION = "planner_drift_guard_v1"

SEVERITY_NONE = "none"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"

_SAFETY_FORBIDDEN_MARKERS = (
    "механизм",
    "прогнозирован",
    "контрол",
    "увидеть механизм",
    "разбор",
)
_SAFETY_REQUIRED_MARKERS = (
    "рядом",
    "стабилиз",
    "опора",
    "здесь-и-сейчас",
    "здесь и сейчас",
    "снизить",
    "перегруз",
)
_SHORT_SUPPORT_FORBIDDEN_MARKERS = (
    "механизм",
    "теория",
    "лекци",
    "анализ",
    "стратег",
)
_SUPPORTIVE_CONTACT_MARKERS = (
    "я рядом",
    "без давления",
    "коротко",
    "не нужно",
    "опора",
)
_PRACTICE_FORBIDDEN_MARKERS = (
    "сделай",
    "попробуй",
    "практик",
    "упражн",
    "таймер",
    "шаг 1",
)
_PRACTICE_NEGATION_PATTERNS = (
    r"\bне\s+нужно\b",
    r"\bбез\s+практик\w*",
    r"\bне\s+предлага\w+\s+практик\w*",
)
_REVOICING_PREFIXES = (
    "вы говорите",
    "ты говоришь",
    "похоже, вы хотите",
    "похоже, ты хочешь",
    "вы спрашиваете",
    "ты спрашиваешь",
)
_KNOWN_CONCEPT_REDIRECT_MARKERS = (
    "что ты вкладываешь",
    "что вы вкладываете",
    "о каком варианте",
    "что именно ты имеешь",
)

_MAX_CHARS_BY_SHAPE = {
    "short_support": 280,
    "safety_grounding": 360,
    "one_question": 360,
    "gentle_close": 220,
    "one_step": 360,
    "compact_direct": 820,
    "repair_acknowledgement": 520,
    "mechanism_explanation": 900,
    "concept_explanation_full": 5000,
    "expanded_explanation": 4200,
    "example_driven_explanation": 4200,
    "repair_and_expand": 4200,
}


@dataclass(frozen=True)
class PlannerDriftCheck:
    version: str
    enabled: bool
    status: str
    severity: str
    flags: list[str]
    shape_obedience: bool
    policy_obedience: bool
    question_policy_obedience: bool
    practice_policy_obedience: bool
    revoicing_policy_obedience: bool
    answer_length_obedience: bool
    safety_grounding_obedience: bool
    short_support_obedience: bool
    close_obedience: bool
    final_answer_chars: int
    final_answer_question_count: int
    planner_next_move: str
    planner_answer_shape: str
    planner_question_policy: str
    planner_practice_policy: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def _contains_any_regex(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(re.search(pattern, lowered) for pattern in patterns)


def _question_count(text: str) -> int:
    return str(text or "").count("?")


def _has_forbidden_practice_instruction(text: str) -> bool:
    lowered = _normalize(text)
    has_marker = _contains_any(lowered, _PRACTICE_FORBIDDEN_MARKERS)
    if not has_marker:
        return False
    if _contains_any_regex(lowered, _PRACTICE_NEGATION_PATTERNS):
        return False
    return True


def _looks_like_multistep_list(text: str) -> bool:
    lowered = str(text or "").lower()
    if re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", lowered):
        return True
    if "шаг 1" in lowered and ("шаг 2" in lowered or "шаг 3" in lowered):
        return True
    return False


def _shape_max_chars(shape: str) -> int:
    return int(_MAX_CHARS_BY_SHAPE.get(str(shape or ""), 900))


def _severity_to_status(severity: str) -> str:
    if severity == SEVERITY_NONE:
        return STATUS_OK
    if severity in {SEVERITY_LOW, SEVERITY_MEDIUM}:
        return STATUS_WARNING
    return STATUS_CRITICAL


def _build_rationale(flags: list[str], planner_next_move: str, planner_answer_shape: str) -> str:
    if not flags:
        return f"planner={planner_next_move}/{planner_answer_shape}; no drift flags"
    return f"planner={planner_next_move}/{planner_answer_shape}; flags={','.join(flags)}"


def _pick_severity(flags: list[str]) -> str:
    high_flags = {
        "safety_mechanism_drift",
        "practice_policy_forbidden_violation",
        "one_step_multistep_list",
        "known_concept_requires_user_definition",
    }
    medium_flags = {
        "question_policy_violation",
        "revoicing_policy_violation",
        "close_opened_new_loop",
        "short_support_too_long",
        "clarify_too_many_questions",
        "short_support_missing_contact",
        "clarify_missing_question",
    }
    low_flags = {
        "answer_length_warning",
    }
    if any(flag in high_flags for flag in flags):
        return SEVERITY_HIGH
    if any(flag in medium_flags for flag in flags):
        return SEVERITY_MEDIUM
    if any(flag in low_flags for flag in flags):
        return SEVERITY_LOW
    return SEVERITY_NONE


def build_planner_drift_check(
    *,
    response_planner: dict[str, Any] | None,
    final_answer: str,
    enabled: bool = True,
) -> PlannerDriftCheck:
    planner = dict(response_planner or {})
    answer_text = str(final_answer or "").strip()
    lowered = _normalize(answer_text)

    planner_next_move = str(planner.get("next_move", "") or "")
    planner_answer_shape = str(planner.get("answer_shape", "") or "")
    planner_question_policy = str(planner.get("question_policy", "none") or "none")
    planner_practice_policy = str(planner.get("practice_policy", "forbidden") or "forbidden")
    planner_revoicing_policy = str(planner.get("revoicing_policy", "suppressed") or "suppressed")
    source_signals = dict(planner.get("source_signals", {})) if isinstance(planner.get("source_signals"), dict) else {}
    mvp_profile = str(source_signals.get("dialogue_profile", "") or "") == "mvp_free_dialogue"
    expansion_requested = bool(source_signals.get("expansion_requested", False))
    expanded_shape = planner_answer_shape in {
        "concept_explanation_full",
        "expanded_explanation",
        "example_driven_explanation",
        "repair_and_expand",
    }

    question_count = _question_count(answer_text)
    max_chars = _shape_max_chars(planner_answer_shape)
    answer_length_obedience = len(answer_text) <= max_chars
    if mvp_profile and expansion_requested and expanded_shape:
        answer_length_obedience = len(answer_text) <= 6000

    question_policy_obedience = True
    if planner_question_policy == "none":
        question_policy_obedience = question_count == 0

    practice_policy_obedience = True
    if planner_practice_policy == "forbidden":
        practice_policy_obedience = not _has_forbidden_practice_instruction(answer_text)

    revoicing_policy_obedience = True
    if planner_revoicing_policy == "suppressed":
        revoicing_policy_obedience = not lowered.startswith(_REVOICING_PREFIXES)

    safety_grounding_obedience = True
    if planner_answer_shape == "safety_grounding" or planner_next_move == "stabilize_safety":
        safety_grounding_obedience = (
            not _contains_any(lowered, _SAFETY_FORBIDDEN_MARKERS)
            and _contains_any(lowered, _SAFETY_REQUIRED_MARKERS)
            and question_count == 0
        )

    short_support_obedience = True
    if planner_answer_shape == "short_support" or planner_next_move == "give_short_support":
        short_support_obedience = (
            len(answer_text) <= _shape_max_chars("short_support")
            and question_count == 0
            and not _contains_any(lowered, _SHORT_SUPPORT_FORBIDDEN_MARKERS)
            and not _has_forbidden_practice_instruction(answer_text)
            and _contains_any(lowered, _SUPPORTIVE_CONTACT_MARKERS)
        )

    close_obedience = True
    if planner_answer_shape == "gentle_close" or planner_next_move == "close_gently":
        close_obedience = question_count == 0 and not _has_forbidden_practice_instruction(answer_text)

    shape_obedience = True
    if planner_answer_shape == "one_question":
        shape_obedience = question_count <= 1 and not _has_forbidden_practice_instruction(answer_text)
    elif planner_answer_shape == "one_step":
        shape_obedience = not _looks_like_multistep_list(answer_text)
    elif planner_answer_shape == "short_support":
        shape_obedience = short_support_obedience
    elif planner_answer_shape == "safety_grounding":
        shape_obedience = safety_grounding_obedience
    elif planner_answer_shape == "gentle_close":
        shape_obedience = close_obedience

    flags: list[str] = []
    if not answer_length_obedience:
        flags.append("answer_length_warning")

    if not question_policy_obedience:
        flags.append("question_policy_violation")

    if not practice_policy_obedience:
        flags.append("practice_policy_forbidden_violation")

    if not revoicing_policy_obedience:
        flags.append("revoicing_policy_violation")

    if (planner_answer_shape == "short_support" or planner_next_move == "give_short_support") and len(answer_text) > _shape_max_chars("short_support"):
        flags.append("short_support_too_long")
    if (
        planner_answer_shape == "short_support" or planner_next_move == "give_short_support"
    ) and not _contains_any(lowered, _SUPPORTIVE_CONTACT_MARKERS):
        flags.append("short_support_missing_contact")

    if (planner_answer_shape == "gentle_close" or planner_next_move == "close_gently") and not close_obedience:
        flags.append("close_opened_new_loop")

    if (planner_answer_shape == "safety_grounding" or planner_next_move == "stabilize_safety") and not safety_grounding_obedience:
        if _contains_any(lowered, _SAFETY_FORBIDDEN_MARKERS):
            flags.append("safety_mechanism_drift")
        else:
            flags.append("safety_grounding_missing_contact")

    if (planner_answer_shape == "one_step" or planner_next_move == "give_direct_step") and _looks_like_multistep_list(answer_text):
        flags.append("one_step_multistep_list")

    if (planner_next_move == "answer_known_concept") and (
        question_count > 0 or _contains_any(lowered, _KNOWN_CONCEPT_REDIRECT_MARKERS)
    ):
        flags.append("known_concept_requires_user_definition")

    if (planner_answer_shape == "one_question" or planner_next_move == "clarify_one_point") and question_count > 1:
        flags.append("clarify_too_many_questions")
    if (planner_answer_shape == "one_question" or planner_next_move == "clarify_one_point") and question_count == 0:
        flags.append("clarify_missing_question")

    policy_obedience = question_policy_obedience and practice_policy_obedience and revoicing_policy_obedience
    severity = _pick_severity(flags)
    status = _severity_to_status(severity)

    return PlannerDriftCheck(
        version=PLANNER_DRIFT_GUARD_VERSION,
        enabled=bool(enabled),
        status=status,
        severity=severity,
        flags=flags,
        shape_obedience=bool(shape_obedience),
        policy_obedience=bool(policy_obedience),
        question_policy_obedience=bool(question_policy_obedience),
        practice_policy_obedience=bool(practice_policy_obedience),
        revoicing_policy_obedience=bool(revoicing_policy_obedience),
        answer_length_obedience=bool(answer_length_obedience),
        safety_grounding_obedience=bool(safety_grounding_obedience),
        short_support_obedience=bool(short_support_obedience),
        close_obedience=bool(close_obedience),
        final_answer_chars=len(answer_text),
        final_answer_question_count=question_count,
        planner_next_move=planner_next_move,
        planner_answer_shape=planner_answer_shape,
        planner_question_policy=planner_question_policy,
        planner_practice_policy=planner_practice_policy,
        rationale=_build_rationale(flags=flags, planner_next_move=planner_next_move, planner_answer_shape=planner_answer_shape),
    )
