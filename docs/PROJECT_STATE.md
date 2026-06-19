# Project State - Bot Psychologist / Neo MindBot

## Current Stage
PRD-047.27 completed the minimal DB-track semantic chunk cards pilot as a bounded, advisory-only Writer grounding layer with `passed_with_warning` status. A local/dev/test-only `semantic_cards_pilot_v1` pack now feeds 1-3 compact semantic cards into the existing `writer_kb_payload_v1` path without changing retrieval authority, Chroma, registry, processed blocks, DB schema, or Writer authorship. Live pilot evidence is explicit: `semantic_card_selected_when_expected_count=5`, `semantic_card_suppressed_when_not_needed_count=2`, `direct_answer_success_rate=1.0`, `card_internal_leak_count=0`, `raw_source_dump_count=0`, `practice_overpush_count=0`. The only honest warning is one overly textbook answer (`SCP-005`), so the next recommended step is `PRD-047.28 - Live Interactive Pilot / Owner Dialogue Review v1`, not broader runtime authority or DB mutation.
PRD-047.26-HF1 completed the targeted route/obligation/evaluator repair on top of the PRD-047.26 live triage baseline and is now the current top-stage evidence layer with `passed_with_warning` status. The runtime/evidence path stayed trustworthy: `source_gate=passed`, `dry_run=passed`, `live_cases=12/12`, `overlay_apply_detected_count=0`, `internal_leak_count=0`, `raw_kb_dump_count=0`, `unsafe_practice_count=0`, `diagnostic_overclaim_count=0`, and `trace_missing_evidence_count=0`. The repaired counters are explicit: `direct_answer_success_rate=1.0`, `overlay_false_positive_count=8`, `dialogue_act_error_count=0`, `answer_obligation_error_count=0`, `writer_style_regression_count=0`, `evaluator_false_pass_count=0`, so DB-track moved from `not_ready` to `ready_with_warning`. The remaining blocker class is no longer answer routing; it is overlay shadow noise only. The next recommended step is `PRD-047.26-HF2 - Overlay Shadow Noise Reduction / Evidence Repair v1`, and DB metadata expansion stays deferred until that warning is reduced.
PRD-047.25 collected live evidence for the cleaned retrieval baseline plus `overlay_shadow_trace` and `writer_kb_payload_v1`, and it is the new top-stage baseline with `passed_with_warning` status. The active local runtime remains singular (`multiagent_adapter`), `current_turn_focus_v1` stays primary for retrieval query assembly, and `writer_kb_payload_v1` stays canonical for KB delivery with `kb_payload_primary_rate=1.0`, `current_turn_focus_clean_rate=1.0`, `legacy_query_builder_primary_count=0`, `overlay_apply_detected_count=0`, and no internal payload leakage or raw KB dump in final answers. The bounded warning is now explicit and evidence-backed: overlay remains trace-only and non-authoritative, but live evidence shows `overlay_false_positive_count=6`, so the next recommended step is `PRD-047.26 - Overlay Shadow Noise Reduction / Evidence Repair v1`, not overlay graduation or authority expansion.
PRD-047.24 closed the retrieval query assembly pollution/duplication class with accepted `passed_with_warning` status and is the current top-stage baseline. The runtime now uses `current_turn_focus_v1` query assembly by default for local/dev/pilot/test surfaces, blocks naive previous-question concatenation for standalone knowledge asks, permits compact inherited-topic context only for genuine elliptical follow-ups, collapses duplicate fragments, avoids mid-word truncation, and exposes `retrieval_query_build_trace_v1` in runtime/debug/API/Web Trace. Live repair evidence shows Q24-002 no longer carries the stale self-realization query, Q24-003 no longer duplicates/truncates mid-word, retrieval relevance is no longer `missing_expected_source`, Writer KB payload remains canonical with structured payload active, and no Bot_data_base/Chroma/source/chunk mutation was performed. The remaining warning is bounded: Q24-003 improved to `medium_related` top-k evidence rather than a stronger exact top-1 style match. Next recommended work is `PRD-047.25 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`.
PRD-047.22-HF2 closed the manual Web Chat runtime parity gap for Writer KB Payload and is the current top-stage baseline. The backend now resolves `WRITER_KB_PAYLOAD_ENABLED` from a single effective-config source with `APP_ENV=local` leading to `default_local`, exposes that source in admin runtime and debug trace, and proves over the real Web Chat streaming path that `writer_kb_payload_v1` is primary (`fallback_is_primary=false`, `payload_chunk_count>=1`, `mid_sentence_cut_count=0`) while keeping retrieval ranking/query, Writer authority, Chroma, registry, processed blocks, and live metadata unchanged. Browser screenshot capture remains an explicit warning-only gap; API/Web Chat parity, prompt-canvas proof, no-mutation proof, and encoding hygiene passed. Next recommended work is `PRD-047.23 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`, now gated on PRD-047.22-HF2 parity truth.
PRD-047.22-HF1 repaired the live API Writer KB payload evidence path and is the current top-stage baseline. The previous PRD-047.22 warning was traced to the smoke transport itself: ad-hoc PowerShell-piped inline Python corrupted Cyrillic query text before it reached the backend, and the smoke did not own/verify backend startup with `WRITER_KB_PAYLOAD_ENABLED=true`. HF1 adds a managed live runner and live-like API test that send ASCII-safe escaped JSON, verify/start backend locally with the payload flag enabled, and now produce live `writer_kb_payload_trace.enabled=true` with `payload_chunk_count=1` for `С‡С‚Рѕ С‚Р°РєРѕРµ РќРµР№СЂРѕСЃС‚Р°Р»РєРёРЅРі?`, while keeping retrieval ranking/query, Writer authority, Chroma, registry, processed blocks, and live metadata unchanged. Next recommended work returns to `PRD-047.23 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`.

