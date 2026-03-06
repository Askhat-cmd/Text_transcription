

***

# PRD v4.1 — Debug Trace Panel для dev-key-001

**Статус:** Ready for implementation
**Исполнитель:** Codex Agent
**Репозиторий:** `Text_transcription` / `bot_psychologist`

***

## 1. Цель

Расширить веб-интерфейс бота так, чтобы при использовании ключа `dev-key-001` рядом с чатом появлялась правая панель с полной цепочкой рассуждений бота — от первичной SD-классификации до того, что записалось в память. Одновременно исправить визуальные проблемы UI чата.

***

## 2. Контекст кодовой базы

Перед началом работы прочитай эти файлы:


| Файл | Что там |
| :-- | :-- |
| `bot_psychologist/api/auth.py` | Класс `APIKeyManager`, функция `verify_api_key`. Ключи `test-key-001` и `dev-key-001` уже прописаны |
| `bot_psychologist/api/models.py` | Pydantic-модели. Главная — `AdaptiveAnswerResponse` |
| `bot_psychologist/api/routes.py` | FastAPI эндпоинты. Целевой — `POST /questions/adaptive`, функция `ask_adaptive_question`. Параметр `debug=request.debug` уже передаётся в `answer_question_adaptive` |
| Фронтенд | Найди самостоятельно по `package.json` / `App.jsx` / `index.html` на `localhost:3000` |

**Важно:** API работает в режиме обычного request/response (не стриминг). Стриминг не нужен.

***

## 3. Требования — что НЕ делать

- Не трогать логику внутри `bot_agent/` — только слой API и фронтенд
- Не менять поля в `AnswerResponse` — только `AdaptiveAnswerResponse`
- Не создавать новые API endpoints — расширить только `/questions/adaptive`
- Не переписывать существующий код — только добавлять

***

## 4. Backend — три файла

### 4.1 `auth.py` — добавить определение dev-ключа

Добавь в класс `APIKeyManager` метод:

```python
def is_dev_key(self, key: str) -> bool:
    """Проверить является ли ключ dev-ключом с расширенными правами."""
    return key == "dev-key-001"
```

Добавь на уровень модуля (рядом с `verify_api_key`):

```python
def is_dev_key(api_key: str) -> bool:
    """Удобная функция для проверки dev-ключа в routes."""
    return api_key_manager.is_dev_key(api_key)
```


***

### 4.2 `models.py` — добавить модели трейса

Добавь в конец файла:

```python
from typing import Optional, List

# ── Debug Trace Models ────────────────────────────────────────

class ChunkTraceItem(BaseModel):
    """Один чанк из ChromaDB с полной информацией для отладки."""
    block_id: str
    title: str
    sd_level: str                  # уровень СД из metadata ChromaDB
    sd_secondary: str = ""
    emotional_tone: str = ""
    score_initial: float           # score до Voyage rerank
    score_final: float             # score после Voyage rerank
    passed_sd_filter: bool         # прошёл ли sd_filter
    filter_reason: str = ""        # причина отсева если passed=False
    preview: str                   # первые 120 символов текста блока


class SDClassificationTrace(BaseModel):
    """Результат классификации SD-уровня пользователя."""
    method: str                    # "heuristic" | "llm" | "profile" | "fallback"
    primary: str                   # основной уровень: GREEN, YELLOW и т.д.
    secondary: Optional[str]       # вторичный уровень или None
    confidence: float              # 0.0 — 1.0
    indicator: str                 # маркер: "keywords_matched_3", "llm_classified" и т.д.
    allowed_levels: List[str]      # уровни блоков разрешённые для показа


class LLMCallTrace(BaseModel):
    """Один вызов LLM в рамках обработки запроса."""
    step: str                      # "main_answer" | "refine" | "summary" | "sd_classify"
    model: str                     # "gpt-4o-mini" и т.д.
    system_prompt_preview: str     # первые 300 символов системного промта
    user_prompt_preview: str       # первые 300 символов пользовательского промта
    response_preview: str          # первые 300 символов ответа LLM
    tokens_used: Optional[int] = None
    duration_ms: Optional[int] = None


class DebugTrace(BaseModel):
    """Полная цепочка рассуждений бота для одного запроса."""
    sd_classification: SDClassificationTrace
    chunks_retrieved: List[ChunkTraceItem]       # все чанки до SD-фильтра
    chunks_after_sd_filter: List[ChunkTraceItem] # только прошедшие фильтр
    llm_calls: List[LLMCallTrace]                # все вызовы LLM по порядку
    context_written_to_memory: str               # что записалось в историю
    total_duration_ms: int
```

