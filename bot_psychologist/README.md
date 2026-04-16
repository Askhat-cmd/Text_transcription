# Bot Psychologist

Bot Psychologist is the active Neo MindBot runtime for reflective dialogue, retrieval-backed responses, and developer observability.

## Completion Update (2026-04-16)

`answer_adaptive.py` modularization is completed.

- Waves completed: `1-144`
- Final `answer_adaptive.py` role: facade-orchestrator only
- Final `answer_adaptive.py` size: `418` lines
- Validation baseline: `501 passed, 13 skipped`

## Architecture After Refactoring

`bot_agent/answer_adaptive.py` now orchestrates runtime stages and delegates implementation to `bot_agent/adaptive_runtime/`.

### Orchestration stages

1. Runtime bootstrap and memory preload.
2. State analysis and pre-routing.
3. Retrieval/rerank and routing context shaping.
4. Generation, output validation, and response build.
5. Memory persistence and trace finalization.

## Adaptive Runtime Modules

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

## Scope

- Active workspace: `bot_psychologist/`
- Main user channel: Web chat (`web_ui`)
- Main API: `/api/v1/questions/adaptive` and `/api/v1/questions/adaptive-stream`
- Trace contract: `v2`

## Quick Start

### Backend

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### Frontend

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

Web UI URL: `http://localhost:3000`
API base URL: `http://localhost:8001/api/v1`

## Core Endpoints

### Chat

- `POST /api/v1/questions/adaptive`
- `POST /api/v1/questions/adaptive-stream`

### Sessions

- `GET /api/v1/users/{user_id}/sessions`
- `POST /api/v1/users/{user_id}/sessions`
- `DELETE /api/v1/users/{user_id}/sessions/{session_id}`

### Debug

- `GET /api/debug/session/{session_id}/metrics`
- `GET /api/debug/session/{session_id}/traces`
- `GET /api/debug/session/{session_id}/llm-payload`
- `GET /api/debug/blob/{blob_id}`

## Documentation

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Bot Agent](docs/bot_agent.md)
- [API](docs/api.md)
- [Web UI](docs/web_ui.md)
- [Testing](docs/testing.md)
- [Trace runtime](docs/trace_runtime.md)

## Notes

- `response_utils.py (removed in Wave 142)` was removed in Wave 142.
- Answer-adaptive modularization has no open TODO in active strategy.

