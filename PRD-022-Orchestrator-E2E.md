# PRD-022 · Orchestrator + E2E + Memory Writeback
## Мультиагентная система NEO — Эпоха №4

---

**Документ:** PRD-022  
**Агент:** Orchestrator (финализация) + Memory Writeback  
**Версия:** 1.0  
**Статус:** В разработке  
**Автор:** Askhat (соло)  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription  
**Целевая директория:** `bot_psychologist/bot_agent/multiagent/`  
**Дата создания:** 2026-04-26  
**Зависимости:** PRD-017 ✅ · PRD-018 ✅ · PRD-019 ✅ · PRD-020 ✅ · PRD-021 ✅  

---

## 1. Контекст и назначение

### 1.1 Состояние пайплайна после PRD-021

Полный пайплайн реализован — `141 passed`. Orchestrator уже связывает всех 5 агентов в правильной последовательности:

```
User Message
     │
     ▼
[State Analyzer]     ← PRD-018 ✅
     │ StateSnapshot
     ▼
[Thread Manager]     ← PRD-017 ✅
     │ ThreadState
     ▼
[Memory+Retrieval]   ← PRD-019 ✅
     │ MemoryBundle
     ▼
[Writer / NEO]       ← PRD-020 ✅
     │ draft_answer
     ▼
[Validator]          ← PRD-021 ✅
     │ final_answer
     ▼
[Orchestrator → Telegram]
```

### 1.2 Что остаётся сделать в PRD-022

Три задачи:

**Задача 1 — Memory Writeback (реализовать scaffold):**  
`memory_retrieval_agent.update()` сейчас — это `logger.debug(...)` и ничего больше.  
Нужно реализовать запись каждого хода в `conversation_memory`.

**Задача 2 — E2E интеграционный тест:**  
Проверить что весь пайплайн работает end-to-end с моками — от `orchestrator.run()` до финального `answer` в dict.

**Задача 3 — Подключение в `answer_adaptive.py`:**  
Сейчас мультиагентный путь существует за флагом, но в `answer_adaptive.py` он, возможно, ещё вызывает старую заглушку. Нужно убедиться что при `MULTIAGENT_ENABLED=True` вызывается реальный `orchestrator.run()`.

### 1.3 Что НЕ входит в PRD-022

- Никаких новых агентов
- Никаких изменений контрактов
- Никаких изменений в существующих агентах
- Только: writeback + E2E тест + интеграция в adaptive

---

## 2. Memory Writeback — реализация update()

### 2.1 Текущий scaffold в memory_retrieval.py

```python
async def update(self, *, user_id, user_message, assistant_response, thread_state) -> None:
    logger.debug("[MRA] update scaffold user_id=%s thread_id=%s", user_id, thread_state.thread_id)
```

### 2.2 Что нужно реализовать

```python
async def update(
    self,
    *,
    user_id: str,
    user_message: str,
    assistant_response: str,
    thread_state: ThreadState,
) -> None:
    """
    Записывает завершённый ход диалога в conversation_memory.
    Вызывается как asyncio.create_task() из orchestrator — не блокирует ответ.
    """
    try:
        from ...conversation_memory import get_conversation_memory
        memory = get_conversation_memory(user_id=user_id)
        memory.add_turn(
            user_input=user_message,
            bot_response=assistant_response,
            metadata={
                "phase": thread_state.phase,
                "response_mode": thread_state.response_mode,
                "thread_id": thread_state.thread_id,
                "continuity_score": thread_state.continuity_score,
            },
        )
        logger.debug(
            "[MRA] update ok user_id=%s thread_id=%s",
            user_id, thread_state.thread_id,
        )
    except Exception as exc:
        logger.warning("[MRA] update failed (non-blocking): %s", exc)
```

**Требования:**
- Ошибка записи — только warning, не исключение (не мешает ответу пользователю)
- Вызывается только `memory.add_turn()` — не изменять профиль, не архивировать нить
- Метаданные (`phase`, `response_mode`, `thread_id`) передаются если `add_turn` их принимает; если API не поддерживает `metadata` — передавать без него

### 2.3 Адаптация к реальному API conversation_memory

`conversation_memory.py` может иметь другой интерфейс чем описано выше. IDE-агент должен:
1. Прочитать `conversation_memory.py` перед реализацией
2. Найти метод записи хода (может называться `add_turn`, `save_turn`, `append`, `add_message`)
3. Использовать реальный метод, не хардкодить предполагаемое имя
4. Если метод не принимает `metadata` — передать без него

---

## 3. E2E интеграционный тест

### 3.1 Подход

Тест проверяет что `orchestrator.run()` проходит полный пайплайн с моками всех внешних зависимостей:
- LLM (Writer) → мок
- ChromaDB (MRA) → мок
- conversation_memory (MRA) → мок
- thread_storage → реальный или in-memory мок

### 3.2 test_orchestrator_e2e.py

