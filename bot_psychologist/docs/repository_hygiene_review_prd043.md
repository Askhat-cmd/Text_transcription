# PRD-043 Repository Hygiene Review List (Список review PRD-043 Repository Hygiene)

## REVIEW tests, сохранённые в репозитории
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

## Why Not Deleted in PRD-043 (Почему они не удалены в PRD-043)
- Scope PRD-043 — repository hygiene и docs consolidation, а не functional removal review/support modules.
- Эти tests могут по-прежнему guard reused diagnostic/support behavior после удаления legacy runtime.
- Удаление требует отдельного ownership audit и explicit deprecation plan.

## Recommended Follow-up (Рекомендуемый follow-up)
- Запустить dedicated ownership mapping и dependency audit в PRD-044.
- Решить keep/refactor/remove per module cluster с explicit regression coverage replacements.
