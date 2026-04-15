# PRD-111: `answer_adaptive.py` Modularization (Wave 97)

## Context
Fast-path Stage-2 still received state-context composition callbacks from facade, although these dependencies are runtime-stable.

## Scope (Wave 97)
Localize fast-path state-context composition in `runtime_misc_helpers.py` and remove pass-through callbacks from facade.

## Objectives
1. Reduce fast-path Stage-2 argument surface in `answer_adaptive.py`.
2. Preserve fast-path response semantics and trace behavior.
3. Validate via targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_fast_path_stage(...)` args:
  - `compose_state_context_fn`
  - `build_state_context_fn`
- localize imports from `state_helpers`:
  - `_compose_state_context`
  - `_build_state_context`
- use localized callables to build fast-path `state_context`.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete fast-path call args:
  - `compose_state_context_fn=_runtime_compose_state_context`
  - `build_state_context_fn=_build_state_context`

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
