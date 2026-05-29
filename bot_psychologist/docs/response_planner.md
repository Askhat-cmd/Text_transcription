# Response Planner

## Scope
`Response Planner v1` is a deterministic layer between Active Line and Writer.

Version:
- `response_planner_v1`

Planner does not generate user-facing text and is not an LLM agent.

## Inputs
- `user_message`
- `thread_state`
- `state_snapshot`
- `active_line`
- `knowledge_answer_guard`
- `philosophy_kernel` (metadata only)

## Decision Output
Main fields:
- `enabled`
- `next_move`
- `answer_shape`
- `response_depth`
- `target_micro_shift`
- `question_policy`
- `practice_policy`
- `revoicing_policy`
- `continuity_policy`
- `must_include`
- `must_avoid`
- `source_signals`
- `confidence`
- `rationale`

## Core Rules
- One answer = one next meaningful move.
- Safety and known-concept routing remain hard boundaries.
- Practice is not default and requires explicit allow path.
- If Active Line suppresses revoicing/questions/practice, planner mirrors that in policy fields.

## PRD-047.5 Calibration Additions
- Added deterministic text detectors for weak live groups:
  - low-resource
  - soft-distress (safety-adjacent)
  - defensive world-blame framing
  - explicit no-question request
  - close/thanks turns
  - explicit direct-step/practice request with negated-practice handling
  - repair-misalignment text
- Added mechanism/practice-suppression override path to avoid false action routing when user asks to continue mechanism analysis without practice.
- Kept safety, knowledge-answer routing, and practice-gate boundaries as hard constraints.

## Runtime Integration
- Orchestrator builds planner decision before `WriterContract`.
- `WriterContract.response_planner` is optional and backward compatible.
- Prompt context gets compact planner fields; Writer remains constrained by compliance checks.

## Trace and API
- `debug.response_planner`
- `debug.response_planner_version`
- `debug.response_planner_error`
- `/api/v1/debug/multiagent-trace` mirrors planner fields.

## Admin Runtime Visibility
`/api/admin/runtime/effective` exposes read-only:
- `response_planner.enabled`
- `response_planner.version`
- `response_planner.kind`
- `response_planner.role`
- `response_planner.live_acceptance_requires_api_trace`
- `response_planner.last_quality_calibration`

No admin editing surface is added in this PRD.

## Calibration Artifacts
- `TO_DO_LIST/logs/PRD-047.4/response_planner_dry.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_direct.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_live.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_trace_samples.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_policy_violations_report.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_dry.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_direct.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_live.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_trace_samples.json`

## PRD-047.5-HF1 Repair Notes
- Fixed false-positive acceptance class where planner selected `stabilize_safety/safety_grounding` but final answer drifted to mechanism explanation.
- Runner strict checks now gate:
  - safety-grounding no-mechanism language
  - short-support compact support shape
  - `question_policy=none` strict no-question/no-question-invite markers
  - `practice_policy=forbidden` strict no-practice-instruction markers
  - planner-shape alignment counters
- HF1 artifacts:
  - `TO_DO_LIST/logs/PRD-047.5-HF1/planner_answer_fit_dry.json`
  - `TO_DO_LIST/logs/PRD-047.5-HF1/planner_answer_fit_direct.json`
  - `TO_DO_LIST/logs/PRD-047.5-HF1/planner_answer_fit_live.json`
  - `TO_DO_LIST/logs/PRD-047.5-HF1/answer_fit_false_positive_regression.json`
