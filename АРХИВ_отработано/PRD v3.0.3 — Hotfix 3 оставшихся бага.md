
***

# PRD v3.0.3 — Hotfix: 3 оставшихся бага

**Проект:** `bot_psychologist` / `web_ui` + `bot_agent`
**Дата:** 2026-03-06
**Статус:** Ready for implementation

***

## Диагностика: точные причины

| \# | Баг | Root cause | Слой |
| :-- | :-- | :-- | :-- |
| 1 | Чанки не раскрываются | `ChunkTraceItem` не имеет поля `text`/`full_text` — бэкенд его не отдаёт | Backend + Frontend types |
| 2 | Токены и стоимость `—` | Бэкенд НЕ пишет `tokens_prompt/completion/total` в top-level trace, они живут только внутри `llm_calls` | Backend + Frontend fallback |
| 3 | История трейсов исчезает | `useTraceCache.ts` создан, но **НИКОГДА не вызывается** из `useChat.ts`; + `sessionStorage` сбрасывается при закрытии браузера | Frontend: интеграция хука |


***

## FIX 1 — Чанки: добавить поле `text` в бэкенд + тип

### Root cause (из кода)

В [`api.types.ts`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/types/api.types.ts) интерфейс `ChunkTraceItem` содержит ТОЛЬКО `preview` — полного текста нет:

```typescript
// ChunkTraceItem — ТЕКУЩЕЕ СОСТОЯНИЕ (баг)
export interface ChunkTraceItem {
  // ... другие поля ...
  preview: string;   // ← ТОЛЬКО превью ~150 символов
  // text: ?          ← НЕТ ПОЛЯ — поэтому chunk?.text всегда undefined
}
```

В `InlineDebugTrace.tsx` логика `hasMore` ВСЕГДА `false`:

```tsx
const fullText = chunk?.text ?? chunk?.full_text; // ← undefined навсегда
const hasMore = Boolean(fullText && ...);         // ← false: кнопка не рендерится
```


### Fix 1a — Backend: [`answer_adaptive.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_adaptive.py)

Найти место где формируются объекты `ChunkTraceItem` (поиск по `preview` или `block_id`). Добавить поле `text`:

```python
# В answer_adaptive.py — при формировании chunk trace items
# НАЙТИ паттерн типа:
# {
#     "block_id": block.block_id,
#     "preview": block.text[:150],
#     ...
# }
# ДОБАВИТЬ поле text:

{
    "block_id": block.block_id,
    "title": getattr(block, "title", ""),
    "sd_level": getattr(block, "sd_level", ""),
    "sd_secondary": getattr(block, "sd_secondary", ""),
    "emotional_tone": getattr(block, "emotional_tone", ""),
    "score_initial": float(getattr(block, "score_initial", 0)),
    "score_final": float(getattr(block, "score_final", 0)),
    "passed_sd_filter": bool(getattr(block, "passed_sd_filter", False)),
    "filter_reason": getattr(block, "filter_reason", ""),
    "preview": (block.text or "")[:150],
    "text": block.text or "",          # ← ДОБАВИТЬ: полный текст чанка
}
```


### Fix 1b — Frontend: [`api.types.ts`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/types/api.types.ts)

```typescript
// ДОБАВИТЬ поле text к ChunkTraceItem:
export interface ChunkTraceItem {
  block_id: string;
  title: string;
  sd_level: string;
  sd_secondary: string;
  emotional_tone: string;
  score_initial: number;
  score_final: number;
  passed_sd_filter: boolean;
  filter_reason: string;
  preview: string;
  text?: string | null;   // ← ДОБАВИТЬ это поле
}
```

После этого `ChunkRow` в `InlineDebugTrace.tsx` уже написан правильно — кнопка `▼ Развернуть` появится автоматически.

***

## FIX 2 — Токены и стоимость: двойной фикс (backend + frontend fallback)

### Root cause

