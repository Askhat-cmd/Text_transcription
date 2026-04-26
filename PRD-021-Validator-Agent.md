# PRD-021 · Validator Agent
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-021  
**Агент:** Validator  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Целевая директория:** `bot_psychologist/bot_agent/multiagent/agents/`  
**Дата создания:** 2026-04-26  
**Зависимости:** PRD-017 ✅ · PRD-018 ✅ · PRD-019 ✅ · PRD-020 ✅  

---

## 1. Контекст и назначение

### 1.1 Что уже сделано

Пайплайн работает полностью за исключением одного зазора: Writer генерирует ответ, но никто его не проверяет перед отправкой пользователю.

```
[State Analyzer] → StateSnapshot
      ↓
[Thread Manager] → ThreadState
      ↓
[Memory+Retrieval] → MemoryBundle
      ↓
[Writer / NEO] → draft_answer (строка)
      ↓
[Validator]        ← PRD-021 (ВЫ ЗДЕСЬ)
      ↓
final_answer → Telegram
```

### 1.2 Что делает Validator

Validator получает черновик Writer-а и проверяет его на три группы рисков:

**Группа 1 — Safety (жёсткие правила, блокирующие):**
- Ответ содержит суицидальные триггеры или вредоносный контент
- Ответ даёт медицинские советы ("принимай препарат X")
- Ответ обещает выздоровление или конкретный результат
- Ответ содержит диагностику ("у тебя депрессия")

**Группа 2 — Contract violations (детерминированные, блокирующие):**
- Нарушены `must_avoid` из ThreadState
- В ответе упоминается, что бот — ИИ или бот
- Ответ явно нарушает `response_mode` (например, в validate есть список советов)

**Группа 3 — Quality flags (предупреждения, не блокирующие):**
- Ответ слишком короткий (< 20 символов)
- Ответ слишком длинный (> 1200 символов)
- Ответ начинается с запрещённых фраз

### 1.3 Архитектурный принцип

**Validator полностью детерминированный — без LLM-вызовов.**

Причины:
- LLM-проверка LLM-ответа — дорого и медленно
- Ключевые риски (safety + contract) хорошо ловятся правилами
- Validator должен работать даже если API недоступен
- Latency пайплайна критична для психологического бота

Если Validator заблокировал ответ — Orchestrator берёт статический safe fallback. Ответ пользователю не задерживается.

### 1.4 Место в пайплайне

```
writer_agent.write(contract) → draft_answer: str
      ↓
validator_agent.validate(draft_answer, contract) → ValidationResult
      ↓
if result.is_blocked:
    final_answer = result.safe_replacement
else:
    final_answer = draft_answer (+ возможные quality_flags в debug)
```

---

## 2. Новый контракт `ValidationResult`

```python
# multiagent/contracts/validation_result.py — новый файл

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    """Result of Validator Agent check on Writer draft."""

    # Заблокирован ли ответ (safety или contract violation)
    is_blocked: bool

    # Причина блокировки (если is_blocked=True)
    block_reason: Optional[str] = None

    # Категория блокировки
    block_category: Optional[str] = None  # "safety" | "contract" | None

    # Замена при блокировке (безопасный текст)
    safe_replacement: Optional[str] = None

    # Некритичные предупреждения (для debug)
    quality_flags: list[str] = field(default_factory=list)

    # Прошёл ли ответ без замечаний
    @property
    def is_clean(self) -> bool:
        return not self.is_blocked and not self.quality_flags
```

---

## 3. Детерминированные правила

### 3.1 Safety keywords (блокирующие)

```python
_MEDICAL_ADVICE_PATTERNS = [
    "принимай", "принимайте", "возьми таблетку", "выпей", "дозировка",
    "take this medication", "take the pill", "dosage",
]

_DIAGNOSIS_PATTERNS = [
    "у тебя депрессия", "у вас депрессия", "у тебя тревожное расстройство",
    "это биполярное", "это шизофрения", "you have depression",
    "you have anxiety disorder", "you are bipolar",
]

_PROMISE_PATTERNS = [
    "ты обязательно справишься", "всё точно будет хорошо", "это пройдёт гарантированно",
    "guaranteed to get better", "you will definitely recover",
]

_BOT_REVEAL_PATTERNS = [
    "я языковая модель", "я искусственный интеллект", "я чат-бот", "я бот",
    "i am an ai", "i am a language model", "i'm a chatbot", "i'm a bot",
    "as an ai", "as a language model",
]

_SELF_HARM_IN_ANSWER = [
    "можно уйти из жизни", "суицид — это вариант",
    "suicide is an option", "you could end it",
]
```

