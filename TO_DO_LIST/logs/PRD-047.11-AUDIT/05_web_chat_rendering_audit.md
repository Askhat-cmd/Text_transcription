# Web Chat Rendering Audit

- status: `warning`
- reason: `playwright_not_installed`
- chat_url: `http://127.0.0.1:3000/chat`

Observed truth:
- The runner attempted a real-page audit against the actual chat route.
- `markdown_real_chat_result.json` was produced, but screenshot and DOM proof are incomplete because Playwright was unavailable in the local environment.
- This means the previous synthetic markdown smoke is not sufficient evidence for live user-facing readability.

Checks:
- has_strong: `unverified`
- has_em: `unverified`
- has_ul_or_ol: `unverified`
- paragraph_count_gte_2: `unverified`
- line_height_readable: `unverified`
- message_bubble_width_ok: `unverified`
- not_plain_markdown_text: `unverified`
