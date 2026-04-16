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

Runtime package includes 20 Python modules (19 functional modules + package initializer):

1. `__init__.py` - package metadata and runtime module map.
2. `bootstrap_runtime_helpers.py` - request bootstrap, memory preload, onboarding/start command guards.
3. `fast_path_stage_helpers.py` - fast-path execution and early-success flow.
4. `full_path_stage_helpers.py` - full generation stage orchestration and success path wiring.
5. `llm_runtime_helpers.py` - LLM invocation support and call-level utilities.
6. `mode_policy_helpers.py` - mode prompt resolution and output-validation policy wiring.
7. `pipeline_utils.py` - shared pipeline helpers and stage-level utility functions.
8. `pricing_helpers.py` - token/cost estimation helpers.
9. `response_common_helpers.py` - shared response builders and observability helpers.
10. `response_failure_helpers.py` - failure/no-retrieval/unhandled-error response paths.
11. `response_success_helpers.py` - full/fast success response composition.
12. `retrieval_pipeline_helpers.py` - retrieval/rerank pipeline internals.
13. `retrieval_stage_helpers.py` - retrieval stage orchestration and handoff to generation.
14. `routing_context_helpers.py` - routing context shaping and practice/context suffixes.
15. `routing_pre_stage_helpers.py` - state analysis, diagnostics, pre-routing decisions.
16. `routing_stage_helpers.py` - compatibility facade for routing split modules.
17. `runtime_adapter_helpers.py` - adapter factories for injected runtime dependencies.
18. `runtime_misc_helpers.py` - compatibility facade for previously split runtime utilities.
19. `state_helpers.py` - state classification, fallback state, and state-context helpers.
20. `trace_helpers.py` - trace payload shaping, LLM canvas payloads, and trace sanitation.

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

