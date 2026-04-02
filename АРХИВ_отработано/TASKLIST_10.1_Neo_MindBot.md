# TASKLIST_10.1_Neo_MindBot

## Назначение
Этот документ — рабочий инженерный чеклист для IDE-агента, который внедряет PRD_10.1 Neo MindBot по фазам.

Главное правило:
**не переходить к следующей фазе, пока текущая не завершена, её контракты не зафиксированы, а тесты не зелёные.**

---

# 0. Глобальные правила выполнения

## Правило 1. Работа строго по фазам
Выполнять только последовательно:

- Phase 0
- Phase 1
- Phase 2
- Phase 3
- Phase 4
- Phase 5
- Phase 6
- Phase 7
- Phase 8
- Phase 9
- Phase 10

Запрещено:
- перескакивать через фазы;
- параллельно смешивать крупные архитектурные изменения из разных фаз;
- делать один гигантский рефакторинг вместо пошаговой миграции.

## Правило 2. Stop-the-line
Если хотя бы один обязательный тест фазы красный:
- остановиться;
- найти причину;
- исправить код;
- повторно прогнать тесты;
- не переходить к следующей фазе.

## Правило 3. Сначала безопаснее и проще
При любой неопределённости выбирать:
- более безопасную реализацию;
- более детерминированную реализацию;
- более тестируемую реализацию;
- менее “магическую” реализацию.

## Правило 4. Никаких скрытых хвостов legacy-логики
Не оставлять в live runtime:
- SD runtime dependency;
- SD retrieval filter;
- user_level_adapter;
- multi-gate routing;
- старые prompt overlays;
- неявные fallback-ветки, конфликтующие с новой логикой.

## Правило 5. После каждой фазы обязателен набор артефактов
После завершения каждой фазы агент обязан:
- обновить код;
- добавить или обновить тесты;
- обновить контракты / схемы / документацию;
- сделать отдельный коммит.

---

# 1. PHASE 0 — Baseline and Safety Net

## Цель
Подготовить проект к миграции без потери управляемости и без скрытых регрессий.

## Сделать
- Зафиксировать текущий pipeline entrypoint(s).
- Составить карту зависимостей текущего runtime.
- Найти все места использования:
  - `sd_classifier`
  - `sd_level`
  - `user_level_adapter`
  - старых decision gate стадий
  - prompt overlays
  - legacy memory assumptions
- Добавить feature flags:
  - `NEO_MINDBOT_ENABLED`
  - `LEGACY_PIPELINE_ENABLED`
  - `DISABLE_SD_RUNTIME`
  - `DISABLE_USER_LEVEL_ADAPTER`
  - `USE_NEW_DIAGNOSTICS_V1`
  - `USE_DETERMINISTIC_ROUTE_RESOLVER`
- Зафиксировать baseline fixtures для текущего поведения.

## Проверить
- Приложение поднимается.
- Legacy pipeline работает как раньше при выключенном новом флаге.
- Smoke tests проходят.

## Тесты
- `tests/smoke/test_app_boot.py`
- `tests/smoke/test_pipeline_entrypoints.py`
- `tests/inventory/test_legacy_runtime_map.py`
- `tests/config/test_feature_flags_baseline.py`

## Acceptance Criteria
- Карта legacy-зависимостей собрана.
- Feature flags добавлены.
- Базовые smoke tests зелёные.
- Есть baseline fixtures для regression comparison.

---

# 2. PHASE 1 — Remove SD Runtime Dependency

## Цель
Полностью убрать SD из online runtime-маршрутизации.

## Сделать
- Выключить `sd_classifier` из runtime под флагом.
- Удалить обязательные зависимости downstream-модулей от SD-результата.
- Убедиться, что response flow не требует `sd_result.primary`.
- Сохранить SD-поля только как пассивные legacy-данные, если они есть в storage.

## Проверить
- На каждом live-turn больше не происходит SD-LLM вызов.
- Pipeline не падает, если SD отсутствует полностью.
- Ответы не зависят от SD.

