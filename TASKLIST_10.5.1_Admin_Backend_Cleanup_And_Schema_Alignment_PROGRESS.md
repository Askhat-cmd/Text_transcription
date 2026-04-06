# TASKLIST_10.5.1_Admin_Backend_Cleanup_And_Schema_Alignment_PROGRESS

## Статус фаз

- [x] Phase 0 — Residual Boundary Audit
- [x] Phase 1 — Backend Trace Responsibility Cleanup
- [x] Phase 2 — Schema / Version Alignment
- [x] Phase 3 — Regression Hardening and Final Boundary Verification

---

## Phase 0 — Checklist

- [x] Прочитан `PRD_10.5.1_Admin_Backend_Cleanup_And_Schema_Alignment.md`
- [x] Прочитан `TASKLIST_10.5.1_Admin_Backend_Cleanup_And_Schema_Alignment.md`
- [x] Добавлен fixture: `bot_psychologist/tests/fixtures/admin_backend_boundary_v1051_phase0.json`
- [x] Добавлены inventory tests:
  - [x] `bot_psychologist/tests/inventory/test_admin_backend_residual_trace_boundary_inventory.py`
  - [x] `bot_psychologist/tests/inventory/test_admin_schema_version_mismatch_inventory.py`
- [x] Inventory тесты зелёные (`4 passed`)

## Phase 1 — Checklist

- [x] В `bot_psychologist/api/admin_routes.py` убрана зависимость `runtime/effective` от `last_trace`
- [x] Удалены backend builders глубокой trace-ответственности:
  - [x] `_build_trace_turn_payload`
  - [x] `_build_prompt_stack_usage_payload`
  - [x] `_extract_prompt_usage_from_trace`
- [x] `/api/admin/trace/last` переведён в deprecated (HTTP 410)
- [x] `/api/admin/trace/recent` переведён в deprecated (HTTP 410)
- [x] `/api/admin/prompts/stack-v2/usage` переведён в deprecated (HTTP 410)
- [x] Обновлён Runtime payload trace block в capability/status-форму:
  - [x] `developer_trace_supported`
  - [x] `developer_trace_enabled`
  - [x] `developer_trace_mode_available`
- [x] В frontend удалены stale admin API вызовы:
  - [x] `getTraceLast`
  - [x] `getTraceRecent`
  - [x] `getPromptStackUsage`
- [x] Удалены stale типы:
  - [x] `AdminTraceLastResponse`
  - [x] `AdminTraceRecentResponse`
  - [x] `PromptStackUsageResponse`

## Phase 2 — Checklist

- [x] В backend выровнены версии:
  - [x] `ADMIN_SCHEMA_VERSION = "10.5"`
  - [x] `ADMIN_EFFECTIVE_SCHEMA_VERSION = "10.5.1"`
- [x] Обновлены контрактные проверки на семейство `10.5.x`
- [x] Выравнены export/import metadata проверки на `10.5`
- [x] Runtime UI оставлен в system-level формате и отображает актуальные schema/version поля

## Phase 3 — Checklist

- [x] Добавлен UI boundary test:
  - [x] `tests/ui/test_admin_ui_and_admin_api_share_management_only_boundary.py`
- [x] Добавлен regression test:
  - [x] `tests/regression/test_admin_management_tabs_still_load_after_backend_cleanup.py`
- [x] Добавлен regression test:
  - [x] `tests/regression/test_prompt_management_and_runtime_status_still_work.py`
- [x] Подтверждено: management tabs продолжают работать после cleanup
- [x] Подтверждено: prompt management + runtime status не сломаны

---

## Прогоны тестов

- [x] `python -m pytest tests/contract/test_admin_trace_endpoints_removed_or_deprecated.py tests/contract/test_admin_runtime_payload_not_derived_from_last_trace.py tests/regression/test_admin_runtime_effective_renders_without_session_trace.py tests/ui/test_runtime_tab_system_level_only.py -v`
  - Результат: `8 passed`

- [x] `python -m pytest tests/contract/test_admin_schema_versions_aligned_to_105_family.py tests/ui/test_runtime_tab_displays_updated_admin_schema_versions.py tests/contract/test_admin_export_import_metadata_uses_105_family.py tests/contract/test_admin_runtime_effective_payload_schema_v1041.py tests/contract/test_admin_diagnostics_effective_payload_schema_v1041.py tests/contract/test_admin_config_schema_v104.py tests/contract/test_admin_export_import_versioning.py tests/contract/test_admin_trace_payload_schema_v1041.py tests/contract/test_admin_prompt_usage_metadata_schema_v1041.py tests/contract/test_prompt_stack_usage_metadata_api.py tests/ui/test_prompt_tab_shows_last_turn_section_usage.py -v`
  - Результат: `23 passed`

- [x] `python -m pytest tests/ui/test_admin_ui_and_admin_api_share_management_only_boundary.py tests/regression/test_admin_management_tabs_still_load_after_backend_cleanup.py tests/regression/test_prompt_management_and_runtime_status_still_work.py -v`
  - Результат: `3 passed`

- [x] `python -m pytest tests/contract/test_admin_trace_endpoints_removed_or_deprecated.py tests/contract/test_admin_runtime_payload_not_derived_from_last_trace.py tests/regression/test_admin_runtime_effective_renders_without_session_trace.py tests/ui/test_runtime_tab_system_level_only.py tests/contract/test_admin_schema_versions_aligned_to_105_family.py tests/ui/test_runtime_tab_displays_updated_admin_schema_versions.py tests/contract/test_admin_export_import_metadata_uses_105_family.py tests/ui/test_admin_ui_and_admin_api_share_management_only_boundary.py tests/regression/test_admin_management_tabs_still_load_after_backend_cleanup.py tests/regression/test_prompt_management_and_runtime_status_still_work.py -v`
  - Результат: `15 passed`

---

## Итого

- [x] PRD 10.5.1 закрыт по backend boundary cleanup
- [x] Admin backend больше не несёт deep trace responsibility как рабочую поверхность
- [x] Runtime effective отвязан от `last_trace`
- [x] Schema/version выровнены под `10.5.x`
- [x] Management operability сохранена
