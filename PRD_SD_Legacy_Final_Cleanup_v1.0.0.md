# PRD: SD Legacy Final Cleanup
### Neo MindBot v0.12.x → v0.13.0
**Версия:** 1.0.0  
**Дата:** 09.04.2026  
**Статус:** FINAL — готово к исполнению IDE-агентом  
**Приоритет:** CRITICAL  
**Scope:** только SD-очистка — промты, routing, память и прочее вне этого PRD

---

## 1. Контекст и цель

### 1.1 Предыстория

Neo MindBot прошёл три итерации архитектуры:
1. **Graph-era** — бот на графовой БД с единственным автором
2. **SD-era** — классификация пользователей по Спиральной динамике Эрла Грейвза, 6 уровней (red/blue/orange/green/yellow/purple), адаптация промтов и retrieval под уровень
3. **Neo-era (текущая)** — отказ от SD, единая база знаний для всех пользователей, классификация по нейро-состоянию (HYPER/WINDOW/HYPO) и функции запроса (6 типов)

### 1.2 Текущее состояние

**Конфигурационный слой — SD полностью отключён:**
- `SD_CLASSIFIER_ENABLED: off`
- `LEGACY_PIPELINE_ENABLED: off`
- `DISABLE_USER_LEVEL_ADAPTER: on`
- `USER_LEVEL_ADAPTER_ENABLED: off`
- `PRE_ROUTING_ENABLED: off`

**Кодовый слой — SD-артефакты живы в трёх местах:**

На каждый запрос в логах фиксируется:
```
INFO  botagent.stateclassifier        curious  0.85
INFO  botagent.answeradaptive         SD runtime disabled in Neo v11 pipeline
WARNING botagent.diagnosticsclassifier DIAG state legacy term curious → window
```

В LLM-полотне (Diagnostics context блок DIAG_ALGORITHM) рендерится:
```
Runtime context:
- curious / contemplative          ← legacy термин SD-эпохи
- intermediate                     ← legacy уровень SD
- NONE . SD- .                     ← SD-директива с битой кириллицей
```

### 1.3 Цель PRD

Полностью устранить все SD-артефакты из **кодового слоя** тремя хирургическими правками:

| # | Файл | Тип правки |
|---|---|---|
| FIX-1 | `bot_agent/state_classifier.py` | Замена выходного словаря состояний |
| FIX-2 | `bot_agent/answer_adaptive.py` | Удаление SD-полей из context builder |
| FIX-3 | `bot_agent/diagnostics_classifier.py` | Удаление mapper-заплатки |

### 1.4 Definition of Done

Задача считается завершённой когда:
- [ ] В логах **отсутствуют** строки с `legacy term`, `curious`, `confused`, `committed`, `SD runtime disabled`, `intermediate`, `NONE . SD-`
- [ ] В LLM-полотне **отсутствуют** поля `Уровень развития (СД)`, `intermediate`, SD-директива
- [ ] `state_classifier.py` возвращает только термины из множества `{hyper, window, hypo}` + `{discharge, understand, solution, validation, explore, contact}`
- [ ] Все 18 тест-кейсов проходят GREEN
- [ ] Diagnostics Contract в админке (`hyper|window|hypo` / `discharge|understand|solution|validation|explore|contact`) соответствует реальному выводу классификатора

---

## 2. Технические требования

### 2.1 FIX-1 — `state_classifier.py`: замена выходного словаря

#### Текущее поведение (БЫЛО)

Классификатор возвращает legacy-термины SD-эпохи:
```python
# Текущий выходной словарь (УДАЛИТЬ/ЗАМЕНИТЬ):
LEGACY_STATES = [
    "curious",       # → маппится в window
    "confused",      # → маппится в window/hypo  
    "committed",     # → маппится в window
    "anxious",       # → маппится в hyper
    "frustrated",    # → маппится в hyper
    "contemplative", # → маппится в window
    "overwhelmed",   # → маппится в hypo
    "disengaged",    # → маппится в hypo
    # ... и другие legacy-термины
]
```

#### Требуемое поведение (СТАЛО)

Классификатор должен возвращать структуру из двух независимых осей:

```python
# ТРЕБУЕМЫЙ выходной тип:
@dataclass
class StateClassifierResult:
    nervous_system_state: Literal["hyper", "window", "hypo"]
    request_function: Literal[
        "discharge", "understand", "solution", 
        "validation", "explore", "contact"
    ]
    confidence: float  # 0.0 – 1.0
    raw_label: str     # исходный текст для логов (не используется в промтах)
```

#### Таблица маппинга для миграции LLM-классификатора

Если классификатор использует LLM (gpt-4o-mini) — обновить system prompt классификатора:

**Текущий промт классификатора (УДАЛИТЬ термины):**
```
Classify user state as one of: curious, confused, committed, anxious, 
frustrated, contemplative, overwhelmed, disengaged
```

**Новый промт классификатора (ЗАМЕНИТЬ на):**
```
Classify the user message along TWO independent axes:

AXIS 1 - Nervous System State (choose ONE):
- hyper: activation, urgency, frustration, anger, anxiety, overwhelm
- window: calm curiosity, reflection, openness, engagement, clarity
- hypo: withdrawal, numbness, shutdown, disengagement, flatness

AXIS 2 - Request Function (choose ONE):
- discharge: user needs to express/vent, not receive advice
- understand: user wants explanation or meaning
- solution: user wants concrete steps or action plan
- validation: user seeks acknowledgment or confirmation
- explore: user wants to think out loud, open-ended inquiry
- contact: user needs human connection, feels alone

Return JSON: {"nervous_system_state": "...", "request_function": "...", "confidence": 0.0-1.0}
```

#### Обновление логирования

```python
# БЫЛО:
logger.info(f"{state_label} {confidence:.2f}")

# СТАЛО:
logger.info(
    f"STATE nss={result.nervous_system_state} "
    f"fn={result.request_function} "
    f"conf={result.confidence:.2f}"
)
```

#### Обновление fast_detector

`fast_state_detector.py` (если существует) — заменить ключи:
```python
# БЫЛО:
FAST_STATE_INDICATORS = {
    "fast_state_curious": [...],
    "fast_state_committed": [...],
}

# СТАЛО:
FAST_STATE_INDICATORS = {
    "fast_state_hyper": [...],     # триггерные слова: "всё плохо", "я в панике"...
    "fast_state_hypo": [...],      # триггерные слова: "не хочу", "устал", "пофиг"...
    "fast_state_window": [...],    # триггерные слова: "интересно", "думаю что"...
    # request_function быстрый детектор не определяет — только LLM
}
```

---

### 2.2 FIX-2 — `answer_adaptive.py`: удаление SD-полей из context builder

#### Локализация

Найти метод, собирающий блок `Runtime context` для инжекции в `DIAG_ALGORITHM`. Ориентир — строки, которые производят следующий текст в LLM-полотне:

```
Runtime context:
- curious / contemplative          ← УДАЛИТЬ эту строку
- intermediate                     ← УДАЛИТЬ эту строку  
- NONE . SD- .                     ← УДАЛИТЬ эту строку
```

Также найти и удалить строку с кодировкой:
```
РЕКОМЕНДАЦИЯ ПО ОТВЕТУ: Р Р°Р·РІРёРІР°Р№ РёРЅС‚РµСЂРµСЃ   ← УДАЛИТЬ (битая кириллица SD-директивы)
```

#### Конкретные строки для удаления (паттерны поиска)

```python
# ПАТТЕРН 1 — legacy state label:
f"- {state_label}"           # где state_label = "curious", "confused" etc.
f"- {user_state}"            # любое поле передающее old-style состояние

# ПАТТЕРН 2 — SD уровень:
f"- {sd_level}"              # "intermediate", "beginner", "advanced" 
f"- Уровень развития (СД): {sd_level}"
f"- sd_level: {sd_level}"
f"- user_level: {user_level}"

# ПАТТЕРН 3 — SD директива (может быть закодирована):
"SD-"                        # любая строка содержащая "SD-"
"Адаптируй стиль ответа к уровню СД"
"РЕКОМЕНДАЦИЯ ПО ОТВЕТУ"    # если это SD-директива
```

#### Требуемый вид Runtime context после FIX-2

```
Diagnostics context:
- interaction_mode: {mode}
- nervous_system_state: {hyper|window|hypo}     ← ТОЛЬКО это поле состояния
- request_function: {function}                  ← ТОЛЬКО это поле функции
- core_theme: {theme}
- resolved_route: {route}
- llm_mode: {mode}
```

**Никаких SD-полей. Никаких legacy-терминов. Никакой кириллицы с SD-директивами.**

#### Обновление encoding

Если в context builder есть строки с русским текстом, добавить явный `encoding="utf-8"` при сборке строк или использовать только ASCII-ключи для технических полей.

---

### 2.3 FIX-3 — `diagnostics_classifier.py`: удаление mapper-заплатки

#### Текущая логика (УДАЛИТЬ)

