# Project State - Bot Psychologist / Neo MindBot

## Current Stage
PRD-047.10-HF2 completed live turn evidence export + follow-up reliability repair + markdown smoke verification in unified runtime: added `live_turn_evidence_v1` payload in trace pipeline, upgraded short follow-up pragmatics/retrieval taxonomy, fixed short-input API validation (`min_length=1`), produced reproducible dry/direct/live artifacts with required case exports, and confirmed live pass on fresh backend `:8020` (`status=passed`).
PRD-047.10-HF1 completed direct follow-up repair + contextual retrieval noise reduction + chat markdown readability calibration in unified runtime: added deterministic `dialogue_pragmatics_v1`, contextual retrieval gating (`included` vs `candidates`, `writer_can_ignore_rag`), writer follow-up/repair compliance fixes, explicit trace/API visibility (`dialogue_pragmatics`, `retrieval_decision`), and safe markdown rendering (`react-markdown + remark-gfm + skipHtml`), with runner acceptance `dry/direct/live=passed` on fresh backend `:8019`.
PRD-047.10 completed human-like writer autonomy calibration in `mvp_free_dialogue`: `human_like_answer_policy` + `constraint_resolution` are now part of unified effective dialogue policy, Writer MVP compliance now handles sarcasm/dissatisfaction repair, structured summary requests, direct concrete answers, and explicit one-step preservation with trace/admin visibility; acceptance runner passed (`dry=passed`, `direct=passed`, `live=passed` on fresh backend `:8018`).
PRD-047.9 completed Unified Adaptive Dialogue Policy context-unclamp for `mvp_free_dialogue`: effective authority resolver (`minimal safety > explicit user request > knowledge/concept need > writer freedom > planner/diagnostic advisory`), recency-preserved writer context budget, practice-overview routing/planner shape, admin effective visibility, and live acceptance passed on fresh backend (`dry=passed`, `direct=passed`, `live=passed` on `:8016`).
PRD-047.7 added Guided Live User Testing Protocol v1: structured scenario set (18), sanitized feedback capture/storage, summary builder, smoke runner, and admin/web runtime visibility for feedback loop readiness (`dry smoke passed`, optional live smoke blocked on unavailable backend and recorded as such).
PRD-047.6 added `planner_drift_guard_v1` as observe-only runtime stability envelope: deterministic planner-vs-answer drift checks, rolling in-memory counters, trace/debug/admin visibility, and dry/direct/live replay artifacts (`dry=32/32`, `direct=32/32`, `live=12/12`, `repeat=3`, `warnings=0`, `criticals=0`, `missing_payload=0`, no runner fallback on fresh backend `:8015`).
PRD-047.5-HF1 repaired the answer-fit false-positive class (planner `stabilize_safety` / `safety_grounding` incorrectly passing mechanism-style answers), hardened final-answer compliance gates, and refreshed HF1 artifacts with strict green matrix (`dry=26/26`, `direct=26/26`, `live=26/26` on fresh temporary backend `:8014`).
PRD-047.5 completed planner quality calibration over live dialogue answer-fit groups and hardened Writer compliance for planner policies (`question/practice/revoicing/shape`), with refreshed artifacts (`dry=26/26`, `direct=26/26`, `live=26/26` on fresh temporary backend `:8013`).
PRD-047.4 added `Response Planner v1` as deterministic next-meaningful-move layer between Active Line and WriterContract, with trace/API/admin visibility and reproducible calibration artifacts (`dry=14/14`, `direct=14/14`, `live=14/14` on fresh temporary backend `:8012`).
PRD-047.0-HF1 closed evaluator false positives by enforcing final-answer compliance for known-concept routing and practice-gate behavior. Failure baseline artifacts are refreshed with honest answer-level validation (`direct=5/5`, `live=skipped` on stale backend). Diagnostic Center v1 remains in governed creator/developer-local boundary; broad rollout remains prohibited and `production_ready=false`.
PRD-047.1 introduced `NEO Philosophy Kernel` + `Writer Freedom Contract v1` as an always-on internal lens layer for Writer, with runtime/admin visibility and trace-safe metadata blocks (no raw source quote dumping).
PRD-047.2 calibrated kernel answer quality with reproducible `12`-case dataset/runner, added prompt compactness budget gates, and synced runtime/admin visibility for quality calibration status (`direct=12/12`, `live=skipped` honestly on stale backend).
PRD-047.3 added `Active Line / Dialogue Continuity v1` as deterministic continuity layer (intent, continuity mode, repair mode, revoicing/practice suppression) with trace + admin effective visibility and reproducible dry/direct/live runner artifacts (`dry=10/10`, `direct=10/10`, `live=10/10` on fresh temporary backend `:8011`).
## Current Runtime Architecture
User path remains unchanged: State Analyzer -> Thread Manager -> Context Assembly -> Diagnostic Card -> Diagnostic Center shadow/limited governance layers -> Writer.

