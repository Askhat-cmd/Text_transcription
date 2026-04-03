# PRD_10.4_Admin_Panel_Neo_Realignment

## Product Requirements Document

**Версия:** 10.4  
**Статус:** ACTIVE — proposed for implementation by IDE agent  
**Тип итерации:** Admin Surface Realignment / Config Truth / Legacy UI Cleanup  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Основные области:** `web-ui/`, `api/`, `bot_psychologist/`, `admin config backend`  
**Предшествующий документ:** `PRD_10.3.1_Curious_Inform_Decoupling.md`  
**Правило совместимости:** PRD_10.4 не заменяет runtime PRD 10.1–10.3.1. Это отдельная итерация по выравниванию веб-админки под уже существующий Neo runtime.

---

# 0. Executive Summary

После серии итераций 10.1 → 10.3.1 сам runtime Neo MindBot уже существенно изменился:

- deterministic routing,
- diagnostics v1,
- prompt stack v2,
- output validation,
- memory v1.1,
- informational recalibration,
- curious/inform decoupling.

Но веб-админка по скриншотам и текущему состоянию UI **всё ещё отражает старую эпоху проекта**, а не текущий runtime truth.

Сейчас в интерфейсе видны legacy-сущности и настройки, которые больше не являются главной архитектурной реальностью:
- SD classifier,
- Decision Gate,
- Path/Prompt Priority старого типа,
- legacy prompt groups по SD и user-level,
- outdated routing mental model,
- misleading prompt naming,
- failed prompt fetch state.

Это создаёт сразу несколько проблем:
1. интерфейс врёт о системе;
2. оператор может настраивать уже несуществующую логику;
3. сложно отлаживать Neo runtime через UI;
4. legacy-мышление продолжает жить через админку, даже если runtime уже ушёл дальше.

**Цель PRD_10.4:**  
полностью привести веб-админку в соответствие с Neo runtime truth,  
убрать misleading legacy surface и сделать админку рабочим инструментом для управления реальной системой, а не музейной витриной старых слоёв.

---

# 1. Why this iteration exists

## 1.1 Проблема не только в “старом дизайне”
Проблема не сводится к визуальной устарелости.  
Сейчас админка показывает **неправильную модель системы**.

Это хуже, чем просто некрасивый UI.

## 1.2 Что видно по текущим скринам

### Routing tab
Показывает legacy-layer stack:
- Layer 1: Fast Detector
- Layer 2: State Classifier
- Layer 3: SD Classifier
- Layer 4: Decision Gate
- Layer 5: Path/Prompt Priority

Это уже не соответствует Neo runtime как единственной source of truth.

### Prompts tab
Показывает:
- Spiral Dynamics prompts
- user-level prompts
- `Mode: informational (curious)`
- failed prompt fetch

Это прямо конфликтует с текущей логикой 10.3.1, где curiosity decoupled from informational override.

### Memory / Search / Runtime
Частично полезны, но информационная архитектура вкладок всё ещё собрана не вокруг:
- diagnostics v1
- route resolver
- memory summary/snapshot
- output validator
- practice selector
- current feature flags
- prompt stack v2

## 1.3 Почему это нужно делать отдельной итерацией
Если смешать это с очередным runtime рефакторингом, получится хаос.

Админка — это отдельный operational surface.  
Её нужно переделывать **как отдельную спецификацию**, с фокусом на:
- truthfulness,
- operability,
- config safety,
- observability,
- alignment with actual runtime.

---

# 2. Product Goal of 10.4

## 2.1 Core goal
Сделать так, чтобы веб-админка:

- отражала только актуальную архитектуру Neo runtime;
- не показывала legacy-сущности как active truth;
- позволяла безопасно управлять реальными runtime-параметрами;
- помогала дебажить живую систему;
- не подталкивала оператора к неправильным mental models.

## 2.2 Success perception
После 10.4 оператор должен ощущать:

- “я вижу ту систему, которая реально работает”;
- “я не путаюсь между старым и новым”;
- “я могу настроить retrieval / routing / prompts / memory / validation без археологии”;
- “админка помогает понимать pipeline, а не запутывает”.

---

# 3. Scope of PRD_10.4

## 3.1 Входит в scope

