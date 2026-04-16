# PRD-118: `answer_adaptive.py` Modularization (Wave 104)

## Context
Stage-2 routing pipeline still required many technical callback args from facade for utilities that are runtime-stable.

## Scope (Wave 104)
Localize stable Stage-2 utilities in `routing_stage_helpers.py` and shrink facade call surface in `answer_adaptive.py`.

## Objectives
1. Significantly reduce callback pass-through noise in facade.
2. Preserve monkeypatch-sensitive hooks (`state_classifier`, `_classify_parallel`, `DecisionGate`, `detect_routing_signals`, `_should_use_fast_path`).
3. Keep behavior and tests unchanged.

## Technical Design
Update `bot_agent/adaptive_runtime/routing_stage_helpers.py`:
- localize these utilities in Stage-2 helper internals:
  - `_timed`
  - `_run_coroutine_sync`
  - `_fallback_state_analysis`
  - `_fallback_sd_result`
  - `resolve_user_stage`
  - `_derive_informational_mode_hint`
  - `resolve_mode_prompt`
  - `detect_contradiction`
- remove corresponding args from:
  - `_run_state_analysis_stage(...)`
  - `_build_contradiction_payload(...)`
  - `_run_state_and_pre_routing_pipeline(...)`

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-2 call args listed above.
- remove now-unused imports tied to removed pass-throughs.

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