## Diagnostic Center Acceptance State
`PRD-046.1.28` accepted provider-backed phase as governed limited-runtime candidate.
Boundary flags remain strict: `broad_rollout_allowed=false`, `production_ready=false`, `normal_user_activation_allowed=false`.
Admin control surface is available via `GET/POST /api/admin/diagnostic-center/*` and mirrored `v1` routes.
`developer_local_all_users` is available for single-developer local governance only and is not production rollout.

## Current Knowledge Base State
Focus source remains `123__кузница_духа`; governed blocks/chroma integrity is preserved by no-mutation policy and explicit gates.

## Current Context / Memory State
Context assembly + additive summaries remain active; deterministic fallback stays mandatory when async summaries are unavailable or invalid.

## Stable Modules
- Multiagent orchestrator and writer compliance chain.
- Diagnostic Center shadow and constrained prompt-constraint stack.
- BotDB registry/query/admin stability gates.
- Artifact encoding hygiene and no-mutation proof flows.

## Permanent Gates
- Final runtime governance acceptance gates.
- Provider-backed evidence and normal-user no-effect gates.
- Rollback/hard-stop, safety/KB boundary, trace sanitization gates.
- BotDB stability, response quality eval/calibration, contract and no-mutation gates.

## Known Risks
- Broad rollout without separate PRD would violate governance boundaries.
- Cleanup/deletion without manifest approval can break reproducibility.
- Historical artifact encoding noise may be misread as current runtime corruption without normalization report.

## Next Planned PRD
`PRD-047.11 — Contextual Dialogue Pragmatics / Repair & Summary Calibration v1`
## Do Not Do Yet
- Do not activate broad Diagnostic Center runtime authority.
- Do not enable normal-user activation.
- Do not mutate KB governance authority fields (`chunk_type`, `allowed_use`, `safety_flags`).
- Do not perform Chroma reindex as part of this cleanup PRD.

## Documentation Update Rule
1. Update this file for every stage/runtime boundary PRD.
2. Update roadmap for sequencing changes.
3. Update decisions for architecture boundary changes.
4. Update PRD index after each merged PRD cycle.
5. Keep full historical details in `TO_DO_LIST`, keep docs operational and compact.

## Last Updated
- Date: 2026-06-01
- Source cycle: PRD-047.10-HF1

## PRD-046.1.35-HF4
Current Stage:
PRD-046.1.35-HF4 calibrated creator-live response behavior: example/explanation requests no longer trigger regulate_first by default, practice rejection suppresses body-action suggestions, and Web Trace displays non-empty safe Writer chunk previews.
Next:
PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1.

## HF4 Delivery Metadata
- prd_id: PRD-046.1.35-HF4
- commit_hash: 3a3c6a32a0c29551440432c0a266ab7cbab25b20
- push_status: pushed_to_origin_main

## PRD-046.1.36 Delivery Metadata
- prd_id: PRD-046.1.36
- commit_hash: 14a04164059dfff8b9b8e625cb1f3f1578e0d57b
- push_status: pushed_to_origin_main

## PRD-046.1.37 Delivery Metadata
- prd_id: PRD-046.1.37
- commit_hash: ff77155
- push_status: pushed_to_origin_main

## Diagnostic Center Track Status
Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE
