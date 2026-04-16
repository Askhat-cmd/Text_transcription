# PRD-155 - Answer Adaptive Modularization (Wave 141)

## Context
After Wave 140, runtime modules still imported shared response helpers through compatibility facade `response_utils.py (removed in Wave 142)`.

## Goal
Switch runtime callsites to direct imports from `response_common_helpers.py` to reduce facade coupling.

## Scope
- `fast_path_stage_helpers.py`: move shared response helper imports from `response_utils.py (removed in Wave 142)` to `response_common_helpers.py`.
- `full_path_stage_helpers.py`: move shared response helper imports from `response_utils.py (removed in Wave 142)` to `response_common_helpers.py`.
- `retrieval_stage_helpers.py`: move `_persist_turn` import from `response_utils.py (removed in Wave 142)` to `response_common_helpers.py`.

## Acceptance Criteria
1. No runtime module imports shared helpers from `response_utils.py (removed in Wave 142)`.
2. Behavior unchanged.
3. Targeted and full tests pass.

