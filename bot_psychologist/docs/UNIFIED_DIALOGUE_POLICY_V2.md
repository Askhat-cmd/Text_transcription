# Unified Dialogue Policy V2

- status: current
- last_verified_prd: PRD-047.13

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

## PRD-047.13 cleanup note
- This document was re-verified during cleanup-only inventory; runtime behavior was not changed.

