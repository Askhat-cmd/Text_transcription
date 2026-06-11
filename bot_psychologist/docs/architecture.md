# Architecture (Архитектура)

## Runtime truth (Актуальное состояние runtime)

- Active runtime: `multiagent_adapter`.
- Runtime mode: `multiagent_only`.
- Legacy cascade физически удалён в PRD-041.
- `answer_adaptive.py` — только compatibility shim.

## System Diagram (Диаграмма системы)

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

## Core Components (Основные компоненты)

- `api/` — HTTP surface, identity/conversations, debug/admin endpoints.
- `bot_agent/multiagent/` — реализация active multiagent runtime.
- `bot_agent/answer_adaptive.py` — deprecated shim для compatibility imports.
- `tests/` — regression, inventory, API, multiagent, streaming и admin contracts.

## Observability (наблюдаемость)

- Inline trace в Web UI для dev-mode sessions.
- Debug endpoint: `/api/debug/session/{session_id}/multiagent-trace`.
- Admin runtime contract endpoint: `/api/admin/runtime/effective`.

## Notes (Заметки)

- `MULTIAGENT_ENABLED` и `LEGACY_PIPELINE_ENABLED` — deprecated compatibility flags; они не переключают runtime.
- Telegram adapter остаётся future integration layer, а не active production channel.
