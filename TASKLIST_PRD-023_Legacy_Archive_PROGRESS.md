# TASKLIST PRD-023 — Legacy Archive + Cleanup

Статус: выполнено  
Дата: 2026-04-26

## Scope
- Провести аудит legacy-компонентов после запуска мультиагентного пайплайна (PRD-017..022).
- Пометить deprecated только те модули, которые дублируются `multiagent/*`, без удаления.
- Добавить документацию `bot_psychologist/bot_agent/multiagent/README.md`.
- Подтвердить rollback при `MULTIAGENT_ENABLED=False`.

## Tasks
- [x] Прочитать PRD-023.
- [x] Провести аудит файлов: `answer_adaptive.py`, `route_resolver.py`, `adaptive_runtime.py` (если есть), `prompts/*` / `prompt_builder.py`.
- [x] Добавить deprecate-маркеры в найденные устаревшие модули.
- [x] Создать `bot_psychologist/bot_agent/multiagent/README.md`.
- [x] Добавить `bot_psychologist/tests/multiagent/test_legacy_rollback.py` (LR-01..LR-05).
- [x] Прогнать тесты PRD-023.
- [x] Обновить этот tasklist финальными результатами.

## Аудит (кратко)
- `bot_psychologist/bot_agent/route_resolver.py` — legacy-резолвер для классического пути; функционально перекрыт `multiagent/agents/thread_manager.py` в новом пайплайне.  
- `bot_psychologist/bot_agent/prompt_registry_v2.py` — prompt stack классического пути; функционально перекрыт `multiagent/agents/writer_agent_prompts.py` в новом пайплайне.
- `bot_psychologist/bot_agent/adaptive_runtime.py` — отсутствует (есть пакет `adaptive_runtime/`).
- `bot_psychologist/bot_agent/prompt_builder.py` — отсутствует.
- `bot_psychologist/bot_agent/answer_adaptive.py` — действующий входной модуль, не помечается как deprecated целиком (содержит переключение на multiagent и rollback-путь).

## Tests
- [x] `pytest bot_psychologist/tests/multiagent/test_legacy_rollback.py -q` (`5 passed`)
- [x] `pytest bot_psychologist/tests/multiagent -q` (`164 passed`)
- [x] `pytest bot_psychologist/tests/test_feature_flags.py -q` (`2 passed`)

## Checks
- [x] Ничего не удалено из рабочего кода.
- [x] Deprecated-маркеры добавлены только в audited legacy-модули.
- [x] `MULTIAGENT_ENABLED=False` не вызывает `orchestrator`.

## Итоговые изменения
- Добавлен `bot_psychologist/bot_agent/multiagent/README.md` с архитектурой пайплайна, таблицами агентов/контрактов и тестовым блоком.
- Добавлены deprecate-маркеры в:
  - `bot_psychologist/bot_agent/route_resolver.py`
  - `bot_psychologist/bot_agent/prompt_registry_v2.py`
- Добавлен rollback-тестовый набор:
  - `bot_psychologist/tests/multiagent/test_legacy_rollback.py` (LR-01..LR-05)
