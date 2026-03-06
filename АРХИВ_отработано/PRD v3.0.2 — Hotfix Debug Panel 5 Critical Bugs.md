
**Проблема 1** — трейс живёт только в React-state, который сбрасывается при смене чата. При возврате история грузится из БД без trace.
**Проблема 2** — у внешнего `<div>` нет никакого toggle, всё всегда `open`.
**Проблема 3** — `ChunkRow` рендерит `chunk.preview` без `useState` expand — просто `<p>` без кнопки.
**Проблема 4** — секция `debug-cost` — `<details>` без атрибута `open`, т.е. свёрнута по умолчанию.
**Проблема 5** — порядок секций: сначала аномалии и конфиг, потом timeline — не отражает поток оркестрации.

Теперь у меня полная картина кода. Составляю полный PRD-фикс документ для IDE агента.

***

# PRD v3.0.2 — Hotfix: Debug Panel 5 Critical Bugs

**Проект:** `bot_psychologist` / `web_ui`
**Дата:** 2026-03-04
**Статус:** Ready for implementation
**Приоритет:** Critical (5 регрессий после v3.0.1)
**Целевой исполнитель:** IDE Agent (Cursor / Windsurf)

***

## 0. КАРТА ПРОБЛЕМ

| \# | Проблема | Root cause | Файл | Сложность |
| :-- | :-- | :-- | :-- | :-- |
| 1 | Трейс исчезает при смене чата | Трейс живёт только в React-state; история из БД грузится без него | `ChatPage.tsx` + хранилище | M |
| 2 | Панель всегда развёрнута | Внешний `<div>` — не `<details>`, внутренние `open` = всегда | `InlineDebugTrace.tsx` | S |
| 3 | Чанк не раскрывается полностью | `ChunkRow` рендерит `chunk.preview` без `useState` expand | `InlineDebugTrace.tsx` | XS |
| 4 | Нет стоимости и токенов | `<details id="debug-cost">` без атрибута `open` | `InlineDebugTrace.tsx` | XS |
| 5 | Порядок секций не отражает оркестрацию | Аномалии и конфиг раньше timeline; хаотичная последовательность | `InlineDebugTrace.tsx` | S |


***

## 1. FIX 1 — Трейс-персистентность через `sessionStorage`

### Корень проблемы