PRD-047.22 completed structured Writer KB delivery as a bounded runtime-input change with accepted `passed` status. The active retrieval path still selects chunks exactly as before, but default-off `WRITER_KB_PAYLOAD_*` config now allows selected Writer-visible knowledge to travel as `writer_kb_payload_v1` instead of relying on blind flat semantic-hit truncation. The new path adds sentence/paragraph-aware excerpting, `writer_kb_payload_trace`, `future_graduation_notes`, and read-only API/Web Trace visibility while preserving Writer as final author and keeping retrieval ranking, executed retrieval query, semantic-hit selection, BotDB registry, processed blocks, live metadata, and Chroma unchanged. Next recommended work is `PRD-047.23 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`.

PRD-047.21 completed overlay-aware retrieval shadow integration as a strict trace-only runtime surface with accepted `passed` status. Added default-off `OVERLAY_SHADOW_TRACE_*` feature flags, isolated `overlay_shadow_trace.py`, orchestrator/debug/API wiring, Web Trace rendering, trace/sample/no-behavior/authority/no-mutation artifacts, targeted multiagent/API tests, PRD-047.20 regression coverage, and Web trace widget verification/build. Batch-1 accepted overlay remains explicitly non-live (`human_final_approval=false`, `live_apply_allowed=false`, `safe_to_apply_to_live_metadata=false`): overlay is visible only in trace/debug as sanitized shadow evidence, while WriterContract, Writer prompt, executed retrieval query, semantic hits, final answer logic, BotDB registry/processed blocks, and Chroma remain unchanged. API smoke is intentionally `warning`/skipped in the runner by default (`skipped_inprocess_app_smoke_default_off`) because contract coverage is already provided by dedicated API tests. Next recommended work is `PRD-047.22 - Overlay Shadow Allowlisted Live Evidence / Trace Review v1`.

