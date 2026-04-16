# PRD-115: `answer_adaptive.py` Modularization (Wave 101)

## Context
Facade still passed preview truncation callback into runtime bootstrap and fast-path stages, while truncation logic is runtime-stable in trace helpers.

## Scope (Wave 101)
Localize preview truncation wiring in runtime helpers and remove obsolete pass-through args from `answer_adaptive.py`.

## Objectives
1. Narrow facade contracts for bootstrap and fast-path.
2. Keep trace/debug payload semantics intact.
3. Preserve test stability on targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove args:
  - `_run_bootstrap_and_onboarding_guard(...): truncate_preview_fn`
  - `_run_fast_path_stage(...): truncate_preview_fn`
- localize `_truncate_preview` import from `trace_helpers`.
- keep existing trace field behavior unchanged.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete args in stage calls:
  - `truncate_preview_fn=_truncate_preview` (bootstrap)
  - `truncate_preview_fn=_truncate_preview` (fast-path)
- remove now-unused `_truncate_preview` import.

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
