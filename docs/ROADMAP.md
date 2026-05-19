# Roadmap

## Done
- PRD-045.x: foundation runtime quality chain (multiagent contracts, context assembly baseline, diagnostic card and writer compliance alignment).
- PRD-045.6.3: async turn LLM summary store integrated with deterministic fallback and context assembly trace reasons.
- PRD-045.6.3-HF1: acceptance completion (eval>=5, validator safety guards, processor pending->ready evidence).
- PRD-046.0..046.0.4.x: knowledge governance, Chroma recovery, governed reindex and API query restore.
- PRD-046.0.5 + HF1 + RUN1 + HF2 + HF3: offline/real LLM enrichment pipeline calibrated to production-candidate quality on controlled batch.
- PRD-046.0.5-APPLY1: controlled apply overlay + Chroma refresh + API/bot enrichment retrieval smoke.
- PRD-046.0.6: retrieval eval dataset + deterministic runner + scorecard + weak-case queue (safety gap found).
- PRD-046.0.6-HF1: retrieval governance safety fix; internal_only leakage closed (`4 -> 0`) with unchanged eval dataset.
- PRD-046.0.7: admin review workflow v1 delivered (sanitized review queue + decision contract validation, no KB mutation).
- PRD-046.0.7-HF1: source hygiene/readiness layer delivered; legacy SD decommissioned from BotDB admin/API active path; readiness gate reports blocker `multiple_active_sources_without_allowlist`.
- PRD-046.0.7-HF2: blocker fix delivered; controlled archive apply completed, `active_source_count=1`, readiness gate switched to `ready` for clean reprocess.
- PRD-046.0.8: clean source reprocess executed in candidate-only mode; production data unchanged; gate result `candidate_needs_governance_calibration`.
- PRD-046.0.8-HF1: candidate practice taxonomy/governance calibration delivered; `direct_practice_misclassified_count=0`, `unsafe_practice_suggestion_count=0`, gate remains `candidate_needs_governance_calibration` due non-critical mixed-intent warnings.
- PRD-046.0.8-HF2: remaining mixed-intent warnings calibrated (`2 -> 0` unresolved), governance gate `passed`, `candidate_ready_for_apply=true`, production remains unchanged.
- PRD-046.0.8.1: controlled apply completed (`all_blocks_merged/registry 229 -> 247`), Chroma reindexed to `247`, post-apply consistency/quality/retrieval gates regenerated; legacy review queue marked stale and new baseline queue rebuilt.
- PRD-046.0.9: post-reprocess enrichment/review rebaseline completed in candidate mode (no apply/reindex); generated fresh inventory/overlay/validation/review queue/scorecard/retrieval preview for current 247 block ids.
- PRD-046.0.9-RUN1-HF1: BotDB Admin dashboard summary contract restored (`/api/dashboard/`), enrichment/review visibility returned, explicit warning/error surfacing added, no production mutations.
- PRD-046.0.9-RUN1-HF2: runtime dashboard acceptance fix (cache-busting + `/api/dashboard` slash/no-slash + production-block semantics), registry delete hygiene policy alignment (UI/backend + snapshot-before-delete), Writer KB snippet boundary guard (no mid-word Cyrillic clipping).
- PRD-046.0.9-RUN1-HF3: registry runtime render fix delivered (row-level isolation + safe Chroma source-exists fallback + explicit registry loading/error/empty UI states), admin consistency gate passed (`Dashboard/Registry/Chroma = 247`, review queue `87`).
- PRD-046.0.9.1: human review decisions layer delivered for fresh RUN1 queue (prepare/workbench/template/validator/no-mutation artifacts + tests), production KB/registry/Chroma unchanged; apply step blocked until queue/block-id alignment is restored in current workspace snapshot.
- PRD-046.0.9.1-HF1: blocks snapshot alignment restored (`229 -> 247`) via authoritative candidate audit + staged restore with backups; strict `--require-aligned` gate added; rerun confirms queue coverage `87/87`.
- PRD-046.0.9.2: architect semantic review preparation delivered (sanitized batches for all `87` aligned items, architect decisions template/overlay, overlay validator with coverage/apply-ready flags, no-mutation proof); mode A completed with `ready_for_architect_review=true`, `apply_ready=false`.
- PRD-046.0.9.3: review automation policy delivered; conservative auto-decisions generated for all `87` items (`approved/needs_edit/rejected/defer` mix), validation passed (`coverage=100%`, `apply_ready=true`), official overlay updated, no production mutation and no Chroma reindex.
- PRD-046.0.7.1: controlled review decision apply completed; validated RUN1 enrichment + architect auto-decisions applied to production advisory metadata (`updated_blocks=200`) with backups, no-authority-mutation proof, retrieval/admin smoke, no Chroma reindex.
- PRD-046.0.7.2: post-apply quality gate delivered (`post_apply_quality_gate.py` + CLI + tests + artifacts); data/apply-route/retrieval/writer gates passed with strict no-mutation proof, final status `done_with_admin_api_blocker` because admin API runtime was unreachable.
- PRD-046.0.7.2-HF1: admin live smoke/launch gate delivered (`admin_live_smoke.py` + `run_admin_live_smoke.py` + tests/artifacts); canonical launch command detected, subprocess startup attempted, final status `done_with_admin_launch_blocker` due readiness timeout and unreachable live endpoints; production hashes unchanged.
- PRD-046.0.7.2-HF2: admin launch/schema hotfix closure delivered (`run_admin_live_smoke_hf2.py` + external-existing runtime path), all required endpoints reached on live backend, schema/quality/no-mutation gates passed, final status `passed` without production apply/reindex.
- PRD-046.0.7.2-HF3: strict dashboard/chroma reconciliation gate delivered (`run_admin_live_smoke_hf3.py` + strict contract tests); stale historical proof override removed, live `chroma.count=229` mismatch preserved as blocker (`done_with_chroma_count_blocker`), no production mutation/reindex/provider call.
- PRD-046.0.7.2-HF4: Chroma recovery cycle completed; direct diagnostic confirmed real mismatch (`229`), controlled focus-only reindex with backup restored direct count (`247`), dashboard count source corrected (`ChromaManager.get_stats` uses `collection.count()`), strict live gate passed (`247/247/247`) with no `all_blocks_merged`/`registry` mutation.
- PRD-046.0.10: legacy SD cleanup/docs alignment completed; SD labeling disabled by default with explicit legacy gate only, dashboard readiness detached from SD, BotDB README and new internal docs pack (`Bot_data_base/docs/*`) aligned to live `:8003` runtime and focus-source `247/247/247`.
- PRD-046.0.10-HF1: SD config/encoding finalization completed; canonical config fixed to default-disabled (`sd_labeling.enabled=false`), env overrides no longer persist back into `config.yaml`, UTF-8 runtime smoke artifacts and anti-mojibake gate added, runtime/no-mutation invariants preserved.
- PRD-046.0.11: final runtime readiness summary completed; live runtime/admin gates (`:8003`) revalidated, KB/chroma focus-source consistency reconfirmed (`1 / 247 / 247 / 247`), retrieval/governance/legacy-SD/UTF-8/docs gates passed, no-mutation proof captured, Diagnostic Center prerequisites confirmed.
- PRD-046.1: Diagnostic Center v1 readiness architecture layer delivered (strict contracts, deterministic dry-run builder, 10 golden/eval cases, contract audit runner, no-mutation proof, ADR-030); final status passed, runtime activation remained disabled.
- PRD-046.1.1: Diagnostic Center v1 runtime shadow mode delivered (trace-only adapter + divergence metrics + orchestrator debug integration + shadow eval runner), shadow gates passed (`10/10`, `safety_match=1.0`, `kb_violations=0`, `user_path_effect=0`, `runtime_smoke_ok=true`) with no mutation and no writer/prompt side effects.
- PRD-046.1.2: Diagnostic Center v1 shadow divergence calibration + Planner Bridge contract delivered (divergence taxonomy module, planner bridge contracts/builder, expanded eval `24/24`, no-mutation proof, ADR-032); bridge remains shadow/eval-only with `apply_to_writer=false`.
- PRD-046.1.2-HF1: artifact encoding hygiene closed for PRD-046.1.2; `test_command_output.txt` regenerated as clean UTF-8, reusable artifact validator added with tests, hygiene report passed (`nul/utf8/json/debug-dir` gates green), no production/runtime mutation.
- PRD-046.1.3: Planner Bridge Shadow-to-Compliance integration delivered in compare-only mode; runtime trace now includes `planner_bridge_candidate` and `planner_bridge_compliance_shadow` with strict no-user-path-effect gates, eval `30/30` passed, runtime smoke + artifact encoding hygiene + no-mutation proofs passed, ADR-033 added.
- PRD-046.1.4: controlled Writer-Contract pilot delivered in `pilot_shadow_only` mode; added candidate overlay contract/builder/runtime trace/eval runner (`36/36`), immutability hash proof, no-user-path-effect gates (`writer_contract/prompt/final_answer unchanged`), runtime smoke + encoding hygiene + no-mutation proofs passed, ADR-034 added.
- PRD-046.1.5: controlled Writer Prompt Replay / Quality Eval delivered as offline-only layer; baseline vs candidate prompt-context replay runner + fixtures (`40/40`) added with deterministic safety/KB/conflict/prompt-bloat/non-mutation checks, runtime smoke passed, provider-call and apply flags remained false, ADR-035 added.
- PRD-046.1.6: controlled Prompt-Constraint Pilot limited runtime flag delivered as default-off/allowlisted layer; added runtime contract/builder/section formatter, orchestrator trace wiring, writer optional apply path, eval runner + fixture (`50/50`), rollback/safety/KB gates and runtime smoke passed with `limited_runtime_flag_ready=true`, ADR-036 added.
- PRD-046.1.7: prompt-constraint runtime results/rollback/quality gate delivered; added deterministic evidence audit + rollback toggle matrix + baseline-vs-test_apply quality delta + safety/KB/conflict/bloat verification runner/artifacts, strict gate passed with `final_status=passed`, `decision=supervised_rollout_candidate`, default-off/allowlist/no-mutation/provider-free invariants preserved.
- PRD-046.1.8: supervised prompt-constraint rollout planning/readiness layer delivered; added rollout contract/builder/CLI plus artifacts (`supervised_rollout_plan`, readiness gate, abort criteria, toggle matrix, operator runbook), passed with `decision=ready_for_supervised_execution_prd`, while default flags stayed conservative (`enabled=false`, `force_disabled=true`) and no production mutation/provider calls occurred.
- PRD-046.1.9: one controlled supervised execution/observability cycle delivered (`run_prompt_constraint_supervised_execution_gate.py` + contracts/tests/artifacts); allowlisted cohort `3` produced `test_apply_applied_count=3`, normal-user no-effect and rollback proofs stayed green, baseline-vs-test_apply showed no regressions, final decision `continue_supervised` with no production mutation/provider call.
- PRD-046.1.10: second supervised continuation cycle delivered on expanded allowlisted cohort (`6`) with full scenario coverage (`6/6`); continuation harness/runner/tests/artifacts added, baseline-vs-test_apply remained clean (`candidate/safety/kb/conflict/bloat regressions = 0`), normal-user no-effect (`2` controls) and rollback gates passed, final decision `continue_supervised` with no production mutation/provider call.
- PRD-046.1.11: supervised results consolidation / rollout decision gate delivered; added consolidation contract/module/CLI + tests/artifacts across both supervised cycles (`046.1.9` + `046.1.10`), confirmed reproducibility (`total_test_apply_applied_count=9`, `total_cases_compared=9`, zero safety/KB/rollback/no-mutation/provider regressions), final decision `prepare_production_limited_rollout_plan`.
- PRD-046.1.12: production-limited rollout planning gate delivered (plan-only, no execution); added rollout plan contract/module/CLI + tests/artifacts (`cohort_policy`, `preflight_gates`, `operator_checklist`, `monitoring_plan`, `rollback_plan`, `abort_criteria`, `readiness_gate`, runbook) with conservative defaults preserved and final decision `ready_for_production_limited_execution_prd`.
- PRD-046.1.13: one production-limited execution/monitoring cycle delivered; added execution contract/module/CLI + tests/artifacts (manifest, preflight, sanitized traces, baseline-vs-test_apply, normal-user no-effect, rollback proof, monitoring scorecard, no-mutation/hygiene), ran single-target window (	arget_user_count=1) with rollback-first success and decision continue_limited.
- PRD-046.1.14: post-run production-limited results/rollback/quality gate delivered; added results-gate contract/module/CLI + tests/artifacts (manifest, quality/rollback/normal-user/trace/risk/decision, no-mutation/hygiene), no new execution performed, final decision 
eady_for_stabilization_cleanup with no provider calls and no production mutation.
- PRD-046.1.15: stabilization/cleanup/eval-harness consolidation delivered; added stabilization contract/module/CLI + tests/artifacts (source gate, module inventory/classification, permanent regression gate catalog, non-destructive cleanup plan, archive manifest, stabilization scorecard, transfer brief, no-mutation/hygiene), with `decision=ready_for_transfer_brief` and no runtime-default/provider/production-state mutation.
- PRD-046.1.16: final acceptance/runtime governance closure delivered; added final-acceptance contract/module/CLI + artifacts (source gate, boundary matrix, permanent gate confirmation, conservative baseline gate, normal-user no-effect gate, KB boundary gate, trace sanitization gate, closure decision, scorecard, no-mutation/hygiene), accepted as governed shadow layer with `broad_rollout_allowed=false` and `runtime_authority_expansion_allowed=false`.
- PRD-046.1.17: response quality eval pack delivered in offline deterministic mode; added response-quality contract/module/CLI + curated scenario/rubric/candidate fixtures + artifacts (scenario catalog, rubric validation, eval results, dimension scorecard, weak-case queue, KB/internal lens boundary eval, no-runtime-authority-expansion gate, no-mutation/hygiene), with `hard_fail_detection_rate=1.00` and no runtime activation/provider calls.
- PRD-046.1.18: response quality calibration/weak-case closure delivered in offline deterministic mode; added calibration contract/module/CLI + expanded fixtures (`34` scenarios, `8` candidate profiles) + artifacts (source gate, weak-case inventory, calibration plan, expanded catalogs, calibrated eval/scorecards, boundary/no-runtime/no-mutation/hygiene), final decision `response_quality_calibration_passed` with runtime authority unchanged.
- PRD-046.1.19: runtime pilot readiness plan-only gate delivered; added readiness contract/module/CLI + required artifacts (pilot scope, cohort policy, toggle matrix, preflight requirements, limited live smoke plan, rollback-first runbook, hard stops, monitoring contract, normal-user/KB/trace guards, no-mutation/hygiene), with `execution_performed=false` and final decision `runtime_pilot_readiness_plan_ready`.

