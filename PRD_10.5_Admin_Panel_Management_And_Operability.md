# PRD_10.5_Admin_Panel_Management_And_Operability.md

## Product Requirements Document

**Версия:** 10.5  
**Статус:** ACTIVE — proposed for implementation by IDE agent  
**Тип итерации:** Admin Panel Cleanup / Remote Management / Operability  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Основные области:** `bot_psychologist/web_ui/`, `bot_psychologist/api/`, `bot_psychologist/config/`  
**Предшествующий контекст:** PRD 10.4 и 10.4.1 по Neo admin surface  
**Новая граница ответственности:** `/admin` = удалённые настройки + состояние системы.  
**Не входит в этот PRD:** подробный developer trace по конкретным сообщениям. Он будет оформлен отдельным следующим PRD для чата разработчика.

---

# 0. Executive Summary

Админка уже прошла через важный этап выравнивания под Neo runtime.  
Она больше не показывает старую картину мира как primary truth и уже содержит полезные панели:
- LLM
- Retrieval
- Diagnostics
- Routing
- Memory
- Prompts
- Runtime

Однако после расширения 10.4–10.4.1 в админке накопилось смешение двух разных задач:

1. **Remote management** — управление параметрами и эксплуатацией системы  
2. **Per-message debugging** — разбор того, как бот отработал конкретный turn  

Это смешение ухудшает продуктовую ясность.

Админка должна быть прежде всего:
- удобной,
- управляемой,
- безопасной,
- пригодной для удалённого администрирования,
а не дублировать developer trace, который естественнее живёт прямо в чате, рядом с конкретным ответом бота.

**Цель PRD_10.5:**  
очистить и доработать админку так, чтобы она стала сильной панелью удалённого управления и состояния системы,  
без глубокого message-level debug surface.

---

# 1. Why this iteration exists

## 1.1 Проблема текущего состояния
Сейчас админка уже намного лучше старой версии, но всё ещё частично тянет на себя debug-задачи, которые логичнее решать в developer trace внутри чата.

Это приводит к трём проблемам:

### A. Смешение ролей
Одна и та же панель пытается быть и:
- control panel,
- и trace console.

### B. Потеря фокуса на управляемости
Чем больше в админке per-turn подробностей, тем хуже она работает как быстрый инструмент удалённого управления.

### C. Неидеальная модель многосессионной работы
Для отладки конкретного сообщения нужен контекст самой беседы и конкретного ответа.  
Админка по природе хуже подходит для этого, чем trace внутри чата.

## 1.2 Что должно измениться
После 10.5 админка должна отвечать на вопросы:

- система жива?
- на каких настройках она реально работает?
- что сейчас включено?
- какие параметры я могу безопасно менять удалённо?
- как быстро вернуть дефолт / экспортировать / импортировать / откатить конфиг?

А не на вопросы вида:
- какой route был у последнего ответа?
- какие чанки попали в LLM на конкретном сообщении?
- почему этот конкретный ответ регенерировался?

Это всё — зона следующего PRD для developer trace в чате.

---

# 2. Product Goal of 10.5

## 2.1 Core goal
Сделать `/admin` **удобной и управляемой operational console** для:
- удалённой настройки бота;
- контроля состояния системы;
- безопасного изменения конфигурации;
- понимания effective runtime truth на уровне системы, а не отдельного сообщения.

## 2.2 Success perception
После 10.5 разработчик должен чувствовать:

- “через админку мне удобно управлять ботом удалённо”;
- “я быстро нахожу нужный параметр”;
- “я не путаюсь между настройками и отладкой сообщений”;
- “админка не перегружает меня лишним trace-шумом”;
- “если нужно разбирать конкретный ответ, я иду в developer trace чата, а не в admin”.

---

# 3. Scope of PRD_10.5

## 3.1 Входит в scope

1. Очистка админки от per-message trace responsibility  
2. Перефокусировка UI на remote management и operability  
3. Упрощение и усиление вкладок:
   - LLM
   - Retrieval
   - Routing
   - Memory
   - Prompts
   - Runtime
