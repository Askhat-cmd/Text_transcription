# TASKLIST PRD-037 — Admin/Web Runtime Contract Cleanup

## Статус
- [x] PRD изучен
- [x] Найдены затронутые backend/web/tests файлы
- [x] Backend runtime contract переведен в multiagent-only
- [x] Legacy/hybrid mode selection отключен в Admin API
- [x] Web UI очищен от selectable legacy/hybrid режимов
- [x] Thread manager статус помечен как heuristic / model not effective
- [x] Добавлены/обновлены тесты по новому контракту
- [x] Прогнаны целевые backend/web проверки

## Backend
- [x] `bot_psychologist/api/admin_routes.py`
  - [x] `_compute_env_pipeline_mode` и `_compute_active_runtime` не выводят legacy/hybrid как active
  - [x] helper `_legacy_status_payload()`
  - [x] helper compatibility payload (`pipeline_mode=multiagent_only`, read_only)
  - [x] `/api/admin/runtime/effective` дополнен runtime/legacy/compatibility/agents contract
  - [x] `/api/admin/orchestrator/config` выдает multiagent-only contract
  - [x] `PATCH /api/admin/orchestrator/config`:
    - [x] `legacy_adaptive|hybrid|classic` => 422
    - [x] `full_multiagent` alias => `multiagent_only`
  - [x] `/api/admin/overview` отражает multiagent-only
  - [x] `/api/admin/agents/status` отражает multiagent-only
  - [x] `/api/admin/agents/llm-config` дополняет `thread_manager` полями `kind=heuristic`, `llm_model_effective=false`

## Web UI
- [x] `bot_psychologist/web_ui/src/types/admin.types.ts`
  - [x] Уточнены типы runtime/pipeline_mode под multiagent-only
  - [x] Добавлены поля `legacy`, `compatibility`, `runtime_entrypoint`
- [x] `bot_psychologist/web_ui/src/services/adminConfig.service.ts`
  - [x] patch orchestrator mode типы под `multiagent_only|full_multiagent`
- [x] `bot_psychologist/web_ui/src/hooks/useOrchestrator.ts`
  - [x] тип PipelineMode обновлен
  - [x] success message нормализован
- [x] `bot_psychologist/web_ui/src/components/admin/OrchestratorTab.tsx`
  - [x] убраны legacy/hybrid кнопки
  - [x] runtime badges: multiagent/entrypoint/fallback-disabled
- [x] `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`
  - [x] Header badge: `multiagent`
  - [x] убран `Legacy Epoch 1-3` label (заменен на `Advanced Controls`)
- [x] `bot_psychologist/web_ui/src/components/admin/AdminOverviewTab.tsx`
  - [x] badge и поля по multiagent-only
- [x] `bot_psychologist/web_ui/src/components/admin/AgentsTab.tsx`
  - [x] `thread_manager` помечен `heuristic / model reserved`

## Тесты
- [x] `bot_psychologist/tests/test_admin_multiagent.py`
  - [x] обновлены ожидания по runtime/mode
  - [x] добавлены проверки reject legacy/hybrid и alias full_multiagent
- [x] `bot_psychologist/tests/test_admin_runtime_contract.py`
  - [x] новый контракт runtime/effective + mode patch rules
  - [x] проверка thread_manager heuristic contract
- [x] `bot_psychologist/tests/inventory/test_admin_runtime_contract_no_mojibake.py`
  - [x] guard на mojibake в targeted runtime/admin segments
- [x] `bot_psychologist/web_ui/src/hooks/useOrchestrator.test.ts`
  - [x] актуализированы mode expectations
- [x] `bot_psychologist/web_ui/src/hooks/useAgentStatus.test.ts`
  - [x] добавлен `active_runtime` в моки для строгой типизации

## Прогоны
- [x] `.venv\Scripts\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py -q` → `27 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_admin_runtime_contract.py -q` → `3 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/inventory/test_admin_runtime_contract_no_mojibake.py -q` → `1 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/multiagent -q` → `181 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/api -q` → `31 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_llm_streaming.py -q` → `7 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/telegram_adapter -q` → `44 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/inventory/test_no_silent_legacy_fallback.py -q` → `1 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/inventory/test_runtime_cutover_no_legacy_entrypoints.py -q` → `4 passed`
- [x] `cd bot_psychologist/web_ui && npm run build` → success (есть только non-blocking warnings по chunk size/dynamic import)
