# TASKLIST_10.4_Admin_Panel_Neo_Realignment

## Назначение
Этот документ — пошаговый execution-чеклист для IDE-агента, который внедряет `PRD_10.4_Admin_Panel_Neo_Realignment.md`.

Главная цель итерации:
**полностью выровнять веб-админку под реальный Neo runtime, убрать misleading legacy UI и сделать admin surface честным operational-инструментом.**

Главное правило:
**не переходить к следующей фазе, пока текущая не завершена, её UI/contract tests не зелёные, а primary admin surface не перестала врать о системе.**

---

# 0. Глобальные правила выполнения

## Правило 1. Это admin-surface iteration, а не runtime rewrite
Запрещено раздувать scope:
- новой core runtime-архитектурой;
- новым retrieval engine;
- новой memory-философией;
- новой большой продуктовой логикой;
- “редизайном ради красоты”.

## Правило 2. Работа строго по фазам
Выполнять только последовательно:

- Phase 0
- Phase 1
- Phase 2
- Phase 3
- Phase 4
- Phase 5

Не смешивать backend schema alignment, IA rebuild и prompt tab refactor в один хаотичный коммит.

## Правило 3. Stop-the-line
Если обязательные tests падают:
- остановиться;
- исправить корень проблемы;
- повторно прогнать тесты;
- не переходить к следующей фазе.

## Правило 4. Admin UI must reflect runtime truth
Если UI показывает:
- SD classifier,
- user-level adaptation,
- old Decision Gate,
- old routing stack,
как primary active surface, значит фаза не завершена.

## Правило 5. Prefer hidden compatibility over misleading primacy
Если legacy controls ещё нужны:
- увести их в compatibility/deprecated section;
- не оставлять их в primary tabs.

## Правило 6. Editable != safe by default
То, что нельзя безопасно редактировать через UI, лучше оставить:
- read-only,
- derived,
- inspectable,
чем фальшиво editable.

---

# 1. PHASE 0 — Admin Surface Audit Baseline

## Цель
Зафиксировать текущее состояние админки и классифицировать legacy/active/broken sections.

## Сделать
- Снять inventory current admin tabs and groups.
- Для каждой вкладки определить:
  - active and correct
  - deprecated but visible
  - misleading
  - broken
- Зафиксировать конкретные legacy элементы:
  - SD classifier controls
  - user-level prompt groups
  - old decision gate controls
  - path/prompt priority legacy surface
  - `Mode: informational (curious)` prompt artifact
  - prompt fetch failure state
- Зафиксировать текущий backend schema / API payload shape для admin UI.
- Собрать before-screenshots / before-state fixtures.

## Проверить
- Есть карта текущих секций.
- Есть классификация active vs deprecated vs misleading.
- Есть список must-remove/must-hide элементов.

## Тесты
- `tests/inventory/test_admin_surface_section_inventory.py`
- `tests/inventory/test_admin_legacy_visibility_inventory.py`
- `tests/inventory/test_admin_prompt_fetch_failure_inventory.py`

## Acceptance Criteria
- Admin baseline formalized.
- Legacy primary surface clearly identified.
- Broken flows documented.

---

# 2. PHASE 1 — Backend Admin Schema Alignment

## Цель
Сделать backend schema источником истины для новой админки.

## Сделать
- Определить admin config schema v10.4.
- Разделить в schema:
  - editable config
  - read-only runtime status
  - derived/debug info
  - deprecated compatibility fields
- Добавить schema version.
- Добавить validation.
- Добавить explicit markers:
  - editable
  - read_only
  - deprecated
  - compatibility_only
- Обновить export/import под versioned schema.
- Сделать mapping старых payloads в новую схему или безопасное игнорирование legacy полей.

## Проверить
- Frontend больше не зависит от legacy static assumptions.
- Backend возвращает типизированный payload.
- Export/import schema versioning работает.

## Тесты
- `tests/contract/test_admin_config_schema_v104.py`
- `tests/contract/test_admin_export_import_versioning.py`
- `tests/contract/test_admin_payload_editable_vs_readonly_markers.py`
- `tests/regression/test_legacy_admin_payloads_map_or_ignore_safely.py`

## Negative Tests
- old export payload with SD fields;
- old export payload with user-level sections;
- unknown deprecated field;
- invalid editable value.

