# PRD-131: `answer_adaptive.py` Modularization (Wave 117)

## Context
Full-path success response assembly still contained legacy `*_fn` naming for response-builder dependencies and finalization glue, despite already being stable callable injection points.

## Scope (Wave 117)
Normalize selected response-builder contracts in full-path success stage:
- `_build_full_path_success_response(...)`
- `_finalize_full_path_success_stage(...)`
- `_run_full_path_success_stage(...)`
- callsite wiring in `runtime_misc_helpers.py`

## Objectives
1. Reduce callable-contract naming noise in full-path response assembly.
2. Keep behavior/schema unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/response_utils.py (removed in Wave 142)`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
Rename selected parameters:
- `build_sources_from_blocks_fn` -> `build_sources_from_blocks`
- `log_blocks_fn` -> `log_blocks`
- `build_success_response_fn` -> `build_success_response`
- `build_full_success_metadata_fn` -> `build_full_success_metadata`
- `prepare_post_llm_fn` -> `prepare_post_llm` (full-path finalizer)

No functional logic changes.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`

Full:
- `pytest -q`