4. Пересборка Diagnostics tab как policy/config surface  
5. Удаление или урезание Trace/Debug из админки  
6. Улучшение editable vs read-only logic  
7. Улучшение usability:
   - группировка
   - подсказки
   - упрощение первичного экрана
   - снижение визуального шума
8. Улучшение config safety:
   - validation
   - export/import
   - reset
   - schema/version awareness
   - rollback-ready structure

## 3.2 Не входит в scope

В 10.5 не входят:
- новый runtime pipeline;
- новый retrieval engine;
- message-level trace deepening;
- отладка route decisions по каждому сообщению;
- trace history per session/message;
- cost breakdown per message;
- LLM raw payload inspection per answer;
- новая developer console в чате.

---

# 4. New Responsibility Boundary

## 4.1 What `/admin` is for
`/admin` должен быть предназначен для:
- remote configuration;
- runtime health;
- effective system state;
- policy management;
- prompt management;
- service actions.

## 4.2 What `/admin` is NOT for
`/admin` не должен быть главным местом для:
- разбора конкретного ответа;
- message-level routing forensics;
- retrieval trace конкретного turn;
- per-message anomalies;
- memory update trace конкретного сообщения;
- developer debugging narrative.

## 4.3 What goes to chat developer trace later
В отдельном следующем PRD будет вынесено в чат:
- routing/classification per message;
- pipeline timeline;
- retrieval blocks and rerank flow;
- output validation per message;
- memory context per message;
- config snapshot per answer;
- trace history per session.

---

# 5. Product Principles for 10.5

## 5.1 Management first
Главная функция админки — управление, а не трассировка.

## 5.2 Clear separation of concerns
Настройки системы и отладка отдельных ответов не должны смешиваться в одном основном инструменте.

## 5.3 Effective truth over noise
Админка должна показывать:
- что реально активно,
- что реально можно менять,
- что реально влияет на поведение системы.

## 5.4 Safe remote operation
Любой изменяемый параметр должен быть:
- валидируемым;
- предсказуемым;
- восстанавливаемым;
- понятным по эффекту.

## 5.5 Convenience matters
Админка должна быть удобной для быстрого использования, а не требовать чтения кода, чтобы понять, что делает настройка.

---

# 6. Fixed Decisions for 10.5

## 6.1 Remove deep Trace/Debug from admin
Полноценная Trace / Debug вкладка должна быть удалена из primary admin surface.

Допустимо оставить только:
- trace enabled/disabled status;
- trace storage available/unavailable;
- very shallow runtime-level trace availability indicator.

Но не подробный per-turn trace viewer.

## 6.2 Diagnostics tab becomes policy/config only
Diagnostics tab должен показывать:
- active diagnostics contract as system documentation;
- current behavior policies;
- informational narrowing state;
- mixed-query handling state;
- user correction policy;
- first-turn richness policy.

Из Diagnostics tab нужно убрать:
- last diagnostics snapshot;
- per-message confidence snapshot;
- per-turn derived values.

## 6.3 Runtime tab remains, but only as system-level truth
Runtime tab должен остаться, но быть строго про:
- health,
- effective config,
- feature flags,
- schema/version,
- source of truth,
- degraded mode,
- blocks loaded,
- config validation,
- cache/warmup/KG.

Не про конкретные turn traces.

## 6.4 Routing tab stays operational, not forensic
Routing tab должен оставаться полезным и включать:
- route taxonomy;
- current routing policy;
- false-inform protection;
- curiosity decoupling;
- practice trigger rules;
- safety override priority;
- advanced low-level knobs in collapsed section.

Но туда не должны попадать:
- last chosen route of a message;
- last routing decision reason;
- message-level rule firing history.

## 6.5 Prompt tab stays in admin
Prompt management — это именно задача админки.

