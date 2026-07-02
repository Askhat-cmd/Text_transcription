# PRD-047.36-HF6 Source Gate

## Read
- `TO_DO_LIST/PRD-047.36-HF6_No_Internal_DB_No_Practice_Boundary_Trace_Integrity_RU.md`
- `TO_DO_LIST/PRD-047.36-POST-HF_Owner_Readiness_Gate_RU.md`
- `TO_DO_LIST/PRD-047.36-POST-HF_TASK_LIST.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/readiness_gate_report.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/readiness_gate_matrix.json`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/boundary_preservation_report.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/trace_reload_report.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/knowledge_path_report.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/delivery_memory_sanity_report.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/test_results.md`
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/next_recommendation.md`
- `TO_DO_LIST/PRD-047.36-HF4_Trace_Restoration_Hard_Blocker_Owner_Web_Verification_RU.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/live_smoke_report.md`
- `TO_DO_LIST/PRD-047.36-HF5_Direct_Concept_Followup_KB_Visibility_RU.md`
- `TO_DO_LIST/logs/PRD-047.36-HF5/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF5/live_smoke_report.md`

## Initial blocker alignment
- Post-HF gate blocker is narrow and explicit:
  - `G5 = no_internal_db_trace_flag_missing`
  - `G6 = no_practice_trace_flag_missing`
  - `G10` is blocked as a consequence of missing boundary trace explainability for G5/G6.
- Visible answer behavior is already mostly acceptable; HF6 must repair trace integrity, not answer quality.

## Scope confirmation
- Allowed scope: boundary trace fields, propagation, tests, runner, reports, docs.
- Disallowed scope: Writer style changes, retrieval ranking changes, selected-knowledge admission changes outside preservation, DB/Chroma/source mutation, new routes, new agents, persistent historical trace store.
