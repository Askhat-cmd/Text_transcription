# TASKLIST PRD-153 - Wave 139 Progress

- [x] Switch unhandled-exception import in `answer_adaptive.py` to `response_failure_helpers.py`.
- [x] Switch full-path LLM-error handler import to `response_failure_helpers.py`.
- [x] Switch retrieval no-block early-response import to `response_failure_helpers.py`.
- [x] Run targeted tests.
- [x] Run full suite.

## Results
- Runtime callsites aligned to direct failure-helper module imports.
- Backward compatibility preserved via `response_utils.py` re-export imports.
- Targeted tests: `7 passed`.
- Full suite: `482 passed, 32 skipped`.
