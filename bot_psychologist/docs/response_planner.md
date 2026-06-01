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

## PRD-047.6 Runtime Drift Guard
- Added deterministic runtime monitor `planner_drift_guard_v1`:
  - compares `response_planner` vs `final_answer`;
  - emits per-turn `status`, `severity`, `flags`, and obedience fields;
  - stores rolling counters in an in-memory monitor window (`max=100`).
- Drift guard is `observe_only`:
  - does not block user answers;
  - does not rewrite final answer text;
  - does not introduce new LLM agents.
- New trace fields:
  - `planner_drift_guard_version`
  - `planner_drift_guard`
  - `planner_drift_guard_error`
  - `planner_drift_summary`
- Runtime replay artifacts:
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_dry.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_direct.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_live.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_summary.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_negative_regression.json`

## PRD-047.9 Unified Adaptive Policy Additions
- Added planner shape for concept-practice overview requests:
  - `next_move=answer_practice_overview`
  - `answer_shape=practice_catalog_explanation`
  - `response_depth=long`
  - `question_policy=optional_none`
  - `practice_policy=overview_allowed`
- Added explicit one-step override branch:
  - if user explicitly asks for one micro-step, planner still returns `one_step`.
- Added stale-active-line signal support (`active_line_stale`) so current concept/practice request can override old line pressure in MVP profile.

## PRD-047.10 Update (2026-06-01)
- `response_planner` remains advisory in MVP profile and does not become a blocking rewriter layer.
- Human-like behavior upgrades (repair/summary/direct concrete response shapes) are applied in Writer compliance and unified policy, while planner authority stays deterministic advisory.
