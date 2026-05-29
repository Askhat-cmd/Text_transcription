# Roadmap

## Done
- PRD-047.6: added observe-only `planner_drift_guard_v1` runtime monitor (deterministic planner-vs-answer drift checks, rolling monitor window=100, trace/debug/admin runtime visibility, 32-case dataset + dry/direct/live replay runner, strict live no-fallback acceptance on fresh backend `:8015`).
- PRD-047.5-HF1: repaired evaluator false-positive class for planner-vs-answer mismatch, tightened strict answer-fit checks/counters, applied minimal writer compliance hotfixes, and regenerated HF1 artifacts with strict acceptance (`dry=26/26`, `direct=26/26`, `live=26/26` on fresh temporary backend `:8014`).
- PRD-047.5: calibrated planner quality for live answer-fit groups (low-resource, soft-distress, defensive, close, no-question, direct-step, repair), expanded dataset/runner to 26 cases, tightened writer planner obedience, and refreshed artifacts (`dry=26/26`, `direct=26/26`, `live=26/26` on fresh temporary backend `:8013`).
- PRD-047.4: added Response Planner v1 deterministic layer (next-move taxonomy + writer contract/prompt/compliance integration), API/debug/admin/runtime visibility, 14-case dataset/runner/evaluator, and refreshed artifacts (`dry=14/14`, `direct=14/14`, `live=14/14` on fresh temporary backend).
- PRD-047.3: added Active Line continuity layer (deterministic intent + continuity/repair + revoicing/practice suppression), integrated WriterContract/prompt/compliance and admin runtime visibility, and delivered active-line eval artifacts (`dry=10/10`, `direct=10/10`, `live=10/10` on fresh temporary backend).
- PRD-047.2: added kernel-quality evaluation dataset/runner (`dry/direct/live`), answer-level evaluator checks, selector/prompt calibrations, prompt compactness gate, trace/admin budget visibility, and docs/report/no-mutation artifacts (`direct=12/12`, `live=skipped` honestly).
- PRD-047.1: added compact NEO Philosophy Kernel module, deterministic lens selector, Writer Freedom Contract v1, writer prompt/kernel wiring, trace/admin effective visibility, PRD smoke runner and no-mutation/report artifacts.
- PRD-047.0-HF1: repaired evaluator false-positive gap by enforcing final-answer compliance checks, strengthened greeting/practice and known-concept answer-first runtime behavior, and refreshed failure artifacts with honest `direct=5/5` and `live=skipped`.
- PRD-047.0: launched Multiagent Quality & Tuning baseline with Knowledge Answer Routing Guard, lexical known-concept override path, writer knowledge-answer contract wiring, live-failure dataset/runner (`dry/direct/live`), trace samples, and no-mutation evidence.
- PRD-046.1.38: synced living docs with post-HF1 runtime reality and added Diagnostic Center Admin Control surface (effective/control/reset contract + Web Admin tab) with developer-local all-users boundary labels.
- PRD-046.1.37: finalized Diagnostic Center completion decision gate with source/provenance/runtime/live/admin/rollback/normal-user/safety/no-mutation evidence and phase-closure transfer brief.
- PRD-046.1.35-HF3: synchronized live RAG evidence with multiagent trace and added writer KB truncation audit.
- PRD-046.1.35-HF2: creator live evidence and BotDB/RAG-to-writer delivery repair with strict diagnostic gates.
- PRD-046.1.35-HF1: creator live evidence and BotDB/RAG-to-writer delivery repair with strict diagnostic gates.
- PRD-046.1.35: creator-live results/rollback/quality gate completed in no-new-execution mode with evidence-strength audit, safety boundary verification, trace/no-mutation/docs gates, and decision handoff.
- PRD-046.1.34: creator-only live activation gate completed with creator identity boundary, runtime controls, web chat smoke, trace monitor MVP, rollback/hard-stop, safety/trace/no-mutation/docs checks.
- PRD-046.1.33: limited runtime activation readiness / normal-user boundary decision gate completed in strict no-new-execution mode; source/live dependency, runtime boundary, rollback/hard-stop, safety/KB, trace sanitization, no-mutation, artifact hygiene, and docs consistency checks consolidated.
- PRD-046.1.32: controlled rollout results/rollback/quality gate completed with no-new-execution consolidation, docs-sync closure, and readiness decision boundary preserved.
- PRD-046.1.31: controlled rollout execution gate completed with bounded cohort (<=3 operators), budget/hard-stop/rollback/safety/trace/no-mutation proofs.
- PRD-046.1.30: controlled rollout planning package completed (plan-only, rollback-first, no provider execution).
- Runtime foundation and governance chain through `PRD-046.0.x`.
- Diagnostic Center readiness, shadow integration, planner/writer pilot, prompt-constraint limited runtime chain through `PRD-046.1.16`.
- Response quality eval and calibration packs through `PRD-046.1.18`.
- Controlled runtime pilot readiness/execution/results and provider-backed cycles through `PRD-046.1.28`.
- `PRD-046.1.29`: stabilization cleanup, artifact classification, docs compaction, permanent gate revalidation (`70635e1`).

## Current / In Progress
- No active PRD in progress after PRD-047.6 closure.

## Next
1. PRD-047.7 Guided Live User Testing Protocol / Human Feedback Capture v1.

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

## PRD-046.1.35-HF4
Current Stage:
PRD-046.1.35-HF4 calibrated creator-live response behavior: example/explanation requests no longer trigger regulate_first by default, practice rejection suppresses body-action suggestions, and Web Trace displays non-empty safe Writer chunk previews.
Next:
PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1.

## HF4 Delivery Metadata
- prd_id: PRD-046.1.35-HF4
- commit_hash: 3a3c6a32a0c29551440432c0a266ab7cbab25b20
- push_status: pushed_to_origin_main

## Done
- PRD-046.1.36: creator-live pilot acceptance completed with source/runtime/admin/creator-pilot/rollback/normal-user/safety gates.
