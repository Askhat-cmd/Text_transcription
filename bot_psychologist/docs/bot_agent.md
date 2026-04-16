# Bot Agent

## Role

`bot_agent` is the core runtime package. It converts a user message into a final assistant answer plus diagnostic trace payload.

## Completion Snapshot

- Answer-adaptive modularization waves: `1-144` (completed)
- `answer_adaptive.py`: facade-orchestrator only
- Facade size: `418` lines
- Completion test baseline: `501 passed, 13 skipped`

## Main Runtime Path

1. Read request context and session state.
2. Detect state and resolve route/pre-routing mode.
3. Retrieve and rerank relevant chunks.
4. Build prompt stack and runtime context.
5. Run LLM call.
6. Validate and format output.
7. Update memory and finalize trace.

## Architecture After Refactoring

### Facade Entrypoint

- `answer_adaptive.py`
  - keeps public runtime entrypoint `answer_question_adaptive(...)`
  - wires stage modules and compatibility exports used by tests/contracts

### Adaptive Runtime Modules

Полный список модулей и их назначение: [docs/architecture.md](./architecture.md)

## Data Contracts

Important contracts used by Bot Agent:

- API request/response models in `api/models.py`
- Trace schema structures in `trace_schema.py`
- Runtime config snapshot from `runtime_config.py`

## Observability Hooks

Bot Agent emits structured telemetry consumed by:

- Inline debug trace in Web UI
- Session metrics endpoint
- LLM payload endpoint
- Trace export JSON

## Current Notes

- `response_utils.py (removed in Wave 142)` was removed in Wave 142.
- No open modularization TODO remains in active strategy.

## Related Docs

- [Architecture](./architecture.md)
- [Overview](./overview.md)
- [Testing](./testing.md)
- [Trace Runtime](./trace_runtime.md)

