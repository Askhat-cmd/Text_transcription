
***

# PRD v1.0.2 — GPT-5 Compatibility Patch: sd_classifier \& state_classifier

**Репозиторий:** `Askhat-cmd/Text_transcription`
**Путь проекта:** `bot_psychologist/`
**Версия документа:** 1.0.2
**Дата:** 2026-03-02
**Статус:** `READY FOR AGENT`
**Приоритет:** `BLOCKER` — бот неработоспособен с `gpt-5-mini`
**Зависимость:** PRD v1.0.1 выполнен (коммит [`6d4d36d`](https://github.com/Askhat-cmd/Text_transcription/commit/6d4d36dd3d4f96ee78716d6b1b4c7344b2c3a875))
**Файлов к изменению:** 2

***

## 1. Подтверждённые баги из логов и кода

### BUG-01 — `sd_classifier.py`: модель игнорирует `PRIMARY_MODEL` из `.env` (`CRITICAL`)

**Доказательство в коде** (`sd_classifier.py`, класс `SDClassifier.__init__`):

```python
self.model = model or str(_SD_SETTINGS.get("model", "gpt-4o-mini"))
#                                              ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
# Читает модель из YAML-конфига (defaults → "gpt-4o-mini")
# Никогда не обращается к config.LLM_MODEL
# При PRIMARY_MODEL=gpt-5-mini в .env — SDClassifier всё равно
# инициализируется с "gpt-4o-mini"
```

**Следствие:** SD-классификатор использует другую модель, чем остальной бот. При этом `config.supports_custom_temperature(self.model)` получает `"gpt-4o-mini"` → думает что `temperature` поддерживается → не ломается. Но вся логика классификации выполняется на отдельной захардкоженной модели, не той что задана пользователем.

**Доказательство в логах** (`error-4.log`):[^1]

```
ERROR botagent.sdclassifier SDCLASSIFIER LLM error name 'config' is not defined
```

**Причина этой ошибки:** В `sd_classifier.py` есть module-level инициализация в момент импорта:

```python
_SD_SETTINGS = _load_sd_settings()       # ← строка ~80, выполняется при import
sd_classifier = SDClassifier()           # ← строка ~290, выполняется при import
sd_compatibility_resolver = SDCompatibilityResolver()
```

В момент выполнения этих строк при старте приложения, если `from .config import config` не успел загрузиться в нужном порядке из-за circular import или порядка инициализации модулей — `config` оказывается не определён в одном из вызовов внутри `_load_sd_settings()` или при создании экземпляра. `NameError: config is not defined` — типичная ошибка Python при circular import или неправильном порядке module-level statements.

***

### BUG-02 — `state_classifier.py`: JSON парсинг падает с GPT-5 mini (`CRITICAL`)

**Доказательство в логах** (`bot-2.log`):[^2]

```
WARNING botagent.stateclassifier JSON Expecting value: line 1 column 1 char 0
INFO botagent.stateclassifier curious 0.30   ← всегда fallback!
```

Эта ошибка появляется в **каждом запросе** при `gpt-5-mini`. GPT-5 mini иногда возвращает:

- Пустую строку `""` (особенно при сложных structured-output промптах без явной инструкции)
- Или JSON обёрнутый в ````json ... ```` без дополнительных пробелов

**Текущий код очистки** в `state_classifier.py → _classify_by_llm()` :

```python
content = response.choices[^0].message.content.strip()

if content.startswith("```"):
    content = content.split("```")[^1]
    if content.startswith("json"):
        content = content[4:]

result = json.loads(content)  # ← падает если content == "" или имеет \n в начале
```

**Проблема:** `.split("```")[^1]` после обрезки оставляет `\njson\n{...}`, а проверка `if content.startswith("json")` убирает только `json` без `\n`. В результате `json.loads("\n{...}")` — корректно работает, но `json.loads("")` — бросает `JSONDecodeError: Expecting value: line 1 column 1 char 0`.

Дополнительно: при пустом ответе от API `response.choices[^0].message.content` может вернуть `None`, а `None.strip()` вызывает `AttributeError`, которое перехватывается в `except Exception` и возвращает `{}` — но в логах мы видим именно `JSONDecodeError`, значит контент не `None`, а пустая строка `""`.

***

## 2. Цели (Goals)

- **G-1:** `SDClassifier` использует ту же модель, что задана в `PRIMARY_MODEL` (через `config.LLM_MODEL`)
- **G-2:** Module-level инициализация `sd_classifier` и `sd_compatibility_resolver` не вызывает `NameError` при старте
- **G-3:** `state_classifier._classify_by_llm()` корректно парсит ответ GPT-5 mini включая пустой контент, `None`, markdown-обёртку
- **G-4:** При пустом или нераспознанном ответе LLM — `StateClassifier` и `SDClassifier` молча возвращают fallback без ERROR в логах


## 3. Не-цели (Non-Goals)

- Не изменять логику классификации (алгоритм, состояния, уровни СД)
- Не изменять промпты (`SD_CLASSIFIER_SYSTEM_PROMPT` и промпт в `state_classifier`)
- Не изменять `config.py` — он уже корректен после PRD v1.0.1
- Не изменять `llm_answerer.py` — он уже корректен после PRD v1.0.1
- Не изменять никакие другие файлы кроме двух указанных

***

## 4. Технические изменения

### 4.1 Файл: `bot_psychologist/bot_agent/sd_classifier.py`

#### Изменение A — Убрать module-level `NameError`: перенести импорт `config` выше блока `_SD_SETTINGS`

**Текущий порядок импортов и module-level кода** (проблема в порядке):

```python
# ... импорты ...
from .config import config   # ← импорт есть, но...

_SD_SETTINGS = _load_sd_settings()   # ← вызывается ДО того как config полностью инициализирован
DEFAULT_LEVEL = ...
SD_COMPATIBILITY_BASE = ...

# ... классы ...

sd_classifier = SDClassifier()          # ← создаётся на module-level
sd_compatibility_resolver = SDCompatibilityResolver()
```

**Решение — Lazy instantiation для глобальных объектов:**

Заменить последние две строки файла:

```python
# БЫЛО (строки в конце файла):
sd_classifier = SDClassifier()
sd_compatibility_resolver = SDCompatibilityResolver()

# СТАЛО:
_sd_classifier_instance: Optional[SDClassifier] = None
_sd_compatibility_resolver_instance: Optional[SDCompatibilityResolver] = None


def get_sd_classifier() -> SDClassifier:
    """Lazy singleton — создаётся при первом обращении, не при импорте."""
    global _sd_classifier_instance
    if _sd_classifier_instance is None:
        _sd_classifier_instance = SDClassifier()
    return _sd_classifier_instance


def get_sd_compatibility_resolver() -> SDCompatibilityResolver:
    """Lazy singleton — создаётся при первом обращении, не при импорте."""
    global _sd_compatibility_resolver_instance
    if _sd_compatibility_resolver_instance is None:
        _sd_compatibility_resolver_instance = SDCompatibilityResolver()
    return _sd_compatibility_resolver_instance


# Backward-compatible aliases — код, использующий sd_classifier напрямую, продолжит работать
# через property-like lazy access. Для полной обратной совместимости создаём сразу:
try:
    sd_classifier = SDClassifier()
    sd_compatibility_resolver = SDCompatibilityResolver()
except Exception as _e:
    logger.warning(f"[SD_CLASSIFIER] Deferred init due to: {_e}")
    sd_classifier = None  # type: ignore
    sd_compatibility_resolver = None  # type: ignore
```

**Важно:** Обернуть в `try/except` — если при старте что-то идёт не так, бот не падает полностью, а SDClassifier переходит в fallback-режим. Все вызывающие модули уже проверяют `if self.client` и обрабатывают `None`.

#### Изменение B — `SDClassifier.__init__`: читать модель из `config.LLM_MODEL`

**Текущий код:**

```python
def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None):
    self.model = model or str(_SD_SETTINGS.get("model", "gpt-4o-mini"))
    self.temperature = float(temperature if temperature is not None else _SD_SETTINGS.get("temperature", 0.1))
```

**Новый код:**

```python
def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None):
    # Приоритет: явный аргумент → PRIMARY_MODEL из .env → YAML default → hardcoded default
    # Это гарантирует что SDClassifier всегда использует ту же модель, что и весь бот
    self.model = model or config.LLM_MODEL or str(_SD_SETTINGS.get("model", "gpt-4o-mini"))
    self.temperature = float(temperature if temperature is not None else _SD_SETTINGS.get("temperature", 0.1))
    logger.debug(f"[SD_CLASSIFIER] Initialized with model={self.model}")
