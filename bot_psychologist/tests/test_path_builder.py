from bot_agent.config import config
from bot_agent.response import ResponseGenerator


class _DummyAnswerer:
    def __init__(self) -> None:
        self.last_call = {}

    def build_system_prompt(self) -> str:
        return "BASE_PROMPT"

    def generate_answer(
        self,
        user_question,
        blocks,
        conversation_history=None,
        model=None,
        temperature=None,
        max_tokens=None,
        **kwargs,
    ):
        self.last_call = {
            "system_prompt": self.build_system_prompt(),
            "question": user_question,
            "max_tokens": max_tokens,
        }
        return {"answer": "ok", "error": None}


class _RestrictiveAnswerer(_DummyAnswerer):
    def build_system_prompt(self) -> str:
        return (
            "BASE_PROMPT\n"
            "Отвечай кратко.\n"
            "Не перегружай пользователя.\n"
            "Задай один точный вопрос."
        )


def _snapshot():
    return {
        "FREE_CONVERSATION_MODE": config.FREE_CONVERSATION_MODE,
        "PROMPT_MODE_OVERRIDES_SD": config.PROMPT_MODE_OVERRIDES_SD,
    }


def _restore(values):
    for key, value in values.items():
        setattr(config, key, value)


def test_free_mode_no_restricting_directives() -> None:
    snapshot = _snapshot()
    try:
        config.FREE_CONVERSATION_MODE = True
        answerer = _RestrictiveAnswerer()
        generator = ResponseGenerator(answerer=answerer)
        generator.generate(
            "Что такое самоосознание?",
            blocks=[],
            mode="THINKING",
            user_level_adapter=object(),
            sd_level="GREEN",
        )
        prompt = answerer.last_call["system_prompt"].lower()
        assert "кратко" not in prompt
        assert "не перегружай" not in prompt
        assert "один точный вопрос" not in prompt
        assert "не ограничивай длину" in prompt
    finally:
        _restore(snapshot)


def test_mode_directive_is_composed_in_system_prompt() -> None:
    snapshot = _snapshot()
    try:
        config.FREE_CONVERSATION_MODE = False
        config.PROMPT_MODE_OVERRIDES_SD = True
        answerer = _DummyAnswerer()
        generator = ResponseGenerator(answerer=answerer)
        generator.generate(
            "Разбери мой паттерн",
            blocks=[],
            mode="THINKING",
            confidence_level="medium",
            sd_level="GREEN",
        )
        prompt = answerer.last_call["system_prompt"]
        mode_preview = "MODE DIRECTIVE"
        assert mode_preview in prompt
        assert prompt.index(mode_preview) > prompt.index("BASE_PROMPT")
    finally:
        _restore(snapshot)


def test_conflicts_with_mode_detection() -> None:
    generator = ResponseGenerator(answerer=_DummyAnswerer())
    assert generator._conflicts_with_mode("Отвечай кратко и не перегружай", "THINKING") is True
    assert generator._conflicts_with_mode("Отвечай кратко и не перегружай", "PRESENCE") is False
    assert generator._conflicts_with_mode("Будь внимателен к деталям", "THINKING") is False
