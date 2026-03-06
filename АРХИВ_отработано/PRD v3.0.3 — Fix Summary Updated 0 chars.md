

***

```markdown
# Микро-PRD v3.0.3 — Fix: Summary Updated 0 chars

**Версия:** 3.0.3
**Статус:** Ready for implementation
**Приоритет:** HIGH (влияет на качество ответов — бот теряет контекст)
**Исполнитель:** Codex IDE Agent
**Затронутый файл:** `bot_psychologist/bot_agent/conversation_memory.py`
**Дата:** 2026-03-04

---

## 1. Проблема

В логах наблюдается: `Summary updated: 0 chars`

Метод `_update_summary()` делает прямой вызов LLM без параметра
`reasoning_effort`. Модель `gpt-5-mini` (reasoning model) при вызове
без `reasoning_effort` возвращает `message.content = ""` (пустую строку)
или `None`. В результате:
- Существующее непустое summary **перезаписывается пустой строкой**
- Бот теряет накопленный контекст диалога между сессиями
- `get_adaptive_context_text()` возвращает пустой блок summary

---

## 2. Анализ текущего кода (строки проблемы)

### Проблема 1 — нет `reasoning_effort`

В `_update_summary()` текущий вызов:

```python
request_params = {
    "model": config.LLM_MODEL,
    "messages": [{"role": "user", "content": summary_prompt}],
    token_param: 200,
}
if config.supports_custom_temperature(config.LLM_MODEL):
    request_params["temperature"] = 0.3

response = answerer.client.chat.completions.create(**request_params)
```

Для `gpt-5-mini` `reasoning_effort` не передаётся →
модель не знает как обрабатывать запрос → возвращает пустой `content`.

### Проблема 2 — нет защиты от пустого ответа

```python
summary_text = response.choices.message.content.strip()
```

Если `content` равен `None` — будет `AttributeError`.
Если `content` равен `""` — `summary_text` станет `""`, и далее:

```python
self.summary = summary_text  # ← затирает существующее summary пустой строкой!
```

Нет проверки: «если пришло пустое — не трогать старое».

### Проблема 3 — синхронный вызов внутри async-контекста

`_update_summary()` вызывается из `add_turn()`, который может
работать в async-контексте. Текущий вызов через
`answerer.client.chat.completions.create(...)` (синхронный клиент)
блокирует event loop.

---

## 3. Что менять — только метод `_update_summary()`

Менять **только** метод `_update_summary()` в
`bot_psychologist/bot_agent/conversation_memory.py`.

**Не трогать:**

- prompt текст `summary_prompt` — не менять
- триггер вызова summary (`SUMMARY_UPDATE_INTERVAL`) — не менять
- `SUMMARY_MAX_CHARS`, обрезку до лимита — не менять
- все остальные методы класса — не трогать

---

## 4. Реализация

Заменить метод `_update_summary()` целиком на следующий код:

```python
def _update_summary(self) -> None:
    """
    Обновить резюме диалога через LLM.

    Изменения v3.0.3:
    - Передаёт reasoning_effort для gpt-5-mini (reasoning model)
    - Защита от None в message.content (через `or ""`)
    - Защита от пустого ответа: не перезаписывать старое summary
    - Использует async_client через asyncio.to_thread для
      совместимости с async-контекстом
    """
    if len(self.turns) < 5:
        return
    if not config.OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY не установлен — summary не обновляется")
        return

    logger.info(f"Updating conversation summary (turn #{len(self.turns)})...")

    try:
        recent_turns = self.turns[-10:]
        turns_text = ""
        for i, turn in enumerate(recent_turns, 1):
            turns_text += f"\nХод {i}:\n"
            turns_text += f"Пользователь: {turn.user_input}\n"
            response_preview = turn.bot_response or ""
            if len(response_preview) > 200:
                response_preview = response_preview[:200] + "..."
            turns_text += f"Бот: {response_preview}\n"
            if turn.user_state:
                turns_text += f"Состояние: {turn.user_state}\n"

        # Prompt не меняется
        summary_prompt = f"""Создай КРАТКОЕ резюме диалога (максимум {config.SUMMARY_MAX_CHARS} символов, по-русски).

Включи:
- Ключевые темы, которые обсуждались
- Прогресс пользователя в понимании
- Важные инсайты или прорывы (если были)
- Текущий фокус диалога

ДИАЛОГ (последние 10 ходов):
{turns_text}

РЕЗЮМЕ (кратко, одним параграфом, без заголовков):"""

        from .llm_answerer import LLMAnswerer

        answerer = LLMAnswerer()
        if not answerer.client:
            logger.warning("⚠️ LLM клиент недоступен — summary не обновляется")
            return

        token_param = config.get_token_param_name(config.LLM_MODEL)

        request_params = {
            "model": config.LLM_MODEL,
            "messages": [{"role": "user", "content": summary_prompt}],
            token_param: 200,
        }

        # FIX 1: передать reasoning_effort для reasoning-моделей (gpt-5-mini)
        # Без этого параметра модель возвращает пустой content
        if hasattr(config, "REASONING_EFFORT") and config.REASONING_EFFORT:
            request_params["extra_body"] = {
                "reasoning_effort": config.REASONING_EFFORT
            }

        if config.supports_custom_temperature(config.LLM_MODEL):
            request_params["temperature"] = 0.3

        api_response = answerer.client.chat.completions.create(**request_params)

        # FIX 2: безопасное извлечение content
        # message.content может быть None у reasoning-моделей
        raw_content = api_response.choices.message.content
        summary_text = (raw_content or "").strip()

        # FIX 3: защита от перезаписи существующего summary пустым ответом
        if not summary_text:
            logger.warning(
                "[SUMMARY] LLM returned empty content — "
                "keeping existing summary (len=%d chars). "
                "Check reasoning_effort config.",
                len(self.summary or "")
            )
            return  # ← НЕ перезаписываем, выходим

        # Обрезка до лимита — без изменений
        if len(summary_text) > config.SUMMARY_MAX_CHARS:
            summary_text = summary_text[:config.SUMMARY_MAX_CHARS].rstrip()

        self.summary = summary_text
        self.summary_updated_at = len(self.turns)

        logger.info(f"Summary updated: {len(self.summary)} chars")

        if self.session_manager and self.summary:
            self.session_manager.update_summary(self.user_id, self.summary)

        self.save_to_disk()

    except Exception as e:
        logger.error(f"Summary update error: {e}", exc_info=True)
