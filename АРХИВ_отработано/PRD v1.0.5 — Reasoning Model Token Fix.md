

***

## Точный диагноз: почему gpt-5-mini не отвечает

**`llm_answerer.py` строка 155:**

```python
max_tokens = max_tokens or config.LLM_MAX_TOKENS  # = 1500 ВСЕГДА
```

**`config.py` строки 80-86:**

```python
_MAX_COMPLETION_TOKENS_PREFIXES: tuple = ("gpt-5", "o1", "o3", "o4")
# get_token_param_name("gpt-5-mini") → "max_completion_tokens" ✓
# supports_custom_temperature("gpt-5-mini") → False ✓ (температура не отправляется)
```

**Что происходит при каждом запросе с `gpt-5-mini`:**

```
1. llm_answerer → API: {max_completion_tokens: 1500, model: "gpt-5-mini", ...}
2. gpt-5-mini — это reasoning-модель, она думает ПЕРЕД ответом
3. Reasoning-токены (~1400-1500) полностью съедают бюджет max_completion_tokens
4. На сам ответ остаётся 0 токенов → content пустой
5. Fallback fires: "Расскажите подробнее о своём вопросе..." (32 секунды тишины)
```

**Подтверждение из логов:**[^1][^2]

- `gpt-4o-mini` (без reasoning): `max_tokens=1500` → полный ответ за 4-13s ✅
- `gpt-5-mini` (reasoning): `max_completion_tokens=1500` → пустой ответ за 32s ❌
- Ошибок API нет — значит проблема не в `system`-роли и не в temperature

**Что агент PRD v1.0.4 исправил корректно:**

- `supports_custom_temperature("gpt-5-mini") → False` → температура НЕ отправляется
- `CLASSIFIER_MODEL = gpt-4o-mini` → классификаторы работают быстро

**Что пропустил — единственная оставшаяся проблема:**
В `config.py` есть вся нужная инфраструктура (`_MAX_COMPLETION_TOKENS_PREFIXES`), но метода `get_effective_max_tokens()` нет. `LLM_MAX_TOKENS = 1500` — hardcoded, одинаковый для всех моделей.

***

# PRD v1.0.5 — Reasoning Model Token Fix

**Репозиторий:** `Askhat-cmd/Text_transcription`
**Версия:** 1.0.5
**Дата:** 2026-03-03
**Статус:** `READY FOR AGENT`
**Приоритет:** `BLOCKER`
**Зависимость:** PRD v1.0.4 выполнен (commit `23deba5`)
**Файлов к изменению:** 2
**Строк изменений:** ~12

***

## Root Cause

`gpt-5-mini` — reasoning-модель. `max_completion_tokens` включает как reasoning-токены (внутреннее «мышление»), так и output-токены. При лимите `1500` reasoning полностью поглощает бюджет, на вывод ответа остаётся 0 токенов → `content = ""` → fallback `"Расскажите подробнее..."`.

Для `gpt-4o-mini` параметр называется `max_tokens` и не включает reasoning — поэтому 1500 достаточно.

***

## Изменение 1: `config.py`

**Файл:** `bot_psychologist/bot_agent/config.py`

Добавить метод `get_effective_max_tokens` в класс `Config`. Вставить ПОСЛЕ метода `supports_custom_temperature`, ПЕРЕД методом `validate`:

```python
@classmethod
def get_effective_max_tokens(cls, model: Optional[str] = None) -> int:
    """Return effective token limit, accounting for reasoning models.
    
    Reasoning models (gpt-5, o1, o3, o4) consume tokens for internal thinking
    before writing output. max_completion_tokens must cover BOTH reasoning AND
    output tokens. Standard models need only output tokens.
    """
    target = (model or cls.LLM_MODEL).lower()
    for prefix in cls._MAX_COMPLETION_TOKENS_PREFIXES:
        if target.startswith(prefix):
            return 16000  # reasoning (thinking) + output
    return cls.LLM_MAX_TOKENS  # standard models: 1500
```

**Изменений: +12 строк.**

***

## Изменение 2: `llm_answerer.py`

**Файл:** `bot_psychologist/bot_agent/llm_answerer.py`

Найти строку (примерно строка 155):

```python
max_tokens = max_tokens or config.LLM_MAX_TOKENS
```

Заменить на:

```python
max_tokens = max_tokens or config.get_effective_max_tokens(model)
```

**Изменений: 1 строка.**

***

## Порядок выполнения

```
Шаг 1 → config.py: добавить метод get_effective_max_tokens после supports_custom_temperature
Шаг 2 → llm_answerer.py: заменить config.LLM_MAX_TOKENS → config.get_effective_max_tokens(model)
Шаг 3 → один коммит с обоими файлами
```


## Ограничения для агента

- **Не изменять** `LLM_MAX_TOKENS = 1500` — это дефолт для gpt-4o-mini, он правильный
- **Не изменять** `state_classifier.py` и `sd_classifier.py` — они используют `CLASSIFIER_MODEL=gpt-4o-mini`, токенов им достаточно
- **Не изменять** промпты, retrieval, path_builder
- **Не добавлять** `reasoning_effort` параметр — не нужен

***

## Acceptance Criteria

### Тест 1: gpt-5-mini генерирует реальный ответ

```
# Не должно быть:
WARNING | llm_answerer | [LLM_ANSWERER] ⚠️ Empty content returned by model gpt-5-mini

# Должно быть:
DEBUG | llm_answerer | [LLM_ANSWERER] raw content length=450 model=gpt-5-mini
```


### Тест 2: В UI виден текст ответа

```
# gpt-4o-mini: "Понятно, что ты переживаешь из-за большого дела..."  ← было работает
# gpt-5-mini:  <аналогичный текстовый ответ>  ← должно начать работать
```


### Тест 3: gpt-4o-mini не изменился

```
# get_effective_max_tokens("gpt-4o-mini") → 1500 (без изменений)
# get_effective_max_tokens("gpt-5-mini") → 16000 (новое поведение)
```
