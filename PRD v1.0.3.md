

***

## Анализ PRD v1.0.3: что правильно и что пропущено

### ✅ Что было правильно

**Корень проблемы** определён верно — `response_format` отсутствует и GPT-5 mini молча возвращает пустую строку. Оба промпта уже содержат слово "JSON" (обязательное условие для `json_object` mode) — в `SD_CLASSIFIER_SYSTEM_PROMPT`: `Верни ТОЛЬКО JSON:`, в `state_classifier` промпте: `Respond ONLY in valid JSON format`. Обратная совместимость с `gpt-4o-mini` сохранена.

### ❌ Что было пропущено — критически

**`sd_classifier` использует `max_completion_tokens: 150` — это опасно мало.**

```python
token_param = config.get_token_param_name(self.model)
request_params = {
    "model": self.model,
    token_param: 150,   # ← ДЛЯ GPT-5-MINI ЭТОТ ПАРАМЕТР = max_completion_tokens
    ...
}
```

Для `gpt-4o-mini` это был `max_tokens: 150` — только выходные токены, достаточно. Для `gpt-5-mini` это `max_completion_tokens: 150` — и это значение **включает все внутренние processing-токены модели**. Если GPT-5 mini тратит часть лимита на внутреннюю обработку, на сам JSON вывод остаётся меньше. Индикатор на русском (`"indicator": "краткий маркер из нескольких слов"`) может занять 20–40 токенов, и при неблагоприятном раскладе JSON обрывается на полуслове → `json.loads()` падает с ошибкой → fallback. Это **вторая причина** пустых ответов, которую я пропустил в первом PRD.

Для `state_classifier` лимит `500` — достаточный запас, там всё в порядке.

***

# PRD v1.0.3 (переработанный) — JSON Response Format + Token Fix