## Тесты
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_no_sd_required_by_response_flow.py`

## Negative Tests
- отсутствие SD-поля в старом объекте состояния;
- старый сериализованный контекст с SD-данными и без них;
- включён legacy fallback, но SD выключен.

## Acceptance Criteria
- SD не участвует в runtime.
- Нет падений из-за отсутствия SD.
- Legacy данные не ломают новый контур.

---

# 3. PHASE 2 — Remove SD Retrieval Filtering

## Цель
Открыть retrieval для всей БД без фильтрации по уровню пользователя.

## Сделать
- Убрать `sd_level` из retrieval contract.
- Удалить все SD-фильтры из query builder и retrieval path.
- Убедиться, что rerank preparation не требует SD.
- Обновить типы / интерфейсы retrieval-модуля.

## Проверить
- Retrieval не принимает SD runtime-параметры.
- Доступен весь corpus.
- Нет скрытых фильтров в промежуточных слоях.

## Тесты
- `tests/unit/test_retriever_no_sd_filter.py`
- `tests/integration/test_full_knowledge_access.py`
- `tests/regression/test_no_hidden_sd_filtering.py`
- `tests/contract/test_retrieval_contract_v101.py`

## Negative Tests
- retrieval с legacy SD-аргументом должен либо игнорироваться безопасно, либо валидно отклоняться;
- пустой retrieval response;
- шумный retrieval response.

## Acceptance Criteria
- `sd_level` убран из runtime retrieval flow.
- Полный доступ к knowledge base подтверждён тестами.
- Retrieval не ломается в degraded mode.

---

# 4. PHASE 3 — Remove UserLevelAdapter

## Цель
Убрать beginner/intermediate/advanced из active pipeline.

## Сделать
- Удалить `user_level_adapter` из активного response flow.
- Очистить prompt assembly от level-based инструкций.
- Удалить post-retrieval level filtering.
- Обновить downstream-модули, чтобы они не ожидали user level.

## Проверить
- Ответы больше не зависят от level classification.
- Prompt stack не содержит старых level overlays.
- Response generator принимает блоки без level adaptation.

## Тесты
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/integration/test_pipeline_without_level_adapter.py`
- `tests/regression/test_no_level_based_prompting.py`

## Negative Tests
- старые объекты с полем `user_level`;
- legacy конфиг с включённым level adapter;
- старый prompt fragment, содержащий level-policy.

## Acceptance Criteria
- UserLevelAdapter отсутствует в live runtime.
- Старые level assumptions не влияют на ответы.
- Prompt assembly очищен.

---

# 5. PHASE 4 — Diagnostics v1 + Deterministic RouteResolver

## Цель
Ввести новую обязательную диагностику и заменить LLM-routing на детерминированный resolver.

## Сделать
- Создать `diagnostics_classifier.py`.
- Реализовать runtime contract с обязательными полями:
  - `interaction_mode`
  - `nervous_system_state`
  - `request_function`
  - `core_theme`
- Реализовать optional enrichment как необязательный блок.
- Добавить confidence-поля.
- Реализовать fallback defaults:
  - `coaching`
  - `window`
  - `understand`
  - `unspecified_current_issue`
- Создать `route_resolver.py`.
- Удалить multi-gate routing.
- Зафиксировать route taxonomy:
  - `safe_override`
  - `regulate`
  - `reflect`
  - `practice`
  - `inform`
  - `contact_hold`

## Проверить
- Один turn → один diagnostics output → один route.
- Route не требует отдельного LLM DecisionGate.
- Optional fields не обязательны для runtime.

## Тесты
- `tests/unit/test_diagnostics_required_fields.py`
- `tests/unit/test_diagnostics_confidence_policy.py`
- `tests/unit/test_route_resolver_rules.py`
- `tests/contract/test_diagnostics_schema_v101.py`
- `tests/golden/test_diagnostics_examples.py`
- `tests/integration/test_single_route_per_turn.py`

