# TASKLIST_10.5_Admin_Panel_Management_And_Operability.md

## Назначение
Этот документ — пошаговый execution-чеклист для IDE-агента, который внедряет `PRD_10.5_Admin_Panel_Management_And_Operability.md`.

Главная цель итерации:
**очистить и доработать `/admin` так, чтобы он был удобной, управляемой и безопасной панелью удалённого управления ботом, а не местом для подробного разбора каждого ответа.**

Главное правило:
**не переходить к следующей фазе, пока текущая не завершена, её UI/contract/e2e tests не зелёные, а админка не стала чище именно как management console.**

---

# 0. Глобальные правила выполнения

## Правило 1. Это admin-management iteration, а не debug iteration
Запрещено раздувать scope:
- новым developer trace UI;
- message-level route/debug consoles;
- new chat debugging widgets;
- новой core runtime-архитектурой;
- редизайном ради красоты.

## Правило 2. Работа строго по фазам
Выполнять только последовательно:

- Phase 0
- Phase 1
- Phase 2
- Phase 3
- Phase 4
- Phase 5

Не смешивать admin cleanup, diagnostics simplification, runtime truth polishing и prompt UX в один хаотичный коммит.

## Правило 3. Stop-the-line
Если обязательные тесты фазы падают:
- остановиться;
- исправить корень проблемы;
- повторно прогнать тесты;
- не переходить дальше.

## Правило 4. `/admin` = управление, а не forensic trace
Любая поверхность, которая отвечает на вопрос
- “как именно сработал конкретный ответ?”
должна считаться подозрительной для админки и, как правило, уходить из `/admin`.

## Правило 5. System-level truth must remain
Убирая message-level debug, нельзя ломать:
- runtime health visibility;
- feature flags visibility;
- effective config truth;
- schema/version awareness;
- prompt management;
- remote operability.

## Правило 6. Better usability is mandatory
После 10.5 админка должна стать:
- проще,
- чище,
- понятнее,
- быстрее для типовых задач удалённого управления.

---

# 1. PHASE 0 — Boundary Audit and Freeze

## Цель
Формально зафиксировать новую границу ответственности между:
- `/admin`
- developer trace внутри чата

## Сделать
- Инвентаризировать текущие surfaces `/admin`.
- Для каждой вкладки и блока пометить:
  - management/config
  - system-level truth
  - message-level debug
  - mixed/ambiguous
- Отдельно зафиксировать всё, что относится к per-message trace:
  - last diagnostics snapshot
  - last turn route data
  - retrieval breakdown for a specific turn
  - output validation of a specific turn
  - memory update of a specific turn
  - recent traces / trace history
  - per-turn anomalies
- Сохранить before-screenshots и before-flow notes.

## Проверить
- Есть явный список того, что остаётся в `/admin`.
- Есть явный список того, что считается лишним для `/admin`.
- Ownership boundary formalized.

## Тесты
- `tests/inventory/test_admin_boundary_inventory_v105.py`
- `tests/inventory/test_message_level_debug_surfaces_inventory.py`

## Acceptance Criteria
- Граница ответственности зафиксирована.
- Ambiguous surfaces отмечены и распределены.
- Есть baseline до очистки.

---

# 2. PHASE 1 — Remove Deep Trace Responsibility from Admin

## Цель
Убрать из primary admin surface всё, что относится к deep per-message debug.

## Сделать
- Удалить полноценную вкладку `Trace / Debug` из primary admin tabs.
- Удалить из `/admin` surfaces:
  - last diagnostics snapshot;
  - recent traces;
  - turn-level retrieval breakdown;
  - turn-level validation breakdown;
  - turn-level memory update breakdown;
  - turn-level prompt participation breakdown;
  - per-turn anomalies view.
- Если нужно, оставить очень лёгкий system-level indicator:
  - trace enabled/disabled
  - trace available/unavailable
- Добавить короткую handoff-подсказку:
  - deep diagnostics are available in developer trace inside chat

## Проверить
- В админке больше нет trace-like forensic viewer.
- Нет последних message snapshots в Diagnostics.
- Нет recent trace list в admin.
- Нет per-turn breakdown в Runtime.

