# PRD-004 — Memory Context Integrity & LLM Observability

**Версия:** 1.0.0  
**Дата:** 2026-04-09  
**Статус:** READY FOR IMPLEMENTATION  
**Базовый коммит:** `479e513` (feat(prd-003): fix sse stream assembly and add telegram adapter)  
**Автор аудита:** AI Review  

---

## 1. Контекст и обоснование

### 1.1 Предпосылки

После выполнения PRD-003 (SSE fix + Telegram adapter) система прошла live-тестирование из 5 туров диалога. Анализ логов `bot.log`, `retrieval.log`, `bot_agent.log` и трейса `llm-payload` (полотно LLM) выявил три группы проблем:

1. **Обрезание истории диалога** — при переходе на SUMMARY-режим (≥5 туров) `hybridquery` стал *короче*, чем на туре 4, хотя истории накопилось больше. Это указывает на ошибку в логике сборки контекста для промпта.
2. **Непрозрачность LLM-payload** — эндпойнт `/api/debug/session/{id}/llm-payload` возвращает плоский текст без структуры. Разработчик не видит, какая секция промпта сколько занимает токенов и что именно передаётся в `RECENT DIALOG`.
3. **Двойная запись в SQLite** — `MEMORY saved` фиксируется дважды до `addturn` при каждом запросе, создавая избыточную I/O нагрузку.

### 1.2 Данные из логов (доказательная база)

| Тур | `hybridquery len` | `CONVMEMORY turns` | `response time` | Событие |
|-----|-------------------|--------------------|-----------------|---------|
| 1   | 356               | 0                  | 24.61s          | первый запрос |
| 2   | 668               | 1                  | 20.07s          | история 1 тур |
| 3   | 877               | 2                  | 18.13s          | история 2 тура |
| 4   | 1081              | 3                  | 25.22s          | история 3 тура |
| 5   | **985** ⚠️        | 4                  | 24.54s          | **SUMMARY сгенерирован, query СОКРАТИЛСЯ** |

Падение `hybridquery len` с 1081 → 985 при росте истории — прямое свидетельство бага в `build_hybrid_query`.

Дополнительно на туре 5 зафиксировано:
```
SUMMARY generated len=424 chars turn5
OpenAI gpt-5-mini maxcompletiontokens  ← второй LLM-вызов
```
Второй синхронный вызов к LLM для генерации SUMMARY — причина деградации latency (+6s).

---

## 2. Цели и охват

### 2.1 Цели PRD-004

- **GOAL-1:** Восстановить целостность контекста диалога — SUMMARY должен корректно входить в промпт, не вытесняя `RECENT DIALOG`.
- **GOAL-2:** Сделать LLM-payload полностью прозрачным для разработчика — структурированный JSON с именами секций, символьными и токенными размерами.
- **GOAL-3:** Устранить двойную запись в SQLite.
- **GOAL-4:** Вынести генерацию SUMMARY в асинхронный фоновый task для восстановления latency.

### 2.2 Вне охвата

- Изменение модели LLM или провайдера
- Изменение структуры базы данных SQLite (только оптимизация записи)
- Изменения в Telegram-адаптере (покрыто PRD-003)
- Изменения в retrieval pipeline (Voyage reranker, confidence scorer)

---

## 3. Технические требования

### 3.1 FIX-4 — Целостность контекста при переходе на SUMMARY

#### 3.1.1 Диагноз

Файл: `bot_psychologist/bot_agent/conversation_memory.py`  
Метод: `build_context_for_prompt()` (или аналог по результатам `grep`)

Проблема в том, что при генерации SUMMARY на туре N:
- SUMMARY записывается в SQLite
- Но в **текущем запросе** метод `build_context_for_prompt` уже отработал без SUMMARY
- На следующем туре N+1 SUMMARY подхватывается, но при этом `RECENT DIALOG` обрезается до N-window реплик **без учёта** того, что SUMMARY уже покрывает ранние туры
- В результате: ни полная история, ни SUMMARY+window не формируют корректный контекст

#### 3.1.2 Требуемое поведение

