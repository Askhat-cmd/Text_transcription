# TASKLIST_10.1_Neo_MindBot_PROGRESS

Дата: 2026-04-02

## Статус фаз
- [x] Phase 0 — Baseline and Safety Net
- [x] Phase 1 — Remove SD Runtime Dependency
- [x] Phase 2 — Remove SD Retrieval Filtering
- [x] Phase 3 — Remove UserLevelAdapter
- [x] Phase 4 — Diagnostics v1 + Deterministic RouteResolver
- [x] Phase 5 — Memory v1.1
- [x] Phase 6 — Prompt Stack v2 + Output Validation
- [x] Phase 7 — Practice Engine v1
- [x] Phase 8 — Informational Branch + Onboarding
- [x] Phase 9 — Observability + Failure Hardening
- [ ] Phase 10 — E2E Hardening and Cleanup

## Phase 0 — Baseline and Safety Net
### Done
- Добавлены migration feature flags: `NEO_MINDBOT_ENABLED`, `LEGACY_PIPELINE_ENABLED`, `DISABLE_SD_RUNTIME`, `DISABLE_USER_LEVEL_ADAPTER`, `USE_NEW_DIAGNOSTICS_V1`, `USE_DETERMINISTIC_ROUTE_RESOLVER`.
- Зафиксирована карта legacy runtime зависимостей и entrypoint’ов.
- Добавлены smoke/inventory/config тесты для baseline.

### Files changed
- `bot_psychologist/bot_agent/feature_flags.py`
- `bot_psychologist/.env.example`
- `bot_psychologist/tests/fixtures/legacy_runtime_map.json`
- `bot_psychologist/docs/legacy_runtime_map.md`
- `bot_psychologist/tests/smoke/test_app_boot.py`
- `bot_psychologist/tests/smoke/test_pipeline_entrypoints.py`
- `bot_psychologist/tests/inventory/test_legacy_runtime_map.py`
- `bot_psychologist/tests/config/test_feature_flags_baseline.py`

### Tests run
- `python -m pytest bot_psychologist/tests/smoke/test_app_boot.py bot_psychologist/tests/smoke/test_pipeline_entrypoints.py bot_psychologist/tests/inventory/test_legacy_runtime_map.py bot_psychologist/tests/config/test_feature_flags_baseline.py -v`
- Result: passed.

## Phase 1 — Remove SD Runtime Dependency
### Done
- SD runtime вызов отключается флагом `DISABLE_SD_RUNTIME` в adaptive pipeline.
- В streaming ветке API добавлено аналогичное отключение SD runtime.
- Для отключенного SD используется fallback `disabled_by_flag` без падения пайплайна.

### Files changed
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/api/routes.py`
- `bot_psychologist/tests/unit/test_sd_runtime_disabled.py`
- `bot_psychologist/tests/integration/test_pipeline_without_sd.py`
- `bot_psychologist/tests/regression/test_no_sd_required_by_response_flow.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_sd_runtime_disabled.py bot_psychologist/tests/integration/test_pipeline_without_sd.py bot_psychologist/tests/regression/test_no_sd_required_by_response_flow.py -v`
- Result: passed.

## Phase 2 — Remove SD Retrieval Filtering
### Done
- `sd_level` удален из runtime retrieval контракта для Bot_data_base API payload.
- Legacy `sd_level` безопасно игнорируется в `DBApiClient` и `SimpleRetriever`.
- Удален legacy retry-path "повтор без SD-фильтра" как больше неактуальный.
- Обновлены существующие тесты fallback/retrieval под новый контракт.
- Добавлены unit/integration/regression/contract тесты для проверки отсутствия hidden SD filtering.

### Files changed
- `bot_psychologist/bot_agent/db_api_client.py`
- `bot_psychologist/bot_agent/retriever.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/tests/test_db_api_client.py`
- `bot_psychologist/tests/test_retriever_fallback.py`
- `bot_psychologist/tests/unit/test_retriever_no_sd_filter.py`
- `bot_psychologist/tests/integration/test_full_knowledge_access.py`
- `bot_psychologist/tests/regression/test_no_hidden_sd_filtering.py`
- `bot_psychologist/tests/contract/test_retrieval_contract_v101.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_retriever_no_sd_filter.py bot_psychologist/tests/integration/test_full_knowledge_access.py bot_psychologist/tests/regression/test_no_hidden_sd_filtering.py bot_psychologist/tests/contract/test_retrieval_contract_v101.py -v`
- `python -m pytest bot_psychologist/tests/test_db_api_client.py bot_psychologist/tests/test_retriever_fallback.py -v`
- Result: passed.

## Phase 3 — Remove UserLevelAdapter
### Done
- Удален `UserLevelAdapter` из активного adaptive runtime-пайплайна.
- В streaming adaptive-ветке API удалено создание `UserLevelAdapter`; в runtime передается `None`.
- Для path recommendation введен нейтральный уровень (`INTERMEDIATE`) через `_resolve_path_user_level`, независимо от входного `user_level`.
- Сохранена backward compatibility: поле `user_level` в API request/metadata остается, но не влияет на runtime-адаптацию.

### Files changed
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/api/routes.py`
- `bot_psychologist/tests/unit/test_user_level_adapter_removed.py`
- `bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py`
- `bot_psychologist/tests/regression/test_no_level_based_prompting.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_user_level_adapter_removed.py bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py bot_psychologist/tests/regression/test_no_level_based_prompting.py -v`
- `python -m pytest tests/test_path_builder.py tests/test_response_generator.py -v` (workdir: `bot_psychologist/`)
- Result: passed.

