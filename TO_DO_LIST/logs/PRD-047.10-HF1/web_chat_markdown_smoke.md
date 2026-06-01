# Web Chat Markdown Smoke

- status: passed
- component: `web_ui/src/components/chat/Message.tsx`
- renderer: `react-markdown` + `remark-gfm`
- safety: `skipHtml=true`

## Smoke Sample

```markdown
Да. Короткая фраза:

**«Тело напряглось — я это замечаю — беру паузу».**

1. Триггер
2. Реакция
3. Пауза

*Курсивная пометка.*
```

## Result

- Bold/italic/list/paragraph formatting rendered in chat bubble.
- No raw HTML rendering path enabled.
- Frontend build passed after integration.