Бэкенд заполняет `tokens_prompt/completion/total` внутри каждого объекта `llm_calls`, но **НЕ агрегирует** их на верхний уровень trace. Frontend пытается читать `trace.tokens_prompt` — получает `null`.

### Fix 2a — Backend: [`answer_adaptive.py`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/bot_agent/answer_adaptive.py)

Найти место финальной сборки trace-объекта. Добавить агрегацию токенов:

```python
# В конце функции формирования trace (перед return или dict()):
# ДОБАВИТЬ агрегацию:

llm_calls_list = trace.get("llm_calls", [])
total_prompt = sum(c.get("tokens_prompt") or 0 for c in llm_calls_list)
total_completion = sum(c.get("tokens_completion") or 0 for c in llm_calls_list)

# Записать в trace только если ещё не заполнено
if not trace.get("tokens_prompt") and total_prompt:
    trace["tokens_prompt"] = total_prompt
if not trace.get("tokens_completion") and total_completion:
    trace["tokens_completion"] = total_completion
if not trace.get("tokens_total") and (total_prompt or total_completion):
    trace["tokens_total"] = total_prompt + total_completion
```


### Fix 2b — Frontend: [`InlineDebugTrace.tsx`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/components/chat/InlineDebugTrace.tsx)

Добавить `useMemo` с fallback-агрегацией из `llm_calls` для случаев, когда бэкенд всё ещё не заполняет top-level поля:

```tsx
// Добавить в InlineDebugTrace после объявления llmCalls:

const tokenStats = useMemo(() => {
  // Приоритет: top-level поля trace, fallback: сумма из llm_calls
  const p = trace.tokens_prompt
    ?? llmCalls.reduce((s, c) => s + (c.tokens_prompt ?? 0), 0) || null;
  const c = trace.tokens_completion
    ?? llmCalls.reduce((s, c) => s + (c.tokens_completion ?? 0), 0) || null;
  const t = trace.tokens_total
    ?? ((p != null && c != null) ? p + c : null);
  return { prompt: p, completion: c, total: t };
}, [trace.tokens_prompt, trace.tokens_completion, trace.tokens_total, llmCalls]);
```

Затем заменить рендер токенов (в секции `debug-cost`):

```tsx
// БЫЛО:
<span>prompt: <b>{trace.tokens_prompt ?? '—'}</b></span>
<span>completion: <b>{trace.tokens_completion ?? '—'}</b></span>
<span>total: <b className="text-amber-600">{trace.tokens_total ?? '—'}</b></span>

// СТАЛО:
<span>prompt: <b>{tokenStats.prompt ?? '—'}</b></span>
<span>completion: <b>{tokenStats.completion ?? '—'}</b></span>
<span>total: <b className="text-amber-600 dark:text-amber-400 font-bold">
  {tokenStats.total ?? '—'}
</b></span>
```


***

## FIX 3 — Персистентность трейсов: интеграция `useTraceCache` в `useChat.ts`

### Root cause (из кода)

Файл [`useChat.ts`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/hooks/useChat.ts) — **нет ни одного импорта или вызова `useTraceCache`**. Хук создан но мёртв. Плюс `useTraceCache.ts` использует `sessionStorage` — данные удаляются при закрытии вкладки .

**Ключевая проблема hydration**: сообщения из БД приходят с серверными UUID, а в `useChat.ts` ID генерируются как `${sessionId}-b-${turnIndex}`. Они никогда не совпадут. Решение — ключ по **позиции в разговоре**: `{sessionId}:turn:{N}` (N = индекс бот-сообщения).

### Fix 3a — [`useTraceCache.ts`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/hooks/useTraceCache.ts): `sessionStorage` → `localStorage`

```typescript
// ЗАМЕНИТЬ во всём файле sessionStorage → localStorage
// (2 вхождения: в setTrace и ensureLoaded)

// БЫЛО:
const raw = sessionStorage.getItem(storageKey);
...
sessionStorage.setItem(storageKey, JSON.stringify(entries));

// СТАЛО:
const raw = localStorage.getItem(storageKey);
...
localStorage.setItem(storageKey, JSON.stringify(entries));
```