Логика сборки промпта должна работать по следующей схеме:

```
if summary exists AND turns > SUMMARY_WINDOW_SIZE:
    context = [SUMMARY_BLOCK] + recent_turns[-RECENT_WINDOW:]
else:
    context = all_turns
```

Где:
- `SUMMARY_WINDOW_SIZE` = 5 (настраивается через `.env`)
- `RECENT_WINDOW` = 4 (настраивается через `.env`)
- `SUMMARY_BLOCK` — отдельная именованная секция промпта с меткой `[CONVERSATION SUMMARY]`

#### 3.1.3 Требования к реализации

**R-4.1:** При наличии SUMMARY в БД — он ОБЯЗАН входить в промпт как отдельная секция перед `RECENT DIALOG`.

**R-4.2:** `RECENT DIALOG` после активации SUMMARY-режима должен содержать строго последние `RECENT_WINDOW` реплик (не меньше, не больше).

**R-4.3:** `hybridquery` при наличии SUMMARY должен включать первые 200 символов SUMMARY + последние 2 реплики пользователя. Длина `hybridquery` не должна *сокращаться* при росте истории.

**R-4.4:** Добавить в лог при каждом запросе:
```
CONTEXT_BUILD mode=summary|full summary_len=N recent_turns=N total_prompt_chars=N
```

#### 3.1.4 Пример структуры промпта после фикса

```
[SYSTEM PROMPT - Core Identity]
...
[CONVERSATION SUMMARY]
Пользователь обратился с темой тревоги перед встречей. Обсудили ...

[RECENT DIALOG]
- user: А если это повторится?
- bot: ...
- user: Можешь подсказать упражнение?
- bot: ...

[TASK INSTRUCTION]
...
```

---

### 3.2 FIX-5 — Структурированный LLM-payload эндпойнт

#### 3.2.1 Диагноз

Файл: `bot_psychologist/api/routes.py` или `debug_routes.py`  
Эндпойнт: `GET /api/debug/session/{session_id}/llm-payload`

Текущий ответ — плоская строка с промптом. Разработчик не может:
- Увидеть, что именно попало в `RECENT DIALOG`
- Понять, был ли передан SUMMARY
- Узнать размер каждой секции в токенах
- Найти причину аномального поведения LLM

#### 3.2.2 Новая схема ответа

Эндпойнт должен возвращать структурированный JSON:

```json
{
  "session_id": "15b8e375-...",
  "turn_index": 5,
  "context_mode": "summary",
  "total_chars": 4821,
  "total_tokens_est": 1205,
  "sections": [
    {
      "name": "CORE_IDENTITY",
      "chars": 312,
      "tokens_est": 78,
      "content": "You are Neo MindBot..."
    },
    {
      "name": "CONVERSATION_SUMMARY",
      "chars": 424,
      "tokens_est": 106,
      "present": true,
      "content": "Пользователь обратился с темой..."
    },
    {
      "name": "RECENT_DIALOG",
      "chars": 680,
      "tokens_est": 170,
      "turns_count": 4,
      "content": "- user: ...\n- bot: ..."
    },
    {
      "name": "KNOWLEDGE_CONTEXT",
      "chars": 1240,
      "tokens_est": 310,
      "blocks_count": 3,
      "content": "..."
    },
    {
      "name": "TASK_INSTRUCTION",
      "chars": 290,
      "tokens_est": 72,
      "content": "..."
    }
  ],
  "retrieval_blocks": [
    {"block_id": "46d62...", "title": "...", "score": 0.4844}
  ],
  "diagnostics": {
    "summary_present": true,
    "summary_lag": false,
    "recent_dialog_turns": 4,
    "hybridquery_len": 985,
    "hybridquery_text": "..."
  }
}
```

#### 3.2.3 Требования к реализации

**R-5.1:** Промпт-сборщик (`prompt_builder.py` или аналог) должен возвращать не строку, а объект `PromptPayload` с именованными секциями.

**R-5.2:** Оценка токенов — через `len(text) // 4` (быстрая эвристика, не требует tiktoken).

