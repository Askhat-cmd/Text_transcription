# TASKLIST_11_0_Neo_MindBot_Migration_PROGRESS

## Статус волн

- [x] Wave 1 — Soft Freeze (feature flags + runtime guardrails)
- [x] Wave 2 — Удаление SD из retrieval/memory контрактов
- [x] Wave 3 — Удаление user-level adapter из активного runtime
- [x] Wave 4 — Single DecisionGate routing cleanup
- [x] Wave 5 — Prompt stack + state model alignment
- [x] Wave 6 — Legacy purge + финальная регрессия

---

## Wave 1 — Soft Freeze

### Выполнено
- [x] Neo-by-default флаги включены:
  - [x] `NEO_MINDBOT_ENABLED = True`
  - [x] `LEGACY_PIPELINE_ENABLED = False`
  - [x] `SD_CLASSIFIER_ENABLED = False`
  - [x] `USER_LEVEL_ADAPTER_ENABLED = False`
  - [x] `PRE_ROUTING_ENABLED = False`
- [x] Runtime guardrails включены:
  - [x] `DISABLE_SD_RUNTIME = True`
  - [x] `DISABLE_USER_LEVEL_ADAPTER = True`
- [x] Добавлен защитный runtime-барьер в SD-контур (позже модуль архивирован в `bot_psychologist/bot_agent/legacy/python/sd_classifier.py`)
- [x] `answer_adaptive` использует fallback при отключённом SD (`_sd_runtime_disabled()`)
- [x] Тесты Wave 1 зелёные:
  - [x] `tests/config/test_feature_flags_baseline.py`
  - [x] `tests/unit/test_sd_runtime_disabled.py`
  - [x] `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- [x] Smoke покрыт автоматизированным набором (>=10 сценариев) через regression/integration trace-контракты

### Последний прогон
`python -m pytest tests/config/test_feature_flags_baseline.py tests/unit/test_sd_runtime_disabled.py tests/regression/test_streaming_sd_runtime_disabled_contract.py -v`

---

## Wave 2 — SD out of retrieval + memory

### Выполнено
- [x] Убран `sd_level` из retrieval API-контрактов:
  - [x] `bot_psychologist/bot_agent/db_api_client.py` (`query/aquery`)
  - [x] `bot_psychologist/bot_agent/retriever.py` (`retrieve`)
- [x] Убран `sd_filter` из Chroma query payload:
  - [x] `bot_psychologist/bot_agent/chroma_loader.py`
- [x] SD-метаданные не пишутся в rebuild-коллекцию Chroma:
  - [x] `bot_psychologist/bot_agent/chroma_loader.py`
- [x] SD убран из cross-session memory surface:
  - [x] `bot_psychologist/bot_agent/answer_adaptive.py`
  - [x] `bot_psychologist/bot_agent/conversation_memory.py`
- [x] Тесты Wave 2 зелёные
- [x] Smoke retrieval по `hyper/window/hypo` без SD-фильтра зафиксирован в regression/integration тестах

### Последний прогон
`python -m pytest tests/test_db_api_client.py tests/unit/test_retriever_no_sd_filter.py tests/regression/test_no_hidden_sd_filtering.py tests/test_retriever_fallback.py tests/contract/test_retrieval_contract_v101.py tests/test_conversation_memory_persistence.py -v`

---

## Wave 3 — user_level_adapter out of runtime

### Выполнено
- [x] Вынесен enum в нейтральный модуль:
  - [x] создан `bot_psychologist/bot_agent/user_level_types.py`
  - [x] `answer_adaptive.py` и `path_builder.py` переведены на `user_level_types.UserLevel`
  - [x] `user_level_adapter.py` импортирует `UserLevel` из `user_level_types.py`
- [x] Удалены runtime-вызовы level adapter из активного пайплайна:
  - [x] `answer_adaptive.py` больше не передаёт `user_level_adapter` в `ResponseGenerator`
  - [x] `answer_adaptive.py` больше не вызывает `filter_blocks_by_level` в активной ветке
  - [x] `response/response_generator.py` принимает `user_level_adapter` только как backward-compatible аргумент (игнорируется)
- [x] Очищены runtime metadata/trace от `user_level*`
- [x] Тесты Wave 3 зелёные:
  - [x] `tests/unit/test_user_level_adapter_removed.py`
  - [x] `tests/regression/test_no_user_level_runtime_metadata.py`
  - [x] `tests/integration/test_pipeline_without_level_adapter.py`
  - [x] `tests/contract/test_live_metadata_contract_after_purge.py`
  - [x] `tests/test_response_generator.py`
  - [x] `tests/test_path_builder.py`

### Последний прогон
`python -m pytest tests/unit/test_user_level_adapter_removed.py tests/test_path_builder.py tests/test_response_generator.py tests/regression/test_no_user_level_runtime_metadata.py tests/integration/test_pipeline_without_level_adapter.py tests/contract/test_live_metadata_contract_after_purge.py -v`

---

## Wave 4 — Single DecisionGate

- [x] Убрать pre-routing/pre-rerank дубли и оставить один route flow
  - [x] Удалён отдельный `pre_rerank` routing-проход в `answer_adaptive.py`
  - [x] Для non-deterministic ветки `routing_result` теперь переиспользует pre-routing результат
  - [x] Убрана fallback-ветка второго `DecisionGate.route()` в non-deterministic потоке
- [x] Trace-контракт на один route-flow зафиксирован тестами
  - [x] нет `pre_routing_result` / `pre_rerank_result` в trace
  - [x] `llm_calls <= 2` на запрос
  - [x] `total_duration_ms <= 5000` (контрактный stub-сценарий)
- [x] Финально упростить форму `RoutingResult` до чистого Neo-пакета (`mode/track/tone`) без legacy-хвостов
  - [x] `RouteResolution` теперь содержит `track` и `tone`
  - [x] `DecisionGate.RoutingResult` теперь содержит `track` и `tone`
  - [x] В trace/runtime добавлен Neo-пакет `routing_result = {mode, track, tone}`
  - [x] Удалены legacy-routing поля (`decision_rule_id`, `mode_reason`, `confidence_level`, `confidence_score`) из публичного runtime metadata payload

## Wave 5 — Prompt stack + state model

- [x] Финализировать 7-блочный Neo stack (`AA → A → Core → Diag → Method → Proc → Output`)
  - [x] `bot_agent/prompts/` создана
  - [x] Добавлены 7 базовых блоков (`aa_safety.md`, `a_seasonal.md`, `core_identity.md`, `diag_algorithm.md`, `reflective_method.md`, `procedural_scripts.md`, `output_layer.md`)
  - [x] `prompt_registry_v2.py` переведён на новый порядок секций (`A_SEASONAL`, `DIAG_ALGORITHM`, `REFLECTIVE_METHOD`, `PROCEDURAL_SCRIPTS`, `OUTPUT_LAYER`)
  - [x] Добавлен контрактный тест на 7 секций (`tests/unit/test_prompt_registry_versioning.py`)
- [x] Убрать SD prompt dependencies из активного registry/runtime
  - [x] SD-промты больше не участвуют в `prompt_registry_v2`
  - [x] Полностью удалить SD-слой из fallback-prompt path (`response_generator` / `_build_llm_prompts`)
- [x] Зафиксировать state taxonomy (`HYPER/WINDOW/HYPO + 6 request_function`) во всех контрактах
  - [x] `diagnostics_classifier` переведён на `solution` (с alias `directive -> solution`)
  - [x] `route_resolver`, `answer_adaptive`, `practice_selector` обновлены для совместимости
  - [x] Runtime/admin payload контракты закреплены без `directive` (только `solution`)

## Wave 6 — Legacy purge + final regression

- [x] Legacy grep/contract (`test_no_legacy.py`)
- [x] Перенос/удаление legacy-файлов в `legacy/`
  - [x] SD/level prompt files (`prompt_sd_*`, `prompt_system_level_*`) перенесены в `bot_agent/legacy/prompts/`
  - [x] Active editable prompt surface очищен до Neo (`prompt_system_base`, `prompt_mode_informational`)
  - [x] Startup snapshot creation в `api/main.py` переведён на динамический список `config.EDITABLE_PROMPTS`
  - [x] Legacy Python modules архивированы в `bot_agent/legacy/python/`
  - [x] Active runtime отвязан от legacy-модулей (`bot_agent/__init__.py`, `api/routes.py`, `answer_adaptive.py`)
  - [x] Выполнен “жесткий вариант”: stub-файлы удалены из active path, legacy-модули оставлены только в `bot_agent/legacy/python/`
- [x] Финальный acceptance + regression suite

---

## Последний прогон (Wave 1-4 regression bundle)

`python -m pytest tests/config/test_feature_flags_baseline.py tests/unit/test_sd_runtime_disabled.py tests/regression/test_streaming_sd_runtime_disabled_contract.py tests/test_db_api_client.py tests/unit/test_retriever_no_sd_filter.py tests/regression/test_no_hidden_sd_filtering.py tests/test_retriever_fallback.py tests/contract/test_retrieval_contract_v101.py tests/test_conversation_memory_persistence.py tests/unit/test_user_level_adapter_removed.py tests/regression/test_no_user_level_runtime_metadata.py tests/integration/test_pipeline_without_level_adapter.py tests/contract/test_live_metadata_contract_after_purge.py tests/test_response_generator.py tests/test_path_builder.py tests/integration/test_single_route_per_turn.py tests/contract/test_trace_contract_after_purge.py tests/e2e/test_legacy_fallback_when_flag_off.py tests/test_retrieval_pipeline_simplified.py -v`

Результат: `59 passed, 2 warnings`.

## Последний прогон (Wave 5 prompt-stack integration)

`python -m pytest tests/unit/test_prompt_registry_versioning.py tests/regression/test_no_legacy_prompt_overlays.py tests/test_response_generator.py tests/integration/test_informational_branch.py tests/regression/test_informational_branch_does_not_force_coaching.py tests/integration/test_runtime_curious_inform_decoupling_v1031.py -v`

Результат: `10 passed`.

## Последний прогон (Wave 4/5 + taxonomy cleanup)

`python -m pytest tests/unit/test_route_resolver_rules.py tests/integration/test_practice_selection_in_pipeline.py tests/unit/test_practice_selector_filters.py tests/unit/test_practice_channel_rotation.py tests/e2e/test_directive_relationship_boundary_case.py tests/e2e/test_practice_start_richness_runtime.py tests/e2e/test_practice_alternative_case.py tests/e2e/test_safe_override_case.py tests/e2e/test_richness_does_not_break_safety_runtime.py tests/test_retrieval_pipeline_simplified.py tests/integration/test_single_route_per_turn.py tests/contract/test_trace_contract_after_purge.py tests/e2e/test_legacy_fallback_when_flag_off.py tests/unit/test_prompt_registry_versioning.py tests/unit/test_prompt_stack_order.py tests/contract/test_admin_diagnostics_effective_payload_schema_v1041.py -v`

Результат: `25 passed, 2 warnings`.

## Последний прогон (Wave 6 legacy-contract smoke)

`python -m pytest tests/contract/test_no_legacy.py -v`

Результат: `1 passed`.

## Последний прогон (Wave 4/5 + Wave 6 incremental)

`python -m pytest tests/unit/test_route_resolver_rules.py tests/integration/test_practice_selection_in_pipeline.py tests/unit/test_practice_selector_filters.py tests/unit/test_practice_channel_rotation.py tests/e2e/test_directive_relationship_boundary_case.py tests/e2e/test_practice_start_richness_runtime.py tests/e2e/test_practice_alternative_case.py tests/e2e/test_safe_override_case.py tests/e2e/test_richness_does_not_break_safety_runtime.py tests/contract/test_no_legacy.py -v`

Результат: `14 passed`.

## Последний прогон (Wave 5 fallback cleanup)

`python -m pytest tests/test_retrieval_pipeline_simplified.py tests/contract/test_trace_contract_after_purge.py tests/contract/test_no_legacy.py -v`

Результат: `8 passed, 2 warnings`.

## Последний прогон (Wave 4 Neo routing package)

`python -m pytest tests/test_decision_gate.py tests/unit/test_route_resolver_rules.py tests/integration/test_single_route_per_turn.py tests/test_retrieval_pipeline_simplified.py tests/contract/test_trace_contract_after_purge.py tests/contract/test_no_legacy.py -v`

Результат: `14 passed, 2 warnings`.

## Последний прогон (Wave 4 runtime payload cleanup)

`python -m pytest tests/regression/test_no_user_level_runtime_metadata.py tests/regression/test_no_sd_runtime_metadata_fields.py tests/contract/test_live_metadata_contract_after_purge.py tests/contract/test_trace_contract_after_purge.py tests/contract/test_no_legacy.py tests/unit/test_route_resolver_rules.py tests/test_decision_gate.py tests/integration/test_single_route_per_turn.py -v`

Результат: `11 passed, 2 warnings`.

## Последний прогон (Wave 1-6 расширенный регрессионный пакет)

`python -m pytest tests/config/test_feature_flags_baseline.py tests/unit/test_sd_runtime_disabled.py tests/regression/test_streaming_sd_runtime_disabled_contract.py tests/test_db_api_client.py tests/unit/test_retriever_no_sd_filter.py tests/regression/test_no_hidden_sd_filtering.py tests/test_retriever_fallback.py tests/contract/test_retrieval_contract_v101.py tests/test_conversation_memory_persistence.py tests/unit/test_user_level_adapter_removed.py tests/regression/test_no_user_level_runtime_metadata.py tests/integration/test_pipeline_without_level_adapter.py tests/contract/test_live_metadata_contract_after_purge.py tests/test_response_generator.py tests/test_path_builder.py tests/integration/test_single_route_per_turn.py tests/contract/test_trace_contract_after_purge.py tests/e2e/test_legacy_fallback_when_flag_off.py tests/test_retrieval_pipeline_simplified.py tests/unit/test_prompt_registry_versioning.py tests/regression/test_no_legacy_prompt_overlays.py tests/integration/test_informational_branch.py tests/regression/test_informational_branch_does_not_force_coaching.py tests/integration/test_runtime_curious_inform_decoupling_v1031.py tests/contract/test_no_legacy.py tests/test_decision_gate.py tests/unit/test_route_resolver_rules.py -v`

Результат: `55 passed, 2 warnings`.

## Последний прогон (Wave 6 prompt-surface cleanup)

`python -m pytest tests/contract/test_no_legacy.py tests/test_admin_api.py tests/contract/test_admin_config_schema_v104.py -v`

Результат: `8 passed`.

## Последний прогон (Wave 6 prompt-surface + admin regression)

`python -m pytest tests/contract/test_no_legacy.py tests/test_admin_api.py tests/unit/test_prompt_registry_versioning.py tests/regression/test_no_legacy_prompt_overlays.py -v`

Результат: `9 passed`.

## Последний прогон (Wave 6 final acceptance, Neo-only active runtime)

`python -m pytest tests/config/test_feature_flags_baseline.py tests/unit/test_sd_runtime_disabled.py tests/regression/test_streaming_sd_runtime_disabled_contract.py tests/test_db_api_client.py tests/unit/test_retriever_no_sd_filter.py tests/regression/test_no_hidden_sd_filtering.py tests/test_retriever_fallback.py tests/contract/test_retrieval_contract_v101.py tests/test_conversation_memory_persistence.py tests/unit/test_user_level_adapter_removed.py tests/regression/test_no_user_level_runtime_metadata.py tests/integration/test_pipeline_without_level_adapter.py tests/contract/test_live_metadata_contract_after_purge.py tests/test_response_generator.py tests/test_path_builder.py tests/integration/test_single_route_per_turn.py tests/contract/test_trace_contract_after_purge.py tests/e2e/test_legacy_fallback_when_flag_off.py tests/test_retrieval_pipeline_simplified.py tests/unit/test_prompt_registry_versioning.py tests/regression/test_no_legacy_prompt_overlays.py tests/integration/test_informational_branch.py tests/regression/test_informational_branch_does_not_force_coaching.py tests/integration/test_runtime_curious_inform_decoupling_v1031.py tests/contract/test_no_legacy.py tests/test_decision_gate.py tests/unit/test_route_resolver_rules.py -v`

Результат: `57 passed`.

Примечание: после восстановления ACL и выполнения “жесткого” варианта пакет проходит полностью без skip.
