# TASKLIST PRD-035 — Multiagent Runtime Cutover

## Статус
- [x] Изучен `TO_DO_LIST/PRD-035_Multiagent_Runtime_Cutover.md`
- [x] Изучены текущие файлы runtime/API/Telegram/tests
- [x] Реализован `multiagent/runtime_adapter.py` (sync+async + normalize)
- [x] API routes переведены с legacy facade на runtime adapter
- [x] Compat endpoints переведены на runtime adapter
- [x] Streaming путь отвязан от legacy facade
- [x] Telegram adapter default executor отвязан от `answer_adaptive`
- [x] Добавлены cutover tests (api/telegram/inventory)
- [x] Прогнаны целевые тесты PRD-035 (с зафиксированными legacy inventory остатками)

## Задачи реализации
- [x] `bot_psychologist/bot_agent/multiagent/runtime_adapter.py`
  - [x] sync bridge (safe call из sync-кода при активном event loop)
  - [x] async entrypoint
  - [x] normalize multiagent result в API-compatible payload
- [x] `bot_psychologist/api/routes/chat.py`
  - [x] импорт runtime adapter вместо `answer_question_adaptive`
  - [x] `_resolve_multiagent_runtime()` c monkeypatch-friendly поведением
  - [x] `/questions/adaptive` вызывает runtime adapter
  - [x] `/questions/adaptive-stream` не использует legacy answer_fn
- [x] `bot_psychologist/api/routes/common.py`
  - [x] убрать импорт legacy `answer_question_adaptive`
  - [x] добавить `_run_multiagent_compat_answer(...)`
  - [x] сохранить совместимость через alias `_run_neo_compat_answer`
- [x] `bot_psychologist/api/routes/__init__.py`
  - [x] экспорт `run_multiagent_adaptive_sync` для monkeypatch в тестах
  - [x] сохранить backward-compatible экспорт `answer_question_adaptive`
- [x] `bot_psychologist/api/telegram_adapter/service.py`
  - [x] default executor вызывает runtime adapter

## Тесты
- [x] `bot_psychologist/tests/api/test_multiagent_runtime_cutover.py`
  - [x] adaptive endpoint не дергает legacy
  - [x] compat endpoints не дергают legacy
  - [x] adaptive-stream не дергает legacy
- [x] `bot_psychologist/tests/telegram_adapter/test_runtime_cutover.py`
  - [x] default chat executor вызывает runtime adapter
- [x] `bot_psychologist/tests/inventory/test_runtime_cutover_no_legacy_entrypoints.py`
  - [x] проверка отсутствия legacy imports/touchpoints в API/Telegram runtime path

## Прогон
- [x] `.venv\\Scripts\\python.exe -m pytest tests/multiagent -q` → `180 passed`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/api -q` → `31 passed`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py -q` → `25 passed`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/telegram_adapter -q` → `44 passed`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory -q` → `42 passed, 3 failed (legacy/baseline inventory вне scope PRD-035)`

## Inventory остатки (вне PRD-035)
- [ ] `tests/inventory/test_admin_prompt_fetch_failure_inventory.py::test_prompt_fetch_failure_markers_are_present_in_current_baseline`
- [ ] `tests/inventory/test_legacy_runtime_map.py::test_legacy_runtime_map_fixture_is_consistent`
- [ ] `tests/inventory/test_legacy_runtime_map.py::test_legacy_runtime_dependencies_are_present_in_mapped_files`

## Ручные smoke-check (после тестов)
- [ ] `/api/v1/questions/adaptive`: runtime=`multiagent`, trace сохраняется
- [ ] `/api/v1/questions/adaptive-stream`: done event корректен, без legacy path
- [ ] Hot-swap моделей через Admin не сломан
