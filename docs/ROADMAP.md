# Roadmap

## Done
- PRD-047.13: completed project cleanup/docs truth-sync/admin surface inventory after the accepted PRD-047.12-HF1 baseline. It was cleanup-only: no Writer, Orchestrator, Gate, Dialogue Act Resolver, RAG/Chroma, Diagnostic Center authority, prompt behavior, production rollout, or normal-user activation changes.

- PRD-047.12-HF1: accepted final-answer acceptance hotfix over the existing unified runtime (`final_answer_acceptance_gate_v1`, stale-stub quarantine, one Writer retry through existing contract, real live/browser evidence, Admin Runtime gate visibility, Web Chat markdown proof, docs truth sync). It remains developer-local and not a production rollout.

- PRD-047.12: completed unified dialogue-policy consolidation over a single runtime path (`unified_dialogue_policy_v2`, preset resolution for `safe_guided`/`free_dialogue_default`/`mvp_free_dialogue`, dialogue-act + last-offer + unanswered-question + style-state + answer-obligation layers, writer-first prompt contract/admin visibility, and passed dry/direct/live/browser/admin evidence pack).
- PRD-047.11-HF3: completed residual live UX reality-repair cycle on the unified runtime (`writer` concrete-answer-fit hotfix, deterministic thanks-close state repair, localhost `:3000` browser/admin proof, explicit reset/memory proof refresh, admin legacy inventory, and docs/encoding hygiene artifacts) without adding a new runtime branch or broadening activation.
- PRD-047.11-HF2: passed fresh-chat isolation / context-aware RAG gate / real Web Chat markdown proof cycle (new `fresh_chat_context_policy_v1`, `writer_context_package_v1`, explicit current-chat reset + dev memory clear controls, writer-visible RAG suppression when gate denies inclusion, admin/runtime/UI visibility, browser markdown smoke, admin screenshots, and live acceptance on isolated backend/UI `:8002/:3001`).
- PRD-047.11-HF1: completed writer prompt diet repair for `mvp_free_dialogue` (new `legacy_advisory_sanitizer.py`, sanitized advisory summary, `no_exercise_but_answer_normally` rewrite, stale runtime fallback cleanup, trace/admin preservation, HF1 tests, and dedicated runner/artifacts with `writer_prompt_diet_eval=4/4 passed`).
- PRD-047.11-AUDIT: added evidence-first audit runner/dataset/artifact pack (`PRD-047.11-AUDIT`) with source inventory, prompt/acceptance truthfulness checks, 18-case live matrix, raw trace + prompt canvas export, admin payload audit, and honest warning-grade reporting (`14/18` live failures, `15` bad-phrase hits, browser screenshot proof unavailable because Playwright was missing locally).
- PRD-047.11: completed writer-first consolidation end-to-end (new `final_answer_directive_v1`, stale stub detector, MVP prompt assembly advisory refactor, live evidence/admin/runtime extensions, tests, runner, artifacts) with final acceptance `passed` (`dry/direct/live=passed`, real Web Chat markdown smoke `passed`).
- PRD-047.10-HF2: added `live_turn_evidence_v1` export path (orchestrator/debug/API trace), follow-up reliability repair runner/dataset (`HF2-001..HF2-008`), short-input robustness fix (`AskQuestionRequest.query min_length=1`), contextual retrieval taxonomy refinement (`example_grounding/practice_catalog/kb_optional/...`) and markdown smoke DOM artifact flow; acceptance `dry/direct/live=passed` on fresh backend `:8020`.
- PRD-047.10-HF1: added deterministic contextual follow-up pragmatics (`dialogue_pragmatics_v1`), contextual retrieval gating (`included` vs `candidates`, `writer_can_ignore_rag`), writer direct-repair/follow-up compliance patch, trace/API visibility updates, and safe Web Chat markdown rendering (`react-markdown` + `remark-gfm` + `skipHtml`) with runner acceptance (`dry=passed`, `direct=passed`, `live=passed` on fresh backend `:8019`).
- PRD-047.10: calibrated human-like writer autonomy in MVP profile (added `human_like_answer_policy` + `constraint_resolution`, Writer repair/summary/direct-answer mappings, admin/runtime/trace visibility extensions, and mandatory dry/direct/live acceptance on fresh backend `:8018`).
- PRD-047.9: unified adaptive dialogue policy context-unclamp for `mvp_free_dialogue` (recency-preserved writer context budget, authority resolver, practice-overview routing shape, admin effective visibility, and mandatory live acceptance passed on fresh backend `:8016`).
- PRD-047.7: added guided live testing protocol v1 (18-scenario set, sanitized feedback capture/storage, summary builder, smoke runner, admin/web runtime read-only visibility, and evidence artifacts for human-feedback loop readiness).
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
- PRD-047.13-HF1 is the active cleanup closure step: docs truth finalization, legacy split label cleanup, empty artifact closure, and no-runtime-mutation proof.
- No active PRD-047.12 blocker remains; unified dialogue policy v2 is accepted on the current developer-local runtime baseline.

## Next
1. Start `PRD-047.14` for live dialogue quality polish / human-reference calibration on top of the passed unified dialogue-policy baseline after cleanup closure.
2. Treat any further `PRD-047.12-HF*` only as residual regression repair if fresh live/browser/admin evidence reopens follow-up, preset-resolution, or rendering issues.

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

