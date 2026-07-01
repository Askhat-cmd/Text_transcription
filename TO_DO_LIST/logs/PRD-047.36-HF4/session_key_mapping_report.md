# PRD-047.36-HF4 Session Key Mapping Report

Date: 2026-07-01

## Fresh Web Chat key chain
- Frontend selected chat: `activeChatId`
- Persisted reload key: `localStorage.bot_active_chat_id`
- Browser identity key: `localStorage.bot_web_session_id`
- Request body:
  - `session_id = activeChatId`
- Headers:
  - `X-Session-Id = bot_web_session_id`
  - `X-Device-Fingerprint = bot_web_session_id`
- Backend history/debug persistence:
  - delivered turn is stored under chat `session_id`
- Debug endpoint lookup:
  - `/api/debug/session/{session_id}/multiagent-trace?turn_index=N`

## Verified live session identities
- Pre-restart fresh chat:
  - `old_session_id = hf4_web_e3bcd9403f`
- Post-restart new chat:
  - `new_session_id = 4891cf6b-b87b-4070-ba08-eee1a9db97e6`
- Browser reload kept:
  - `active_chat_id = 4891cf6b-b87b-4070-ba08-eee1a9db97e6`

## Conclusion
- Session identity is now exact and stable across frontend active chat, streaming request, backend persistence, history reload, and debug trace lookup.
