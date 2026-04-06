# PRD_10.4.1_Admin_Operational_Surface_Completion

## Product Requirements Document

**Версия:** 10.4.1  
**Статус:** ACTIVE — proposed for implementation by IDE agent  
**Тип итерации:** Admin Operations Completion / Diagnostics–Routing–Trace Deepening  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Основные области:** `bot_psychologist/web_ui/`, `bot_psychologist/api/`, `bot_psychologist/bot_agent/`  
**Предшествующий документ:** `PRD_10.4_Admin_Panel_Neo_Realignment.md`  
**Правило совместимости:** PRD_10.4.1 не отменяет PRD_10.4. Это follow-up итерация, цель которой — довести новую админку от “архитектурно выровнена” до “операционно полноценна”.

---

# 0. Executive Summary

Итерация 10.4 успешно выровняла primary admin surface под Neo runtime:

- primary tabs перестроены под Neo IA;
- legacy SD / Decision Gate / user-level больше не являются главной operational truth;
- prompt tab переведён на prompt stack v2;
- runtime / retrieval / memory стали заметно честнее;
- compatibility surface вынесен отдельно;
- backend schema v10.4 и prompt stack v2 admin API добавлены.

Но после этой итерации остаются важные operational gaps:

1. **Diagnostics tab пока слишком поверхностный**  
2. **Routing tab всё ещё transitional и слишком low-level**  
3. **Trace / Debug пока почти пустой и не даёт реальной трассировки**  
4. **Prompt operations пока слишком ограничены и местами скорее обзорные, чем operational**  
5. **Compatibility всё ещё слишком заметен в primary header**  

То есть 10.4 убрал главную ложь из интерфейса, но админка ещё не стала полноценно сильным инструментом удалённой диагностики и контроля.

**Цель PRD_10.4.1:**  
доделать веб-админку до состояния, где разработчик может:
- видеть реальное поведение runtime;
- понимать route / diagnostics / retrieval / validation на конкретных turn'ах;
- безопасно управлять prompt and policy surface;
- быстро отлаживать “почему бот ответил именно так”.

---

# 1. Why this iteration exists

## 1.1 Что уже решено
После 10.4 админка больше не живёт в старой карте мира. Это уже серьёзный прогресс.

## 1.2 Что всё ещё мешает разработчику
Для полноценной удалённой отладки всё ещё не хватает:

- inspectable diagnostics state;
- нормального trace viewer;
- ясного routing policy surface;
- prompt stack operations beyond базовый обзор;
- связи между admin surface и реальным turn behavior.

## 1.3 Главный operational запрос
Разработчику важно не просто видеть конфиг, а понимать:

- что именно классифицировал runtime;
- какой route был выбран;
- почему он был выбран;
- какие блоки retrieval попали в финальный контекст;
- прошёл ли ответ validation;
- что попало в memory / summary;
- какой prompt stack реально собрался.

Именно это должно стать центром 10.4.1.

---

# 2. Product Goal of 10.4.1

## 2.1 Core goal
Сделать админку полноценной **операционной панелью Neo MindBot**, а не только выровненным конфиг-редактором.

## 2.2 Success perception
После 10.4.1 разработчик должен ощущать:

- “я могу увидеть, как реально прошёл конкретный turn”;
- “я понимаю, почему бот ушёл в inform / reflect / practice”;
- “я вижу, что retrieval дал и что реально попало в LLM”;
- “я могу безопасно редактировать prompt surface там, где это допустимо”;
- “админка помогает быстро находить root cause, а не гадать”.

---

# 3. Scope of PRD_10.4.1

## 3.1 Входит в scope

1. Углубление Diagnostics tab  
2. Углубление Routing tab  
3. Реальный Trace / Debug viewer  
4. Trace API / backend support for operational inspection  
5. Улучшение Prompt operations surface  
6. Улучшение Runtime panel через effective runtime truth  
7. Ослабление заметности Compatibility surface  
8. Улучшение связки admin UI ↔ real answer cards / request traces  
9. Admin safety / validation / readonly policies for editable surfaces