**R-5.3:** Поле `diagnostics.summary_lag` = `true`, если SUMMARY был сгенерирован на текущем туре, но ещё **не вошёл** в промпт (lag-1 ситуация). Это поле должно логироваться как WARNING.

**R-5.4:** Эндпойнт `/api/debug/session/{id}/llm-payload` сохраняет обратную совместимость: при добавлении query-параметра `?format=flat` возвращает старый плоский текст.

---

### 3.3 FIX-6 — Устранение двойной записи в SQLite

#### 3.3.1 Диагноз

Файл: `bot_psychologist/bot_agent/conversation_memory.py`

Паттерн в логах при каждом туре:
```
MEMORY saved turns=N    ← ЛИШНИЙ вызов (до addturn)
MEMORY saved turns=N    ← ЛИШНИЙ вызов (после старта LLM, до ответа)
MEMORY addturn turnsbefore=N
MEMORY turnadded turnindex=N+1
MEMORY saved turns=N+1  ← ЕДИНСТВЕННЫЙ нужный вызов
```

Два первых `save` — артефакт промежуточных `await memory.save()` вызовов в pipeline, которые сохраняют состояние *до* фактического добавления нового тура.

#### 3.3.2 Требования к реализации

**R-6.1:** `memory.save()` вызывается **строго один раз** — после успешного `addturn()`. Все промежуточные `save()` в pipeline убираются.

**R-6.2:** Если промежуточный `save()` был нужен для персистенции на случай краша — заменить на `memory.checkpoint()` с флагом `dirty=True` без фактической записи на диск. Реальная запись происходит только в `addturn()` или при graceful shutdown.

**R-6.3:** Добавить в лог:
```
MEMORY save userid={id} turns={N} reason=addturn|checkpoint|shutdown
```

---

### 3.4 FIX-7 — Асинхронная генерация SUMMARY

#### 3.4.1 Диагноз

Файл: `bot_psychologist/bot_agent/conversation_memory.py`  
Метод: `Updating conversation summary turn N`

Генерация SUMMARY происходит **синхронно** после записи тура, до отправки ответа пользователю. Это добавляет второй LLM-вызов (~2-3 секунды) в критический путь ответа.

Из лога:
```
13:27:09 INFO MEMORY saved turns=5
13:27:10 INFO OpenAI gpt-5-mini maxcompletiontokens  ← SUMMARY LLM call
13:27:12 INFO SUMMARY generated len=424 chars turn5
13:27:12 INFO ADAPTIVE response ready in 24.54s
```

#### 3.4.2 Требования к реализации

**R-7.1:** Генерация SUMMARY выносится в `asyncio.create_task()` — не блокирует основной поток ответа.

**R-7.2:** SUMMARY-task стартует **после** того как основной ответ уже сформирован и отправлен пользователю (SSE stream завершён).

**R-7.3:** При ошибке SUMMARY-task — логировать WARNING, но не роняющий основной pipeline.

**R-7.4:** Добавить в лог при старте task:
```
SUMMARY_TASK scheduled turn={N} user_id={id} (background)
```
И при завершении:
```
SUMMARY_TASK done turn={N} len={chars} elapsed={ms}ms
```

**R-7.5 (lag-1 документация):** В `diagnostics` поле `summary_lag` = `true` когда SUMMARY был сгенерирован на туре N, но в промпт войдёт только на туре N+1. Это **ожидаемое поведение** и оно документируется, а не лечится.

---

## 4. Затрагиваемые файлы

Для точных путей выполнить в корне репозитория перед началом работы:

```bash
# Найти файл сборки контекста/промпта
grep -r "RECENT DIALOG\|build_context\|build_hybrid_query\|PromptBuilder\|prompt_builder" \
  bot_psychologist/bot_agent/ --include="*.py" -l

# Найти файл conversation_memory
grep -r "MEMORY saved\|addturn\|SUMMARY generated" \
  bot_psychologist/bot_agent/ --include="*.py" -l

# Найти llm-payload эндпойнт
grep -r "llm-payload\|llm_payload" \
  bot_psychologist/api/ --include="*.py" -l
```

