# PRD_10.5.1_Admin_Backend_Cleanup_And_Schema_Alignment.md

## Product Requirements Document

**Версия:** 10.5.1  
**Статус:** ACTIVE — proposed for implementation by IDE agent  
**Тип итерации:** Corrective Patch / Admin Backend Cleanup / Schema Alignment  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Основные области:** `bot_psychologist/api/`, `bot_psychologist/web_ui/`, `bot_psychologist/tests/`  
**Предшествующий документ:** `PRD_10.5_Admin_Panel_Management_And_Operability.md`  
**Правило совместимости:** PRD_10.5.1 не заменяет PRD_10.5. Это узкий corrective PRD, цель которого — добить оставшиеся хвосты после успешной очистки админки.

---

# 0. Executive Summary

PRD 10.5 в целом выполнен успешно:
- `Trace / Debug` убран из primary admin surface;
- Diagnostics стал policy-only;
- Runtime стал system-level truth surface;
- Prompt tab очищен от last-turn usage surface;
- админка стала заметно чище и полезнее как management console.

Но после аудита остались 2–3 небольших хвоста, которые лучше закрыть отдельной короткой итерацией, а не тянуть в следующий большой PRD:

1. **Backend admin trace responsibility не дочищен до конца**  
   Админский backend всё ещё хранит и отдаёт trace-heavy endpoints, хотя frontend уже ушёл от deep per-message debug. Это создаёт архитектурную нечистоту.

2. **Schema/version naming не выровнен под 10.5**  
   В runtime/admin payload still visible `10.4` / `10.4.1`, хотя product boundary уже соответствует 10.5.

3. **Runtime tab still depends on trace availability derived from admin backend trace storage**  
   Даже если UI уже не forensic, system-level indicator всё ещё завязан на следы старой debug responsibility.

**Цель PRD_10.5.1:**  
сделать админку не только чистой по UI, но и чистой по backend responsibility,  
при этом не смешивая сюда отдельную runtime/data-source проблему `json_fallback`.

---

# 1. Important Scope Clarification

## 1.1 Что входит в 10.5.1
Входит только то, что относится к хвостам **админки**:
- admin backend cleanup;
- schema/version alignment;
- trace responsibility cleanup in admin API;
- runtime payload cleanup;
- final contract alignment.

## 1.2 Что НЕ входит в 10.5.1
Не входит:
- разбор причины `json_fallback`;
- исправление data source switching;
- новый developer trace PRD;
- новый runtime pipeline;
- переработка retrieval корпуса.

## 1.3 Почему это важно
Проблема `json_fallback` может быть реальной, но это уже другая ось:
- runtime/data-source,
а не:
- admin management boundary.

Смешивать это в 10.5.1 нельзя.

---

# 2. Why this corrective iteration exists

## 2.1 UI уже очищен, backend — не до конца
После 10.5 frontend уже показывает правильную product boundary:
- admin is for management;
- deep trace is not primary there.

Но backend всё ещё содержит следы старой смешанной ответственности:
- `/api/admin/trace/last`
- `/api/admin/trace/recent`
- runtime effective payload смотрит в `last_trace`

Это означает, что admin API всё ещё partially thinks of itself as trace backend.

## 2.2 Version markers lag behind product reality
Пользователь и IDE-агент уже работают в логике PRD 10.5, но schema/version markers всё ещё несут `10.4` / `10.4.1`.

Это создаёт:
- документальную путаницу;
- audit mismatch;
- operational ambiguity.

## 2.3 Нужна финальная архитектурная чистота
После 10.5 админка должна быть чистой не только визуально, но и по backend-границам.

---

# 3. Product Goal of 10.5.1

## 3.1 Core goal
Добить оставшиеся backend и contract хвосты так, чтобы `/admin` был:
- management-first,
- system-level,
- version-aligned,
- без residual deep-trace responsibility.

## 3.2 Success perception
После 10.5.1 должно быть верно:

- admin UI и admin backend описывают одну и ту же границу;
- schema/version naming соответствует текущему продукту;
- trace-heavy responsibility больше не живёт в admin backend как полузабытый остаток;
- admin остаётся полезным и не теряет system-level visibility.

---

# 4. Fixed Decisions for 10.5.1

## 4.1 Admin backend must stop being a deep trace provider
Deep per-message trace не должен жить в admin backend как самостоятельная product responsibility.

### Разрешено оставить
- лёгкий system-level indicator:
  - trace enabled/disabled
  - trace available feature flag
  - pointer to developer trace in chat

### Не должно оставаться как primary admin responsibility
- `/api/admin/trace/last`
- `/api/admin/trace/recent`
- trace payloads shaped as per-turn debugging objects

## 4.2 Runtime effective payload must be system-level only
`runtime/effective` не должен читать глубокую turn identity и не должен conceptually зависеть от admin-trace semantics.

Если нужен indicator trace availability, он должен быть:
- config/status based;
- feature-flag based;
- or explicit runtime capability based;
а не через “есть ли last trace в session store”.

## 4.3 Schema/version markers must align to 10.5 family
Все admin-facing schema/version markers должны быть приведены к логике 10.5.x.

Допустимые варианты:
- `ADMIN_SCHEMA_VERSION = "10.5"`
- `ADMIN_EFFECTIVE_SCHEMA_VERSION = "10.5.1"`

или иная последовательная схема, если она документирована и объяснима.

Но нынешняя связка `10.4` / `10.4.1` должна быть устранена.

## 4.4 Tests must reflect the new boundary truth
Тесты, которые сейчас implicitly допускают trace dependence, должны быть обновлены под новую product truth.

Например, сейчас один тест допускает `trace available: bool(last_trace)` как acceptable runtime indicator.  
После 10.5.1 это уже должно быть пересмотрено.

---

# 5. Required Changes

## 5.1 `api/admin_routes.py`
### Сделать
- удалить или задепрекейтить admin trace endpoints:
  - `/trace/last`
  - `/trace/recent`
- убрать `_build_trace_turn_payload()` из primary admin responsibility, если он больше не нужен;
- пересчитать `runtime/effective` так, чтобы trace availability не опирался на `last_trace`;
- выровнять:
  - `ADMIN_SCHEMA_VERSION`
  - `ADMIN_EFFECTIVE_SCHEMA_VERSION`

### Цель
Чтобы backend соответствовал уже очищенной admin boundary.

---

## 5.2 `web_ui/src/components/admin/AdminPanel.tsx`
### Сделать
- сохранить текущую чистую UI-архитектуру;
- если где-то ещё остались trace-oriented assumptions or calls — удалить;
- убедиться, что Runtime tab использует only system-level trace status;
- при необходимости обновить wording around schema/version and trace availability.

### Цель
Frontend и backend должны быть fully aligned.

---

## 5.3 Runtime system indicator redesign
### Сделать
Если trace availability нужен в Runtime:
- сделать его capability/status field,
- а не derived-from-last-trace field.

Например:
- `developer_trace_supported`
- `developer_trace_enabled`
- `developer_trace_mode_available`

### Цель
Убрать остаточную forensic semantics из admin runtime payload.

---

## 5.4 Contract/schema cleanup
### Сделать
- обновить admin schema payloads to 10.5 family;
- проверить export/import metadata;
- убедиться, что admin schema version in UI matches backend truth.

### Цель
Документальная и operational consistency.

---

# 6. What should stay unchanged

Эта итерация не должна ломать то, что уже правильно сделано в 10.5:

- Trace / Debug остаётся убранным из primary admin UI;
- Diagnostics остаётся policy/config only;
- Runtime остаётся system-level truth tab;
- Prompts остаются management surface;
- Routing / Retrieval / Memory / LLM остаются usable remote management tabs.

---

# 7. Testing Strategy

## 7.1 Main test intent
Эта итерация должна доказать:

**админка очищена не только визуально, но и по backend responsibility**

