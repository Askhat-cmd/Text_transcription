
# PRD v5.2 — LLM Payload Debug + Curious Mode Prompt

**Версия:** 5.2 
**Дата:** 31.03.2026
**Репозиторий:** [Askhat-cmd/Text_transcription](https://github.com/Askhat-cmd/Text_transcription/tree/main/bot_psychologist)
**Статус:** Ready for implementation

***

## Контекст и архитектура системы

### Существующая слоистая архитектура промптов

Перед реализацией агент обязан понять структуру. В кодовой базе уже присутствуют следующие слои сборки системного промпта:


| Слой | Файл | Назначение |
| :-- | :-- | :-- |
| Layer 1 — Base | [`prompt_system_base.md`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/prompt_system_base.md) | Личность бота, базовые правила |
| Layer 2 — User Level | `prompt_system_level_beginner/intermediate/advanced.md` | Адаптация под уровень пользователя |
| Layer 3 — SD | `prompt_sd_green/yellow/orange/red/blue/purple.md` | Состояние по Спиральной Динамике |
| Layer 4 — RAG | Контекст из ChromaDB / [`retriever.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/retriever.py) | Знания базы данных |
| **Layer 5 — Mode** | **`prompt_mode_informational.md` (создать)** | **Режимный override** |

Порядок сборки при `curious`-состоянии:

```
[base] + [user_level] + [mode_informational] + [RAG]
```

Mode-слой (Layer 5) **заменяет** SD-слой (Layer 3), но не удаляет остальные. Директива «говори коротко» из `prompt_system_base.md` перекрывается явной фразой внутри `prompt_mode_informational.md`. Файл `prompt_system_base.md` **не трогать**.

***

## Диагностика: два корневых дефекта

### Дефект 1 — `/llm-payload` возвращает HTTP 404

Эндпоинт [`/api/debug/session/{session_id}/llm-payload`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/api/debug_routes.py) реализован корректно.  Он ищет `llm_calls` в последнем трейсе сессии через [`session_store.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/api/session_store.py) и извлекает `system_prompt_blob_id` и `user_prompt_blob_id`. Проблема в том, что [`answer_adaptive.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_adaptive.py) и [`answer_graph_powered.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_graph_powered.py) **не записывают эти поля в трейс** — эндпоинт находит трейс, видит пустой `llm_calls = []` и выбрасывает 404.[^1][^2]

### Дефект 2 — Бот скупо отвечает в `curious`-состоянии

Маршрутизатор [`state_classifier.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/state_classifier.py) и [`fast_detector.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/fast_detector.py) уже умеют определять `curious`-состояние.  Однако файл `prompt_mode_informational.md` в директории `bot_agent/` **отсутствует** — для `curious` применяется только `prompt_system_base.md` с директивой «говори коротко», что противоречит цели «полноценный информационный ассистент».[^2]

***

## Задача 1 — Починить LLM Payload

### 1.1 Что читать перед реализацией

Агент обязан **прочитать следующие файлы** и найти в них конкретные места:

1. [`bot_agent/llm_answerer.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/llm_answerer.py) — найти метод, который формирует `messages[]` и вызывает OpenAI API
2. [`bot_agent/answer_adaptive.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_adaptive.py) — найти место вызова `store.save_trace(session_id, trace)`
3. [`bot_agent/answer_graph_powered.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_graph_powered.py) — найти аналогичное место
4. [`api/session_store.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/api/session_store.py) — убедиться в наличии метода `save_blob()` и понять его сигнатуру

### 1.2 Изменение в `llm_answerer.py`

В методе, который формирует `messages[]` перед вызовом OpenAI, добавить сохранение blob **до** вызова API, с обязательным `try/except` (graceful degradation):

```python
# ШАГ 1: Сформировать финальные строки промптов
system_prompt_text: str  # финальный system prompt со вставленными RAG-блоками
user_messages_text: str  # история диалога + текущий вопрос пользователя

# ШАГ 2: Сохранить как blob — с fallback при ошибке
try:
    system_blob_id = session_store.save_blob(system_prompt_text)
    user_blob_id = session_store.save_blob(user_messages_text)
    blob_error = None
except Exception as e:
    system_blob_id = None
    user_blob_id = None
    blob_error = f"blob_save_failed: {str(e)}"

# ШАГ 3: Сформировать объект трейс-записи
llm_call = {
    "step": "answer",
    "model": model_name,                          # имя модели (напр. "gpt-4o-mini")
    "system_prompt_blob_id": system_blob_id,       # None если ошибка
    "user_prompt_blob_id": user_blob_id,           # None если ошибка
    "system_prompt_preview": system_prompt_text[:300],   # всегда присутствует
    "user_prompt_preview": user_messages_text[:300],     # всегда присутствует
    "blob_error": blob_error,                      # None если всё ок
    "response_preview": "",                        # заполнить после получения ответа
    "tokens_used": 0,                              # заполнить после получения ответа
}

# ШАГ 4: Вызвать OpenAI API
response = openai_client.chat.completions.create(...)

# ШАГ 5: Дополнить объект после получения ответа
llm_call["response_preview"] = response.choices[^0].message.content[:300]
llm_call["tokens_used"] = response.usage.total_tokens
```

**Принцип:** если blob не сохранился — эндпоинт `/llm-payload` всё равно вернёт **HTTP 200** с `preview`-полями (300 символов) и флагом `blob_error`. Пользователь увидит частичные данные вместо 404.

### 1.3 Изменение в `answer_adaptive.py`

Найти место вызова `store.save_trace()`. Убедиться, что объект `trace` содержит поле `llm_calls` как **список** перед сохранением:

```python
# Убедиться что llm_calls добавляется ПЕРЕД save_trace
trace["llm_calls"] = trace.get("llm_calls", [])
trace["llm_calls"].append(llm_call)  # llm_call из llm_answerer.py

# Только после этого:
store.save_trace(session_id, trace)
```


### 1.4 Изменение в `answer_graph_powered.py`

**Повторить шаги 1.2–1.3 полностью** для graph-powered движка. Этот файл — альтернативный путь выполнения при включённом Knowledge Graph режиме, и без него Debug Panel будет работать лишь в половине случаев.[^1]

Проверить: в `answer_graph_powered.py` существует аналогичный вызов `session_store` или `store.save_trace()`. Если структура хранения трейса отличается — адаптировать под неё, но гарантировать присутствие `llm_calls` с теми же полями.

### 1.5 Что уже реализовано — не трогать

Эндпоинт [`api/debug_routes.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/api/debug_routes.py) уже возвращает правильную структуру ответа:

```json
{
  "session_id": "...",
  "turn_number": 3,
  "llm_calls": [
    {
      "step": "answer",
      "model": "gpt-4o-mini",
      "system_prompt": "Ты — помощник...\n\n[КОНТЕКСТ]\nБлок 1...",
      "user_prompt": "ИСТОРИЯ ДИАЛОГА:\nПользователь: ...\nБот: ...\n\nВОПРОС: ...",
      "response_preview": "...",
      "blob_error": null
    }
  ],
  "memory_snapshot": "..."
}
```

Фронтенд Web UI (секция «Полотно LLM» с треугольничками) тоже уже реализован. Данные должны просто появиться.[^2]

### 1.6 Критерии приёмки — Задача 1

- [ ] `GET /api/debug/session/{session_id}/llm-payload` → **HTTP 200** (не 404)
- [ ] `llm_calls` содержит минимум 1 элемент
- [ ] `system_prompt` (или `system_prompt_preview`) содержит текст ≥ 300 символов, включая вставленные RAG-блоки
- [ ] `user_prompt` (или `user_prompt_preview`) содержит историю диалога и текущий вопрос
- [ ] При умышленной ошибке `save_blob` — эндпоинт всё равно возвращает 200, `blob_error != null`, preview-поля присутствуют
- [ ] **Тест graph-режима:** при включённом Knowledge Graph `answer_graph_powered.py` → `/llm-payload` тоже возвращает 200 с данными
- [ ] В Web UI секция «Полотно LLM» раскрывается треугольничком и показывает текст промптов

***

## Задача 2 — Промпт для `curious`-состояния

### 2.1 Создать файл `prompt_mode_informational.md`

**Путь:** `bot_psychologist/bot_agent/prompt_mode_informational.md`

**Полное содержание файла:**

```markdown
Ты — информационный ассистент по системе Саламата Сарсекенова.

Пользователь задаёт вопрос из интереса: хочет понять концепцию, разобраться в теме,
получить структурированное объяснение.

ВАЖНО: Для информационных запросов директивы краткости из базовых инструкций
НЕ применяются. Давай ответ настолько полный, насколько требует тема.

Твоя задача:
- дать развёрнутый, точный ответ на вопрос
- опираться на материалы из базы знаний (они предоставлены ниже в контексте)
- структурировать ответ логично: сначала суть, потом детали, потом примеры если есть
- использовать абзацы и нумерацию когда это помогает понять
- говорить своими словами — не копировать куски текста дословно

Стиль:
- живой, но точный
- без лишних вводных ("Отличный вопрос!", "Конечно!")
- без психологического зондирования и вопросов в конце
- длина ответа — столько, сколько нужно для полного понимания темы

Если в базе знаний нет точного ответа — скажи об этом прямо и ответь
на основе общего понимания системы.
```


### 2.2 Зарегистрировать в `runtime_config.py`

В файле [`bot_agent/runtime_config.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/runtime_config.py) найти словарь `EDITABLE_PROMPTS` (или его аналог) и добавить запись:[^1]

```python
"prompt_mode_informational": {
    "label": "Режим: Информационный (curious)",
    "file": "prompt_mode_informational.md",
    "group": "prompts",
    "description": "Применяется когда user_state == 'curious'. Перекрывает SD-слой.",
},
```

После этого промпт появится в **Admin Panel → Промпты** как отдельный редактируемый пункт без деплоя.

### 2.3 Добавить `ModePromptResolver` в `answer_adaptive.py`

Это расширяемый паттерн для всех будущих mode-промптов. Создать в начале файла словарь и функцию:

```python
# ── Mode Prompt Resolver ──────────────────────────────────────────────────
# Добавление нового режима — одна строка в словарь, ничего больше не менять
MODE_PROMPT_MAP: dict[str, str] = {
    "curious": "prompt_mode_informational",
    # "creative":   "prompt_mode_creative",    # пример будущего расширения
    # "crisis":     "prompt_mode_crisis",      # пример будущего расширения
}

def resolve_mode_prompt(user_state: str, config) -> str | None:
    """
    Возвращает текст mode-промпта для данного состояния.
    Возвращает None если для состояния нет mode-override —
    в этом случае используется стандартный SD-промпт.
    """
    prompt_key = MODE_PROMPT_MAP.get(user_state)
    if prompt_key is None:
        return None
    prompt_text = config.get_prompt(prompt_key)
    return prompt_text if prompt_text else None
# ─────────────────────────────────────────────────────────────────────────
```


### 2.4 Подключить в основной логике `answer_adaptive.py`

Найти место где выбирается системный промпт перед отправкой в LLM. Заменить/расширить логику выбора:

```python
# Существующая логика SD (не менять):
if sd_level == "GREEN":
    sd_prompt = config.get_prompt("prompt_sd_green")
elif sd_level == "YELLOW":
    sd_prompt = config.get_prompt("prompt_sd_yellow")
elif sd_level == "ORANGE":
    sd_prompt = config.get_prompt("prompt_sd_orange")
elif sd_level == "RED":
    sd_prompt = config.get_prompt("prompt_sd_red")
elif sd_level == "BLUE":
    sd_prompt = config.get_prompt("prompt_sd_blue")
elif sd_level == "PURPLE":
    sd_prompt = config.get_prompt("prompt_sd_purple")
else:
    sd_prompt = ""

# НОВОЕ: Mode-override для curious и будущих режимов
mode_prompt = resolve_mode_prompt(user_state, config)

if mode_prompt:
    # Mode перекрывает SD-слой. Base и user_level остаются.
    final_system_prompt = base_prompt + "\n\n" + user_level_prompt + "\n\n" + mode_prompt
    informational_mode = True
else:
    # Стандартный путь — SD-промпт как обычно
    final_system_prompt = base_prompt + "\n\n" + user_level_prompt + "\n\n" + sd_prompt
    informational_mode = False
```

**Критически важно:** `prompt_system_base.md` остаётся первым и неизменным. `prompt_mode_informational.md` добавляется **после** base и содержит внутри явную фразу-override для length-директив.[^1]

### 2.5 Добавить флаг `informational_mode` в трейс

В объект `trace` перед вызовом `store.save_trace()` добавить поле:

```python
trace["informational_mode"] = informational_mode   # True / False
trace["user_state"] = user_state                   # "curious" / "anxious" / etc.
trace["applied_mode_prompt"] = "prompt_mode_informational" if informational_mode else None
```

Это позволяет в Debug Panel видеть какой именно промпт был применён к каждому запросу.

### 2.6 Критерии приёмки — Задача 2

- [ ] При запросе с `state=curious` бот даёт ответ из **3+ абзацев** или нумерованный список
- [ ] `GET /llm-payload` при curious-запросе: в `system_prompt` виден текст из `prompt_mode_informational.md`
- [ ] В трейсе: `informational_mode == true` при curious-запросе
- [ ] В трейсе: `informational_mode == false` при не-curious запросе (тревога, конфликт, горе, нейтральный)
- [ ] В трейсе: `applied_mode_prompt == "prompt_mode_informational"` при curious-запросе
- [ ] Admin Panel → Промпты: пункт «Режим: Информационный (curious)» присутствует и редактируется без деплоя
- [ ] **Регрессия SD:** при `state=anxious/conflict/grief/green/yellow/etc.` — `resolve_mode_prompt()` возвращает `None`, применяется соответствующий `prompt_sd_*.md`, поведение не изменилось

***

## Полный порядок выполнения для агента

```
=== ФАЗА 1: ЧТЕНИЕ (обязательно перед любыми изменениями) ===

1. Читать llm_answerer.py
   → найти метод вызова OpenAI API
   → найти место формирования system_prompt и messages[]
   → зафиксировать имена переменных

2. Читать answer_adaptive.py
   → найти место выбора SD-промпта
   → найти вызов store.save_trace()
   → проверить есть ли уже поле llm_calls в trace

3. Читать answer_graph_powered.py
   → найти аналогичную структуру
   → зафиксировать отличия от answer_adaptive.py

4. Читать api/session_store.py
   → убедиться в наличии save_blob()
   → понять возвращаемый тип (строка ID или иное)

5. Читать bot_agent/runtime_config.py
   → найти EDITABLE_PROMPTS или аналог
   → понять формат существующих записей

=== ФАЗА 2: РЕАЛИЗАЦИЯ ЗАДАЧИ 1 (LLM Payload) ===

6. llm_answerer.py:
   → добавить save_blob() в try/except
   → сформировать объект llm_call с blob_id, preview, blob_error

7. answer_adaptive.py:
   → убедиться что trace["llm_calls"] формируется и передаётся в save_trace()

8. answer_graph_powered.py:
   → повторить шаг 7

=== ФАЗА 3: ТЕСТ ЗАДАЧИ 1 ===

9. Отправить тестовый запрос боту
10. GET /api/debug/session/{session_id}/llm-payload
    → ожидать HTTP 200
    → проверить llm_calls[^0].system_prompt_preview содержит текст
11. Включить Knowledge Graph режим, отправить запрос
    → GET /llm-payload → HTTP 200

=== ФАЗА 4: РЕАЛИЗАЦИЯ ЗАДАЧИ 2 (Curious Mode) ===

12. Создать файл bot_agent/prompt_mode_informational.md (текст из раздела 2.1)

13. runtime_config.py:
    → добавить запись в EDITABLE_PROMPTS (раздел 2.2)

14. answer_adaptive.py:
    → добавить MODE_PROMPT_MAP и resolve_mode_prompt() (раздел 2.3)
    → добавить ветку mode-override в логику выбора промпта (раздел 2.4)
    → добавить informational_mode + applied_mode_prompt в trace (раздел 2.5)

=== ФАЗА 5: ТЕСТ ЗАДАЧИ 2 ===

15. Отправить запрос с state=curious
    → ответ бота: 3+ абзаца
    → /llm-payload: system_prompt содержит текст из prompt_mode_informational.md
    → trace: informational_mode == true

16. Отправить запрос с state=anxious (или любым SD-состоянием)
    → ответ бота: стандартное поведение (короткий, эмпатичный)
    → trace: informational_mode == false

17. Открыть Admin Panel → Промпты
    → проверить наличие пункта "Режим: Информационный (curious)"
    → изменить текст → сохранить → отправить curious-запрос
    → убедиться что изменение применилось без рестарта
```


***

## Таблица файлов

| Файл | Действие | Что именно |
| :-- | :-- | :-- |
| [`bot_agent/llm_answerer.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/llm_answerer.py) | **Изменить** | `save_blob` в `try/except`, объект `llm_call` с blob_id + preview + blob_error |
| [`bot_agent/answer_adaptive.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_adaptive.py) | **Изменить** | `MODE_PROMPT_MAP`, `resolve_mode_prompt()`, mode-ветка, `informational_mode` в трейс |
| [`bot_agent/answer_graph_powered.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_graph_powered.py) | **Изменить** | Аналог `llm_answerer.py` — blob_id в трейс |
| [`bot_agent/prompt_mode_informational.md`](https://github.com/Askhat-cmd/Text_transcription/tree/main/bot_psychologist/bot_agent) | **Создать** | Новый файл, текст из раздела 2.1 |
| [`bot_agent/runtime_config.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/runtime_config.py) | **Изменить** | Добавить запись в `EDITABLE_PROMPTS` |

**Файлы — НЕ ТРОГАТЬ:**


| Файл | Причина |
| :-- | :-- |
| [`api/debug_routes.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/api/debug_routes.py) | Эндпоинт корректен, проблема не в нём |
| [`bot_agent/prompt_system_base.md`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/prompt_system_base.md) | Базовый промпт — override делается через mode-файл |
| `bot_agent/prompt_sd_*.md` (все 6) | SD-слой не меняется, только добавляется обход |
| [`api/session_store.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/api/session_store.py) | Только читать для понимания `save_blob()` |
| [`bot_agent/state_classifier.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/state_classifier.py) | Маршрутизатор уже корректно определяет `curious` |
| [`bot_agent/fast_detector.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/fast_detector.py) | Детектор уже корректен |


***

## Ожидаемый результат

После успешного выполнения всех задач система работает так:

- **Debug Panel** полностью функциональна: `/llm-payload` возвращает полный system prompt со вставленными RAG-блоками и историю диалога для любого запроса, в обоих движках ответов.[^2][^1]
- **Curious-режим** даёт развёрнутые структурированные ответы, не нарушая работу ни одного из 6 SD-состояний.
- **Архитектура масштабируема:** добавление нового режима в будущем — одна строка в `MODE_PROMPT_MAP` плюс создание `prompt_mode_*.md` файла.
- **Admin Panel** позволяет редактировать информационный промпт без деплоя.[^1]
- **Отказоустойчивость:** если blob-хранилище недоступно, бот продолжает отвечать, а Debug Panel показывает preview-данные с флагом `blob_error`.


