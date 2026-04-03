# TASKLIST_10.3.1_Curious_Inform_Decoupling_PROGRESS

## Статус фаз

- [x] Phase 0 — Baseline decoupling audit
- [x] Phase 1 — Curious/Inform decoupling
- [x] Phase 2 — Validator wiring check
- [x] Phase 3 — Inform narrowing tests
- [x] Phase 4 — Runtime verification notes

## Детализация задач

### Phase 0 — Baseline decoupling audit
- [x] Зафиксировать текущие точки связки `curious -> inform` в runtime
- [x] Проверить derivation `informational_mode` в обычном и fast path
- [x] Проверить, что `query` пробрасывается в output validation во всех путях

### Phase 1 — Curious/Inform decoupling
- [x] Убрать/сузить эвристики, из-за которых exploratory-запросы ложно попадают в informational
- [x] Развести concept-first и self/practice/mixed случаи в классификаторе
- [x] Сохранить корректную обработку чисто информационных запросов

### Phase 2 — Validator wiring check
- [x] Добавить автотест на проброс `query` в `_apply_output_validation_policy`
- [x] Добавить интеграционный тест на query-aware anti-sparse поведение

### Phase 3 — Inform narrowing tests
- [x] Добавить тесты на отсутствие false `inform` для self-referential/practice-entry запросов
- [x] Добавить тесты на сохранение `inform` для чисто концептуальных запросов
- [x] Прогнать целевой набор unit/integration/regression тестов

### Phase 4 — Runtime verification notes
- [x] Сверить поведение с PRD 10.3.1 criteria
- [x] Обновить статусы фаз в этом файле

## Что изменено в коде

- `bot_psychologist/bot_agent/onboarding_flow.py`
  - Сужены сигналы informational intent.
  - Убраны слишком широкие маркеры (`расскажи`, `система`).
  - Добавлен учёт practice-intent в `mixed_query`.
- `bot_psychologist/bot_agent/diagnostics_classifier.py`
  - Сужен regex для informational-классификации.
  - Усилен акцент на definition/comparison-паттерны.
- `bot_psychologist/bot_agent/answer_adaptive.py`
  - Уточнён комментарий/лог fast-path для informational route.
- Добавлены тесты:
  - `bot_psychologist/tests/unit/test_phase8_informational_intent_narrowing_v1031.py`
  - `bot_psychologist/tests/unit/test_diagnostics_informational_decoupling_v1031.py`
  - `bot_psychologist/tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
  - `bot_psychologist/tests/integration/test_runtime_validation_receives_query_v1031.py`
  - `bot_psychologist/tests/integration/test_runtime_curious_inform_decoupling_v1031.py`

## Тесты

Команда:
`python -m pytest bot_psychologist/tests/unit/test_phase8_informational_intent_narrowing_v1031.py bot_psychologist/tests/unit/test_diagnostics_informational_decoupling_v1031.py bot_psychologist/tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py bot_psychologist/tests/unit/test_informational_mode_narrowing.py bot_psychologist/tests/integration/test_routing_recalibration_for_exploratory_queries.py bot_psychologist/tests/integration/test_sparse_output_triggers_regeneration_hint.py bot_psychologist/tests/integration/test_runtime_validation_receives_query_v1031.py bot_psychologist/tests/integration/test_runtime_curious_inform_decoupling_v1031.py -q`

Результат: `16 passed`.

## Runtime verification notes (Phase 4)

- Проверен runtime-кейс `Расскажи о системе нейросталкинга`:
  - `informational_mode=False`, `resolved_route!=inform`.
- Проверен runtime-кейс `Что такое нейросталкинг?`:
  - `informational_mode=True`, `resolved_route=inform`.
- Проверен runtime-кейс `Объясни ... и как начать это практиковать`:
  - `informational_mode=False`, `resolved_route!=inform`.
- Проверен проброс `query` в output validation на runtime-пути:
  - `query` стабильно передаётся в validator.