## 7.2 Required test layers
Обязательны:
- unit
- contract
- UI rendering sanity tests
- admin integration tests

## 7.3 Required tests

### Trace backend cleanup
- `tests/contract/test_admin_trace_endpoints_removed_or_deprecated.py`
- `tests/contract/test_admin_runtime_payload_not_derived_from_last_trace.py`

### Version alignment
- `tests/contract/test_admin_schema_versions_aligned_to_105_family.py`
- `tests/ui/test_runtime_tab_displays_updated_admin_schema_versions.py`

### Boundary consistency
- `tests/ui/test_admin_ui_and_admin_api_share_management_only_boundary.py`

### Regression
- `tests/regression/test_admin_management_tabs_still_load_after_backend_cleanup.py`
- `tests/regression/test_prompt_management_and_runtime_status_still_work.py`

## 7.4 Negative tests
- runtime/effective should not require session trace to render;
- admin should not fail if session store empty;
- no stale frontend requests to removed trace endpoints;
- export/import should still preserve valid schema metadata.

---

# 8. Acceptance Criteria

## 8.1 Backend cleanup accepted only if
- admin backend no longer serves deep trace as a primary responsibility;
- runtime/effective no longer conceptually depends on `last_trace`.

## 8.2 Version alignment accepted only if
- admin schema/version markers align to 10.5 family;
- UI and backend show the same version truth.

## 8.3 Whole 10.5.1 accepted only if
- admin remains fully useful as management console;
- no regression in prompts/runtime/retrieval/routing/memory controls;
- backend boundary now matches frontend boundary;
- no mixed trace-management responsibility remains.

---

# 9. Delivery Plan

## Phase 0 — Residual Boundary Audit
- inventory remaining trace dependence in admin backend
- inventory schema/version mismatches

## Phase 1 — Backend Trace Responsibility Cleanup
- remove or deprecate trace endpoints
- remove last-trace based runtime derivation

## Phase 2 — Schema / Version Alignment
- update version markers to 10.5 family
- align export/import metadata and runtime display

## Phase 3 — Regression Hardening
- update tests
- verify admin tabs still work
- verify no stale frontend dependencies remain

---

# 10. Risk Management

## 10.1 Main risk
Можно слишком резко удалить backend pieces, и что-то скрытое во frontend сломается.

### Mitigation
- first audit actual callers;
- remove only after confirming no active dependency;
- keep deprecation shim briefly if needed.

## 10.2 Secondary risk
Можно перепутать admin version markers with runtime version markers.

### Mitigation
- explicitly separate:
  - app/runtime version
  - admin schema version
  - effective payload version

## 10.3 Over-scoping risk
Можно начать чинить `json_fallback` в рамках этого PRD.

### Mitigation
- explicitly keep data-source issue out of scope;
- create separate PRD later if needed.

---

# 11. Definition of Done

PRD_10.5.1 считается выполненным только если одновременно верно всё:

1. Admin backend no longer carries deep trace responsibility.  
2. Runtime effective payload is system-level only.  
3. Admin schema/version markers align to 10.5 family.  
4. Frontend and backend boundaries match.  
5. No regression in admin remote management usability.  
6. Tests confirm the new clean boundary.  

---

# 12. Instructions to IDE Agent

1. Не превращай 10.5.1 в большой новый этап.  
2. Работай как инженер точечной дочистки backend responsibility.  
3. Не смешивай сюда проблему `json_fallback`.  
4. Главная задача — добить хвосты после успешного 10.5.  
5. После каждой фазы:
   - обнови backend contracts;
   - обнови tests;
   - проверь, что admin UI не сломался;
   - зафиксируй final boundary consistency.

---

# 13. Final Note

PRD_10.5.1 intentionally focuses on one practical truth:

**Если админка уже очищена по UI, нужно довести до той же чистоты и её backend.**

Это маленькая, но важная итерация,
чтобы следующую большую работу по developer trace в чате строить уже на полностью чистой архитектурной границе.
