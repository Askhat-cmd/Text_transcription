# Neo MindBot Runtime v10.1

## Цель
Этот документ фиксирует фактический runtime-контур после миграции на Neo MindBot v10.1.

## Активный pipeline (online runtime)
1. `answer_question_adaptive(...)` получает запрос.
2. Safety/route сигналы + Diagnostics v1.
3. Deterministic `RouteResolver` (один route на turn).
4. Retrieval из Bot_data_base + optional rerank + block cap.
5. Prompt Stack v2 (единый сборщик инструкций).
6. Генерация ответа (`ResponseGenerator`) + Output Validation.
7. Memory v1.1 snapshot update.
8. Trace assembly + schema validation (`trace_schema_valid`).

## Что отключено из legacy в активном runtime
- SD runtime dependency в online-классификации.
- SD-filtering в retrieval контракте.
- User level adaptation в online prompt/retrieval flow.
- Multi-gate routing через дополнительные LLM decision-gate.

## Fault tolerance
- Startup fail-fast валидация критичных runtime-конфигов (`assert_runtime_config`).
- Degraded retrieval mode:
  - `retriever_init_failed`
  - `retrieval_failed`
- Частичный отказ LLM/retrieval не должен валить весь pipeline.
- Admin import с rollback к последней валидной версии overrides.

## Контракты наблюдаемости
- `debug_trace` содержит:
  - route, confidence, diagnostics
  - retrieval/rerank стадии
  - selected practice + alternatives
  - memory strategy/staleness
  - llm calls + token accounting
  - `trace_schema_valid` и `trace_schema_errors`

## E2E-пакет (Phase 10, базовый)
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

