# PRD-047.36 Source Gate

## Status
- Source gate opened before any PRD-047.36 code changes.

## Required Files Read
- `TO_DO_LIST/PRD-047.36_Owner_Pilot_Readiness_Gate_12_Scenario_Freeze_RU.md`
- `TO_DO_LIST/PRD-047.36-HF2_Retrieval_Recall_Candidate_Selection_Audit_Source_Chunk_Match_Reliability_RU.md`
- `TO_DO_LIST/PRD-047.36-HF2_TASK_LIST.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/test_results.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/live_smoke_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/chat_8_replay_report.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/retrieval_recall_audit.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/candidate_path_matrix.json`
- `TO_DO_LIST/logs/PRD-047.36-HF2/fix_decision.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/no_mutation_proof.md`
- `TO_DO_LIST/logs/PRD-047.36-HF2/next_recommendation.md`
- `TO_DO_LIST/PRD-047.35_Product_Simplicity_Hidden_Knowledge_Competence_Wake_Depth_RU.md`
- `TO_DO_LIST/logs/PRD-047.35/implementation_report.md`
- `TO_DO_LIST/logs/PRD-047.35/live_owner_pilot_smoke_report.md`
- `TO_DO_LIST/logs/PRD-047.35/next_recommendation.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/PRD_INDEX.md`
- `docs/DECISIONS.md`
- `запуск проека.txt`

## Private Local Context
- Read local private owner context:
  - `TO_DO_LIST/context/ЧАТ_С_БОТОМ_9.txt`
- This file exists locally, was used for context, and must remain uncommitted.

## Initial Readiness Risk Identified Before Implementation
- Chat 9 already shows a likely readiness-gate risk:
  - `payload_match.near_exact=true`
  - `sent_to_writer=true`
  - while `loss_stage=raw_source`
- This may be only a trace-taxonomy inconsistency, or it may indicate a real readiness blocker in source-proof truth.
- PRD-047.36 must classify this explicitly before any behavior fix is considered.

## Git Baseline
- Local `main` fast-forwarded to `origin/main` commit:
  - `0b38eb0cf3f12ced5ec7942d451bbb5e8e40d266`

## Non-Goal Reminder
- No new runtime route
- No new LLM agent
- No DB/Chroma/registry/source mutation
- No dictionary or alias-map repair
- No stealth behavior hotfix unless it is a tiny gate/report-only consistency cleanup
