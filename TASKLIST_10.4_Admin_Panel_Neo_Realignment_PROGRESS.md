# TASKLIST_10.4_Admin_Panel_Neo_Realignment_PROGRESS

Трекер исполнения по `PRD_10.4_Admin_Panel_Neo_Realignment.md` / `TASKLIST_10.4_Admin_Panel_Neo_Realignment.md`.

## Статус фаз

- [x] Phase 0 — Admin Surface Audit Baseline
- [x] Phase 1 — Backend Admin Schema Alignment
- [x] Phase 2 — Primary Information Architecture Rebuild
- [x] Phase 3 — Prompt Tab Realignment
- [x] Phase 4 — Retrieval / Memory / Runtime / Routing Panels Alignment
- [x] Phase 5 — Compatibility, Regression Hardening and Final Verification

---

## Phase 0 — Admin Surface Audit Baseline

### Подзадачи

- [x] Снять inventory текущих admin tabs and groups.
- [x] Классифицировать секции: active / deprecated / misleading / broken.
- [x] Зафиксировать legacy элементы:
  - [x] SD classifier controls
  - [x] user-level prompt groups
  - [x] old decision gate controls
  - [x] path/prompt priority legacy surface
  - [x] `Mode: informational (curious)` prompt artifact
  - [x] prompt fetch failure state
- [x] Зафиксировать текущий backend schema/API payload baseline.
- [x] Добавить inventory tests фазы.
- [x] Прогнать обязательные тесты фазы.

### Артефакты

- Fixture baseline: `bot_psychologist/tests/fixtures/admin_surface_inventory_v104_phase0.json`
- Тесты inventory:
  - `bot_psychologist/tests/inventory/test_admin_surface_section_inventory.py`
  - `bot_psychologist/tests/inventory/test_admin_legacy_visibility_inventory.py`
  - `bot_psychologist/tests/inventory/test_admin_prompt_fetch_failure_inventory.py`

### Результат фазы

- Baseline админ-поверхности зафиксирован.
- Legacy и misleading поверхности отмечены как кандидаты для выноса из primary UI.
- Broken flow `prompt fetch failure` зафиксирован в inventory для последующей правки на Phase 3.

---

## Phase 1 — Backend Admin Schema Alignment

### Подзадачи

- [x] Добавлена backend schema v10.4 endpoint: `/api/admin/config/schema-v104` (+ `/api/v1/admin/...`).
- [x] В schema разделены `editable` и `read_only` секции.
- [x] Для editable полей добавлены explicit markers:
  - [x] `editable`
  - [x] `read_only`
  - [x] `deprecated`
  - [x] `compatibility_only`
- [x] Добавлен `schema_version` для admin surface payload.
- [x] Обновлены export/import с versioned meta (`schema_version`, `schema_family`).
- [x] Добавлен legacy import mapping + safe ignore unknown legacy fields.
- [x] Прогнаны обязательные tests фазы и регрессии admin endpoints.

### Изменённые файлы

- `bot_psychologist/api/admin_routes.py`
- `bot_psychologist/bot_agent/runtime_config.py`
- `bot_psychologist/tests/contract/test_admin_config_schema_v104.py`
- `bot_psychologist/tests/contract/test_admin_export_import_versioning.py`
- `bot_psychologist/tests/contract/test_admin_payload_editable_vs_readonly_markers.py`
- `bot_psychologist/tests/regression/test_legacy_admin_payloads_map_or_ignore_safely.py`

### Тесты фазы

- `python -m pytest tests/contract/test_admin_config_schema_v104.py tests/contract/test_admin_export_import_versioning.py tests/contract/test_admin_payload_editable_vs_readonly_markers.py tests/regression/test_legacy_admin_payloads_map_or_ignore_safely.py -v`
- `python -m pytest tests/test_admin_api.py tests/test_admin_config.py tests/integration/test_admin_config_rollback.py -v`

### Результат фазы

- Backend даёт schema v10.4 с явным разделением editable/read-only/deprecated compatibility-полей.
- Export/import теперь version-aware и устойчивы к legacy payload с неизвестными полями.
- Совместимость с существующими admin endpoint tests сохранена.

---

## Phase 2 — Primary Information Architecture Rebuild

### Подзадачи

- [x] Primary tabs пересобраны под Neo IA:
  - [x] `LLM`
  - [x] `Retrieval`
  - [x] `Diagnostics`
  - [x] `Routing`
  - [x] `Memory`
  - [x] `Prompts`
  - [x] `Runtime`
  - [x] `Trace / Debug`
  - [x] `Compatibility`
- [x] Legacy `storage` и `history` убраны из primary nav и перенесены в `Compatibility`.
- [x] Legacy RoutingTab с old layer stack убран из primary surface.
- [x] Deprecated routing controls скрыты из primary routing panel.
- [x] Добавлены diagnostics/trace read-only панели как operational surface.