```python
# Текущий mapper (ВЕСЬ ЭТОТ КОД УДАЛИТЬ):
LEGACY_TO_NEO_MAP = {
    "curious":       "window",
    "confused":      "window",  
    "committed":     "window",
    "anxious":       "hyper",
    "frustrated":    "hyper",
    "overwhelmed":   "hypo",
    "disengaged":    "hypo",
    # ...
}

def map_legacy_state(state: str) -> str:
    if state in LEGACY_TO_NEO_MAP:
        logger.warning(f"DIAG state legacy term {state} → {LEGACY_TO_NEO_MAP[state]}")
        return LEGACY_TO_NEO_MAP[state]
    return state
```

#### Требуемое поведение после FIX-3

После выполнения FIX-1 классификатор уже отдаёт правильные термины. `diagnostics_classifier.py` либо:

**Вариант A (предпочтительный) — удалить mapper, оставить валидацию:**
```python
VALID_NSS = {"hyper", "window", "hypo"}
VALID_REQUEST_FN = {"discharge", "understand", "solution", "validation", "explore", "contact"}

def validate_state(result: StateClassifierResult) -> StateClassifierResult:
    """Валидирует что state_classifier вернул корректные термины."""
    if result.nervous_system_state not in VALID_NSS:
        logger.error(f"DIAG invalid nss={result.nervous_system_state}, fallback to window")
        result.nervous_system_state = "window"
    if result.request_function not in VALID_REQUEST_FN:
        logger.error(f"DIAG invalid fn={result.request_function}, fallback to understand")
        result.request_function = "understand"
    return result
    # НЕТ WARNING о "legacy term" — только ERROR при реальной невалидности
```

**Вариант B — полностью удалить файл**, если он не выполняет других функций. Тогда валидацию добавить inline в `answer_adaptive.py`.

---

## 3. Порядок выполнения

```
FIX-1 (state_classifier.py)
    ↓
FIX-2 (answer_adaptive.py)        ← зависит от FIX-1: нужны новые поля
    ↓  
FIX-3 (diagnostics_classifier.py) ← зависит от FIX-1: mapper больше не нужен
    ↓
Тесты (все 18 кейсов)
    ↓
Smoke test (живой запрос + проверка логов)
```

> **ВАЖНО:** Не выполнять FIX-2 и FIX-3 до завершения FIX-1.  
> Не запускать тесты до завершения всех трёх FIX.

---

## 4. Тестовый пакет

### 4.1 Настройка тестового окружения

```python
# tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock
from bot_agent.state_classifier import StateClassifier, StateClassifierResult

@pytest.fixture
def classifier():
    return StateClassifier()

@pytest.fixture  
def mock_llm_response():
    """Мок LLM для unit-тестов без реального API-вызова."""
    def _mock(nss: str, fn: str, conf: float = 0.85):
        return {"nervous_system_state": nss, "request_function": fn, "confidence": conf}
    return _mock
```

---

### T1 — StateClassifier: выходной словарь (6 тестов)

```python
# tests/test_state_classifier.py
"""
ЦЕЛЬ: Убедиться что state_classifier НИКОГДА не возвращает legacy-термины.
"""

import pytest
from bot_agent.state_classifier import StateClassifier, StateClassifierResult

VALID_NSS = {"hyper", "window", "hypo"}
VALID_REQUEST_FN = {"discharge", "understand", "solution", "validation", "explore", "contact"}
LEGACY_TERMS = {"curious", "confused", "committed", "anxious", "frustrated", 
                "contemplative", "overwhelmed", "disengaged", "intermediate",
                "beginner", "advanced", "red", "blue", "orange", "green", "yellow", "purple"}


class TestStateClassifierOutputVocabulary:

    def test_T1_01_result_type_is_dataclass(self, classifier):
        """T1-01: Возвращаемый тип — StateClassifierResult с двумя осями."""
        result = classifier.classify("Мне интересно как это работает")
        assert isinstance(result, StateClassifierResult), (
            f"Ожидался StateClassifierResult, получен {type(result)}"
        )
        assert hasattr(result, "nervous_system_state")
        assert hasattr(result, "request_function")
        assert hasattr(result, "confidence")

    def test_T1_02_nss_only_valid_terms(self, classifier):
        """T1-02: nervous_system_state ТОЛЬКО из {hyper, window, hypo}."""
        test_inputs = [
            "Я в панике, всё рушится!",
            "Мне интересно, расскажи подробнее",
            "Мне всё равно, не хочу ничего",
        ]
        for text in test_inputs:
            result = classifier.classify(text)
            assert result.nervous_system_state in VALID_NSS, (
                f"Недопустимый nss='{result.nervous_system_state}' для input='{text}'. "
                f"Допустимо только: {VALID_NSS}"
            )

    def test_T1_03_request_function_only_valid_terms(self, classifier):
        """T1-03: request_function ТОЛЬКО из 6 допустимых значений."""
        test_inputs = [
            "Просто хочу выговориться",
            "Объясни мне что такое тревога",
            "Что мне конкретно делать?",
            "Я правильно понимаю?",
            "Хочу подумать вслух",
            "Мне одиноко",
        ]
        for text in test_inputs:
            result = classifier.classify(text)
            assert result.request_function in VALID_REQUEST_FN, (
                f"Недопустимый fn='{result.request_function}' для input='{text}'. "
                f"Допустимо только: {VALID_REQUEST_FN}"
            )

    def test_T1_04_no_legacy_terms_in_result(self, classifier):
        """T1-04: Результат НЕ содержит ни одного legacy-термина."""
        result = classifier.classify("Любой текст пользователя")
        result_values = {result.nervous_system_state, result.request_function}
        legacy_found = result_values & LEGACY_TERMS
        assert not legacy_found, (
            f"Найдены legacy-термины в результате классификатора: {legacy_found}. "
            f"Эти термины остались от SD-эпохи и должны быть удалены."
        )

    def test_T1_05_confidence_is_float_in_range(self, classifier):
        """T1-05: Confidence — float в диапазоне [0.0, 1.0]."""
        result = classifier.classify("Тестовый запрос")
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0, (
            f"Confidence={result.confidence} вне диапазона [0.0, 1.0]"
        )

    def test_T1_06_no_sd_level_field(self, classifier):
        """T1-06: В результате отсутствует поле sd_level или user_level."""
        result = classifier.classify("Тестовый запрос")
        assert not hasattr(result, "sd_level"), "Найдено legacy-поле sd_level в результате"
        assert not hasattr(result, "user_level"), "Найдено legacy-поле user_level в результате"
        assert not hasattr(result, "spiral_level"), "Найдено legacy-поле spiral_level"
```

