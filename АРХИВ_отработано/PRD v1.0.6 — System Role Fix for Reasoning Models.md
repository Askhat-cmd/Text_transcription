

## Диагноз: проблема НЕ в токенах

Агент правильно применил PRD v1.0.5 — в коде `config.get_effective_max_tokens(model)` стоит . Но `Empty content` **всё равно срабатывает**. Это означает одно: **gpt-5-mini возвращает `content = null` намеренно**.[^1]

### Что реально происходит

Посмотри на тайминги в логах:[^1]

```
10:35:17 → запрос отправлен (CLARIFICATION fast-path)
10:35:24 → WARNING: Empty content    ← 7 секунд на запрос
10:35:42 → второй вызов (полный путь)  
10:35:49 → WARNING: Empty content    ← снова 7 секунд
```

Только **7 секунд** на reasoning-модель — это слишком мало для реального reasoning. При `max_completion_tokens=16000` она должна думать 20-40 секунд. Значит **API возвращает быстрый пустой ответ** — это поведение `gpt-5-mini` при вызове с `system`-ролью.

### Настоящая причина

**`gpt-5-mini` не поддерживает `system` role в messages.** Это известное ограничение reasoning-моделей OpenAI (серии o1/o3/o5). Они принимают только `user` и `assistant` роли. При передаче `system` — API не возвращает ошибку, просто отдаёт `content = None`.

Нет ни одного `ERROR` в логах  — значит API отвечает 200 OK, но content пустой. Это классический симптом именно этой проблемы.[^1]

***

# PRD v1.0.6 — System Role Fix for Reasoning Models

**Репозиторий:** `Askhat-cmd/Text_transcription`
**Файлов к изменению:** 1 (`llm_answerer.py`)
**Строк изменений:** ~8
**Зависимость:** PRD v1.0.5 выполнен (commit `3df09fd`)

***

## Изменение: `llm_answerer.py`

**Найти** в методе `generate_answer` блок формирования `request_params` (примерно строки 155-170):

```python
# БЫЛО:
request_params = {
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ],
    token_param: max_tokens,
}
```

**Заменить на:**

```python
# СТАЛО:
if config.supports_custom_temperature(model):
    # Standard models: system role supported
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
else:
    # Reasoning models (gpt-5, o1, o3): no system role
    # Merge system prompt into user message
    messages = [
        {"role": "user", "content": system_prompt + "\n\n" + context},
    ]

request_params = {
    "model": model,
    "messages": messages,
    token_param: max_tokens,
}
```

**Удалить** строку ниже (она теперь дублируется — уже вынесена в блок выше):

```python
if config.supports_custom_temperature(model):
    request_params["temperature"] = temperature
else:
    logger.debug("Skipping custom temperature for model %s", model)
```

**Вернуть** в конец `request_params` (после `messages`):

```python
if config.supports_custom_temperature(model):
    request_params["temperature"] = temperature
```


***

## Итоговый вид блока (для агента — вставить целиком)

```python
if config.supports_custom_temperature(model):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
else:
    messages = [
        {"role": "user", "content": system_prompt + "\n\n" + context},
    ]

request_params = {
    "model": model,
    "messages": messages,
    token_param: max_tokens,
}
if config.supports_custom_temperature(model):
    request_params["temperature"] = temperature
else:
    logger.debug("Skipping custom temperature for model %s", model)
```


***

## Acceptance Criteria

```
# НЕ должно быть:
WARNING | llm_answerer | [LLM_ANSWERER] ⚠️ Empty content returned by model gpt-5-mini

# ДОЛЖНО быть:
DEBUG | llm_answerer | [LLM_ANSWERER] raw content length=350 model=gpt-5-mini
```

**Только 1 файл, только 1 функция, только замена одного блока кода.**


