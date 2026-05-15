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

## Current / In Progress
- PRD-DOCS-001: living documentation consolidation layer (`docs/`) and report hygiene normalization.
- PRD-046.0.9-RUN1: real provider enrichment run blocked by provider preflight (`api_key_missing`); waiting for credential restore and rerun.

## Next
1. PRD-046.0.9-RUN1-FIX - Provider/Budget Configuration Fix v1.
2. PRD-046.0.9.1 - Human Review Decisions for Post-Reprocess Enrichment v1.
3. PRD-046.0.7.1 - Controlled Review Decision Apply v1 (new block ids only).

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
