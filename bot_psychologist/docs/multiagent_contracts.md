# Контракты мультиагентной системы

Документ описывает dataclass-контракты, используемые в Эпохе 4.

См. также:
- [Архитектура](./multiagent_architecture.md)
- [Жизненный цикл нити](./thread_lifecycle.md)
- [Система безопасности](./safety_system.md)

## StateSnapshot

Источник: `bot_agent/multiagent/contracts/state_snapshot.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `nervous_state` | `str` | `window`, `hyper`, `hypo` | Нервное состояние на текущем ходе |
| `intent` | `str` | `clarify`, `vent`, `explore`, `contact`, `solution` | Основное коммуникативное намерение |
| `openness` | `str` | `open`, `mixed`, `defensive`, `collapsed` | Готовность к контакту/исследованию |
| `ok_position` | `str` | `I+W+`, `I-W+`, `I+W-`, `I-W-` | Позиция контакта (транзакционный маркер) |
| `safety_flag` | `bool` | `true/false` | Признак safety-риска |
| `confidence` | `float` | `0.0..1.0` | Уверенность классификации |

Валидация:
- выполняется в `__post_init__`;
- при нарушении диапазона/enum бросается `ValueError`.

## ThreadState

Источник: `bot_agent/multiagent/contracts/thread_state.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `thread_id` | `str` | UUID-like строка | Идентификатор активной нити |
| `user_id` | `str` | non-empty | Идентификатор пользователя |
| `core_direction` | `str` | text | Смысловое ядро нити |
| `phase` | `Literal` | `stabilize`, `clarify`, `explore`, `integrate` | Фаза нити |
| `open_loops` | `list[str]` | любое | Незакрытые смысловые петли |
| `closed_loops` | `list[str]` | любое | Закрытые петли |
| `nervous_state` | `str` | `window/hyper/hypo` | Прокинутый state-сигнал |
| `intent` | `str` | `clarify/vent/explore/contact/solution` | Прокинутый intent |
| `openness` | `str` | `open/mixed/defensive/collapsed` | Прокинутая openness |
| `ok_position` | `str` | `I+W+`, `I-W+`, `I+W-`, `I-W-` | Позиция контакта |
| `relation_to_thread` | `Literal` | `continue`, `branch`, `new_thread`, `return_to_old` | Отношение нового хода к текущей нити |
| `response_goal` | `str` | text | Цель ответа на текущем ходе |
| `response_mode` | `Literal` | `reflect`, `validate`, `explore`, `regulate`, `practice`, `safe_override` | Режим генерации |
| `must_avoid` | `list[str]` | любое | Ограничения для Writer |
| `continuity_score` | `float` | `0.0..1.0` | Оценка непрерывности нити |
| `turns_in_phase` | `int` | `>=1` | Сколько ходов в текущей фазе |
| `last_meaningful_shift` | `str` | text | Маркер последнего перехода |
| `safety_active` | `bool` | `true/false` | Активен ли safety-режим |
| `created_at` | `datetime` | ISO datetime | Время создания нити |
| `updated_at` | `datetime` | ISO datetime | Время последнего обновления |

Особенности:
- если `safety_active=True`, режим принудительно `safe_override`;
- если `updated_at < created_at`, `updated_at` выравнивается до `created_at`.

## ArchivedThread

Источник: `bot_agent/multiagent/contracts/thread_state.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `thread_id` | `str` | UUID-like строка | Идентификатор архивной нити |
| `core_direction` | `str` | text | Ядро нити на момент архивации |
| `closed_loops` | `list[str]` | любое | Закрытые петли |
| `open_loops` | `list[str]` | любое | Открытые петли |
| `final_phase` | `str` | `stabilize/clarify/explore/integrate` | Фаза при архивации |
| `archived_at` | `datetime` | ISO datetime | Время архивации |
| `archive_reason` | `str` | text | Причина архивации |

## SemanticHit

Источник: `bot_agent/multiagent/contracts/memory_bundle.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `chunk_id` | `str` | любое | Идентификатор чанка |
| `content` | `str` | любое | Полный текст чанка |
| `source` | `str` | любое | Источник чанка |
| `score` | `float` | `>=0` | Релевантность |

