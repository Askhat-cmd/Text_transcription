# No Stub Dialogue Policy

- status: current
- last_verified_prd: PRD-047.12-HF1

## Active Now
- Known stale phrases are detected by `stale_stub_detector`.
- Final answers containing stale mechanism stubs fail `final_answer_acceptance_gate_v1`.
- Failed answers do not close unanswered questions and do not become healthy context.

## Not Production Ready
- This policy is a runtime acceptance gate, not a complete dialogue quality solution.

## How To Test
- Run stale detector tests.
- Run gate tests with PRD-HF1 stale phrases.
