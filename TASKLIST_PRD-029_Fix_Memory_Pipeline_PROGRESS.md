# TASKLIST — PRD-029 Fix Memory Pipeline

## Scope
- [x] Изучить PRD-029 и зафиксировать область изменений.
- [x] Проверить целевые файлы и текущую реализацию.
- [x] FIX 1: переключить conversation context в `memory_retrieval.py` на `get_adaptive_context_text(...)` с `user_message`.
- [x] FIX 2: переключить RAG на глобальный retriever (`get_retriever`) в `memory_retrieval.py`.
- [x] FIX 3: изменить `CONVERSATION_TURNS_NEW_THREAD` в `memory_retrieval_config.py` (`2 -> 5`).
- [x] FIX 4: усилить `WRITER_SYSTEM` по использованию имени пользователя из контекста.
- [x] Разобрать частый `new_thread` и внести безопасный фикс в `thread_manager.py` (маркеры + tokenization).
- [x] Обновить тест-контракты под новый `new_thread`-порог контекста (`expected_n_turns: 5`).
- [x] Устранить блокер live-ветки multiagent в API (`asyncio.run() cannot be called from a running event loop`) через безопасный thread-bridge в `answer_adaptive.py`.
- [x] Добавить post-processing удержания имени в `writer_agent.py` (если имя явно есть в контексте и отсутствует в ответе).
- [x] Прогнать целевые тесты.
- [x] Прогнать расширенный набор multiagent-тестов.

## Изменённые файлы
- `bot_psychologist/bot_agent/multiagent/agents/memory_retrieval.py`
- `bot_psychologist/bot_agent/multiagent/agents/memory_retrieval_config.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py`
- `bot_psychologist/bot_agent/multiagent/agents/thread_manager.py`
- `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/tests/multiagent/test_memory_retrieval.py`
- `bot_psychologist/tests/multiagent/fixtures/memory_retrieval_fixtures.json`

## Тесты
- [x] `python -m pytest bot_psychologist/tests/multiagent/test_memory_retrieval.py -q` → `33 passed`
- [x] `python -m pytest bot_psychologist/tests/multiagent/test_thread_manager.py -q` → `6 passed`
- [x] `python -m pytest bot_psychologist/tests/multiagent/test_orchestrator_e2e.py -q` → `15 passed`
- [x] `python -m pytest bot_psychologist/tests/multiagent/test_writer_agent.py -q` → `30 passed`
- [x] `python -m pytest bot_psychologist/tests/test_multiagent_trace.py -q` → `10 passed`
- [x] `python -m pytest bot_psychologist/tests/multiagent -q` → `190 passed`

## Приёмка по PRD (live-проверки)
- [x] На 3-м ходе бот корректно удерживает имя пользователя из памяти.
  - live session: `prd029-live-47629a80`
  - turn#3 answer содержит обращение: `Привет, Максим! ...`
- [x] В trace есть `context_turns > 0`.
  - live session: `prd029-live-47629a80`
  - observed: `context_turns=5` (turn#1..#3)
- [x] В trace есть `semantic_hits_count > 0` при релевантных данных.
  - live session: `prd029-live-47629a80`
  - observed: `semantic_hits_count=3/4/4` (max=4)
- [x] В логике retrieval добавлен лог `[MRA] rag hits=N`.
- [x] Регрессий по multiagent safety/validator тестам не выявлено (`tests/multiagent` зелёный).

### Live replay 2026-04-27
- [x] Проверка 1 (удержание имени): `prd029-live-bc7c8100`
  - turn#3 answer содержит имя пользователя (`Maksim`) → `PASS`
- [x] Проверка 2 (контекст диалога): `prd029-live-bc7c8100`
  - `context_turns=5` → `PASS`
- [x] Проверка 3 (semantic retrieval): `prd029-live-47629a80`
  - after live query `semantic_hits_count=1` → `PASS`
