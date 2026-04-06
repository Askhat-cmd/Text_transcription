# TASKLIST_10.4.1_Admin_Operational_Surface_Completion

## Назначение
Этот документ — пошаговый execution-чеклист для IDE-агента, который внедряет `PRD_10.4.1_Admin_Operational_Surface_Completion.md`.

Главная цель итерации:
**довести новую Neo-админку до полноценной operational surface для удалённой диагностики, отладки и управления живым runtime.**

Главное правило:
**не переходить к следующей фазе, пока текущая не завершена, её UI/contract/e2e tests не зелёные, а админка не стала лучше объяснять, почему бот ответил именно так.**

---

# 0. Глобальные правила выполнения

## Правило 1. Это operational-depth iteration, а не новый большой редизайн
Запрещено раздувать scope:
- новым core runtime pipeline;
- новой memory-архитектурой;
- новой retrieval-философией;
- красивым redesign ради красоты;
- новой аналитической BI-системой;
- крупной переработкой ролей/permissions.

## Правило 2. Работа строго по фазам
Выполнять только последовательно:

- Phase 0
- Phase 1
- Phase 2
- Phase 3
- Phase 4
- Phase 5

Не смешивать trace API, diagnostics deepening и prompt operations completion в один большой хаотичный коммит.

## Правило 3. Stop-the-line
Если обязательные тесты фазы падают:
- остановиться;
- исправить корень проблемы;
- повторно прогнать тесты;
- не переходить дальше.

## Правило 4. Главная ценность — turn-level observability
Любое изменение должно усиливать способность через UI понять:
- что runtime диагностировал;
- какой route выбрал;
- что retrieval дал;
- что попало в prompt;
- что сделал validator;
- что обновилось в memory.

## Правило 5. Read-only truth лучше ложной editability
Если что-то нельзя безопасно редактировать через UI:
- показывать как read-only;
- объяснять источник и причину;
- не притворяться, что это editable.

## Правило 6. Compatibility должен оставаться вторичным
Compatibility surface допустим, но:
- не должен визуально конкурировать с primary actions;
- не должен снова стать ментальной моделью системы по умолчанию.

---

# 1. PHASE 0 — Operational Gaps Baseline

## Цель
Зафиксировать, чего именно не хватает текущей 10.4-админке для удалённой отладки.

## Сделать
- Снять baseline по текущим tab surfaces:
  - Diagnostics
  - Routing
  - Prompts
  - Runtime
  - Trace / Debug
- Зафиксировать конкретные пробелы:
  - Diagnostics too summary-only
  - Routing still too transitional / low-level
  - Trace almost placeholder
  - Prompt operations not turn-aware enough
  - Compatibility too visible
- Сохранить before-screenshots.
- Сформировать список required backend payloads:
  - effective diagnostics
  - effective routing
  - trace last/recent
  - prompt runtime usage metadata

## Проверить
- Есть список operational gaps.
- Есть before-state fixtures.
- Понятно, какие backend данные отсутствуют для полноценного UI.

## Тесты
- `tests/inventory/test_admin_operational_gaps_inventory.py`
- `tests/inventory/test_trace_surface_baseline_inventory.py`
- `tests/inventory/test_prompt_runtime_usage_metadata_gap_inventory.py`

## Acceptance Criteria
- Operational gaps formalized.
- Before-state зафиксирован.
- Backend/UI deficits clearly mapped.

---

# 2. PHASE 1 — Backend Effective Payloads and Trace Schema

## Цель
Добавить backend-источники правды для глубокой operational surface.

## Сделать
- Добавить или расширить admin endpoints для:
  - effective runtime payload
  - effective diagnostics payload
  - effective routing payload
  - last trace
  - recent traces
- Зафиксировать trace schema v10.4.1.
- Включить в payload:
  - turn id
  - timestamp
  - query
  - diagnostics
  - routing
  - retrieval
  - prompt stack
  - validation
  - memory
  - flags
  - anomalies
- Для prompt stack sections добавить:
  - read_only_reason
  - source
  - derived_from
  - usage markers if available
- Разделить:
  - editable config
  - effective derived runtime state
  - trace state

## Проверить
- Backend больше не заставляет frontend гадать.
- Trace payload контракт стабилен.
- Runtime/diagnostics/routing effective payloads пригодны для UI-рендера.