**Репозиторий:** `Askhat-cmd/Text_transcription`
**Путь проекта:** `bot_psychologist/`
**Версия документа:** 1.0.3 rev.2
**Дата:** 2026-03-02
**Статус:** `READY FOR AGENT`
**Приоритет:** `BLOCKER`
**Зависимость:** PRD v1.0.2 выполнен (коммит [`66e8b50`](https://github.com/Askhat-cmd/Text_transcription/commit/66e8b50ca853d6d144efd106be42bf542f079223))
**Файлов к изменению:** 2

***

## 1. Два подтверждённых бага

### BUG-01 — Оба классификатора: отсутствует `response_format` (`CRITICAL`)

**Доказательство в логах**:[^1]

```
# Воспроизводится на КАЖДОМ запросе при gpt-5-mini:
WARNING | state_classifier | ⚠️ LLM вернул пустой ответ при классификации состояния
WARNING | sd_classifier    | [SD_CLASSIFIER] LLM returned empty content, using fallback

# Оба вызова занимают 7 и 3 секунды — API отвечает, не timeout.
# Модель обрабатывает запрос и возвращает пустую строку намеренно.
```

**Причина:** `gpt-5-mini` без явного `response_format={"type": "json_object"}` не гарантирует JSON-вывод и возвращает пустой контент при structured-output промптах. `gpt-4o-mini` делал это в свободном режиме, `gpt-5-mini` — нет.

**Оба промпта уже содержат слово "JSON"** — обязательное условие OpenAI для активации `json_object` mode:

- `state_classifier`: `"Respond ONLY in valid JSON format"`
- `sd_classifier`: `"Верни ТОЛЬКО JSON:"`

Дополнительных изменений в промптах не требуется.

***

### BUG-02 — `sd_classifier` только: `max_completion_tokens: 150` недостаточно (`HIGH`)

**Доказательство в коде** (`sd_classifier.py`, метод `_llm_classify`) :

```python
token_param = config.get_token_param_name(self.model)
# Для gpt-5-mini: token_param == "max_completion_tokens"
request_params = {
    "model": self.model,
    token_param: 150,   # ← 150 max_completion_tokens для gpt-5-mini
    ...
}
```

**Ожидаемый JSON-ответ:**

```json
{
  "primary": "ORANGE",
  "secondary": "GREEN",
  "confidence": 0.75,
  "indicator": "фокус на результате и эффективности карьеры"
}
```

Это ~40–60 токенов. Но при лимите в 150 токенов и учёте того что GPT-5 mini может использовать часть лимита на внутреннюю обработку — запас слишком мал. Увеличить до **500** — достаточный буфер для любого реального ответа.

Для `state_classifier` лимит уже `500` токенов — достаточно, не трогаем.

***

## 2. Цели (Goals)

- **G-1:** `state_classifier._classify_by_llm()` получает валидный JSON от `gpt-5-mini` при каждом запросе
- **G-2:** `sd_classifier._llm_classify()` получает валидный JSON от `gpt-5-mini` при каждом запросе
- **G-3:** `sd_classifier` имеет достаточный токен-лимит для полного JSON-ответа включая `indicator` на русском
- **G-4:** Обратная совместимость с `gpt-4o-mini` сохранена полностью


## 3. Не-цели (Non-Goals)

- Не изменять промпты — они корректны
- Не изменять `config.py`, `llm_answerer.py` и любые другие файлы
- Не изменять `state_classifier` токен-лимит — `500` уже достаточен
- Не исправлять 38-секундную загрузку `semantic_memory` — это отдельный PRD

***

## 4. Технические изменения

### 4.1 Файл: `bot_psychologist/bot_agent/state_classifier.py`

**Метод:** `StateClassifier._classify_by_llm()`

Найти `request_params` и добавить `response_format`. Только это изменение, ничего больше:

```python
# БЫЛО:
token_param = config.get_token_param_name(config.LLM_MODEL)
request_params = {
    "model": config.LLM_MODEL,
    "messages": [{"role": "user", "content": prompt}],
    token_param: 500,
}
if config.supports_custom_temperature(config.LLM_MODEL):
    request_params["temperature"] = 0.3

# СТАЛО:
token_param = config.get_token_param_name(config.LLM_MODEL)
request_params = {
    "model": config.LLM_MODEL,
    "messages": [{"role": "user", "content": prompt}],
    token_param: 500,
    "response_format": {"type": "json_object"},
}
if config.supports_custom_temperature(config.LLM_MODEL):
    request_params["temperature"] = 0.3
```

**Изменений: +1 строка.**

***

### 4.2 Файл: `bot_psychologist/bot_agent/sd_classifier.py`

**Метод:** `SDClassifier._llm_classify()`

Найти `request_params` и внести **два изменения**: добавить `response_format` и увеличить токен-лимит с `150` до `500`:

```python
# БЫЛО:
token_param = config.get_token_param_name(self.model)
request_params = {
    "model": self.model,
    token_param: 150,
    "messages": [
        {"role": "system", "content": SD_CLASSIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ],
}
if config.supports_custom_temperature(self.model):
    request_params["temperature"] = self.temperature

# СТАЛО:
token_param = config.get_token_param_name(self.model)
request_params = {
    "model": self.model,
    token_param: 500,
    "messages": [
        {"role": "system", "content": SD_CLASSIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ],
    "response_format": {"type": "json_object"},
}
if config.supports_custom_temperature(self.model):
    request_params["temperature"] = self.temperature
```

**Изменений: +1 строка (`response_format`), изменение значения `150 → 500`.**

***

## 5. Порядок выполнения агентом

```
Шаг 1 → state_classifier.py: добавить "response_format": {"type": "json_object"}
Шаг 2 → sd_classifier.py:    добавить "response_format": {"type": "json_object"}
                               изменить токен-лимит 150 → 500
Шаг 3 → один коммит с обоими файлами
```

**Итого: 2 файла, 2 строки добавлено, 1 значение изменено.**

***

## 6. Acceptance Criteria

### Тест 1: `state_classifier` перестаёт возвращать вечный fallback

```
# Не должно быть при каждом запросе:
WARNING | state_classifier | ⚠️ LLM вернул пустой ответ

# Должно быть реальное состояние:
INFO | state_classifier | ✅ Состояние определено: committed (уверенность: 0.82)
```


### Тест 2: `sd_classifier` перестаёт возвращать вечный fallback

```
# Не должно быть:
WARNING | sd_classifier | [SD_CLASSIFIER] LLM returned empty content, using fallback

# Должно быть:
INFO | answer_adaptive | ✅ SD уровень: GREEN (conf=0.72, method=llm)
```


### Тест 3: В UI пропадает вечный `Curious (30%)` и `conf: 0.08 SD: GREEN`

```
# Скриншот показывает: Curious (30%), conf:0.08, SD: GREEN на КАЖДОМ запросе
# После фикса: реальный state и confidence > 0.5 при содержательных сообщениях
```


### Тест 4: Обратная совместимость с `gpt-4o-mini`

```
# При PRIMARY_MODEL=gpt-4o-mini поведение идентично предыдущим версиям
# response_format json_object поддерживается gpt-4o-mini нативно
# Токен-лимит 500 для sd_classifier — не хуже чем 150 для gpt-4o-mini
```


***

## 7. Ограничения для агента

- **Не изменять** промпты `SD_CLASSIFIER_SYSTEM_PROMPT` и промпт `state_classifier`
- **Не изменять** логику парсинга из PRD v1.0.2 — `re.sub`, `None`-safety остаются
- **Не добавлять** `response_format` в `llm_answerer.py` — основной генератор работает с free-form текстом
- **Не изменять** токен-лимит `state_classifier` — `500` уже достаточен



