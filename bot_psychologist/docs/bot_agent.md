# Bot Agent

## Role

`bot_agent` is the core runtime package. It converts a user message into a final assistant answer and a diagnostic trace.

## Main Runtime Path

1. Read request context and session state.
2. Detect user state and resolve route.
3. Retrieve relevant chunks.
4. Optionally apply rerank gate.
5. Build prompt stack.
6. Run LLM call.
7. Validate and format output.
8. Update memory and trace.

## Key Modules

### Routing and State

- `diagnostics_classifier.py`
- `state_classifier.py`
- `route_resolver.py`

### Retrieval

- `data_loader.py`
- `retriever.py`
- `progressive_rag.py`
- `reranker_gate.py`

### Prompt and Generation

- `prompt_registry_v2.py`
- `prompt_system_base.md`
- `prompt_mode_informational.md`
- `llm_answerer.py`
- `llm_streaming.py`

### Response Control

- `output_validator.py`
- `response/response_formatter.py`

### Memory

- `conversation_memory.py`
- `memory_v11.py`
- `memory_v12.py`
- `summary_manager.py`
- `semantic_memory.py`

### Practice and Recommendation

- `practice_selector.py`
- `practice_schema.py`
- `practices_recommender.py`

### Runtime Config

- `runtime_config.py`
- `feature_flags.py`
- `config.py`

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

## Failure Strategy

- Defensive defaults when retrieval or rerank is unavailable.
- Controlled fallback behavior for memory and diagnostics.
- Validation stage can trigger regeneration hints when output quality is low.

## Related Docs

- [Architecture](./architecture.md)
- [Overview](./overview.md)
- [Testing](./testing.md)