1. Удаление legacy runtime concepts из UI  
2. Пересборка вкладок и информационной архитектуры под Neo runtime  
3. Новый prompt/admin model для prompt stack v2  
4. Новый routing/admin model для Neo diagnostics + route resolver  
5. Новый memory/admin model под summary/snapshot/context  
6. Новый runtime/debug surface для реального live pipeline  
7. Config/schema alignment between backend and UI  
8. Fix broken prompt fetching and related admin loading states  
9. Export/import/versioning/rollback behavior for admin config

## 3.2 Не входит в scope

В 10.4 не входят:
- новая бизнес-логика самого runtime;
- новая retrieval-философия;
- новый classifier stack;
- большая переработка базы знаний;
- редизайн ради красоты без product alignment;
- полноценная аналитическая BI-панель;
- mobile-first redesign.

## 3.3 Scope discipline
Любое изменение должно отвечать на вопрос:

**Это делает админку более честным и полезным отражением Neo runtime?**

Если нет — задача out-of-scope.

---

# 4. Product Principles for 10.4

## 4.1 Admin UI must reflect runtime truth
Интерфейс не должен показывать устаревшую модель системы как активную.

## 4.2 No legacy mythology in primary UI
Старые сущности можно оставить только:
- в migration/dev section,
- в compatibility section,
- или полностью убрать из UI.

Но не в primary operational tabs.

## 4.3 Config must be safe to edit
Любая изменяемая настройка должна иметь:
- validation,
- versioning,
- rollback,
- visible effective value.

## 4.4 Read-only truth is better than misleading editability
Если какая-то часть системы ещё не готова к безопасному редактированию через UI, лучше показать её как read-only, чем как фальшиво editable control.

## 4.5 Admin IA must follow actual pipeline
Вкладки и группы должны повторять реальную архитектуру:
- LLM
- Retrieval
- Diagnostics
- Routing
- Memory
- Prompts
- Runtime / Trace
- Compatibility / Legacy (optional hidden)

---

# 5. Current UI Problems to Fix

## 5.1 Legacy routing mental model
Текущая вкладка “Маршрутизация” закрепляет старую схему layer-by-layer, включая SD и Decision Gate.

Это надо убрать из primary UI.

## 5.2 Prompt library is architecturally stale
Текущий список промптов показывает:
- SD prompts,
- user level prompts,
- curious informational mode prompt,
- old grouping logic.

Это вводит в заблуждение.

## 5.3 Prompt fetch instability
На скрине есть `Failed to fetch` в Prompt UI.  
Это must-fix issue.

## 5.4 Search tab is too low-level without runtime explanation
Настройки retrieval полезны, но их нужно вписать в понятный Neo context:
- initial top-k
- rerank
- confidence cap
- final block cap
- source of knowledge
- degraded mode behavior

## 5.5 Memory tab lacks Neo mental model
Память сейчас выглядит как набор чисел, но не как:
- dialogue context depth,
- summary policy,
- snapshot policy,
- semantic memory usage,
- session continuity behavior.

## 5.6 Runtime tab is too shallow
Runtime section показывает только несколько system toggles, но не даёт реальной operational visibility в:
- active runtime version
- source of truth
- enabled feature flags
- degraded mode state
- live pipeline alignment
- trace diagnostics availability

---

# 6. Fixed Decisions for 10.4

## 6.1 Remove SD, user-level and legacy decision-gate from primary admin surface
В primary admin UI больше не должно быть active sections про:
- SD classifier
- user level adaptation
- old Decision Gate
- old Path/Prompt Priority logic

Если совместимость ещё нужна, это должно жить в:
- hidden compatibility panel,
- advanced legacy diagnostics section,
- migration-only view.

Но не в основной operational поверхности.

## 6.2 Routing tab must represent Neo runtime
Вместо legacy stack routing tab должен показывать:

1. diagnostics v1  
2. route resolver  
3. informational narrowing / mixed-query behavior  
4. practice selection trigger  
5. safety override policy  
6. output validation coupling

## 6.3 Prompt tab must represent prompt stack v2
Вместо SD / level-based prompt lists prompt UI должен отображать:

- `AA_SAFETY`
- `A_STYLE_POLICY`
- `CORE_IDENTITY`
- `CONTEXT_MEMORY`
- `DIAGNOSTIC_CONTEXT`
- `RETRIEVED_CONTEXT`
- `TASK_INSTRUCTION`

