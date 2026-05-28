# Philosophy Kernel

## Scope
`PRD-047.1` introduced internal `NEO Philosophy Kernel`.
`PRD-047.2` calibrated quality and compactness gates.

Module:
- `bot_agent/multiagent/philosophy_kernel.py`

Version:
- `neo_philosophy_kernel_v1`

## Design Rules
- Internal lens layer only, not a user quote source.
- Compact and structured prompt blocks.
- No long raw source passages in prompt/trace.
- Safety and hard boundaries remain authoritative.

## Runtime Payload
`build_philosophy_kernel_runtime_payload(...)` returns:
- `kernel_version`
- `kernel_enabled`
- `quote_policy`
- `practice_policy`
- `selection`
- `prompt_block`
- `writer_freedom_contract`
- `writer_freedom_prompt_block`
- `prompt_compactness`

## Deterministic Lens Selection
Rules include:
- `нейросталкинг` -> `neurostalking`
- imperfect-self phrases -> `imperfect_self_program`
- driver-pressure phrases -> `drivers`
- inner-loop phrases -> `autopilot`
- short-support requests -> `resource_first_contact` + depth suppression

PRD-047.2 selector calibration aliases include:
- imperfect-self: `прошивка`, `потерплю неудачу`
- drivers: `не буду сильным`
- short-support: `не нужны практики`, `побудь со мной коротко`

## Prompt Compactness Gate
Tracked and enforced:
- `philosophy_kernel_prompt_block_chars <= 1800`
- `writer_freedom_contract_chars <= 1000`
- `combined_chars <= 2600`
- `selected_lenses_count <= 3`

## Trace and Admin
- Trace includes sanitized kernel metadata + compactness block.
- Admin runtime effective includes kernel status, budget limits, and last quality calibration summary.