## Phase 4 — Diagnostics v1 + Deterministic RouteResolver
### Done
- Добавлен `diagnostics_classifier.py` с runtime-контрактом обязательных полей:
  - `interaction_mode`
  - `nervous_system_state`
  - `request_function`
  - `core_theme`
- Добавлена confidence policy + sanitize/default fallback для битых/частичных payload.
- Добавлен `route_resolver.py` с детерминированной route taxonomy:
  - `safe_override`, `regulate`, `reflect`, `practice`, `inform`, `contact_hold`
- Интеграция в adaptive pipeline под flags:
  - `USE_NEW_DIAGNOSTICS_V1`
  - `USE_DETERMINISTIC_ROUTE_RESOLVER`
- При включенных flags:
  - используется Diagnostics v1
  - применяется детерминированный resolver
  - fast-path отключен (один route на turn)
  - в trace/metadata добавлены `diagnostics_v1`, `resolved_route`, `route_resolution_count`.
- Исправлен runtime баг после Phase 3:
  - при `level_adapter=None` убран вызов `filter_blocks_by_level` для `None`.

### Files changed
- `bot_psychologist/bot_agent/diagnostics_classifier.py`
- `bot_psychologist/bot_agent/route_resolver.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/tests/unit/test_diagnostics_required_fields.py`
- `bot_psychologist/tests/unit/test_diagnostics_confidence_policy.py`
- `bot_psychologist/tests/unit/test_route_resolver_rules.py`
- `bot_psychologist/tests/contract/test_diagnostics_schema_v101.py`
- `bot_psychologist/tests/golden/test_diagnostics_examples.py`
- `bot_psychologist/tests/integration/test_single_route_per_turn.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_diagnostics_required_fields.py bot_psychologist/tests/unit/test_diagnostics_confidence_policy.py bot_psychologist/tests/unit/test_route_resolver_rules.py bot_psychologist/tests/contract/test_diagnostics_schema_v101.py bot_psychologist/tests/golden/test_diagnostics_examples.py bot_psychologist/tests/integration/test_single_route_per_turn.py -v`
- Result: passed.

## Phase 5 — Memory v1.1
### Done
- Добавлен модуль `memory_v11.py`:
  - snapshot schema `1.1`
  - snapshot validation
  - summary staleness policy (`fresh`, `stale`, `missing`)
  - fallback chain для контекста:
    - `fresh_summary_small_window`
    - `stale_summary_large_window`
    - `missing_summary_snapshot_plus_recent`
    - `corrupted_snapshot_recent_dialog`
- Добавлен `summary_manager.py` (normalization + staleness policy).
- Добавлен `memory_updater.py`:
  - сбор runtime context через Memory v1.1
  - сохранение `last_state_snapshot_v11` в metadata/memory.
- Интеграция в adaptive pipeline:
  - контекст строится через `memory_updater.build_runtime_context(...)`
  - в trace добавлены `memory_strategy`, `summary_staleness`
  - snapshot v1.1 сохраняется после выбора route.

