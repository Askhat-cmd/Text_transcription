# Active Line / Dialogue Continuity v1 (Active Line / непрерывность диалога v1)

## Scope (Область)
`Active Line` — детерминированный continuity layer для качества multi-turn dialogue.

Модуль:
- `bot_agent/multiagent/active_line.py`

Версия:
- `active_line_v1`

## State Contract (Контракт состояния)
Состояние на ход:
- `active_line`
- `user_intent`
- `continuity_mode`
- `next_meaningful_move`
- `should_continue_line`
- `should_ask_question`
- `should_offer_practice`
- `revoicing_allowed`
- `revoicing_style`
- `repair_mode`
- `confidence`
- `practice_suppression_active`

## Deterministic Intents (Детерминированные intent)
- `understand_mechanism`
- `ask_for_practice`
- `ask_for_direct_step`
- `short_support`
- `known_concept_question`
- `correction_of_bot`
- `thanks_close`
- `unknown`

## Continuity Modes (Режимы continuity)
- `start_new_line`
- `continue_existing_line`
- `repair_and_continue_line`
- `close_gently`

## Writer Integration (Интеграция с Writer)
- `WriterContract.active_line` несёт полное состояние.
- Writer prompt получает поля active-line как явные constraints.
- Writer compliance обеспечивает:
  - подавление механических revoicing openings, когда это запрещено
  - подавление не запрошенных action/practice для mechanism-first turns
  - repair response path после user correction
  - чистое закрытие на `thanks_close`

## Trace / Admin (Trace и admin)
- Trace block: `debug.active_line`.
- Admin runtime effective block: `active_line` (enabled/version/revoicing policy/practice suppression/calibration summary).

## Evaluation (Оценка)
- Dataset: `tests/evaluation/prd_047_3_active_line_cases.json` (10 cases).
- Runner: `scripts/run_prd_047_3_active_line_cases.py` с режимами `dry/direct/live`.
- Артефакты:
  - `TO_DO_LIST/logs/PRD-047.3/active_line_dry.json`
  - `TO_DO_LIST/logs/PRD-047.3/active_line_direct.json`
  - `TO_DO_LIST/logs/PRD-047.3/active_line_live.json`
  - `TO_DO_LIST/logs/PRD-047.3/active_line_trace_samples.json`
  - `TO_DO_LIST/logs/PRD-047.3/revoicing_report.json`
  - `TO_DO_LIST/logs/PRD-047.3/practice_suppression_report.json`
