# TASKLIST PRD-025: Safety + Thread Fixes

Статус: `done`  
PRD: `PRD-025-Safety-Thread-Fixes.md`  
Дата старта: `2026-04-26`

## 1) Thread continuity (FIX-01)
- [x] Исправить базовый путь `ThreadStorage` на стабильный абсолютный путь от `__file__`.
- [x] Добавить лог стартового пути хранения.
- [x] Добавить тесты `TS-01..TS-05` в `tests/multiagent/test_thread_storage_persistence.py`.

## 2) Safety detection (FIX-02)
- [x] Расширить `_SAFETY_KEYWORDS` в `state_analyzer.py`.
- [x] Добавить secondary LLM fallback `_llm_safety_check(...)`.
- [x] Интегрировать fallback safety-check в `_analyze_with_llm(...)`.
- [x] Добавить тесты `SD-01..SD-10` в `tests/multiagent/test_safety_detection.py`.

## 3) Encoding normalization
- [x] Добавить `_normalize_query()` в `multiagent/orchestrator.py`.
- [x] Вызвать нормализацию в начале `run(...)`.

## 4) Прогоны и критерии
- [x] `pytest bot_psychologist/tests/multiagent/test_thread_storage_persistence.py -q`
- [x] `pytest bot_psychologist/tests/multiagent/test_safety_detection.py -q`
- [x] `pytest bot_psychologist/tests/multiagent -q`
- [x] Обновить статус и итоги в этом tasklist.

## Итоги прогонов
- `test_thread_storage_persistence.py`: `5 passed`
- `test_safety_detection.py`: `10 passed`
- `tests/multiagent -q`: `189 passed`
- В регрессии есть только предупреждения (DeprecationWarning/asyncio pending task warning), падений нет.
