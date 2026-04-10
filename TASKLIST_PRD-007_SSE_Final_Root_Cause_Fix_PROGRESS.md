# TASKLIST PRD-007 — SSE Final Root Cause Fix (PROGRESS)

## Контекст
- PRD: `PRD-007-SSE-Final-Root-Cause-Fix.md`
- Статус: В работе
- Дата старта: 2026-04-10

## A. Parser contract (critical)
- [x] A1. Убрать premature `flushEvent()` из веток `event:` и `data:` в `api.service.ts`
- [x] A2. Добавить EOF flush незавершенного события в конце stream-чтения
- [x] A3. Изолировать `trace`-event: не влияет на `fullText` и `doneReceived`
- [x] A4. Зафиксировать `done.answer` как канонический финальный текст
- [x] A5. Обработать degraded/end cases: no done + has text, no done + no text
- [x] A6. Оставить legacy completion marker `[DONE]` / `done`

## B. Test contract repair
- [x] B1. Перевести SSE тесты на валидный framing (`\n\n` между событиями)
- [x] B2. Добавить helper `buildSSEStream()` для валидных фикстур
- [x] B3. Оставить/добавить negative test про invalid single-`\n` fixture
- [x] B4. Проверить/добавить кейсы: EOF flush, trace isolation, done.answer priority, cyrillic chunks, keep-alive

## C. Hook hardening
- [x] C1. Проверить `useChat.ts`: явная очистка `streamingText` после финализации
- [x] C2. Проверить fallback-логику финального ответа при degraded stream

## D. Observability
- [x] D1. DEV-only warnings/info в SSE parser
- [x] D2. Исправить лог `max_completion_tokens` в `llm_answerer.py` (числовое значение)

## E. Validation
- [x] E1. Vitest: `api.stream.test.ts`
- [x] E2. Pytest: stream/debug контрактные тесты
- [x] E3. Обновить tasklist фактическими результатами

## Факт выполнения
- 2026-04-10: `npm run test -- src/services/api.stream.test.ts src/hooks/useChat.test.ts` → 16 passed.
- 2026-04-10: `.venv\\Scripts\\python.exe -m pytest -q tests/integration/test_adaptive_stream_contract.py` → 6 passed.
- 2026-04-10: `.venv\\Scripts\\python.exe -m pytest -q tests/test_llm_answerer.py` → 8 passed.