```
E2E-01  FULL_PIPELINE_RETURNS_DICT — orchestrator.run() возвращает dict с полями status/answer/thread_id/phase
E2E-02  ANSWER_NON_EMPTY — answer в результате непустой
E2E-03  DEBUG_ALL_FIELDS — debug содержит все поля: nervous_state, intent, safety_flag, confidence, has_relevant_knowledge, context_turns, semantic_hits_count, validator_blocked, validator_block_reason, validator_quality_flags
E2E-04  STATUS_OK — status == "ok"
E2E-05  PHASE_VALID — phase один из: clarify, explore, stabilize, integrate
E2E-06  RESPONSE_MODE_VALID — response_mode один из: reflect, validate, explore, regulate, practice, safe_override
E2E-07  SAFETY_OVERRIDE_FLOW — при safety_flag=True в StateSnapshot: response_mode=safe_override и answer не пустой
E2E-08  VALIDATOR_BLOCKED_FLOW — если Writer вернул опасный текст: answer = safe_replacement
E2E-09  MEMORY_UPDATE_CALLED — после orchestrator.run(): memory_retrieval_agent.update() была вызвана (через asyncio.create_task)
E2E-10  THREAD_SAVED — после run(): thread_storage содержит thread для user_id
E2E-11  NEW_THREAD_ARCHIVED — при new_thread + existing: старая нить архивируется
E2E-12  CONTINUE_THREAD — при continue: та же thread_id сохраняется
E2E-13  RUN_SYNC_EQUIVALENT — run_sync() возвращает тот же результат что и await run()
E2E-14  EMPTY_QUERY — пустой query: пайплайн не падает, возвращает dict
E2E-15  LONG_QUERY — query 2000+ символов: пайплайн не падает
```

---

## 4. Интеграция в answer_adaptive.py

### 4.1 Текущий вызов мультиагентного пути

В `answer_adaptive.py` уже есть проверка `MULTIAGENT_ENABLED`. Нужно убедиться что она выглядит так:

```python
from bot_agent.feature_flags import feature_flags
from bot_agent.multiagent.orchestrator import orchestrator

async def get_adaptive_answer(user_id: str, user_message: str) -> str:
    if feature_flags.is_enabled("MULTIAGENT_ENABLED"):
        result = await orchestrator.run(query=user_message, user_id=user_id)
        return result["answer"]
    # ... старый путь
```

Если интеграция уже корректна — подтвердить в прогресс-логе и не изменять.  
Если интеграция отсутствует или вызывает заглушку — исправить.

### 4.2 Что НЕ трогать в answer_adaptive.py

- Весь старый путь (классический `answer_adaptive`)
- Логику определения флага (уже работает)
- Импорты не связанные с мультиагентным путём

---

## 5. Структура файлов

```
bot_psychologist/
└── bot_agent/
    ├── multiagent/
    │   ├── agents/
    │   │   └── memory_retrieval.py      ← реализовать update() scaffold
    │   └── orchestrator.py              ← не изменять (уже финальный)
    └── answer_adaptive.py               ← проверить/исправить multiagent branch

tests/
└── multiagent/
    └── test_orchestrator_e2e.py         ← [новый] E2E тесты
```

---

## 6. Тесты E2E — полный список

```
E2E-01  FULL_PIPELINE_RETURNS_DICT
E2E-02  ANSWER_NON_EMPTY
E2E-03  DEBUG_ALL_FIELDS
E2E-04  STATUS_OK
E2E-05  PHASE_VALID
E2E-06  RESPONSE_MODE_VALID
E2E-07  SAFETY_OVERRIDE_FLOW
E2E-08  VALIDATOR_BLOCKED_FLOW
E2E-09  MEMORY_UPDATE_CALLED
E2E-10  THREAD_SAVED
E2E-11  NEW_THREAD_ARCHIVED
E2E-12  CONTINUE_THREAD
E2E-13  RUN_SYNC_EQUIVALENT
E2E-14  EMPTY_QUERY
E2E-15  LONG_QUERY
```

### 6.1 Регрессионные чеки

```
REG-01  pytest tests/multiagent/ — все 141 тест PRD-017..021 зелёные
REG-02  pytest tests/test_feature_flags.py — зелёный
REG-03  memory_retrieval.update() — не бросает исключений при ошибке записи
REG-04  orchestrator.py — не изменён (только memory_retrieval.py и answer_adaptive.py)
REG-05  MULTIAGENT_ENABLED=False — классический путь работает без изменений
```

---

## 7. Acceptance Criteria (Definition of Done)

PRD-022 завершён когда:

- [ ] `memory_retrieval.py` — `update()` реализован (пишет в conversation_memory)
- [ ] `tests/multiagent/test_orchestrator_e2e.py` создан
- [ ] Все 15 E2E тестов зелёные
- [ ] `answer_adaptive.py` — мультиагентный branch вызывает `orchestrator.run()`
- [ ] Все тесты PRD-017..021 зелёные (REG-01)
- [ ] `pytest tests/multiagent/ -q` → 156+ passed

---

## 8. Важные замечания для IDE-агента

1. **Прочитать `conversation_memory.py` перед реализацией `update()`.** Интерфейс может отличаться от описанного. Приоритет: реальный API модуля.
2. **`update()` вызывается через `asyncio.create_task()`** — это означает что ошибка внутри задачи не поднимается наружу автоматически. Поэтому `try/except` внутри `update()` обязателен.
3. **E2E тесты мокают всё внешнее** — Writer LLM, ChromaDB, conversation_memory. Оркестратор должен проходить путь с моками без реальных сетевых вызовов.
4. **`answer_adaptive.py`** — минимальные изменения. Только убедиться что при `MULTIAGENT_ENABLED=True` вызывается `orchestrator.run()`, а не старая заглушка.
5. **`orchestrator.py` не изменять** — он уже финальный после PRD-021.

---

*Конец PRD-022 · Orchestrator + E2E + Memory Writeback*  
*Следующие документы: PRD-023 · Legacy Archive · PRD-024 · Telegram Adapter*
