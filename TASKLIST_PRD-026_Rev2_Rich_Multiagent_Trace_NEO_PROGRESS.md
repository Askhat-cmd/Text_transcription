# TASKLIST PRD-026 Rev.2 — Богатый мультиагентный трейс NEO (PROGRESS)

## Контекст
Источник: `PRD-026 Rev.2 — Богатый мультиагентный трейс NEO.md`

## План реализации
- [x] T0: Прочитать PRD Rev.2 и зафиксировать контракт полей/блоков.
- [x] B1: Расширить multiagent debug в `orchestrator.py` (semantic_hits_detail, writer_llm, turn_diff, memory context refs).
- [x] B2: Добавить в `WriterAgent` стабильный `last_debug` с промптами/токенами/стоимостью/моделью.
- [x] B3: Добавить `rag_query` в `MemoryBundle` и заполнение в retrieval-агенте.
- [x] B4: Добавить накопление session-метрик в `api/session_store.py`.
- [x] B5: Расширить `/api/debug/session/{session_id}/multiagent-trace` + `api/models.py` под rich-trace контракт.
- [x] F1: Обновить TypeScript-типы rich trace.
- [x] F2: Переработать `MultiAgentTraceWidget.tsx` (7 блоков, accordion, copy, fallback-safe rendering).
- [x] TST-BE: Добавить/обновить backend тесты по пунктам PRD.
- [x] TST-FE: Добавить/обновить frontend тесты рендера rich виджета.
- [x] QA: Прогон целевых тестов и smoke API/UI на rich trace.

## Тесты
- [x] `bot_psychologist/.venv/Scripts/python.exe -m pytest bot_psychologist/tests/test_multiagent_trace.py -q`
- [x] `bot_psychologist/.venv/Scripts/python.exe -m pytest bot_psychologist/tests/test_debug_metrics_and_export.py bot_psychologist/tests/test_llm_payload_endpoint.py -q`
- [x] `cd bot_psychologist/web_ui; npm test -- src/components/chat/MultiAgentTraceWidget.test.ts`

## Чек-лист готовности
- [x] Endpoint отдает секции: pipeline, memory_context, writer_llm, models_tokens_cost, turn_diff, anomalies, session_dashboard.
- [x] На фронте все 7 блоков есть и сворачиваются.
- [x] Контракт обратной совместимости сохранен для отсутствующих полей.
- [x] Нет регрессии по текущим тестам multiagent/trace.
