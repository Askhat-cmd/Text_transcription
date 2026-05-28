# Writer Freedom Contract

## Scope
`Writer Freedom Contract v1` is the guided-freedom policy for Writer.

Version:
- `writer_freedom_contract_v1`

## Required Fields
- `enabled`
- `freedom_level`
- `mode_hint`
- `mode_is_hint_not_cage`
- `question_limit`
- `practice_requires_gate`
- `practice_allowed`
- `hard_boundaries`
- `must_follow_exact_mode`

## Contract Semantics
- Response mode is guidance, not a strict cage.
- Keep one main move per answer.
- Practice requires explicit gate/safety need.
- Hard boundaries are mandatory (`no_diagnosis`, `no_spiritual_authority`, `no_raw_kb_quote_dumping`, `no_unsolicited_practice`).

## Prompt Integration
- Prompt block renderer: `render_writer_freedom_contract_prompt_block(...)`.
- Writer prompt includes compact freedom block instead of verbose contract dump.
- Micro-guidance in Writer prompt:
  - speak from lens, not about lens
  - avoid exposing internal lens names unless useful
  - avoid bureaucratic phrasing on personal tone
  - warm direct style for vulnerable user messages

## Runtime / Trace / Admin
- Propagated through `WriterContract` prompt context.
- Trace includes `debug.writer_freedom_contract.prompt_block_chars`.
- Admin runtime effective exposes read-only freedom contract state.

## Interaction With Active Line
- Writer freedom remains guided, but continuity constraints come from `active_line` signals.
- `active_line_should_offer_practice=false` suppresses unsolicited action-step behavior.
- `active_line_revoicing_allowed=false` suppresses mechanical question revoicing openers.
- `active_line_repair_mode` prioritizes acknowledgement + return to mechanism on correction turns.
- This keeps `mode_is_hint_not_cage` semantics while enforcing continuity-quality boundaries.

## Interaction With Response Planner
- `response_planner` provides compact per-turn move shape, depth, and policy hints.
- Freedom contract is still the style/governance frame; planner is the turn-level move selector.
- Compliance keeps hard limits even with freedom preserved:
  - `question_policy=none` suppresses follow-up question behavior.
  - `practice_policy=forbidden` suppresses unsolicited practice steps.
  - `revoicing_policy=suppressed` blocks mechanical revoicing openers.
- Writer remains non-scripted: planner is deterministic guidance, not rigid text templating.
