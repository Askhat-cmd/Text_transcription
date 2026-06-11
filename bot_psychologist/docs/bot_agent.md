# Bot Agent (Bot Agent)

## Role (Роль)

`bot_agent` — основной runtime package. Преобразует user message в финальный assistant answer плюс diagnostic trace payload.

## Completion Snapshot (Снимок завершения)

- Answer-adaptive modularization waves: `1-144` (completed)
- `answer_adaptive.py`: только facade-orchestrator
- Размер facade: `418` строк
- Baseline completion tests: `501 passed, 13 skipped`

## Main Runtime Path (Основной runtime path)

1. Чтение request context и session state.
2. Detect state и разрешение route/pre-routing mode.
3. Retrieve и rerank relevant chunks.
4. Сборка prompt stack и runtime context.
5. LLM call.
6. Validate и format output.
7. Update memory и finalize trace.

## Architecture After Refactoring (Архитектура после рефакторинга)

### Facade entrypoint

- `answer_adaptive.py`
  - сохраняет public runtime entrypoint `answer_question_adaptive(...)`
  - подключает stage modules и compatibility exports, используемые tests/contracts

### Adaptive runtime modules

Полный список модулей и их назначение: [docs/architecture.md](./architecture.md)

## Data contracts (Data contracts)

Важные contracts, используемые Bot Agent:

- API request/response models в `api/models.py`
- Trace schema structures в `trace_schema.py`
- Runtime config snapshot из `runtime_config.py`

## Observability hooks (Observability hooks)

Bot Agent эмитирует structured telemetry, потребляемую:

- Inline debug trace в Web UI
- Session metrics endpoint
- LLM payload endpoint
- Trace export JSON

## Current Notes (Текущие заметки)

- `response_utils.py (removed in Wave 142)` удалён в Wave 142.
- Открытых modularization TODO в active strategy не осталось.

## Related Docs (Связанные документы)

- [Architecture](./architecture.md)
- [Overview](./overview.md)
- [Testing](./testing.md)
- [Trace Runtime](./trace_runtime.md)