И отдельно:
- variants / modifiers
- versioning
- active/inactive flags
- last updated metadata

## 6.4 Memory tab must represent memory v1.1 behavior
Memory UI должен показывать:
- conversation history depth
- summary usage
- summary update interval
- summary max length
- semantic memory toggle and thresholds
- snapshot v1.1 status
- context strategy (fresh / stale / missing summary)
- active continuity policy

## 6.5 Runtime tab must become operational truth panel
Runtime section должен показывать:
- active runtime version
- Neo mode enabled or not
- degraded mode status
- knowledge source
- blocks loaded
- active feature flags
- prompt stack v2 enabled
- output validation enabled
- informational branch enabled
- diagnostics v1 enabled
- route resolver enabled

## 6.6 Prompt fetch must be stable and inspectable
Если prompt fetch падает:
- UI должен показывать понятную ошибку;
- должна быть retry action;
- должно быть видно source/backend response state;
- нельзя просто показывать generic `Failed to fetch` без operational context.

---

# 7. Target Information Architecture

## 7.1 Proposed top-level tabs

1. **LLM**  
2. **Retrieval**  
3. **Diagnostics**  
4. **Routing**  
5. **Memory**  
6. **Prompts**  
7. **Runtime**  
8. **Trace / Debug**  
9. **Compatibility** (optional hidden or advanced)

## 7.2 What should disappear from primary IA
Не должно быть в primary IA:
- SD as active classifier tab
- user-level runtime adaptation
- old layer 1-5 routing mental model
- curious informational mode prompt as a primary prompt artifact
- old path/prompt priority panel

---

# 8. Detailed Requirements by Tab

## 8.1 LLM
Должно содержать:
- primary model
- classifier model
- max tokens / completion limits
- reasoning depth if applicable
- streaming toggle
- temperature / mode notes
- effective active values
- model capability notes where useful

## 8.2 Retrieval
Должно содержать:
- initial top-k
- minimum relevance threshold
- confidence caps by level
- rerank enabled
- rerank model
- rerank top-k
- knowledge source
- degraded retrieval fallback state
- optional legacy metadata filtering note as read-only if exists

Важно:
UI должен объяснять разницу между:
- initial retrieval
- rerank result
- final capped blocks

## 8.3 Diagnostics
Новая вкладка.

Должна содержать:
- interaction_mode behavior
- nervous_system_state behavior
- request_function behavior
- core_theme behavior
- informational narrowing policy
- mixed-query policy
- first-turn policy
- user correction protocol

Не должно содержать:
- SD classifier
- user level classification
- old 10-layer pseudo-psychological routing abstractions as primary truth

## 8.4 Routing
Должна содержать:
- route taxonomy:
  - safe_override
  - regulate
  - reflect
  - practice
  - inform
  - contact_hold
- deterministic route resolver enabled
- route confidence / cap relation
- practice trigger rules
- informational route narrowing toggles if editable
- false-inform protection state
- curiosity decoupling state (read-only or editable depending on safety)

## 8.5 Memory
Должна содержать:
- history depth
- max context size
- semantic memory enabled
- semantic top-k
- semantic min similarity
- semantic max chars
- summary enabled
- summary update interval
- summary max length
- snapshot v1.1 enabled
- summary staleness behavior
- context fallback policy summary

## 8.6 Prompts
Должна содержать:
- prompt stack v2 groups
- active prompt versions
- edit / preview / validate
- version history
- diff between versions
- effective prompt assembly preview
- loading state and fetch diagnostics
- prompt fetch retry

Не должна содержать в primary list:
- Spiral Dynamics prompt groups
- user-level prompt groups
- `Mode: informational (curious)` as active runtime truth

## 8.7 Runtime
Должна содержать:
- system status
- API / degraded mode
- blocks in memory
- version
- warmup enabled
- query cache enabled
- knowledge graph state
- feature flags summary
- active source of truth summary

## 8.8 Trace / Debug
Новая или расширенная вкладка.

Должна содержать:
- last turn route
- diagnostics snapshot
- retrieval stages
- blocks before/after rerank/cap
- output validation result
- selected practice
- memory summary status
- pipeline anomalies
- prompt stack summary
- no fake legacy stages if they are disabled

## 8.9 Compatibility
Если нужно оставить legacy controls:
- спрятать в advanced / compatibility view;
- clearly mark as deprecated;
- do not present as default operational controls.

