# TASKLIST PRD-008 — Neo OutputValidator Fix (PROGRESS)

## Контекст
- PRD: `PRD-008-Neo-OutputValidator-Fix.md`
- Статус: В работе
- Дата старта: 2026-04-10

## A. Core Fix (OutputValidator)
- [x] A1. Обновить thin_body порог: `len(sentences) <= 1 and len(body) < 80`
- [x] A2. Добавить `preserve_structure: bool = False` в `validate()`
- [x] A3. При `preserve_structure=True` не вызывать `_strip_markdown()`
- [x] A4. Добавить Neo-инструкцию в `build_regeneration_hint()`

## B. Integration (Adaptive Pipeline)
- [x] B1. В `answer_adaptive.py` передавать `preserve_structure=True` для Neo-маршрутов
- [x] B2. Сохранить обратную совместимость для остальных вызовов/маршрутов

## C. Stream Observability
- [x] C1. Логировать `finish_reason` в `answer_stream()` (chat-completions ветка)
- [x] C2. Логировать завершение reasoning-stream ветки
- [x] C3. Логировать usage/token-метрики после стрима
- [x] C4. Добавить `[CONFIG]` лог лимитов токенов при инициализации клиента

## D. Tests
- [x] D1. Переписать `test_formatter_clips_long_answer` -> `test_formatter_does_not_clip_neo_answer`
- [x] D2. Добавить `tests/test_output_validator_neo.py`
- [x] D3. Добавить `tests/test_llm_answerer_stream.py`
- [x] D4. Обновить тесты monkeypatch для нового аргумента `preserve_structure`

## E. Validation
- [x] E1. Прогон unit/integration тестов по validator/adaptive/stream
- [x] E2. Проверить отсутствие регрессий в существующих тестах целевого скоупа
- [x] E3. Обновить tasklist фактическими результатами

## Факт выполнения
- 2026-04-10: `.venv\Scripts\python.exe -m pytest -q tests/test_response_formatter.py tests/test_output_validator_neo.py tests/test_llm_answerer_stream.py tests/unit/test_output_validator_rules.py tests/unit/test_output_validator_anti_sparse_rules.py tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py tests/integration/test_runtime_validation_receives_query_v1031.py tests/integration/test_sparse_output_triggers_regeneration_hint.py tests/test_llm_answerer.py` → `37 passed`.
