# Architecture Current

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now
- The active user path is the single multiagent runtime in `bot_agent.multiagent.orchestrator`.
- `unified_dialogue_policy_v2` resolves profile presets and feeds Writer through one `WriterContract`.
- Writer and Validator are followed by `final_answer_acceptance_gate_v1` before dialogue state, last offer, and memory acceptance.
- Diagnostic Center, Planner, Active Line, and Diagnostic Card remain advisory/context sources.

## Not Production Ready
- Broad rollout is not enabled.
- Normal-user activation is not approved.
- The free dialogue profile is developer-local.

## How To Test
- Run targeted backend tests for final answer gate and orchestrator quarantine.
- Run `scripts/run_prd_047_12_hf1_acceptance.py --live --browser` against local backend and Web UI.

## PRD-047.13-HF1 cleanup closure note
- This document was re-verified during cleanup closure; runtime behavior was not changed.