В [`ChatPage.tsx`](https://github.com/Askhat-cmd/Text_transcription/blob/main/bot_psychologist/web_ui/src/pages/ChatPage.tsx) (или аналоге) при получении ответа от бота трейс хранится внутри `Message.debug_trace`. При переключении чата React-state сбрасывается. При загрузке истории из БД бэкенд возвращает сообщения **без поля `debug_trace`** — оно не сохраняется в БД-таблице `messages`.

### Стратегия фикса: `sessionStorage` cache, hydration при загрузке истории

Это минимально-инвазивный фикс: не трогаем БД, не трогаем `Message.tsx`/`MessageList.tsx`.

### 1.1 Новый хук `useTraceCache.ts`

```typescript
// web_ui/src/hooks/useTraceCache.ts
// СОЗДАТЬ НОВЫЙ ФАЙЛ

import { useCallback, useRef } from 'react';
import type { InlineTrace } from '../types';

const STORAGE_KEY_PREFIX = 'debug_trace_cache_';
const MAX_ENTRIES = 100; // максимум трейсов на чат в sessionStorage

interface TraceEntry {
  messageId: string;
  trace: InlineTrace;
}

export function useTraceCache(chatId: string) {
  // In-memory кэш для текущей сессии (быстрый доступ)
  const memCache = useRef<Map<string, InlineTrace>>(new Map());

  const storageKey = `${STORAGE_KEY_PREFIX}${chatId}`;

  // Загрузить кэш из sessionStorage при первом обращении
  const ensureLoaded = useCallback(() => {
    if (memCache.current.size > 0) return;
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (raw) {
        const entries: TraceEntry[] = JSON.parse(raw);
        entries.forEach(({ messageId, trace }) => {
          memCache.current.set(messageId, trace);
        });
      }
    } catch {
      // Ignore parse errors
    }
  }, [storageKey]);

  // Сохранить трейс
  const setTrace = useCallback((messageId: string, trace: InlineTrace) => {
    ensureLoaded();
    memCache.current.set(messageId, trace);
    // Персистентность в sessionStorage
    try {
      const entries: TraceEntry[] = Array.from(memCache.current.entries())
        .slice(-MAX_ENTRIES)
        .map(([id, t]) => ({ messageId: id, trace: t }));
      sessionStorage.setItem(storageKey, JSON.stringify(entries));
    } catch {
      // sessionStorage may be full — ignore
    }
  }, [ensureLoaded, storageKey]);

  // Получить трейс по message_id
  const getTrace = useCallback((messageId: string): InlineTrace | undefined => {
    ensureLoaded();
    return memCache.current.get(messageId);
  }, [ensureLoaded]);

  // Очистить при смене чата
  const clearCache = useCallback(() => {
    memCache.current.clear();
    sessionStorage.removeItem(storageKey);
  }, [storageKey]);

  return { setTrace, getTrace, clearCache };
}
```


### 1.2 Изменения в `ChatPage.tsx` (или где живёт логика отправки/загрузки)

> ⚠️ **ВАЖНО:** `Message.tsx`, `MessageList.tsx`, `ChatWindow.tsx` — **НЕ ТРОГАТЬ** (запрет из PRD v2.0.6). Все изменения — только в родительском page-компоненте.

Найти файл, где происходит:

- `onSendMessage` — обработка ответа с трейсом
- Загрузка истории (`fetchMessages` / `loadHistory`)

Добавить следующий паттерн:

```typescript
// В ChatPage.tsx (или аналоге) — ДОБАВИТЬ к существующему коду

import { useTraceCache } from '../hooks/useTraceCache';

// Внутри компонента, рядом с chatId:
const { setTrace, getTrace, clearCache } = useTraceCache(activeChatId ?? 'default');

// --- При получении ответа от бота ---
// Найти место, где добавляется message в state после API-ответа.
// После успешного ответа ДОБАВИТЬ сохранение трейса:
//
// const botMessage: Message = {
//   id: response.message_id,        ← должен быть уникальный id
//   role: 'assistant',
//   content: response.answer,
//   debug_trace: response.debug_trace,  ← уже есть
// };
// setMessages(prev => [...prev, botMessage]);
//
// ДОБАВИТЬ ПОСЛЕ:
if (response.debug_trace && response.message_id) {
  setTrace(response.message_id, response.debug_trace);
}

// --- При загрузке истории из БД ---
// Найти место, где messages устанавливаются из API (loadHistory / fetchMessages).
// После setMessages(loadedMessages) ДОБАВИТЬ гидрацию:
//
// const hydratedMessages = loadedMessages.map(msg => ({
//   ...msg,
//   debug_trace: msg.debug_trace ?? getTrace(msg.id),
// }));
// setMessages(hydratedMessages);

// --- При смене чата (когда activeChatId меняется) ---
// В useEffect при смене chatId ДОБАВИТЬ:
// clearCache() — НЕ нужно (кэш per-chat, храним все чаты)
// Просто убедиться, что при загрузке нового чата вызывается hydration выше.
```


### 1.3 Тип `Message` — убедиться, что `id` всегда есть

```typescript
// web_ui/src/types/chat.types.ts — ПРОВЕРИТЬ, что Message имеет поле id

export interface Message {
  id: string;           // ← ОБЯЗАТЕЛЬНО: уникальный ID сообщения из БД
  role: 'user' | 'assistant';
  content: string;
  debug_trace?: InlineTrace | null;
  // ... другие поля
}
```

Если бэкенд не возвращает `message_id` в ответе на отправку — добавить его:

```python
# В API response для /api/chat/send (или аналоге)
return {
    "answer": answer,
    "message_id": str(saved_message.id),  # ← ДОБАВИТЬ
    "debug_trace": trace.dict() if debug_mode else None,
}
```


***

## 2. FIX 2 — Панель сворачивается в шапку (Progressive Disclosure)

### Корень проблемы

В `InlineDebugTrace.tsx` строка:

```tsx
<div className="mt-2 rounded-xl border ...">
  <StatusBar trace={trace} />
  <div className="px-4 pb-4 pt-2 space-y-4">
    <details open id="debug-routing">   {/* ← open всегда */}
    <details open id="debug-chunks">    {/* ← open всегда */}
```

Внешний `<div>` не имеет toggle-механизма. Все внутренние секции L1 открыты по умолчанию.

### Фикс: обернуть в `<details>` с L0 = StatusBar как summary

```tsx
// ЗАМЕНИТЬ в InlineDebugTrace.tsx
// БЫЛО:
return (
  <div className="mt-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-xs">
    <StatusBar trace={trace} />
    <div className="px-4 pb-4 pt-2 space-y-4">
      ...
    </div>
  </div>
);

// СТАЛО:
const [panelOpen, setPanelOpen] = useState(false);

return (
  <div className="mt-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-xs">
    {/* L0: StatusBar — всегда видим, является кнопкой раскрытия панели */}
    <div
      className="cursor-pointer select-none"
      onClick={() => setPanelOpen(prev => !prev)}
      title={panelOpen ? 'Свернуть панель отладки' : 'Развернуть панель отладки'}
    >
      <StatusBar trace={trace} isExpanded={panelOpen} />
    </div>

    {/* L1–L3: тело панели — скрыто по умолчанию */}
    {panelOpen && (
      <div className="px-4 pb-4 pt-2 space-y-4">
        {/* ... всё содержимое ... */}
      </div>
    )}
  </div>
);
```


### Обновление `StatusBar.tsx` — индикатор раскрытия

```tsx
// В StatusBar.tsx — ДОБАВИТЬ проп isExpanded и chevron-индикатор

interface StatusBarProps {
  trace: InlineTrace;
  isExpanded?: boolean;  // ← ДОБАВИТЬ
}

export const StatusBar: React.FC<StatusBarProps> = ({ trace, isExpanded = false }) => {
  // ... существующий код chips ...

  return (
    <div className="flex flex-wrap gap-1.5 px-3 py-2 bg-slate-50 dark:bg-slate-900
                    border-b border-slate-200 dark:border-slate-700 rounded-t-lg
                    hover:bg-slate-100 dark:hover:bg-slate-800/70 transition-colors">
      {chips.map((chip, i) => (
        // ... существующий рендер чипов (убрать href, т.к. теперь onClick на родителе) ...
        <span key={i} className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ${chipColors[chip.color]}`}>
          {chip.label}
        </span>
      ))}
      {/* Chevron справа */}
      <span className="ml-auto text-slate-400 text-[10px] self-center">
        {isExpanded ? '▲ свернуть' : '▼ детали'}
      </span>
    </div>
  );
};
```


### Все внутренние `<details>` — убрать `open` (начинать свёрнутыми)

```tsx
// НАЙТИ И ИСПРАВИТЬ в InlineDebugTrace.tsx:

