"""Config/constants for Validator Agent."""

MEDICAL_ADVICE_PATTERNS: list[str] = [
    "принимай",
    "принимайте",
    "возьми таблетку",
    "выпей",
    "дозировка",
    "препарат",
    "take this medication",
    "take the pill",
    "dosage",
    "medication dosage",
]

DIAGNOSIS_PATTERNS: list[str] = [
    "у тебя депрессия",
    "у вас депрессия",
    "у тебя тревожное расстройство",
    "у вас тревожное расстройство",
    "это биполярное",
    "это шизофрения",
    "you have depression",
    "you have anxiety disorder",
    "you are bipolar",
]

PROMISE_PATTERNS: list[str] = [
    "ты обязательно справишься",
    "всё точно будет хорошо",
    "это пройдёт гарантированно",
    "guaranteed to get better",
    "you will definitely recover",
    "it will definitely pass",
]

BOT_REVEAL_PATTERNS: list[str] = [
    "я языковая модель",
    "я искусственный интеллект",
    "я чат-бот",
    "я бот",
    "i am an ai",
    "i am a language model",
    "i'm a chatbot",
    "i'm a bot",
    "as an ai",
    "as a language model",
]

SELF_HARM_IN_ANSWER: list[str] = [
    "можно уйти из жизни",
    "суицид — это вариант",
    "suicide is an option",
    "you could end it",
]

MODE_VIOLATION_PATTERNS: dict[str, dict] = {
    "validate": {
        "patterns": ["1.", "2.", "3.", "во-первых", "во-вторых", "• ", "- "],
        "message": "validate mode: list structure detected",
    },
    "regulate": {
        "patterns": ["во-первых", "во-вторых", "1.", "2.", "3.", "список", "подумай о"],
        "message": "regulate mode: analysis structure detected",
    },
    "safe_override": {
        "patterns": ["практика", "упражнение", "попробуй сделать", "вот что", "шаг 1", "step 1"],
        "message": "safe_override: exercises detected",
    },
}

FORBIDDEN_STARTS: list[str] = [
    "я понимаю, что",
    "как специалист",
    "как психолог",
    "конечно, я понимаю",
    "i understand that",
    "as a specialist",
]

MIN_ANSWER_LENGTH: int = 20
MAX_ANSWER_LENGTH: int = 1200

SAFE_FALLBACKS: dict[str, str] = {
    "safety": (
        "Я здесь. Ты не один. Если тебе сейчас очень тяжело, можно позвонить "
        "на линию психологической помощи."
    ),
    "contract": "Я слышу тебя. Расскажи больше, если хочешь.",
    "default": "Я слышу тебя.",
}

