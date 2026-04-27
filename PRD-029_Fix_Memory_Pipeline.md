# PRD-029 — Fix Memory Pipeline in Multiagent Runtime

**Версия:** 1.0  
**Дата:** 2026-04-27  
**Статус:** READY FOR IMPLEMENTATION  
**Приоритет:** CRITICAL  
**Автор:** Perplexity AI (на основе анализа логов, истории чата и кода)

---

## Контекст и причина

После перехода на мультиагентную систему (`multiagent_v1`) перестали работать три ключевых компонента, которые корректно работали в каскадной системе:

1. **Бот не помнит имя и историю** — Writer не получает полноценный контекст диалога
2. **RAG всегда возвращает 0 блоков** — ChromaDB-поиск не работает, TF-IDF fallback тоже не активируется
3. **Каждый ход трактуется как `new_thread`** — история искусственно обрезается до 2 ходов

Доказательства из логов:
```
[CHROMA] Семантический поиск '...': 0 блоков  # все запросы
[CONV_MEMORY] cache_hit ... turns=2            # на 3-м ходу видит только 2
conversation.created                           # каждый ход — "новый разговор"
```

---

## Файлы для изменения

| Файл | Изменение |
|------|-----------|
| `bot_agent/multiagent/agents/memory_retrieval.py` | FIX 1 + FIX 2 |
| `bot_agent/multiagent/agents/memory_retrieval_config.py` | FIX 3 |
| `bot_agent/multiagent/agents/writer_agent_prompts.py` | FIX 4 (улучшение) |

---

## FIX 1 — Полноценный контекст памяти вместо плоских N ходов

**Файл:** `bot_agent/multiagent/agents/memory_retrieval.py`  
**Метод:** `_load_conversation()` (строки ~110-130)

### Проблема
Текущий код:
```python
@staticmethod
async def _load_conversation(user_id: str, n_turns: int) -> str:
    memory = get_conversation_memory(user_id=user_id)
    turns = memory.get_last_turns(n=n_turns)
    if not turns:
        return ""
    lines: list[str] = []
    for turn in turns:
        user_input = (turn.user_input or "").strip()
        bot_response = (turn.bot_response or "").strip()
        if user_input:
            lines.append(f"User: {user_input}")
        if bot_response:
            lines.append(f"Assistant: {bot_response}")
        lines.append("---")
    return "\n".join(lines)
```

Этот код игнорирует:
- `summary` диалога (если ходов > 10)
- `semantic_memory` (семантически похожие ходы из прошлого)
- `cross_session_context` (контекст предыдущих сессий)
- `get_adaptive_context_text()` — метод, который уже делает всё правильно

В старой каскадной системе (`bootstrap_runtime_helpers.py`, метод `_load_runtime_memory_context`) использовался:
```python
conversation_context = (
    memory_context_bundle.context_text
    or memory.get_adaptive_context_text(query)
)
```

### Решение — заменить метод целиком:
```python
@staticmethod
async def _load_conversation(user_id: str, n_turns: int, user_message: str = "") -> str:
    """
    Загружает полноценный контекст памяти через адаптивный метод ConversationMemory.

    Использует get_adaptive_context_text() — тот же метод, что и в каскадной системе.
    Он автоматически включает:
      - последние N ходов (short-term)
      - summary диалога (при > 10 ходах)
      - семантически релевантные ходы (semantic_memory)

    Параметр n_turns сохраняется для логирования и трейса,
    но реальная глубина управляется через config (CONVERSATION_HISTORY_DEPTH).
    """
    try:
        from ...conversation_memory import get_conversation_memory

        memory = get_conversation_memory(user_id=user_id)

        if not memory.turns:
            return ""

        # Используем адаптивный контекст — идентично каскадной системе
        context = memory.get_adaptive_context_text(user_message or "")

        if not context:
            # Fallback: хотя бы плоские последние ходы
            turns = memory.get_last_turns(n=n_turns)
            lines: list[str] = []
            for turn in turns:
                user_input = (turn.user_input or "").strip()
                bot_response = (turn.bot_response or "").strip()
                if user_input:
                    lines.append(f"User: {user_input}")
                if bot_response:
                    lines.append(f"Assistant: {bot_response}")
                lines.append("---")
            return "\n".join(lines)

        return context

    except Exception as exc:
        logger.warning("[MRA] conversation load error: %s", exc)
        return ""
```

