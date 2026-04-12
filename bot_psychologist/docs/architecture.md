# Architecture

## System Diagram

```text
Web UI (React)
  -> FastAPI (`api/main.py`)
    -> Adaptive runtime (`bot_agent/answer_adaptive.py`)
      -> Routing and state detection
      -> Retrieval and rerank
      -> Prompt stack build
      -> LLM generation
      -> Output validation
      -> Memory update
    -> Trace store / debug routes
```

## Components

### 1. Web UI (`web_ui/`)

- Chat page and session list.
- Inline debug trace panel for developer sessions.
- Admin panel for runtime config and prompt controls.

### 2. API (`api/`)

- `routes.py`: chat, sessions, utility endpoints.
- `debug_routes.py`: trace, payload, and metrics endpoints.
- `admin_routes.py`: runtime config, prompts, diagnostics controls.
- `models.py`: request/response and trace schemas.

### 3. Runtime (`bot_agent/`)

- `route_resolver.py`: deterministic route selection.
- `state_classifier.py`: user state inference.
- `retriever.py`: chunk retrieval from knowledge source.
- `reranker_gate.py`: rerank decision and application.
- `prompt_registry_v2.py`: prompt assembly from prompt blocks.
- `llm_answerer.py` and `llm_streaming.py`: LLM execution paths.
- `output_validator.py`: post-generation quality and safety checks.
- `conversation_memory.py`, `memory_v12.py`: conversational memory operations.

### 4. Storage and Data

- `data/admin_overrides.json`: runtime overrides from admin panel.
- `data/bot_sessions.db`: session storage.
- In-memory trace blobs for developer diagnostics.
- External knowledge access through `Bot_data_base` API.

## Runtime Principles

- One production runtime truth for standard and streaming requests.
- Deterministic route resolver and explicit diagnostics output.
- Prompt stack composition is centralized and observable.
- Trace contract is versioned (`v2`) for stable UI rendering.

## Trace Contract v2

Required high-level fields include:

- `trace_contract_version`
- `session_id`, `turn_number`
- `recommended_mode`, `user_state`, `decision_rule_id`
- `confidence_score`, `confidence_level`
- `pipeline_stages`, `llm_calls`, `anomalies`
- `chunks_retrieved`, `chunks_after_filter`
- `tokens_prompt`, `tokens_completion`, `tokens_total`
- `estimated_cost_usd`, `total_duration_ms`
- `config_snapshot`

## Deployment Shape

- Local development: Uvicorn + Vite.
- Runtime logs: `logs/`.
- Optional reverse proxy deployment supported via standard FastAPI setup.

## References

- [Project Overview](./overview.md)
- [Bot Agent](./bot_agent.md)
- [API](./api.md)
- [Web UI](./web_ui.md)
