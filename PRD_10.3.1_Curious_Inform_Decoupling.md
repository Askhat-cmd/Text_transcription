# PRD_10.3.1_Curious_Inform_Decoupling

## Product Requirements Document

**Версия:** 10.3.1  
**Статус:** ACTIVE — proposed for implementation by IDE agent  
**Тип итерации:** Corrective Patch / Behavioral Routing Fix / Informational Decoupling  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Основные области:** `bot_psychologist/bot_agent/`, `api/`, `tests/`  
**Предшествующий документ:** `PRD_10.3_Response_Richness_Recalibration.md`  
**Правило совместимости:** PRD_10.3.1 не заменяет PRD_10.3 целиком. Это узкий corrective release, который должен добить главный root cause sparse behavior, оставшийся после 10.3.

---

# 0. Executive Summary

После PRD_10.3 в проекте реально улучшены:

- style policy для `inform`;
- richer task instructions;
- anti-sparse validation;
- защита от FAQ-like answer body.

Однако live-логи и код показывают, что **главный источник слишком скупого поведения всё ещё не устранён полностью**.

Основной симптом:
- запросы exploratory / reflective типа продолжают попадать в informational-like behavior слишком легко;
- на реальных запросах runtime по-прежнему выбирает `route=inform`;
- practice layer пропускается;
- ответ получает richer prompt, но остаётся в ограниченной explanatory рамке;
- итоговая субъективная “скупость” снижается недостаточно.

Корневой технический источник:
- в `answer_adaptive.py` всё ещё присутствует жёсткая связка `curious -> prompt_mode_informational`;
- `informational_mode` продолжает зависеть от `mode_prompt_override`;
- anti-sparse validator вероятно недоподключён, если в runtime не передаётся исходный `query`;
- therefore richness tuning partially works, but upstream routing still compresses behavior.

**Цель PRD_10.3.1:**  
не переписывать весь runtime, а **точечно разорвать связку между `curious` и informational dryness**,  
сузить true informational activation и добить runtime-подключение anti-sparse protection.

---

# 1. Important Clarification About SD

## 1.1 Что нужно различать

В системе есть как минимум два разных смысла SD:

### A. SD как live runtime influence
Это то, что НЕ должно управлять текущим поведением:
- runtime route selection;
- state framing;
- response generation policy;
- mode override;
- response metadata logic.

### B. SD как историческая разметка чанков
Это может оставаться в данных как пассивная metadata-разметка:
- SD labels на чанках;
- старые поля в knowledge base;
- historical enrichment fields;
- архивные признаки, не влияющие на live decision path.

## 1.2 Решение для 10.3.1

PRD_10.3.1 **не требует удалять chunk-level SD metadata**, если:

- она больше не управляет runtime routing;
- она не участвует в prompt policy как active controller;
- она не искажает output behavior;
- она остаётся просто исторической/пассивной разметкой данных.

То есть:

**remove runtime SD influence** ≠ **physically delete all SD labels from chunks**

## 1.3 Что запрещено
Нельзя:
- использовать chunk-level `GREEN` как implicit runtime user-state signal;
- использовать SD label чанка как скрытый controller richness/route/mode;
- делать вид, что SD “убран”, если он просто переехал в другой активный слой orchestration.

---

# 2. Why this corrective iteration exists

## 2.1 Что показали live logs
Live logs после 10.3 показывают:

- запрос про самоосознание получает `curious`;
- runtime остаётся на deterministic path;
- retrieval и rerank работают хорошо;
- однако дальше всё равно видно `route=inform` и `PRACTICE skipped for route=inform`;
- bot therefore behaves more richly than before, but still more informational than intended.

## 2.2 Что показал код
В runtime-коде всё ещё присутствует логика:

- `MODE_PROMPT_MAP = {"curious": "prompt_mode_informational"}`
- `informational_mode = bool(mode_prompt_override)`

Это означает, что exploratory curiosity всё ещё слишком близка к informational override.

## 2.3 Почему 10.3 не добил проблему до конца
10.3 улучшил:
- prompt richness;
- task instruction;
- validator richness awareness.

Но он не до конца изменил:
- routing activation source;
- mode override derivation;
- coupling between `curious` and informationality.

---

# 3. Scope of PRD_10.3.1

## 3.1 Входит в scope

1. Удаление жёсткой связки `curious -> informational mode prompt override`
2. Перекалибровка derivation логики `informational_mode`
3. Сужение true informational activation
4. Проверка и фиксация передачи `query` в output validation
5. Улучшение mixed/exploratory behavior без route explosion
6. Regression tests specifically against false `inform`
7. Live-log verification after patch

## 3.2 Не входит в scope