## Тесты
- `tests/contract/test_admin_trace_payload_schema_v1041.py`
- `tests/contract/test_admin_runtime_effective_payload_schema_v1041.py`
- `tests/contract/test_admin_diagnostics_effective_payload_schema_v1041.py`
- `tests/contract/test_admin_prompt_usage_metadata_schema_v1041.py`

## Negative Tests
- trace unavailable;
- trace partially missing sections;
- diagnostics payload missing one derived field;
- prompt section has `editable=false` but no reason.

## Acceptance Criteria
- Effective payloads defined.
- Trace schema stable.
- Backend truth sufficient for next UI phases.

---

# 3. PHASE 2 — Diagnostics and Routing Deepening

## Цель
Сделать Diagnostics и Routing tabs operational, а не только summary-like.

## Сделать

### Diagnostics tab
- Добавить cards:
  - Active Diagnostics Contract
  - Current Behavior Policies
  - Last Diagnostics Snapshot
  - Informational Narrowing
  - Mixed Query Handling
  - User Correction Protocol
- Показывать минимум:
  - interaction_mode
  - nervous_system_state
  - request_function
  - core_theme
  - confidence where available
  - informational_mode_hint if available
  - mixed_query flag if available
- Для каждого блока добавить короткое объяснение:
  - what it affects
  - editable or runtime-derived

### Routing tab
- Добавить cards:
  - Route Taxonomy
  - Current Routing Policy
  - False-Inform Protection
  - Curiosity Decoupling
  - Practice Trigger Rules
  - Safety Override Priority
- Переместить low-level toggles в advanced/collapsed section:
  - fast detector
  - state classifier threshold
  - прочие internal knobs
- Добиться, чтобы tab визуально был policy-first, а не knob-first.

## Проверить
- Diagnostics tab стал operational.
- Routing tab стал policy-first.
- Low-level controls больше не доминируют визуально.

## Тесты
- `tests/ui/test_diagnostics_tab_shows_effective_policy_cards.py`
- `tests/ui/test_diagnostics_tab_can_render_last_snapshot.py`
- `tests/ui/test_routing_tab_is_policy_first.py`
- `tests/ui/test_routing_advanced_controls_collapsed_by_default.py`
- `tests/ui/test_false_inform_and_curiosity_decoupling_visible.py`

## Negative Tests
- no last diagnostics available;
- confidence values absent;
- advanced routing controls missing data;
- no mixed-query policy payload.

## Acceptance Criteria
- Diagnostics no longer summary-only.
- Routing no longer visually transitional.
- Policy clarity improved materially.

---

# 4. PHASE 3 — Trace / Debug Viewer

## Цель
Превратить Trace / Debug из placeholder в реальный last-turn / recent-turn trace viewer.

## Сделать
- Реализовать viewer для:
  - last trace
  - recent traces list
- Добавить блоки:
  1. Turn header
  2. Diagnostics snapshot
  3. Routing decision
  4. Retrieval pipeline
  5. Prompt stack summary
  6. Output validation
  7. Memory / summary update
  8. Flags / anomalies / degraded mode
- Для retrieval показывать:
  - initial top-k
  - rerank enabled
  - rerank top-k
  - final cap
  - before/after narrowing counts
- Для validation показывать:
  - passed / failed
  - regenerated / repaired / accepted
  - anti-sparse triggered or not
  - safety issue or not
- Для memory показывать:
  - summary state
  - snapshot updated
  - semantic memory used
  - fallback chain if any
- Реализовать empty/disabled/error states:
  - trace disabled
  - no trace yet
  - fetch error
  - partial trace

## Проверить
- Developer can inspect why last answer happened.
- Viewer not just status text, but real turn-level breakdown.
- Missing trace states are explicit and actionable.

## Тесты
- `tests/ui/test_trace_tab_renders_last_turn_trace.py`
- `tests/ui/test_trace_tab_renders_recent_traces_list.py`
- `tests/ui/test_trace_tab_handles_disabled_state.py`
- `tests/ui/test_trace_tab_handles_partial_trace.py`
- `tests/e2e/test_admin_trace_viewer_last_turn_flow.py`

## Negative Tests
- trace endpoint returns empty list;
- partial trace payload;
- validation block absent;
- retrieval block absent;
- memory block absent.

## Acceptance Criteria
- Trace / Debug becomes actually useful.
- Last-turn root-cause inspection available.
- Error states handled cleanly.

---

# 5. PHASE 4 — Prompt Operations Completion

## Цель
Сделать prompt tab полезным не только для обзора sections, но и для понимания реальной prompt assembly.