## Golden Cases
- panic / urgency → `hyper`
- reflective structured inquiry → `window`
- emptiness / apathy → `hypo`
- pure concept explanation → `informational`
- mixed personal + explanatory query → coaching with bridge or inform with bridge
- explicit contact-only request → `contact_hold`

## Negative Tests
- битый JSON от classifier;
- отсутствует одно обязательное поле;
- низкий confidence на mode/state/function;
- конфликтующие сигналы (`hyper` + informational phrasing);
- мусорный `core_theme`.

## Acceptance Criteria
- Diagnostics v1 стабилен.
- RouteResolver детерминирован.
- LLM DecisionGate не нужен.
- Golden tests зелёные.

---

# 6. PHASE 5 — Memory v1.1

## Цель
Внедрить memory-контракт с fallback chain и schema validation.

## Сделать
- Создать snapshot schema v1.1.
- Реализовать `memory_updater.py`.
- Реализовать `summary_manager.py`.
- Ввести `schema_version` и validation.
- Реализовать `dialog_cache`.
- Реализовать summary staleness states:
  - `fresh`
  - `stale`
  - `missing`
- Реализовать fallback chain:
  - fresh summary → summary + small snapshot subset
  - stale summary → summary + larger recent window
  - missing summary → snapshot + recent window
  - corrupted snapshot → ignore broken fields + use recent dialog
- Ограничить размер injected memory context.

## Проверить
- Runtime не зависит от наличия summary.
- Битая память не валит pipeline.
- Межсессионная continuity работает.

## Тесты
- `tests/unit/test_snapshot_schema_v11.py`
- `tests/unit/test_memory_fallback_chain.py`
- `tests/unit/test_summary_staleness_policy.py`
- `tests/contract/test_memory_contract_v11.py`
- `tests/integration/test_context_continuity_between_sessions.py`
- `tests/regression/test_memory_does_not_require_full_raw_history.py`

## Negative Tests
- missing summary;
- stale summary;
- corrupted snapshot;
- unsupported schema version;
- oversized summary;
- conflicting summary vs recent messages.

## Acceptance Criteria
- Memory v1.1 валидируется.
- Есть рабочий fallback chain.
- Continuity есть, псевдопрофилирования нет.

---

# 7. PHASE 6 — Prompt Stack v2 + Output Validation

## Цель
Собрать новый prompt stack и отделить generation от validation.

## Сделать
- Создать prompt registry.
- Зафиксировать порядок:
  - `AA_SAFETY`
  - `A_STYLE_POLICY`
  - `CORE_IDENTITY`
  - `CONTEXT_MEMORY`
  - `DIAGNOSTIC_CONTEXT`
  - `RETRIEVED_CONTEXT`
  - `TASK_INSTRUCTION`
- Удалить legacy prompt overlays.
- Сделать `A_STYLE_POLICY` адаптивным:
  - `inform` → допустим neutral style
  - `hypo` → minimal / neutral or winter_soft
  - `safe_override` → no poetics
- Создать `output_validator.py`.
- Реализовать validator checks:
  - safety consistency
  - route consistency
  - mode consistency
  - formatting validity
  - no broken HTML
  - no forbidden directive advice
  - no hallucinated certainty
- Реализовать invalid output policy:
  - local repair
  - regenerate once
  - safe fallback

## Проверить
- Prompt stack версионируется.
- Нет конфликтующих инструкций.
- Validator реально блокирует невалидный output.

## Тесты
- `tests/unit/test_prompt_stack_order.py`
- `tests/unit/test_prompt_registry_versioning.py`
- `tests/unit/test_output_validator_rules.py`
- `tests/contract/test_prompt_stack_contract_v2.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/regression/test_no_legacy_prompt_overlays.py`

