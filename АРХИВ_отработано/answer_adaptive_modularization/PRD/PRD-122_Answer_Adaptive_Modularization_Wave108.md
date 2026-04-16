# PRD-122: `answer_adaptive.py` Modularization (Wave 108)

## Context
Post Wave 107, one facade import remained unused in `answer_adaptive.py`:
- `_runtime_compose_state_context`

## Scope (Wave 108)
Remove the remaining dead import from facade module while preserving behavior.

## Objectives
1. Keep facade import surface strictly aligned with live usage.
2. Preserve runtime behavior and test contracts.
3. Maintain green full suite.

## Technical Design
Update `bot_agent/answer_adaptive.py`:
- remove unused import alias `_runtime_compose_state_context`

No functional behavior changes.

## Test Plan
Targeted:
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/unit/test_sd_runtime_disabled.py`

Full:
- `pytest -q`
