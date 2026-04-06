# TASKLIST_10.4.1_Admin_Operational_Surface_Completion_PROGRESS

## Статус фаз

- [x] Phase 0 — Operational Gaps Baseline
- [x] Phase 1 — Backend Effective Payloads and Trace Schema
- [x] Phase 2 — Diagnostics and Routing Deepening
- [x] Phase 3 — Trace / Debug Viewer
- [x] Phase 4 — Prompt Operations Completion
- [x] Phase 5 — Runtime Truth Completion + Compatibility De-Emphasis

## Phase 0 — Checklist

- [x] Прочитан `PRD_10.4.1_Admin_Operational_Surface_Completion.md`
- [x] Прочитан `TASKLIST_10.4.1_Admin_Operational_Surface_Completion.md`
- [x] Зафиксированы operational gaps в отдельной fixture `v10.4.1-phase0`
- [x] Добавлены inventory-тесты для baseline gaps:
  - [x] diagnostics/routing/prompt/runtime/compatibility gaps inventory
  - [x] trace surface baseline inventory
  - [x] prompt runtime usage metadata gap inventory
- [x] Phase-0 тесты зелёные

## Добавленные файлы (Phase 0)

- `bot_psychologist/tests/fixtures/admin_operational_surface_inventory_v1041_phase0.json`
- `bot_psychologist/tests/inventory/test_admin_operational_gaps_inventory.py`
- `bot_psychologist/tests/inventory/test_trace_surface_baseline_inventory.py`
- `bot_psychologist/tests/inventory/test_prompt_runtime_usage_metadata_gap_inventory.py`

## Запуск тестов (Phase 0)

- `python -m pytest bot_psychologist/tests/inventory/test_admin_operational_gaps_inventory.py bot_psychologist/tests/inventory/test_trace_surface_baseline_inventory.py bot_psychologist/tests/inventory/test_prompt_runtime_usage_metadata_gap_inventory.py -v`

## Phase 1 — Checklist

- [x] Добавлен effective runtime payload endpoint: `/api/admin/runtime/effective`
- [x] Добавлен effective diagnostics payload endpoint: `/api/admin/diagnostics/effective`
- [x] Добавлены trace endpoints: `/api/admin/trace/last`, `/api/admin/trace/recent`
- [x] Добавлен prompt usage metadata endpoint: `/api/admin/prompts/stack-v2/usage`
- [x] Добавлен trace-aware support в `session_store` (`get_last_trace`, `get_recent_traces`)
- [x] Добавлены contract tests v10.4.1 для runtime/diagnostics/trace/prompt-usage
- [x] Contract tests Phase 1 зелёные

## Запуск тестов (Phase 1)

- `cd bot_psychologist; python -m pytest tests/contract/test_admin_runtime_effective_payload_schema_v1041.py tests/contract/test_admin_diagnostics_effective_payload_schema_v1041.py tests/contract/test_admin_trace_payload_schema_v1041.py tests/contract/test_admin_prompt_usage_metadata_schema_v1041.py -v`

## Phase 2 — Checklist

- [x] Diagnostics tab углублён до policy/contract/snapshot surface
- [x] Добавлены cards:
  - [x] Active Diagnostics Contract
  - [x] Current Behavior Policies
  - [x] Last Diagnostics Snapshot
  - [x] Inform/Mixed/User Correction
- [x] Routing tab переведён в policy-first
- [x] Добавлены cards:
  - [x] Current Routing Policy
  - [x] False-Inform Protection
  - [x] Curiosity Decoupling
  - [x] Practice Trigger Rules
  - [x] Safety Override Priority
- [x] Low-level knobs перенесены в `Advanced Routing Controls` (collapsed `<details>`)
- [x] Добавлены UI tests Phase 2 и они зелёные

## Запуск тестов (Phase 2)

