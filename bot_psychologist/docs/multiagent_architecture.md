# Мультиагентная архитектура NEO

## Обзор

Документ описывает актуальную мультиагентную архитектуру рантайма в `bot_psychologist`.
Система введена в Эпохе 4 (PRD-017..PRD-025) и является единственным активным runtime после PRD-036/037/039.

Ключевой переключатель:
- `MULTIAGENT_ENABLED=true` — рекомендуемое значение compatibility flag.
- `MULTIAGENT_ENABLED=false` — deprecated value, не включает legacy runtime.

См. также:
- [Контракты](./multiagent_contracts.md)
- [Жизненный цикл нити](./thread_lifecycle.md)
- [Система безопасности](./safety_system.md)
- [Переход с legacy](./migration_legacy_to_multiagent.md)

## Схема пайплайна

```text
User Message
    |
    v
[State Analyzer Agent]
    outputs: StateSnapshot
    |
    v
[Thread Manager Agent]
    inputs: StateSnapshot + current_thread + archive
    outputs: ThreadState
    |
    v
[Memory Retrieval Agent]
    inputs: user_message + ThreadState + user_id
    outputs: MemoryBundle
    |
    v
[Writer Agent NEO]
    inputs: WriterContract(ThreadState + MemoryBundle + user_message)
    outputs: draft_answer + debug(meta/tokens/prompts)
    |
    v
[Validator Agent]
    inputs: draft_answer + WriterContract
    outputs: ValidationResult
    |
    +-- blocked? -> safe_replacement
    |
    v
Final Answer + Multiagent Debug Payload
```

## Агенты

### State Analyzer Agent

Файл: `bot_agent/multiagent/agents/state_analyzer.py`

Назначение:
- классифицирует текущее состояние пользователя в формате `StateSnapshot`;
- детерминированно проверяет safety-триггеры (`_SAFETY_KEYWORDS`);
- при необходимости добавляет LLM-уточнение (`_analyze_with_llm`).

Вход:
- `user_message: str`
- `previous_thread: Optional[ThreadState]`

Выход:
- `StateSnapshot`:
  - `nervous_state` (`window|hyper|hypo`)
  - `intent` (`clarify|vent|explore|contact|solution`)
  - `openness` (`open|mixed|defensive|collapsed`)
  - `ok_position` (`I+W+|I-W+|I+W-|I-W-`)
  - `safety_flag` (`bool`)
  - `confidence` (`0.0..1.0`)

Ключевая логика:
- `safety_flag=True` ставится детерминированно на совпадении с `_SAFETY_KEYWORDS`;
- onboarding-команды (`/start`, `привет`) дают быстрый контактный снапшот;
- при неочевидном кейсе используется LLM с JSON-ответом.

### Thread Manager Agent

Файл: `bot_agent/multiagent/agents/thread_manager.py`

Назначение:
- решает, продолжать ли текущую нить или начинать новую;
- обновляет фазу нити и целевой `response_mode`.

Вход:
- `user_message`
- `state_snapshot`
- `current_thread`
- `archived_threads`
- `user_id`

Выход:
- `ThreadState` (активная нить)

Ключевые решения:
- relation: `continue|branch|new_thread|return_to_old`;
- continuity через `_continuity_score` (Jaccard-пересечение токенов);
- порог создания новой нити: `_NEW_THREAD_THRESHOLD=0.20`;
- safety-патч форсирует фазу `stabilize` и режим `safe_override`.

### Memory Retrieval Agent

Файл: `bot_agent/multiagent/agents/memory_retrieval.py`

Назначение:
- собирает контекст для Writer из трех источников:
  - история диалога;
  - профиль пользователя;
  - RAG-попадания (`semantic_hits`).

Вход:
- `user_message`
- `thread_state`
- `user_id`

Выход:
- `MemoryBundle`

Ключевая логика:
- параллельная загрузка (`asyncio.gather`) conversation/profile/RAG;
- фильтрация semantic hits по `RAG_MIN_SCORE`;
- сортировка hits по score по убыванию;
- неблокирующий update памяти после генерации ответа.

### Writer Agent NEO

Файл: `bot_agent/multiagent/agents/writer_agent.py`

Назначение:
- генерирует финальный текст ответа на основе `WriterContract`.

Вход:
- `WriterContract`

Выход:
- `draft_answer: str`
- служебный debug в `writer_agent.last_debug`:
  - system/user prompt,
  - raw LLM response,
  - token usage,
  - estimated cost,
  - duration/error.

Ключевая логика:
- safety-ветка: при `thread_state.safety_active=True` используется safe override при любой ошибке;
- стандартная ветка: LLM-вызов + fallback, если пустой/ошибочный ответ;
- отдельные расчеты стоимости по модели (`_COST_PER_1K_TOKENS`).

### Validator Agent

Файл: `bot_agent/multiagent/agents/validator_agent.py`

Назначение:
- детерминированно проверяет качество и безопасность draft-ответа.

Вход:
- `draft: str`
- `contract: WriterContract`

Выход:
- `ValidationResult`:
  - `is_blocked`
  - `block_reason`
  - `block_category`
  - `safe_replacement`
  - `quality_flags`