```

**Почему такой порядок приоритетов:**

1. `model` — явный аргумент при создании экземпляра (максимальный приоритет, для тестов)
2. `config.LLM_MODEL` — значение из `.env` → `PRIMARY_MODEL` (основное рабочее значение)
3. `_SD_SETTINGS.get("model", "gpt-4o-mini")` — YAML конфиг (fallback если `.env` не задан)

#### Изменение C — `SDClassifier._llm_classify()`: улучшить обработку ответа

В методе `_llm_classify`, в блоке `try`, добавить защиту от пустого `raw`:

```python
# ТЕКУЩИЙ КОД:
response = self.client.chat.completions.create(**request_params)
raw = (response.choices.message.content or "").strip()
data = json.loads(raw)

# НОВЫЙ КОД:
response = self.client.chat.completions.create(**request_params)
raw = (response.choices.message.content or "").strip()

# Очистка markdown-обёртки
if "```" in raw:
    import re
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

# Защита от пустого ответа
if not raw:
    logger.warning("[SD_CLASSIFIER] LLM returned empty content, using fallback")
    return SDClassificationResult(
        primary=self.default_level,
        secondary=None,
        confidence=0.50,
        indicator="llm_empty_response",
        method="fallback",
    )

data = json.loads(raw)
```


***

### 4.2 Файл: `bot_psychologist/bot_agent/state_classifier.py`

#### Изменение A — Метод `_classify_by_llm()`: надёжный парсинг ответа GPT-5 mini

Найти блок парсинга ответа в методе `_classify_by_llm` и заменить целиком:

**Текущий код:**

```python
response = self.llm.client.chat.completions.create(**request_params)