- `cd bot_psychologist; python -m pytest tests/ui/test_diagnostics_tab_shows_effective_policy_cards.py tests/ui/test_diagnostics_tab_can_render_last_snapshot.py tests/ui/test_routing_tab_is_policy_first.py tests/ui/test_routing_advanced_controls_collapsed_by_default.py tests/ui/test_false_inform_and_curiosity_decoupling_visible.py -v`

## Phase 3 — Checklist

- [x] Добавлен trace-aware backend surface:
  - [x] `/api/admin/trace/last`
  - [x] `/api/admin/trace/recent`
  - [x] `session_store.get_last_trace()` и `session_store.get_recent_traces()`
- [x] Trace tab переведён с placeholder на real viewer
- [x] Реализованы блоки:
  - [x] Turn header
  - [x] Diagnostics snapshot
  - [x] Routing decision
  - [x] Retrieval pipeline
  - [x] Prompt stack summary
  - [x] Output validation
  - [x] Memory / summary update
  - [x] Flags / degraded / anomalies
- [x] Добавлен recent traces list
- [x] Добавлены состояния:
  - [x] trace unavailable/disabled
  - [x] no trace yet
  - [x] partial trace (safe `?? {}` render blocks)
- [x] Добавлен e2e тест flow last/recent trace
- [x] UI/contract/e2e тесты фазы зелёные

## Запуск тестов (Phase 3)

- `cd bot_psychologist; python -m pytest tests/ui/test_trace_tab_renders_last_turn_trace.py tests/ui/test_trace_tab_renders_recent_traces_list.py tests/ui/test_trace_tab_handles_disabled_state.py tests/ui/test_trace_tab_handles_partial_trace.py tests/e2e/test_admin_trace_viewer_last_turn_flow.py -v`

## Следующий шаг

## Phase 4 — Checklist

- [x] Prompt tab расширен до operational surface:
  - [x] Effective Assembly Preview
  - [x] Last Turn Section Usage
  - [x] Section Metadata (source / derived_from / read_only_reason)
  - [x] Явный индикатор участия текущей секции в last turn (`used in last turn`)
- [x] Prompt usage metadata endpoint используется в UI (`/api/admin/prompts/stack-v2/usage`)
- [x] Добавлены Phase 4 tests:
  - [x] UI: `test_prompt_tab_shows_effective_assembly_preview.py`
  - [x] UI: `test_prompt_tab_shows_readonly_reason.py`
  - [x] UI: `test_prompt_tab_shows_last_turn_section_usage.py`
  - [x] Contract: `test_prompt_stack_usage_metadata_api.py`
  - [x] E2E: `test_prompt_operational_surface_flow.py`
- [x] Phase 4 тесты зелёные

## Запуск тестов (Phase 4)

- `cd bot_psychologist; python -m pytest tests/ui/test_prompt_tab_shows_effective_assembly_preview.py tests/ui/test_prompt_tab_shows_readonly_reason.py tests/ui/test_prompt_tab_shows_last_turn_section_usage.py tests/contract/test_prompt_stack_usage_metadata_api.py tests/e2e/test_prompt_operational_surface_flow.py -v`
- `cd bot_psychologist; python -m pytest tests/contract/test_admin_runtime_effective_payload_schema_v1041.py tests/contract/test_admin_diagnostics_effective_payload_schema_v1041.py tests/contract/test_admin_trace_payload_schema_v1041.py tests/contract/test_admin_prompt_usage_metadata_schema_v1041.py tests/contract/test_prompt_stack_usage_metadata_api.py tests/ui/test_diagnostics_tab_shows_effective_policy_cards.py tests/ui/test_diagnostics_tab_can_render_last_snapshot.py tests/ui/test_routing_tab_is_policy_first.py tests/ui/test_routing_advanced_controls_collapsed_by_default.py tests/ui/test_false_inform_and_curiosity_decoupling_visible.py tests/ui/test_trace_tab_renders_last_turn_trace.py tests/ui/test_trace_tab_renders_recent_traces_list.py tests/ui/test_trace_tab_handles_disabled_state.py tests/ui/test_trace_tab_handles_partial_trace.py tests/ui/test_prompt_tab_shows_effective_assembly_preview.py tests/ui/test_prompt_tab_shows_readonly_reason.py tests/ui/test_prompt_tab_shows_last_turn_section_usage.py tests/e2e/test_admin_trace_viewer_last_turn_flow.py tests/e2e/test_prompt_operational_surface_flow.py -v`

