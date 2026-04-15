# PRD-108: `answer_adaptive.py` Modularization (Wave 94)

## Context
After Wave 93, Stage-4 still accepted `semantic_analyzer_cls` and `path_builder` from facade although these are runtime-stable dependencies.

## Scope (Wave 94)
Localize semantic/path dependencies inside `runtime_misc_helpers.py` and remove facade pass-throughs.

## Objectives
1. Further narrow Stage-4 facade contract.
2. Preserve recommendation and semantic-analysis behavior.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove signature args:
  - `semantic_analyzer_cls`
  - `path_builder`
- localize runtime imports in function scope:
  - `SemanticAnalyzer`
  - `path_builder`
- pass localized dependencies into `_run_full_path_success_stage(...)`.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 call args.
- remove now-unused imports `SemanticAnalyzer` and `path_builder`.

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