## Negative Tests
- broken HTML output;
- markdown leakage;
- unsafe directive answer;
- пустой ответ;
- overly long answer;
- response inconsistent with `inform` route;
- response over-aestheticized in `safe_override`.

## Acceptance Criteria
- Prompt stack v2 собран.
- Output validation отделён.
- Adaptive style policy работает по route/state.

---

# 8. PHASE 7 — Practice Engine v1

## Цель
Вынести подбор практик в отдельный детерминированный механизм.

## Сделать
- Создать `practice_schema.py`.
- Создать `practices_db.json`.
- Реализовать `practice_selector.py`.
- Ввести минимальную схему:
  - id
  - title
  - channel
  - scientific_basis
  - triggers
  - nervous_system_states
  - request_functions
  - core_themes
  - instruction
  - micro_tuning
  - closure
  - time_limit_minutes
  - contraindications
- Реализовать selection filters:
  1. safety / contraindications
  2. state match
  3. route relevance
  4. request_function
  5. recent channel history
- Реализовать scoring.
- Реализовать rotation policy:
  - не повторять `last_practice_channel`, если есть равнозначная альтернатива.
- Реализовать alternative offer policy:
  - не более 2 альтернатив.

## Проверить
- Выбор объясним и воспроизводим.
- Практика не выбирается “по вдохновению”.
- Hyper/hypo/window ведут к разным типам интервенции.

## Тесты
- `tests/unit/test_practice_schema_v1.py`
- `tests/unit/test_practice_selector_filters.py`
- `tests/unit/test_practice_channel_rotation.py`
- `tests/golden/test_practice_selection_scenarios.py`
- `tests/integration/test_practice_selection_in_pipeline.py`

## Golden Cases
- `hyper + discharge` → body
- `hypo + contact` → body or very soft action
- `window + understand` → thinking or action
- `window + explore + last_channel=body` → non-body if valid alternative exists
- user asks for alternative → max 2 alternatives

## Negative Tests
- contraindicated practice;
- empty practice library;
- malformed practice entry;
- only same-channel candidates remain;
- track info missing.

## Acceptance Criteria
- Practice engine работает детерминированно.
- Rotation policy соблюдается.
- Альтернативы ограничены и осмысленны.

---

# 9. PHASE 8 — Informational Branch + Onboarding

## Цель
Добавить ограниченную informational ветку и корректный first-session flow.

## Сделать
- Реализовать informational branch как ограниченную ветку, не ломающую coaching-first модель.
- Добавить mixed-query handling:
  - короткое объяснение + мягкий мост в coaching при уместности.
- Реализовать `/start`.
- Реализовать first-turn handling.
- Реализовать `UserCorrectionProtocol`:
  - признать промах
  - снизить уверенность
  - перекалиброваться
- Проверить, что informational branch:
  - не запускает полную reflective method без причины;
  - не навязывает практики;
  - не притворяется психотерапией.

## Проверить
- Новый пользователь не получает бюрократический intake.
- Informational ответы остаются в своих границах.
- Mixed queries обрабатываются мягко.

## Тесты
- `tests/integration/test_onboarding_first_session.py`
- `tests/integration/test_informational_branch.py`
- `tests/integration/test_mixed_query_bridge.py`
- `tests/golden/test_user_correction_protocol.py`
- `tests/regression/test_informational_branch_does_not_force_coaching.py`

## Negative Tests
- purely informational request in middle of coaching context;
- personal disclosure hidden inside informational wording;
- user says “нет, не то” after first interpretation;
- `/start` without follow-up message.

## Acceptance Criteria
- Onboarding не давит.
- Informational branch ограничен и полезен.
- User correction работает без конфликта.

---

# 10. PHASE 9 — Observability + Failure Hardening

## Цель
Сделать систему наблюдаемой и устойчивой к частичным сбоям.

## Сделать
- Реализовать turn trace:
  - safety flags
  - diagnostics result
  - route
  - retrieval stats
  - selected practice
  - validation result
  - memory update result
