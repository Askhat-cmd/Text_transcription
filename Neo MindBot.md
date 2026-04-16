# Neo MindBot

## Final Runtime Snapshot (2026-04-16)

This document is the high-level architecture snapshot after completing `answer_adaptive.py` modularization.

## Completion Status

- Modularization program: completed
- Scope: Waves `1-144`
- Final orchestrator file: `bot_psychologist/bot_agent/answer_adaptive.py` (`418` lines)
- Tests at completion checkpoint: `501 passed, 13 skipped`

## Architecture After Refactoring

`answer_adaptive.py` now acts only as a facade-orchestrator that coordinates runtime stages:

1. bootstrap and memory preload,
2. state/diagnostics and pre-routing,
3. retrieval/rerank/context shaping,
4. generation and output validation,
5. memory persistence and trace finalization.

All stage logic is moved into `bot_psychologist/bot_agent/adaptive_runtime/`.

## Adaptive Runtime Module Map

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

## Operational Principles

- One production truth for regular and SSE chat flow.
- Backward-compatible response and trace contracts.
- Deterministic routing with explicit diagnostics trace.
- No active runtime dependency on removed `response_utils.py`.

## Canonical Technical Docs

- `bot_psychologist/README.md`
- `bot_psychologist/docs/architecture.md`
- `bot_psychologist/docs/bot_agent.md`
- `bot_psychologist/docs/trace_runtime.md`