## 3.2 Не входит в scope

В 10.4.1 не входят:
- новый core runtime pipeline;
- новая retrieval engine architecture;
- новая memory schema;
- новая классификационная теория;
- визуальный redesign ради красоты;
- полноценная аналитическая BI-платформа;
- multi-user admin roles and permissions.

## 3.3 Scope discipline
Любое изменение должно отвечать на вопрос:

**Это усиливает способность удалённо понимать и отлаживать живой runtime?**

Если нет — задача out-of-scope.

---

# 4. Current Gaps to Fix

## 4.1 Diagnostics tab is too summary-like
Сейчас diagnostics tab уже не legacy, но он ещё не operational.  
Ему не хватает:
- effective diagnostics contract view;
- current policies;
- inspectable examples / last diagnostics;
- mixed-query / informational narrowing status;
- user correction protocol visibility.

## 4.2 Routing tab is still transitional
Сейчас routing tab уже не старый layer stack, но внутри всё ещё много low-level switches вроде fast detector / state classifier thresholds.

Это допустимо как internal knobs, но tab всё ещё недостаточно отвечает на вопрос:

**как route реально выбирается сейчас?**

## 4.3 Trace / Debug is mostly a placeholder
Сейчас trace tab не даёт реального пост-turn анализа:
- last route
- diagnostics snapshot
- retrieval before/after rerank/cap
- selected practice
- output validation result
- summary status
- prompt stack assembly summary

Без этого remote debugging всё ещё неполноценен.

## 4.4 Prompt operations are still limited
Prompt stack v2 уже есть, но operations surface пока ограничен:
- мало editable operational sections;
- нет явного effective assembly preview по конкретному turn;
- не хватает richer inspectability for variants/modifiers.

## 4.5 Compatibility is still too visible
Кнопка compatibility сейчас ещё слишком рядом с основными действиями.  
Это не критическая ошибка, но operationally её primacy стоит уменьшить.

---

# 5. Product Principles for 10.4.1

## 5.1 Show the real turn, not just the config
Конфиг важен, но для отладки важнее видеть поведение конкретного запроса.

## 5.2 Operational observability over static settings
Лучше меньше “абстрактных тумблеров”, но больше полезной turn-level observability.

## 5.3 Read-only truth is valuable
Не всё нужно делать editable.  
Но многое должно быть inspectable.

## 5.4 Explain why, not only what
Админка должна показывать не только выбранный route, но и причины выбора.

## 5.5 Safe editability only
Editable surface должен быть:
- валидируемым;
- версионируемым;
- ограниченным там, где это опасно.

---

# 6. Fixed Decisions for 10.4.1

## 6.1 Diagnostics tab becomes operational
Diagnostics tab должен стать местом, где видно:
- active diagnostics contract v1;
- active informational narrowing policy;
- active mixed-query handling policy;
- first-turn richness policy;
- user correction policy;
- last diagnostics snapshot from runtime if available.

## 6.2 Routing tab becomes policy-first
Routing tab должен отвечать прежде всего на вопросы:
- какие route values существуют;
- какие policy rules сейчас активны;
- какие gates влияют на `inform` / `practice` / `reflect`;
- включена ли false-inform protection;
- включён ли curiosity decoupling.

Low-level toggles можно оставить, но не как главную сущность панели.

## 6.3 Trace / Debug becomes a real trace viewer
Trace / Debug должен показывать для последнего запроса или выбранного turn:

- query / timestamp
- diagnostics result
- route selected
- retrieval stats
- rerank stats
- final block cap
- selected practice
- validation result
- memory update result
- prompt stack summary
- degraded mode / anomalies if any

## 6.4 Prompt tab gets effective assembly awareness
Prompt tab должен уметь показывать:
- sections
- variants/modifiers
- read-only vs editable
- effective runtime assembly preview
- which sections participated in last turn
- why a section is read-only

