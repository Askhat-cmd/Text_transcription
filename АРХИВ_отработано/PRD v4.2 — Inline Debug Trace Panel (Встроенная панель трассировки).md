

***

# PRD v4.2 — Inline Debug Trace Panel (Встроенная панель трассировки)


***

## 1. Контекст и цель

Существующая реализация `DebugTrace` отображает трассировку последнего ответа в **отдельной правой колонке**. При каждом новом запросе данные перезаписываются — история трассировок теряется. Это не позволяет сравнивать, как менялась оркестрация и retrieval по ходу диалога.

**Цель:** перенести трассировку **прямо под каждый ответ бота** в основном чате. Каждый ответ хранит свою трассировку навсегда — вся история видна вертикально. Правая колонка `DebugTrace` удаляется.

***

## 2. Принципы UX (главное правило: удобно и наглядно)

- **Сворачивается по умолчанию** — не мешает читать ответ бота
- **Разворачивается одним кликом** — без лишних действий
- **Каждая секция независимо сворачивается** — можно открыть только то, что нужно
- **Чанки показываются ПОЛНОСТЬЮ** — весь текст, без обрезки
- **Источник каждого чанка** — `block_id`, файл/тема, позиция
- **Цветовая маркировка** — зелёный ✅ прошёл, красный ❌ отсеян, с причиной фильтра
- **Не требует перезагрузки** — trace хранится в объекте сообщения в памяти React

***

## 3. Изменения в типах (`types/index.ts`)

Добавить поле `trace` в интерфейс `Message`:

```ts
// Добавить интерфейс для одного чанка
export interface TraceBlock {
  block_id: string;
  score: number;
  text: string;          // ПОЛНЫЙ текст чанка
  source: string;        // источник: имя файла / тема / раздел
  stage: string;         // на каком этапе: 'initial' | 'stage_filter' | 'confidence_cap' | 'final'
  passed: boolean;       // прошёл или отсеян
  filter_reason?: string; // причина отсева (если passed = false)
}

// Добавить интерфейс трассировки
export interface InlineTrace {
  recommended_mode: string;       // PRESENCE | CLARIFICATION | VALIDATION | THINKING | INTERVENTION | INTEGRATION
  decision_rule_id: string;       // rule_001, rule_002 ...
  confidence_level: string;       // LOW | MEDIUM | HIGH
  confidence_score: number;       // 0.00 — 1.00
  user_state: string;             // текущее состояние пользователя
  sd_level?: string;              // SD уровень (purple/red/blue/orange/green/yellow)
  query_hash?: string;            // хэш запроса для дедупликации
  blocks: TraceBlock[];           // ВСЕ чанки всех этапов
  signals?: Record<string, number>; // вклад сигналов в confidence
  prompt_overlay?: string;        // какой SD-промт был применён
  summary_used?: boolean;         // использовалось ли summary диалога
  semantic_hits?: number;         // сколько семантических совпадений нашлось
}

// Расширить существующий Message
export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  state?: string;
  concepts?: string[];
  trace?: InlineTrace | null;     // НОВОЕ ПОЛЕ
}
```


***

## 4. Изменения в `useChat.ts`

При получении adaptive-ответа — строить объект `InlineTrace` и прикреплять к сообщению бота **в момент создания**:

```ts
// внутри функции sendQuestion, когда пришёл ответ
const rawTrace = response.trace; // то, что уже приходит с бэкенда

const inlineTrace: InlineTrace | null = (isDevKey && rawTrace) ? {
  recommended_mode: rawTrace.recommended_mode,
  decision_rule_id: rawTrace.decision_rule_id,
  confidence_level: rawTrace.confidence_level,
  confidence_score: rawTrace.confidence_score,
  user_state: rawTrace.user_state || '',
  sd_level: rawTrace.sd_level,
  query_hash: rawTrace.query_hash,
  signals: rawTrace.signals,
  prompt_overlay: rawTrace.prompt_overlay,
  summary_used: rawTrace.summary_used,
  semantic_hits: rawTrace.semantic_hits,
  blocks: [
    // Все прошедшие блоки — финальный список
    ...(rawTrace.retrieval_details?.final_blocks || []).map(b => ({
      block_id: b.block_id,
      score: b.score,
      text: b.text,
      source: b.source || b.block_id,
      stage: 'final',
      passed: true,
    })),
    // Отсеянные stage_filter
    ...(rawTrace.retrieval_details?.stage_filtered || []).map(b => ({
      block_id: b.block_id,
      score: b.score,
      text: b.text,
      source: b.source || b.block_id,
      stage: 'stage_filter',
      passed: false,
      filter_reason: 'stage filter',
    })),
    // Отсеянные confidence_cap
    ...(rawTrace.retrieval_details?.confidence_capped || []).map(b => ({
      block_id: b.block_id,
      score: b.score,
      text: b.text,
      source: b.source || b.block_id,
      stage: 'confidence_cap',
      passed: false,
      filter_reason: 'confidence cap',
    })),
  ],
} : null;

const botMessage: Message = {
  id: `bot-${Date.now()}`,
  role: 'bot',
  content: response.answer,
  timestamp: new Date(),
  state: response.user_state,
  concepts: response.concepts,
  trace: inlineTrace,   // ПРИКРЕПЛЯЕМ СЮДА
};
```

**Важно:** `traceData` из `useState` в `ChatPage.tsx` больше не нужен — удалить его и удалить `onAdaptiveResponse` колбэк из `useChat`.

***

## 5. Новый компонент `InlineDebugTrace.tsx`

Создать файл `web_ui/src/components/chat/InlineDebugTrace.tsx`:

### 5.1 Структура компонента

```
Компонент состоит из **главного `<details>`** и **4 внутренних секций**, каждая — отдельный `<details>`:
```

```
▶ 🔍 Debug — VALIDATION · rule_004 · conf: 0.87 · GREEN
  │
  ├── ▶ 📊 Роутинг и оркестрация
  │     MODE / RULE / CONFIDENCE / STATE / SD / SIGNALS
  │
  ├── ▶ ✅ Чанки в ответ (3)
  │     [block_041] score: 0.91 | source: тема_1.json
  │     ───────────────────────────────
  │     Полный текст чанка здесь...
  │     (весь, без обрезки)
  │
  ├── ▶ ❌ Отсеянные чанки (4)
  │     [block_089] score: 0.61 | причина: stage filter
  │     ───────────────────────────────
  │     Полный текст чанка здесь...
  │
  └── ▶ 🧠 Контекст памяти
        summary_used: да | semantic_hits: 3 | prompt: sd_green
```


### 5.2 Полный код компонента

