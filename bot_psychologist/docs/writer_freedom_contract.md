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
  - `answer_shape=one_step` enforces one executable step instead of reflective filler.
  - `next_move=repair_misalignment` enforces short repair acknowledgement without reopening loops.
- Writer remains non-scripted: planner is deterministic guidance, not rigid text templating.

## PRD-047.5-HF1 Compliance Tightening
- Added targeted compliance repair for cases exposed by strict evaluator:
  - safety-adjacent outputs (`stabilize_safety`) are forced away from mechanism-language drift;
  - `question_policy=none` avoids latent question invites in final text;
  - `answer_known_concept` + `practice_policy=forbidden` avoids unsolicited practice framing.
- Compliance remains trace-visible and deterministic; no hidden runner-side fallback was introduced.
- Writer freedom stays active, but final-answer policy obedience is now stricter for acceptance-critical planner shapes.

## PRD-047.6 Observability Guard Boundary
- Runtime drift guard is external to Writer generation path.
- Writer freedom remains intact when answer complies with:
  - planner `answer_shape`
  - planner `question_policy`
  - planner `practice_policy`
  - safety policy boundaries
- Drift guard produces warning/critical diagnostics only:
  - trace/debug/admin visibility;
  - replay artifact evidence.
- Drift guard does not block or replace user-visible final answer.

## PRD-047.9 Unified Adaptive Policy Alignment
- `mvp_free_dialogue` remains a developer-local preset within one runtime path.
- In MVP profile, explicit user request for explanation/overview/examples has higher practical authority than advisory planner/diagnostic constraints, while minimal safety baseline stays mandatory.
- Writer prompt now receives explicit `MVP FREE DIALOGUE OVERRIDES` block and context diagnostics (`context_budget_chars`, truncation flags, preserved recent turns counters).
- Context assembly is recency-preserving: latest turns are kept first within profile budget; old-prefix clipping (`[:2000]`) is removed from writer prompt path.