- Добавить LLM trace:
  - prompt version
  - model
  - elapsed
  - parse success
  - fallback used
- Реализовать degraded modes:
  - retrieval failure
  - summary missing/stale
  - partial subsystem outage
  - admin misconfiguration rollback
- Реализовать config validation at startup.
- Реализовать rollback to last valid admin-edited config/prompt.

## Проверить
- Система не падает при частичных сбоях.
- Trace показывает, что произошло.
- Невалидный admin config не ломает runtime silently.

## Тесты
- `tests/unit/test_trace_payload_schema.py`
- `tests/unit/test_config_validation.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/integration/test_admin_config_rollback.py`
- `tests/regression/test_partial_outage_does_not_crash_pipeline.py`

## Negative Tests
- retrieval timeout;
- malformed admin config;
- broken prompt block version;
- summary manager unavailable;
- practice DB unavailable.

## Acceptance Criteria
- Failure modes покрыты.
- Есть degraded mode.
- Trace полезен для дебага.

---

# 11. PHASE 10 — E2E Hardening and Cleanup

## Цель
Зафиксировать качество всей системы и убрать остаточные runtime-хвосты.

## Сделать
- Прогнать полный e2e pack.
- Удалить оставшийся dead runtime code.
- Оставить legacy только там, где он нужен для controlled fallback.
- Обновить архитектурную документацию.
- Обновить migration notes.
- Проверить rollback strategy.
- Подготовить release checklist.

## E2E Tests
- `tests/e2e/test_full_pipeline_hyper_case.py`
- `tests/e2e/test_full_pipeline_window_case.py`
- `tests/e2e/test_full_pipeline_hypo_case.py`
- `tests/e2e/test_safe_override_case.py`
- `tests/e2e/test_directive_relationship_boundary_case.py`
- `tests/e2e/test_informational_case.py`
- `tests/e2e/test_mixed_query_case.py`
- `tests/e2e/test_returning_user_stale_summary_case.py`
- `tests/e2e/test_user_correction_case.py`
- `tests/e2e/test_practice_alternative_case.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/e2e/test_legacy_fallback_when_flag_off.py`

## Final Acceptance
Система считается готовой только если одновременно:
- SD отсутствует в runtime;
- retrieval открыт;
- user level logic отсутствует;
- один route на turn;
- diagnostics v1 стабилен;
- memory fallback chain работает;
- prompt stack v2 активен;
- output validator отделён;
- informational branch не ломает coaching-first;
- safety override работает поверх modes;
- failure modes не валят pipeline;
- e2e пакет зелёный;
- документация обновлена.

---

# 12. Рекомендуемый формат коммитов

- `phase-0: add baseline safety net and feature flags`
- `phase-1: remove sd runtime dependency`
- `phase-2: remove sd retrieval filtering`
- `phase-3: remove user level adapter`
- `phase-4: add diagnostics v1 and deterministic route resolver`
- `phase-5: implement memory v1.1 with fallback chain`
- `phase-6: add prompt stack v2 and output validation`
- `phase-7: implement practice engine v1`
- `phase-8: add informational branch and onboarding`
- `phase-9: add observability and failure hardening`
- `phase-10: finalize e2e hardening and cleanup`

---

# 13. Definition of Done for IDE Agent

Работа считается завершённой только если:
- все phase acceptance criteria закрыты;
- все required tests зелёные;
- runtime contracts обновлены;
- legacy conflicts устранены;
- rollback paths сохранены;
- изменения готовы к коммиту и пушу.

---

# 14. Финальная инструкция IDE-агенту

Работай как инженер production-миграции, а не как генератор “красивого рефакторинга”.

Твоя задача:
- уменьшать хаос;
- повышать предсказуемость;
- делать систему безопаснее;
- делать систему проще для поддержки;
- не влюбляться в сложность там, где можно решить проще.

Neo MindBot v10.1 должен быть не самым абстрактно умным, а самым надёжно реализуемым.
