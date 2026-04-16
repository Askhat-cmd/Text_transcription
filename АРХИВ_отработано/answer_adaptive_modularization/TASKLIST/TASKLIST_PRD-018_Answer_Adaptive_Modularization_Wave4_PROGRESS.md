# TASKLIST PRD-018: `answer_adaptive.py` Modularization (Wave 4)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create PRD-018 Wave 4 document.
- [x] Extract mode/policy helpers to dedicated module.
- [x] Replace local helpers with proxies.
- [x] Restore compatibility for monkeypatch-based validation test touchpoint.
- [x] Run targeted tests.
- [x] Run full suite.
- [x] Finalize Wave 4 snapshot.

## Result Snapshot
- Added module: `bot_agent/adaptive_runtime/mode_policy_helpers.py`.
- `answer_adaptive.py`: 2146 -> 2057 lines.
- Targeted bundle: `13 passed`.
- Full suite: `501 passed, 13 skipped`.