## Acceptance Criteria
- Backend schema v10.4 defined and validated.
- Editable vs status vs deprecated clearly separated.
- Frontend can render from schema truth rather than legacy assumptions.

---

# 3. PHASE 2 — Primary Information Architecture Rebuild

## Цель
Пересобрать основную навигацию и вкладки вокруг Neo runtime truth.

## Сделать
- Перестроить primary tabs под Neo runtime:
  - LLM
  - Retrieval
  - Diagnostics
  - Routing
  - Memory
  - Prompts
  - Runtime
  - Trace / Debug
  - Compatibility (optional hidden/advanced)
- Убрать из primary IA:
  - SD classifier section
  - old decision gate
  - old layer-by-layer routing stack
  - user-level adaptation controls
  - path/prompt priority legacy logic
- Добавить новую Diagnostics surface.
- Добавить Trace/Debug surface.
- Если compatibility нужна — спрятать в отдельную advanced секцию.

## Проверить
- Primary navigation больше не рассказывает старую историю про систему.
- Оператор видит Neo runtime concepts.
- Legacy controls не торчат на первом уровне.

## Тесты
- `tests/ui/test_primary_admin_tabs_match_neo_runtime_ia.py`
- `tests/ui/test_legacy_routing_stack_hidden_from_primary_surface.py`
- `tests/ui/test_sd_and_user_level_not_primary_controls.py`
- `tests/ui/test_diagnostics_and_trace_tabs_present.py`

## Negative Tests
- old tab config fallback;
- hidden compatibility section accidentally shown as primary;
- no-data state for new tabs.

## Acceptance Criteria
- Primary IA rebuilt.
- Legacy mental model removed from primary surface.
- Neo concepts visible at top level.

---

# 4. PHASE 3 — Prompt Tab Realignment

## Цель
Перевести Prompt UI с legacy prompt library на prompt stack v2.

## Сделать
- Убрать primacy legacy prompt groups:
  - SD prompts
  - user-level prompts
  - `Mode: informational (curious)` as active artifact
- Отобразить prompt stack v2 groups:
  - `AA_SAFETY`
  - `A_STYLE_POLICY`
  - `CORE_IDENTITY`
  - `CONTEXT_MEMORY`
  - `DIAGNOSTIC_CONTEXT`
  - `RETRIEVED_CONTEXT`
  - `TASK_INSTRUCTION`
- Добавить support for variants/modifiers:
  - inform-rich
  - mixed-query
  - first-turn
  - user-correction
  - safe override
- Добавить:
  - preview
  - versioning
  - diff
  - validate before save
  - retry on fetch failure
  - actionable error state instead of bare `Failed to fetch`
- Сделать loading/error state inspectable.

## Проверить
- Prompt UI показывает текущую активную архитектуру.
- Legacy prompt groups не являются primary truth.
- Failed fetch state перестал быть тупиковой красной строкой.

## Тесты
- `tests/ui/test_prompt_stack_v2_groups_rendered.py`
- `tests/ui/test_legacy_prompt_groups_not_primary.py`
- `tests/ui/test_prompt_fetch_error_state_actionable.py`
- `tests/ui/test_prompt_preview_and_versioning_controls.py`
- `tests/contract/test_prompt_admin_api_matches_prompt_stack_v2.py`

## Negative Tests
- backend prompt fetch failure;
- empty prompt registry;
- deprecated prompt groups still present in payload;
- prompt save validation failure.

## Acceptance Criteria
- Prompt tab aligned with stack v2.
- Legacy prompt primacy removed.
- Prompt fetch error flow fixed and actionable.

---

# 5. PHASE 4 — Retrieval / Memory / Runtime / Routing Panels Alignment

## Цель
Сделать рабочие панели понятными и соответствующими фактическому Neo pipeline.

## Сделать

### Retrieval
- Переименовать и структурировать retrieval controls:
  - initial top-k
  - minimum relevance threshold
  - rerank enabled
  - rerank model
  - rerank top-k
  - confidence caps
  - final capped blocks
  - knowledge source
  - degraded mode/fallback note
- Объяснить difference between retrieval stages.

### Diagnostics
- Добавить diagnostics v1 surface:
  - interaction_mode
  - nervous_system_state
  - request_function
  - core_theme behavior
  - informational narrowing
  - mixed-query policy
  - user correction protocol

### Routing
- Отобразить real route taxonomy:
  - safe_override
  - regulate
  - reflect
  - practice
  - inform
  - contact_hold