### Files changed
- `bot_psychologist/bot_agent/memory_v11.py`
- `bot_psychologist/bot_agent/summary_manager.py`
- `bot_psychologist/bot_agent/memory_updater.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/tests/unit/test_snapshot_schema_v11.py`
- `bot_psychologist/tests/unit/test_memory_fallback_chain.py`
- `bot_psychologist/tests/unit/test_summary_staleness_policy.py`
- `bot_psychologist/tests/contract/test_memory_contract_v11.py`
- `bot_psychologist/tests/integration/test_context_continuity_between_sessions.py`
- `bot_psychologist/tests/regression/test_memory_does_not_require_full_raw_history.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_snapshot_schema_v11.py bot_psychologist/tests/unit/test_memory_fallback_chain.py bot_psychologist/tests/unit/test_summary_staleness_policy.py bot_psychologist/tests/contract/test_memory_contract_v11.py bot_psychologist/tests/integration/test_context_continuity_between_sessions.py bot_psychologist/tests/regression/test_memory_does_not_require_full_raw_history.py -v`
- `python -m pytest bot_psychologist/tests/unit/test_user_level_adapter_removed.py bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py bot_psychologist/tests/regression/test_no_level_based_prompting.py -v`
- Result: passed.

## Phase 6 — Prompt Stack v2 + Output Validation
### Done
- Добавлен `prompt_registry_v2.py` с фиксированным порядком prompt stack:
  - `AA_SAFETY`
  - `A_STYLE_POLICY`
  - `CORE_IDENTITY`
  - `CONTEXT_MEMORY`
  - `DIAGNOSTIC_CONTEXT`
  - `RETRIEVED_CONTEXT`
  - `TASK_INSTRUCTION`
- Добавлен `output_validator.py`:
  - правила валидации safety/route/mode/format;
  - local repair для markdown leakage + certainty softening;
  - policy: validate → retry once → safe fallback.
- Интеграция в adaptive runtime:
  - feature flags `USE_PROMPT_STACK_V2`, `USE_OUTPUT_VALIDATION`;
  - для Prompt Stack v2 добавлен `system_prompt_override` в `ResponseGenerator.generate(...)`;
  - в trace добавлены `prompt_stack_v2` и `output_validation`.
- Legacy SD prompt overlays в runtime обходятся при включенном Prompt Stack v2 (через system prompt override).

### Files changed
- `bot_psychologist/bot_agent/prompt_registry_v2.py`
- `bot_psychologist/bot_agent/output_validator.py`
- `bot_psychologist/bot_agent/response/response_generator.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/bot_agent/feature_flags.py`
- `bot_psychologist/.env.example`
- `bot_psychologist/tests/unit/test_prompt_stack_order.py`
- `bot_psychologist/tests/unit/test_prompt_registry_versioning.py`
- `bot_psychologist/tests/unit/test_output_validator_rules.py`
- `bot_psychologist/tests/contract/test_prompt_stack_contract_v2.py`
- `bot_psychologist/tests/integration/test_generation_validation_separation.py`
- `bot_psychologist/tests/regression/test_no_legacy_prompt_overlays.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_prompt_stack_order.py bot_psychologist/tests/unit/test_prompt_registry_versioning.py bot_psychologist/tests/unit/test_output_validator_rules.py bot_psychologist/tests/contract/test_prompt_stack_contract_v2.py bot_psychologist/tests/integration/test_generation_validation_separation.py bot_psychologist/tests/regression/test_no_legacy_prompt_overlays.py bot_psychologist/tests/test_response_generator.py -v`
- `python -m pytest bot_psychologist/tests/integration/test_single_route_per_turn.py bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py bot_psychologist/tests/regression/test_no_level_based_prompting.py -v`
- `python -m pytest bot_psychologist/tests/test_llm_payload_endpoint.py -v`
- Result: passed.

## Phase 7 — Practice Engine v1
### Done
- Добавлены схема и валидатор практик:
  - `practice_schema.py`
  - обязательные поля и строгая проверка malformed entry.
- Добавлена библиотека практик `practices_db.json` (детерминированный v1 seed набор).
- Добавлен `practice_selector.py`:
  - фильтры: safety/contraindications, state, route, request_function;
  - scoring по route/state/function/theme overlap;
  - rotation policy через `last_practice_channel`;
  - alternative policy (`max 2 alternatives`).
