# Roadmap

## Done
- PRD-045.x: foundation runtime quality chain (multiagent contracts, context assembly baseline, diagnostic card and writer compliance alignment).
- PRD-046.0..046.0.4.x: knowledge governance, Chroma recovery, governed reindex and API query restore.
- PRD-046.0.5 + HF1 + RUN1 + HF2 + HF3: offline/real LLM enrichment pipeline calibrated to production-candidate quality on controlled batch.

## Current / In Progress
- PRD-DOCS-001: living documentation consolidation layer (`docs/`) and report hygiene normalization.

## Next
1. PRD-046.0.5-APPLY1 - Apply Real LLM Enrichment Overlay + Chroma Refresh v1.
2. PRD-045.6.3 - Async Turn LLM Summary Store v1.
3. PRD-046.0.6 - Knowledge Retrieval Eval Set v1.
4. PRD-046.0.7 - Admin Review Workflow v1.

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
Async Turn LLM Summary (`PRD-045.6.3`) должен быть внедрен до активного усиления runtime через enriched KB и до запуска Diagnostic Center, чтобы recent dialogue context не уступал по качеству KB context.
