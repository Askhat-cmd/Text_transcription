# Philosophy Kernel

## Scope
`PRD-047.1` adds a compact internal `NEO Philosophy Kernel` for multiagent Writer guidance.

Module:
- `bot_agent/multiagent/philosophy_kernel.py`

Version:
- `neo_philosophy_kernel_v1`

## Design Rules
- Kernel is internal lensing, not a user-facing quote source.
- Kernel payload stays compact and structured.
- Long raw source excerpts are forbidden in prompt/trace artifacts.
- Safety and hard-boundary rules remain dominant.

## Runtime Payload
`build_philosophy_kernel_runtime_payload(...)` returns:
- `kernel_version`
- `kernel_enabled`
- `quote_policy`
- `practice_policy`
- `selection`
- `prompt_block`
- `writer_freedom_contract`

## Lens Selection (v0)
Deterministic rules include:
- `нейросталкинг` -> `neurostalking`
- imperfect-self phrases (`не справлюсь`, `я недостаточен`, etc.) -> `imperfect_self_program`
- driver pressure phrases (`должен`, `надо быть сильным`, etc.) -> `drivers`
- low-resource short-support -> `resource_first_contact` with suppressed depth

## Trace and Admin
- Multiagent trace stores sanitized kernel metadata only.
- Admin runtime effective payload exposes kernel status in read-only form.
