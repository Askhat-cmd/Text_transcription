# Reload History Persistence Report

## Repair
- `ConversationTurnResponse` now exposes `turn_number`.
- History API returns stored `turn_number` for session-backed turns and stable fallback numbering for legacy memory history.
- `ChatPage.historyToMessages()` and `useChat()` now hydrate messages with explicit `turnNumber` and trace-cache keys derived from that value.

## Outcome
- Reloaded chat history rehydrates the same user/assistant ordering and the same trace binding instead of recomputing from fragile array positions.
