# PRD-146: `answer_adaptive.py` Modularization (Wave 132)

## Context
After Wave 131, `runtime_misc_helpers.py` became a compatibility facade. `answer_adaptive.py` still imported orchestration helpers through that facade.

## Scope (Wave 132)
Switch `answer_adaptive.py` to direct imports from new modules:
- `bootstrap_runtime_helpers.py`
- `fast_path_stage_helpers.py`
- `full_path_stage_helpers.py`

Keep runtime alias names unchanged in `answer_adaptive.py`.

## Objectives
1. Reduce indirection in active runtime path.
2. Keep behavior unchanged and preserve monkeypatch/test touchpoints in `answer_adaptive.py`.
3. Maintain compatibility facade for external imports.

## Technical Design
### Files
- `bot_agent/answer_adaptive.py`

### Changes
- Replace:
  - `from .adaptive_runtime.runtime_misc_helpers import ...`
- With direct imports from split helper modules.

No logic changes.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/contract/test_prompt_stack_contract_v2.py`
- `tests/unit/test_prompt_stack_order.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`

Full:
- `pytest -q` (with local TMP/TEMP override)
