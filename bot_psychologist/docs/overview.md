# Project Overview

## Purpose

Bot Psychologist is a Neo MindBot system for reflective conversations.
It combines retrieval from `Bot_data_base`, adaptive routing, memory context, and observable runtime diagnostics.

## Main Goals

- Provide psychologically careful responses with practical next steps.
- Keep response quality stable in both normal and streaming modes.
- Preserve transparent developer observability for every assistant turn.

## Runtime Layers

1. **API layer** (`api/`): request validation, chat endpoints, sessions, debug and admin routes.
2. **Agent layer** (`bot_agent/`): routing, retrieval, prompt assembly, generation, validation, memory update.
3. **Storage layer** (`data/`, `bot_agent/storage/`): sessions, traces, admin overrides.
4. **UI layer** (`web_ui/`): chat interface, inline trace, admin controls.

## User Flow

1. User sends a message from Web UI.
2. API calls adaptive runtime.
3. Runtime resolves route and user state.
4. Retriever selects relevant chunks and optional rerank.
5. Prompt stack is built and sent to LLM.
6. Response is validated and formatted.
7. Memory state is updated.
8. Trace `v2` is returned for developer diagnostics.

## Observability

The inline trace in Web UI is split into two levels:

- **Simple layer**: compact status chips for quick health checks.
- **Deep layer**: collapsible sections with routing, retrieval, LLM calls, memory, and config snapshot.

Developer LLM canvas is available only for developer key sessions.

## Core Entry Points

- Backend app: `api/main.py`
- Main chat routes: `api/routes.py`
- Debug routes: `api/debug_routes.py`
- Admin routes: `api/admin_routes.py`
- Adaptive runtime: `bot_agent/answer_adaptive.py`

## Related Docs

- [Architecture](./architecture.md)
- [Bot Agent](./bot_agent.md)
- [API](./api.md)
- [Web UI](./web_ui.md)
- [Testing](./testing.md)