// БЫЛО:
<details open id="debug-routing">
<details open id="debug-chunks">
<details open>  // "Chunks in response"

// СТАЛО (убрать open):
<details id="debug-routing">
<details id="debug-chunks">
<details>  // "Chunks in response"
```


***

## 3. FIX 3 — ChunkRow: полное раскрытие по клику

### Корень проблемы

Текущий `ChunkRow` (`InlineDebugTrace.tsx`):

```tsx
{chunk?.preview && (
  <p className="text-[11px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
    {chunk.preview}
  </p>
)}
```

Нет toggle — `preview` — это первые ~150 символов. Кнопки для раскрытия полного текста нет.

### Фикс: добавить `useState(false)` + кнопку "Развернуть / Свернуть"

```tsx
// ЗАМЕНИТЬ ChunkRow полностью:

const ChunkRow: React.FC<{ chunk: any; passed?: boolean }> = ({ chunk, passed }) => {
  const [expanded, setExpanded] = useState(false);  // ← НОВОЕ

  const sdLevel = (chunk?.sd_level || '').toUpperCase();
  const sdColor = SD_COLORS[sdLevel] || 'text-slate-500';
  const isPassed = passed ?? chunk?.passed_sd_filter ?? false;

  // Полный текст — из chunk.text или chunk.full_text, preview — из chunk.preview
  const fullText: string | undefined = chunk?.text ?? chunk?.full_text;
  const previewText: string | undefined = chunk?.preview;
  const hasMore = fullText && fullText.length > (previewText?.length ?? 0);

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs space-y-1">
      <div className="flex items-center gap-2">
        <span className={isPassed ? 'text-emerald-600' : 'text-rose-500'}>
          {isPassed ? 'OK' : 'NO'}
        </span>
        <code className="font-mono font-semibold text-slate-700 dark:text-slate-300">
          {chunk?.block_id}
        </code>
        <span className={`text-[10px] uppercase ${sdColor}`}>{sdLevel || '—'}</span>
        <span className="ml-auto text-slate-500 font-mono">
          {formatNumber(chunk?.score_initial ?? 0, 3)} {'>'} {formatNumber(chunk?.score_final ?? 0, 3)}
        </span>
      </div>

      {chunk?.filter_reason && !isPassed && (
        <div className="text-[10px] text-rose-500">{chunk.filter_reason}</div>
      )}

      {/* Текст чанка с expand/collapse */}
      {(previewText || fullText) && (
        <div>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
            {expanded && fullText ? fullText : (previewText ?? fullText)}
          </p>
          {hasMore && (
            <button
              onClick={() => setExpanded(prev => !prev)}
              className="mt-1 text-[10px] text-sky-500 hover:text-sky-700 dark:hover:text-sky-300 transition-colors"
            >
              {expanded ? '▲ Свернуть' : `▼ Развернуть (${fullText!.length} символов)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
```


***

## 4. FIX 4 — debug-cost: открыть по умолчанию

### Корень проблемы

```tsx
// БЫЛО:
<details id="debug-cost">

// СТАЛО:
<details id="debug-cost" open>
```

Одна строка. Секция "Модели, токены и стоимость" теперь видна сразу при раскрытии панели.

***

## 5. FIX 5 — Порядок секций: по потоку оркестрации

### Принцип: порядок = порядок исполнения пайплайна

```
Запрос → [State Classifier] → [SD Classifier] → [Fast path?]
       → [Retrieval → Funnel фильтров] → [LLM call] → [Memory write]
       → [Cost] → [Anomaly check]
```


### Новый порядок секций в `InlineDebugTrace.tsx`

```tsx
// ИТОГОВЫЙ ПОРЯДОК внутри {panelOpen && <div ...>}:

{/* 1. ERROR FIRST — если есть */}
{trace.pipeline_error && (
  <div id="debug-error">
    <ErrorView error={trace.pipeline_error} />
  </div>
)}

{/* 2. ROUTING & SD — что классифицировано, какой режим, SD уровень */}
<details id="debug-routing">
  <summary ...>🎯 Роутинг и классификация</summary>
  ...
</details>

{/* 3. PIPELINE TIMELINE — визуальный поток всех этапов */}
<details id="debug-timeline">
  <summary ...>⏱ Pipeline Timeline</summary>
  ...
</details>

{/* 4. CHUNKS — воронка retrieval после routing */}
<details id="debug-chunks">
  <summary ...>📦 Чанки и retrieval</summary>
  ...
</details>

{/* 5. LLM CALLS — что ушло в LLM, промпты */}
{llmCalls.length > 0 && (
  <details id="debug-llm">
    <summary ...>🤖 LLM Calls ({llmCalls.length})</summary>
    ...
  </details>
)}

{/* 6. MEMORY — что было в памяти + что записано */}
<details id="debug-memory">
  <summary ...>🧠 Контекст памяти</summary>
  ...
</details>

{/* 7. MODELS + TOKENS + COST — открыто по умолчанию */}
<details id="debug-cost" open>
  <summary ...>💰 Модели, токены и стоимость</summary>
  ...
</details>

{/* 8. ANOMALIES — итог: что пошло не так */}
<details id="debug-anomalies" open={openAnomalies} onToggle={...}>
  <summary ...>⚠️ Anomalies</summary>
  ...
</details>

{/* 9. SESSION DASHBOARD — L3 */}
{trace.session_id && (
  <div id="debug-session">
    <SessionDashboard sessionId={trace.session_id} />
  </div>
)}

{/* 10. TRACE HISTORY — L3 */}
{trace.session_id && (
  <div id="debug-history">
    <TraceHistory sessionId={trace.session_id} />
  </div>
)}

{/* 11. CONFIG SNAPSHOT — L3 */}
<div id="debug-config">
  <ConfigSnapshot trace={trace} />
</div>

{/* 12. EXPORT */}
<div className="flex justify-end px-3 pb-2">
  <button onClick={handleExport} ...>⬇ Export trace JSON</button>
</div>
```


### Обновить summary-заголовки с эмодзи-якорями для быстрой навигации

| id | Было | Стало |
| :-- | :-- | :-- |
| `debug-routing` | `Роутинг и SD` | `🎯 Роутинг и классификация` |
| `debug-timeline` | `Pipeline Timeline` | `⏱ Pipeline Timeline` |
| `debug-chunks` | `Чанки` | `📦 Чанки и retrieval` |
| `debug-llm` | `LLM Calls (N)` | `🤖 LLM Calls (N)` |
| `debug-memory` | `Контекст памяти` | `🧠 Контекст памяти` |
| `debug-cost` | `Модели, токены и стоимость` | `💰 Модели, токены и стоимость` |
| `debug-anomalies` | `Anomalies` | `⚠️ Anomalies` |


***

## 6. ИТОГОВЫЙ DIFF — только затронутые файлы

| Файл | Тип изменения |
| :-- | :-- |
| `web_ui/src/hooks/useTraceCache.ts` | **СОЗДАТЬ** (новый файл) |
| `web_ui/src/pages/ChatPage.tsx` | Добавить `useTraceCache`, hydration при загрузке истории, `setTrace` при получении ответа |
| `web_ui/src/components/chat/InlineDebugTrace.tsx` | Fix 2 (outer toggle), Fix 3 (ChunkRow), Fix 4 (debug-cost open), Fix 5 (порядок секций) |
| `web_ui/src/components/debug/StatusBar.tsx` | Добавить `isExpanded` проп + chevron |
| `api/routes/chat.py` (или аналог) | Добавить `message_id` в response body при отправке сообщения |

### НЕ ТРОГАТЬ

- `Message.tsx`, `MessageList.tsx`, `ChatWindow.tsx` — запрет из PRD v2.0.6
- `config.py`, `state_classifier.py`, `response_formatter.py`
- Существующие Pydantic-поля — только добавлять

***

## 7. DEFINITION OF DONE (v3.0.2)

- [ ] Панель при открытии чата свёрнута — видна только строка StatusBar с чипами и `▼ детали`
- [ ] Клик на StatusBar раскрывает/сворачивает всю панель
- [ ] При переходе между чатами и возврате — трейс всех предыдущих сообщений виден (из sessionStorage)
- [ ] Каждый чанк раскрывается кнопкой `▼ Развернуть (N символов)` при наличии полного текста
- [ ] Секция "Модели, токены и стоимость" **открыта по умолчанию** при раскрытии панели
- [ ] Порядок секций: Routing → Timeline → Chunks → LLM → Memory → Cost → Anomalies
- [ ] `npm run lint` — 0 ошибок
- [ ] `npm run build` — успешная сборка

***

## 8. ПРИОРИТИЗАЦИЯ ДЛЯ IDE АГЕНТА

| \# | Задача | Время | Ценность |
| :-- | :-- | :-- | :-- |
| 1 | Fix 4: `open` на `debug-cost` | 30 сек | Мгновенная победа |
| 2 | Fix 3: ChunkRow `useState` expand | 5 мин | Восстанавливает сломанный UX |
| 3 | Fix 2: outer panel toggle + убрать `open` с L1 | 10 мин | Ключевой UX |
| 4 | Fix 5: Переставить секции + эмодзи | 10 мин | Читаемость оркестрации |
| 5 | Fix 1: `useTraceCache` + hydration | 30 мин | Персистентность трейса |


***

