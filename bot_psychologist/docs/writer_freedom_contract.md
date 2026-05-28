# Writer Freedom Contract

## Scope
`PRD-047.1` introduces `Writer Freedom Contract v1` as an explicit guided-freedom policy for Writer.

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

## Contract Semantics
- Writer mode is a hint, not a strict cage.
- One main move per answer is preferred.
- Practice content requires gate permission.
- Hard boundaries remain mandatory (`no_diagnosis`, `no_spiritual_authority`, `no_raw_kb_quote_dumping`, `no_unsolicited_practice`).

## Integration
- Attached to `WriterContract` (`philosophy_kernel`, `writer_freedom_contract`).
- Propagated to writer prompt template and debug trace.
- Exposed in admin runtime effective payload as read-only state.
