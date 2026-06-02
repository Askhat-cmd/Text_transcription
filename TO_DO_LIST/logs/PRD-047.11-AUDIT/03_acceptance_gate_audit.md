# Acceptance Gate Audit

- Detector checks all answer turns per case and latest trace payload.
- Exact + semantic bad-pattern checks are enabled via stale_stub_detector.
- Runner does not allow global `passed` when any case has failed checks.

False-pass risks tracked:
- encoding/misaligned phrase constants
- last-turn-only scan
- synthetic-only markdown checks without real chat page
