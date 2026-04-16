# TASKLIST PRD-019: `answer_adaptive.py` Modularization (Wave 5)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create PRD-019 Wave 5 document.
- [x] Extract runtime misc helpers to dedicated module.
- [x] Replace local helper implementations with proxies.
- [x] Run targeted tests.
- [x] Run full suite.
- [x] Finalize Wave 5 snapshot.

## Result Snapshot
- New module:
  - `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- Moved from monolith:
  - `_estimate_cost` + `COST_PER_1K_TOKENS`
  - `_sd_runtime_disabled`
  - `_build_start_command_response`
- `answer_adaptive.py` now keeps thin proxy wrappers for moved helpers.
- Preserved `/start` persistence warning behavior via delegated logger.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
