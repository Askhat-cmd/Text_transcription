# TASKLIST 12.0 - Neo MindBot BugFix (PROGRESS)

Status: IN PROGRESS (implementation done, focused regression passed)  
PRD: `PRD_12_0_Neo_MindBot_BugFix.md`  
Started: 2026-04-08

## Wave 1 - Critical Bugs (BUG-01, BUG-02, BUG-03)
- [x] BUG-01-A: Add dedicated summarizer config (model/reasoning/min turns/retries/fallback).
- [x] BUG-01-B: Refactor summary generation with retry + fallback on empty response.
- [x] BUG-01-C: Add/update summarizer prompt asset.
- [x] BUG-01-D: Add summary diagnostics logging (success/failure, length, turn).
- [x] BUG-02-A: Implement snapshot schema v12 fields in runtime memory updater.
- [x] BUG-02-B: Keep compatibility path for existing v11 consumers while exposing v12 snapshot.
- [x] BUG-02-C: Remove legacy `user_state` dependency from runtime memory snapshot surface.
- [x] BUG-03-A: Ensure single source-of-truth for `nervous_system_state` in final system prompt.
- [x] BUG-03-B: Remove duplicate snapshot injection from prompt assembly.
- [x] BUG-03-C: Add prompt consistency validation guard.

## Wave 2 - Critical + Important (BUG-04, IMP-01)
- [x] BUG-04-A: Lower semantic similarity threshold defaults for better recall.
- [x] BUG-04-B: Fix semantic search pool behavior to avoid zero hits on early turns.
- [x] BUG-04-C: Add semantic diagnostics logs (pool size, threshold, hit counts).
- [x] IMP-01-A: Migrate legacy state terms to `window|hyper|hypo` with safe mapping.
- [x] IMP-01-B: Ensure unknown legacy terms fallback safely and are logged.

## Wave 3 - Prompt UX Improvements (IMP-02, IMP-03)
- [x] IMP-02-A: Ensure practice block is skipped for contact-hold routes.
- [x] IMP-02-B: Keep prompt lean when practice is skipped.
- [x] IMP-03-A: Strengthen User Correction protocol instruction (>=3 sentences + question).
- [x] IMP-03-B: Extend correction trigger patterns for common confusion phrases.

## Validation
- [x] Add/adjust unit-contract tests for summary/snapshot/prompt/semantic behavior.
- [x] Run focused regression for touched modules.
- [x] Run acceptance subset for PRD12 behavior.
- [x] Update API app version target to `0.12.0`.
- [x] Run full expanded project test suite.
- [x] Final pass: mark completed items and leave notes for any deferred scope.

## Notes
- Ignore `voice_bot_pipeline` per request.
- Do not touch unrelated archive/migration changes in git working tree.
- Added migration utility: `bot_psychologist/migrations/migrate_snapshots_v12.py`.
- Full expanded suite executed on 2026-04-09: `412 passed, 13 skipped` (`pytest -q` in `bot_psychologist`).