## UserProfile

Источник: `bot_agent/multiagent/contracts/memory_bundle.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `patterns` | `list[str]` | любое | Паттерны пользователя |
| `triggers` | `list[str]` | любое | Триггеры |
| `values` | `list[str]` | любое | Ценности |
| `progress_notes` | `list[str]` | любое | Накопленные заметки прогресса |

## MemoryBundle

Источник: `bot_agent/multiagent/contracts/memory_bundle.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `conversation_context` | `str` | любое | Сборка последних ходов диалога |
| `rag_query` | `str` | любое | Сформированный запрос в retrieval |
| `user_profile` | `UserProfile` | dataclass | Профиль пользователя |
| `semantic_hits` | `list[SemanticHit]` | список | Отфильтрованные RAG-попадания |
| `retrieved_chunks` | `list[Any]` | список | Технический список retrieved chunks |
| `has_relevant_knowledge` | `bool` | `true/false` | Есть ли релевантные знания |
| `context_turns` | `int` | `>=0` | Сколько ходов взято в контекст |

## WriterContract

Источник: `bot_agent/multiagent/contracts/writer_contract.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `user_message` | `str` | text | Текущее сообщение пользователя |
| `thread_state` | `ThreadState` | dataclass | Состояние нити |
| `memory_bundle` | `MemoryBundle` | dataclass | Память/контекст для Writer |
| `response_language` | `str \| None` | `ru/en/...` | Язык ответа (опционально) |

`to_prompt_context()` дополнительно сериализует:
- phase, response_mode, response_goal, must_avoid;
- nervous_state, ok_position, openness, safety_active;
- open/closed loops;
- conversation_context и top semantic hits.

## ValidationResult

Источник: `bot_agent/multiagent/contracts/validation_result.py`

| Поле | Тип | Допустимые значения | Описание |
|---|---|---|---|
| `is_blocked` | `bool` | `true/false` | Заблокирован ли ответ |
| `block_reason` | `str \| None` | text | Причина блокировки |
| `block_category` | `str \| None` | `safety/contract/...` | Категория блокировки |
| `safe_replacement` | `str \| None` | text | Безопасная замена ответа |
| `quality_flags` | `list[str]` | список | Нефатальные предупреждения качества |

## Поля debug-вывода `orchestrator.run()`

Источник: `bot_agent/multiagent/orchestrator.py`

Основные верхнеуровневые поля:
- `status`
- `answer`
- `thread_id`
- `phase`
- `response_mode`
- `relation_to_thread`
- `continuity_score`
- `debug` (словарь rich-трейса)

Ключевые поля внутри `debug`:

| Поле | Тип | Описание |
|---|---|---|
| `multiagent_enabled` | `bool` | Признак, что ответ построен мультиагентной системой |
| `pipeline_version` | `str` | Версия контракта пайплайна (`multiagent_v1`) |
| `total_latency_ms` | `int` | Полная задержка оркестратора |
| `nervous_state`, `intent`, `safety_flag`, `confidence` | scalar | Выход State Analyzer |
| `thread_id`, `phase`, `relation_to_thread`, `continuity_score` | scalar | Выход Thread Manager |
| `context_turns`, `semantic_hits_count`, `semantic_hits_detail` | scalar/list | Выход Memory Retrieval |
| `rag_query`, `conversation_context`, `user_profile` | mixed | Memory контекст |
| `writer_system_prompt`, `writer_user_prompt`, `writer_llm_response_raw` | `str` | Полотно LLM |
| `tokens_prompt`, `tokens_completion`, `tokens_total` | `int \| None` | Токены Writer-вызова |
| `estimated_cost_usd` | `float \| None` | Стоимость Writer-вызова |
| `model_used`, `model_temperature`, `model_max_tokens` | mixed | Параметры Writer |
| `validator_blocked`, `validator_block_reason`, `validator_quality_flags` | mixed | Выход Validator |
| `memory_written` | `dict` | Мини-preview записи в память |
| `timings` | `dict` | Поэтапные задержки (`state/thread/memory/writer/validator`) |