В 10.3.1 не входят:
- новый prompt stack version;
- новая memory schema;
- новый retrieval engine;
- новая diagnostics philosophy;
- новый large routing tree;
- физическое удаление chunk-level SD metadata из базы;
- новая purge-итерация по всему legacy-коду.

## 3.3 Scope discipline
Любая задача должна отвечать на вопрос:

**Она уменьшает ложное informational схлопывание exploratory запросов?**

Если нет — задача out-of-scope.

---

# 4. Root Cause Definition

## 4.1 Root Cause A — curiosity is still treated as quasi-informational
`curious` в системе всё ещё ведёт себя как скрытая прокси-переменная для explanatory mode.

Это неверно.

`curious` должен означать:
- исследовательскую открытость;
- готовность к осмыслению;
- интерес к различению и пониманию;

а не:
- почти-справочный режим,
- снижение coaching richness,
- ограниченный explanatory body.

## 4.2 Root Cause B — informational mode is derived too early and too broadly
Сейчас `informational_mode` слишком сильно зависит от наличия mode override.

Это делает informational behavior слишком лёгким для активации.

## 4.3 Root Cause C — validator may not be fully operational in runtime
Если anti-sparse validator вызывается без `query`, часть правил underfilled detection не сработает как задумано.

В результате:
- anti-sparse layer формально написан;
- но не всегда реально защищает output от бедного explanatory body.

---

# 5. Product Goal of 10.3.1

## 5.1 Core goal
Сделать так, чтобы:

- `curious` больше не тянул бот в informational dryness;
- exploratory / self-referential / practical questions не схлопывались в `inform`;
- informational route активировался только там, где он действительно нужен;
- anti-sparse validation реально работал в live runtime;
- chunk-level SD metadata могла существовать пассивно, не влияя на поведение.

## 5.2 Success perception
После 10.3.1 пользователь должен замечать:

- бот реже отвечает “как справочник” на живые exploratory вопросы;
- запросы типа “кажется, это про меня” больше не звучат как glossary reply;
- “как начать это практиковать?” не получает полу-справочный ответ;
- informational answers остаются ясными, но не становятся default trap.

---

# 6. Fixed Decisions for 10.3.1

## 6.1 Remove hard mapping of `curious` to `prompt_mode_informational`
Это решение обязательно.

После 10.3.1:
- `curious` не должен автоматически маппиться на informational mode prompt;
- `curious` сам по себе не должен включать explanatory override.

## 6.2 `informational_mode` must not be derived from override presence alone
`informational_mode` нельзя определять через:
- `bool(mode_prompt_override)`

Потому что это превращает внутренний prompt helper в runtime behavioral switch.

## 6.3 Informational activation must become evidence-based
Pure `inform` допустим только если запрос действительно:
- concept-first;
- explanation-first;
- definition-first;
- comparison-first without strong self-application framing.

## 6.4 Mixed/exploratory/practical questions must resist false `inform`
Запросы типа:
- “кажется, это про меня”
- “как это увидеть у себя”
- “а как начать это практиковать?”
- “что это значит в реальном опыте?”

не должны default-иться в pure `inform`.

## 6.5 Chunk-level SD labels may remain as passive metadata
Если SD labels на чанках есть исторически:
- не удалять их насильно в этой итерации;
- не использовать их как active user/runtime control signal.

## 6.6 Validator must receive the original query
Если `output_validator` использует query-aware anti-sparse rules, runtime обязан реально передавать `query` в validation path.

---

# 7. Target Behavioral Model After 10.3.1

## 7.1 `curious` should mean this
- пользователь открыт к исследованию;
- можно давать живой, содержательный, разворачивающий ответ;
- это не повод автоматически включать informational narrowness.

## 7.2 True informational queries should remain informational
Например:
- “что такое самоосознание?”
- “в чём разница между присутствием и наблюдением?”
- “объясни термин X”

Но даже тут ответ может быть:
- ясным;
- живым;
- различающим;
- не FAQ-like.

## 7.3 Exploratory-personal queries should no longer collapse
Например:
- “кажется, это про меня”
- “как это увидеть у себя?”
- “как начать это практиковать?”

Должны вести к richer behavior:
- mixed
- coaching-biased
- concept + self-application
- concept + practical lens

---

# 8. Required Runtime Changes

## 8.1 `answer_adaptive.py` — decouple curiosity from informational override

### Сделать
- убрать `curious` из `MODE_PROMPT_MAP`;
- либо оставить `MODE_PROMPT_MAP` только для действительно специальных режимов;
- не использовать curiosity as shorthand for informational override.

### Цель
Убрать старый root-cause at the source.

---

## 8.2 Rebuild `informational_mode` derivation

### Сделать
Вместо:
- `informational_mode = bool(mode_prompt_override)`