- Показать deterministic route resolver status.
- Показать false-inform protection / curiosity decoupling state.
- Убрать old decision gate mental model.

### Memory
- Отразить summary/snapshot/semantic memory model:
  - history depth
  - semantic memory
  - summary enabled
  - summary interval
  - summary max length
  - snapshot v1.1
  - staleness / fallback policy summary

### Runtime
- Показать:
  - active runtime version
  - degraded mode
  - blocks loaded
  - feature flags
  - prompt stack enabled
  - output validation enabled
  - diagnostics enabled
  - route resolver enabled
  - source of truth summary

## Проверить
- Панели объясняют реальную систему.
- Оператор видит effective values, а не разрозненные числа без контекста.
- Нет misleading labels from old architecture.

## Тесты
- `tests/ui/test_retrieval_panel_matches_actual_pipeline_stages.py`
- `tests/ui/test_diagnostics_panel_matches_v1_runtime_contract.py`
- `tests/ui/test_routing_panel_matches_neo_route_taxonomy.py`
- `tests/ui/test_memory_panel_matches_summary_snapshot_model.py`
- `tests/ui/test_runtime_panel_shows_real_feature_flags_and_status.py`

## Negative Tests
- partial backend data for one panel;
- feature flag missing;
- degraded mode active;
- no semantic memory enabled.

## Acceptance Criteria
- Retrieval/memory/runtime/routing panels aligned with actual system.
- No major misleading legacy labels remain.
- Effective values and state are visible.

---

# 6. PHASE 5 — Compatibility, Regression Hardening and Final Verification

## Цель
Закрыть переход безопасно и проверить, что админка перестала врать без поломки useful admin workflows.

## Сделать
- Если нужно, добавить hidden/deprecated Compatibility section.
- Проверить export/import on new schema.
- Проверить rollback/versioning.
- Удалить dead admin-only legacy UI code where safe.
- Прогнать full admin UI regression pack.
- Сверить final UI against real runtime behavior.
- Обновить admin docs / operator notes / migration notes.

## E2E Tests
- `tests/e2e/test_admin_ui_loads_without_legacy_primary_surface.py`
- `tests/e2e/test_prompt_fetch_and_retry_flow.py`
- `tests/e2e/test_admin_export_import_with_schema_versioning.py`
- `tests/e2e/test_runtime_status_and_flags_visible_in_admin.py`
- `tests/e2e/test_compatibility_section_hidden_by_default.py`

## Log / Manual Verification
Проверить вручную или automation-assisted:
- no SD/user-level/Decision Gate in primary operational tabs;
- prompt tab shows stack v2;
- routing tab shows Neo taxonomy;
- memory tab shows summary/snapshot mental model;
- failed fetch is actionable;
- compatibility view, if exists, is hidden/deprecated by default.

## Final Acceptance Criteria
Одновременно должно быть верно всё:
- primary admin UI aligned with Neo runtime;
- legacy primary surface removed;
- prompt tab realigned;
- runtime/memory/routing/diagnostics panels truthful;
- admin schema versioned and safe;
- export/import works;
- UI tests pass.

---

# 7. Рекомендуемый формат коммитов

- `phase-0: add admin surface inventory and legacy visibility baseline`
- `phase-1: introduce admin schema v104 and config versioning`
- `phase-2: rebuild primary admin information architecture for neo runtime`
- `phase-3: realign prompt tab to prompt stack v2 and fix fetch flow`
- `phase-4: align retrieval diagnostics routing memory and runtime panels`
- `phase-5: add compatibility gate regression hardening and final verification`

---

# 8. Definition of Done for IDE Agent

Работа по PRD_10.4 считается завершённой только если:
- все phase acceptance criteria закрыты;
- admin UI больше не показывает legacy architecture как primary truth;
- prompt fetch failures handled properly;
- runtime/memory/routing/diagnostics panels align with actual system;
- backend schema versioned and validated;
- export/import and rollback safe;
- UI and contract tests зелёные.

---

# 9. Финальная инструкция IDE-агенту

Работай как инженер operational surface realignment.

Твоя задача в этой итерации:
- не просто “освежить интерфейс”;
- а сделать так, чтобы оператор через админку видел и настраивал именно ту систему, которая реально работает.

После 10.4 веб-админка должна перестать быть музейной витриной legacy-архитектуры и стать рабочей панелью управления Neo MindBot.
