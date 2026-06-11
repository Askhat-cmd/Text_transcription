# Philosophy Kernel (Ядро философии)

## Scope (Область)
`PRD-047.1` ввёл internal `NEO Philosophy Kernel`.
`PRD-047.2` откалибровал quality и compactness gates.

Модуль:
- `bot_agent/multiagent/philosophy_kernel.py`

Версия:
- `neo_philosophy_kernel_v1`

## Design Rules (Правила проектирования)
- Только internal lens layer, не user quote source.
- Compact и structured prompt blocks.
- Без длинных raw source passages в prompt/trace.
- Safety и hard boundaries остаются authoritative.

## Runtime Payload (Runtime payload данных)
`build_philosophy_kernel_runtime_payload(...)` возвращает:
- `kernel_version`
- `kernel_enabled`
- `quote_policy`
- `practice_policy`
- `selection`
- `prompt_block`
- `writer_freedom_contract`
- `writer_freedom_prompt_block`
- `prompt_compactness`

## Deterministic Lens Selection (Детерминированный выбор lens)
Правила включают:
- `нейросталкинг` -> `neurostalking`
- imperfect-self phrases -> `imperfect_self_program`
- driver-pressure phrases -> `drivers`
- inner-loop phrases -> `autopilot`
- short-support requests -> `resource_first_contact` + depth suppression

Калибровочные aliases selector PRD-047.2 включают:
- imperfect-self: `прошивка`, `потерплю неудачу`
- drivers: `не буду сильным`
- short-support: `не нужны практики`, `побудь со мной коротко`

## Prompt Compactness Gate (Gate компактности prompt)
Отслеживается и enforce:
- `philosophy_kernel_prompt_block_chars <= 1800`
- `writer_freedom_contract_chars <= 1000`
- `combined_chars <= 2600`
- `selected_lenses_count <= 3`

## Trace and Admin (Trace и Admin-панель)
- Trace включает sanitized kernel metadata + compactness block.
- Admin runtime effective включает kernel status, budget limits и last quality calibration summary.
