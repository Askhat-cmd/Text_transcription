

***

# PRD-v3.0.4: Исправление отображения токенов и стоимости в Debug Trace

**Версия:** 1.0 | **Приоритет:** HIGH | **Статус:** Готово к выполнению

***

## Цель

Устранить 4 бага, из-за которых в Web UI debug-панели поля `prompt/completion/total tokens`, `session_turns` и `$cost` показывают `—` или `$0.000000`.

***

## Затрагиваемые файлы

```
bot_psychologist/
├── bot_agent/
│   ├── answer_adaptive.py   ← 3 правки
│   ├── llm_answerer.py      ← 1 правка
│   └── config.py            ← 1 правка
```


***

## ЗАДАЧА 1 — `answer_adaptive.py`: исправить `or`-баг при записи токенов в `debug_trace`

**Проблема:** В конце non-fast-path ветки три строки используют `or` для записи токенов в `debug_trace`. Если токен-счётчик возвращает `0` (валидное значение), `0 or tokens_prompt` вернёт `None`, и поле останется пустым.

**Найти** (ищи по тексту `# FIX 2a`):

```python
# Основные значения (имеют приоритет)
debug_trace["tokens_prompt"] = debug_trace.get("tokens_prompt") or tokens_prompt
debug_trace["tokens_completion"] = debug_trace.get("tokens_completion") or tokens_completion
debug_trace["tokens_total"] = debug_trace.get("tokens_total") or tokens_total
```

**Заменить на:**

```python
# Основные значения (имеют приоритет)
if debug_trace.get("tokens_prompt") is None:
    debug_trace["tokens_prompt"] = tokens_prompt
if debug_trace.get("tokens_completion") is None:
    debug_trace["tokens_completion"] = tokens_completion
if debug_trace.get("tokens_total") is None:
    debug_trace["tokens_total"] = tokens_total
```


***

## ЗАДАЧА 2 — `answer_adaptive.py`: заменить словарь `COST_PER_1K_TOKENS`

**Проблема:** Словарь в верхней части файла используется функцией `_estimate_cost()`. Многих актуальных моделей нет, поэтому `gpt-4.1-mini`, `gpt-5-nano` и др. падают в `"default"` и считают неверно.

**Найти** (ищи по точному тексту в начале файла):

```python
COST_PER_1K_TOKENS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-5-mini": {"input": 0.00025, "output": 0.002},
    "gpt-5": {"input": 0.00125, "output": 0.01},
    "default": {"input": 0.001, "output": 0.002},
}
```

**Заменить на** (ставки = цена за 1M / 1000):

```python
COST_PER_1K_TOKENS = {
    "gpt-5.2":      {"input": 0.00175,  "output": 0.01400},
    "gpt-5.1":      {"input": 0.00125,  "output": 0.01000},
    "gpt-5":        {"input": 0.00125,  "output": 0.01000},
    "gpt-5-mini":   {"input": 0.00025,  "output": 0.00200},
    "gpt-5-nano":   {"input": 0.00005,  "output": 0.00040},
    "gpt-4.1":      {"input": 0.00200,  "output": 0.00800},
    "gpt-4.1-mini": {"input": 0.00040,  "output": 0.00160},
    "gpt-4.1-nano": {"input": 0.00010,  "output": 0.00040},
    "gpt-4o-mini":  {"input": 0.00015,  "output": 0.00060},
    "default":      {"input": 0.00125,  "output": 0.01000},
}
```


***

## ЗАДАЧА 3 — `answer_adaptive.py`: заменить `cost_per_1m` внутри `_update_session_token_metrics()`

**Проблема:** Этот словарь используется для накопительного подсчёта `session_cost_usd`. Он также устарел и не содержит новые модели, поэтому `session_cost_usd` остаётся `None`.

**Найти** (внутри функции `_update_session_token_metrics`, ищи по строке `"gpt-4-turbo"`):

```python
    cost_per_1m = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
        "gpt-5-mini": {"input": 0.25, "output": 2.00},
        "gpt-5-mini-2025-08-07": {"input": 0.25, "output": 2.00},
        "gpt-5": {"input": 1.25, "output": 10.00},
        "gpt-5-2025-08-07": {"input": 1.25, "output": 10.00},
    }
```