ввести более явную логику:
- informational only if diagnostics / heuristics / routing evidence strongly says concept-first explanatory query;
- override text may support style, but must not define mode alone.

### Цель
Разорвать ложную зависимость mode-behavior от prompt override helper.

---

## 8.3 Narrow informational activation rules

### Сделать
Пересмотреть условия, где `interaction_mode` / `route=inform` считаются корректными.

### Explicitly keep as `inform`
- “что такое X?”
- “объясни термин X”
- “в чём отличие A и B?”

### Explicitly resist pure `inform`
- “мне кажется, это про меня”
- “как это увидеть у себя”
- “как начать практиковать”
- “что это значит в реальном опыте”
- “помоги понять это на моём случае”

### Цель
Сделать `inform` точнее и реже как false-positive.

---

## 8.4 Mixed/exploratory queries should use richer modifiers
Не обязательно добавлять новый route enum.
Разрешено решить это через:
- flags/modifiers;
- task instruction enrichments;
- style policy modifiers;
- route refinement rules.

Главное:
- не плодить лишнюю route taxonomy без нужды;
- не оставлять current false-inform behavior.

---

## 8.5 Pass `query` into `_apply_output_validation_policy(...)`

### Сделать
Проверить все runtime вызовы validation:
- fast path
- regular adaptive path
- retry path if applicable

И убедиться, что original `query` реально передаётся в validator.

### Цель
Чтобы `underfilled_inform_answer` реально срабатывал, когда нужно.

---

## 8.6 Preserve passive chunk metadata
Если на чанках есть SD label `GREEN`:
- не удалять её в этой итерации из knowledge base;
- не ломать retrieval contract только ради purge purity;
- но удостовериться, что эта metadata не управляет current user behavior.

---

# 9. Prompt / Policy Adjustments

## 9.1 Keep 10.3 richness improvements
Нужно сохранить уже внедрённые улучшения:
- richer `inform` style policy;
- anti-sparse task instructions;
- mixed-query enrichment;
- softened first-turn structure.

## 9.2 Do not revert to old dry informational style
10.3.1 не должен откатывать:
- живую explanatory style policy;
- richer comparison behavior;
- anti-FAQ constraints.

## 9.3 Optional small policy refinement
Если после decoupling потребуется тонкая подстройка:
- можно добавить extra modifier for concept-first but self-referential queries;
- но без новой большой prompt-архитектуры.

---

# 10. Output Validation Correction

## 10.1 Query-aware validation must become real, not nominal
Если validator проверяет:
- comparison completeness;
- bridge-without-depth;
- underfilled inform answer;

то runtime обязан давать ему исходный вопрос.

## 10.2 Anti-sparse validation should not misfire on safe brevity
Сохранить допустимую краткость для:
- safe_override;
- regulate;
- hypo-sensitive responses;
- explicit short answer requests.

## 10.3 Regeneration path must use same query-aware context
Если validator инициирует regeneration:
- regeneration hint должен опираться на исходный запрос;
- нельзя терять user intent на retry step.

---

# 11. Required Code Changes

## 11.1 `answer_adaptive.py`
- удалить `curious` из `MODE_PROMPT_MAP` либо radically change its meaning;
- пересчитать `informational_mode`;
- сузить informational_mode_hint activation;
- передавать `query` в `_apply_output_validation_policy(...)`;
- проверить both fast path and regular path;
- при необходимости обновить debug metadata.

## 11.2 `diagnostics_classifier.py`
- если informational detection partly сидит там, уточнить criteria;
- сделать stronger distinction between concept-first vs self-referential concept queries.

## 11.3 `route_resolver.py`
- убедиться, что route selection не наследует ложную informational bias косвенно.

## 11.4 `output_validator.py`
- логика underfilled detection уже есть; проверить, что runtime использует её полностью;
- при необходимости улучшить diagnostics in warning/errors for auditability.

---

# 12. Testing Strategy

## 12.1 Main test intent
Эта итерация должна доказать:

**exploratory curiosity no longer collapses into false informational behavior**

## 12.2 Required test layers
Обязательны:
- unit
- integration
- regression
- golden
- e2e
- runtime log verification

## 12.3 New required tests

### Curiosity decoupling
- `tests/unit/test_curious_no_longer_maps_to_informational_override.py`
- `tests/regression/test_curious_does_not_force_informational_mode.py`

### Inform narrowing
- `tests/unit/test_true_inform_still_routes_to_inform.py`
- `tests/golden/test_self_referential_concept_query_not_pure_inform.py`
- `tests/golden/test_how_to_start_practice_not_pure_inform.py`

### Validator wiring
- `tests/unit/test_query_is_passed_to_output_validation_policy.py`
- `tests/integration/test_underfilled_inform_validator_uses_query_context.py`

