# TASKLIST SD Legacy Final Cleanup v1.0.0 (PROGRESS)

Status: DONE  
PRD: `PRD_SD_Legacy_Final_Cleanup_v1.0.0.md`  
Started: 2026-04-09

## Scope
- [x] Read PRD and extract FIX-1/FIX-2/FIX-3.
- [x] Apply FIX-1 in `bot_psychologist/bot_agent/state_classifier.py`.
- [x] Apply FIX-2 in `bot_psychologist/bot_agent/answer_adaptive.py`.
- [x] Apply FIX-3 in `bot_psychologist/bot_agent/diagnostics_classifier.py`.
- [x] Add/update tests for SD legacy cleanup acceptance.
- [x] Run focused test suite for SD cleanup.
- [x] Run full regression suite.
- [x] Update this tasklist with final results.

## FIX-1 Checklist (`state_classifier.py`)
- [x] Add Neo runtime output contract (`nervous_system_state`, `request_function`, `confidence`, `raw_label`).
- [x] Ensure runtime vocabulary is constrained to:
- [x] `nervous_system_state in {hyper, window, hypo}`
- [x] `request_function in {discharge, understand, solution, validation, explore, contact}`
- [x] Replace legacy log format with:
- [x] `STATE nss=... fn=... conf=...`
- [x] Keep compatibility for existing adaptive pipeline (no breaking API changes).

## FIX-2 Checklist (`answer_adaptive.py`)
- [x] Remove SD-level line from prompt context builder.
- [x] Remove SD recommendation directive line from prompt context builder.
- [x] Remove malformed SD/cyrillic directive artifacts from prompt context builder.
- [x] Ensure diagnostics context keeps only Neo fields (`nervous_system_state`, `request_function`, etc.).
- [x] Remove runtime log line `SD runtime disabled in Neo v11 pipeline`.

## FIX-3 Checklist (`diagnostics_classifier.py`)
- [x] Remove legacy mapper warning path (`legacy term ... -> ...`).
- [x] Add strict validator/fallback for invalid NSS and request function.
- [x] Keep only ERROR-level fallback logs for truly invalid values.
- [x] Ensure no legacy mapper attributes remain.

## Validation Plan
- [x] Add/adjust tests:
- [x] `tests/unit/test_sd_legacy_final_cleanup_state_classifier.py`
- [x] `tests/unit/test_sd_legacy_final_cleanup_diagnostics.py`
- [x] `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- [x] `tests/unit/test_sd_legacy_final_cleanup_grep.py`
- [x] Run focused cleanup tests.
- [x] Run full `pytest -q` in `bot_psychologist`.

## Notes
- Keep compatibility with current Neo runtime contracts and existing green suite.
- Do not touch `voice_bot_pipeline` (excluded by user).
- Focused SD cleanup tests: `9 passed`.
- Full regression after cleanup: `421 passed, 13 skipped`.
