# TASKLIST_10.5.1_Admin_Backend_Cleanup_And_Schema_Alignment.md

## Назначение
Этот документ — пошаговый execution-чеклист для IDE-агента, который внедряет `PRD_10.5.1_Admin_Backend_Cleanup_And_Schema_Alignment.md`.

Главная цель итерации:
**дочистить backend-границы админки после успешного PRD 10.5, убрать остаточную trace-responsibility из admin backend и выровнять schema/version naming под 10.5.x.**

Главное правило:
**не переходить к следующей фазе, пока текущая не завершена, её contract/regression tests не зелёные, а admin backend не стал чище по responsibility boundary.**

---

# 0. Глобальные правила выполнения

## Правило 1. Это corrective patch, а не новый большой этап
Запрещено раздувать scope:
- новым developer trace UI;
- новым chat trace backend;
- исправлением `json_fallback`;
- новой retrieval/data-source архитектурой;
- глобальным redesign admin UI.

## Правило 2. Работа строго по фазам
Выполнять только последовательно:

- Phase 0
- Phase 1
- Phase 2
- Phase 3

Не смешивать backend trace cleanup, schema alignment и unrelated runtime fixes в один хаотичный коммит.

## Правило 3. Stop-the-line
Если обязательные tests фазы падают:
- остановиться;
- исправить корень проблемы;
- повторно прогнать тесты;
- не переходить дальше.

## Правило 4. Не смешивать сюда `json_fallback`
Проблема `json_fallback` **out-of-scope** для 10.5.1.  
Если она остаётся — оформить отдельно потом.

## Правило 5. `/admin` backend должен соответствовать `/admin` UI
Если frontend уже management-only, backend тоже должен быть management-only.

## Правило 6. System-level truth must remain
Убирая residual trace responsibility, нельзя ломать:
- runtime health visibility;
- feature flags visibility;
- schema/version visibility;
- prompt management;
- remote configuration usability.

---

# 1. PHASE 0 — Residual Boundary Audit

## Цель
Зафиксировать все оставшиеся backend-хвосты, которые нарушают новую admin boundary.

## Сделать
- Проинвентаризировать `api/admin_routes.py`.
- Отметить всё, что still looks like deep trace responsibility:
  - `/api/admin/trace/last`
  - `/api/admin/trace/recent`
  - `_build_trace_turn_payload(...)`
  - `runtime/effective` dependence on `last_trace`
- Зафиксировать version/schema mismatches:
  - `ADMIN_SCHEMA_VERSION`
  - `ADMIN_EFFECTIVE_SCHEMA_VERSION`
  - UI runtime display of schema versions
- Проверить текущие frontend dependencies на trace-heavy admin endpoints.
- Сохранить baseline notes:
  - что используется реально,
  - что уже orphaned,
  - что нужно remove vs deprecate.

## Проверить
- Есть список residual trace surfaces.
- Есть список version/schema mismatches.
- Понятно, есть ли активные frontend callers к admin trace endpoints.

## Тесты
- `tests/inventory/test_admin_backend_residual_trace_boundary_inventory.py`
- `tests/inventory/test_admin_schema_version_mismatch_inventory.py`

## Acceptance Criteria
- Residual backend boundary formally mapped.
- Нет неясности, что удалять, а что можно временно deprecate.

---

# 2. PHASE 1 — Backend Trace Responsibility Cleanup

## Цель
Убрать из admin backend deep trace responsibility.

## Сделать
- Удалить или задепрекейтить:
  - `/api/admin/trace/last`
  - `/api/admin/trace/recent`
- Убрать `_build_trace_turn_payload(...)` из primary admin responsibility, если после аудита он больше не нужен.
- Пересобрать `runtime/effective`, чтобы trace availability:
  - не derived from `last_trace`;
  - не depended on session store turn presence.
- Если нужен trace indicator, заменить его на capability/status form:
  - `developer_trace_supported`
  - `developer_trace_enabled`
  - `developer_trace_mode_available`
  или эквивалентную system-level формулировку.

## Проверить
- Admin backend больше не отдаёт deep trace payload как primary product responsibility.
- Runtime/effective больше не depends on `last_trace`.
- Empty session store не влияет на admin runtime payload.

