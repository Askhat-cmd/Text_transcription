# PRD-047.36-HF4 Reload Trace Restoration Report

Date: 2026-07-01

## Problem before final fix
- `bot_active_chat_id` was persisted, but `ChatPage` removed it on page mount because `activeChatId=''` before sessions finished loading.
- That caused reload to forget the selected fresh chat and reopen the wrong session.

## Repair
- `ChatPage.tsx`
  - stopped clearing `bot_active_chat_id` during initial empty-state hydrate;
  - only clears stored active chat when session loading is complete and there are truly no sessions.

## Live proof
- Pre-restart fresh chat:
  - `active_chat_id` stayed `hf4_web_e3bcd9403f` before and after reload
- Post-restart new chat:
  - `active_chat_id` stayed `4891cf6b-b87b-4070-ba08-eee1a9db97e6` before and after reload
- No fresh reloaded chat showed `Trace unavailable`.
