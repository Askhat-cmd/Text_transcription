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

## Current / In Progress
- PRD-DOCS-001: living documentation consolidation layer (`docs/`) and report hygiene normalization.

## Next
1. PRD-046.1 - Diagnostic Center v1 Readiness / Architecture PRD.
2. PRD-046.0.11 - Final Runtime Readiness Summary v1 (optional before PRD-046.1).

## Later
- Diagnostic Center v1 rollout after KB/retrieval/context readiness confirmation.
- Planner-lite for workflow automation.
- Production hardening cycle (SLO monitoring, operational guardrails, incident playbooks).

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
