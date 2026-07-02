# TRANSFER BRIEF AFTER PRD-047.37

Date: 2026-07-02
Status: `freeze_baseline_transfer`

## Current Architecture Baseline
- Active runtime: `multiagent_adapter / multiagent_v1`.
- Writer remains final answer author.
- `final_answer_directive_v1` owns latest-turn authority and answer target.
- `writer_context_package_v1` / `writer_kb_payload_v1` gate Writer-visible knowledge.
- `runtime_truth_trace_v1`, `source_chunk_match_trace_v1`, and `boundary_trace_v1` are owner/debug proof surfaces.
- Semantic cards are advisory-only and Writer-can-ignore.
- Safety remains above depth, DB, style, and user curiosity.

## Latest Accepted PRDs
- PRD-047.36-HF4: fresh Web Chat trace/reload restored; old pre-restart trace expiry accepted if labelled.
- PRD-047.36-HF5: direct concept follow-up selected knowledge can reach Writer as minimal hidden payload.
- PRD-047.36-HF6: `no_internal_db` and `no_practice` boundary proof restored through `boundary_trace_v1`.
- PRD-047.37: current PRD freezes baseline, documents warnings, prepares pilot brief and cleanup backlog; no runtime fix.

## Owner Decision
The owner chose not to continue immediate hotfix/rerun-gate cycling. The project moves to frozen baseline + pilot evidence + cleanup roadmap. Remaining known issues are warnings unless pilot evidence proves a blocker.

## Known Warnings
- Old debug traces may expire after backend restart if labelled honestly.
- Greeting/contact wording can be too therapeutic.
- Some source exact-match coverage is weak without better DB/chunk preparation.
- Shadow planner can be noisy/invalid while production path is correct.
- Full pytest still has historical `_build_llm_prompts` import debt.
- UI trace labels and Session Trace Panel need later polish.
- Strategic source docs have location/name inconsistencies.

## Next Recommended Options
- Option A - Owner Pilot Start: use `pilot_start_brief.md`, collect evidence, avoid new hotfixes unless blocker.
- Option B - Cleanup Pass 1: docs/logs/trace labels/legacy report hygiene only.
- Option C - DB/Chunk Preparation Strategy: separate source/DB preparation phase based on Wake Up DB Structure.
- Option D - Historical Test Debt: repair `_build_llm_prompts` import blocker if it starts blocking confidence or CI.

Default recommendation: Option A first, then cleanup/source preparation based on pilot evidence.

## What Not To Do
- Do not add dictionaries, alias maps, term-specific routes, or rule-engine sprawl.
- Do not add a new LLM agent or runtime path.
- Do not mutate Bot_data_base, Chroma, source documents, registry, or processed blocks inside cleanup/freeze work.
- Do not tune Writer style globally without a narrow PRD and evidence.
- Do not implement persistent historical trace storage unless explicitly scoped.
- Do not commit raw private chat logs or screenshots.

## How The Next Architect Should Continue
1. Start from `pilot_start_brief.md` and `invariants_register.md`.
2. Treat warnings as backlog, not automatic hotfix scope.
3. If pilot finds a blocker, create one narrow PRD named after the failing invariant.
4. If pilot is acceptable, run Cleanup Pass 1 focused on documentation, trace labels, reports, and retirement proof.
5. Keep DB/chunk preparation separate from runtime behavior changes.
6. Preserve no-mutation/no-overengineering discipline.