---

### T2 — StateClassifier: матрица состояний 3×6 (18 кейсов)

```python
# tests/test_state_classifier_matrix.py
"""
ЦЕЛЬ: Проверить что классификатор корректно определяет
все комбинации нейро-состояния и функции запроса.
Тест не проверяет точность LLM — проверяет что формат корректен
и что возвращаемые значения принадлежат допустимым множествам.
"""

import pytest
from bot_agent.state_classifier import StateClassifier

VALID_NSS = {"hyper", "window", "hypo"}
VALID_FN = {"discharge", "understand", "solution", "validation", "explore", "contact"}

# (input_text, expected_nss, expected_fn, description)
STATE_MATRIX_CASES = [
    # HYPER × 6 функций
    ("Всё бесит! Просто хочу выговориться!", "hyper", "discharge", "HYPER+discharge"),
    ("Я в тревоге, почему так происходит?", "hyper", "understand", "HYPER+understand"),
    ("Паника! Скажи что делать прямо сейчас!", "hyper", "solution", "HYPER+solution"),
    ("Я правильно сделал что ушёл?", "hyper", "validation", "HYPER+validation"),
    ("Со мной что-то не так? Хочу разобраться", "hyper", "explore", "HYPER+explore"),
    ("Мне страшно и я один с этим", "hyper", "contact", "HYPER+contact"),
    # WINDOW × 6 функций
    ("Хочу рассказать как прошёл день", "window", "discharge", "WINDOW+discharge"),
    ("Объясни мне механизм тревоги", "window", "understand", "WINDOW+understand"),
    ("Какие есть техники для фокуса?", "window", "solution", "WINDOW+solution"),
    ("Мне кажется я правильно понимаю ACT?", "window", "validation", "WINDOW+validation"),
    ("Интересно, как связаны тело и эмоции?", "window", "explore", "WINDOW+explore"),
    ("Хочется просто поговорить", "window", "contact", "WINDOW+contact"),
    # HYPO × 6 функций
    ("Устал. Не знаю зачем вообще рассказываю", "hypo", "discharge", "HYPO+discharge"),
    ("Почему мне ничего не интересно?", "hypo", "understand", "HYPO+understand"),
    ("Что можно сделать когда нет сил?", "hypo", "solution", "HYPO+solution"),
    ("Это нормально — чувствовать пустоту?", "hypo", "validation", "HYPO+validation"),
    ("Не понимаю что со мной происходит", "hypo", "explore", "HYPO+explore"),
    ("Мне одиноко и тяжело", "hypo", "contact", "HYPO+contact"),
]


@pytest.mark.parametrize("text,expected_nss,expected_fn,desc", STATE_MATRIX_CASES)
def test_T2_state_matrix(text, expected_nss, expected_fn, desc):
    """
    T2-xx: Матрица 3×6 — формат результата корректен для каждой комбинации.

    NOTE: Тест проверяет ФОРМАТ, не точность LLM.
    Если LLM ошибается в классификации — это приемлемо на данном этапе.
    Если результат вне допустимых множеств — это FAIL теста.
    """
    classifier = StateClassifier()
    result = classifier.classify(text)

    assert result.nervous_system_state in VALID_NSS, (
        f"[{desc}] nss='{result.nervous_system_state}' недопустимо. "
        f"Ожидалось из {VALID_NSS}"
    )
    assert result.request_function in VALID_FN, (
        f"[{desc}] fn='{result.request_function}' недопустимо. "
        f"Ожидалось из {VALID_FN}"
    )
```

