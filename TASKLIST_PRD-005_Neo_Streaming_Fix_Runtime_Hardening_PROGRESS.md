# TASKLIST PRD-005 — Neo Streaming Fix & Runtime Hardening (PROGRESS)

## Контекст
- PRD: `PRD-005-Neo-Streaming-Fix-Runtime-Hardening.md`
- Статус: Завершено
- Дата старта: 2026-04-10
- Дата завершения: 2026-04-10

## A. Реализация
- [x] A1. Создать `bot_psychologist/bot_agent/llm_streaming.py` с `stream_answer_tokens()`
- [x] A2. Перевести `/api/v1/questions/adaptive-stream` на `stream_answer_tokens()`
- [x] A3. Удалить `_graph_client` dependency из stream endpoint
- [x] A4. Разделить SSE payload: `done` без `trace`, `event: trace` отдельно (только debug)
- [x] A5. Ввести bounded user stats (`_seen_users`, `_record_user`, лимит)
- [x] A6. Применить `_record_user()` во всех endpoint-обновлениях статистики
- [x] A7. Экспортировать `stream_answer_tokens` в `bot_psychologist/bot_agent/__init__.py`

## B. Тесты PRD-005
- [x] B1. `bot_psychologist/tests/test_llm_streaming.py`
- [x] B2. `bot_psychologist/tests/test_sse_payload.py`
- [x] B3. `bot_psychologist/tests/test_stats_counter.py`
- [x] B4. `bot_psychologist/tests/test_stream_dependencies.py`
- [x] B5. `bot_psychologist/tests/test_concurrent_streams.py`
- [x] B6. `bot_psychologist/tests/test_sse_cyrillic.py`
- [x] B7. Обновить существующие stream-регрессии под новый контракт trace

## C. Прогон
- [x] C1. Запустить целевой набор тестов PRD-005
- [x] C2. Проверить, что соседние критичные stream/neo тесты не сломаны

## D. Заметки по ходу
- План: реализовать FIX-005-1..5 без изменения контракта `token/done/error`.
- trace будет передаваться отдельным SSE-событием `event: trace`, чтобы не раздувать `done`.
- Факт: целевой прогон PRD-005 — `19 passed` (новые + затронутые stream/regression/integration/smoke).
- Факт: дополнительный регресс соседних модулей — `9 passed` (`tests/test_retrieval_pipeline_simplified.py`, `tests/test_llm_payload_endpoint.py`).
