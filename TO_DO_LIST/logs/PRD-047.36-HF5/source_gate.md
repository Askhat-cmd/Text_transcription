# PRD-047.36-HF5 Source Gate

## Read
- `TO_DO_LIST/PRD-047.36-HF5_Direct_Concept_Followup_KB_Visibility_RU.md`
- `TO_DO_LIST/PRD-047.36-HF4_Trace_Restoration_Hard_Blocker_Owner_Web_Verification_RU.md`
- `TO_DO_LIST/PRD-047.36-HF4_TASK_LIST.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/test_results.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/live_smoke_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/next_recommendation.md`
- `TO_DO_LIST/logs/PRD-047.36-HF4/no_mutation_proof.md`
- `TO_DO_LIST/context/ЧАТ_С_БОТОМ_12.txt`
- `TO_DO_LIST/context/Рекомендации для архитектора.txt`

## Confirmed HF5 Problem
- Chat 12 proves retrieval/selection can succeed while Writer KB Payload remains zero.
- The failing class is selected relevant knowledge being suppressed as trace-only with `grounding_reason=no_clear_retrieval_need`.
- The target is coordination repair in the admission contract, not retrieval ranking, source mutation, or a term dictionary.

## Confirmed Boundaries
- Greeting/contact turns may still suppress KB.
- `no_internal_db` must still hard-block writer-visible knowledge.
- Semantic cards must remain advisory-only, not Writer authority.
- Public answers must not mention DB/chunks/cards/trace internals.
