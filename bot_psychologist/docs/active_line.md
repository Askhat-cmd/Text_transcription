# Active Line / Dialogue Continuity v1

## Scope
`Active Line` is a deterministic continuity layer for multi-turn dialogue quality.

Module:
- `bot_agent/multiagent/active_line.py`

Version:
- `active_line_v1`

## State Contract
Per turn state:
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

## Deterministic Intents
- `understand_mechanism`
- `ask_for_practice`
- `ask_for_direct_step`
- `short_support`
- `known_concept_question`
- `correction_of_bot`
- `thanks_close`
- `unknown`

## Continuity Modes
- `start_new_line`
- `continue_existing_line`
- `repair_and_continue_line`
- `close_gently`

## Writer Integration
- `WriterContract.active_line` carries the full state.
- Writer prompt receives active-line fields as explicit constraints.
- Writer compliance enforces:
  - suppression of mechanical revoicing openings when disallowed
  - suppression of unsolicited action/practice for mechanism-first turns
  - repair response path after user correction
  - clean close on `thanks_close`

## Trace / Admin
- Trace block: `debug.active_line`.
- Admin runtime effective block: `active_line` (enabled/version/revoicing policy/practice suppression/calibration summary).

## Evaluation
- Dataset: `tests/evaluation/prd_047_3_active_line_cases.json` (10 cases).
- Runner: `scripts/run_prd_047_3_active_line_cases.py` with `dry/direct/live`.
- Artifacts:
  - `TO_DO_LIST/logs/PRD-047.3/active_line_dry.json`
  - `TO_DO_LIST/logs/PRD-047.3/active_line_direct.json`
  - `TO_DO_LIST/logs/PRD-047.3/active_line_live.json`
  - `TO_DO_LIST/logs/PRD-047.3/active_line_trace_samples.json`
  - `TO_DO_LIST/logs/PRD-047.3/revoicing_report.json`
  - `TO_DO_LIST/logs/PRD-047.3/practice_suppression_report.json`