## Тесты
- `tests/ui/test_trace_debug_tab_removed_from_primary_admin.py`
- `tests/ui/test_admin_primary_surface_has_no_deep_message_trace.py`
- `tests/ui/test_admin_handoff_message_to_chat_trace_present.py`

## Negative Tests
- stale frontend import of removed trace tab;
- backend payload still expected by removed admin widgets;
- missing placeholder causes layout break.

## Acceptance Criteria
- Trace responsibility removed from admin primary surface.
- No deep per-message debug remains in `/admin`.
- UI still coherent after removal.

---

# 3. PHASE 2 — Rebuild Diagnostics and Runtime as System-Level Surfaces

## Цель
Сделать Diagnostics и Runtime строго system-level и policy-level surfaces.

## Сделать

### Diagnostics
- Удалить все last-message specific blocks.
- Оставить и упорядочить:
  - diagnostics contract overview;
  - informational narrowing;
  - mixed-query handling;
  - user correction protocol;
  - first-turn richness policy;
  - editable vs read-only hints.
- Сделать Diagnostics tab policy/config oriented.

### Runtime
- Оставить только:
  - effective runtime truth;
  - schema/version;
  - prompt stack version;
  - feature flags;
  - config validation status;
  - data source;
  - degraded mode;
  - blocks loaded;
  - warmup/cache/KG;
  - trace availability only as system-level indicator.
- Убрать всё, что похоже на turn forensics.

## Проверить
- Diagnostics больше не показывает last snapshot.
- Runtime больше не ведёт себя как debug tab.
- Оба раздела стали чище и понятнее.

## Тесты
- `tests/ui/test_diagnostics_tab_policy_only_no_last_snapshot.py`
- `tests/ui/test_runtime_tab_system_level_only.py`
- `tests/ui/test_runtime_tab_keeps_effective_truth_without_trace_forensics.py`

## Negative Tests
- missing diagnostics policy payload;
- no feature flags;
- degraded mode active;
- trace availability absent.

## Acceptance Criteria
- Diagnostics = policy/config surface.
- Runtime = system-level truth surface.
- No message-level forensic leftovers.

---

# 4. PHASE 3 — Improve Core Management Tabs

## Цель
Сделать ключевые вкладки сильнее именно как remote management tools.

## Сделать

### LLM
- улучшить tooltips и пояснения;
- проверить safe validation ranges;
- показать effective active values яснее.

### Retrieval
- улучшить пояснения для:
  - top-k,
  - min relevance,
  - rerank top-k,
  - confidence caps high/medium/low/zero;
- визуально объяснить связь между retrieval -> rerank -> final cap.

### Routing
- оставить policy-first structure;
- улучшить help text для:
  - false-inform protection
  - curiosity decoupling
  - practice trigger rules
  - safety override priority
- сохранить advanced routing controls, но не давать им доминировать.

### Memory
- улучшить объяснение разницы между:
  - history
  - semantic memory
  - summary
- улучшить usability numeric settings.

### Prompts
- сохранить prompt stack v2 management;
- убрать last-turn usage surface;
- улучшить clarity around:
  - editable/read-only
  - read_only_reason
  - source/derived_from
  - preview/original/save flow

## Проверить
- Management tabs полезны без trace-noise.
- Оператору стало проще понимать, что меняет параметр.
- Advanced controls не захламляют UI.

## Тесты
- `tests/ui/test_retrieval_tab_explains_caps_and_pipeline.py`
- `tests/ui/test_routing_tab_policy_first_and_no_forensic_trace.py`
- `tests/ui/test_memory_tab_explains_layers_clearly.py`
- `tests/ui/test_prompt_tab_no_last_turn_usage_surface.py`
- `tests/ui/test_llm_tab_has_effective_value_and_validation_help.py`

## Negative Tests
- prompt tab still depends on removed usage payload;
- retrieval tooltip content missing;
- advanced routing section expanded by default;
- memory field labels ambiguous.

## Acceptance Criteria
- Core tabs materially better as management tools.
- User guidance improved.
- Trace clutter removed without weakening control.

---

