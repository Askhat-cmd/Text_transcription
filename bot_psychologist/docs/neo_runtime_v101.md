# Neo Runtime Notes

This file is kept as a stable link target for runtime notes.

## Current Runtime Baseline

- Active production path: adaptive runtime.
- Deterministic route resolver enabled.
- Prompt stack v2 enabled.
- Output validation enabled.
- Trace contract version: `v2`.

## Operational Checks

- Non-stream and stream paths must produce aligned trace semantics.
- Debug payload endpoint must expose full API to LLM observability for developer sessions.
- Session metrics should summarize runtime performance without hidden fields.

## Recommended Smoke Checks

1. Send a message in Web UI and verify a full assistant answer.
2. Open inline trace and validate status chips + deep sections.
3. Open LLM canvas and confirm payload visibility.
4. Export trace JSON and verify `trace_contract_version = "v2"`.

## Related files

- `api/routes.py`
- `api/debug_routes.py`
- `web_ui/src/components/chat/InlineDebugTrace.tsx`
- `web_ui/src/components/debug/LLMPayloadPanel.tsx`