### Изменённые файлы

- `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`
- `bot_psychologist/web_ui/src/types/admin.types.ts`
- `bot_psychologist/api/admin_routes.py` (расширенный `/status` для feature flags)
- `bot_psychologist/tests/ui/test_primary_admin_tabs_match_neo_runtime_ia.py`
- `bot_psychologist/tests/ui/test_legacy_routing_stack_hidden_from_primary_surface.py`
- `bot_psychologist/tests/ui/test_sd_and_user_level_not_primary_controls.py`
- `bot_psychologist/tests/ui/test_diagnostics_and_trace_tabs_present.py`

### Тесты фазы

- `python -m pytest tests/ui/test_primary_admin_tabs_match_neo_runtime_ia.py tests/ui/test_legacy_routing_stack_hidden_from_primary_surface.py tests/ui/test_sd_and_user_level_not_primary_controls.py tests/ui/test_diagnostics_and_trace_tabs_present.py -v`
- `python -m pytest tests/test_admin_api.py -v`

### Результат фазы

- Primary IA больше не повторяет legacy tab layout.
- Основная навигация теперь ориентирована на Neo runtime surface.
- Legacy controls перемещены в compatibility-поверхность и не являются primary truth.

---

## Phase 3 — Prompt Tab Realignment

### Подзадачи

- [x] Добавлен admin API surface для prompt stack v2:
  - [x] `GET /api/admin/prompts/stack-v2`
  - [x] `GET /api/admin/prompts/stack-v2/{section}`
  - [x] `PUT /api/admin/prompts/stack-v2/{section}` (только editable секции)
  - [x] `POST /api/admin/prompts/stack-v2/{section}/reset`
  - [x] v1 aliases для всех новых endpoints
- [x] Prompt tab фронтенда переключён на stack v2 API вместо legacy `/prompts`.
- [x] Legacy prompt groups (SD/user-level/mode artifact) убраны из primary prompt surface.
- [x] Добавлен read-only режим для runtime-derived stack sections.
- [x] Добавлена валидация перед save (минимальная длина).
- [x] Улучшен fetch error flow:
  - [x] отдельный `promptError` в hook
  - [x] actionable retry-кнопка в Prompt UI
- [x] Добавлены поля версионирования в prompt meta (`version`, `updated_at`, `stack_version`).

### Изменённые файлы

- `bot_psychologist/api/admin_routes.py`
- `bot_psychologist/web_ui/src/services/adminConfig.service.ts`
- `bot_psychologist/web_ui/src/hooks/useAdminConfig.ts`
- `bot_psychologist/web_ui/src/components/admin/PromptEditorPanel.tsx`
- `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`
- `bot_psychologist/web_ui/src/types/admin.types.ts`
- `bot_psychologist/tests/contract/test_prompt_admin_api_matches_prompt_stack_v2.py`
- `bot_psychologist/tests/ui/test_prompt_stack_v2_groups_rendered.py`
- `bot_psychologist/tests/ui/test_legacy_prompt_groups_not_primary.py`
- `bot_psychologist/tests/ui/test_prompt_fetch_error_state_actionable.py`
- `bot_psychologist/tests/ui/test_prompt_preview_and_versioning_controls.py`

### Тесты фазы

- `python -m pytest tests/ui/test_prompt_stack_v2_groups_rendered.py tests/ui/test_legacy_prompt_groups_not_primary.py tests/ui/test_prompt_fetch_error_state_actionable.py tests/ui/test_prompt_preview_and_versioning_controls.py tests/contract/test_prompt_admin_api_matches_prompt_stack_v2.py -v`
- `python -m pytest tests/test_admin_api.py tests/test_admin_config.py tests/integration/test_admin_config_rollback.py -v`

### Результат фазы

- Prompt tab теперь опирается на prompt stack v2 surface.
- Legacy prompt groups больше не primary truth в админке.
- Ошибка загрузки prompt секции стала actionable (retry вместо тупикового состояния).

---

## Phase 4 — Retrieval / Memory / Runtime / Routing Panels Alignment

### Подзадачи

- [x] Retrieval panel выровнен под реальные этапы pipeline:
  - initial top-k
  - relevance threshold
  - rerank enable/model/top-k
  - confidence cap
  - final blocks semantics
  - degraded mode note
- [x] Diagnostics panel отражает diagnostics v1 contract (interaction/state/request/core theme).
- [x] Routing panel отражает Neo route taxonomy:
  - safe_override, regulate, reflect, practice, inform, contact_hold
- [x] Legacy routing mental model убран из primary routing surface.
- [x] Memory panel выровнен под summary/snapshot model (v1.1 и fallback/staleness note).
- [x] Runtime panel показывает real status + feature flags snapshot.

