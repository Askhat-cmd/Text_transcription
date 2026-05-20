# Roadmap

## Done
- PRD-046.1.31: controlled rollout execution gate completed with bounded cohort (<=3 operators), budget/hard-stop/rollback/safety/trace/no-mutation proofs.
- PRD-046.1.30: controlled rollout planning package completed (plan-only, rollback-first, no provider execution).
- Runtime foundation and governance chain through `PRD-046.0.x`.
- Diagnostic Center readiness, shadow integration, planner/writer pilot, prompt-constraint limited runtime chain through `PRD-046.1.16`.
- Response quality eval and calibration packs through `PRD-046.1.18`.
- Controlled runtime pilot readiness/execution/results and provider-backed cycles through `PRD-046.1.28`.
- `PRD-046.1.29`: stabilization cleanup, artifact classification, docs compaction, permanent gate revalidation (`70635e1`).

## Current / In Progress
- No active cleanup/stabilization PRD in progress.

## Next
1. PRD-046.1.32 - Diagnostic Center Controlled Rollout Results / Rollback / Quality Gate v1.
1. PRD-046.1.31 - Diagnostic Center Controlled Rollout Execution Gate v1.
2. Hotfix path only if new blockers appear in rollout-planning preparation.

## Later
- Operational hardening for governed limited runtime.
- Additional observability and runbook hardening.
- Explicit broad-rollout governance PRD (separate from cleanup).

## Deferred / Not Yet
- Broad rollout to normal users.
- Production-ready declaration for Diagnostic Center authority expansion.

## Roadmap Rules
1. Runtime/architecture PRDs update `docs/PROJECT_STATE.md`.
2. Sequencing PRDs update `docs/ROADMAP.md`.
3. Boundary decisions update `docs/DECISIONS.md`.
4. Every merged PRD updates `docs/PRD_INDEX.md`.
5. `TO_DO_LIST` is historical evidence; `docs/` is compact operational map.