- Интеграция в adaptive pipeline:
  - после route resolution выбирается primary practice;
  - в state context добавляется `PRACTICE_SUGGESTION`;
  - в trace/metadata добавлены `selected_practice` и `practice_alternatives`;
  - в memory metadata обновляется `last_practice_channel`.

### Files changed
- `bot_psychologist/bot_agent/practice_schema.py`
- `bot_psychologist/bot_agent/practices_db.json`
- `bot_psychologist/bot_agent/practice_selector.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`

### Tests run
- `python -m pytest bot_psychologist/tests/unit/test_practice_schema_v1.py bot_psychologist/tests/unit/test_practice_selector_filters.py bot_psychologist/tests/unit/test_practice_channel_rotation.py bot_psychologist/tests/golden/test_practice_selection_scenarios.py bot_psychologist/tests/integration/test_practice_selection_in_pipeline.py bot_psychologist/tests/unit/test_prompt_stack_order.py bot_psychologist/tests/unit/test_prompt_registry_versioning.py bot_psychologist/tests/unit/test_output_validator_rules.py bot_psychologist/tests/contract/test_prompt_stack_contract_v2.py bot_psychologist/tests/integration/test_generation_validation_separation.py bot_psychologist/tests/regression/test_no_legacy_prompt_overlays.py -v`
- `python -m pytest bot_psychologist/tests/test_llm_payload_endpoint.py bot_psychologist/tests/integration/test_single_route_per_turn.py bot_psychologist/tests/regression/test_no_level_based_prompting.py -v`
- Result: passed.

## Phase 8 — Informational Branch + Onboarding
### Done
- Добавлен модуль `onboarding_flow.py` с детекцией сигналов:
  - `first_turn`
  - `start_command`
  - `user_correction`
  - `informational_intent`
  - `mixed_query`
- Добавлен runtime feature flag:
  - `INFORMATIONAL_BRANCH_ENABLED` (в `feature_flags.py` и `.env.example`).
- Интегрирован `/start` onboarding flow в `answer_adaptive.py`:
  - ранний безопасный ответ без запуска полной генерации;
  - запись turn в память.
- Интегрированы phase8-инструкции в prompt/runtime context:
  - `FIRST_TURN_POLICY`
  - `MIXED_QUERY_POLICY`
  - `USER_CORRECTION_PROTOCOL`
  - `INFORMATIONAL_GUARDRAIL`
- Расширен `prompt_registry_v2.py`:
  - новые флаги сборки `first_turn`, `mixed_query_bridge`, `user_correction_protocol`;
  - route-aware правила для `inform`.
- Реализована логика `UserCorrectionProtocol`:
  - при сигнале коррекции снижается confidence;
  - `request_function` переводится в `validation`.
- Исправлена логика practice selection:
  - для informational route практика не подмешивается (`selected_practice=None`), чтобы не ломать informational ветку.

### Files changed
- `bot_psychologist/bot_agent/onboarding_flow.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/bot_agent/prompt_registry_v2.py`
- `bot_psychologist/bot_agent/feature_flags.py`
- `bot_psychologist/.env.example`
- `bot_psychologist/tests/phase8_runtime_support.py`
- `bot_psychologist/tests/integration/test_onboarding_first_session.py`
- `bot_psychologist/tests/integration/test_informational_branch.py`
- `bot_psychologist/tests/integration/test_mixed_query_bridge.py`
- `bot_psychologist/tests/golden/test_user_correction_protocol.py`
- `bot_psychologist/tests/regression/test_informational_branch_does_not_force_coaching.py`

### Tests run
- `python -m pytest bot_psychologist/tests/integration/test_onboarding_first_session.py bot_psychologist/tests/integration/test_informational_branch.py bot_psychologist/tests/integration/test_mixed_query_bridge.py bot_psychologist/tests/golden/test_user_correction_protocol.py bot_psychologist/tests/regression/test_informational_branch_does_not_force_coaching.py -q`
- `python -m pytest bot_psychologist/tests/test_feature_flags.py bot_psychologist/tests/config/test_feature_flags_baseline.py bot_psychologist/tests/contract/test_prompt_stack_contract_v2.py bot_psychologist/tests/unit/test_prompt_stack_order.py -q`
- Result: passed.

## Phase 9 — Observability + Failure Hardening
### Done
- Добавлен `trace_schema.py`:
  - runtime-проверка структуры trace payload;
  - флаги `trace_schema_valid` и `trace_schema_errors`.