### Изменённые файлы

- `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`
- `bot_psychologist/api/admin_routes.py`
- `bot_psychologist/web_ui/src/types/admin.types.ts`
- `bot_psychologist/tests/ui/test_retrieval_panel_matches_actual_pipeline_stages.py`
- `bot_psychologist/tests/ui/test_diagnostics_panel_matches_v1_runtime_contract.py`
- `bot_psychologist/tests/ui/test_routing_panel_matches_neo_route_taxonomy.py`
- `bot_psychologist/tests/ui/test_memory_panel_matches_summary_snapshot_model.py`
- `bot_psychologist/tests/ui/test_runtime_panel_shows_real_feature_flags_and_status.py`

### Тесты фазы

- `python -m pytest tests/ui/test_retrieval_panel_matches_actual_pipeline_stages.py tests/ui/test_diagnostics_panel_matches_v1_runtime_contract.py tests/ui/test_routing_panel_matches_neo_route_taxonomy.py tests/ui/test_memory_panel_matches_summary_snapshot_model.py tests/ui/test_runtime_panel_shows_real_feature_flags_and_status.py -v`

### Результат фазы

- Retrieval/memory/runtime/routing/diagnostics панели отражают фактический Neo runtime flow, а не legacy-семантику.

---

## Phase 5 — Compatibility, Regression Hardening and Final Verification

### Подзадачи

- [x] Compatibility surface скрыт по умолчанию, доступен через explicit toggle.
- [x] Проверены export/import с versioned schema metadata.
- [x] Добавлен e2e/contract набор на новые admin surface guarantees.
- [x] Проверена регрессионная совместимость существующих admin API tests.
- [x] Прогнан consolidated regression pack для фаз 0–5.

### Изменённые файлы

- `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`
- `bot_psychologist/tests/e2e/test_admin_ui_loads_without_legacy_primary_surface.py`
- `bot_psychologist/tests/e2e/test_prompt_fetch_and_retry_flow.py`
- `bot_psychologist/tests/e2e/test_admin_export_import_with_schema_versioning.py`
- `bot_psychologist/tests/e2e/test_runtime_status_and_flags_visible_in_admin.py`
- `bot_psychologist/tests/e2e/test_compatibility_section_hidden_by_default.py`

### Тесты фазы

- `python -m pytest tests/e2e/test_admin_ui_loads_without_legacy_primary_surface.py tests/e2e/test_prompt_fetch_and_retry_flow.py tests/e2e/test_admin_export_import_with_schema_versioning.py tests/e2e/test_runtime_status_and_flags_visible_in_admin.py tests/e2e/test_compatibility_section_hidden_by_default.py -v`
- `python -m pytest tests/inventory/test_admin_surface_section_inventory.py tests/inventory/test_admin_legacy_visibility_inventory.py tests/inventory/test_admin_prompt_fetch_failure_inventory.py tests/contract/test_admin_config_schema_v104.py tests/contract/test_admin_export_import_versioning.py tests/contract/test_admin_payload_editable_vs_readonly_markers.py tests/contract/test_prompt_admin_api_matches_prompt_stack_v2.py tests/regression/test_legacy_admin_payloads_map_or_ignore_safely.py tests/ui/test_primary_admin_tabs_match_neo_runtime_ia.py tests/ui/test_legacy_routing_stack_hidden_from_primary_surface.py tests/ui/test_sd_and_user_level_not_primary_controls.py tests/ui/test_diagnostics_and_trace_tabs_present.py tests/ui/test_prompt_stack_v2_groups_rendered.py tests/ui/test_legacy_prompt_groups_not_primary.py tests/ui/test_prompt_fetch_error_state_actionable.py tests/ui/test_prompt_preview_and_versioning_controls.py tests/ui/test_retrieval_panel_matches_actual_pipeline_stages.py tests/ui/test_diagnostics_panel_matches_v1_runtime_contract.py tests/ui/test_routing_panel_matches_neo_route_taxonomy.py tests/ui/test_memory_panel_matches_summary_snapshot_model.py tests/ui/test_runtime_panel_shows_real_feature_flags_and_status.py tests/e2e/test_admin_ui_loads_without_legacy_primary_surface.py tests/e2e/test_prompt_fetch_and_retry_flow.py tests/e2e/test_admin_export_import_with_schema_versioning.py tests/e2e/test_runtime_status_and_flags_visible_in_admin.py tests/e2e/test_compatibility_section_hidden_by_default.py tests/test_admin_api.py tests/test_admin_config.py tests/integration/test_admin_config_rollback.py -v`

### Результат фазы

- Primary admin surface выровнен под Neo runtime.
- Legacy primary surface убран.
- Prompt stack v2, schema versioning, runtime truth и retry-fallback flow закреплены тестами.
