# TASKLIST PRD-041 — Physical Legacy Purge

## Context
- PRD: `TO_DO_LIST/PRD-041_Physical_Legacy_Purge.md`
- Goal: physically remove callable legacy cascade while preserving active multiagent runtime.

## Implementation Plan
- [x] Create legacy purge audit doc with DELETE/KEEP/REVIEW classification.
- [x] Add import graph helper script for legacy symbol usage scan.
- [x] Shrink `bot_agent/answer_adaptive.py` to tiny compatibility shim.
- [x] Delete `bot_agent/adaptive_runtime/` after shim cutover.
- [x] Classify remaining legacy candidates (`state_classifier`, `route_resolver`, `decision`, `response`, `fast_detector`, `user_level_types`, `memory_v12`) in audit.
- [x] Add physical purge inventory guard test.
- [x] Update `tests/fixtures/multiagent_runtime_invariants_v1.json` with physical purge section.
- [x] Update docs to reflect PRD-041 physical purge completion.

## Tests
- [x] `.venv\Scripts\python -m pytest tests/inventory/test_physical_legacy_purge.py -q`
- [x] `.venv\Scripts\python -m pytest tests/inventory/test_multiagent_runtime_invariants.py -q`
- [x] `.venv\Scripts\python -m pytest tests/inventory -q`
- [x] `.venv\Scripts\python -m pytest tests/api -q`
- [x] `.venv\Scripts\python -m pytest tests/multiagent -q`
- [x] `.venv\Scripts\python -m pytest tests/test_llm_streaming.py -q`
- [x] `.venv\Scripts\python -m pytest tests/telegram_adapter -q`
- [x] `.venv\Scripts\python -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py tests/test_admin_runtime_contract.py -q`
- [x] `.venv\Scripts\python -m pytest tests/test_feature_flags.py -q`
- [x] `npm run build` (in `bot_psychologist/web_ui`)

## Checks
- [x] `bot_agent/adaptive_runtime/` does not exist.
- [x] `answer_adaptive.py` has no legacy cascade body and no legacy imports.
- [x] Active runtime contract remains multiagent-only.

## Progress
- [x] PRD-041 reviewed
- [x] Initial legacy references scan started
- [x] Code changes
- [x] Test pass
- [x] Final validation