---

### T3 — answer_adaptive.py: SD-поля не попадают в промт (4 теста)

```python
# tests/test_no_sd_in_prompt.py
"""
ЦЕЛЬ: Убедиться что answer_adaptive.py НЕ инжектирует SD-артефакты в LLM-промт.
Это прямая проверка FIX-2.
"""

import pytest
import re
from unittest.mock import patch, MagicMock
from bot_agent.answer_adaptive import AnswerAdaptive

SD_ARTIFACTS = [
    r"Уровень развития \(СД\)",
    r"sd_level",
    r"user_level",
    r"intermediate",          # SD уровень
    r"beginner",              # SD уровень
    r"advanced",              # SD уровень
    r"SD-",                   # SD-директива
    r"РЕКОМЕНДАЦИЯ ПО ОТВЕТУ", # SD-директива с кириллицей
    r"curious",               # legacy state term
    r"confused",              # legacy state term
    r"committed",             # legacy state term
    r"Адаптируй стиль.*СД",   # SD инструкция
]

@pytest.fixture
def adaptive_with_mocked_llm():
    """AnswerAdaptive с замоканным LLM — для проверки промта без реального вызова."""
    captured_prompt = {}

    def mock_llm_call(messages, **kwargs):
        # Сохраняем промт для проверки
        captured_prompt["system"] = " ".join(
            m["content"] for m in messages if m["role"] == "system"
        )
        captured_prompt["full"] = str(messages)
        return MagicMock(choices=[MagicMock(message=MagicMock(content="Test response"))])

    with patch("bot_agent.llm_answerer.openai.chat.completions.create", mock_llm_call):
        adapter = AnswerAdaptive()
        adapter._captured_prompt = captured_prompt
        yield adapter


class TestNoSDInPrompt:

    def test_T3_01_no_sd_level_in_diag_context(self, adaptive_with_mocked_llm):
        """T3-01: Блок DIAG_ALGORITHM не содержит sd_level / user_level."""
        adaptive_with_mocked_llm.process("Тестовый запрос", user_id="test_user")
        prompt = adaptive_with_mocked_llm._captured_prompt.get("full", "")

        for pattern in [r"sd_level", r"user_level", r"Уровень развития \(СД\)"]:
            assert not re.search(pattern, prompt, re.IGNORECASE), (
                f"Найден SD-артефакт по паттерну '{pattern}' в промте LLM. "
                f"FIX-2 не выполнен корректно."
            )

    def test_T3_02_no_legacy_state_in_runtime_context(self, adaptive_with_mocked_llm):
        """T3-02: Runtime context не содержит legacy state terms."""
        adaptive_with_mocked_llm.process("Мне интересно", user_id="test_user")
        prompt = adaptive_with_mocked_llm._captured_prompt.get("full", "")

        for term in ["curious", "confused", "committed", "anxious", "frustrated"]:
            # Проверяем что термин не в секции Runtime context (может быть в тексте пользователя)
            runtime_section = re.search(r"Runtime context:(.+?)(?=TITLE|\Z)", prompt, re.DOTALL)
            if runtime_section:
                assert term not in runtime_section.group(1), (
                    f"Legacy term '{term}' найден в секции Runtime context промта."
                )

    def test_T3_03_no_sd_directive_in_prompt(self, adaptive_with_mocked_llm):
        """T3-03: В промте отсутствует SD-директива (включая битую кириллицу)."""
        adaptive_with_mocked_llm.process("Любой запрос", user_id="test_user")
        prompt = adaptive_with_mocked_llm._captured_prompt.get("full", "")

        assert "SD-" not in prompt, (
            "Найдена SD-директива 'SD-' в промте LLM."
        )
        assert "РЕКОМЕНДАЦИЯ ПО ОТВЕТУ" not in prompt, (
            "Найдена битая SD-директива 'РЕКОМЕНДАЦИЯ ПО ОТВЕТУ' в промте."
        )

    def test_T3_04_diag_context_has_correct_fields(self, adaptive_with_mocked_llm):
        """T3-04: Diagnostics context содержит правильные поля Neo-архитектуры."""
        adaptive_with_mocked_llm.process("Тестовый запрос", user_id="test_user")
        prompt = adaptive_with_mocked_llm._captured_prompt.get("full", "")

        required_fields = [
            "nervous_system_state",
            "request_function",
            "resolved_route",
        ]
        for field in required_fields:
            assert field in prompt, (
                f"Обязательное поле '{field}' отсутствует в Diagnostics context промта."
            )
```

