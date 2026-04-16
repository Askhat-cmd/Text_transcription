# PRD-075: `answer_adaptive.py` Modularization (Wave 61)

## Context
Top section of `answer_question_adaptive(...)` still contained a large Stage-1 bootstrap block (memory context setup, debug trace hydration, phase8 detection, onboarding guard, and level resolution).

## Scope (Wave 61)
Extract Stage-1 bootstrap/onboarding guard orchestration into runtime helper and replace inline block in `answer_adaptive.py`.

## Objectives
1. Shrink `answer_question_adaptive(...)` top orchestration block.
2. Keep Stage-1 behavior fully identical.
3. Preserve regression compatibility marker for level-adapter removal contract tests.

## Technical Design
Update `adaptive_runtime/runtime_misc_helpers.py`:
- add `_run_bootstrap_and_onboarding_guard(...)` that composes:
  - `_load_runtime_memory_context(...)`
  - phase8 signal detection
  - optional onboarding start-command early response
  - debug trace/debug info hydration
  - path-level resolution for path recommendation layer

Update `answer_adaptive.py`:
- import `_run_bootstrap_and_onboarding_guard` as runtime helper.
- replace inline Stage-1 block with helper call.
- preserve compatibility sentinel `level_adapter = None` in function source to satisfy regression contract test.

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