PRD-047.20 completed the first real curated overlay batch and offline retrieval evaluation without changing runtime behavior. Added batch-1 selection over `16` real PRD-047.18 queue candidates, an evaluation-only decisions pack (`12` accepted overlay items, `139` accepted fields), accepted-overlay preview, PRD-047.19-based dry-run apply/preflight wrapper, and retrieval shadow evaluation over `18` curated cases. The overlay remains explicitly non-live: `human_final_approval=false`, `evaluation_only=true`, `live_apply_allowed=false`, `ready_for_live_apply=false`, while `ready_for_eval_over_real_overlay=true` is now supported for offline evidence. Read-only BotDB smoke passed on `:8003`; retrieval eval passed with `overlay_shadow_hit_rate=0.7778`, `combined_expected_help_rate=0.7778`, `unsafe_overlay_hit_count=0`, and `practice_without_safety_count=0`. No Writer/runtime/Admin/Web/registry/processed-block/Chroma mutation was performed. Next recommended work is `PRD-047.21 - Overlay-Aware Retrieval Shadow Integration / Trace-Only v1`.

PRD-047.19-HF1 repaired acceptance evidence integrity for PRD-047.19 without changing functionality. The hotfix reran the PRD-047.18, PRD-047.17, and PRD-047.19 regression subsets with repository-local `--basetemp` and local `TEMP/TMP`, eliminating the false `C:\Users\video\AppData\Local\Temp\pytest-of-video` `PermissionError` failures from the original command log. HF1 also regenerated `test_command_output.txt` as clean UTF-8, restored `replacement_char_warning_count=0`, added explicit source-gate / rerun-summary / no-mutation evidence, and left Writer, runtime, live metadata, Chroma, processed blocks, and registry untouched. Next recommended work remains `PRD-047.20 - Real Human Curated Overlay Batch 1 / Accepted Decisions Pack v1`.

PRD-047.19 completed curated candidate dry-run apply preflight with accepted `passed_with_expected_blockers` status. Added `mechanism_metadata_overlay_intake_report_v1`, `mechanism_metadata_dry_run_apply_plan_v1`, `mechanism_metadata_apply_preflight_v1`, future field-apply mapping, negative overlay fixtures, anti-runtime-activation proof, read-only BotDB smoke, and no-mutation/encoding artifacts over the PRD-047.18 fixture overlay. The project can now explain candidate/block consistency, future metadata targets, and diff previews under `overlay_only_no_write`, but it still honestly reports `ready_for_live_apply=false` and `ready_for_eval_over_real_overlay=false` because the current overlay is fixture-only and contains no real human-reviewed accepted decisions. No processed blocks, live metadata, Chroma, retrieval, Writer prompt, or runtime behavior were changed. Next recommended work is `PRD-047.20 - Real Human Curated Overlay Batch 1 / Accepted Decisions Pack v1`.

PRD-047.18 completed manual review / curated candidate acceptance workflow with accepted `passed` implementation status. Added `mechanism_metadata_review_decision_v1`, `mechanism_metadata_review_queue_v1`, `mechanism_metadata_curated_overlay_preview_v1`, offline decision validation, fixture-only curated overlay preview, and a dedicated review runner over the `80` real PRD-047.17 candidates. The workflow now produces a governed review queue, all-pending decision template, validation report, curated overlay preview, curation status report, anti-runtime-activation proof, read-only BotDB smoke, and no-mutation/encoding artifacts. Real candidates still remain preview-only: `live_apply_allowed=false`, `safe_to_apply_to_live_metadata=false`, no Writer/runtime behavior changed, Chroma was not reindexed, and DB/live metadata were not mutated. Next recommended work is `PRD-047.19 - Curated Candidate Dry-Run Apply Plan / Preflight over Accepted Overlay v1`.

PRD-047.17 completed offline enrichment candidate generation over the real Kuznica source with accepted `passed` status. Added `mechanism_metadata_enrichment_candidate_v1`, a deterministic offline enrichment runner over `123__???????_????`, source-profile and chapter-coverage reports, manual-review pack, anti-runtime-activation proof, and encoding/no-mutation artifacts. The run selected `80` real blocks out of `247` and produced `80` manual-review candidates across `practice`, `diagnostic_lens`, `source_fragment`, `mechanism`, `concept`, `case_example`, `safety`, and `style_voice`. Candidates are explicitly not applied to live metadata, Writer/runtime behavior is unchanged, Chroma was not reindexed, DB was not mutated, and LLM-candidate mode remains deferred/skipped behind explicit confirmation and safe configuration. Next recommended work is `PRD-047.18 - Manual Review / Curated Candidate Acceptance Workflow v1`.

