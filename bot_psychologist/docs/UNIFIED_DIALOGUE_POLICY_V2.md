# Unified Dialogue Policy V2

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now
- `safe_guided`, `mvp_free_dialogue`, and `free_dialogue_default` resolve through one unified policy surface.
- `mvp_free_dialogue` is a compatibility alias/preset, not a separate orchestrator or API path.
- The authority order remains: minimal safety, explicit user request, knowledge/concept need, writer freedom, planner/diagnostic advisory.

## Not Production Ready
- Developer-local profiles are not broad rollout profiles.
- Planner and diagnostic blocks are not hard authority over final answer content.

## How To Test
- Check `/api/admin/runtime/effective` for `dialogue_policy.version`, `active_profile_alias`, and `profile_preset`.
- Run architecture audit artifacts under `TO_DO_LIST/logs/PRD-047.12-HF1/`.

## PRD-047.13-HF1 cleanup closure note
- This document was re-verified during cleanup closure; runtime behavior was not changed.

## PRD-047.13-HF1 Split Closure
- `unified_dialogue_policy_v2` is the only current policy surface.
- `safe_guided`, `mvp_free_dialogue`, and `free_dialogue_default` are preset/alias values resolved by the unified policy, not separate systems.
- Profile-specific depth/token/planner settings are treated as configuration inside the same runtime path.