Prompt tab должен остаться и улучшиться как:
- prompt stack v2 editor/inspector;
- editable vs read-only section manager;
- version-aware management surface;
- preview/diff surface;
- rollback-ready prompt management surface.

Но message-level prompt participation trace должен уйти в chat trace later.

## 6.6 Compatibility must become even more secondary
Compatibility controls допустимы только как:
- advanced,
- hidden by default,
- явно deprecated.

---

# 7. Target Admin Information Architecture After 10.5

## 7.1 Tabs to keep
- **LLM**
- **Retrieval**
- **Diagnostics**
- **Routing**
- **Memory**
- **Prompts**
- **Runtime**

## 7.2 Tabs to remove or reduce
- **Trace / Debug** — удалить как полноценную вкладку из primary admin surface

## 7.3 Optional secondary surfaces
- **Compatibility** — hidden/advanced only

---

# 8. Detailed Requirements by Tab

## 8.1 LLM
### Purpose
Удалённое управление LLM-конфигурацией.

### Must contain
- primary model;
- classifier model;
- max tokens;
- optional token limit controls;
- reasoning depth;
- streaming toggle;
- temperature where applicable;
- explanation/tooltips for each parameter.

### Must improve
- clearer explanation for reasoning-model limitations;
- effective active value display;
- validation for unsafe/invalid values.

---

## 8.2 Retrieval
### Purpose
Управление retrieval pipeline на уровне системы.

### Must contain
- initial top-k;
- min relevance threshold;
- confidence caps:
  - high
  - medium
  - low
  - zero
- rerank enabled;
- rerank top-k;
- rerank model;
- data source;
- degraded mode note.

### Must improve
- better explanations of what each cap means;
- clearer distinction between:
  - retrieval top-k,
  - rerank top-k,
  - final capped blocks;
- tooltips/examples for practical tuning.

### Must not contain
- chunks from the last message;
- retrieval trace of a specific answer.

---

## 8.3 Diagnostics
### Purpose
Управление и понимание diagnostics/policy layer на уровне всей системы.

### Must contain
- diagnostics contract overview;
- current behavior policies;
- informational narrowing;
- mixed-query handling;
- user correction protocol;
- first-turn richness policy;
- whether these are editable or read-only.

### Must improve
- turn static summary cards into clearer policy cards;
- explain what each policy influences;
- show effective state, not last message state.

### Must remove
- last diagnostics snapshot;
- message-level confidence snapshot;
- last turn-specific fields.

---

## 8.4 Routing
### Purpose
Управление route-policy layer.

### Must contain
- Neo route taxonomy;
- current routing policy;
- false-inform protection;
- curiosity decoupling;
- practice trigger rules;
- safety override priority;
- free conversation mode;
- advanced routing controls in collapsed section.

### Must improve
- clearer distinction between:
  - policy controls,
  - advanced low-level controls;
- better help text for advanced knobs;
- reduced clutter in main routing view.

### Must not contain
- last route trace;
- per-message routing decisions.

---

## 8.5 Memory
### Purpose
Управление conversational memory model.

### Must contain
- history depth;
- max context size;
- session limits;
- semantic memory on/off;
- semantic top-k;
- min similarity;
- semantic max chars;
- summary enabled;
- summary interval;
- summary max length;
- snapshot/state model summary.

### Must improve
- better explanation of each memory layer;
- clearer difference between:
  - dialogue history,
  - semantic memory,
  - summary;
- better usability of numeric fields.

### Must not contain
- memory trace per message;
- last turn summary update details.

---

## 8.6 Prompts
### Purpose
Удалённое управление prompt stack.

### Must contain
- prompt stack v2 sections;
- editable/read-only markers;
- version info;
- preview;
- original vs edited view;
- save/reset flow;
- read-only reasons;
- derived_from/source where relevant.

### Must improve
- usability of editing experience;
- clarity of why some sections are read-only;
- prompt change safety;
- pre-save validation;
- revert/rollback readiness.

### Must remove from admin
- last-turn section usage;
- per-message prompt participation trace.

---