PRD-047.16 completed mechanism-aware knowledge base preparation / chunk metadata foundation with accepted `passed` implementation status and read-only audit evidence. Added `MechanismAwareChunkMetadata v1` in the existing `Bot_data_base/knowledge_governance` layer, a backward-compatible adapter from legacy governed blocks, and a dry-run audit runner over fixture plus real local BotDB blocks. The new metadata is explicitly semantic guidance only: Writer remains the sole author of user-facing text, runtime answer behavior is unchanged, and no new metadata was activated in the live Writer path. Chroma was not reindexed, DB schema was not mutated, and no new runtime path or LLM enrichment agent was added. Real-sample audit checked `54` chunks (`50` real + `4` fixture) and passed structurally while surfacing quality warnings for incomplete mechanism/practice metadata. Next recommended work is `PRD-047.18 - Manual Review / Curated Candidate Acceptance Workflow v1`.

PRD-047.15-HF2-R1 completed Hybrid Retrieval Planner / Query-Before-RAG with accepted `passed` status. Added `hybrid_retrieval_planner_v1_r1` as a metadata-only planner in the existing multiagent runtime: deterministic universal gates cover simple greeting/thanks/summary/formatting/reject/support cases, optional strict-JSON LLM planning is reserved for complex low-confidence cases, and approved retrieval metadata now reaches `MemoryRetrievalAgent` before RAG execution. Trace/debug/API now expose planned vs executed query, query-before-RAG proof, planner validity/fallback, planner mode, needed chunk types, and mechanism hints while Writer remains the sole final answer author. Direct acceptance passed `16/16`; live acceptance passed `6/6` after restarting the live backend on `:8001` with `HYBRID_RETRIEVAL_PLANNER_MODE=apply`; anti-overengineering, encoding, and no-mutation gates passed; no DB/KB/frontend mutation or new runtime path was added. User-owned documentation updates under `bot_psychologist/docs/**` and `TO_DO_LIST/context/**` were included in the main push as requested. Next recommended work is `Backend в†” Web Admin в†” Web Trace Sync`, with `PRD-047.16` deferred behind that visibility follow-up.

PRD-047.15-HF1 completed Contextual Retrieval Composer Live Calibration / Owner Trace Review with warning status and no runtime mutation. HF1 generated a 40-case replay library, composer trace schema, replay trace review, owner review sheet, live trace inventory, LLM/hybrid decision brief, runtime-scope proof, encoding gate, acceptance artifact, and tests. Automated blocker gates passed (`literal_short_reply_query_count=0`, `summary_external_kb_leak_count=0`, `no_stub_violations_count=0`, tests passed), while mixed/low-confidence cases produced evidence for future hybrid assistance. Owner scores are intentionally pending; Writer remains final answer author, no LLM calls or new runtime path were added. Next recommended PRD is `PRD-047.15-HF1.1 - Owner Trace Review Completion / Calibration Decisions v1`, with `PRD-047.15-HF2 - Hybrid LLM-Assisted Query Composer Experiment v1` as the evidence-backed follow-up if owner review confirms the automated findings.