### Fix 3b — [`useChat.ts`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/hooks/useChat.ts): интегрировать `useTraceCache`

```typescript
// ─── ДОБАВИТЬ ИМПОРТ в начало файла ───────────────────────────────
import { useTraceCache } from './useTraceCache';

// ─── ДОБАВИТЬ внутри useChat, рядом с другими useState ────────────
const traceCacheId = sessionId ?? userId ?? 'default';
const { setTrace, getTrace } = useTraceCache(traceCacheId);

// ─── ИЗМЕНИТЬ в sendQuestion, после addMessage('bot', ...) ─────────
// НАЙТИ:
addMessage('bot', finalText, {
  id: botMessageId,
  processingTime: doneMeta?.latency_ms ? doneMeta.latency_ms / 1000 : undefined,
  trace: doneMeta?.trace ?? undefined,
});

// ЗАМЕНИТЬ НА:
const botTrace = doneMeta?.trace ?? undefined;
const botTurnIndex = Math.floor(messagesRef.current.length / 2); // индекс до добавления сообщения
addMessage('bot', finalText, {
  id: botMessageId,
  processingTime: doneMeta?.latency_ms ? doneMeta.latency_ms / 1000 : undefined,
  trace: botTrace,
});
// Сохранить трейс по позиции (не по ID, т.к. ID из БД не совпадают)
if (botTrace) {
  setTrace(`turn:${botTurnIndex}`, botTrace);
}

// ─── ИЗМЕНИТЬ replaceMessages: добавить hydration ─────────────────
// БЫЛО:
const replaceMessages = useCallback((nextMessages: Message[]) => {
  const normalized = nextMessages.map(normalizeMessage);
  setMessages(normalized);
  ...
}, []);

// СТАЛО:
const replaceMessages = useCallback((nextMessages: Message[]) => {
  const normalized = nextMessages.map(normalizeMessage);

  // Hydration: восстановить трейсы по порядку бот-сообщений
  let botIndex = 0;
  const hydrated = normalized.map((msg) => {
    if (msg.role === 'bot') {
      const cached = getTrace(`turn:${botIndex}`);
      botIndex++;
      // Не перезаписывать если trace уже есть в сообщении
      if (cached && !msg.trace) {
        return { ...msg, trace: cached };
      }
    }
    return msg;
  });

  setMessages(hydrated);

  const lastBotMessage = getLastBotMessage(hydrated);
  setCurrentUserState(lastBotMessage?.state);
  setCurrentStateConfidence(lastBotMessage?.confidence);
  setIsLoading(false);
  setError(null);
}, [getTrace]);   // ← добавить getTrace в зависимости
```


***

## Итоговая таблица изменений

| Файл | Тип | Изменение |
| :-- | :-- | :-- |
| `bot_agent/answer_adaptive.py` | **ИЗМЕНИТЬ** | Добавить `text` в chunk items + агрегация токенов |
| `web_ui/src/types/api.types.ts` | **ИЗМЕНИТЬ** | `ChunkTraceItem.text?: string \| null` |
| `web_ui/src/components/chat/InlineDebugTrace.tsx` | **ИЗМЕНИТЬ** | `tokenStats` useMemo + обновить рендер токенов |
| `web_ui/src/hooks/useTraceCache.ts` | **ИЗМЕНИТЬ** | `sessionStorage` → `localStorage` |
| `web_ui/src/hooks/useChat.ts` | **ИЗМЕНИТЬ** | Импорт + `setTrace` при ответе + hydration в `replaceMessages` |

## Definition of Done

- [ ] Каждый чанк раскрывается кнопкой `▼ Развернуть` — видно полный текст
- [ ] `prompt: 1234`, `completion: 456`, `total: 1690` — числа, не `—`
- [ ] `$0.002340` — реальная стоимость, не `$0.000000`
- [ ] При открытии вчерашнего чата — трейс всех сообщений виден