В класс `AdaptiveAnswerResponse` добавь поле:

```python
trace: Optional[DebugTrace] = None  # заполняется только при debug=True
```


***

### 4.3 `routes.py` — расширить `/questions/adaptive`

**Шаг A.** Добавь импорт в начало файла:

```python
from .auth import verify_api_key, is_dev_key
```

**Шаг B.** В функции `ask_adaptive_question`, сразу после строки `session_key = request.session_id or request.user_id` добавь:

```python
# Dev-ключ автоматически включает debug-режим
if is_dev_key(api_key):
    request.debug = True
```

**Шаг C.** После получения `result` от `answer_question_adaptive` добавь сборку трейса:

```python
trace = None
if request.debug and result.get("debug_trace"):
    raw = result["debug_trace"]
    try:
        trace = DebugTrace(
            sd_classification=SDClassificationTrace(
                **raw["sd_classification"]
            ),
            chunks_retrieved=[
                ChunkTraceItem(**c) for c in raw.get("chunks_retrieved", [])
            ],
            chunks_after_sd_filter=[
                ChunkTraceItem(**c) for c in raw.get("chunks_after_filter", [])
            ],
            llm_calls=[
                LLMCallTrace(**c) for c in raw.get("llm_calls", [])
            ],
            context_written_to_memory=raw.get("context_written", ""),
            total_duration_ms=raw.get("total_duration_ms", 0),
        )
    except Exception as trace_exc:
        logger.warning(f"[DEBUG_TRACE] Failed to build trace: {trace_exc}")
        trace = None
```

**Шаг D.** В `return AdaptiveAnswerResponse(...)` добавь поле:

```python
trace=trace,
```


***

## 5. Frontend — три задачи

### 5.1 Исправить UI сообщений пользователя

Найди CSS/стили компонента сообщений пользователя и:

```css
/* Было: фиолетовый пузырь справа */
/* Стало: */
.message-user {
  background: #F4F4F5;    /* светло-серый */
  color: #18181B;          /* тёмный текст */
  border-radius: 12px;
  margin-left: 32px;       /* отступ слева, не справа */
  margin-right: 0;
  align-self: flex-start;  /* в одном столбце с ботом */
}
```

Сообщения пользователя и бота должны быть в **одной колонке**, пользователь — серый блок с отступом слева.

***

### 5.2 Создать компонент `DebugTrace.jsx`

Создай файл рядом с другими компонентами чата.

**Цвета SD-уровней** (пастельные, для бейджей):

```js
const SD_COLORS = {
  BEIGE:     "#FEF9C3",
  PURPLE:    "#F3E8FF",
  RED:       "#FFE4E6",
  BLUE:      "#DBEAFE",
  ORANGE:    "#FFEDD5",
  GREEN:     "#DCFCE7",
  YELLOW:    "#FEF9C3",
  TURQUOISE: "#CCFBF1",
};
```

**Компонент ChunkBadge** — карточка одного чанка:

