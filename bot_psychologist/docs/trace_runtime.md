# Trace Runtime Guide

## Purpose
Trace endpoints and UI panels provide observability for each user turn in the multiagent runtime.

## Runtime facts
- Active runtime path: `multiagent_adapter`
- Legacy cascade trace fields are not part of active runtime contract

## Quality trace v1
`quality_trace` — compact deterministic audit layer for answer quality signals.
It does not change the answer and does not block runtime.

Expected fields in trace/debug:
- `quality_trace_version=quality_trace_v1`
- `quality_trace.answer/state/thread/memory/continuity/response_mode/validator/summary_flags`
- `quality_trace_error` (nullable fallback marker if trace build fails)

Delivery requirement: `quality_trace` must be visible not only in internal `orchestrator.debug`,
but also in external debug surfaces:
- `/api/v1/questions/adaptive` with `debug=true`
- `/api/debug/session/{session_id}/traces`
- `/api/debug/session/{session_id}/multiagent-trace`
- baseline live report extraction

## Main endpoints
- `GET /api/debug/session/{session_id}/metrics`
- `GET /api/debug/session/{session_id}/traces?format=full|compact`
- `GET /api/debug/session/{session_id}/llm-payload?format=structured|flat`
- `GET /api/debug/session/{session_id}/multiagent-trace`

## Access
- Debug endpoints require a development API key (`X-API-Key`).
- Unauthorized requests should return `403` for debug surfaces.

## What to verify in trace
- `runtime_entrypoint=multiagent_adapter`
- `pipeline_version=multiagent_v1`
- `legacy_fallback_used=false`
- writer/model metadata present (`writer_llm.model`, `writer_llm.api_mode`)

## UI surfaces
- Inline trace in chat message card
- Session trace panel with aggregates
- LLM payload panel for prompt/response diagnostics

## Regression checks after trace changes
- `tests/test_llm_payload_endpoint.py`
- `tests/test_debug_metrics_and_export.py`
- `tests/ui/test_trace_ia_refactor_contract.py`
