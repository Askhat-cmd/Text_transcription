# Real Live Acceptance Protocol

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now
- Live acceptance must call the running backend and export real turn traces.
- Mocked/dry cases are not accepted as live proof.
- Failed live/browser/architecture gates must not be reported as passed.

## Not Production Ready
- Passing local live cycles does not imply production readiness.

## How To Test
- Start services from `запуск проека.txt`.
- Run `python scripts/run_prd_047_12_hf1_acceptance.py --live --browser`.

## PRD-047.13-HF1 cleanup closure note
- This document was re-verified during cleanup closure; runtime behavior was not changed.

