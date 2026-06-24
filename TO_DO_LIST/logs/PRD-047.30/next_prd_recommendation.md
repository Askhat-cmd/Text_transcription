# Next PRD Recommendation After PRD-047.30

Date: 2026-06-24
Status: recommended

## Recommendation

`PRD-047.31 - Legacy Advisory Retirement / Writer Prompt Noise Collapse v1`

## Why This Is the Best Next Step

PRD-047.30 fixed the main Writer-visible grounding authority problem without changing routes or storage. The biggest remaining noise class is now narrower:

- duplicate advisory wording still overlaps with `final_answer_directive_v1`
- retrieval context and payload context can still feel redundant
- semantic cards are now safely throttled, so the next useful work is cleanup/retirement evidence, not another new control layer

## What PRD-047.31 Should Do

- measure remaining advisory duplication on real prompt canvases
- move more duplicate prose to trace-only where safe
- prove no hidden fallback still pushes internal wording into Writer
- keep direct KB/source/safety grounding intact

## What It Should Not Do

- no new planner
- no new route
- no DB/Chroma mutation
- no thin-spine live apply
