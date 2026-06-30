# Frontend Trace Availability Report

## Files Changed
- `web_ui/src/services/api.service.ts`
- `web_ui/src/hooks/useMultiAgentTrace.ts`
- `web_ui/src/components/chat/Message.tsx`
- `web_ui/src/types/chat.types.ts`

## HF3 Frontend Repair
- `apiService.getMultiAgentTrace()` now preserves structured 404 trace-availability payload through `TraceUnavailableError`.
- `useMultiAgentTrace()` now tracks `availability` separately from `trace`.
- Exact turn mismatch no longer ends in silent disappearance; the hook emits:
  - `status=unavailable`
  - `reason_code=turn_mismatch`
  - requested/resolved turn metadata
- `Message.tsx` now renders an owner/dev-only unavailable notice under assistant messages when trace is absent for that turn.

## Result
- Normal public mode remains unchanged.
- Owner/dev mode now gets explicit unavailable-state visibility after reload instead of "no trace block and no explanation".

## Verification
- `src/hooks/useMultiAgentTrace.test.ts`: passed
- `src/components/chat/Message.test.ts`: passed
- `npm run lint`: passed
- `npm run build`: passed
