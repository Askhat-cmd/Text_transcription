# TASKLIST PRD-062: `answer_adaptive.py` Modularization (Wave 48)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_resolve_routing_and_apply_block_cap(...)` in routing helpers.
- [x] Replace inline routing/cap block in `answer_adaptive.py` with helper call.
- [x] Preserve returned contract used by phase-8 context and retrieval observability.
- [x] Run targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/routing_stage_helpers.py`:
  - `_resolve_routing_and_apply_block_cap(...)`
- Updated `answer_adaptive.py`:
  - routing+cap stage replaced with helper call
  - runtime import/wrapper alignment
- Validation:
  - Targeted: `12 passed`
  - Full suite: `501 passed, 13 skipped`