```jsx
function ChunkBadge({ chunk }) {
  const cardBg  = chunk.passed_sd_filter ? "#DCFCE7" : "#FFE4E6";
  const sdBg    = SD_COLORS[chunk.sd_level] || "#F4F4F5";

  return (
    <div style={{ background: cardBg, borderRadius: 8,
                  padding: "6px 10px", marginBottom: 6 }}>
      <div>
        <span style={{ background: sdBg, borderRadius: 4,
                       padding: "1px 6px", fontSize: 11, marginRight: 6 }}>
          {chunk.sd_level}
        </span>
        <b>{chunk.title}</b>
      </div>
      <div style={{ color: "#71717A", fontSize: 11, marginTop: 2 }}>
        score: {chunk.score_initial.toFixed(3)} → {chunk.score_final.toFixed(3)}
        {chunk.sd_secondary &&
          <span style={{ marginLeft: 8 }}>2°: {chunk.sd_secondary}</span>}
        {chunk.emotional_tone &&
          <span style={{ marginLeft: 8 }}>tone: {chunk.emotional_tone}</span>}
        {!chunk.passed_sd_filter &&
          <span style={{ color: "#EF4444", marginLeft: 8 }}>
            ✗ {chunk.filter_reason}
          </span>}
      </div>
      <div style={{ color: "#A1A1AA", fontSize: 11, marginTop: 2 }}>
        {chunk.preview}
      </div>
    </div>
  );
}
```

**Компонент Section** — сворачиваемая секция:

```jsx
function Section({ label, open, onToggle, children }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div
        onClick={onToggle}
        style={{ cursor: "pointer", padding: "6px 0", fontWeight: 600,
                 fontSize: 12, color: "#3F3F46",
                 borderBottom: "1px solid #E4E4E7", userSelect: "none" }}
      >
        {open ? "▾" : "▸"} {label}
      </div>
      {open && <div style={{ paddingTop: 8 }}>{children}</div>}
    </div>
  );
}
```

**Главный компонент DebugTrace:**

```jsx
import { useState } from "react";

export function DebugTrace({ trace }) {
  const [open, setOpen] = useState({
    sd: true, chunks: true, filtered: false, llm: false, memory: false
  });
  const toggle = (key) => setOpen(p => ({ ...p, [key]: !p[key] }));

  const sd = trace.sd_classification;

  return (
    <div style={{ width: 420, flexShrink: 0, borderLeft: "1px solid #E4E4E7",
                  overflowY: "auto", background: "#FAFAFA",
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
                  padding: 12 }}>

      {/* Заголовок панели */}
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12,
                    borderBottom: "1px solid #E4E4E7", paddingBottom: 8,
                    color: "#18181B" }}>
        🔍 Debug Trace
        <span style={{ color: "#71717A", fontWeight: 400, marginLeft: 8 }}>
          {trace.total_duration_ms}ms
        </span>
      </div>

      {/* A. SD-классификация */}
      <Section label="A · SD-классификация"
               open={open.sd} onToggle={() => toggle("sd")}>
        <div style={{ lineHeight: 1.8 }}>
          <div>
            <b>Уровень:</b>{" "}
            <span style={{ background: SD_COLORS[sd.primary] || "#F4F4F5",
                           borderRadius: 4, padding: "1px 8px" }}>
              {sd.primary}
            </span>
            {sd.secondary &&
              <span style={{ color: "#71717A" }}> / {sd.secondary}</span>}
          </div>
          <div><b>Метод:</b> {sd.method}</div>
          <div><b>Confidence:</b> {(sd.confidence * 100).toFixed(0)}%</div>
          <div><b>Маркер:</b> {sd.indicator}</div>
          <div><b>Разрешены:</b> {sd.allowed_levels.join(", ")}</div>
        </div>
      </Section>

      {/* B. Все чанки до фильтра */}
      <Section label={`B · Чанки из ChromaDB (${trace.chunks_retrieved.length})`}
               open={open.chunks} onToggle={() => toggle("chunks")}>
        {trace.chunks_retrieved.map(c =>
          <ChunkBadge key={c.block_id} chunk={c} />)}
      </Section>

      {/* C. После SD-фильтра */}
      <Section label={`C · После SD-фильтра (${trace.chunks_after_sd_filter.length})`}
               open={open.filtered} onToggle={() => toggle("filtered")}>
        {trace.chunks_after_sd_filter.map(c =>
          <ChunkBadge key={c.block_id} chunk={c} />)}
      </Section>

      {/* D. LLM вызовы */}
      <Section label={`D · LLM вызовы (${trace.llm_calls.length})`}
               open={open.llm} onToggle={() => toggle("llm")}>
        {trace.llm_calls.map((call, i) => (
          <div key={i} style={{ marginBottom: 10, padding: 8,
                                background: "#F4F4F5", borderRadius: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {call.step} · {call.model}
              {call.duration_ms &&
                <span style={{ color: "#71717A", fontWeight: 400 }}>
                  {" "}· {call.duration_ms}ms
                </span>}
              {call.tokens_used &&
                <span style={{ color: "#71717A", fontWeight: 400 }}>
                  {" "}· {call.tokens_used} tok
                </span>}
            </div>
            <details>
              <summary style={{ color: "#6366F1", cursor: "pointer" }}>
                System prompt
              </summary>
              <pre style={{ whiteSpace: "pre-wrap", color: "#3F3F46",
                            fontSize: 11, marginTop: 4 }}>
                {call.system_prompt_preview}
              </pre>
            </details>
            <details>
              <summary style={{ color: "#6366F1", cursor: "pointer" }}>
                User prompt
              </summary>
              <pre style={{ whiteSpace: "pre-wrap", color: "#3F3F46",
                            fontSize: 11, marginTop: 4 }}>
                {call.user_prompt_preview}
              </pre>
            </details>
            <details>
              <summary style={{ color: "#059669", cursor: "pointer" }}>
                Ответ LLM
              </summary>
              <pre style={{ whiteSpace: "pre-wrap", color: "#3F3F46",
                            fontSize: 11, marginTop: 4 }}>
                {call.response_preview}
              </pre>
            </details>
          </div>
        ))}
      </Section>

      {/* E. Память */}
      <Section label="E · Записано в память"
               open={open.memory} onToggle={() => toggle("memory")}>
        <pre style={{ whiteSpace: "pre-wrap", color: "#3F3F46", fontSize: 11 }}>
          {trace.context_written_to_memory || "—"}
        </pre>
      </Section>
    </div>
  );
}
```