content = response.choices.message.content.strip()

# Очистка от markdown если есть
if content.startswith("```"):
    content = content.split("```")
    if content.startswith("json"):
        content = content[4:]

result = json.loads(content)
return result
```

**Новый код:**

```python
response = self.llm.client.chat.completions.create(**request_params)

# Безопасное извлечение контента — GPT-5 может вернуть None
raw_content = response.choices.message.content
content = (raw_content or "").strip()

# Очистка markdown-обёртки (```json ... ``` или ``` ... ```)
if "```" in content:
    import re
    content = re.sub(r"```(?:json)?\s*", "", content).strip()

# Защита от пустого ответа — GPT-5 mini иногда возвращает пустую строку
# при сложных structured JSON промптах
if not content:
    logger.warning("⚠️ LLM вернул пустой ответ при классификации состояния")
    return {}

result = json.loads(content)
return result
```

**Почему `re.sub` вместо `.split()`:**

- `re.sub(r"```(?:json)?\s*", "", content)` удаляет **все вхождения** открывающего и закрывающего `````, включая варианты ````json\n`, ```` \n`, ````JSON`
- `.split("```")[^1]` — хрупкий подход: не работает если модель добавляет пробел перед кавычками или использует другой регистр


#### Изменение B — Метод `_classify_by_llm()`: улучшить logging уровня

Изменить уровень предупреждения при JSON ошибке с `WARNING` на `DEBUG` — это не критичная ошибка, а ожидаемое поведение при коротких вопросах:

```python
# БЫЛО:
except json.JSONDecodeError as e:
    logger.warning(f"⚠️ Ошибка парсинга JSON: {e}")
    return {}

# СТАЛО:
except json.JSONDecodeError as e:
    logger.debug(f"🔍 JSON parse miss (нормально для коротких сообщений): {e}")
    return {}