### Также нужно обновить вызов `_load_conversation` в методе `assemble()`:

Найти строку:
```python
results = await asyncio.gather(
    self._load_conversation(user_id, n_turns),
    ...
```

Заменить на:
```python
results = await asyncio.gather(
    self._load_conversation(user_id, n_turns, user_message),
    ...
```

---

## FIX 2 — RAG: использовать глобальный синглтон retriever вместо нового ChromaLoader

**Файл:** `bot_agent/multiagent/agents/memory_retrieval.py`  
**Метод:** `_load_rag()` (строки ~150-195)

### Проблема
Текущий код создаёт **новый** инстанс `ChromaLoader()`:
```python
loader = ChromaLoader()
results = loader.query_blocks(query_text=query, top_k=RAG_N_RESULTS)
```

Новый инстанс:
1. Не имеет кэша `_query_endpoint_available` → делает HTTP запрос на `/api/query/`
2. Получает 404 (эндпоинт не реализован в Bot_data_base) → возвращает `[]`
3. TF-IDF fallback не активируется, потому что он живёт в `retriever.py`, а не в `ChromaLoader`

В старой каскадной системе RAG шёл через `retriever.py` → `get_retriever()` → TF-IDF/semantic search по уже загруженным 229 блокам.

### Решение — переписать `_load_rag()` для использования retriever:
```python
@staticmethod
async def _load_rag(query: str) -> list[SemanticHit]:
    """
    Семантический поиск по базе знаний.

    Использует глобальный retriever (TF-IDF + rerank) — идентично каскадной системе.
    ChromaLoader.query_blocks() намеренно НЕ используется: 
    эндпоинт /api/query/ не реализован в Bot_data_base, все 229 блоков 
    загружены через API и доступны только через retriever (TF-IDF индекс).
    """
    try:
        if not query.strip():
            return []

        # Используем тот же retriever что и каскадная система
        from ...retriever import get_retriever

        retriever = get_retriever()
        # retrieve возвращает List[Block] или List[Tuple[Block, score]]
        raw_results = retriever.retrieve(query, top_k=RAG_N_RESULTS)

        hits: list[SemanticHit] = []
        for item in raw_results:
            if isinstance(item, tuple) and len(item) >= 2:
                block, score = item[0], float(item[1] or 0.0)
            else:
                block = item
                score = 0.5  # TF-IDF не всегда возвращает score

            chunk_id = str(getattr(block, "block_id", ""))
            content = str(getattr(block, "content", "") or "")
            source = str(getattr(block, "document_title", "") or 
                        getattr(block, "source_type", "unknown"))

            if content:  # не добавляем пустые блоки
                hits.append(SemanticHit(
                    chunk_id=chunk_id,
                    content=content,
                    source=source,
                    score=score,
                ))

        logger.info("[MRA] rag hits=%d query='%s...'", len(hits), query[:50])
        return hits

    except Exception as exc:
        logger.warning("[MRA] rag load error: %s", exc)
        return []
```

**ВАЖНО:** Нужно проверить сигнатуру `retriever.retrieve()` в файле `bot_agent/retriever.py`.  
Если метод называется иначе (например `search()`, `get_top_k()`) — использовать правильное имя.  
Принцип тот же: вызвать тот же retriever что используется в каскадной системе в stage3 (`_run_retrieval_routing_context_stage`).

---

## FIX 3 — Исправить обрезку контекста при new_thread

**Файл:** `bot_agent/multiagent/agents/memory_retrieval_config.py`

### Проблема
```python
CONVERSATION_TURNS_NEW_THREAD: int = 2
```

Когда ThreadManager определяет `relation_to_thread == "new_thread"`, `_resolve_n_turns()` возвращает `2`. Из логов видно что КАЖДЫЙ ход помечается как `new_thread` — это значит что история всегда обрезается до 2 ходов, из-за чего бот не видит имя пользователя уже на 3-м ходу.

