# TASKLIST_10.3_Response_Richness_Recalibration

## Назначение
Этот документ — пошаговый execution-чеклист для IDE-агента, который внедряет `PRD_10.3_Response_Richness_Recalibration.md`.

Главная цель итерации:
**не переписать архитектуру заново, а убрать поведенческую скупость ответов и вернуть Neo MindBot живость, полноту и смысловую щедрость без потери safety и route discipline.**

Главное правило:
**не переходить к следующей фазе, пока текущая не завершена, её тесты не зелёные, а representative ответы не стали богаче по смыслу, а не просто длиннее.**

---

# 0. Глобальные правила выполнения

## Правило 1. Это behavioral tuning iteration, а не новая архитектурная миграция
Запрещено раздувать scope:
- новыми крупными runtime-подсистемами;
- новой memory-архитектурой;
- новым большим routing tree;
- новыми admin-фичами;
- новой retrieval-философией.

## Правило 2. Работа строго по фазам
Выполнять только последовательно:

- Phase 0
- Phase 1
- Phase 2
- Phase 3
- Phase 4
- Phase 5

Не смешивать routing recalibration, prompt tuning и validator tuning в один хаотичный коммит.

## Правило 3. Stop-the-line
Если обязательные тесты или golden fixtures фазы падают:
- остановиться;
- исправить причину;
- повторить прогон;
- не идти дальше.

## Правило 4. Richness ≠ verbosity
Нельзя считать фазу успешной только потому, что ответы стали длиннее.
Успех = ответ стал:
- содержательнее,
- теплее,
- живее,
- полезнее,
- при этом не стал водянистым.

## Правило 5. Safety и route consistency сохраняются всегда
Нельзя улучшать richness ценой:
- unsafe directives;
- потери route clarity;
- чрезмерной поэтизации;
- broken informational discipline;
- размывания regulated/safe flows.

## Правило 6. Before/after examples обязательны
После ключевых фаз нужно фиксировать:
- representative inputs;
- old output sample;
- new output sample;
- краткое объяснение, в чём improvement.

---

# 1. PHASE 0 — Richness Baseline

## Цель
Зафиксировать текущие sparse-output паттерны и bottlenecks.

## Сделать
- Собрать набор representative user queries, на которых бот сейчас отвечает скупо.
- Зафиксировать:
  - output text,
  - selected route,
  - informational_mode,
  - applied_mode_prompt,
  - diagnostics result,
  - prompt stack sections,
  - output validation result.
- Выделить случаи:
  - pure informational
  - mixed informational + personal
  - first-turn exploratory
  - “how to start practicing”
  - “what is X and how it differs from Y”
- Проверить, в каких кейсах срабатывает `curious -> informational` связка.
- Проверить текущую `A_STYLE_POLICY` и `TASK_INSTRUCTION` для `inform`.

## Проверить
- Есть baseline fixtures.
- Есть список реальных sparse anti-patterns.
- Понятно, где richness режется: routing / style / first-turn / validator.

## Тесты
- `tests/inventory/test_sparse_output_fixture_inventory.py`
- `tests/inventory/test_informational_routing_baseline_map.py`
- `tests/inventory/test_prompt_richness_bottlenecks_map.py`

## Acceptance Criteria
- Сформирован baseline набор.
- Sparse behavior задокументирован.
- Есть контрольные запросы для before/after.

---

# 2. PHASE 1 — Informational Routing Recalibration

## Цель
Сузить случаи, когда бот уходит в informational-like behavior, и убрать жёсткую связку `curious -> informational dryness`.

## Сделать
- Пересмотреть `MODE_PROMPT_MAP`.
- Убрать или радикально ослабить:
  - `curious -> prompt_mode_informational`
- Проверить derivation:
  - `informational_mode`
  - `informational_mode_hint`
- Пересмотреть критерии, когда exploratory query считается truly informational.
- Mixed/exploratory queries смещать в:
  - richer mixed behavior
  - coaching-biased behavior
- Не вводить новый route enum без крайней необходимости.

