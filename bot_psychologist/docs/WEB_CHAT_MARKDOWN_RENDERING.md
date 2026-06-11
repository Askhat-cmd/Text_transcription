# Web Chat Markdown Rendering (Рендеринг markdown в Web Chat)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now (Активно сейчас)
- Assistant messages Web Chat рендерятся через `ReactMarkdown` с `remark-gfm`.
- Assistant bubbles используют styling `assistant-markdown` для видимых headings, bold text, lists, markers и paragraph spacing.
- Browser proof проверяет real assistant bubble DOM и computed styles.

## Not Production Ready (Не готово к production)
- Rendering proof — локальное smoke evidence, а не cross-browser production certification.

## How To Test (Как тестировать)
- Запустите Web UI build.
- Запустите HF1 browser smoke и просмотрите `browser_markdown_real_dom.json` плюс screenshot/dom snapshot artifacts.

## PRD-047.13-HF1 cleanup closure note (Заметка о закрытии cleanup PRD-047.13-HF1)
- Документ повторно проверен при закрытии cleanup; runtime behavior не менялся.
