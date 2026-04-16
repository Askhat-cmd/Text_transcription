# TASKLIST PRD-152 - Wave 138 Progress

- [x] Extract failure/no-retrieval helper cluster into `response_failure_helpers.py`.
- [x] Keep compatibility import surface in `response_utils.py (removed in Wave 142)`.
- [x] Verify syntax and imports in runtime callsites.
- [x] Run targeted tests.
- [x] Run full suite.

## Results
- `response_failure_helpers.py` added.
- `response_utils.py (removed in Wave 142)` reduced to success/shared compatibility surface.
- Targeted tests: `7 passed`.
- Full suite: `482 passed, 32 skipped`.