```tsx
import React from 'react';
import type { InlineTrace, TraceBlock } from '../../types';

interface Props {
  trace: InlineTrace;
}

// Цвета по SD уровням
const SD_COLORS: Record<string, string> = {
  purple: 'text-purple-600 dark:text-purple-400',
  red:    'text-red-600 dark:text-red-400',
  blue:   'text-blue-600 dark:text-blue-400',
  orange: 'text-orange-500 dark:text-orange-400',
  green:  'text-emerald-600 dark:text-emerald-400',
  yellow: 'text-yellow-500 dark:text-yellow-300',
};

// Цвета по режиму ответа
const MODE_COLORS: Record<string, string> = {
  PRESENCE:      'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  CLARIFICATION: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  VALIDATION:    'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  THINKING:      'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
  INTERVENTION:  'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
  INTEGRATION:   'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
};

// Один чанк (полный текст + метаданные)
const ChunkCard: React.FC<{ block: TraceBlock; passed: boolean }> = ({ block, passed }) => (
  <details className="mb-2 rounded-lg border border-slate-200 dark:border-slate-700">
    <summary className="cursor-pointer px-3 py-2 flex items-center gap-2 text-xs select-none hover:bg-slate-50 dark:hover:bg-slate-800/50">
      <span>{passed ? '✅' : '❌'}</span>
      <code className="font-mono font-semibold text-slate-700 dark:text-slate-300">{block.block_id}</code>
      <span className={`ml-auto font-semibold ${passed ? 'text-emerald-600' : 'text-rose-500'}`}>
        {block.score.toFixed(3)}
      </span>
      <span className="text-slate-400 truncate max-w-[160px]">{block.source}</span>
      {!passed && block.filter_reason && (
        <span className="text-rose-400 text-[10px] border border-rose-200 rounded px-1">
          {block.filter_reason}
        </span>
      )}
    </summary>
    <div className="px-3 py-2 border-t border-slate-200 dark:border-slate-700">
      {/* Источник */}
      <p className="text-[10px] text-slate-400 mb-2 font-mono">
        📄 {block.source} · stage: {block.stage}
      </p>
      {/* ПОЛНЫЙ текст чанка */}
      <p className="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
        {block.text}
      </p>
    </div>
  </details>
);

export const InlineDebugTrace: React.FC<Props> = ({ trace }) => {
  const passedBlocks = trace.blocks.filter(b => b.passed);
  const filteredBlocks = trace.blocks.filter(b => !b.passed);
  const sdColor = trace.sd_level ? (SD_COLORS[trace.sd_level] || '') : '';
  const modeColor = MODE_COLORS[trace.recommended_mode] || 'bg-slate-100 text-slate-700';
  const confColor = trace.confidence_score >= 0.75
    ? 'text-emerald-600' : trace.confidence_score >= 0.5
    ? 'text-amber-500' : 'text-rose-500';

  return (
    <details className="mt-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-xs">
      {/* Главный заголовок — всё самое важное в одну строку */}
      <summary className="cursor-pointer px-4 py-2 flex items-center gap-2 select-none hover:bg-slate-100 dark:hover:bg-slate-800/50 rounded-xl">
        <span>🔍</span>
        <span className={`px-2 py-0.5 rounded-full font-semibold text-[11px] ${modeColor}`}>
          {trace.recommended_mode}
        </span>
        <span className="text-slate-400">{trace.decision_rule_id}</span>
        <span className={`font-bold ${confColor}`}>conf: {trace.confidence_score.toFixed(2)}</span>
        {trace.sd_level && (
          <span className={`font-semibold uppercase text-[10px] ${sdColor}`}>
            SD: {trace.sd_level}
          </span>
        )}
        <span className="ml-auto text-slate-400">
          ✅{passedBlocks.length} ❌{filteredBlocks.length}
        </span>
      </summary>

      <div className="px-4 pb-4 pt-2 space-y-3 border-t border-slate-200 dark:border-slate-700">

        {/* ─── СЕКЦИЯ 1: Роутинг ─── */}
        <details open>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            📊 Роутинг и оркестрация
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Режим</p>
              <p className={`font-bold px-1 rounded ${modeColor}`}>{trace.recommended_mode}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Правило</p>
              <p className="font-mono font-semibold text-slate-700 dark:text-slate-300">{trace.decision_rule_id}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Confidence</p>
              <p className={`font-bold ${confColor}`}>{trace.confidence_score.toFixed(3)} ({trace.confidence_level})</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Состояние</p>
              <p className="font-semibold text-slate-700 dark:text-slate-300">{trace.user_state || '—'}</p>
            </div>
            {trace.sd_level && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">SD уровень</p>
                <p className={`font-bold uppercase ${sdColor}`}>{trace.sd_level}</p>
              </div>
            )}
            {trace.query_hash && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Query hash</p>
                <p className="font-mono text-[10px] text-slate-500 truncate">{trace.query_hash}</p>
              </div>
            )}
          </div>

          {/* Сигналы confidence */}
          {trace.signals && Object.keys(trace.signals).length > 0 && (
            <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Вклад сигналов</p>
              {Object.entries(trace.signals).map(([signal, value]) => (
                <div key={signal} className="flex items-center gap-2 mb-1">
                  <span className="text-slate-500 w-40 truncate">{signal}</span>
                  <div className="flex-1 h-1.5 rounded bg-slate-200 dark:bg-slate-700">
                    <div
                      className="h-1.5 rounded bg-emerald-500"
                      style={{ width: `${Math.min(value * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-slate-600 dark:text-slate-400 w-10 text-right">
                    {value.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </details>

        {/* ─── СЕКЦИЯ 2: Принятые чанки ─── */}
        <details open>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            ✅ Чанки в ответ ({passedBlocks.length})
          </summary>
          <div className="mt-2">
            {passedBlocks.length === 0
              ? <p className="text-slate-400 px-2">Нет принятых чанков</p>
              : passedBlocks.map(b => <ChunkCard key={b.block_id} block={b} passed={true} />)
            }
          </div>
        </details>

        {/* ─── СЕКЦИЯ 3: Отсеянные чанки ─── */}
        {filteredBlocks.length > 0 && (
          <details>
            <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
              ❌ Отсеянные чанки ({filteredBlocks.length})
            </summary>
            <div className="mt-2">
              {filteredBlocks.map(b => <ChunkCard key={b.block_id} block={b} passed={false} />)}
            </div>
          </details>
        )}

        {/* ─── СЕКЦИЯ 4: Контекст памяти ─── */}
        <details>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            🧠 Контекст памяти
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Summary</p>
              <p className="font-semibold">{trace.summary_used ? '✅ использован' : '—'}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Semantic hits</p>
              <p className="font-semibold">{trace.semantic_hits ?? '—'}</p>
            </div>
            {trace.prompt_overlay && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2 col-span-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">SD Промт оверлей</p>
                <p className="font-mono text-slate-700 dark:text-slate-300">{trace.prompt_overlay}</p>
              </div>
            )}
          </div>
        </details>

      </div>
    </details>
  );
};
```


***

## 6. Изменения в `ChatWindow` / `MessageBubble`

Найти место, где рендерится сообщение бота, и добавить:

```tsx
import { InlineDebugTrace } from './InlineDebugTrace';