## Сделать
- Добавить effective assembly preview:
  - stack order
  - active sections
  - current section source
  - read-only / editable reason
  - variants/modifiers
- Добавить last-turn usage view:
  - какие sections участвовали
  - какие modifiers были активны
  - какие sections derived/runtime-only
- Для read-only sections показывать:
  - why read-only
  - derived_from
  - source
- Улучшить distinction between:
  - editable prompt content
  - runtime-derived sections
  - operational modifiers
- Если section runtime-derived, не притворяться editor'ом без объяснения.

## Проверить
- Prompt tab shows operational awareness.
- Read-only sections understandable.
- Variants/modifiers visible as actual runtime influences.

## Тесты
- `tests/ui/test_prompt_tab_shows_effective_assembly_preview.py`
- `tests/ui/test_prompt_tab_shows_readonly_reason.py`
- `tests/ui/test_prompt_tab_shows_last_turn_section_usage.py`
- `tests/contract/test_prompt_stack_usage_metadata_api.py`
- `tests/e2e/test_prompt_operational_surface_flow.py`

## Negative Tests
- no last-turn prompt usage available;
- runtime-derived section with missing reason;
- editable section save validation error;
- variant metadata missing.

## Acceptance Criteria
- Prompt tab no longer merely lists sections.
- Developer can understand actual prompt participation in runtime.
- Read-only vs editable is operationally clear.

---

# 6. PHASE 5 — Runtime Truth Completion + Compatibility De-Emphasis + Final Verification

## Цель
Довести Runtime tab и общий header до зрелой operational surface и закрепить все изменения тестами.

## Сделать

### Runtime tab
- Добавить deeper runtime truth blocks:
  - active diagnostics state
  - active routing state
  - prompt stack version
  - admin schema version
  - trace availability
  - config validation status
  - feature flag grouping
- Показать effective source-of-truth summary, а не только raw status.

### Compatibility de-emphasis
- Переместить compatibility control в less prominent area:
  - advanced dropdown / utility area / tucked button
- Сделать его secondary visually and semantically.

### Final hardening
- Прогнать full UI/contract/e2e pack.
- Обновить admin docs / operator notes.
- Зафиксировать before/after screenshots and flows.

## Проверить
- Runtime tab helps debug, not just report status.
- Compatibility no longer competes visually with primary actions.
- Whole admin surface now supports remote bot tuning and debugging.

## Тесты
- `tests/ui/test_runtime_tab_shows_effective_runtime_truth.py`
- `tests/ui/test_compatibility_button_deemphasized.py`
- `tests/e2e/test_compatibility_hidden_under_advanced_controls.py`
- `tests/e2e/test_admin_operational_surface_end_to_end.py`

## Log / Manual Verification
Проверить вручную или automation-assisted:
- diagnostics tab gives actual inspectable state;
- routing tab explains policies and route logic;
- trace tab explains last turn;
- prompt tab shows effective assembly;
- runtime tab shows deeper truth;
- compatibility visually secondary.

## Final Acceptance Criteria
Одновременно должно быть верно всё:
- diagnostics operational;
- routing policy-first;
- trace viewer real;
- prompt operations richer;
- runtime truth deeper;
- compatibility de-emphasized;
- full tests green.

---

# 7. Рекомендуемый формат коммитов

- `phase-0: add admin operational gaps baseline and missing payload inventory`
- `phase-1: add effective runtime and trace payload schemas for admin`
- `phase-2: deepen diagnostics and routing tabs into policy-first surfaces`
- `phase-3: implement last-turn and recent-turn trace viewer`
- `phase-4: complete prompt operational surface with effective assembly preview`
- `phase-5: deepen runtime truth and de-emphasize compatibility`

---

# 8. Definition of Done for IDE Agent

Работа по PRD_10.4.1 считается завершённой только если:
- все phase acceptance criteria закрыты;
- diagnostics/routing/trace/prompt/runtime tabs стали operationally useful;
- trace payload contracts стабильны;
- UI/contract/e2e tests зелёные;
- developer can remotely inspect why the bot answered the way it did.

---

# 9. Финальная инструкция IDE-агенту

Работай как инженер operational completion.

Твоя задача в этой итерации:
- не просто “добавить ещё панелей”;
- а дать разработчику реальную удалённую видимость в живой turn-level pipeline.

После 10.4.1 веб-админка должна помогать не только менять настройки,
но и быстро объяснять поведение Neo MindBot на реальных запросах.
