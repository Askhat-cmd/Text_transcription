# Trace Runtime Guide (Руководство по trace runtime)

## Purpose (Назначение)
Trace endpoints и UI panels обеспечивают observability для каждого user turn в multiagent runtime.

## Runtime facts (Факты runtime)
- Active runtime path: `multiagent_adapter`
- Legacy cascade trace fields не входят в active runtime contract
- Runtime effective payload включает compact `diagnostic_center_control` snapshot для admin observability.

## Quality Trace v1 (Качество trace v1)
`quality_trace` — compact deterministic audit layer для сигналов качества ответа.
Не меняет answer и не блокирует runtime.

Ожидаемые поля в trace/debug:
- `quality_trace_version=quality_trace_v1`
- `quality_trace.answer/state/thread/memory/continuity/response_mode/validator/summary_flags`
- `quality_trace_error` (nullable fallback marker при сбое сборки trace)

Требование доставки: `quality_trace` должен быть виден не только во internal `orchestrator.debug`,
но и во external debug surfaces:
- `/api/v1/questions/adaptive` с `debug=true`
- `/api/debug/session/{session_id}/traces`
- `/api/debug/session/{session_id}/multiagent-trace`
- baseline live report extraction

## Main endpoints (Основные endpoints)
- `GET /api/debug/session/{session_id}/metrics`
- `GET /api/debug/session/{session_id}/traces?format=full|compact`
- `GET /api/debug/session/{session_id}/llm-payload?format=structured|flat`
- `GET /api/debug/session/{session_id}/multiagent-trace`
- `GET /api/admin/runtime/effective`
- `GET /api/admin/diagnostic-center/effective`

## Access (Доступ)
- Debug endpoints требуют development API key (`X-API-Key`).
- Unauthorized requests должны возвращать `403` для debug surfaces.

## What to verify in trace (Что проверять в trace)
- `runtime_entrypoint=multiagent_adapter`
- `pipeline_version=multiagent_v1`
- `legacy_fallback_used=false`
- writer/model metadata present (`writer_llm.model`, `writer_llm.api_mode`)

## UI Surfaces (Поверхности UI)
- Inline trace в chat message card
- Session trace panel с aggregates
- LLM payload panel для prompt/response diagnostics

## Regression Checks After Trace Changes (Проверки regression после изменений trace)
- `tests/test_llm_payload_endpoint.py`
- `tests/test_debug_metrics_and_export.py`
- `tests/ui/test_trace_ia_refactor_contract.py`