# 5. PHASE 4 — Safety, Config Operability, and Admin Actions Hardening

## Цель
Усилить надёжность удалённого управления через админку.

## Сделать
- Проверить и улучшить:
  - inline validation
  - allowed ranges
  - save feedback
  - reset semantics
  - export/import
  - schema version display
- Убедиться, что:
  - editable vs read-only contract remains explicit;
  - config updates are validated before save;
  - import of old schemas remains safe;
  - admin remains rollback-ready in structure.
- При необходимости добавить clearer success/error states.

## Проверить
- Admin actions предсказуемы и безопасны.
- Ошибки понятны.
- Remote edit flow не вызывает сомнений.

## Тесты
- `tests/contract/test_admin_schema_v105_management_only.py`
- `tests/contract/test_admin_payloads_no_message_level_trace_dependency.py`
- `tests/e2e/test_admin_prompt_edit_and_runtime_status_flow.py`
- `tests/e2e/test_admin_export_import_reset_remote_operability.py`
- `tests/ui/test_admin_save_feedback_and_validation_states.py`

## Negative Tests
- invalid numeric input;
- invalid import payload;
- deprecated schema import;
- readonly field accidentally editable.

## Acceptance Criteria
- Safe remote operation strengthened.
- Validation/export/import/reset remain solid.
- No hidden dependency on removed trace surfaces.

---

# 6. PHASE 5 — Final UX Cleanup and Regression Verification

## Цель
Закрепить итоговую админку как чистую management console.

## Сделать
- Прогнать полный UI/contract/e2e pack.
- Проверить before/after admin flows:
  - change LLM setting
  - tune retrieval
  - inspect routing policy
  - adjust memory
  - inspect runtime truth
  - edit prompt section
  - export/import/reset config
- Пересмотреть визуальный шум:
  - grouping
  - empty space
  - advanced sections
  - section titles
  - handoff wording to chat developer trace
- Обновить admin docs/operator notes.

## Проверить
- Админка стала чище и быстрее в использовании.
- Нет regressions по основным задачам.
- New responsibility boundary visually respected.

## Тесты
- `tests/e2e/test_admin_management_flow_without_trace_surface.py`
- `tests/e2e/test_admin_primary_management_tasks_are_faster_and_cleaner.py`
- `tests/ui/test_admin_tabs_focus_on_management_surfaces.py`

## Log / Manual Verification
Проверить вручную или automation-assisted:
- no primary trace tab;
- diagnostics has no last message snapshot;
- runtime has no per-turn breakdown;
- prompt tab no longer shows last-turn usage;
- admin still fully useful for remote bot management.

## Final Acceptance Criteria
Одновременно должно быть верно всё:
- `/admin` clearly behaves as management console;
- deep message-level debug no longer lives there;
- system-level truth remains strong;
- usability materially improves;
- remote configuration remains powerful and safe.

---

# 7. Рекомендуемый формат коммитов

- `phase-0: freeze admin vs chat-trace responsibility boundary`
- `phase-1: remove deep trace responsibility from primary admin surface`
- `phase-2: rebuild diagnostics and runtime as system-level surfaces`
- `phase-3: improve management usability of llm retrieval routing memory and prompts`
- `phase-4: harden validation export import reset and config safety`
- `phase-5: finalize ux cleanup and management-console regression verification`

---

# 8. Definition of Done for IDE Agent

Работа по PRD_10.5 считается завершённой только если:
- все phase acceptance criteria закрыты;
- admin no longer duplicates deep per-message trace;
- diagnostics/runtime are system-level only;
- LLM/Retrieval/Routing/Memory/Prompts remain strong management tabs;
- remote operability improves;
- UI/contract/e2e tests зелёные.

---

# 9. Финальная инструкция IDE-агенту

Работай как инженер управляемости и удобства админки.

Твоя задача в этой итерации:
- не сделать ещё один debug-интерфейс;
- а сделать сильную, чистую и удобную панель удалённого управления ботом.

После 10.5 `/admin` должен помогать быстро управлять Neo MindBot,
не перегружая разработчика тем, что логичнее смотреть внутри developer trace прямо в чате.
