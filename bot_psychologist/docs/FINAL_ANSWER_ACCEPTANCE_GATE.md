# Final Answer Acceptance Gate

- status: current
- last_verified_prd: PRD-047.12-HF1

## Active Now
- `final_answer_acceptance_gate_v1` runs after Writer and Validator.
- It blocks stale stubs, generic concrete-situation answers, missed direct questions, repeated bad answers, failed repair, wrong close/greeting behavior, missing requested markdown, and writer errors.
- Failed answers are quarantined from answered-state, healthy context memory, and last-offer seeding.
- One Writer retry can be triggered with gate feedback through the same `WriterContract`.

## Not Production Ready
- Gate is a developer-local acceptance and observability layer, not a production rollout claim.

## How To Test
- Run `pytest tests/test_final_answer_acceptance_gate_v1.py tests/multiagent/test_final_answer_acceptance_orchestrator.py -q`.
- Inspect `debug.final_answer_acceptance_gate` in live traces.
