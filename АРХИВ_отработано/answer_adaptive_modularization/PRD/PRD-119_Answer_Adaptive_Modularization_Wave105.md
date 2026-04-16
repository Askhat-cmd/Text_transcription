# PRD-119: `answer_adaptive.py` Modularization (Wave 105)

## Context
Bootstrap orchestration still passed two runtime-stable callbacks from facade:
- memory-context loader
- Phase-8 signal detector

## Scope (Wave 105)
Localize these callbacks inside bootstrap helper and simplify facade call.

## Objectives
1. Further reduce bootstrap callback surface.
2. Preserve monkeypatch-sensitive hook for `get_conversation_memory`.
3. Keep regression matrix green.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_bootstrap_and_onboarding_guard(...)` args:
  - `load_runtime_memory_context_fn`
  - `detect_phase8_signals_fn`
- localize internals:
  - use `_load_runtime_memory_context(...)` directly
  - import and use `detect_phase8_signals` directly

Update `bot_agent/answer_adaptive.py`:
- remove obsolete bootstrap call args listed above.
- remove now-unused related imports.

## Test Plan
Expanded targeted:
- `tests/regression/test_no_level_based_prompting.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/integration/test_generation_validation_separation.py`

Full:
- `pytest -q tests --maxfail=1`
