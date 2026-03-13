

## 🛠 Мини-ПРД: Фикс SD-разметки в Bot_data_base

### Контекст

`Bot_data_base` — подпроект, заменяющий `voice_bot_pipeline`. Он загружает книги, разбивает на чанки и размечает их по уровням Спиральной Динамики (SD) через OpenAI. Разметка сейчас **полностью не работает** — все блоки получают `UNCERTAIN` вместо реальных SD-уровней.

### Проблема

Файл: `Bot_data_base/processors/sd_labeler.py`

Три причины сбоя, подтверждённые логами и анализом кода:

1. **OpenAI возвращает пустую строку** — отсутствует `response_format: json_object`, поэтому GPT иногда возвращает `""` вместо JSON → `JSON parse error: Expecting value: line 1 column 1`
2. **`max_tokens: 300` слишком мало** — для батча из 5 чанков нужно минимум 800 токенов, GPT обрезает ответ
3. **Промпт противоречив** — описывает ответ для одного объекта, но запрос содержит батч из 5 — GPT не понимает нужный формат ответа

### Эталон

Рабочее решение уже есть в `bot_psychologist/bot_agent/sd_classifier.py` — использует `response_format`, `max_tokens: 2000`, защиту от пустого ответа.

***

### Задача: изменить `Bot_data_base/processors/sd_labeler.py`

**Изменение 1 — добавить `response_format` и увеличить `max_tokens`:**

```python
# В методе _call_openai()
response = client.chat.completions.create(
    model=self.model,
    temperature=self.temperature,
    max_tokens=self.max_tokens,       # default теперь 800
    response_format={"type": "json_object"},  # ← ДОБАВИТЬ
    messages=[
        {"role": "system", "content": SD_LABELER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ],
)
```

**Изменение 2 — защита от пустого ответа (после получения `raw`):**

```python
raw = (response.choices[0].message.content or "").strip()
logger.debug(f"[SD_LABELER] raw response: {raw[:200]}")

if not raw:
    logger.warning("[SD_LABELER] empty LLM response, using defaults")
    return json.dumps([self._default_label() for _ in texts])
```

**Изменение 3 — исправить дефолт `max_tokens` в `__init__`:**

```python
# было: cfg.get("max_tokens", 300)
self.max_tokens = int(cfg.get("max_tokens", 800))
```

**Изменение 4 — переписать `SD_LABELER_SYSTEM_PROMPT`:**

Убрать пример одиночного объекта. Промпт должен заканчиваться **только** так:

```
Верни ТОЛЬКО JSON-массив объектов — по одному на каждый переданный текст,
в том же порядке. Пример для 2 текстов:
[
  {"sd_level": "GREEN", "sd_secondary": "YELLOW", "sd_confidence": 0.85, "complexity": 0.45, "reasoning": "..."},
  {"sd_level": "BLUE",  "sd_secondary": null,     "sd_confidence": 0.90, "complexity": 0.30, "reasoning": "..."}
]
Никакого другого текста кроме JSON-массива.
```


***

### Критерий готовности

После изменений запустить сервер и загрузить тестовую книгу. В логах должны **исчезнуть** строки:

```
[SD_LABELER] JSON parse error
[SD_LABELER] low confidence 0.00
```

И **появиться** строки вида:

```
[SD_LABELER] raw response: [{"sd_level": "GREEN", ...
```

В реестре источников колонка SD должна показывать реальные уровни (`{"GREEN":15, "BLUE":8, ...}`) вместо `{"UNCERTAIN":35}`.