## 8.7 Runtime
### Purpose
System health and effective runtime truth.

### Must contain
- schema/version;
- admin schema version;
- prompt stack version;
- diagnostics/routing enabled states;
- grouped feature flags;
- config validation status;
- system status;
- data source;
- degraded mode;
- blocks in memory;
- warmup;
- cache;
- KG state.

### Must improve
- clearer grouping;
- cleaner separation between:
  - effective truth,
  - raw flags,
  - editable runtime params;
- reduced visual overload.

### Must not contain
- per-message trace data;
- recent turn debug history.

---

# 9. Required Global UX Improvements

## 9.1 Reduce cognitive load
Нужно уменьшить ощущение “слишком много инженерных деталей сразу”.

### Requirements
- better grouping;
- collapsible advanced sections;
- shorter explanatory text where possible;
- consistent layout.

## 9.2 Improve discoverability
Оператор должен быстро находить:
- model controls,
- retrieval controls,
- routing policy,
- memory controls,
- prompts,
- runtime health.

## 9.3 Improve edit safety
Для изменяемых полей нужны:
- inline validation;
- safe ranges;
- explicit save feedback;
- better reset semantics.

## 9.4 Improve remote operability
Админка должна быть полезной при удалённой работе без доступа к коду или консоли.

---

# 10. Backend / API Requirements

## 10.1 Keep admin API focused
Admin API должен обслуживать:
- config retrieval,
- config update,
- prompt management,
- runtime status,
- effective system state.

## 10.2 Remove trace-heavy admin payloads from primary admin flow
Не использовать admin API как главный поставщик message-level trace surface.

## 10.3 Maintain schema versioning
Нужно сохранить:
- schema version;
- export/import compatibility;
- future rollback readiness.

## 10.4 Editable/read-only contract must remain explicit
Frontend должен точно знать:
- что editable;
- что read-only;
- почему read-only;
- откуда derived value.

---

# 11. Cleaning / Removal Plan

## 11.1 Remove from admin primary surface
- Trace / Debug as primary tab
- last diagnostics snapshot
- recent traces
- per-turn retrieval breakdown
- per-turn validation breakdown
- per-turn memory update breakdown
- per-turn prompt participation breakdown
- per-turn anomalies surface

## 11.2 Keep only lightweight system-level indicators
Можно оставить:
- trace enabled/disabled
- trace collection available/unavailable
- maybe pointer that deep trace is in developer chat mode

## 11.3 Add handoff language
Где уместно, UI может коротко пояснять:
- “deep message-level diagnostics are available in developer trace inside chat”

---

# 12. Testing Strategy

## 12.1 Main test intent
Эта итерация должна доказать:

**админка стала лучше как инструмент удалённого управления и перестала быть дублирующей debug-console**

## 12.2 Required test layers
Обязательны:
- unit
- contract
- frontend rendering tests
- admin integration tests
- e2e admin tests

## 12.3 Required tests

### Admin cleanup
- `tests/ui/test_trace_debug_tab_removed_from_primary_admin.py`
- `tests/ui/test_admin_tabs_focus_on_management_surfaces.py`

### Diagnostics cleanup
- `tests/ui/test_diagnostics_tab_policy_only_no_last_snapshot.py`

### Prompt cleanup
- `tests/ui/test_prompt_tab_no_last_turn_usage_surface.py`

### Runtime clarity
- `tests/ui/test_runtime_tab_system_level_only.py`

### Retrieval clarity
- `tests/ui/test_retrieval_tab_explains_caps_and_pipeline.py`

### Routing clarity
- `tests/ui/test_routing_tab_policy_first_and_no_forensic_trace.py`

### Contract tests
- `tests/contract/test_admin_schema_v105_management_only.py`
- `tests/contract/test_admin_payloads_no_message_level_trace_dependency.py`

### E2E
- `tests/e2e/test_admin_management_flow_without_trace_surface.py`
- `tests/e2e/test_admin_prompt_edit_and_runtime_status_flow.py`
- `tests/e2e/test_admin_export_import_reset_remote_operability.py`