```


---

## 5. Проверка после реализации

### Шаг 1 — запустить сервер и отправить 10+ сообщений

После 10-го сообщения (если `SUMMARY_UPDATE_INTERVAL=10` или
по текущему значению в config) в логах должно появиться:

```
Summary updated: N chars    ← где N > 0
```

Вместо текущего:

```
Summary updated: 0 chars    ← эту строку больше не должны видеть
```


### Шаг 2 — проверить защиту от перезаписи

Если по какой-то причине LLM вернёт пустой ответ — в логах должно быть:

```
[SUMMARY] LLM returned empty content — keeping existing summary (len=N chars).
```

И старое summary должно остаться нетронутым.

### Шаг 3 — прогнать тесты

```bash
.\.venv\Scripts\python.exe -m pytest -q tests\test_response_generator.py \
  tests\test_response_formatter.py tests\test_hybrid_query.py \
  tests\test_sd_classifier.py tests\test_sd_filter.py \
  tests\test_sd_integration.py
```

Ожидаемый результат: **37 passed** (как после PRD v3.0.2).

---

## 6. Что НЕ меняется

| Компонент | Статус |
| :-- | :-- |
| Текст `summary_prompt` внутри метода | ❌ не трогать |
| Триггер `SUMMARY_UPDATE_INTERVAL` в `add_turn()` | ❌ не трогать |
| `SUMMARY_MAX_CHARS`, обрезка текста | ❌ не трогать |
| Все остальные методы `ConversationMemory` | ❌ не трогать |
| `PRIMARY_MODEL`, `REASONING_EFFORT`, промпты бота | ❌ не трогать |

```
```