- PRD-046.1.20: first controlled runtime pilot execution (limited live smoke) delivered; allowlisted operator-only apply, >=2 normal-user controls, rollback pre/post checks passed, quality/safety/KB/trace gates green, hard-stop not triggered, no-mutation/encoding proofs passed, decision=controlled_runtime_pilot_execution_passed.
- PRD-046.1.21: post-execution runtime pilot results/rollback/quality gate delivered; consolidated PRD-046.1.20 evidence without new execution/provider calls, passed source/execution/rollback/normal-user/quality/safety/trace/no-mutation gates, captured source encoding warning as non-blocking, decision=continue_limited_candidate.
- PRD-046.1.21-HF1: emergency BotDB/Admin/Chroma integrity repair cycle delivered (`run_live_botdb_chroma_registry_audit_hf1.py`, persistent-store diagnostic, backup/reindex/hygiene/browser/retrieval/no-mutation artifacts, `/api/registry/stats` degraded-resilience). Live runtime blocker remains on current `:8003`: `/api/query/` still returns `503 ChromaDB unavailable`, so cycle closed as `done_with_query_blocker`.
## Current / In Progress
- PRD-DOCS-001: living documentation consolidation layer (`docs/`) and report hygiene normalization.
- PRD-046.1.21-HF2: live query recovery closure passed; next: PRD-046.1.22 provider-backed limited smoke readiness.