---

# 13. Acceptance Criteria

## 13.1 Admin responsibility split accepted only if
- admin no longer duplicates deep per-message trace;
- message-level debug surfaces are removed from primary admin flow.

## 13.2 Usability accepted only if
- admin is easier to navigate;
- controls are grouped more clearly;
- advanced knobs are less noisy;
- management tasks are faster.

## 13.3 Operability accepted only if
- remote configuration remains strong or improves;
- runtime/system status remains visible;
- prompt/routing/retrieval/memory controls remain practical.

## 13.4 Whole 10.5 accepted only if
- `/admin` clearly becomes a management console;
- deep trace responsibility is removed from admin;
- safety/validation/versioning remain intact;
- developer can manage the bot remotely with less confusion and less noise.

---

# 14. Delivery Plan

## Phase 0 — Audit and Boundary Freeze
- inventory current admin surfaces
- mark management vs trace responsibilities
- freeze new ownership boundary

## Phase 1 — Remove Trace Responsibility from Admin
- remove primary trace/debug tab
- remove last diagnostics snapshot
- remove per-turn breakdown surfaces from admin

## Phase 2 — Rebuild Diagnostics / Runtime Around System-Level Truth
- diagnostics becomes policy/config only
- runtime becomes health/effective truth only

## Phase 3 — Improve Management Surfaces
- polish LLM / Retrieval / Routing / Memory / Prompts
- improve tooltips, grouping, advanced controls

## Phase 4 — Harden Safety and Operability
- validation
- export/import
- reset
- schema/version display
- save feedback and rollback readiness

## Phase 5 — Regression and Final UX Verification
- run full test pack
- verify admin is cleaner and more usable
- confirm no critical remote management capability was lost

---

# 15. Risk Management

## 15.1 Main risk
Можно убрать слишком много и ослабить useful observability.

### Mitigation
- keep Runtime tab strong;
- keep effective config truth;
- only remove message-level forensics, not system-level visibility.

## 15.2 Secondary risk
Можно сделать админку слишком “стерильной”, потеряв полезный context.

### Mitigation
- retain helpful policy summaries;
- improve explanations/tooltips;
- keep operationally useful read-only truth.

## 15.3 Prompt risk
Упрощая UI, можно ухудшить prompt management.

### Mitigation
- prompt tab remains first-class;
- editing, preview, versioning and read-only reasons must stay strong.

---

# 16. Definition of Done

PRD_10.5 считается выполненным только если одновременно верно всё:

1. `/admin` больше не дублирует deep per-message trace.  
2. Trace / Debug removed from primary admin surface.  
3. Diagnostics tab стал policy/config surface, а не last-message diagnostics view.  
4. Runtime tab стал system-level truth surface, а не debug surface.  
5. Retrieval / Routing / Memory / Prompts / LLM remain strong management tabs.  
6. Admin usability materially improves.  
7. Remote configuration remains safe and effective.  
8. Export/import/reset/versioning/validation remain intact.  
9. UI/contract/e2e tests pass.  

---

# 17. Instructions to IDE Agent

1. Не превращай 10.5 в новый большой redesign.  
2. Работай как инженер управляемости и удобства админки.  
3. Главный приоритет — очистить границы ответственности.  
4. Сохрани сильную удалённую управляемость.  
5. Убери message-level debugging из admin, но не ослабь system-level visibility.  
6. После каждой фазы:
   - обнови frontend;
   - обнови backend payloads where needed;
   - обнови tests;
   - зафиксируй before/after screenshots of admin UX.

---

# 18. Final Note

PRD_10.5 intentionally focuses on one practical truth:

**Админка должна помогать управлять ботом, а не пытаться стать местом для полного разбора каждого ответа.**

После 10.5 `/admin` должен стать:
- чище,
- удобнее,
- понятнее,
- безопаснее,
- сильнее именно как панель удалённого управления Neo MindBot.
