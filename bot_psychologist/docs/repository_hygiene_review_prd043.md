# PRD-043 Repository Hygiene Review List

## REVIEW tests kept in repository
- `bot_psychologist/tests/test_decision_gate.py`
- `bot_psychologist/tests/test_decision_table.py`
- `bot_psychologist/tests/test_response_formatter.py`
- `bot_psychologist/tests/test_response_generator.py`
- `bot_psychologist/tests/test_signal_detector.py`
- `bot_psychologist/tests/test_fast_detector.py`
- `bot_psychologist/tests/test_confidence_scorer.py`
- `bot_psychologist/tests/test_path_builder.py`
- `bot_psychologist/tests/test_mode_handlers.py`
- `bot_psychologist/tests/test_phase1.py`
- `bot_psychologist/tests/test_phase2.py`
- `bot_psychologist/tests/test_phase3.py`
- `bot_psychologist/tests/test_phase4.py`
- `bot_psychologist/tests/phase8_runtime_support.py`

## Why they were not deleted in PRD-043
- PRD-043 scope is repository hygiene and docs consolidation, not functional removal of review/support modules.
- These tests may still guard reused diagnostic/support behavior after legacy runtime removal.
- Removing them requires separate ownership audit and explicit deprecation plan.

## Suggested follow-up
- Run dedicated ownership mapping and dependency audit in PRD-044.
- Decide keep/refactor/remove per module cluster with explicit regression coverage replacements.