---

# 9. Backend / API Requirements for Admin Surface

## 9.1 Admin config schema must be explicit
Нужен единый backend schema для админки:
- with typed sections;
- with version;
- with validation;
- with effective values;
- with editable vs read-only markers.

## 9.2 UI must not invent fields from old templates
Frontend не должен рендерить legacy fields просто потому, что они раньше были в статическом шаблоне.

## 9.3 Prompt API must support prompt stack v2 model
Backend должен возвращать prompt groups в актуальной Neo структуре.

## 9.4 Read-only status fields must be separated from editable config
Нужно чётко различать:
- editable runtime config
- derived runtime status
- debug-only operational state

---

# 10. Prompt Surface Realignment

## 10.1 Legacy prompt groups to hide or retire from primary UI
- SD prompt groups
- user-level prompt groups
- old curious-inform prompt artifacts
- any prompts tied to removed legacy routing assumptions

## 10.2 Active prompt groups to expose
- AA_SAFETY
- A_STYLE_POLICY
- CORE_IDENTITY
- CONTEXT_MEMORY
- DIAGNOSTIC_CONTEXT
- RETRIEVED_CONTEXT
- TASK_INSTRUCTION

## 10.3 Variant support
Prompt UI should support variants like:
- inform-rich
- mixed-query modifier
- first-turn modifier
- user-correction modifier
- safe override modifier

But as variants under current stack, not as free-floating legacy files.

---

# 11. UX Requirements

## 11.1 UI must reduce confusion
Оператор не должен гадать:
- что реально включено;
- что legacy;
- что editable;
- что derived.

## 11.2 Errors must be actionable
Любая ошибка вроде `Failed to fetch` должна иметь:
- clear source
- retry
- maybe backend error text
- degraded fallback or empty state guidance

## 11.3 Sections must explain what they affect
Каждая группа настроек должна коротко объяснять:
- что она меняет;
- когда применяется;
- чем отличается от соседних групп.

## 11.4 Do not expose hidden complexity without structure
Если параметров много, UI должен использовать:
- grouped panels
- section descriptions
- tooltips
- read-only derived state blocks

---

# 12. Migration Strategy

## 12.1 Do not delete runtime first
Сначала:
- align backend config schema
- align frontend render model
- mark deprecated sections
- migrate UI

Потом:
- optionally remove dead admin-only legacy code

## 12.2 Legacy UI fields may remain temporarily behind compatibility gate
Если immediate removal рискован:
- hide behind feature flag
- mark deprecated
- exclude from primary tabs

## 12.3 Export/import compatibility
Admin export/import должен:
- поддерживать schema version;
- уметь читать старые payloads;
- маппить старые поля в новые или безопасно игнорировать их.

---

# 13. Testing Strategy

## 13.1 Main test intent
Эта итерация должна доказать:

**админка больше не врёт о том, как устроен Neo runtime**

## 13.2 Required test layers
Обязательны:
- unit
- integration
- frontend rendering tests
- contract tests
- e2e UI tests
- regression tests

## 13.3 Required tests

### Legacy surface cleanup
- `tests/ui/test_legacy_sd_controls_hidden_from_primary_admin.py`
- `tests/ui/test_user_level_controls_hidden_from_primary_admin.py`
- `tests/ui/test_old_routing_stack_not_shown_in_primary_tabs.py`

### Prompt UI
- `tests/ui/test_prompt_stack_v2_groups_rendered.py`
- `tests/ui/test_legacy_prompt_groups_not_primary.py`
- `tests/ui/test_prompt_fetch_error_state_actionable.py`

### Routing / diagnostics UI
- `tests/ui/test_routing_tab_matches_neo_route_taxonomy.py`
- `tests/ui/test_diagnostics_tab_matches_v1_contract.py`

### Runtime / memory UI
- `tests/ui/test_runtime_tab_shows_real_feature_flags.py`
- `tests/ui/test_memory_tab_shows_summary_and_snapshot_model.py`

### Contract tests
- `tests/contract/test_admin_config_schema_v104.py`
- `tests/contract/test_prompt_admin_api_matches_prompt_stack_v2.py`

### E2E
- `tests/e2e/test_admin_ui_loads_without_legacy_primary_surface.py`
- `tests/e2e/test_prompt_fetch_and_retry_flow.py`
- `tests/e2e/test_export_import_with_schema_versioning.py`