### 3.2 Правила проверки must_avoid

`must_avoid` из ThreadState содержит список строк — тем/элементов которые нельзя упоминать.  
Validator проверяет каждый элемент как подстроку (case-insensitive) в ответе.

Пример:
```python
must_avoid = ["советы", "практики", "список"]
answer = "Вот тебе практика на сегодня..."
# → найдено "практика" → contract violation
```

### 3.3 Режимные ограничения (response_mode violations)

```python
_MODE_VIOLATIONS = {
    "validate": {
        "patterns": ["1.", "2.", "3.", "во-первых", "во-вторых", "• ", "- "],
        "message": "validate mode should not contain lists",
    },
    "regulate": {
        "patterns": ["во-первых", "во-вторых", "1.", "2.", "3.", "список", "подумай о"],
        "message": "regulate mode should not contain analysis",
    },
    "safe_override": {
        "patterns": ["практика", "упражнение", "попробуй сделать", "вот что", "шаг 1", "step 1"],
        "message": "safe_override should not contain exercises",
    },
}
```

### 3.4 Quality flags (не блокирующие)

```python
_FORBIDDEN_STARTS = [
    "я понимаю, что",
    "как специалист",
    "как психолог",
    "конечно, я понимаю",
    "i understand that",
    "as a specialist",
]

_MIN_LENGTH = 20
_MAX_LENGTH = 1200
```

---

## 4. Структура файлов

```
bot_psychologist/
└── bot_agent/
    └── multiagent/
        ├── agents/
        │   ├── __init__.py                    ← добавить validator_agent
        │   ├── writer_agent.py                ← не трогать ✅
        │   ├── validator_agent.py             ← ОСНОВНОЙ ФАЙЛ PRD-021  [новый]
        │   └── validator_agent_config.py      ← все слова/паттерны изолированно [новый]
        ├── orchestrator.py                    ← добавить validator_agent.validate()
        └── contracts/
            └── validation_result.py           ← новый контракт [новый]

tests/
└── multiagent/
    ├── fixtures/
    │   └── validator_agent_fixtures.json      ← [новый]
    └── test_validator_agent.py                ← [новый]
```

---

## 5. validator_agent_config.py

```python
# multiagent/agents/validator_agent_config.py

"""Все паттерны и правила Validator Agent. Изолированы от логики."""

MEDICAL_ADVICE_PATTERNS: list[str] = [
    "принимай", "принимайте", "возьми таблетку", "выпей",
    "дозировка", "препарат", "take this medication",
    "take the pill", "dosage", "medication dosage",
]

DIAGNOSIS_PATTERNS: list[str] = [
    "у тебя депрессия", "у вас депрессия",
    "у тебя тревожное расстройство", "у вас тревожное расстройство",
    "это биполярное", "это шизофрения",
    "you have depression", "you have anxiety disorder",
    "you are bipolar",
]

PROMISE_PATTERNS: list[str] = [
    "ты обязательно справишься", "всё точно будет хорошо",
    "это пройдёт гарантированно", "guaranteed to get better",
    "you will definitely recover", "it will definitely pass",
]

BOT_REVEAL_PATTERNS: list[str] = [
    "я языковая модель", "я искусственный интеллект",
    "я чат-бот", "я бот", "i am an ai", "i am a language model",
    "i'm a chatbot", "i'm a bot", "as an ai", "as a language model",
]

SELF_HARM_IN_ANSWER: list[str] = [
    "можно уйти из жизни", "суицид — это вариант",
    "suicide is an option", "you could end it",
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
    "safety": "Я здесь. Ты не один. Если тебе сейчас очень тяжело, можно позвонить на линию психологической помощи.",
    "contract": "Я слышу тебя. Расскажи больше, если хочешь.",
    "default": "Я слышу тебя.",
}
```

---

## 6. Реализация validator_agent.py

