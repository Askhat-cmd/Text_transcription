# No Stub Dialogue Policy

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now
- Known stale phrases are detected by `stale_stub_detector`.
- Final answers containing stale mechanism stubs fail `final_answer_acceptance_gate_v1`.
- Failed answers do not close unanswered questions and do not become healthy context.

## Not Production Ready
- This policy is a runtime acceptance gate, not a complete dialogue quality solution.

## How To Test
- Run stale detector tests.
- Run gate tests with PRD-HF1 stale phrases.

## PRD-047.13-HF1 cleanup closure note
- This document was re-verified during cleanup closure; runtime behavior was not changed.