- Интегрирована проверка trace schema в `answer_adaptive.py` перед возвратом `debug_trace`.
- Добавлен `config_validation.py`:
  - валидация критичных runtime-параметров;
  - fail-fast через `assert_runtime_config(...)`.
- В `api/main.py` на startup добавлена проверка runtime config с логированием результата.
- В `answer_adaptive.py` добавлен degraded retrieval mode:
  - fallback при падении `get_retriever()` или retrieval вызова;
  - trace поле `retrieval_degraded_reason`.
- Реализован rollback admin overrides в `admin_routes.py`:
  - входящий payload валидируется;
  - критичные runtime-поля проверяются до сохранения;
  - при ошибке применяется rollback к последней валидной версии.
- Добавлен regression-контур для частичных сбоев:
  - падение retrieval не валит pipeline;
  - падение LLM subsystem возвращает controlled error/partial response.

### Files changed
- `bot_psychologist/bot_agent/trace_schema.py`
- `bot_psychologist/bot_agent/config_validation.py`
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/api/admin_routes.py`
- `bot_psychologist/api/main.py`
- `bot_psychologist/tests/unit/test_trace_payload_schema.py`
- `bot_psychologist/tests/unit/test_config_validation.py`
- `bot_psychologist/tests/integration/test_degraded_mode_without_retrieval.py`
- `bot_psychologist/tests/integration/test_admin_config_rollback.py`
- `bot_psychologist/tests/regression/test_partial_outage_does_not_crash_pipeline.py`

### Tests run
- `python -m pytest bot_psychologist/tests/integration/test_degraded_mode_without_retrieval.py bot_psychologist/tests/unit/test_trace_payload_schema.py bot_psychologist/tests/unit/test_config_validation.py -q`
- `python -m pytest bot_psychologist/tests/integration/test_admin_config_rollback.py bot_psychologist/tests/regression/test_partial_outage_does_not_crash_pipeline.py -q`
- `python -m pytest bot_psychologist/tests/integration/test_onboarding_first_session.py bot_psychologist/tests/integration/test_informational_branch.py bot_psychologist/tests/integration/test_mixed_query_bridge.py bot_psychologist/tests/golden/test_user_correction_protocol.py bot_psychologist/tests/regression/test_informational_branch_does_not_force_coaching.py bot_psychologist/tests/integration/test_degraded_mode_without_retrieval.py bot_psychologist/tests/unit/test_trace_payload_schema.py bot_psychologist/tests/unit/test_config_validation.py bot_psychologist/tests/integration/test_admin_config_rollback.py bot_psychologist/tests/regression/test_partial_outage_does_not_crash_pipeline.py -q`
- Result: passed.

## Phase 10 — E2E Hardening and Cleanup (in progress)
### Done so far
- Добавлен e2e smoke-pack из PRD:
  - `test_full_pipeline_hyper_case.py`
  - `test_full_pipeline_window_case.py`
  - `test_full_pipeline_hypo_case.py`
  - `test_safe_override_case.py`
  - `test_directive_relationship_boundary_case.py`
  - `test_informational_case.py`
  - `test_mixed_query_case.py`
  - `test_returning_user_stale_summary_case.py`
  - `test_user_correction_case.py`
  - `test_practice_alternative_case.py`
  - `test_degraded_retrieval_case.py`
  - `test_legacy_fallback_when_flag_off.py`
- Добавлен общий e2e runtime helper:
  - `tests/e2e/neo_e2e_support.py`.
- Расширен phase8 runtime helper:
  - `build_diagnostics(...)` теперь поддерживает `nervous_system_state` и отдельную confidence для state.

### Files changed
- `bot_psychologist/tests/e2e/neo_e2e_support.py`
- `bot_psychologist/tests/e2e/test_full_pipeline_hyper_case.py`
- `bot_psychologist/tests/e2e/test_full_pipeline_window_case.py`
- `bot_psychologist/tests/e2e/test_full_pipeline_hypo_case.py`
- `bot_psychologist/tests/e2e/test_safe_override_case.py`
- `bot_psychologist/tests/e2e/test_directive_relationship_boundary_case.py`
- `bot_psychologist/tests/e2e/test_informational_case.py`
- `bot_psychologist/tests/e2e/test_mixed_query_case.py`
- `bot_psychologist/tests/e2e/test_returning_user_stale_summary_case.py`
- `bot_psychologist/tests/e2e/test_user_correction_case.py`
- `bot_psychologist/tests/e2e/test_practice_alternative_case.py`
- `bot_psychologist/tests/e2e/test_degraded_retrieval_case.py`
- `bot_psychologist/tests/e2e/test_legacy_fallback_when_flag_off.py`
- `bot_psychologist/tests/phase8_runtime_support.py`

### Tests run
- `python -m pytest bot_psychologist/tests/e2e -v`
- `python -m pytest bot_psychologist/tests/integration/test_onboarding_first_session.py bot_psychologist/tests/integration/test_informational_branch.py bot_psychologist/tests/integration/test_mixed_query_bridge.py bot_psychologist/tests/golden/test_user_correction_protocol.py bot_psychologist/tests/regression/test_informational_branch_does_not_force_coaching.py bot_psychologist/tests/integration/test_degraded_mode_without_retrieval.py bot_psychologist/tests/unit/test_trace_payload_schema.py bot_psychologist/tests/unit/test_config_validation.py bot_psychologist/tests/integration/test_admin_config_rollback.py bot_psychologist/tests/regression/test_partial_outage_does_not_crash_pipeline.py bot_psychologist/tests/e2e/test_full_pipeline_hyper_case.py bot_psychologist/tests/e2e/test_full_pipeline_window_case.py bot_psychologist/tests/e2e/test_full_pipeline_hypo_case.py bot_psychologist/tests/e2e/test_safe_override_case.py bot_psychologist/tests/e2e/test_directive_relationship_boundary_case.py bot_psychologist/tests/e2e/test_informational_case.py bot_psychologist/tests/e2e/test_mixed_query_case.py bot_psychologist/tests/e2e/test_returning_user_stale_summary_case.py bot_psychologist/tests/e2e/test_user_correction_case.py bot_psychologist/tests/e2e/test_practice_alternative_case.py bot_psychologist/tests/e2e/test_degraded_retrieval_case.py bot_psychologist/tests/e2e/test_legacy_fallback_when_flag_off.py -q`
- Result: passed (26 tests).

## Сводный прогон (Phase 0-5; targeted)
```bash
python -m pytest \
  bot_psychologist/tests/smoke/test_app_boot.py \
  bot_psychologist/tests/smoke/test_pipeline_entrypoints.py \
  bot_psychologist/tests/inventory/test_legacy_runtime_map.py \
  bot_psychologist/tests/config/test_feature_flags_baseline.py \
  bot_psychologist/tests/unit/test_sd_runtime_disabled.py \
  bot_psychologist/tests/integration/test_pipeline_without_sd.py \
  bot_psychologist/tests/regression/test_no_sd_required_by_response_flow.py \
  bot_psychologist/tests/unit/test_retriever_no_sd_filter.py \
  bot_psychologist/tests/integration/test_full_knowledge_access.py \
  bot_psychologist/tests/regression/test_no_hidden_sd_filtering.py \
  bot_psychologist/tests/contract/test_retrieval_contract_v101.py \
  bot_psychologist/tests/unit/test_user_level_adapter_removed.py \
  bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py \
  bot_psychologist/tests/regression/test_no_level_based_prompting.py \
  bot_psychologist/tests/unit/test_diagnostics_required_fields.py \
  bot_psychologist/tests/unit/test_diagnostics_confidence_policy.py \
  bot_psychologist/tests/unit/test_route_resolver_rules.py \
  bot_psychologist/tests/contract/test_diagnostics_schema_v101.py \
  bot_psychologist/tests/golden/test_diagnostics_examples.py \
  bot_psychologist/tests/integration/test_single_route_per_turn.py \
  bot_psychologist/tests/unit/test_snapshot_schema_v11.py \
  bot_psychologist/tests/unit/test_memory_fallback_chain.py \
  bot_psychologist/tests/unit/test_summary_staleness_policy.py \
  bot_psychologist/tests/contract/test_memory_contract_v11.py \
  bot_psychologist/tests/integration/test_context_continuity_between_sessions.py \
  bot_psychologist/tests/regression/test_memory_does_not_require_full_raw_history.py -v
```

Результат: 42 passed (targeted suites).

## Next
- Продолжить `Phase 10`: cleanup/dead-code и обновление архитектурной документации под итоговый Neo runtime.