### Решение — увеличить `CONVERSATION_TURNS_NEW_THREAD`:
```python
# Было:
CONVERSATION_TURNS_NEW_THREAD: int = 2

# Стало:
CONVERSATION_TURNS_NEW_THREAD: int = 5
```

Логика: даже при переходе к новой теме (new_thread) пользователь — тот же человек.  
Его имя, эмоциональный фон и ключевые факты из последних 5 ходов критичны для психологического контакта.

**ДОПОЛНИТЕЛЬНО:** Нужно изучить почему каждый ход помечается `new_thread` в `thread_manager.py`.  
Это может быть отдельный баг в логике определения continuity. Если `continuity_score` всегда низкий → ThreadManager думает что каждый запрос — новая тема. Проверить пороговые значения в `thread_manager.py`.

---

## FIX 4 — Улучшение Writer System Prompt (имя пользователя)

**Файл:** `bot_agent/multiagent/agents/writer_agent_prompts.py`

### Проблема
В `WRITER_SYSTEM` нет явной инструкции использовать имя пользователя из контекста.  
Writer может игнорировать имя даже когда оно есть в `conversation_context`.

### Решение — добавить в `WRITER_SYSTEM` правило:
```python
WRITER_SYSTEM = """
Ты — NEO, психологический бот-собеседник. Ты работаешь как часть мультиагентной системы.
Стратегия и анализ уже выполнены другими агентами. Твоя задача — написать ОДИН ответ.

# ← ДОБАВИТЬ ЭТОТ БЛОК после первого абзаца:
КОНТЕКСТ И ПАМЯТЬ:
- Если в КОНТЕКСТЕ ПРЕДЫДУЩИХ ХОДОВ упоминается имя пользователя — ВСЕГДА используй его.
- Помни детали из предыдущих ходов: имя, ситуацию, ключевые темы.
- Не переспрашивай то, что пользователь уже сказал.

РЕЖИМЫ ОТВЕТА...
```

---

## Порядок реализации

1. **FIX 2** (`memory_retrieval.py` → `_load_rag`) — самый критичный, даст чанки из базы
2. **FIX 1** (`memory_retrieval.py` → `_load_conversation`) — даст полную память
3. **FIX 3** (`memory_retrieval_config.py`) — увеличить `CONVERSATION_TURNS_NEW_THREAD`
4. **FIX 4** (`writer_agent_prompts.py`) — улучшение промпта
5. **ИССЛЕДОВАНИЕ** — разобраться почему `new_thread` на каждом ходу

---

## Тест приёмки (как проверить что всё работает)

После внесения изменений запустить бота и выполнить следующий сценарий:

```
Ход 1: "привет, меня зовут Асхат"
  → Ожидаем: бот отвечает и использует имя "Асхат"

Ход 2: (любое сообщение о другой теме)
  → Ожидаем: бот по-прежнему знает имя

Ход 3: "как меня зовут?"
  → Ожидаем: бот отвечает "Асхат" ✅

Проверить в трейсе (Web UI):
  - "context_turns" > 0
  - "semantic_hits_count" > 0 (хотя бы 1 чанк из базы)
  - В "Memory Agent" → "context_turns" ≥ 2
  - В логах НЕТ: [CHROMA] ... 0 блоков
  - В логах ЕСТЬ: [MRA] rag hits=N
```

---

## Справочные ссылки (файлы на GitHub)

- [`memory_retrieval.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/multiagent/agents/memory_retrieval.py)
- [`memory_retrieval_config.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/multiagent/agents/memory_retrieval_config.py)
- [`writer_agent_prompts.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py)
- [`conversation_memory.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/conversation_memory.py) — эталон: `get_adaptive_context_text()`
- [`bootstrap_runtime_helpers.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/adaptive_runtime/bootstrap_runtime_helpers.py) — эталон: `_load_runtime_memory_context()`

---

## Итог

Все три бага возникли потому что мультиагентная система была написана с нуля и не переиспользовала готовые, рабочие компоненты из каскадной системы. Фиксы сводятся к одному принципу: **подключить те же модули памяти и retrieval что работали раньше**, а не изобретать упрощённые замены.