---

### T4 — DiagnosticsClassifier: нет legacy WARNING (3 теста)

```python
# tests/test_diagnostics_classifier.py
"""
ЦЕЛЬ: Убедиться что diagnostics_classifier НЕ бросает WARNING о legacy terms.
Это прямая проверка FIX-3.
"""

import pytest
import logging
from bot_agent.diagnostics_classifier import DiagnosticsClassifier
from bot_agent.state_classifier import StateClassifierResult


class TestDiagnosticsClassifierNoLegacy:

    def test_T4_01_no_warning_for_valid_neo_terms(self, caplog):
        """T4-01: При корректных Neo-терминах нет WARNING в логах."""
        classifier = DiagnosticsClassifier()

        valid_result = StateClassifierResult(
            nervous_system_state="window",
            request_function="understand",
            confidence=0.85
        )

        with caplog.at_level(logging.WARNING, logger="bot_agent.diagnosticsclassifier"):
            classifier.validate(valid_result)

        legacy_warnings = [r for r in caplog.records if "legacy term" in r.message.lower()]
        assert not legacy_warnings, (
            f"Найдены WARNING о legacy terms при валидных Neo-терминах: "
            f"{[r.message for r in legacy_warnings]}"
        )

    def test_T4_02_no_legacy_mapper_attribute(self):
        """T4-02: В DiagnosticsClassifier нет атрибута LEGACY_TO_NEO_MAP."""
        classifier = DiagnosticsClassifier()
        assert not hasattr(classifier, "LEGACY_TO_NEO_MAP"), (
            "Найден атрибут LEGACY_TO_NEO_MAP — mapper-заплатка не удалена (FIX-3)."
        )
        assert not hasattr(classifier, "legacy_map"), (
            "Найден атрибут legacy_map — mapper-заплатка не удалена (FIX-3)."
        )

    def test_T4_03_error_logged_for_truly_invalid_state(self, caplog):
        """T4-03: ERROR логируется только при реально невалидном термине (не legacy — а мусор)."""
        classifier = DiagnosticsClassifier()

        invalid_result = StateClassifierResult(
            nervous_system_state="totally_invalid_garbage",
            request_function="understand",
            confidence=0.5
        )

        with caplog.at_level(logging.ERROR, logger="bot_agent.diagnosticsclassifier"):
            result = classifier.validate(invalid_result)

        # Должен быть ERROR (не WARNING) и fallback на "window"
        error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_logs, "Ожидался ERROR лог при невалидном nss, но он не появился"
        assert result.nervous_system_state == "window", (
            f"Ожидался fallback на 'window', получен '{result.nervous_system_state}'"
        )
```

---

### T5 — Grep-тест: SD-артефакты отсутствуют в кодовой базе (1 тест)

```python
# tests/test_no_sd_legacy_grep.py
"""
ЦЕЛЬ: Статический анализ — убедиться что SD-артефакты физически отсутствуют
в рабочих Python-файлах (не в архиве).
"""

import os
import re
import pytest
from pathlib import Path

# Корень бота — настроить под реальный путь проекта
BOT_ROOT = Path(__file__).parent.parent / "bot_agent"

# Файлы и директории, исключённые из проверки (архив, тесты, конфиг)
EXCLUDED_PATHS = {
    "archive", "legacy", "_archive", "test_", "conftest",
    "feature_flags.py",   # флаги намеренно содержат имена legacy-компонентов
    "README", ".md",
}

# Паттерны, которые НЕ должны встречаться в рабочем коде
SD_CODE_PATTERNS = [
    (r'"curious"',          "Legacy state term 'curious'"),
    (r'"confused"',         "Legacy state term 'confused'"),
    (r'"committed"',        "Legacy state term 'committed'"),
    (r'sd_level\s*=',       "SD level assignment"),
    (r'user_level\s*=',     "User level assignment (SD legacy)"),
    (r'LEGACY_TO_NEO_MAP',  "Legacy mapper dict"),
    (r'spiral_level',       "Spiral dynamics level field"),
    (r'sd_classifier',      "SD classifier reference (should be disabled, not referenced)"),
    (r'"intermediate"',     "SD level term 'intermediate'"),
    (r'СД\)',               "Russian SD reference in code"),
    (r'prompt_sd_',         "SD prompt file reference"),
]


def get_python_files_to_check():
    """Возвращает список .py файлов в bot_agent, исключая архив и тесты."""
    files = []
    for f in BOT_ROOT.rglob("*.py"):
        skip = any(excl in str(f) for excl in EXCLUDED_PATHS)
        if not skip:
            files.append(f)
    return files


@pytest.mark.parametrize("pattern,description", SD_CODE_PATTERNS)
def test_T5_no_sd_artifacts_in_source(pattern, description):
    """T5: Статический grep — SD-артефакты отсутствуют в рабочем коде."""
    files_to_check = get_python_files_to_check()
    violations = []

    for filepath in files_to_check:
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    violations.append(f"{filepath.name}:{i}: {line.strip()}")
        except Exception:
            pass

    assert not violations, (
        f"SD-артефакт [{description}] найден в {len(violations)} местах:\n" +
        "\n".join(violations[:10])  # показать первые 10
    )
```

