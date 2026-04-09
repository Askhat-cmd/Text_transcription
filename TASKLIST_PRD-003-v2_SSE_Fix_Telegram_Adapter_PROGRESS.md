# TASKLIST PRD-003 v2 SSE Fix + Telegram Adapter (PROGRESS)

Status: IN PROGRESS (code complete, manual checks pending)  
PRD: `PRD-003-v2-SSE-Fix-Telegram-Adapter.md`  
Started: 2026-04-09

## Phase 0 — Intake
- [x] Read PRD and extract scope (FIX-3 + Telegram Adapter Layer).
- [x] Locate active frontend stream integration file(s).
- [x] Confirm current failure scenario from code path (A/B/C) and note evidence.

## Phase 1 — Web SSE Fix (frontend)
- [x] Audit current stream parser in `web_ui/src/services/api.service.ts`.
- [x] Ensure chunk assembly is cumulative (no overwrite by delta).
- [x] Ensure empty SSE separators (`\n\n`) do not trigger early return.
- [x] Ensure timeout is >= 60s and abort handling is user-friendly.
- [x] Ensure UTF-8 decode with streaming mode preserves Cyrillic on chunk boundaries.
- [x] Keep API contract unchanged (`/api/v1/questions/adaptive-stream`).

## Phase 2 — Telegram Adapter Layer
- [x] Create `telegram_adapter/` package skeleton and entrypoint.
- [x] Implement SSE consumer (`api_client/stream_consumer.py`) with full accumulation.
- [x] Implement formatter (`formatters/telegram_formatter.py`) with HTML escaping.
- [x] Implement session persistence (`persistence/session_store.py`) via SQLite.
- [x] Implement handlers (`handlers/message_handler.py`, `handlers/command_handler.py`).
- [x] Implement env/config bootstrap (`config.py`, `.env.example`, `requirements.txt`).
- [x] Add `telegram_sessions.db` ignore rule.

## Phase 3 — Tests
- [x] Add frontend stream unit tests (T2.x equivalent for this project setup).
- [x] Add python unit tests for `stream_consumer` (T4.x).
- [x] Add python unit tests for formatter (T5.x).
- [x] Add python unit tests for session store (T6.x).
- [x] Run targeted frontend tests.
- [x] Run targeted python tests.

## Phase 4 — Validation & Reporting
- [x] Record diagnosis outcome and implementation notes in this file.
- [x] Mark completed checks with concise evidence (test outputs).
- [x] Summarize residual manual checks (T3/T7) requiring real UI/Telegram token.

## Diagnosis Notes
- Frontend integration path found: `bot_psychologist/web_ui/src/services/api.service.ts` + `bot_psychologist/web_ui/src/hooks/useChat.ts`.
- Code-based diagnosis: parser accepted mainly `payload.token` and silently degraded on non-token/plain events, which can cause partial assembly in UI when SSE payload shape diverges.
- Additional reliability gaps fixed:
- `AbortError` from `fetch()` was not caught (fetch call was outside `try/catch`).
- No explicit stream timeout policy on client side.
- Classified as closest to scenario **A/B reliability mix** (assembly fragility in client parser), not strict hard-timeout scenario C in current code.

## Validation Notes
- Frontend unit tests: `npm run test` in `bot_psychologist/web_ui` -> `6 passed`.
- Frontend type check: `npm run lint` in `bot_psychologist/web_ui` -> success.
- Telegram adapter unit tests: `.\.venv\Scripts\python.exe -m pytest -q tests/telegram_adapter` in `bot_psychologist` -> `23 passed`.
- Residual manual checks (not executable from CLI-only environment):
- T3.x DevTools EventStream verification in browser UI.
- T7.x smoke tests with real `TELEGRAM_BOT_TOKEN` from @BotFather.
