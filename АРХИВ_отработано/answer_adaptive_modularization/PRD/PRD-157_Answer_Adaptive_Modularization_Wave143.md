# PRD-157 - Answer Adaptive Modularization (Wave 143)

## Context
After Wave 142, `answer_adaptive.py` still contained a set of thin compatibility wrappers that only proxied runtime helpers.

## Goal
Simplify `answer_adaptive.py` by replacing no-op proxy wrappers with direct compatibility aliases while preserving existing exported names for tests/contracts.

## Scope
- Replace proxy wrappers with direct aliases:
  - `resolve_mode_prompt`
  - `_output_validation_enabled`
  - `_resolve_path_user_level`
  - `_classify_parallel`
  - `_build_state_context`
  - `_should_use_fast_path`
- Keep `_apply_output_validation_policy` wrapper (injects runtime validator policy dependencies).
- Keep `_build_llm_prompts` compatibility wrapper for regression contract tests.
- Remove now-unused typing/runtime imports after aliasing.

## Acceptance Criteria
1. Exported compatibility names above remain available from `answer_adaptive.py`.
2. Runtime behavior unchanged.
3. Targeted tests and full suite pass.
