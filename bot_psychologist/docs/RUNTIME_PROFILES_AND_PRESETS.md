# Runtime Profiles And Presets

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now
- `safe_guided` remains a conservative preset of the unified runtime.
- `mvp_free_dialogue` remains supported as a developer-local alias.
- `free_dialogue_default` is the resolved freer preset for MVP testing.

## Not Production Ready
- No profile enables broad production rollout.
- No profile bypasses minimal safety.

## How To Test
- Use Admin Runtime effective payload.
- Verify there is no duplicate orchestrator, Writer, Planner, or API path for these profiles.

## PRD-047.13-HF1 cleanup closure note
- This document was re-verified during cleanup closure; runtime behavior was not changed.

## PRD-047.13-HF1 Preset/Alias Closure
- `safe_guided`: compatibility preset for conservative guided behavior.
- `mvp_free_dialogue`: developer-local compatibility alias that resolves to the freer preset.
- `free_dialogue_default`: preset value inside the unified policy surface.
- These names must not be presented as separate bots, separate orchestrators, or separate API paths.