## Следующий шаг

## Phase 5 — Checklist

- [x] Runtime tab расширен до `Effective Runtime Truth` surface:
  - [x] Schema / Versions block (`schema_version`, `admin_schema_version`, `prompt_stack_version`)
  - [x] Diagnostics / Routing block (contract + key routing policies)
  - [x] Trace / Validation block (trace availability + validation status)
  - [x] Grouped Feature Flags block (feature flag grouping from backend truth payload)
- [x] Compatibility де-emphasized:
  - [x] Убран из primary action buttons в header
  - [x] Перенесён в secondary `Advanced` control (dropdown/details)
- [x] Добавлены Phase 5 tests:
  - [x] UI: `test_runtime_tab_shows_effective_runtime_truth.py`
  - [x] UI: `test_compatibility_button_deemphasized.py`
  - [x] E2E: `test_compatibility_hidden_under_advanced_controls.py`
  - [x] E2E: `test_admin_operational_surface_end_to_end.py`
- [x] Phase 5 тесты зелёные

## Запуск тестов (Phase 5)

- `cd bot_psychologist; python -m pytest tests/ui/test_runtime_tab_shows_effective_runtime_truth.py tests/ui/test_compatibility_button_deemphasized.py tests/e2e/test_compatibility_hidden_under_advanced_controls.py tests/e2e/test_admin_operational_surface_end_to_end.py -v`
- `cd bot_psychologist; python -m pytest tests/inventory/test_admin_operational_gaps_inventory.py tests/inventory/test_trace_surface_baseline_inventory.py tests/inventory/test_prompt_runtime_usage_metadata_gap_inventory.py tests/contract/test_admin_runtime_effective_payload_schema_v1041.py tests/contract/test_admin_diagnostics_effective_payload_schema_v1041.py tests/contract/test_admin_trace_payload_schema_v1041.py tests/contract/test_admin_prompt_usage_metadata_schema_v1041.py tests/contract/test_prompt_stack_usage_metadata_api.py tests/ui/test_diagnostics_tab_shows_effective_policy_cards.py tests/ui/test_diagnostics_tab_can_render_last_snapshot.py tests/ui/test_routing_tab_is_policy_first.py tests/ui/test_routing_advanced_controls_collapsed_by_default.py tests/ui/test_false_inform_and_curiosity_decoupling_visible.py tests/ui/test_trace_tab_renders_last_turn_trace.py tests/ui/test_trace_tab_renders_recent_traces_list.py tests/ui/test_trace_tab_handles_disabled_state.py tests/ui/test_trace_tab_handles_partial_trace.py tests/ui/test_prompt_tab_shows_effective_assembly_preview.py tests/ui/test_prompt_tab_shows_readonly_reason.py tests/ui/test_prompt_tab_shows_last_turn_section_usage.py tests/ui/test_runtime_tab_shows_effective_runtime_truth.py tests/ui/test_compatibility_button_deemphasized.py tests/e2e/test_admin_trace_viewer_last_turn_flow.py tests/e2e/test_prompt_operational_surface_flow.py tests/e2e/test_compatibility_hidden_under_advanced_controls.py tests/e2e/test_admin_operational_surface_end_to_end.py -v`

## Итог

PRD/TASKLIST 10.4.1 operational completion закрыт: Diagnostics, Routing, Trace, Prompt, Runtime и Compatibility surface доведены и покрыты inventory/contract/ui/e2e проверками.