---

### T6 — Интеграционный Smoke Test (2 теста)

```python
# tests/test_smoke_sd_clean.py
"""
ЦЕЛЬ: End-to-end проверка что живой запрос к боту
не производит SD-артефактов ни в логах, ни в промте.

ТРЕБУЕТ: запущенный сервер на localhost:8000
ЗАПУСК: pytest tests/test_smoke_sd_clean.py -m smoke
"""

import pytest
import requests
import re

BASE_URL = "http://localhost:8000"
TEST_USER = "test_sd_cleanup_user"
TEST_QUERY = "Мне интересно как справляться с тревогой"

SD_LOG_PATTERNS = [
    "legacy term",
    "SD runtime disabled",
    "curious",
    "confused", 
    "committed",
    "intermediate",
    "NONE . SD-",
]


@pytest.mark.smoke
def test_T6_01_api_response_no_sd_in_session_debug():
    """
    T6-01: Debug trace ответа не содержит SD-артефактов.
    Проверяет LLM-payload через debug endpoint.
    """
    # Создать сессию
    session_resp = requests.post(
        f"{BASE_URL}/api/v1/users/{TEST_USER}/sessions",
        headers={"X-API-Key": "dev-key-00"},
        json={}
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json().get("session_id")

    # Отправить запрос
    query_resp = requests.post(
        f"{BASE_URL}/api/v1/questions/adaptive-stream",
        headers={"X-API-Key": "dev-key-00"},
        json={"query": TEST_QUERY, "user_key": TEST_USER},
    )
    assert query_resp.status_code == 200

    # Получить LLM payload из debug endpoint
    if session_id:
        payload_resp = requests.get(
            f"{BASE_URL}/api/debug/session/{session_id}/llm-payload",
            headers={"X-API-Key": "dev-key-00"}
        )
        if payload_resp.status_code == 200:
            payload_text = str(payload_resp.json())

            for pattern in ["sd_level", "Уровень развития (СД)", "SD-", "curious", "intermediate"]:
                assert pattern not in payload_text, (
                    f"SD-артефакт '{pattern}' найден в LLM payload debug trace."
                )


@pytest.mark.smoke  
def test_T6_02_classifier_output_in_neo_taxonomy():
    """
    T6-02: Diagnostics endpoint подтверждает Neo-таксономию в реальном трейсе.
    """
    session_resp = requests.post(
        f"{BASE_URL}/api/v1/users/{TEST_USER}/sessions",
        headers={"X-API-Key": "dev-key-00"},
        json={}
    )
    session_id = session_resp.json().get("session_id", "")

    requests.post(
        f"{BASE_URL}/api/v1/questions/adaptive-stream",
        headers={"X-API-Key": "dev-key-00"},
        json={"query": TEST_QUERY, "user_key": TEST_USER},
    )

    if session_id:
        traces_resp = requests.get(
            f"{BASE_URL}/api/debug/session/{session_id}/traces",
            headers={"X-API-Key": "dev-key-00"}
        )
        if traces_resp.status_code == 200:
            trace = str(traces_resp.json())

            # Должны быть Neo-термины
            neo_nss_found = any(t in trace for t in ["hyper", "window", "hypo"])
            assert neo_nss_found, (
                "Ни один Neo NSS термин (hyper/window/hypo) не найден в trace. "
                "Классификатор возможно всё ещё возвращает legacy-термины."
            )

            # НЕ должно быть legacy-терминов
            for legacy in ["curious", "confused", "committed"]:
                assert legacy not in trace, (
                    f"Legacy-термин '{legacy}' найден в debug trace после FIX-1."
                )
```

---

## 5. Запуск тестов

### 5.1 Полный прогон (unit + grep)