### SD passive metadata safety
- `tests/regression/test_chunk_level_sd_metadata_does_not_control_runtime_behavior.py`
- `tests/regression/test_legacy_sd_chunk_labels_do_not_break_retrieval.py`

## 12.4 Negative tests
Обязательны:
- pure dictionary-style query still allowed to be `inform`;
- exploratory concept query no longer gets dry informational collapse;
- chunk with `GREEN` metadata does not auto-shift route;
- old sessions with SD values still do not break runtime;
- validator still allows short safe responses where appropriate.

---

# 13. Acceptance Criteria

## 13.1 Decoupling accepted only if
- `curious` no longer auto-activates informational mode;
- `MODE_PROMPT_MAP` no longer acts as behavioral trap;
- exploratory queries no longer default to `inform` without strong reason.

## 13.2 Inform narrowing accepted only if
- pure concept queries still behave correctly;
- self-referential concept queries stop collapsing into dry inform;
- practical-entry queries stop behaving like glossary prompts.

## 13.3 Validator wiring accepted only if
- query-aware anti-sparse checks truly execute in runtime;
- underfilled informational answers are now catchable in live path.

## 13.4 SD clarification accepted only if
- chunk-level SD metadata may remain;
- but runtime behavior no longer depends on SD as active signal;
- no false belief remains that passive chunk metadata must be purged immediately.

## 13.5 Whole 10.3.1 accepted only if
- user-perceived scarcity noticeably decreases further;
- no route explosion is introduced;
- no retrieval degradation appears;
- logs confirm fewer false `route=inform` cases on exploratory prompts.

---

# 14. Delivery Plan

## Phase 0 — Decoupling Baseline
- capture current false-inform examples
- capture current route / informational_mode / validator wiring
- identify exact runtime points of mode derivation

## Phase 1 — Curious/Inform Decoupling
- remove `curious -> informational` mapping
- rebuild `informational_mode` derivation
- update debug metadata

## Phase 2 — Validator Wiring Fix
- pass `query` into output validation
- ensure regular and fast path both comply
- ensure retry path preserves query context

## Phase 3 — Inform Narrowing Tests
- add unit/golden/regression coverage
- verify practical/self-referential queries stop collapsing

## Phase 4 — Runtime Verification
- replay representative live scenarios
- compare before/after logs
- verify fewer false `route=inform` outcomes

---

# 15. Risk Management

## 15.1 Main risk
Можно слишком сильно сузить `inform` и потерять хорошие explanatory answers.

### Mitigation
- keep pure concept queries working;
- do not destroy informational branch;
- recalibrate, do not disable.

## 15.2 Secondary risk
Можно случайно начать удалять chunk-level SD metadata, хотя она уже не является runtime controller.

### Mitigation
- explicitly separate passive metadata from active runtime influence;
- do not perform unnecessary data purge in 10.3.1.

## 15.3 Validator risk
Если anti-sparse wiring починить грубо, можно получить лишние regeneration cycles.

### Mitigation
- only trigger where query truly demands richness;
- preserve short-answer exemptions.

---

# 16. Definition of Done

PRD_10.3.1 считается выполненным только если одновременно верно всё:

1. `curious` больше не маппится автоматически в informational override.  
2. `informational_mode` больше не выводится из одного `mode_prompt_override`.  
3. Exploratory/self-referential/practical queries реже уходят в false `inform`.  
4. Pure concept questions по-прежнему могут идти в `inform`.  
5. `query` реально передаётся в output validation.  
6. Anti-sparse validator реально работает в live runtime.  
7. Chunk-level SD metadata может оставаться пассивно без влияния на runtime.  
8. Live logs показывают меньше ложных `route=inform` на exploratory inputs.  
9. Пользовательская “скупость” заметно уменьшается.  

---

# 17. Instructions to IDE Agent

1. Не превращай 10.3.1 в новую большую миграцию.  
2. Работай как инженер точечной коррекции root cause.  
3. Главный приоритет — decouple curiosity from informational collapse.  
4. Не путай passive chunk metadata с active runtime behavior.  
5. Не ломай good informational answers ради борьбы с false informationality.  
6. После каждой фазы:
   - обнови код;
   - обнови tests;
   - сохрани before/after logs;
   - проверь, что route behavior действительно изменился.

---

# 18. Final Note

PRD_10.3.1 intentionally focuses on one surgical truth:

**Проблема уже не в том, что бот “не умеет быть живым”.  
Проблема в том, что runtime всё ещё слишком легко решает быть informational там, где надо быть живо-исследовательским.**

Эта итерация должна убрать именно эту ложную развилку — аккуратно, доказуемо и без лишней перестройки системы.