## 6.5 Compatibility should be secondary, not co-equal
Compatibility должен остаться доступным, но стать менее prominent:
- secondary menu
- tucked advanced button
- collapsible section
- not equal visual weight with primary actions

---

# 7. Required UX / UI Changes

## 7.1 Diagnostics tab requirements
Нужно добавить:
- карточку “Active Diagnostics Contract”
- карточку “Current Behavior Policies”
- карточку “Last Diagnostics Snapshot”
- карточку “Informational Narrowing / Mixed Query / User Correction”
- explainers for what each field influences

### Minimum fields to show
- interaction_mode
- nervous_system_state
- request_function
- core_theme
- informational_mode_hint if applicable
- mixed_query flag if applicable
- confidence values when available

## 7.2 Routing tab requirements
Нужно добавить:
- route taxonomy card
- current route-policy card
- false-inform protection card
- curiosity decoupling status
- practice trigger rules
- safety override precedence summary
- optional “advanced knobs” collapsed section for low-level controls

### Important UI rule
Fast detector / state classifier controls should not visually dominate the tab.

## 7.3 Trace / Debug tab requirements
Нужно создать реальный trace inspector.

### Minimum trace blocks
1. Turn header  
2. Diagnostics snapshot  
3. Routing decision  
4. Retrieval pipeline  
5. Prompt stack summary  
6. Output validation  
7. Memory / summary update  
8. Flags / degraded mode / anomalies  

### UX note
Если trace unavailable:
- show why;
- show whether trace collection disabled;
- provide retry or instructions.

## 7.4 Prompt tab requirements
Нужно добавить:
- effective assembly preview
- last-turn section usage summary
- section participation markers
- clearer reason for read-only sections
- variants/modifiers visualization
- better separation of editable prompt content vs runtime-derived sections

## 7.5 Runtime tab requirements
Runtime tab должен показывать не только status snapshot, но и:
- effective feature flag groups
- active diagnostics / routing / validation / prompt-stack state
- trace availability
- admin schema version
- prompt stack version
- config validation status

## 7.6 Header / Compatibility requirements
Нужно уменьшить primacy compatibility button:
- move to right-side utility area
- hide under advanced menu
- visually de-emphasize vs export/import/reset

---

# 8. Backend / API Requirements

## 8.1 Add trace-oriented admin endpoints
Нужен backend support для trace inspection.

### Allowed shape
- `/api/admin/trace/last`
- `/api/admin/trace/recent`
- `/api/admin/runtime/effective`
- `/api/admin/diagnostics/effective`

Формат может отличаться, но смысл должен быть таким.

## 8.2 Add effective runtime payload
Нужен consolidated effective payload, который frontend сможет использовать без догадок:
- diagnostics policies
- routing policies
- feature flags
- prompt stack version
- validation status
- trace status

## 8.3 Prompt surface API should expose runtime usage metadata
Для prompt tab желательно вернуть:
- section usage markers
- editable/read-only reasons
- variant list
- stack order
- effective section source

## 8.4 Read-only runtime-derived sections must explain themselves
Если section non-editable, API должен возвращать:
- `editable: false`
- `read_only_reason`
- `source`
- `derived_from`

---

# 9. Target Information Architecture After 10.4.1

## 9.1 Tabs remain
- LLM
- Retrieval
- Diagnostics
- Routing
- Memory
- Prompts
- Runtime
- Trace / Debug

## 9.2 Internal deepening
Главное изменение не в количестве tabs, а в их operational depth.

## 9.3 Compatibility placement
Compatibility:
- hidden by default
- available via advanced controls
- not visually equal to core tabs/actions

---

# 10. Diagnostics Surface Deepening

## 10.1 Must-have cards
- Diagnostics v1 Contract
- Current Policy Summary
- Last Turn Diagnostics Snapshot
- Informational Narrowing Status
- Mixed Query Handling Status
- User Correction Protocol Status