Ключевая логика:
- при safety/block нарушениях ответ блокируется;
- в конце возвращается `safe_replacement`;
- при отсутствии блокировки добавляются `quality_flags`.

### Orchestrator

Файл: `bot_agent/multiagent/orchestrator.py`

Назначение:
- координирует все агентные этапы;
- формирует итоговый ответ и rich debug payload.

Порядок:
1. нормализация query (`_normalize_query`, включая repair mojibake);
2. `state_analyzer_agent.analyze(...)`;
3. `thread_manager_agent.update(...)`;
4. `memory_retrieval_agent.assemble(...)`;
5. `writer_agent.write(...)`;
6. `validator_agent.validate(...)`;
7. неблокирующий `memory_retrieval_agent.update(...)`;
8. возврат стандартного результата + `debug`.

## Контракты данных

Полные таблицы полей: [multiagent_contracts.md](./multiagent_contracts.md)

### StateSnapshot
- контракт состояния на один ход (State Analyzer → Thread Manager).

### ThreadState
- активное состояние нити (Thread Manager → Writer/Orchestrator).

### MemoryBundle
- агрегированный memory-контекст (Memory Retrieval → Writer).

### WriterContract
- единый вход Writer (`user_message + thread_state + memory_bundle`).

## Feature Flags

Файл: `bot_agent/feature_flags.py`

Ключевые флаги:
- `MULTIAGENT_ENABLED` (bool, default: `True`) — deprecated compatibility flag (runtime не переключает).
- `STATE_ANALYZER_MODEL` (str, default: `gpt-5-nano`)
- `THREAD_MANAGER_MODEL` (str, default: `gpt-5-nano`, reserved; thread manager now heuristic)
- `WRITER_MODEL` (str, default: `gpt-5-mini`)
- `MULTIAGENT_LLM_TIMEOUT` (str->float, default: `30`)
- `MULTIAGENT_MAX_TOKENS` (str->int, default: `600`)
- `MULTIAGENT_TEMPERATURE` (str->float, default: `0.7`)
- `THREAD_STORAGE_DIR` (str, default: `bot_psychologist/data/threads`)

## Конфигурация

Практический минимум `.env`:

```env
MULTIAGENT_ENABLED=true
STATE_ANALYZER_MODEL=gpt-5-nano
THREAD_MANAGER_MODEL=gpt-5-nano
WRITER_MODEL=gpt-5-mini
MULTIAGENT_LLM_TIMEOUT=30
MULTIAGENT_MAX_TOKENS=600
MULTIAGENT_TEMPERATURE=0.7
THREAD_STORAGE_DIR=bot_psychologist/data/threads
```

Замечания:
- `THREAD_STORAGE_DIR` разрешается в абсолютный путь в `thread_storage.py` через `Path(...).resolve()`.
- Legacy cascade implementation physically removed in PRD-041; `answer_adaptive.py` kept only as compatibility shim.

## Пример вывода orchestrator.run()

Ниже упрощенный реальный пример структуры ответа:

```json
{
  "status": "ok",
  "answer": "...",
  "thread_id": "tm_xxx",
  "phase": "clarify",
  "response_mode": "validate",
  "relation_to_thread": "continue",
  "continuity_score": 0.74,
  "debug": {
    "multiagent_enabled": true,
    "pipeline_version": "multiagent_v1",
    "total_latency_ms": 1530,
    "nervous_state": "window",
    "intent": "contact",
    "safety_flag": false,
    "confidence": 0.9,
    "thread_id": "tm_xxx",
    "phase": "clarify",
    "relation_to_thread": "continue",
    "continuity_score": 0.74,
    "response_mode": "validate",
    "context_turns": 2,
    "semantic_hits_count": 1,
    "semantic_hits_detail": [...],
    "rag_query": "...",
    "conversation_context": "...",
    "writer_system_prompt": "...",
    "writer_user_prompt": "...",
    "writer_llm_response_raw": "...",
    "tokens_prompt": 300,
    "tokens_completion": 120,
    "tokens_total": 420,
    "estimated_cost_usd": 0.000315,
    "model_used": "gpt-5-mini",
    "validator_blocked": false,
    "validator_block_reason": null,
    "validator_quality_flags": [],
    "memory_written": {...},
    "timings": {
      "state_analyzer_ms": 200,
      "thread_manager_ms": 10,
      "memory_retrieval_ms": 350,
      "writer_ms": 900,
      "validator_ms": 20
    }
  }
}
```

Описание полей:
- `status` — итог исполнения оркестратора.
- `thread_id` / `phase` / `relation_to_thread` — состояние нити после Thread Manager.
- `response_mode` — режим ответа, который Writer должен выдержать.
- `debug` — единый payload для trace API и диагностики.

## Режимы ответа (`response_mode`)

Базовые режимы из `ThreadState`:
- `reflect` — отражение и удержание контакта.
- `validate` — нормализация и подтверждение.
- `explore` — исследование смысла/контекста.
- `regulate` — мягкая стабилизация.
- `practice` — один практический шаг.
- `safe_override` — аварийный безопасный режим.

Правило:
- при `safety_flag=True` итоговый режим должен быть `safe_override`.
