# Architecture

## System Diagram

```text
Web UI (React)
  -> FastAPI (`api/main.py`)
    -> Facade Orchestrator (`bot_agent/answer_adaptive.py`)
      -> Adaptive runtime stages (`bot_agent/adaptive_runtime/*`)
        -> bootstrap / state / routing / retrieval / generation / validation / memory / trace
    -> Trace store / debug routes
```

## Completion Snapshot

- Modularization waves: `1-144` (completed)
- Facade size: `418` lines (`answer_adaptive.py`)
- Test checkpoint: `501 passed, 13 skipped`

## Runtime Components

### 1. Web UI (`web_ui/`)

- Chat page and session list.
- Inline debug trace panel for developer sessions.
- Admin panel for runtime config and prompt controls.

### 2. API (`api/`)

- `routes.py`: chat, sessions, utility endpoints.
- `debug_routes.py`: trace, payload, and metrics endpoints.
- `admin_routes.py`: runtime config, prompts, diagnostics controls.
- `models.py`: request/response and trace schemas.

### 3. Bot Runtime (`bot_agent/`)

- `answer_adaptive.py`: facade-orchestrator.
- `adaptive_runtime/`: implementation of runtime stages and shared helpers.
- `route_resolver.py`, `state_classifier.py`: route/state inference.
- `prompt_registry_v2.py`: prompt assembly.
- `output_validator.py`: output quality/safety checks.
- `conversation_memory.py`, `memory_v12.py`: memory operations.

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

## Runtime Principles

- One production runtime truth for standard and streaming requests.
- Deterministic route resolver and explicit diagnostics output.
- Prompt stack composition is centralized and observable.
- Trace contract is versioned (`v2`) for stable UI rendering.

## Trace Contract v2 (high level)

- `trace_contract_version`
- `session_id`, `turn_number`
- `recommended_mode`, `user_state`, `decision_rule_id`
- `confidence_score`, `confidence_level`
- `pipeline_stages`, `llm_calls`, `anomalies`
- `chunks_retrieved`, `chunks_after_filter`
- `tokens_prompt`, `tokens_completion`, `tokens_total`
- `estimated_cost_usd`, `total_duration_ms`
- `config_snapshot`

## References

- [Project Overview](./overview.md)
- [Bot Agent](./bot_agent.md)
- [API](./api.md)
- [Web UI](./web_ui.md)
- [Trace Runtime](./trace_runtime.md)