PRD-047.15 completed Contextual Retrieval Query Composer v1 with warning status. Added deterministic internal `contextual_retrieval_query_composer_v1` plus `retrieval_query_contract.py`: the composer builds retrieval need/action/query from dialogue context, last assistant offer, dialogue act, answer obligation, final directive, planner signals, and knowledge need instead of blindly relying on the current user utterance. Short confirmations can inherit the previous offer topic; summary requests default to `use_current_context_only`; greeting/close/support/one-step turns suppress RAG; knowledge and practice overview questions compose compact KB queries. The composer is visible in `retrieval_decision`, `writer_context_package_v1`, `WriterContract.to_prompt_context`, and debug trace. It is deterministic, does not create user-facing text, does not add an LLM agent, and does not mutate DB/KB/frontend. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.15/`; validation/runtime-scope/encoding/no-stub composer scan passed. Warning remains for deterministic-v1 live calibration and HF1.2 out-of-scope static/advisory candidates. Next recommended PRD is `PRD-047.15-HF1 - Contextual Retrieval Composer Live Calibration / Owner Trace Review v1`.

PRD-047.14-HF2 completed summary request routing / answer obligation repair with warning status. Explicit current-conversation summary requests now route as `dialogue_act=summary_request`, outrank open last-offer confirmation, resolve to `answer_obligation=summarize_current_conversation`, and expose `summary_request`, `summary_scope=current_conversation`, `no_confirmation_needed`, and `no_practice_unless_requested` through `final_answer_directive_v1` / WriterContract. Writer no longer injects a canned summary; bad summary attempts are handled by `final_answer_acceptance_gate_v1` as retry/quarantine signals (`summary_request_reconfirmed_instead_of_answered`, `summary_answered_last_offer_instead`, `summary_answer_lacks_conversation_context`). Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF2/`; validation, runtime scope, encoding, and no-stub summary scan passed. Warning remains only because HF1.2 out-of-scope static/advisory candidates are intentionally not part of this HF2 scope. Next recommended PRD is `PRD-047.15 - Contextual Retrieval Query Composer Agent v1`.

PRD-047.14-HF1.2 completed targeted no-stub runtime repair with warning status: high-confidence Writer static repair/knowledge/direct-answer returns were converted to `no_stub_repair_signal_v1` and existing final-answer gate retry/quarantine semantics instead of canned replacement answers. Writer target blockers moved `31 -> 0`; total blocker inventory moved `55 -> 24`; no new user-facing stub was created; runtime mutation scope, encoding gate, and tests passed. Remaining candidates are out-of-scope/advisory/safety-minimal or summary-routing debt and are tracked for later PRDs. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF1.2/`; the next repair path returns to `PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1`.

PRD-047.14-HF1.1 completed as an audit-only no-stub boundary inventory with no runtime mutation. The audit tool inventoried hardcoded user-facing reply candidates across active runtime paths, classified all candidates, and produced an honest `blocker` result: 55 `blocker_stub_user_facing` candidates and 41 `warning_needs_targeted_refactor` candidates remain, with `unknown_active_candidates_count=0`, `runtime_mutation_status=passed`, `encoding_gate_status=passed`, and guard regression tests passed. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF1.1/`; the next repair path is `PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1`.

PRD-047.14-HF1 passed as a targeted hotfix after the PRD-047.14 blocker audit. Active hardcoded template-family fallback was removed from `concrete_answer_fit.py`; `template_family_guard_v1` now detects exact/fuzzy leakage in the existing final-answer acceptance gate, triggers retry/quarantine semantics, and prevents contaminated answers from becoming healthy memory, summary source, or last assistant offer. Writer call sites now defer problematic drafts to the existing gate instead of generating a canned replacement answer. No new runtime path, no new LLM agent, no prompt philosophy overhaul, no KB/Chroma/governance mutation, and no rollout flag changes were introduced. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF1/`.

PRD-047.14 completed as an audit-only blocker cycle, not a runtime repair. The audit found active template-family leakage in `bot_psychologist/bot_agent/multiagent/concrete_answer_fit.py` and static summary/recap routing risk (`summary_request` has no dedicated answer-obligation route while `confirmation_to_last_offer` risk is present). No Writer, Orchestrator, prompts, policy, RAG/Chroma, Admin API, Web UI runtime, KB/governance, or database files were changed. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14/`; the next repair path is `PRD-047.14-HF1 - Template Leakage Quarantine / Summary Contamination Guard v1`.

