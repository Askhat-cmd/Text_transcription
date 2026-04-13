# TASKLIST PRD-022: `answer_adaptive.py` Modularization (Wave 8)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add shared trace finalization helpers in `trace_helpers.py`.
- [x] Integrate helpers in fast/full success branches.
- [x] Integrate helpers in partial/error branches.
- [x] Verify branch-specific legacy strip semantics are preserved.
- [x] Run targeted tests.
- [x] Run full suite.
- [x] Finalize Wave 8 snapshot.

## Result Snapshot
- New shared helpers in `adaptive_runtime/trace_helpers.py`:
  - `_apply_trace_memory_snapshot(...)`
  - `_finalize_trace_payload(...)`
- Replaced repeated debug-trace finalization blocks in 5 branches of `answer_adaptive.py`:
  - fast-path success
  - full success
  - partial/no-blocks
  - LLM error
  - exception return
- Preserved per-branch legacy stripping behavior:
  - `strip_legacy=True` only where it existed before (success + exception paths).
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
