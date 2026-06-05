# Web Chat Markdown Rendering

- status: current
- last_verified_prd: PRD-047.13

## Active Now
- Web Chat assistant messages render through `ReactMarkdown` with `remark-gfm`.
- Assistant bubbles use `assistant-markdown` styling for visible headings, bold text, lists, markers, and paragraph spacing.
- Browser proof checks real assistant bubble DOM and computed styles.

## Not Production Ready
- Rendering proof is local smoke evidence, not cross-browser production certification.

## How To Test
- Run Web UI build.
- Run HF1 browser smoke and inspect `browser_markdown_real_dom.json` plus screenshot/dom snapshot artifacts.

## PRD-047.13 cleanup note
- This document was re-verified during cleanup-only inventory; runtime behavior was not changed.

