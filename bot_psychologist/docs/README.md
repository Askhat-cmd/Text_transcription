# Bot Psychologist Docs Index

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md
- verification_scope: cleanup-only inventory, documentation truth sync, no runtime behavior changes

This index separates living runtime documentation from historical evidence. Treat the files below as the current documentation surface unless a later PRD updates this index.

## Current Sources Of Truth

- `docs/PROJECT_STATE.md` - repository-level current state and PRD status.
- `docs/PRD_INDEX.md` - PRD acceptance and implementation index.
- `docs/ROADMAP.md` - current roadmap and next PRD direction.
- `bot_psychologist/docs/PROJECT_STATUS_CURRENT.md` - bot runtime status summary.
- `/api/admin/runtime/effective` - effective runtime policy and admin-visible configuration.

## Living Runtime Docs

- `ARCHITECTURE_CURRENT.md` - current multiagent architecture boundaries.
- `UNIFIED_DIALOGUE_POLICY_V2.md` - unified dialogue policy v2 and authority order.
- `RUNTIME_PROFILES_AND_PRESETS.md` - runtime profile and preset behavior.
- `FINAL_ANSWER_ACCEPTANCE_GATE.md` - final answer acceptance gate contract.
- `NO_STUB_DIALOGUE_POLICY.md` - no-stub runtime policy.
- `REAL_LIVE_ACCEPTANCE_PROTOCOL.md` - real live acceptance protocol.
- `WEB_CHAT_MARKDOWN_RENDERING.md` - Web Chat markdown rendering contract.
- `DIAGNOSTIC_CENTER_BOUNDARY.md` - Diagnostic Center boundary and observability limits.

## Admin And Observability Docs

- `ADMIN_RUNTIME_EFFECTIVE.md` - Admin Runtime effective payload contract.
- `ADMIN_PROMPTS_READINESS_MAP.md` - admin prompt readiness map.
- `DIAGNOSTIC_CENTER_ADMIN_CONTROL.md` - Diagnostic Center admin control docs.
- `RUNTIME_DRIFT_GUARD.md` - observability-first drift guard notes.
- `LIVE_USER_TESTING_PROTOCOL.md` - guided live testing protocol.

## Historical Or Reference Docs

Historical docs, migration notes, PRD artifacts, old generated reports, and archived evidence are reference-only. They must not override the living runtime docs or Admin Runtime effective payload.

## How To Test

- Run the targeted backend regression listed in `TO_DO_LIST/logs/PRD-047.13-HF1/test_command_output.txt`.
- Run `npm run build` from `bot_psychologist/web_ui`.
- Verify current effective policy through `/api/admin/runtime/effective`.

## PRD-047.13 Cleanup Boundary

PRD-047.13-HF1 closes documentation and artifact cleanup noise after PRD-047.13. It does not change Writer, Orchestrator, Dialogue Act, RAG, Chroma retrieval, Diagnostic Center authority, Web Chat runtime behavior, or safety policy.

Current flags remain developer-local:

- `mvp_free_dialogue`: developer-local only.
- `production_rollout`: false.
- `normal_user_activation`: false.

Recommended next work item:

- `PRD-047.14` - Live Dialogue Quality Polish / Human Reference Calibration v1.
