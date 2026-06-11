# PRD-047.15-HF2-R2 Admin Surface Inventory

## Status

- screenshots directory present: `true`
- screenshot evidence used: `true`
- code audit used: `true`
- runtime payload audit used: `true`

## Before HF2-R2

- Runtime mixed two roles:
  - editable raw runtime config
  - read-only effective runtime cards
- Advanced Controls exposed duplicate navigation layers
- Hybrid Retrieval Planner visibility missing in both Runtime and Web Trace

## After HF2-R2 target

- Runtime = effective observability surface
- Compatibility = legacy/read-only status surface
- Advanced Controls = Compatibility only
- Hybrid Retrieval Planner visible in:
  - Admin Runtime
  - Web Trace
  - compact debug summary

## Warnings

- `ENABLE_KNOWLEDGE_GRAPH` still exists in backend config as a legacy/optional subsystem flag.
- HF2-R2 must not delete that backend capability without a separate cleanup PRD.
- HF2-R2 may hide it from the modern primary Runtime surface and present it as compatibility status only.
