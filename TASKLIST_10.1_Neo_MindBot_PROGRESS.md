# TASKLIST_10.1_Neo_MindBot_PROGRESS

Дата: 2026-04-02

## Статус фаз
- [x] Phase 0 — Baseline and Safety Net
- [x] Phase 1 — Remove SD Runtime Dependency
- [x] Phase 2 — Remove SD Retrieval Filtering
- [ ] Phase 3 — Remove UserLevelAdapter
- [ ] Phase 4 — Diagnostics v1 + Deterministic RouteResolver
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

## Сводный прогон (Phase 0-2)
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
  bot_psychologist/tests/contract/test_retrieval_contract_v101.py -v
```

Результат: 15 passed.

## Next
- Следующий шаг: `Phase 3 — Remove UserLevelAdapter`.