PRD-047.13-HF1 completed cleanup closure after PRD-047.13: active docs contradictions, misleading legacy labels, active empty artifacts, active duplicate docs, and unknown current docs are closed with no runtime mutation. PRD-047.13 completed as the cleanup-only inventory and docs truth-sync step. It inventoried docs, reports, logs, admin surfaces, legacy terms, empty artifacts, and encoding/corruption candidates after the accepted PRD-047.12-HF1 baseline, without changing Writer, Orchestrator, Final Answer Acceptance Gate, Stale Stub Detector, Dialogue Act Resolver, RAG/Chroma, Diagnostic Center authority, or prompt/runtime behavior.

PRD-047.12-HF1 is accepted as the current engineering baseline: `final_answer_acceptance_gate_v1` runs after Writer/Validator, failed/stale final answers are quarantined before unanswered-question closure, healthy context memory, and last-offer seeding, and Admin Runtime exposes gate capability. Web Chat markdown rendering uses the existing `ReactMarkdown` path with stronger real assistant bubble styling. Required live/browser/encoding/no-mutation artifacts passed under `TO_DO_LIST/logs/PRD-047.12-HF1/`.

Current rollout boundary remains unchanged: `production_ready=false`, `broad_rollout_allowed=false`, and `normal_user_activation_allowed=false`. Next planned quality work is `Backend в†” Web Admin в†” Web Trace Sync`.

PRD-047.12 completed as a passed unification cycle: `unified_dialogue_policy_v2` now owns preset resolution (`safe_guided`, `free_dialogue_default`, `mvp_free_dialogue` alias), dialogue-act / last-offer / unanswered-question / style-state / answer-obligation layers are wired through the single multiagent runtime, Writer-first prompt assembly exposes one effective control/context contract, Admin Runtime shows unified policy/resolver state, and the dedicated PRD-047.12 acceptance runner finished `dry=passed`, `direct=passed`, `live=passed`, `browser=passed`, `admin_surface=passed`. Artifacts live under `TO_DO_LIST/logs/PRD-047.12/`; no new runtime path, no new LLM agent, and no governance-authority mutation were introduced.
PRD-047.11-HF3 completed as a residual reality-repair cycle on top of HF2: concrete situation answers no longer fall back to the formula stub `РЎРµР№С‡Р°СЃ РїРѕР»РµР·РЅРµРµ РЅРµ СѓРїСЂР°Р¶РЅРµРЅРёРµ...` in MVP cases that need a contextual explanation, bare gratitude turns keep deterministic `intent=contact` and `nervous_state=window`, real localhost Web Chat/Admin proof moved back to `localhost:3000`, and HF3 artifacts now capture source inventory, HF2 audit, reset/memory proof, browser/admin snapshots, live cases, and encoding hygiene under `TO_DO_LIST/logs/PRD-047.11-HF3/`. HF3 remains a local stabilization hotfix, not a rollout PRD; Diagnostic Center/Planner/Active Line remain advisory-only, and production readiness is still not claimed.
PRD-047.11-HF2 completed as a passed runtime/frontend repair: fresh chats now start under `fresh_chat_context_policy_v1`, Writer receives RAG only through `writer_context_package_v1`, greeting/repair turns no longer inherit stale mechanism context, current-chat reset and dev-only user-memory clear controls are explicit, and real browser/Admin proof passed on isolated live runtime (`8002/3001`). Required HF2 artifacts are stored in `TO_DO_LIST/logs/PRD-047.11-HF2/`, with `live_cases_passed=true`, `memory_controls_passed=true`, `markdown_browser_passed=true`, and `admin_screenshots_passed=true`.
PRD-047.11-HF1 completed as a passed writer-prompt-diet repair: `mvp_free_dialogue` now keeps `FINAL ANSWER DIRECTIVE` writer-visible while collapsing legacy diagnostic/planner/active-line command pressure into a sanitized advisory summary, rewriting practice suppression to `no_exercise_but_answer_normally`, preserving raw observability in trace/admin, and removing stale runtime fallback phrases. Required HF1 artifacts are stored in `TO_DO_LIST/logs/PRD-047.11-HF1/`, with `writer_prompt_diet_eval=4/4 passed`.
PRD-047.11-AUDIT completed as a warning-grade evidence audit, not a pass: `TO_DO_LIST/logs/PRD-047.11-AUDIT/` now contains the dedicated runner output, source inventory, prompt/acceptance audits, live case matrix, raw traces, and no-mutation proof, but live evidence still shows `14/18` failed cases, `15` bad-phrase hits, missing browser screenshot proof, and incomplete admin configurability proof. The next recommended repair path is `PRD-047.11-HF1`, while Diagnostic Center remains advisory-only and production readiness is explicitly not claimed.
PRD-047.11 passed full Writer-first consolidation acceptance: `final_answer_directive_v1`, MVP prompt assembly cleanup, legacy-constraint suppression metadata, stale-stub detector, admin/runtime/UI exposure, live evidence enrichment, strict dry/direct/live runner, and real Web Chat markdown smoke are all green in final artifacts.
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
Focus source remains `123__РєСѓР·РЅРёС†Р°_РґСѓС…Р°`; governed blocks/chroma integrity is preserved by no-mutation policy and explicit gates.

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
`PRD-047.28 - Live Interactive Pilot / Owner Dialogue Review v1`

