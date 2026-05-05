# TASKLIST PRD-036 — Disable Legacy Fallback & Runtime Guard

## Статус
- [x] PRD изучен
- [x] Проверены текущие runtime/API/Telegram/tests точки входа
- [x] `answer_adaptive` переведен в deprecated multiagent-only shim
- [x] Добавлен controlled error без classic fallback
- [x] Обновлен e2e-контракт (legacy fallback disabled)
- [x] Добавлен inventory guard против silent legacy fallback
- [x] Обновлен multiagent regression-контракт под post-cutover поведение
- [x] Прогнаны целевые тесты PRD-036

## Выполненные изменения
- [x] `bot_psychologist/bot_agent/answer_adaptive.py`
  - [x] Добавлен импорт `run_multiagent_adaptive_sync`
  - [x] Публичный `answer_question_adaptive(...)` переведен на multiagent-only compatibility shim
  - [x] Добавлены runtime markers:
    - `runtime_entrypoint = answer_adaptive_deprecated_shim`
    - `legacy_fallback_used = false`
    - `legacy_fallback_blocked = true`
  - [x] Добавлен helper `_build_multiagent_shim_error_response(...)`
  - [x] Legacy cascade сохранен как private/deprecated: `_answer_question_adaptive_legacy_cascade(...)`
- [x] `bot_psychologist/tests/e2e/test_legacy_fallback_disabled_after_cutover.py`
  - [x] Контракт: `MULTIAGENT_ENABLED=False` не включает legacy cascade
- [x] `bot_psychologist/tests/e2e/test_no_legacy_fallback_after_cutover.py`
  - [x] Контракт: ошибка adapter не включает legacy cascade, возвращается controlled error
- [x] `bot_psychologist/tests/inventory/test_no_silent_legacy_fallback.py`
  - [x] Guard по source public shim (нет legacy fallback path, есть `run_multiagent_adaptive_sync`)
- [x] `bot_psychologist/tests/multiagent/test_legacy_rollback.py`
  - [x] Контракт обновлен на post-cutover поведение

## Целевые прогоны
- [x] `.venv\Scripts\python.exe -m pytest tests/e2e/test_no_legacy_fallback_after_cutover.py -q` → `1 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/e2e/test_legacy_fallback_disabled_after_cutover.py -q` → `1 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/inventory/test_no_silent_legacy_fallback.py -q` → `1 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/multiagent -q` → `181 passed` (один флак при первом прогоне, повторный прогон зеленый)
- [x] `.venv\Scripts\python.exe -m pytest tests/api -q` → `31 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_llm_streaming.py -q` → `7 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/telegram_adapter -q` → `44 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py -q` → `25 passed`
