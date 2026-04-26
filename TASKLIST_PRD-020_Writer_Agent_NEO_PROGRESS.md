# TASKLIST PRD-020 - Writer Agent (NEO)

Start date: 2026-04-25  
PRD: `PRD-020-Writer-Agent-NEO.md`  
Scope: `bot_psychologist/bot_agent/multiagent/`

## 1. Implementation
- [x] Прочитать PRD-020 и зафиксировать границы.
- [x] Расширить `contracts/writer_contract.py` методом `to_prompt_context()`.
- [x] Добавить `agents/writer_agent_prompts.py` (`WRITER_SYSTEM`, `WRITER_USER_TEMPLATE`).
- [x] Добавить `agents/writer_agent.py` с LLM-вызовом и fallback-логикой.
- [x] Обновить `agents/__init__.py` (экспорт `writer_agent`).
- [x] Обновить `orchestrator.py`: заменить `_build_answer` на `writer_agent.write(...)`.
- [x] Добавить writer-флаги в `feature_flags.py`:
  - [x] `WRITER_MODEL`
  - [x] `WRITER_MAX_TOKENS`
  - [x] `WRITER_TEMPERATURE`

## 2. Tests
- [x] Добавить fixtures: `tests/multiagent/fixtures/writer_agent_fixtures.json`.
- [x] Добавить `tests/multiagent/test_writer_agent.py`.
- [x] Покрыть WA-01..WA-30 из PRD (LLM только через мок).
- [x] Проверить orchestrator integration без `_build_answer`.

## 3. Regression checks
- [x] `contracts/memory_bundle.py` без изменений (PRD-019 контракт стабильный).
- [x] `contracts/thread_state.py` без изменений.
- [x] `contracts/state_snapshot.py` без изменений.
- [x] `pytest tests/multiagent -q` зеленый.
- [x] `MULTIAGENT_ENABLED=False` классический путь не затронут.

## 4. Execution checks
- [x] `py_compile` для измененных файлов.
- [x] `pytest tests/multiagent/test_writer_agent.py -q`
- [x] `pytest tests/multiagent -q`

## 5. Progress log
- 2026-04-25: PRD-020 прочитан, тасклист создан, реализация начата.
- 2026-04-25: Добавлены `writer_agent.py` и `writer_agent_prompts.py`, расширен `writer_contract`, обновлены `orchestrator` и `feature_flags`.
- 2026-04-25: Добавлены fixtures `writer_agent_fixtures.json` и тесты `test_writer_agent.py` (WA-01..WA-30).
- 2026-04-25: Валидация завершена — `test_writer_agent.py`: 30 passed; `tests/multiagent -q`: 105 passed.