```python
# multiagent/agents/validator_agent.py

from __future__ import annotations

import logging
from typing import Optional

from ..contracts.validation_result import ValidationResult
from ..contracts.writer_contract import WriterContract
from .validator_agent_config import (
    BOT_REVEAL_PATTERNS,
    DIAGNOSIS_PATTERNS,
    FORBIDDEN_STARTS,
    MAX_ANSWER_LENGTH,
    MEDICAL_ADVICE_PATTERNS,
    MIN_ANSWER_LENGTH,
    MODE_VIOLATION_PATTERNS,
    PROMISE_PATTERNS,
    SAFE_FALLBACKS,
    SELF_HARM_IN_ANSWER,
)

logger = logging.getLogger(__name__)


def _contains_any(text: str, patterns: list[str]) -> Optional[str]:
    """Returns first matching pattern or None."""
    lowered = text.lower()
    for p in patterns:
        if p.lower() in lowered:
            return p
    return None


class ValidatorAgent:
    """
    Deterministic safety and contract validator for Writer drafts.
    No LLM calls. Always returns ValidationResult.
    """

    def validate(self, draft: str, contract: WriterContract) -> ValidationResult:
        try:
            text = (draft or "").strip()

            # 1. Safety checks (blocking)
            safety_hit = self._check_safety(text)
            if safety_hit:
                logger.warning("[VALIDATOR] safety block: %s", safety_hit)
                return ValidationResult(
                    is_blocked=True,
                    block_reason=safety_hit,
                    block_category="safety",
                    safe_replacement=SAFE_FALLBACKS["safety"],
                )

            # 2. Contract checks (blocking)
            contract_hit = self._check_contract(text, contract)
            if contract_hit:
                logger.warning("[VALIDATOR] contract block: %s", contract_hit)
                return ValidationResult(
                    is_blocked=True,
                    block_reason=contract_hit,
                    block_category="contract",
                    safe_replacement=SAFE_FALLBACKS["contract"],
                )

            # 3. Quality flags (non-blocking)
            quality_flags = self._check_quality(text, contract)

            return ValidationResult(
                is_blocked=False,
                quality_flags=quality_flags,
            )

        except Exception as exc:
            logger.error("[VALIDATOR] validate failed: %s", exc, exc_info=True)
            return ValidationResult(is_blocked=False, quality_flags=["validator_error"])

    def _check_safety(self, text: str) -> Optional[str]:
        hit = _contains_any(text, SELF_HARM_IN_ANSWER)
        if hit:
            return f"self_harm_in_answer: {hit}"
        hit = _contains_any(text, MEDICAL_ADVICE_PATTERNS)
        if hit:
            return f"medical_advice: {hit}"
        hit = _contains_any(text, DIAGNOSIS_PATTERNS)
        if hit:
            return f"diagnosis: {hit}"
        hit = _contains_any(text, PROMISE_PATTERNS)
        if hit:
            return f"guarantee_promise: {hit}"
        hit = _contains_any(text, BOT_REVEAL_PATTERNS)
        if hit:
            return f"bot_reveal: {hit}"
        return None

    def _check_contract(self, text: str, contract: WriterContract) -> Optional[str]:
        # must_avoid
        must_avoid = contract.thread_state.must_avoid or []
        for item in must_avoid:
            if item and item.lower() in text.lower():
                return f"must_avoid_violated: {item}"

        # response_mode violations
        mode = contract.thread_state.response_mode
        if mode in MODE_VIOLATION_PATTERNS:
            spec = MODE_VIOLATION_PATTERNS[mode]
            hit = _contains_any(text, spec["patterns"])
            if hit:
                return spec["message"]

        return None

    @staticmethod
    def _check_quality(text: str, contract: WriterContract) -> list[str]:
        flags = []
        if len(text) < MIN_ANSWER_LENGTH:
            flags.append(f"too_short: {len(text)} chars")
        if len(text) > MAX_ANSWER_LENGTH:
            flags.append(f"too_long: {len(text)} chars")
        lowered = text.lower()
        for phrase in FORBIDDEN_STARTS:
            if lowered.startswith(phrase.lower()):
                flags.append(f"forbidden_start: {phrase}")
                break
        return flags


validator_agent = ValidatorAgent()
```

---

## 7. Обновление Orchestrator

