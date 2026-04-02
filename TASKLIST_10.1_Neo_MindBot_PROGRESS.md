# TASKLIST_10.1_Neo_MindBot_PROGRESS

Дата: 2026-04-02

## Статус фаз
- [x] Phase 0 — Baseline and Safety Net
- [x] Phase 1 — Remove SD Runtime Dependency
- [x] Phase 2 — Remove SD Retrieval Filtering
- [x] Phase 3 — Remove UserLevelAdapter
- [x] Phase 4 — Diagnostics v1 + Deterministic RouteResolver
- [ ] Phase 5 — Memory v1.1
- [ ] Phase 6 — Prompt Stack v2 + Output Validation
- [ ] Phase 7 — Practice Engine v1
- [ ] Phase 8 — Informational Branch + Onboarding
- [ ] Phase 9 — Observability + Failure Hardening
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

## Сводный прогон (Phase 0-4)
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
  bot_psychologist/tests/integration/test_single_route_per_turn.py -v
```

Результат: 31 passed.

## Next
- Следующий шаг: `Phase 5 — Memory v1.1`.
