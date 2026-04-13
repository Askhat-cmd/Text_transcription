# Strategy: `answer_adaptive.py` Modularization

## Goal
Split `bot_agent/answer_adaptive.py` into focused modules without changing runtime behavior, contracts, or trace semantics.

## Why
- Current file is operationally heavy (3000+ lines, one orchestration function ~1800 lines).
- Legacy cleanup is harder while logic is concentrated in one place.
- Safe change velocity requires smaller, testable units.

## Non-Negotiable Invariants
1. Public entrypoint remains `answer_question_adaptive(...)`.
2. API/SSE payload contracts remain backward-compatible.
3. NEO routing/diagnostics behavior remains unchanged.
4. Trace fields and `Полотно LLM` content stay compatible.
5. Full test suite remains green after each wave.

## Wave Plan
### Wave 1 (Safe Extraction, no behavior changes)
- Extract pure/safe helpers into `bot_agent/adaptive_runtime/*`.
- Keep `answer_question_adaptive` as orchestration facade.
- No schema or endpoint changes.

### Wave 2 (Pipeline Slices)
- Split orchestration into internal stages:
  - classification/diagnostics
  - retrieval/re-rank
  - prompt/llm/validation
  - trace/session accounting
- Preserve exact output contracts.

### Wave 3 (Legacy Purge + Simplification)
- Remove dead compatibility code confirmed unused by runtime/tests.
- Final trace/documentation cleanup for NEO-first IA.

## Safety Gates (Each Wave)
1. Targeted tests for changed scope.
2. Full `pytest tests` pass.
3. API import/smoke pass.
4. Manual web trace sanity check (one session).
5. Rollback path documented (single-wave revert).

## Risk Controls
- One wave = one PRD + one tasklist.
- Avoid parallel risky edits in routing + trace + memory in same wave.
- Keep refactor commits separate from behavior commits.
- Never remove legacy path unless covered by tests and grep-backed usage check.

## Definition of Done (Final)
- `answer_adaptive.py` reduced to orchestration facade + explicit stage calls.
- No unused SD-era route/classification fragments in active runtime path.
- Docs updated for module boundaries and debugging entrypoints.
- Stable green CI/local suite.

