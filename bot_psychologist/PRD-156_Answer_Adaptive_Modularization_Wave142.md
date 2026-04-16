# PRD-156 - Answer Adaptive Modularization (Wave 142)

## Context
After Wave 141, `response_utils.py` remained as a compatibility facade only. Runtime imports were already rewired to direct helper modules.

## Goal
Complete facade removal by deleting `response_utils.py` and locking the contract with test validation.

## Scope
- Remove `bot_agent/adaptive_runtime/response_utils.py`.
- Verify there are no active Python imports from `response_utils`.
- Run targeted tests for adaptive runtime paths.
- Run full `pytest tests` suite.

## Acceptance Criteria
1. `bot_agent/adaptive_runtime/response_utils.py` does not exist.
2. No active `*.py` imports depend on `response_utils`.
3. Targeted tests pass.
4. Full suite passes green.