## PRD-047.23 Audit State
PRD-047.23 closed the evidence gap between Bot_data_base chunks, retrieval query assembly, Writer KB payload, and Web Trace preview.
Stored/source evidence does not support a primary Bot_data_base chunk-boundary defect for the observed Neurostalking case; the suspicious `...изнутри чего т` cut is downstream from stored content and aligns with preview/full-content ambiguity in the uploaded trace.
The dominant failure class is current-turn retrieval query pollution/duplication for the "Программа несовершенное Я" and "Пять драйверов" cases, with secondary trace-schema mismatch where Web Trace chunk counters can diverge from actual writer payload counters.

## HF2-R2 Runtime Visibility State
Hybrid Retrieval Planner visibility is now synchronized across backend admin runtime, Web Admin Runtime, multiagent trace, and compact trace summary.
Advanced Controls is compatibility-only; duplicate legacy sub-tabs are no longer presented as primary control centers.
Knowledge Graph runtime flag remains backend-legacy/optional but is shown as compatibility status instead of a modern primary Runtime toggle.
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
2026-06-19
- Date: 2026-06-05
- Source cycle: PRD-047.12
- Source cycle: PRD-047.11-HF3
- Source cycle: PRD-047.11-HF2
- Source cycle: PRD-047.11-HF1
- Source cycle: PRD-047.11-AUDIT
- Source cycle: PRD-047.10-HF2
- Source cycle: PRD-047.11

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

## PRD-047.15-HF2-R2 Delivery Metadata
- prd_id: PRD-047.15-HF2-R2
- commit_hash: 3480666
- push_status: pushed_to_origin_main

## PRD-047.23 Delivery Metadata
- prd_id: PRD-047.23
- commit_hash: 4f70dc4
- push_status: pushed_to_origin_main

## PRD-047.24 Delivery Metadata
- prd_id: PRD-047.24
- commit_hash: 47693c2
- push_status: pushed_to_origin_main

## PRD-047.25 Delivery Metadata
- prd_id: PRD-047.25
- commit_hash: e1b0fb5
- push_status: pushed_to_origin_main

## PRD-047.26 Delivery Metadata
- prd_id: PRD-047.26
- commit_hash: da2e8f5
- push_status: pushed_to_origin_main

## Diagnostic Center Track Status
Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE


## PRD-047.26-HF1 Delivery Metadata
- prd_id: PRD-047.26-HF1
- commit_hash: e131358
- push_status: pushed_to_origin_main

## PRD-047.27 Delivery Metadata
- prd_id: PRD-047.27
- commit_hash: 6ad266b
- push_status: pushed_to_origin_main

## PRD-047.27-HF1 Delivery Metadata
- prd_id: PRD-047.27-HF1
- commit_hash: 74cb113
- push_status: pushed_to_origin_main

## PRD-047.27-HF2 Delivery Metadata
- prd_id: PRD-047.27-HF2
- commit_hash: pending_main_commit
- push_status: pending