**Ожидаемые файлы (предположительно):**

| Файл | FIX |
|------|-----|
| `bot_agent/conversation_memory.py` | FIX-4, FIX-6, FIX-7 |
| `bot_agent/answer_adaptive.py` | FIX-4 (build_hybrid_query) |
| `bot_agent/prompt_builder.py` (или аналог) | FIX-4, FIX-5 |
| `api/routes.py` или `api/debug_routes.py` | FIX-5 |

---

## 5. Тест-план

### 5.1 Unit-тесты

#### T1 — Context build в режиме SUMMARY

**Файл:** `tests/test_conversation_memory.py`  
**Приоритет:** 🔴 CRITICAL

```python
# test_context_summary_mode
def test_context_includes_summary_before_recent_dialog():
    """
    При наличии SUMMARY и turns >= SUMMARY_WINDOW_SIZE
    сборщик контекста должен вернуть:
    1. Секцию [CONVERSATION SUMMARY] с непустым текстом
    2. Секцию [RECENT DIALOG] с <= RECENT_WINDOW репликами
    3. Общая длина контекста НЕ МЕНЬШЕ длины предыдущего тура
    """
    memory = ConversationMemory(user_id="test-user")
    # Добавляем 6 туров
    for i in range(6):
        memory.add_turn(user=f"user message {i}", bot=f"bot response {i}")
    memory.set_summary("Пользователь обсудил темы тревоги и самооценки.")
    
    context = memory.build_context_for_prompt()
    
    assert "[CONVERSATION SUMMARY]" in context
    assert "Пользователь обсудил" in context
    # RECENT DIALOG содержит не более RECENT_WINDOW реплик
    dialog_section = extract_section(context, "RECENT DIALOG")
    turns_in_dialog = dialog_section.count("- user:")
    assert turns_in_dialog <= memory.RECENT_WINDOW
    assert turns_in_dialog >= 2  # минимум 2 реплики для связности

def test_context_full_mode_without_summary():
    """
    При отсутствии SUMMARY и turns < SUMMARY_WINDOW_SIZE
    контекст содержит все реплики без SUMMARY-секции
    """
    memory = ConversationMemory(user_id="test-user")
    for i in range(3):
        memory.add_turn(user=f"user {i}", bot=f"bot {i}")
    
    context = memory.build_context_for_prompt()
    
    assert "[CONVERSATION SUMMARY]" not in context
    assert context.count("- user:") == 3
```

#### T2 — hybridquery не сокращается при росте истории

**Файл:** `tests/test_answer_adaptive.py`  
**Приоритет:** 🔴 CRITICAL

```python
def test_hybridquery_len_does_not_decrease_after_summary():
    """
    Регрессионный тест на баг из логов:
    hybridquery на туре 5 (с SUMMARY) не должен быть короче,
    чем на туре 4 (без SUMMARY)
    """
    queries = []
    agent = AdaptiveAnswerAgent()
    
    for i in range(5):
        query = agent.build_hybrid_query(
            user_query=f"вопрос номер {i}",
            turns=i,
            summary="Краткое резюме диалога." if i >= 4 else None
        )
        queries.append(len(query))
    
    # Длина не должна сократиться при переходе на SUMMARY-режим
    for i in range(1, len(queries)):
        assert queries[i] >= queries[i-1] * 0.9, (
            f"hybridquery сократился на туре {i+1}: "
            f"{queries[i]} < {queries[i-1]}"
        )

def test_hybridquery_includes_summary_text():
    """
    При наличии SUMMARY он включается в hybridquery
    """
    agent = AdaptiveAnswerAgent()
    summary_text = "Пользователь обсудил тревогу перед выступлением."
    
    query = agent.build_hybrid_query(
        user_query="как справиться?",
        turns=5,
        summary=summary_text
    )
    
    assert summary_text[:100] in query or "тревогу" in query
```

#### T3 — Двойная запись в SQLite

**Файл:** `tests/test_conversation_memory.py`  
**Приоритет:** 🟡 MEDIUM

```python
def test_single_save_per_turn(mocker):
    """
    При обработке одного запроса save() должен вызываться
    строго один раз с reason=addturn
    """
    memory = ConversationMemory(user_id="test-user")
    save_spy = mocker.spy(memory, '_persist_to_db')
    
    memory.add_turn(user="привет", bot="добрый день")
    
    # Только один реальный save
    assert save_spy.call_count == 1
    call_kwargs = save_spy.call_args_list[0][1]
    assert call_kwargs.get('reason') == 'addturn'

def test_save_reasons_logged(caplog):
    """
    Каждый save() логирует reason
    """
    import logging
    memory = ConversationMemory(user_id="test-user")
    
    with caplog.at_level(logging.INFO, logger="botagent.conversationmemory"):
        memory.add_turn(user="тест", bot="ответ")
    
    save_logs = [r for r in caplog.records if "MEMORY save" in r.message]
    assert len(save_logs) == 1
    assert "reason=addturn" in save_logs[0].message
```

#### T4 — Асинхронность SUMMARY-task

**Файл:** `tests/test_conversation_memory.py`  
**Приоритет:** 🟡 MEDIUM

```python
import asyncio
from unittest.mock import AsyncMock, patch

async def test_summary_generated_as_background_task(mocker):
    """
    Генерация SUMMARY не блокирует основной pipeline:
    add_turn() должен вернуться до завершения SUMMARY-генерации
    """
    summary_started = asyncio.Event()
    summary_done = asyncio.Event()
    
    async def slow_summary_generator(*args, **kwargs):
        summary_started.set()
        await asyncio.sleep(0.1)  # имитация LLM-вызова
        summary_done.set()
        return "Generated summary."
    
    memory = ConversationMemory(user_id="test-async")
    mocker.patch.object(memory, '_generate_summary_via_llm', slow_summary_generator)
    
    # Добавляем SUMMARY_WINDOW_SIZE туров для триггера
    for i in range(memory.SUMMARY_WINDOW_SIZE):
        await memory.add_turn_async(user=f"msg {i}", bot=f"resp {i}")
    
    # add_turn_async должен вернуться ДО завершения summary
    assert summary_started.is_set()   # task запущен
    assert not summary_done.is_set()  # но ещё не завершён
    
    await asyncio.sleep(0.2)  # ждём завершения
    assert summary_done.is_set()

async def test_summary_task_failure_does_not_crash_pipeline(mocker):
    """
    Ошибка в SUMMARY-task не должна ронять основной pipeline
    """
    async def failing_summary(*args, **kwargs):
        raise RuntimeError("LLM timeout")
    
    memory = ConversationMemory(user_id="test-fail")
    mocker.patch.object(memory, '_generate_summary_via_llm', failing_summary)
    
    for i in range(memory.SUMMARY_WINDOW_SIZE):
        await memory.add_turn_async(user=f"msg {i}", bot=f"resp {i}")
    
    await asyncio.sleep(0.1)
    # Память должна быть сохранена даже при ошибке SUMMARY
    assert memory.turns_count == memory.SUMMARY_WINDOW_SIZE
```

---

### 5.2 Unit-тесты LLM-payload эндпойнта

#### T5 — Структура ответа llm-payload

**Файл:** `tests/test_debug_routes.py`  
**Приоритет:** 🔴 CRITICAL

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_llm_payload_returns_structured_json(mock_session_with_5_turns):
    """
    GET /api/debug/session/{id}/llm-payload возвращает структурированный JSON
    со всеми обязательными полями
    """
    session_id = mock_session_with_5_turns.session_id
    response = client.get(
        f"/api/debug/session/{session_id}/llm-payload",
        headers={"X-API-Key": "dev-key-001"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Верхний уровень
    assert "session_id" in data
    assert "turn_index" in data
    assert "context_mode" in data  # "full" или "summary"
    assert "total_chars" in data
    assert "total_tokens_est" in data
    assert "sections" in data
    assert "diagnostics" in data

def test_llm_payload_sections_have_required_fields(mock_session_with_5_turns):
    """
    Каждая секция содержит name, chars, tokens_est, content
    """
    session_id = mock_session_with_5_turns.session_id
    response = client.get(f"/api/debug/session/{session_id}/llm-payload",
                         headers={"X-API-Key": "dev-key-001"})
    data = response.json()
    
    required_section_fields = {"name", "chars", "tokens_est", "content"}
    for section in data["sections"]:
        assert required_section_fields.issubset(set(section.keys())), \
            f"Секция {section.get('name')} не содержит обязательных полей"

def test_llm_payload_summary_section_present_when_exists(mock_session_with_summary):
    """
    При наличии SUMMARY в памяти — секция CONVERSATION_SUMMARY присутствует
    в ответе и не пустая
    """
    session_id = mock_session_with_summary.session_id
    response = client.get(f"/api/debug/session/{session_id}/llm-payload",
                         headers={"X-API-Key": "dev-key-001"})
    data = response.json()
    
    summary_sections = [s for s in data["sections"] 
                        if s["name"] == "CONVERSATION_SUMMARY"]
    assert len(summary_sections) == 1
    assert summary_sections[0]["chars"] > 0
    assert summary_sections[0]["content"] != ""
    assert data["diagnostics"]["summary_present"] is True

def test_llm_payload_flat_format_backward_compat(mock_session_with_5_turns):
    """
    При ?format=flat возвращается плоская строка (обратная совместимость)
    """
    session_id = mock_session_with_5_turns.session_id
    response = client.get(
        f"/api/debug/session/{session_id}/llm-payload?format=flat",
        headers={"X-API-Key": "dev-key-001"}
    )
    assert response.status_code == 200
    # flat format — Content-Type text/plain или JSON со строкой
    data = response.json()
    assert isinstance(data, str) or "raw_prompt" in data

def test_llm_payload_diagnostics_summary_lag(mock_session_summary_just_generated):
    """
    diagnostics.summary_lag = true когда SUMMARY сгенерирован
    на текущем туре но ещё не вошёл в промпт
    """
    session_id = mock_session_summary_just_generated.session_id
    response = client.get(f"/api/debug/session/{session_id}/llm-payload",
                         headers={"X-API-Key": "dev-key-001"})
    data = response.json()
    
    assert data["diagnostics"]["summary_lag"] is True
```

---

### 5.3 Интеграционные тесты

#### T6 — End-to-end: контекст через 7 туров

**Файл:** `tests/integration/test_memory_e2e.py`  
**Приоритет:** 🔴 CRITICAL

```python
import pytest

@pytest.mark.integration
async def test_context_integrity_over_7_turns(live_api_client):
    """
    Интеграционный тест: 7 туров диалога.
    На каждом туре проверяем что hybridquery не сокращается
    и что payload корректен.
    """
    session = await live_api_client.create_session()
    prev_query_len = 0
    
    messages = [
        "Привет! У меня тревога перед важной встречей.",
        "Это повторяется уже третий раз.",
        "Что ты можешь посоветовать?",
        "Как мне успокоиться прямо сейчас?",
        "Можешь объяснить про дыхание подробнее?",
        "А если не помогает?",
        "Спасибо, попробую применить."
    ]
    
    for turn_idx, message in enumerate(messages):
        response = await live_api_client.send_message(session.id, message)
        assert response.status_code == 200
        
        # Получаем payload
        payload = await live_api_client.get_llm_payload(session.id)
        
        # hybridquery не должен сокращаться
        current_query_len = payload["diagnostics"]["hybridquery_len"]
        if turn_idx > 0:
            assert current_query_len >= prev_query_len * 0.85, (
                f"Turn {turn_idx+1}: hybridquery сократился "
                f"{prev_query_len} -> {current_query_len}"
            )
        prev_query_len = current_query_len
        
        # Начиная с тура 6 (index 5) должен быть SUMMARY
        if turn_idx >= 5:
            assert payload["context_mode"] == "summary"
            assert payload["diagnostics"]["summary_present"] is True
            summary_section = next(
                s for s in payload["sections"] 
                if s["name"] == "CONVERSATION_SUMMARY"
            )
            assert summary_section["chars"] > 100

@pytest.mark.integration  
async def test_response_latency_does_not_degrade_after_summary(live_api_client):
    """
    После генерации SUMMARY latency не должна вырастать > 30%
    относительно среднего по первым 4 турам
    """
    import time
    session = await live_api_client.create_session()
    latencies = []
    
    messages = [
        "Расскажи о тревоге.",
        "Почему это происходит?",
        "Как с этим работать?",
        "Есть конкретные упражнения?",
        "Покажи на примере.",  # тур 5 — триггер SUMMARY
        "Понял, спасибо.",
    ]
    
    for message in messages:
        start = time.monotonic()
        await live_api_client.send_message(session.id, message)
        latencies.append(time.monotonic() - start)
    
    avg_first_4 = sum(latencies[:4]) / 4
    avg_last_2 = sum(latencies[4:]) / 2
    
    assert avg_last_2 <= avg_first_4 * 1.3, (
        f"Latency после SUMMARY выросла: {avg_first_4:.1f}s -> {avg_last_2:.1f}s"
    )
```

#### T7 — Регрессионный тест: нет двойного save

**Файл:** `tests/integration/test_memory_e2e.py`  
**Приоритет:** 🟡 MEDIUM

```python
@pytest.mark.integration
async def test_no_double_save_in_logs(live_api_client, log_capture):
    """
    В логах для одного запроса присутствует строго одна строка
    'MEMORY save ... reason=addturn'
    """
    session = await live_api_client.create_session()
    
    with log_capture("botagent.conversationmemory") as logs:
        await live_api_client.send_message(session.id, "тест дублирования")
    
    save_records = [l for l in logs if "MEMORY save" in l and "reason=" in l]
    addturn_saves = [l for l in save_records if "reason=addturn" in l]
    
    assert len(addturn_saves) == 1, (
        f"Ожидался 1 save, найдено {len(addturn_saves)}: {addturn_saves}"
    )
```

---

### 5.4 Ручное тестирование (smoke-tests)

#### T8 — Smoke: полотно LLM в веб-интерфейсе

**Среда:** локальная (localhost:3000 / localhost:8000)  
**Предусловие:** запущен бот, проведён диалог из ≥ 5 туров

**Шаги:**
1. Открыть веб-чат, провести 6 туров диалога на тему тревоги.
2. Открыть Debug Panel → вкладка **LLM Payload**.
3. ✅ Должны быть видны все секции промпта: `CORE_IDENTITY`, `CONVERSATION_SUMMARY`, `RECENT_DIALOG`, `KNOWLEDGE_CONTEXT`, `TASK_INSTRUCTION`.
4. ✅ В секции `CONVERSATION_SUMMARY` — непустой текст (краткое изложение туров 1–2).
5. ✅ В секции `RECENT_DIALOG` — последние 4 реплики (не все 6).
6. ✅ Поле `total_tokens_est` — разумное число (500–2000).
7. ✅ `diagnostics.summary_present = true`.
8. ✅ `diagnostics.summary_lag = false` (SUMMARY уже вошёл в промпт).

**Ожидаемый результат:** разработчик видит полный структурированный дамп промпта.

#### T9 — Smoke: latency после SUMMARY

**Шаги:**
1. Открыть веб-чат, провести 6 туров.
2. Засечь время ответа на туре 5 и туре 6.
3. ✅ Время ответа на туре 6 не превышает время тура 5 более чем на 5 секунд.
4. Проверить лог: присутствует строка `SUMMARY_TASK scheduled ... (background)`.
5. ✅ Через 2–3 секунды после ответа — `SUMMARY_TASK done ...`.

---

## 6. Definition of Done (DoD)

- [ ] **R-4.1** — SUMMARY секция присутствует в промпте при `turns >= SUMMARY_WINDOW_SIZE`
- [ ] **R-4.2** — `RECENT DIALOG` содержит строго `RECENT_WINDOW` реплик в SUMMARY-режиме
- [ ] **R-4.3** — `hybridquery len` не сокращается при переходе в SUMMARY-режим (проверяется тестом T2)
- [ ] **R-4.4** — Лог содержит `CONTEXT_BUILD mode=...` на каждый запрос
- [ ] **R-5.1** — Промпт-сборщик возвращает `PromptPayload` объект с секциями
- [ ] **R-5.2** — Оценка токенов через `len // 4` в каждой секции
- [ ] **R-5.3** — Поле `diagnostics.summary_lag` корректно проставляется
- [ ] **R-5.4** — `?format=flat` возвращает плоский текст (обратная совместимость)
- [ ] **R-6.1** — `memory.save()` вызывается строго один раз с `reason=addturn`
- [ ] **R-6.3** — Лог содержит `reason=` при каждом save
- [ ] **R-7.1** — SUMMARY генерируется в `asyncio.create_task()`
- [ ] **R-7.2** — SUMMARY-task стартует после завершения SSE stream
- [ ] **R-7.3** — Ошибка SUMMARY-task не роняет pipeline
- [ ] **R-7.4** — Лог содержит `SUMMARY_TASK scheduled` и `SUMMARY_TASK done`
- [ ] Тесты T1–T7 проходят `pytest -m 'not integration'` (unit) и `pytest -m integration` (integration)
- [ ] Smoke T8 и T9 выполнены вручную и задокументированы
- [ ] Нет регрессий в существующих тестах (`tests_after.txt` baseline)

---

## 7. Порядок выполнения (волны)

### Волна 1 — Критические фиксы (FIX-4 + FIX-6)

> Цель: восстановить целостность контекста и устранить двойной save.

1. `grep`-диагностика: найти точные файлы (см. раздел 4)
2. Рефакторинг `conversation_memory.py`:
   - Убрать лишние `save()` вызовы
   - Добавить `reason=` в лог
3. Рефакторинг `build_context_for_prompt` / `build_hybrid_query`:
   - Включить SUMMARY в hybridquery
   - Добавить секцию `[CONVERSATION SUMMARY]` в промпт
4. Запустить тесты T1, T2, T3
5. Коммит: `fix(memory): restore context integrity and remove double save`

### Волна 2 — Observability (FIX-5)

> Цель: сделать llm-payload структурированным.

1. Создать/рефакторить `PromptPayload` dataclass
2. Обновить эндпойнт `/api/debug/session/{id}/llm-payload`
3. Запустить тесты T5
4. Smoke T8
5. Коммит: `feat(debug): structured llm-payload endpoint`

### Волна 3 — Performance (FIX-7)

> Цель: вынести SUMMARY-генерацию в background task.

1. Обернуть `_generate_summary_via_llm` в `asyncio.create_task()`
2. Добавить `SUMMARY_TASK scheduled/done` логи
3. Запустить тесты T4, T6 (latency)
4. Smoke T9
5. Коммит: `perf(memory): async summary generation to reduce latency`

---

## 8. Конфигурационные переменные (.env)

Добавить в `.env.example`:

```dotenv
# Memory context windows
SUMMARY_WINDOW_SIZE=5        # Тур, начиная с которого активируется SUMMARY-режим
RECENT_WINDOW=4              # Количество последних реплик в RECENT DIALOG при SUMMARY-режиме
SUMMARY_MAX_CHARS=600        # Максимальная длина SUMMARY в символах

# LLM Payload debug
LLM_PAYLOAD_INCLUDE_FULL_CONTENT=true   # false — обрезать content до 500 символов в ответе эндпойнта
```

---

## 9. Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|----------|
| SUMMARY-task падает при высокой нагрузке на LLM | Средняя | Низкое — lag-1 контекст | R-7.3: graceful degradation |
| Рефакторинг `build_context` ломает существующие тесты | Низкая | Высокое | Запустить `tests_after.txt` baseline перед мержем |
| PromptPayload объект несовместим с текущим форматом промпта | Средняя | Высокое | Сохранить `to_flat_string()` метод для fallback |
| asyncio.create_task теряется при graceful shutdown | Низкая | Низкое | Добавить `await pending_tasks` в shutdown handler |

---

*Конец документа PRD-004 v1.0.0*
