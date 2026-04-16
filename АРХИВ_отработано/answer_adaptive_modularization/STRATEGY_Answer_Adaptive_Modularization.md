# Strategy: `answer_adaptive.py` Modularization

## Status

Completed.

- Completion date: `2026-04-16`
- Waves completed: `1-144`
- Final facade size: `418` lines (`bot_agent/answer_adaptive.py`)
- Final verification baseline: `501 passed, 13 skipped`

## Final Goal (Achieved)

Split `bot_agent/answer_adaptive.py` into focused modules without changing runtime behavior, contracts, or trace semantics.

## Non-Negotiable Invariants (Preserved)

1. Public entrypoint remains `answer_question_adaptive(...)`.
2. API/SSE payload contracts remain backward-compatible.
3. NEO routing/diagnostics behavior remains unchanged.
4. Trace fields and `LLM canvas` contract remain compatible.
5. Full test suite remained green on completion checkpoints.

## Architecture After Refactoring

`answer_adaptive.py` is now a facade-orchestrator. Runtime logic is implemented in `bot_agent/adaptive_runtime/`.

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

## Closure Notes

- `response_utils.py (removed in Wave 142)` was removed in Wave 142.
- All modularization PRD/TASKLIST artifacts (`PRD-015 ... PRD-158`) are historical records of completed work.
- There are no open modularization TODO items in active strategy.

## Archive Policy

- Keep wave PRD/TASKLIST files as immutable implementation history.
- Use this strategy file and `bot_psychologist/README.md` as current source of truth.