## 10.2 Must-have explanations
Каждый блок должен объяснять:
- what this field influences;
- when it is used;
- whether it is editable or runtime-derived.

## 10.3 Non-goal
Не превращать diagnostics tab в бесконечную философскую панель.  
Это должна быть compact operational surface.

---

# 11. Routing Surface Deepening

## 11.1 Must-have cards
- Route Taxonomy
- Current Routing Policy
- False-Inform Protection
- Curiosity Decoupling
- Practice Triggering
- Safety Override Priority

## 11.2 Advanced controls
Low-level controls допускаются, но:
- collapsed by default;
- clearly marked as advanced;
- not primary mental model.

## 11.3 Non-goal
Не возвращать old “Layer 1–5” stack как основную поверхность.

---

# 12. Trace / Debug Viewer

## 12.1 Core requirement
Сделать trace реально полезным.

## 12.2 Minimum data model for last trace
```json
{
  "turn_id": "string",
  "timestamp": "ISO8601",
  "query": "string",
  "diagnostics": {},
  "routing": {},
  "retrieval": {},
  "prompt_stack": {},
  "validation": {},
  "memory": {},
  "flags": {},
  "anomalies": []
}
```

## 12.3 Minimum retrieval info
- initial top-k
- rerank enabled
- rerank top-k
- final cap
- blocks before/after narrowing

## 12.4 Minimum validation info
- passed / failed
- repaired / regenerated / accepted as-is
- anti-sparse triggered or not
- safety issue detected or not

## 12.5 Minimum memory info
- summary state
- snapshot updated or not
- semantic memory used or not
- fallback chain if any

## 12.6 UX fallback
Если trace disabled:
- clear disabled state
- how to enable
- what is unavailable because of that

---

# 13. Prompt Operations Completion

## 13.1 Effective assembly preview
Нужно дать разработчику возможность видеть:
- section order
- active section text or preview
- which sections were used in last turn
- which modifiers were active

## 13.2 Editability rules
Editable should stay limited where needed, but UI must clearly explain:
- why section is read-only;
- what source defines it;
- can it be changed elsewhere or not.

## 13.3 Variant visibility
Нужно показать variants/modifiers:
- inform-rich
- mixed-query
- first-turn
- user-correction
- safe-override

не как абстрактный список, а как operational modifiers.

---

# 14. Testing Strategy

## 14.1 Main test intent
Эта итерация должна доказать:

**админка стала инструментом удалённой диагностики и объяснения поведения конкретного turn**

## 14.2 Required test layers
Обязательны:
- unit
- contract
- integration
- UI rendering tests
- e2e admin tests

## 14.3 Required tests

### Diagnostics
- `tests/ui/test_diagnostics_tab_shows_effective_policy_cards.py`
- `tests/ui/test_diagnostics_tab_can_render_last_snapshot.py`

### Routing
- `tests/ui/test_routing_tab_is_policy_first.py`
- `tests/ui/test_routing_advanced_controls_collapsed_by_default.py`

### Trace
- `tests/ui/test_trace_tab_renders_last_turn_trace.py`
- `tests/contract/test_admin_trace_payload_schema_v1041.py`
- `tests/e2e/test_admin_trace_viewer_last_turn_flow.py`

### Prompt operations
- `tests/ui/test_prompt_tab_shows_effective_assembly_preview.py`
- `tests/ui/test_prompt_tab_shows_readonly_reason.py`
- `tests/contract/test_prompt_stack_usage_metadata_api.py`

### Runtime
- `tests/ui/test_runtime_tab_shows_effective_runtime_truth.py`

### Compatibility
- `tests/ui/test_compatibility_button_deemphasized.py`
- `tests/e2e/test_compatibility_hidden_under_advanced_controls.py`

---

# 15. Acceptance Criteria

## 15.1 Diagnostics accepted only if
- diagnostics tab shows more than static summary text;
- last diagnostics snapshot or effective diagnostics state is visible;
- policies are explainable and inspectable.