---

# 14. Acceptance Criteria

## 14.1 UI cleanup accepted only if
- primary admin tabs no longer present legacy SD/user-level/decision-gate mental model;
- outdated routing stack is removed from main surface.

## 14.2 Prompt tab accepted only if
- prompt stack v2 is the visible active truth;
- failed fetch state is actionable;
- legacy prompt groups are hidden or deprecated-only.

## 14.3 Memory/runtime accepted only if
- memory UI reflects summary/snapshot/semantic model;
- runtime UI reflects actual live feature flags and source of truth.

## 14.4 Whole 10.4 accepted only if
- admin panel aligns with Neo runtime truth;
- operator confusion is materially reduced;
- no misleading legacy operational controls remain in primary UI;
- config export/import remains safe;
- tests prove UI and backend schema alignment.

---

# 15. Delivery Plan

## Phase 0 — Admin Surface Audit Baseline
- inventory current tabs
- map every visible section to actual runtime relevance
- classify sections as:
  - active
  - deprecated
  - misleading
  - broken

## Phase 1 — Backend Schema Alignment
- define admin config schema v10.4
- separate editable vs read-only
- version config payloads
- add compatibility mapping

## Phase 2 — Primary IA Rebuild
- rebuild tabs around Neo runtime
- hide/remove primary legacy sections
- add Diagnostics and Trace/Debug surfaces

## Phase 3 — Prompt UI Realignment
- implement prompt stack v2 grouping
- remove legacy prompt primacy
- fix failed fetch flow
- add versioning and preview support

## Phase 4 — Runtime / Memory / Retrieval Panels
- align these tabs with actual runtime behavior
- expose effective values and status
- remove misleading labels

## Phase 5 — Compatibility / Regression Hardening
- add hidden compatibility view if needed
- test export/import
- verify no broken admin flows remain

---

# 16. Risk Management

## 16.1 Main risk
Можно случайно сломать useful admin workflows, удаляя legacy UI слишком резко.

### Mitigation
- keep compatibility section if needed;
- deprecate before hard delete where necessary;
- back config with explicit schema versioning.

## 16.2 Secondary risk
Можно сделать “красивую админку”, которая всё ещё не соответствует backend truth.

### Mitigation
- contract tests between UI and admin API;
- render only schema-backed fields;
- expose effective values.

## 16.3 Prompt risk
Prompt editor можно сделать слишком свободным и опасным.

### Mitigation
- validation before save;
- version history;
- rollback;
- read-only for sensitive sections if needed.

---

# 17. Definition of Done

PRD_10.4 считается выполненным только если одновременно верно всё:

1. Primary admin UI no longer uses legacy routing mental model.  
2. SD/user-level/old Decision Gate are removed from primary operational surface.  
3. Prompt tab reflects prompt stack v2 instead of legacy prompt groups.  
4. Prompt fetch flow is stable and actionable on failure.  
5. Memory tab reflects Neo summary/snapshot model.  
6. Runtime tab reflects actual live system status and feature flags.  
7. Diagnostics and Routing tabs map to real Neo runtime concepts.  
8. Compatibility is hidden/deprecated rather than primary.  
9. Admin config schema is versioned and validated.  
10. UI tests and contract tests pass.  

---

# 18. Instructions to IDE Agent

1. Не превращай 10.4 в runtime refactor.  
2. Работай как инженер operational surface alignment.  
3. Главная задача — сделать admin UI честным отражением текущей системы.  
4. Не держи legacy controls в primary surface просто “на всякий случай”.  
5. Если legacy ещё нужно — убери в compatibility / deprecated section.  
6. После каждой фазы:
   - обнови backend schema;
   - обнови frontend rendering;
   - обнови tests;
   - проверь, что UI не врёт о runtime.

---

# 19. Final Note

PRD_10.4 intentionally focuses on one operational truth:

**Если runtime уже Neo, админка тоже должна стать Neo.**

Нельзя строить новую систему и продолжать управлять ею через интерфейс,
который рассказывает оператору старую историю про SD, user-level и Decision Gate.

После 10.4 веб-админка должна стать:
- понятной,
- честной,
- полезной,
- aligned with reality,
- пригодной для управления живым Neo MindBot, а не его прошлой версией.