**Заменить на** (ставки в USD за 1 000 000 токенов, точно по таблице):

```python
    cost_per_1m = {
        "gpt-5.2":      {"input": 1.75,  "output": 14.00},
        "gpt-5.1":      {"input": 1.25,  "output": 10.00},
        "gpt-5":        {"input": 1.25,  "output": 10.00},
        "gpt-5-mini":   {"input": 0.25,  "output":  2.00},
        "gpt-5-nano":   {"input": 0.05,  "output":  0.40},
        "gpt-4.1":      {"input": 2.00,  "output":  8.00},
        "gpt-4.1-mini": {"input": 0.40,  "output":  1.60},
        "gpt-4.1-nano": {"input": 0.10,  "output":  0.40},
        "gpt-4o-mini":  {"input": 0.15,  "output":  0.60},
    }
```


***

## ЗАДАЧА 4 — `llm_answerer.py`: исправить `or`-баг при разборе `usage` из Responses API

**Проблема:** Модели `gpt-5*` используют Responses API, где поля называются `input_tokens` / `output_tokens`. Текущий код читает их через `or`, что даёт `None` при значении `0`.

**Найти** (внутри блока `if not config.supports_custom_temperature(model):`):

```python
                if usage is not None:
                    tokens_prompt = (
                        getattr(usage, "prompt_tokens", None)
                        or getattr(usage, "input_tokens", None)
                    )
                    tokens_completion = (
                        getattr(usage, "completion_tokens", None)
                        or getattr(usage, "output_tokens", None)
                    )
                    tokens_total = getattr(usage, "total_tokens", None)
                    if tokens_total is None and tokens_prompt is not None and tokens_completion is not None:
                        tokens_total = int(tokens_prompt) + int(tokens_completion)
```

**Заменить на:**

```python
                if usage is not None:
                    _tp = getattr(usage, "prompt_tokens", None)
                    tokens_prompt = _tp if _tp is not None else getattr(usage, "input_tokens", None)

                    _tc = getattr(usage, "completion_tokens", None)
                    tokens_completion = _tc if _tc is not None else getattr(usage, "output_tokens", None)

                    tokens_total = getattr(usage, "total_tokens", None)
                    if tokens_total is None and tokens_prompt is not None and tokens_completion is not None:
                        tokens_total = int(tokens_prompt) + int(tokens_completion)
```


***

## ЗАДАЧА 5 — `config.py`: обновить `SUPPORTED_MODELS`

**Проблема:** Список содержит устаревшие модели (`gpt-4-turbo`, `gpt-4o`), которые не используются, и отсутствуют новые (`gpt-4.1`, `gpt-5-nano` и др.). `validate()` может падать при правильных настройках.

**Найти:**

```python
    SUPPORTED_MODELS: tuple = (
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-5-mini",
        "gpt-5-mini-2025-08-07",
        "gpt-5",
        "gpt-5-2025-08-07",
    )
```

**Заменить на:**

```python
    SUPPORTED_MODELS: tuple = (
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4o-mini",
    )
```


***

## Чеклист выполнения

```
[ ] ЗАДАЧА 1  answer_adaptive.py  — or → is None  (3 строки, ~финал non-fast-path)
[ ] ЗАДАЧА 2  answer_adaptive.py  — COST_PER_1K_TOKENS  (верхний уровень файла)
[ ] ЗАДАЧА 3  answer_adaptive.py  — cost_per_1m  (внутри _update_session_token_metrics)
[ ] ЗАДАЧА 4  llm_answerer.py     — or → is not None  (Responses API usage)
[ ] ЗАДАЧА 5  config.py           — SUPPORTED_MODELS  (9 актуальных моделей)
```


***

## Проверка после исправления

1. Запустить бота, отправить любой запрос с флагом `debug=true`
2. В Web UI → открыть **Модели, токены и стоимость**
3. Ожидаемый результат:
| Поле | До | После |
| :-- | :-- | :-- |
| `prompt` | `—` | число (напр. `1 240`) |
| `completion` | `—` | число (напр. `380`) |
| `total` | `—` | число (напр. `1 620`) |
| `session tokens` | `—` | накопленное число |
| `session turns` | `—` | `1`, `2`, `3`... |
| `$cost` | `$0.000000` | реальная сумма |

