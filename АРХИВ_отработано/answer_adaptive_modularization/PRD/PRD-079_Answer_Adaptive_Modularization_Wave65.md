# PRD-079: `answer_adaptive.py` Modularization (Wave 65)

## Context
After Wave 64, Stage-4..8 flow in `answer_question_adaptive(...)` still remained as a long inline sequence (state-context composition, full-path LLM stage, and success finalization).

## Scope (Wave 65)
Extract Stage-4..8 orchestration into a dedicated runtime helper in `runtime_misc_helpers.py`.

## Objectives
1. Shrink `answer_question_adaptive(...)` further while preserving contracts.
2. Keep LLM error early-return behavior unchanged.
3. Preserve all observability, trace, and metadata wiring in success path.

## Technical Design
Update `adaptive_runtime/runtime_misc_helpers.py`:
- add `_run_generation_and_success_stage(...)` high-level orchestrator that composes:
  - state-context composition
  - `_run_full_path_llm_stage(...)`
  - full success assembly (`_run_full_path_success_stage(...)`)

Update `answer_adaptive.py`:
- import and call `_run_generation_and_success_stage(...)`.
- replace inline Stage-4..8 block with compact helper invocation + returned `current_stage` propagation.

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
