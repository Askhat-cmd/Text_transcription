# TASKLIST PRD-031 — Web Admin Multiagent (Progress)

## Контекст
- PRD: `TO_DO_LIST/PRD-031-Web-Admin-Multiagent.md`
- Дата старта: 2026-05-01
- Статус: Implemented (code + auto tests), pending manual UI smoke

## Этап 1 — Backend (`api/admin_routes.py`)
- [x] Добавить импорты для multiagent (os/Path/datetime/orchestrator/thread_storage)
- [x] Добавить in-memory store метрик/трейсов/режима
- [x] Добавить helper `_compute_agent_metrics()`
- [x] Добавить endpoints:
  - [x] `GET /api/admin/agents/status`
  - [x] `POST /api/admin/agents/{agent_id}/toggle`
  - [x] `POST /api/admin/agents/metrics/record`
  - [x] `GET/PATCH /api/admin/orchestrator/config`
  - [x] `GET/POST /api/admin/agents/traces`
  - [x] `GET/DELETE /api/admin/threads`
  - [x] `GET/PUT/POST /api/admin/agents/{agent_id}/prompts`

## Этап 2 — Web types + service + hook
- [x] Расширить `web_ui/src/types/admin.types.ts`
- [x] Расширить `web_ui/src/services/adminConfig.service.ts`
- [x] Создать `web_ui/src/hooks/useAgents.ts`

## Этап 3 — Admin UI
- [x] Создать `AgentCard.tsx`
- [x] Создать `AgentsTab.tsx`
- [x] Создать `OrchestratorTab.tsx`
- [x] Создать `ThreadsTab.tsx`
- [x] Создать `AgentPromptEditorPanel.tsx` (Phase 2, без wiring)
- [x] Интегрировать 3 вкладки в `AdminPanel.tsx`

## Этап 4 — Debug UI
- [x] Обновить `PipelineFunnel.tsx` (multiagent stages)
- [x] Обновить `SessionTracePanel.tsx` (Agent в history)
- [x] Обновить `LLMPayloadPanel.tsx` (`agent_id` badge)

## Этап 5 — Тесты
- [x] Добавить `bot_psychologist/tests/test_admin_multiagent.py`
- [x] Добавить `web_ui/src/hooks/useAgents.test.ts`
- [x] Прогнать backend тесты PRD-031
- [x] Прогнать frontend unit tests/hook tests
- [x] Прогнать `npx tsc --noEmit`

## Фактические прогоны
- [x] `python -m py_compile bot_psychologist/api/admin_routes.py bot_psychologist/tests/test_admin_multiagent.py`
- [x] `bot_psychologist/.venv/Scripts/python -m pytest -q tests/test_admin_multiagent.py tests/test_admin_api.py` → `21 passed`
- [x] `web_ui: npm run test -- --run src/hooks/useAgents.test.ts` → `4 passed`
- [x] `web_ui: npm run lint` (`tsc --noEmit`) → OK

## Финальные чеки
- [ ] Ручной UI smoke: вкладки **🤖 Агенты / 🎭 Оркестратор / 🧵 Треды** в AdminPanel
- [ ] Ручной UI smoke: существующие 8 вкладок не сломаны
- [ ] Ручной UI smoke: в trace видны добавленные поля (PipelineFunnel/Agent/agent_id)