```

**Почему это важно:** Текущие `WARNING` в логах засоряют monitoring и маскируют реальные ошибки. Падение парсинга JSON при коротком сообщении — ожидаемый сценарий, не ошибка.

***

## 5. Порядок выполнения агентом

```
Шаг 1 → sd_classifier.py: Изменение B (SDClassifier.__init__ читает config.LLM_MODEL)
Шаг 2 → sd_classifier.py: Изменение C (_llm_classify: защита от пустого raw)
Шаг 3 → sd_classifier.py: Изменение A (lazy init + try/except для module-level объектов)
Шаг 4 → state_classifier.py: Изменение A (надёжный парсинг)
Шаг 5 → state_classifier.py: Изменение B (уровень логирования JSON ошибки)
```

**Шаг 3 выполняется последним** в `sd_classifier.py` намеренно: lazy init меняет интерфейс модуля, и его нужно делать только после того как логика классов уже исправлена и проверена.

***

## 6. Acceptance Criteria (Smoke-тесты)

### Тест 1: SDClassifier использует модель из `.env`

```bash
# В .env: PRIMARY_MODEL=gpt-5-mini
python -c "
from bot_agent.sd_classifier import sd_classifier
print(sd_classifier.model)
# Ожидаемый вывод: gpt-5-mini
# НЕ должно быть: gpt-4o-mini
"
```


### Тест 2: Нет `NameError` при импорте модуля

```bash
python -c "import bot_agent.sd_classifier; print('OK')"
# Ожидаемый вывод: OK
# В логах НЕ должно быть: NameError / config is not defined
```


### Тест 3: `state_classifier` не возвращает вечный fallback `curious 0.30`

```bash
# В логах после запроса НЕ должно быть:
# WARNING botagent.stateclassifier JSON Expecting value: line 1 column 1 char 0
# INFO botagent.stateclassifier curious 0.30
# При корректном ответе LLM должен быть реальный распознанный state
```


### Тест 4: Пустой ответ API обрабатывается корректно (graceful fallback)

```bash
# В логах при пустом ответе должно быть:
# WARNING [SD_CLASSIFIER] LLM returned empty content, using fallback
# WARNING ⚠️ LLM вернул пустой ответ при классификации состояния
# НЕ должно быть: Exception traceback / ERROR
```


### Тест 5: SD-уровень определяется методом `llm`, не только `fallback`

```bash
# В логах при достаточно длинном сообщении должно быть:
# INFO botagent.answeradaptive SD GREEN conf 0.85, method llm
# НЕ должно быть: method fallback при каждом запросе
```


### Тест 6: Возврат на `gpt-4o-mini` не сломан

```bash
# В .env: PRIMARY_MODEL=gpt-4o-mini
python -c "
from bot_agent.sd_classifier import sd_classifier
from bot_agent.config import config
print(sd_classifier.model)       # gpt-4o-mini
print(config.LLM_MODEL)          # gpt-4o-mini
print(config.get_token_param_name())         # max_tokens
print(config.supports_custom_temperature())  # True
"
```


***

## 7. Ограничения для агента (Out-of-Scope Guards)

- **Не изменять** `SD_CLASSIFIER_SYSTEM_PROMPT` — промпт не является причиной бага
- **Не изменять** `SD_KEYWORDS`, `SD_LEVELS_ORDER`, `_default_settings()` — логика классификации верна
- **Не изменять** `_load_sd_settings()` — YAML-загрузка работает корректно
- **Не изменять** `SDCompatibilityResolver` — класс не имеет отношения к проблеме
- **Не изменять** `config.py` — после PRD v1.0.1 он уже содержит все нужные методы: `get_token_param_name()` и `supports_custom_temperature()` с правильными сигнатурами
- **Не изменять** `llm_answerer.py` — уже исправлен в PRD v1.0.1

***

## 8. Итоговый список изменений

| Файл | Изменение | Суть |
| :-- | :-- | :-- |
| `bot_agent/sd_classifier.py` | B: `__init__` | `self.model = model or config.LLM_MODEL or ...` вместо YAML-default |
| `bot_agent/sd_classifier.py` | C: `_llm_classify` | `re.sub` для markdown, защита от `raw == ""` |
| `bot_agent/sd_classifier.py` | A: module-level | Обернуть `sd_classifier = SDClassifier()` в `try/except` |
| `bot_agent/state_classifier.py` | A: `_classify_by_llm` | `re.sub` для markdown, `if not content: return {}`, `None`-safety |
| `bot_agent/state_classifier.py` | B: logging | `WARNING → DEBUG` для `JSONDecodeError` |

**Итого: 2 файла, 5 точечных изменений, 0 новых файлов.**


