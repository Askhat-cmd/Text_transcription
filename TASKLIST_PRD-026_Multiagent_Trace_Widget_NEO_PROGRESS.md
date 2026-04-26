# TASKLIST_PRD-026_Multiagent_Trace_Widget_NEO_PROGRESS

## Цель
Реализовать мультиагентный trace-widget NEO end-to-end: backend контракт + API + frontend виджет + тесты.

## План работ
- [x] B1. Добавить тайминги 5 агентов и `pipeline_version=multiagent_v1` в `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- [x] B2. Добавить Pydantic модели мультиагентного трейса в `bot_psychologist/api/models.py`
- [x] B3. Добавить сохранение/чтение multiagent debug в `bot_psychologist/api/session_store.py`
- [x] B4. Сохранять multiagent debug из `bot_psychologist/api/routes/chat.py`
- [x] B5. Добавить endpoint `GET /api/debug/session/{session_id}/multiagent-trace` в `bot_psychologist/api/debug_routes.py`
- [x] F1. Добавить TypeScript типы мультиагентного трейса (`web_ui/src/types`)
- [x] F2. Добавить `apiService.getMultiAgentTrace(...)` и `hasDevKey()`
- [x] F3. Добавить хук `web_ui/src/hooks/useMultiAgentTrace.ts`
- [x] F4. Добавить `web_ui/src/components/chat/MultiAgentTraceWidget.tsx`
- [x] F5. Встроить виджет в рендер bot-message без ломки legacy trace
- [x] T1. Добавить backend тесты мультиагентного трейса
- [x] T2. Добавить frontend тесты виджета
- [x] V1. Прогон backend тестов
- [x] V2. Прогон frontend typecheck + tests

## Проверки
- [x] `pytest bot_psychologist/tests/test_multiagent_trace.py -q`
- [x] `pytest bot_psychologist/tests/multiagent/test_orchestrator_e2e.py -q` (smoke regression)
- [x] `cd bot_psychologist/web_ui && npx tsc --noEmit`
- [x] `cd bot_psychologist/web_ui && npm run test -- MultiAgentTraceWidget`

## Критерии готовности
- [ ] Endpoint `/api/debug/session/{session_id}/multiagent-trace` отдает валидный payload для dev-key
- [ ] В dev-режиме под bot-сообщением отображается мультиагентный виджет
- [ ] Legacy trace не сломан при `MULTIAGENT_ENABLED=false`
- [ ] Тесты и typecheck зеленые