```python
# multiagent/orchestrator.py — добавить Validator после Writer

from .agents.validator_agent import validator_agent
from .contracts.validation_result import ValidationResult

# ... внутри run():

# 5. Writer / NEO
writer_contract = WriterContract(
    user_message=query,
    thread_state=updated_thread,
    memory_bundle=memory_bundle,
)
draft_answer = await writer_agent.write(writer_contract)

# 6. Validator  ← PRD-021
validation_result = validator_agent.validate(draft_answer, writer_contract)
if validation_result.is_blocked:
    final_answer = validation_result.safe_replacement or draft_answer
else:
    final_answer = draft_answer

# 7. Async update памяти
asyncio.create_task(memory_retrieval_agent.update(
    user_id=user_id,
    user_message=query,
    assistant_response=final_answer,
    thread_state=updated_thread,
))

return {
    "status": "ok",
    "answer": final_answer,
    ...
    "debug": {
        ...
        "validator_blocked": validation_result.is_blocked,
        "validator_block_reason": validation_result.block_reason,
        "validator_quality_flags": validation_result.quality_flags,
    },
}
```

---

## 8. Обновление `agents/__init__.py`

```python
from .state_analyzer import state_analyzer_agent
from .thread_manager import thread_manager_agent
from .memory_retrieval import memory_retrieval_agent
from .writer_agent import writer_agent
from .validator_agent import validator_agent

__all__ = [
    "state_analyzer_agent",
    "thread_manager_agent",
    "memory_retrieval_agent",
    "writer_agent",
    "validator_agent",
]
```

---

## 9. Fixtures для тестов

```json
[
  {
    "id": "VA-F01",
    "draft": "Я слышу тебя. Расскажи больше.",
    "response_mode": "validate",
    "must_avoid": [],
    "safety_active": false,
    "expected_blocked": false
  },
  {
    "id": "VA-F02",
    "draft": "Принимай витамин D каждый день — это поможет.",
    "response_mode": "reflect",
    "must_avoid": [],
    "safety_active": false,
    "expected_blocked": true,
    "expected_category": "safety"
  },
  {
    "id": "VA-F03",
    "draft": "Я слышу тебя. Вот упражнение на дыхание.",
    "response_mode": "safe_override",
    "must_avoid": [],
    "safety_active": true,
    "expected_blocked": true,
    "expected_category": "contract"
  },
  {
    "id": "VA-F04",
    "draft": "Расскажи мне про свою практику медитации.",
    "response_mode": "validate",
    "must_avoid": ["практика"],
    "safety_active": false,
    "expected_blocked": true,
    "expected_category": "contract"
  },
  {
    "id": "VA-F05",
    "draft": "Я понимаю, что это тяжело.",
    "response_mode": "reflect",
    "must_avoid": [],
    "safety_active": false,
    "expected_blocked": false,
    "expected_quality_flags": ["forbidden_start"]
  },
  {
    "id": "VA-F06",
    "draft": "ок",
    "response_mode": "validate",
    "must_avoid": [],
    "safety_active": false,
    "expected_blocked": false,
    "expected_quality_flags": ["too_short"]
  }
]
```

---

## 10. Тесты

### 10.1 test_validator_agent.py — полный список

