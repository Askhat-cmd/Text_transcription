# PRD-047.36-HF4 Root Cause Report

Date: 2026-07-01

## Root causes confirmed
1. Streamed assistant turns were not fully persisted into session history under the exact chat `session_id`.
2. Web UI did not send `X-Device-Fingerprint`, so backend identity resolution could drift away from the intended browser session scope.
3. `ChatPage` cleared `bot_active_chat_id` on mount when `activeChatId=''` before session hydration finished, so reload could silently drop the selected fresh chat and reopen a different session.

## Secondary proof-harness issues
- The initial HF4 browser runner also produced false negatives:
  - it raced the new-chat activation after restart;
  - it cleared local storage on every reload through `addInitScript`.
- Those runner defects were repaired, but they were not the product runtime root cause.

## Outcome
- Fresh chats now keep exact trace through delivery, history, reload, and debug lookup.
- Old chats after backend restart now fail honestly with `debug_trace_expired_after_backend_restart` instead of a misleading fresh-chat failure shape.