// внутри рендера сообщения с role === 'bot':
{message.role === 'bot' && (
  <div>
    {/* существующий текст ответа */}
    <MessageContent content={message.content} />

    {/* Inline trace — только если есть и isDevKey */}
    {message.trace && (
      <InlineDebugTrace trace={message.trace} />
    )}
  </div>
)}
```

`isDevKey` не нужен здесь — поле `trace` будет `null` у обычных пользователей, т.к. оно не записывается в `useChat`.

***

## 7. Удалить старое

| Что удалить | Где |
| :-- | :-- |
| `import { DebugTrace }` | `ChatPage.tsx` |
| `{isDevKey && traceData && <DebugTrace .../>}` | `ChatPage.tsx` |
| `useState<DebugTraceData \| null>(null)` для `traceData` | `ChatPage.tsx` |
| `onAdaptiveResponse` колбэк (перенести логику в `useChat`) | `ChatPage.tsx` |
| `DebugTrace.tsx` | `components/chat/` |


***

## 8. Изменения на бэкенде (`api/routes.py`)

Убедиться, что в ответе adaptive-эндпоинта приходят поля для полного текста чанков:

```python
# В metadata.retrieval_details каждый блок должен содержать:
{
  "block_id": "block_041",
  "score": 0.91,
  "text": "...полный текст чанка...",   # ОБЯЗАТЕЛЬНО
  "source": "имя_файла_или_тема",         # ОБЯЗАТЕЛЬНО
  "stage": "final"                        # final | stage_filter | confidence_cap
}
```

Если поля `text` нет — добавить его в `answer_adaptive.py` при формировании `retrieval_details`.

***

## 9. Чеклист для агента

- [ ] Добавить `InlineTrace`, `TraceBlock` в `types/index.ts`
- [ ] Добавить поле `trace?: InlineTrace | null` в `Message`
- [ ] В `useChat.ts` — строить `InlineTrace` из `response.trace` и прикреплять к `botMessage`
- [ ] Создать `InlineDebugTrace.tsx` в `components/chat/`
- [ ] Подключить `InlineDebugTrace` в рендер сообщения бота
- [ ] Удалить старый `DebugTrace.tsx` и всё связанное в `ChatPage.tsx`
- [ ] Проверить бэкенд: поля `text` и `source` есть в каждом блоке `retrieval_details`
- [ ] Проверить: при `isDevKey = false` поле `trace` не заполняется (остаётся `null`)
- [ ] Проверить: история трассировок не теряется при новых сообщениях
- [ ] Проверить: каждая секция раскрывается независимо
- [ ] Тест: 5 сообщений подряд — у каждого своя трассировка, все читаемы
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: image.jpg