```
VA-01  RESULT_FIELDS — ValidationResult содержит все поля: is_blocked, block_reason, block_category, safe_replacement, quality_flags
VA-02  IS_CLEAN_PROPERTY — is_clean=True когда не заблокирован и нет quality_flags
VA-03  CLEAN_DRAFT — чистый нейтральный ответ → is_blocked=False, quality_flags=[]
VA-04  SAFETY_MEDICAL — "принимай таблетки" → blocked, category=safety
VA-05  SAFETY_DIAGNOSIS — "у тебя депрессия" → blocked, category=safety
VA-06  SAFETY_PROMISE — "ты обязательно справишься" → blocked, category=safety
VA-07  SAFETY_BOT_REVEAL — "я языковая модель" → blocked, category=safety
VA-08  SAFETY_SELF_HARM — "суицид — это вариант" → blocked, category=safety
VA-09  SAFETY_EN_MEDICAL — "take this medication" → blocked, category=safety
VA-10  SAFETY_EN_BOT_REVEAL — "i am an ai" → blocked, category=safety
VA-11  CONTRACT_MUST_AVOID — слово из must_avoid в ответе → blocked, category=contract
VA-12  CONTRACT_MUST_AVOID_CASE — must_avoid нечувствителен к регистру
VA-13  CONTRACT_MUST_AVOID_EMPTY — пустой must_avoid → не блокирует
VA-14  CONTRACT_MODE_VALIDATE_LIST — режим validate + нумерованный список → blocked
VA-15  CONTRACT_MODE_REGULATE_ANALYSIS — regulate + "подумай о" → blocked
VA-16  CONTRACT_MODE_SAFE_EXERCISE — safe_override + "упражнение" → blocked
VA-17  CONTRACT_MODE_NO_VIOLATION — mode=reflect → нет mode-violations
VA-18  QUALITY_TOO_SHORT — ответ < 20 символов → quality_flag too_short
VA-19  QUALITY_TOO_LONG — ответ > 1200 символов → quality_flag too_long
VA-20  QUALITY_FORBIDDEN_START_RU — начинается с "я понимаю, что" → quality_flag
VA-21  QUALITY_FORBIDDEN_START_EN — начинается с "i understand that" → quality_flag
VA-22  QUALITY_NOT_BLOCKING — quality_flags не делают is_blocked=True
VA-23  SAFETY_BEFORE_CONTRACT — safety проверяется раньше contract (приоритет)
VA-24  SAFE_REPLACEMENT_SAFETY — при safety block: safe_replacement из SAFE_FALLBACKS["safety"]
VA-25  SAFE_REPLACEMENT_CONTRACT — при contract block: safe_replacement из SAFE_FALLBACKS["contract"]
VA-26  NO_LLM_CALLS — validate() не делает LLM-вызовов (синхронный метод)
VA-27  EXCEPTION_GRACEFUL — при внутренней ошибке: возвращает is_blocked=False + quality_flag
VA-28  ORCHESTRATOR_CALLS_VALIDATOR — orchestrator.run() вызывает validator_agent.validate()
VA-29  ORCHESTRATOR_BLOCKED_USES_REPLACEMENT — при is_blocked=True: answer = safe_replacement
VA-30  ORCHESTRATOR_DEBUG_FIELDS — debug содержит validator_blocked, block_reason, quality_flags
```

### 10.2 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ — все 105 тестов PRD-017..020 зелёные
REG-02  validator_agent.py — синхронный метод validate(), без async
REG-03  contracts/writer_contract.py не изменён
REG-04  contracts/memory_bundle.py не изменён
REG-05  MULTIAGENT_ENABLED=False — классический путь не затронут
```

---

## 11. Acceptance Criteria (Definition of Done)

PRD-021 завершён когда:

- [ ] `contracts/validation_result.py` создан с `ValidationResult` dataclass
- [ ] `agents/validator_agent_config.py` создан с изолированными паттернами
- [ ] `agents/validator_agent.py` создан (синхронный, без LLM)
- [ ] `agents/__init__.py` экспортирует `validator_agent`
- [ ] `orchestrator.py` вызывает `validator_agent.validate()` после Writer
- [ ] Debug-поля в orchestrator: `validator_blocked`, `validator_block_reason`, `validator_quality_flags`
- [ ] Все 30 тестов VA зелёные
- [ ] Все тесты PRD-017..020 зелёные (REG-01)
- [ ] `pytest tests/multiagent/ -q` → 135+ passed

---

## 12. Что НЕ входит в PRD-021

| Что | PRD |
|---|---|
| Запись ответа в conversation_memory | PRD-022 |
| Полный E2E тест пайплайна | PRD-022 |
| LLM-based validation | Не планируется |
| Архивирование legacy | PRD-023 |
| Telegram Adapter | PRD-024 |

---

## 13. Важные замечания для IDE-агента

1. **Validator — синхронный метод `validate()`, не async.** Это нарочно: он детерминированный и быстрый, нет смысла делать coroutine.
2. **Порядок проверок:** safety → contract → quality. Только первый hit (safety) блокирует с safety-заменой, второй — contract-заменой.
3. **`must_avoid` проверяется как подстрока.** Если в must_avoid = ["практика"], а в ответе "практики" — это должно находиться (case-insensitive).
4. **quality_flags не блокируют.** Они идут в debug для мониторинга, не заменяют ответ.
5. **При ошибке внутри Validator** — возвращать `ValidationResult(is_blocked=False, quality_flags=["validator_error"])`. Никогда не бросать исключение.
6. **В `orchestrator.py`** — `validator_agent.validate()` вызывается синхронно (не await), т.к. метод не async.

---

*Конец PRD-021 · Validator Agent*  
*Следующий документ: PRD-022 · Orchestrator + E2E (полный пайплайн + memory writeback)*