```bash
# Установить зависимости для тестов (если не установлены)
pip install pytest pytest-asyncio

# Запустить все тесты SD-очистки
pytest tests/test_state_classifier.py \
       tests/test_state_classifier_matrix.py \
       tests/test_no_sd_in_prompt.py \
       tests/test_diagnostics_classifier.py \
       tests/test_no_sd_legacy_grep.py \
       -v --tb=short 2>&1 | tee sd_cleanup_test_report.txt
```

### 5.2 Только grep (быстрая проверка после правок)

```bash
pytest tests/test_no_sd_legacy_grep.py -v
```

### 5.3 Smoke test (требует запущенный сервер)

```bash
pytest tests/test_smoke_sd_clean.py -m smoke -v
```

### 5.4 Ожидаемый результат

```
============================== test session starts ==============================
tests/test_state_classifier.py::TestStateClassifierOutputVocabulary::test_T1_01 PASSED
tests/test_state_classifier.py::TestStateClassifierOutputVocabulary::test_T1_02 PASSED
tests/test_state_classifier.py::TestStateClassifierOutputVocabulary::test_T1_03 PASSED
tests/test_state_classifier.py::TestStateClassifierOutputVocabulary::test_T1_04 PASSED
tests/test_state_classifier.py::TestStateClassifierOutputVocabulary::test_T1_05 PASSED
tests/test_state_classifier.py::TestStateClassifierOutputVocabulary::test_T1_06 PASSED
tests/test_state_classifier_matrix.py::test_T2_state_matrix[HYPER+discharge] PASSED
... (все 18 матричных кейсов)
tests/test_no_sd_in_prompt.py::TestNoSDInPrompt::test_T3_01 PASSED
tests/test_no_sd_in_prompt.py::TestNoSDInPrompt::test_T3_02 PASSED
tests/test_no_sd_in_prompt.py::TestNoSDInPrompt::test_T3_03 PASSED
tests/test_no_sd_in_prompt.py::TestNoSDInPrompt::test_T3_04 PASSED
tests/test_diagnostics_classifier.py::TestDiagnosticsClassifierNoLegacy::test_T4_01 PASSED
tests/test_diagnostics_classifier.py::TestDiagnosticsClassifierNoLegacy::test_T4_02 PASSED
tests/test_diagnostics_classifier.py::TestDiagnosticsClassifierNoLegacy::test_T4_03 PASSED
tests/test_no_sd_legacy_grep.py::test_T5[...] PASSED (×9 паттернов)
======================== 37 passed in X.Xs ================================
```

---

## 6. Критерии приёмки

### 6.1 Чеклист до merge

```
[ ] FIX-1: state_classifier.py возвращает StateClassifierResult с nss + request_function
[ ] FIX-1: Промт LLM-классификатора обновлён на двухосевую таксономию  
[ ] FIX-1: Логирование обновлено (nss=window fn=understand conf=0.85)
[ ] FIX-1: fast_detector.py обновлён (hyper/window/hypo вместо curious/committed)
[ ] FIX-2: Из context builder удалены: state_label, sd_level, SD-директива
[ ] FIX-2: Diagnostics context содержит: nervous_system_state, request_function
[ ] FIX-2: Отсутствует битая кириллица в промте
[ ] FIX-3: LEGACY_TO_NEO_MAP удалён
[ ] FIX-3: WARNING "DIAG state legacy term" не появляется в логах
[ ] TESTS: Все 37 тестов GREEN
[ ] SMOKE: Живой запрос не содержит SD-артефактов в LLM-полотне
[ ] LOGS:  Строки "SD runtime disabled", "legacy term" отсутствуют
```

### 6.2 Проверка логов после деплоя (30-секундный smoke)

Запустить бот, отправить один тестовый запрос, проверить `bot.log`:

**БЫЛО (до фикса):**
```
INFO  botagent.stateclassifier        curious  0.85          ← legacy
INFO  botagent.answeradaptive         SD runtime disabled     ← лишнее
WARNING botagent.diagnosticsclassifier DIAG state legacy term  ← должно исчезнуть
```

**СТАЛО (после фикса):**
```
INFO  botagent.stateclassifier  STATE nss=window fn=understand conf=0.85
INFO  botagent.answeradaptive   ROUTING nss=window fn=understand route=reflect
```

Никакого `SD`, `legacy`, `curious`, `curious`, `intermediate`. Тема закрыта.

---

## 7. Что НЕ входит в этот PRD

Следующие задачи намеренно исключены и выполняются в отдельной итерации:

- Отстройка промтов (CORE_IDENTITY, REFLECTIVE_METHOD, A_SEASONAL)
- Оптимизация Voyage TOP-K override
- Снижение latency (FAST_PATH)  
- Summary interval tuning
- Migration script для исторических данных в SQLite

---

*PRD v1.0.0 — SD Legacy Final Cleanup — Neo MindBot v0.12.x → v0.13.0*
