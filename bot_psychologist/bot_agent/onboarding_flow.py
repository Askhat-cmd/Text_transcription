"""Phase 8 helpers: onboarding, informational branch, and correction protocol."""

from __future__ import annotations

from dataclasses import dataclass
import re


_START_COMMAND_RE = re.compile(r"^\s*/?(start|старт)\s*$", flags=re.IGNORECASE)
_USER_CORRECTION_RE = re.compile(
    r"(нет,\s*не\s*то|ты\s+меня\s+не\s+понял|я\s+не\s+об\s+этом|не\s+об\s+этом|это\s+не\s+то|не\s+совсем\s+так)",
    flags=re.IGNORECASE,
)
_INFORMATIONAL_RE = re.compile(
    r"(что\s+такое|объясни|расскажи|в\s+чем|как\s+работает|термин|концепц|система)",
    flags=re.IGNORECASE,
)
_PERSONAL_RE = re.compile(
    r"(\bя\b|\bмне\b|\bменя\b|\bмой\b|чувств|боюсь|тревог|стыд|вина|со\s+мной)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class Phase8Signals:
    first_turn: bool
    start_command: bool
    user_correction: bool
    informational_intent: bool
    personal_disclosure: bool
    mixed_query: bool

    def as_dict(self) -> dict:
        return {
            "first_turn": self.first_turn,
            "start_command": self.start_command,
            "user_correction": self.user_correction,
            "informational_intent": self.informational_intent,
            "personal_disclosure": self.personal_disclosure,
            "mixed_query": self.mixed_query,
        }


def detect_phase8_signals(query: str, turns_count: int) -> Phase8Signals:
    text = (query or "").strip()
    informational_intent = bool(_INFORMATIONAL_RE.search(text))
    personal_disclosure = bool(_PERSONAL_RE.search(text))
    return Phase8Signals(
        first_turn=turns_count <= 0,
        start_command=bool(_START_COMMAND_RE.match(text)),
        user_correction=bool(_USER_CORRECTION_RE.search(text)),
        informational_intent=informational_intent,
        personal_disclosure=personal_disclosure,
        mixed_query=informational_intent and personal_disclosure,
    )


def build_start_message() -> str:
    return (
        "Привет. Я Neo MindBot.\n"
        "Помогаю прояснить внутренний процесс: что с тобой происходит и какой шаг сделать дальше.\n"
        "Напиши, с чем ты пришёл(а) сейчас — коротко, в 1-2 фразах."
    )


def build_first_turn_instruction() -> str:
    return (
        "FIRST_TURN_POLICY:\n"
        "- Не перегружай пользователя схемами и длинными списками.\n"
        "- Дай ясный вход: 1 короткое отражение + 1 рабочий вопрос.\n"
        "- Не превращай ответ в бюрократический intake."
    )


def build_mixed_query_instruction() -> str:
    return (
        "MIXED_QUERY_POLICY:\n"
        "- Сначала кратко объясни концепт (2-4 предложения).\n"
        "- Затем мягко свяжи объяснение с текущей ситуацией пользователя.\n"
        "- Заверши одним вопросом-мостом в coaching."
    )


def build_user_correction_instruction() -> str:
    return (
        "USER_CORRECTION_PROTOCOL:\n"
        "- Признай, что мог промахнуться в интерпретации.\n"
        "- Не спорь и не защищай прошлый ответ.\n"
        "- Снизь уверенность и перекалибруйся по последнему сообщению.\n"
        "- Дай обновлённый ответ и 1 уточняющий вопрос."
    )


def build_informational_guardrail_instruction() -> str:
    return (
        "INFORMATIONAL_GUARDRAIL:\n"
        "- Не запускай глубокий reflective/coaching поток без явного запроса.\n"
        "- Не навязывай практику.\n"
        "- Объясняй по существу, с конкретикой и без псевдодиагностики."
    )