## Тесты
- `tests/contract/test_admin_trace_endpoints_removed_or_deprecated.py`
- `tests/contract/test_admin_runtime_payload_not_derived_from_last_trace.py`
- `tests/regression/test_admin_runtime_effective_renders_without_session_trace.py`

## Negative Tests
- session store empty;
- session store unavailable;
- stale request to removed trace endpoint;
- no developer trace capability flag.

## Acceptance Criteria
- Residual trace responsibility removed from admin backend.
- Runtime/effective is system-level only.
- No hidden dependency on trace storage remains.

---

# 3. PHASE 2 — Schema / Version Alignment

## Цель
Привести admin schema/version naming в соответствие с логикой 10.5.x.

## Сделать
- Обновить:
  - `ADMIN_SCHEMA_VERSION`
  - `ADMIN_EFFECTIVE_SCHEMA_VERSION`
- Проверить все места отображения schema/version:
  - Runtime tab
  - export/import metadata
  - contract payloads
  - tests
- Явно разделить:
  - app/runtime version
  - admin schema version
  - effective payload version
- Убедиться, что UI показывает те же значения, что backend реально отдаёт.

## Проверить
- Нет больше `10.4` / `10.4.1` как admin-facing mismatch after 10.5.
- UI and backend aligned.
- Export/import metadata remain valid.

## Тесты
- `tests/contract/test_admin_schema_versions_aligned_to_105_family.py`
- `tests/ui/test_runtime_tab_displays_updated_admin_schema_versions.py`
- `tests/contract/test_admin_export_import_metadata_uses_105_family.py`

## Negative Tests
- import old schema payload;
- export after version bump;
- runtime version mistaken for admin schema version.

## Acceptance Criteria
- Admin schema/version naming aligned to 10.5.x.
- UI displays correct version truth.
- Contract metadata consistent.

---

# 4. PHASE 3 — Regression Hardening and Final Boundary Verification

## Цель
Закрепить, что admin backend cleanup ничего полезного не сломал.

## Сделать
- Прогнать полный contract/regression pack.
- Проверить, что admin UI всё ещё работает корректно для:
  - LLM
  - Retrieval
  - Diagnostics
  - Routing
  - Memory
  - Prompts
  - Runtime
- Проверить, что нет stale frontend requests to removed trace endpoints.
- Проверить, что prompt management, runtime status and config operations still healthy.
- Обновить docs/notes around new backend boundary if needed.

## Проверить
- Frontend and backend now share same management-only boundary.
- No regression in remote operability.
- No orphan references to old trace endpoints remain.

## Тесты
- `tests/ui/test_admin_ui_and_admin_api_share_management_only_boundary.py`
- `tests/regression/test_admin_management_tabs_still_load_after_backend_cleanup.py`
- `tests/regression/test_prompt_management_and_runtime_status_still_work.py`

## Log / Manual Verification
Проверить вручную или automation-assisted:
- no admin trace tab;
- no admin trace endpoint dependency;
- runtime tab still loads;
- schema version displayed correctly;
- admin remains clean and usable.

## Final Acceptance Criteria
Одновременно должно быть верно всё:
- admin backend no longer acts as trace backend;
- runtime/effective is system-level only;
- schema/version markers aligned to 10.5.x;
- admin remote management remains intact;
- tests green.

---

# 5. Рекомендуемый формат коммитов

- `phase-0: audit residual trace responsibility and schema mismatches in admin backend`
- `phase-1: remove admin trace endpoints and decouple runtime effective from last trace`
- `phase-2: align admin schema and effective versions to 105 family`
- `phase-3: harden regressions and verify management-only backend boundary`

---

# 6. Definition of Done for IDE Agent

Работа по PRD_10.5.1 считается завершённой только если:
- все phase acceptance criteria закрыты;
- admin backend no longer carries deep trace responsibility;
- runtime/effective no longer depends on last trace;
- admin schema versions aligned to 10.5.x;
- no regression in admin usability or operability;
- contract/regression tests зелёные.

---

# 7. Финальная инструкция IDE-агенту

Работай как инженер точечной дочистки backend responsibility.

Твоя задача в этой итерации:
- не запускать новый большой этап;
- а добить backend-хвосты после удачного 10.5,
чтобы admin boundary стала чистой и на UI, и на API-уровне.

После 10.5.1 админка должна быть не только визуально management-first,
но и backend-wise полностью соответствовать этой роли.
