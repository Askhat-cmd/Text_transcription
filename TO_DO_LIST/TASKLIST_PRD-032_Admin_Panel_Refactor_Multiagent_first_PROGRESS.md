# TASKLIST PRD-032 Admin Panel Refactor (Multiagent-first)

## Scope
- Backend: admin overview endpoint, orchestrator config/env sync, agent metrics wiring.
- Frontend: multiagent-first tab layout, overview tab, dedicated agent-prompts tab, legacy tabs collapse.
- Keep existing API compatibility from PRD-031.

## Tasks
- [x] Read PRD-032 and inspect current Admin/API implementation.
- [x] Add `GET /api/admin/overview` in `api/admin_routes.py`.
- [x] Extend `GET /api/admin/orchestrator/config` with `actual_pipeline_mode` and `env_flags`.
- [x] Wire orchestrator metrics/traces in `bot_agent/multiagent/orchestrator.py`.
- [x] Add overview/admin types in `web_ui/src/types/admin.types.ts`.
- [x] Add `getOverview()` in `web_ui/src/services/adminConfig.service.ts`.
- [x] Add `AdminOverviewTab.tsx`.
- [x] Refactor `AdminPanel.tsx`:
  - [x] multiagent-first primary tabs
  - [x] dedicated `agent_prompts` tab
  - [x] legacy tabs in collapsible section
  - [x] mode badge in header
- [x] Extend `OrchestratorTab.tsx` to show actual/env mode data.
- [x] Add/update tests for new admin overview/config contract.

## Checks
- [x] Backend endpoints respond with expected schema.
- [x] Admin panel renders without runtime crash.
- [x] New tabs render (`overview`, `agent prompts`, `agents`, `orchestrator`, `threads`).
- [x] Legacy tabs remain accessible via collapse.

## Tests
- [x] `python -m pytest bot_psychologist/tests/test_admin_multiagent.py -q`
- [x] `npm --prefix bot_psychologist/web_ui run lint`
- [x] `npm --prefix bot_psychologist/web_ui run test` (vitest)

## Notes
- Repo has unrelated dirty files; commit must include only PRD-032 files.