## Проверить
- `curious` больше не означает почти автоматически informational override.
- `inform` route сузился до действительно concept-first запросов.
- Mixed queries перестали преждевременно сжиматься.

## Тесты
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_informational_mode_narrowing.py`
- `tests/golden/test_mixed_query_not_reduced_to_glossary.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`

## Negative Tests
- pure definition request still reaches `inform`;
- mixed self-referential query no longer collapses to dry `inform`;
- “how to start practicing” no longer behaves like glossary answer;
- query with personal framing does not silently stay in informational dryness.

## Acceptance Criteria
- `curious` больше не является shorthand для informational mode.
- `inform` route стал уже.
- exploratory richness не убивается routing stage.

---

# 3. PHASE 2 — Prompt Richness Recalibration

## Цель
Сделать `inform`, `mixed_query` и `first_turn` заметно богаче по стилю и смысловой массе.

## Сделать
- Переписать `A_STYLE_POLICY` для `inform`:
  - ясно
  - структурно
  - живо
  - 2-4 примера where useful
  - различия и нюансы
  - why-it-matters layer
- Добавить richer variants для:
  - `inform`
  - `first_turn_inform`
  - `first_turn_coaching`
  - `mixed_query`
- Переписать `TASK_INSTRUCTION`:
  - для `inform`: не glossary style
  - для difference questions: реально сравнивать
  - для mixed query: concept + relevance + practical lens
  - для first turn: не ужимать тело ответа до минимума
- Сохранить guardrails против лекционности и перегруза.

## Проверить
- Informational answer больше не выглядит как сухой FAQ snippet.
- Mixed query получает полноценную структуру ответа.
- First turn остаётся лёгким, но не бедным.

## Тесты
- `tests/unit/test_prompt_style_policy_inform_rich.py`
- `tests/unit/test_first_turn_instruction_softened.py`
- `tests/unit/test_mixed_query_instruction_enriched.py`
- `tests/golden/test_difference_question_has_real_comparison.py`
- `tests/golden/test_first_turn_not_underfilled.py`
- `tests/golden/test_informational_answer_not_sparse.py`

## Negative Tests
- informational answer too poetic;
- first-turn answer too long and lecture-like;
- mixed query answer loses structure;
- route says inform but answer drifts into full coaching session.

## Acceptance Criteria
- Prompt stack explicitly supports richness.
- Inform/mixed/first-turn ответы стали богаче без расползания.
- Сохраняется ясность и структура.

---

# 4. PHASE 3 — Output Validation Enrichment

## Цель
Добавить защиту от смысловой скупости как новой ошибки output quality.

## Сделать
- Добавить anti-sparse checks в `output_validator`.
- Ввести понятие underfilled answer:
  - definition + 1 generic sentence + 1 bridge question
  - нет сравнения, хотя asked for difference
  - нет примеров, хотя нужен explanatory richness
  - слишком бедный informational answer при хорошем retrieval
- Добавить regenerate hints для cases:
  - enrich comparison
  - add examples
  - deepen concept explanation
  - connect concept to user framing
- Не превращать validator в forcing-longness mechanism.

## Проверить
- Validator ловит реально бедные ответы.
- Validator не ломает уместную краткость в:
  - safe_override
  - regulate
  - hypo-sensitive cases
  - explicit short-answer preference

## Тесты
- `tests/unit/test_output_validator_anti_sparse_rules.py`
- `tests/unit/test_output_validator_allows_appropriate_brevity.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/golden/test_inform_answer_not_definition_plus_bridge_only.py`

## Negative Tests
- short safe_override should pass;
- short regulate answer should pass;
- long but empty answer should still fail richness check;
- rich but concise answer should pass.

## Acceptance Criteria
- Anti-sparse validation работает.
- Regeneration hint улучшает смысловую полноту.
- Нет тупого принуждения к длинным ответам.

---

# 5. PHASE 4 — Golden / Qualitative Test Hardening

## Цель
Зафиксировать качество richer behavior не только кодом, но и качественными rubric-based тестами.

## Сделать
- Собрать golden fixtures по ключевым сценариям:
  1. what is X and how is it different from Y
  2. seems this is about me
  3. how to start practicing this
  4. first-turn exploratory request
  5. mixed query: concept + self-application
- Для каждого кейса описать rubric:
  - explanation depth
  - comparison present
  - examples present where needed
  - practical relevance
  - tone not flat
  - not over-verbose
- Сохранить before/after samples.

## Проверить
- Есть формализованная оценка richer answers.
- Улучшения видны не только по длине.
- Safety и structure не деградировали.

## Тесты
- `tests/golden/test_richness_rubric_inform_case.py`
- `tests/golden/test_richness_rubric_mixed_case.py`
- `tests/golden/test_richness_rubric_first_turn_case.py`
- `tests/golden/test_practice_entry_not_glossary_like.py`
- `tests/regression/test_richness_changes_do_not_break_safe_routes.py`

## Acceptance Criteria
- Golden fixtures зафиксированы.
- Rubric tests отражают реальную задачу 10.3.
- Есть внятное before/after доказательство improvement.

---

# 6. PHASE 5 — Runtime Verification

## Цель
Проверить, что richer behavior проявляется в реальном runtime, а не только в тестовых фикстурах.

## Сделать
- Прогнать representative реальные сценарии:
  1. “Привет! Я хочу понять, что такое самоосознание и чем оно отличается от самонаблюдения”
  2. “Кажется, это про меня. Как это увидеть у себя?”
  3. “А как начать это практиковать?”
  4. “Объясни, что такое избегание”
  5. “Объясни, что такое избегание, потому что кажется это про меня”
- Сохранить:
  - route
  - informational_mode
  - applied_mode_prompt
  - output_validation meta
  - final answer text
- Сравнить с baseline.
- Обновить runtime docs / tuning notes.

## E2E Tests
- `tests/e2e/test_informational_richness_runtime.py`
- `tests/e2e/test_mixed_query_richness_runtime.py`
- `tests/e2e/test_first_turn_richness_runtime.py`
- `tests/e2e/test_practice_start_richness_runtime.py`
- `tests/e2e/test_richness_does_not_break_safety_runtime.py`

## Log Verification
После фазы проверить:
- informational_mode не срабатывает слишком широко;
- route=inform больше не даёт сухой мини-ответ по умолчанию;
- first-turn outputs не выглядят недоданными;
- validator/regen не уводят ответы в пустое многословие.

## Final Acceptance Criteria
Одновременно должно быть верно всё:
- `curious` больше не схлопывает richness;
- informational route стал уже и качественнее;
- mixed query ответы богаче;
- first-turn ответы не скупые;
- anti-sparse validation работает;
- safety и route consistency не деградировали;
- user-perceived scarcity materially reduced.

---

# 7. Рекомендуемый формат коммитов

- `phase-0: add sparse-output baseline fixtures and routing inventory`
- `phase-1: recalibrate informational routing and curious handling`
- `phase-2: enrich prompt style for inform mixed and first-turn cases`
- `phase-3: add anti-sparse output validation`
- `phase-4: add richness rubric golden tests`
- `phase-5: verify runtime richness and finalize tuning docs`

---

# 8. Definition of Done for IDE Agent

Работа по PRD_10.3 считается завершённой только если:
- все phase acceptance criteria закрыты;
- golden/qualitative tests зелёные;
- representative answers стали содержательнее, а не просто длиннее;
- safety не деградировал;
- route discipline сохранён;
- user-perceived scarcity visibly reduced.

---

# 9. Финальная инструкция IDE-агенту

Работай как инженер behavioral calibration.

Твоя задача в этой итерации:
- не сделать бота болтливее;
- а сделать его менее скупым на смысл.

Neo MindBot после 10.3 должен отвечать так, чтобы пользователь чувствовал:
его не только поняли,
но и действительно помогли развернуть тему достаточно полно, живо и бережно.
