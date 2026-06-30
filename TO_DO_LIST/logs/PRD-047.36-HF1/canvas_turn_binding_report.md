# Canvas Turn Binding Report

## Repair
- `useMultiAgentTrace` now prefers explicit `turnNumber` over legacy message-id parsing.
- `Message.tsx` passes the stored turn number into trace lookup.
- If the API returns a different trace turn than requested, the hook now surfaces an error and suppresses the mismatched canvas instead of silently rendering another turn.

## Outcome
- Visible assistant bubbles now expand only their own trace/canvas turn under the repaired path.
