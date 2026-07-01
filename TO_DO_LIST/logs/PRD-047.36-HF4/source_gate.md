# PRD-047.36-HF4 Source Gate

## Read
- `TO_DO_LIST/PRD-047.36-HF4_Trace_Restoration_Hard_Blocker_Owner_Web_Verification_RU.md`
- `TO_DO_LIST/PRD-047.36-HF3_Trace_Availability_Reload_Hydration_Completeness_RU.md`
- `TO_DO_LIST/PRD-047.36-HF3_TASK_LIST.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/test_results.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/live_smoke_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/debug_endpoint_exact_lookup_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/frontend_trace_availability_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/trace_store_key_audit.md`
- `TO_DO_LIST/logs/PRD-047.36-HF3/next_recommendation.md`

## Owner Evidence Available
- Inline owner screenshots in task request show fresh and older chats with `Trace unavailable`.
- No raw local `ЧАТ_С_БОТОМ_12.txt` was provided in the workspace at start of HF4.

## HF4 Scope Confirmation
- Hard blocker is real trace restoration in Web Chat, not merely structured unavailable-state.
- API-only smoke is insufficient for acceptance.
- Fresh multi-turn browser/reload verification is mandatory.
- Writer/retrieval/DB/Chroma/source/model/safety behavior stays out of scope.