## 15.2 Routing accepted only if
- routing tab is clearly policy-first;
- low-level controls do not dominate;
- false-inform protection and curiosity decoupling are visible.

## 15.3 Trace accepted only if
- trace/debug tab shows real turn-level runtime information;
- trace unavailability is explicit and actionable;
- developer can inspect why the last answer happened the way it did.

## 15.4 Prompt operations accepted only if
- prompt tab shows effective assembly awareness;
- read-only/runtime-derived sections are understandable;
- prompt modifiers are visible operationally.

## 15.5 Whole 10.4.1 accepted only if
- remote debugging materially improves;
- operator can see route / diagnostics / retrieval / validation / memory flow for real turns;
- compatibility becomes secondary;
- admin surface becomes genuinely useful for bot tuning.

---

# 16. Delivery Plan

## Phase 0 — Operational Gaps Audit
- inventory current 10.4 gaps
- define exact missing trace/policy surfaces
- capture before-state screenshots and admin flows

## Phase 1 — Backend Effective/Trace Payloads
- add effective runtime payloads
- add admin trace endpoints / trace schema
- expose readonly reasons and usage metadata

## Phase 2 — Diagnostics and Routing Deepening
- deepen diagnostics tab
- make routing tab policy-first
- collapse advanced knobs

## Phase 3 — Trace / Debug Viewer
- implement real trace viewer
- add last-turn and recent-turn trace rendering
- add disabled/error states

## Phase 4 — Prompt Operations Completion
- add effective assembly preview
- add runtime usage markers
- improve readonly/derived explanations

## Phase 5 — UX Polish + Compatibility De-Emphasis + Final Tests
- de-emphasize compatibility
- tune header/utility placement
- run UI/contract/e2e tests
- update admin operator docs

---

# 17. Risk Management

## 17.1 Main risk
Можно перегрузить админку диагностической информацией и сделать её тяжёлой.

### Mitigation
- use cards and progressive disclosure;
- keep advanced controls collapsed;
- prioritize last-turn operational value over full raw dump.

## 17.2 Secondary risk
Можно показать trace data, которая не соответствует реальному runtime.

### Mitigation
- contract tests for trace payload;
- render from backend truth, not frontend inference;
- explicit unavailable/unknown states.

## 17.3 Prompt risk
Можно слишком расширить editable prompt surface.

### Mitigation
- keep safe defaults;
- limit editability where needed;
- explain readonly reasons instead of exposing unsafe edits.

---

# 18. Definition of Done

PRD_10.4.1 считается выполненным только если одновременно верно всё:

1. Diagnostics tab стал operational, а не summary-only.  
2. Routing tab стал policy-first и меньше transitional.  
3. Trace / Debug показывает реальный last-turn trace.  
4. Prompt tab показывает effective assembly awareness.  
5. Runtime tab показывает effective runtime truth глубже.  
6. Compatibility стал менее заметен.  
7. Backend trace/effective payloads валидируются контрактами.  
8. UI/e2e tests проходят.  
9. Разработчик реально может через админку понять, почему бот ответил именно так.  

---

# 19. Instructions to IDE Agent

1. Не делай 10.4.1 новым глобальным redesign.  
2. Работай как инженер operational depth completion.  
3. Главная цель — turn-level observability и policy-level clarity.  
4. Не возвращай legacy сущности ради “полноты контроля”.  
5. Не заставляй разработчика читать код, чтобы понять, почему бот так ответил.  
6. После каждой фазы:
   - обнови backend payloads;
   - обнови frontend surfaces;
   - обнови tests;
   - зафиксируй before/after screenshots and trace flows.

---

# 20. Final Note

PRD_10.4.1 intentionally focuses on one practical truth:

**Хорошая админка для такого бота нужна не только чтобы менять числа.  
Она нужна, чтобы удалённо понимать поведение живой системы.**

После 10.4.1 веб-админка должна помогать разработчику не только настраивать Neo MindBot,  
но и быстро видеть, диагностировать и объяснять его реальные ответы.
