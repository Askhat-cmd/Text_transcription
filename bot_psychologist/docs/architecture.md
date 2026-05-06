# Architecture

## Runtime truth

- Active runtime: `multiagent_adapter`.
- Runtime mode: `multiagent_only`.
- Legacy cascade physically removed in PRD-041.
- `answer_adaptive.py` is a compatibility shim only.

## System Diagram

```text
Web UI (React/Vite)
  -> FastAPI (`api/main.py`)
    -> Chat routes (`api/routes/chat.py`)
      -> Multiagent adapter (`bot_agent/multiagent/runtime_adapter.py`)
        -> Orchestrator (`bot_agent/multiagent/orchestrator.py`)
          -> state_analyzer -> thread_manager -> memory_retrieval -> writer -> validator
    -> Debug routes (`api/debug_routes.py`)
    -> Admin runtime contract (`api/admin_routes.py`)
```

## Core Components

- `api/` — HTTP surface, identity/conversations, debug/admin endpoints.
- `bot_agent/multiagent/` — active multiagent runtime implementation.
- `bot_agent/answer_adaptive.py` — deprecated shim for compatibility imports.
- `tests/` — regression, inventory, API, multiagent, streaming and admin contracts.

## Observability

- Inline trace in Web UI for dev-mode sessions.
- Debug endpoint: `/api/debug/session/{session_id}/multiagent-trace`.
- Admin runtime contract endpoint: `/api/admin/runtime/effective`.

## Notes

- `MULTIAGENT_ENABLED` and `LEGACY_PIPELINE_ENABLED` are deprecated compatibility flags and do not switch runtime.
- Telegram adapter remains a future integration layer, not an active production channel.
