# PRD-047.38 Source Gate

Date: 2026-07-02
Status: `completed`

## PRD Input
- Pulled `origin/main` fast-forward to `0c678f600062e9ea501d52305314f65e3777a7bd`.
- Read `TO_DO_LIST/PRD-047.38_Automated_Owner_Pilot_Evidence_Gate_Architecture_Consolidation_Entry_RU.md`.

## Required Source
- Read `TO_DO_LIST/logs/PRD-047.37/pilot_start_brief.md`.
- Read `запуск проека.txt`.

## Current Objective
Replace manual owner pilot classification with an automated read-only evidence gate over the 12 scenarios from `pilot_start_brief.md`.

## Hard Boundaries
- Do not improve answer intelligence or style.
- Do not mutate Bot_data_base, Chroma, registry, source documents, processed blocks, or run reindex.
- Do not add agents, runtime paths, dictionaries, alias maps, or marker routes.
- Do not commit raw private chat logs or screenshots.
- Commit only sanitized runner reports.

## Existing Utilities To Inspect / Reuse
- `bot_psychologist/tools/run_prd_047_36_post_hf_owner_readiness_gate.py`
- `bot_psychologist/tools/run_prd_047_36_owner_pilot_readiness_gate.py`
- `bot_psychologist/tools/run_prd_047_36_hf4_trace_restoration_smoke.py`
- `bot_psychologist/tools/run_prd_047_36_hf5_direct_concept_followup_kb_visibility.py`
- `bot_psychologist/tools/run_prd_047_36_hf6_boundary_trace_integrity.py`

## Expected Outputs
- `automated_owner_pilot_report.md`
- `automated_owner_pilot_report.json`
- `blockers_and_warnings.md`
- `no_mutation_proof.md`
- `next_recommendation.md`
