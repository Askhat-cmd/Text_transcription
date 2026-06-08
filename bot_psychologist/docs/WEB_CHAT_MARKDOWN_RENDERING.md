# Web Chat Markdown Rendering

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now
- Web Chat assistant messages render through `ReactMarkdown` with `remark-gfm`.
- Assistant bubbles use `assistant-markdown` styling for visible headings, bold text, lists, markers, and paragraph spacing.
- Browser proof checks real assistant bubble DOM and computed styles.

## Not Production Ready
- Rendering proof is local smoke evidence, not cross-browser production certification.

## How To Test
- Run Web UI build.
- Run HF1 browser smoke and inspect `browser_markdown_real_dom.json` plus screenshot/dom snapshot artifacts.

## PRD-047.13-HF1 cleanup closure note
- This document was re-verified during cleanup closure; runtime behavior was not changed.

