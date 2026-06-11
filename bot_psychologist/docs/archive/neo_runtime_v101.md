# Neo Runtime Notes (Заметки Neo Runtime)

Файл сохранён как stable link target для runtime notes.

## Current Runtime Baseline (Текущий baseline runtime)

- Active production path: adaptive runtime.
- Deterministic route resolver enabled.
- Prompt stack v2 enabled.
- Output validation enabled.
- Trace contract version: `v2`.

## Operational Checks (Операционные проверки)

- Non-stream и stream paths должны производить aligned trace semantics.
- Debug payload endpoint должен expose full API to LLM observability для developer sessions.
- Session metrics должны summarize runtime performance без hidden fields.

## Recommended Smoke Checks (Рекомендуемые smoke checks)

1. Отправьте сообщение в Web UI и проверьте полный assistant answer.
2. Откройте inline trace и validate status chips + deep sections.
3. Откройте LLM canvas и подтвердите payload visibility.
4. Export trace JSON и проверьте `trace_contract_version = "v2"`.

## Related files (Связанные файлы)

- `api/routes.py`
- `api/debug_routes.py`
- `web_ui/src/components/chat/InlineDebugTrace.tsx`
- `web_ui/src/components/debug/LLMPayloadPanel.tsx`
