# PRD-151 - Answer Adaptive Modularization (Wave 137)

## Context
After Wave 136 extraction, some callsites still imported success helpers indirectly from `response_utils.py (removed in Wave 142)`.

## Goal
Align callsites to import success-stage helpers directly from `response_success_helpers.py`.

## Scope
- Update `fast_path_stage_helpers.py` imports.
- Update `full_path_stage_helpers.py` imports.
- Keep backward compatibility in `response_utils.py (removed in Wave 142)`.

## Acceptance Criteria
1. Success helpers imported directly from `response_success_helpers.py` in runtime stage modules.
2. No behavior change.
3. Targeted tests pass.
4. Full suite passes.