***

### 5.3 Подключить Debug Panel в layout чата

В главном компоненте чата (`App.jsx` или аналог):

```jsx
import { DebugTrace } from "./DebugTrace";

// Определить тип ключа (читай из конфига/env/localStorage)
const IS_DEV = apiKey === "dev-key-001";

// Стейт для трейса
const [traceData, setTraceData] = useState(null);

// После каждого ответа от /questions/adaptive:
const handleResponse = (response) => {
  // ... обычная обработка ответа ...
  if (IS_DEV) {
    setTraceData(response.trace || null);
  }
};

// Layout:
return (
  <div style={{ display: "flex", height: "100vh" }}>
    <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
      {/* Сайдбар сессий + основной чат — как сейчас */}
    </div>

    {IS_DEV && traceData && (
      <DebugTrace trace={traceData} />
    )}
  </div>
);
```


***

## 6. Логика активации

```
Запрос с X-API-Key: dev-key-001
  → is_dev_key() = true
  → request.debug = True (автоматически)
  → answer_question_adaptive(..., debug=True)
  → result содержит "debug_trace"
  → response.trace = DebugTrace(...)
  → фронтенд показывает панель справа

Запрос с X-API-Key: test-key-001
  → is_dev_key() = false
  → debug остаётся как в запросе (обычно False)
  → response.trace = None
  → панель не показывается
```


***

## 7. Проверка результата

После реализации проверь:

- [ ] `POST /questions/adaptive` с `dev-key-001` → в JSON-ответе есть поле `trace` с вложенными объектами
- [ ] `POST /questions/adaptive` с `test-key-001` → поле `trace` отсутствует или `null`
- [ ] В браузере с `dev-key-001`: правая панель 420px появляется после первого ответа
- [ ] Секции A–E сворачиваются/разворачиваются кликом
- [ ] Чанки: зелёный фон = прошли фильтр, красный = отсеяны, на каждом бейдж с SD-уровнем
- [ ] Сообщения пользователя — серые `#F4F4F5`, в одной колонке с ботом, без фиолетового

