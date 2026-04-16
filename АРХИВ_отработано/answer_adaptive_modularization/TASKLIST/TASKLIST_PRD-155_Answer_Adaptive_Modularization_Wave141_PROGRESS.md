# TASKLIST PRD-155 - Wave 141 Progress

- [x] Rewire fast-path shared response helper imports to `response_common_helpers.py`.
- [x] Rewire full-path shared response helper imports to `response_common_helpers.py`.
- [x] Rewire retrieval `_persist_turn` import to `response_common_helpers.py`.
- [x] Run targeted tests.
- [x] Run full suite.

## Results
- Runtime stage callsites decoupled from `response_utils.py (removed in Wave 142)` facade.
- Facade kept for compatibility imports only.
- Targeted tests: `7 passed`.
- Full suite: `482 passed, 32 skipped`.