## Next
1. PRD-046.1.21-HF2 - Chroma Persistent Store Deep Recovery / Rebuild v2.
2. PRD-046.1.22 - Diagnostic Center Controlled Runtime Pilot Continuation / Provider-Backed Limited Smoke Readiness v1 (after HF2 gate closure).

## Later
- Diagnostic Center v1 rollout after KB/retrieval/context readiness confirmation.
- Planner-lite for workflow automation.
- Production hardening cycle (SLO monitoring, operational guardrails, incident playbooks).
- Post-stabilization governance closure: подтвердить final acceptance на закрепленных permanent regression gates и зафиксировать runtime governance boundaries перед любым расширением rollout.

## Deferred / Not Yet
- Full runtime reliance on enriched KB until APPLY1 + retrieval checks complete.
- Direct expansion of Writer autonomy without upstream diagnostic/context safeguards.

## Roadmap Rules
1. Runtime/architecture PRDs must update `docs/PROJECT_STATE.md`.
2. Sequence-changing PRDs must update this roadmap.
3. New architecture decisions must be reflected in `docs/DECISIONS.md`.
4. Every merged PRD cycle updates `docs/PRD_INDEX.md`.
5. `TO_DO_LIST` remains detailed archive; `docs/` remains compact navigation layer.

## Ordering Constraint
Async Turn LLM Summary (`PRD-045.6.3`) внедрен; перед запуском Diagnostic Center обязательны retrieval eval + review workflow readiness gates.






