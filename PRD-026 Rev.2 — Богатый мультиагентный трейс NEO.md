# PRD-026 Rev.2 — Богатый мультиагентный трейс NEO

**Версия:** 2.0 (полная переработка после code review + UI анализа)
**Статус:** Ready for implementation
**Репозиторий:** https://github.com/Askhat-cmd/Text_transcription
**Рабочая директория:** `bot_psychologist/`
**Заменяет:** PRD-026 v1.0
**Дата:** 2026-04-26

---

## 1. Философия и цель

### 1.1 Главный принцип

Трейс — это "рентген" каждого ответа NEO. Разработчик смотрит на трейс и **точно понимает**:
- В каком состоянии был пользователь
- Какую нить диалога выбрал Thread Manager и почему
- Что именно Memory Agent достал из памяти и базы знаний
- Буквально весь текст который улетел в OpenAI API (Writer)
- Почему ответ именно такой — и как изменить поведение через системный промпт

### 1.2 Проблема v1.0

PRD-026 v1.0 реализован, но виджет слишком скудный: нет чанков, нет полотна LLM, нет истории ходов, нет токенов с разбивкой, нет стоимости, нет аномалий, нет Session Dashboard. Это PRD-026 Rev.2 — полная версия.

### 1.3 Принципы реализации

- **Additive** — дополняем существующий `MultiAgentTraceWidget.tsx`, не переписываем с нуля
- **Всё свёрнуто по умолчанию** — каждый блок открывается треугольником, чат не перегружен
- **Feature flag** — `MULTIAGENT_ENABLED` управляет видимостью
- **Только dev-ключ** — обычный пользователь трейс не видит

---

## 2. Структура трейса (полная, все блоки)

```
┌─────────────────────────────────────────────────────────────────┐
│ [ЗАГОЛОВОК] Pipeline NEO | multiagent_v1 | 1240ms | 🟢 OK       │  ← всегда виден
├─────────────────────────────────────────────────────────────────┤
│ ▶ Мультиагентный пайплайн                                       │  ← БЛОК 1
│   ▶ State Analyzer  310ms                                       │
│   ▶ Thread Manager  45ms                                        │
│   ▶ Memory Agent    280ms                                       │
│   ▶ Writer          580ms                                       │
│   ▶ Validator       25ms                                        │
│   [█████State█][█Thread█][████Memory████][██████Writer████][V█] │  ← timeline
├─────────────────────────────────────────────────────────────────┤
│ ▶ Контекст памяти                                               │  ← БЛОК 2
│   TURNS: 4  |  SEMANTIC HITS: 3  |  KNOWLEDGE: ✅              │
│   ▶ История ходов (4 turns)                                     │
│   ▶ Чанки в Writer (3)  — заголовки со score                    │
│   ▶ Все извлечённые чанки (9)                                   │
│   ▶ RAG query                                                   │
│   ▶ User Profile (паттерны, ценности)                           │
│   ▶ Memory snapshot (записано в память)                         │
├─────────────────────────────────────────────────────────────────┤
│ ▶ Полотно LLM (Writer)                                          │  ← БЛОК 3
│   session: xxx  |  turn: 5  |  mode: empathic                   │
│   ▶ System prompt                                               │
│   ▶ User prompt (полный контекст)                               │
│     ▶ — Conversation context                                    │
│     ▶ — Semantic hits в промпте                                 │
│     ▶ — User message                                            │
│   ▶ LLM response (что вернула модель)                           │
│   [Скопировать всё]                                             │
├─────────────────────────────────────────────────────────────────┤
│ ▶ Модели, токены и стоимость                                    │  ← БЛОК 4
│   MODEL: gpt-5-mini  |  TEMP: 0.7  |  MAX_TOKENS: 600          │
│   prompt: 412  completion: 87  total: 499  |  $0.000149         │
│   session total: 2045 tokens  |  $0.000612                      │
├─────────────────────────────────────────────────────────────────┤
│ ▶ Turn Diff                                                     │  ← БЛОК 5
│   nervous_state: calm → confused  |  phase: exploring → deepening│
│   relation: continue  |  thread: same                           │
│   memory delta: +1 turn  |  semantic: 0 → 3                     │
├─────────────────────────────────────────────────────────────────┤
│ ▶ Аномалии  [WARN: 1]                                           │  ← БЛОК 6
│   SLOW_WRITER  WARN: Writer занял 580ms (47% общего времени)    │
├─────────────────────────────────────────────────────────────────┤
│ ▶ Session Dashboard                                             │  ← БЛОК 7
│   TURNS: 5  |  AVG LATENCY: 1100ms  |  TOTAL COST: $0.0057     │
│   STATE TRAJECTORY: calm → curious → confused                   │
│   THREAD SWITCHES: 0  |  SAFETY EVENTS: 0  |  BLOCKS: 0        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Задачи бэкенда

### TASK-B1: Расширить debug в orchestrator.py

**Файл:** `bot_psychologist/bot_agent/multiagent/orchestrator.py`

Добавить в возвращаемый `debug` dict следующие поля (сверх уже существующих таймингов из PRD-026 v1.0):

```python
# После получения memory_bundle:
raw_chunks = memory_bundle.semantic_hits  # список SemanticHit

# После writer._call_llm — нужно прокинуть промпты из writer наружу:
# Добавить в WriterAgent._call_llm: сохранять system_prompt и user_prompt в атрибуты
# и возвращать их через write() как tuple (answer, prompt_debug)

# В debug dict добавить:
"debug": {
    # ... уже существующие поля ...

    # Чанки
    "semantic_hits_detail": [
        {
            "chunk_id": h.chunk_id,
            "source": h.source,
            "score": float(h.score),
            "content_preview": h.content[:200],  # первые 200 символов
            "content_full": h.content,            # полный текст (для раскрытия)
        }
        for h in memory_bundle.semantic_hits
    ],

    # RAG query
    "rag_query": memory_bundle.rag_query if hasattr(memory_bundle, 'rag_query') else "",

    # Контекст памяти (turns)
    "conversation_context": memory_bundle.conversation_context,

    # User profile
    "user_profile": {
        "patterns": memory_bundle.user_profile.patterns if memory_bundle.user_profile else [],
        "values": memory_bundle.user_profile.values if memory_bundle.user_profile else [],
        "progress_notes": memory_bundle.user_profile.progress_notes if memory_bundle.user_profile else [],
    },

    # LLM промпты из Writer (см. TASK-B2)
    "writer_system_prompt": writer_debug.get("system_prompt", ""),
    "writer_user_prompt": writer_debug.get("user_prompt", ""),
    "writer_llm_response_raw": writer_debug.get("llm_response", ""),

    # Токены и стоимость
    "tokens_prompt": writer_debug.get("tokens_prompt"),
    "tokens_completion": writer_debug.get("tokens_completion"),
    "tokens_total": writer_debug.get("tokens_total"),
    "estimated_cost_usd": writer_debug.get("estimated_cost_usd"),
    "model_temperature": writer_debug.get("temperature"),
    "model_max_tokens": writer_debug.get("max_tokens"),

    # Memory writeback
    "memory_written": {
        "user_input": query[:200],
        "bot_response": final_answer[:200],
        "thread_id": updated_thread.thread_id,
        "phase": updated_thread.phase,
    },
}
```

**Acceptance Criteria:**
- [ ] `debug.semantic_hits_detail` — список объектов с `chunk_id`, `source`, `score`, `content_preview`, `content_full`
- [ ] `debug.conversation_context` — строка с историей ходов
- [ ] `debug.writer_system_prompt` и `debug.writer_user_prompt` — непустые строки
- [ ] `debug.tokens_prompt` + `debug.tokens_completion` + `debug.tokens_total` — целые числа
- [ ] `debug.estimated_cost_usd` — float

---

### TASK-B2: Прокинуть промпты и токены из WriterAgent

**Файл:** `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`

Изменить метод `write()` чтобы он возвращал не только строку ответа, но и debug-данные.

**Вариант реализации — через атрибут экземпляра (не ломает интерфейс):**

```python
class WriterAgent:
    def __init__(self, ...):
        ...
        self.last_debug: dict = {}  # ← добавить

    async def write(self, contract: WriterContract) -> str:
        self.last_debug = {}  # сбросить
        try:
            result = await self._call_llm(contract)
            return result if result.strip() else self._static_fallback(contract)
        except Exception as exc:
            logger.error("[WRITER] write failed: %s", exc, exc_info=True)
            return self._static_fallback(contract)

    async def _call_llm(self, contract: WriterContract) -> str:
        client = self._get_client()
        ...
        ctx = contract.to_prompt_context()
        user_prompt = WRITER_USER_TEMPLATE.format(...)

        # ← сохранять промпты перед вызовом
        self.last_debug["system_prompt"] = WRITER_SYSTEM
        self.last_debug["user_prompt"] = user_prompt
        self.last_debug["model"] = self._model
        self.last_debug["temperature"] = self._temperature
        self.last_debug["max_tokens"] = self._max_tokens

        response = await client.chat.completions.create(
            model=self._model,
            messages=[...],
            ...
        )

        # ← сохранять результат и токены
        raw_text = (response.choices[0].message.content or "").strip()
        usage = response.usage
        if usage:
            self.last_debug["tokens_prompt"] = usage.prompt_tokens
            self.last_debug["tokens_completion"] = usage.completion_tokens
            self.last_debug["tokens_total"] = usage.total_tokens
            # Стоимость: gpt-4o-mini примерный тариф
            cost_per_1k_prompt = 0.00015
            cost_per_1k_completion = 0.0006
            self.last_debug["estimated_cost_usd"] = round(
                (usage.prompt_tokens / 1000) * cost_per_1k_prompt +
                (usage.completion_tokens / 1000) * cost_per_1k_completion,
                6
            )
        self.last_debug["llm_response"] = raw_text

        return raw_text
```

В `orchestrator.run()` после `draft_answer = await writer_agent.write(...)` добавить:
```python
writer_debug = writer_agent.last_debug
```

**Acceptance Criteria:**
- [ ] `writer_agent.last_debug` заполняется после каждого вызова `write()`
- [ ] Содержит `system_prompt`, `user_prompt`, `llm_response`, `tokens_*`, `estimated_cost_usd`
- [ ] При ошибке LLM — `last_debug` может быть пустым, orchestrator это обрабатывает через `.get(key, default)`

---

### TASK-B3: Добавить rag_query в MemoryBundle

**Файл:** `bot_psychologist/bot_agent/multiagent/contracts/memory_bundle.py`

Добавить поле `rag_query: str = ""` в dataclass/модель `MemoryBundle`.

**Файл:** `bot_psychologist/bot_agent/multiagent/agents/memory_retrieval.py`

В методе `assemble()` после `_build_rag_query()`:
```python
rag_query = self._build_rag_query(user_message, thread_state)
# ... существующая логика ...
return MemoryBundle(
    ...
    rag_query=rag_query,  # ← добавить
)
```

**Acceptance Criteria:**
- [ ] `memory_bundle.rag_query` — строка с запросом который улетел в ChromaDB

---

### TASK-B4: Накопление Session-метрик в session_store

**Файл:** `bot_psychologist/api/session_store.py`

Добавить метод накопления сессионной статистики:
```python
def accumulate_session_stats(self, session_id: str, debug: dict) -> None:
    """Накапливает метрики по сессии: токены, стоимость, state_trajectory, аномалии."""
    key = f"session_stats_{session_id}"
    stats = self._store.get(key, {
        "total_turns": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "total_latency_ms": 0,
        "state_trajectory": [],
        "thread_switches": 0,
        "safety_events": 0,
        "validator_blocks": 0,
        "anomalies_count": 0,
    })
    stats["total_turns"] += 1
    stats["total_tokens"] += int(debug.get("tokens_total") or 0)
    stats["total_cost_usd"] = round(stats["total_cost_usd"] + float(debug.get("estimated_cost_usd") or 0), 6)
    stats["total_latency_ms"] += int(debug.get("total_latency_ms") or 0)
    nervous = debug.get("nervous_state")
    if nervous:
        traj = stats["state_trajectory"]
        if not traj or traj[-1] != nervous:
            traj.append(nervous)
    if debug.get("relation_to_thread") == "new_thread":
        stats["thread_switches"] += 1
    if debug.get("safety_flag"):
        stats["safety_events"] += 1
    if debug.get("validator_blocked"):
        stats["validator_blocks"] += 1
    self._store[key] = stats

def get_session_stats(self, session_id: str) -> dict:
    return self._store.get(f"session_stats_{session_id}", {})
```

**Acceptance Criteria:**
- [ ] После 3 ходов `get_session_stats(id)["total_turns"] == 3`
- [ ] `state_trajectory` содержит дедуплицированную последовательность nervous_state
- [ ] `thread_switches` инкрементируется при `relation_to_thread == "new_thread"`

---

### TASK-B5: Расширить /multiagent-trace endpoint

**Файл:** `bot_psychologist/api/debug_routes.py`

Расширить ответ существующего эндпоинта, добавив в `MultiAgentTraceResponse` новые поля.

Обновить модели в `models.py` (дополнить, не ломать):

```python
class SemanticHitTrace(BaseModel):
    chunk_id: str
    source: str
    score: float
    content_preview: str
    content_full: str

class MemoryContextTrace(BaseModel):
    conversation_context: str = ""
    rag_query: str = ""
    semantic_hits: List[SemanticHitTrace] = []
    user_profile_patterns: List[str] = []
    user_profile_values: List[str] = []
    memory_written_preview: str = ""

class WriterLLMTrace(BaseModel):
    system_prompt: str = ""
    user_prompt: str = ""
    llm_response_raw: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 600
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    estimated_cost_usd: Optional[float] = None

class TurnDiffTrace(BaseModel):
    nervous_state_prev: Optional[str] = None
    nervous_state_curr: str = ""
    phase_prev: Optional[str] = None
    phase_curr: str = ""
    relation_to_thread: str = ""
    memory_turns_delta: int = 0
    semantic_hits_delta: int = 0

class AnomalyItem(BaseModel):
    code: str
    severity: str  # "WARN" | "ERROR"
    message: str

class SessionDashboard(BaseModel):
    total_turns: int = 0
    avg_latency_ms: int = 0
    total_cost_usd: float = 0.0
    state_trajectory: List[str] = []
    thread_switches: int = 0
    safety_events: int = 0
    validator_blocks: int = 0

# Обновить MultiAgentTraceResponse — добавить поля:
class MultiAgentTraceResponse(BaseModel):
    session_id: str
    turn_index: Optional[int]
    pipeline_version: str
    total_latency_ms: int
    agents: MultiAgentPipelineTrace       # уже существует
    memory_context: MemoryContextTrace    # ← новое
    writer_llm: WriterLLMTrace            # ← новое
    turn_diff: Optional[TurnDiffTrace]    # ← новое
    anomalies: List[AnomalyItem] = []     # ← новое
    session_dashboard: Optional[SessionDashboard] = None  # ← новое
```

В эндпоинте собирать новые секции из debug и session_stats:
```python
# Формирование anomalies — автодиагностика:
anomalies = []
timings = debug.get("timings", {})
total_ms = debug.get("total_latency_ms", 1)
writer_ms = timings.get("writer_ms", 0)
if writer_ms > 0 and writer_ms / total_ms > 0.6:
    anomalies.append(AnomalyItem(
        code="SLOW_WRITER",
        severity="WARN",
        message=f"Writer занял {writer_ms}ms ({round(writer_ms/total_ms*100)}% общего времени)"
    ))
if debug.get("safety_flag"):
    anomalies.append(AnomalyItem(
        code="SAFETY_FLAG",
        severity="WARN",
        message="State Analyzer обнаружил признак кризисного состояния"
    ))
if debug.get("validator_blocked"):
    anomalies.append(AnomalyItem(
        code="VALIDATOR_BLOCKED",
        severity="ERROR",
        message=f"Ответ заблокирован: {debug.get('validator_block_reason', 'неизвестная причина')}"
    ))

# Session dashboard из накопленной статистики:
stats = store.get_session_stats(session_id)
avg_latency = round(stats.get("total_latency_ms", 0) / max(stats.get("total_turns", 1), 1))
session_dashboard = SessionDashboard(
    total_turns=stats.get("total_turns", 0),
    avg_latency_ms=avg_latency,
    total_cost_usd=stats.get("total_cost_usd", 0.0),
    state_trajectory=stats.get("state_trajectory", []),
    thread_switches=stats.get("thread_switches", 0),
    safety_events=stats.get("safety_events", 0),
    validator_blocks=stats.get("validator_blocks", 0),
)
```

**Acceptance Criteria:**
- [ ] Endpoint возвращает `memory_context.semantic_hits` — список чанков с content_full
- [ ] `writer_llm.system_prompt` и `writer_llm.user_prompt` — непустые строки
- [ ] `anomalies` заполнен при SLOW_WRITER (writer > 60% total time)
- [ ] `session_dashboard.state_trajectory` — список уникальных состояний в порядке появления
- [ ] `turn_diff` показывает предыдущие значения (берётся из предыдущего сохранённого debug)

---

## 4. Задачи фронтенда

### TASK-F1: Обновить TypeScript-типы

**Файл:** `bot_psychologist/web_ui/src/types/index.ts`

Добавить новые интерфейсы (дополнить существующие, не удалять):

```typescript
export interface SemanticHitTrace {
  chunk_id: string;
  source: string;
  score: number;
  content_preview: string;
  content_full: string;
}

export interface MemoryContextTrace {
  conversation_context: string;
  rag_query: string;
  semantic_hits: SemanticHitTrace[];
  user_profile_patterns: string[];
  user_profile_values: string[];
  memory_written_preview: string;
}

export interface WriterLLMTrace {
  system_prompt: string;
  user_prompt: string;
  llm_response_raw: string;
  model: string;
  temperature: number;
  max_tokens: number;
  tokens_prompt?: number;
  tokens_completion?: number;
  tokens_total?: number;
  estimated_cost_usd?: number;
}

export interface TurnDiffTrace {
  nervous_state_prev?: string;
  nervous_state_curr: string;
  phase_prev?: string;
  phase_curr: string;
  relation_to_thread: string;
  memory_turns_delta: number;
  semantic_hits_delta: number;
}

export interface AnomalyItem {
  code: string;
  severity: 'WARN' | 'ERROR';
  message: string;
}

export interface SessionDashboard {
  total_turns: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  state_trajectory: string[];
  thread_switches: number;
  safety_events: number;
  validator_blocks: number;
}

// Обновить существующий MultiAgentTraceData — добавить поля:
export interface MultiAgentTraceData {
  session_id: string;
  turn_index?: number;
  pipeline_version: string;
  total_latency_ms: number;
  agents: MultiAgentPipelineTrace;          // уже есть
  memory_context?: MemoryContextTrace;      // ← новое
  writer_llm?: WriterLLMTrace;              // ← новое
  turn_diff?: TurnDiffTrace;                // ← новое
  anomalies?: AnomalyItem[];                // ← новое
  session_dashboard?: SessionDashboard;     // ← новое
}
```

---

### TASK-F2: Полная переработка MultiAgentTraceWidget.tsx

**Файл:** `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`

Переписать компонент полностью. Структура — 7 аккордеон-блоков:

#### Блок 1 — Мультиагентный пайплайн (уже существует, улучшить)

Добавить к каждой секции агента:
- State Analyzer: отображать `intent` полным текстом (не обрезать)
- Thread Manager: бейдж `NEW THREAD` при `relation_to_thread === 'new_thread'`
- Memory Agent: добавить `rag_query` строкой
- Writer: добавить `response_mode` + `model_used`
- Validator: `quality_flags` списком

#### Блок 2 — Контекст памяти (НОВЫЙ)

```tsx
<AccordionSection title={`Контекст памяти | turns: ${ctx.conversation_context_turns} | hits: ${ctx.semantic_hits.length}`}>

  {/* История ходов */}
  <AccordionSection title={`История ходов (${turnsCount})`} nested>
    <pre className="text-xs whitespace-pre-wrap">{trace.memory_context.conversation_context}</pre>
  </AccordionSection>

  {/* Чанки отправленные в Writer */}
  <AccordionSection title={`Чанки в Writer (${sentChunks.length})`} nested>
    {trace.memory_context.semantic_hits.map(hit => (
      <ChunkCard key={hit.chunk_id} hit={hit} />  // аккордеон: заголовок + score + content_full
    ))}
  </AccordionSection>

  {/* RAG query */}
  <AccordionSection title="RAG query" nested>
    <code className="text-xs">{trace.memory_context.rag_query || '—'}</code>
  </AccordionSection>

  {/* User Profile */}
  <AccordionSection title="User Profile" nested>
    <div>Паттерны: {patterns.join(', ') || '—'}</div>
    <div>Ценности: {values.join(', ') || '—'}</div>
  </AccordionSection>

  {/* Записано в память */}
  <AccordionSection title="Записано в память" nested>
    <code className="text-xs">{trace.memory_context.memory_written_preview}</code>
  </AccordionSection>

</AccordionSection>
```

Компонент `ChunkCard`:
```tsx
const ChunkCard = ({ hit }: { hit: SemanticHitTrace }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border rounded p-2 mb-1">
      <button onClick={() => setOpen(p => !p)} className="w-full text-left text-xs flex justify-between">
        <span>{hit.source}</span>
        <span className="text-slate-400">score: {hit.score.toFixed(3)} {open ? '▼' : '▶'}</span>
      </button>
      {open && <pre className="mt-1 text-xs whitespace-pre-wrap text-slate-600">{hit.content_full}</pre>}
    </div>
  );
};
```

#### Блок 3 — Полотно LLM (НОВЫЙ)

```tsx
<AccordionSection title={`Полотно LLM | ${llm.model} | tokens: ${llm.tokens_total ?? '—'}`}>

  {/* Мета-строка */}
  <div className="flex gap-4 text-xs mb-2">
    <span>session: {trace.session_id.slice(0,8)}...</span>
    <span>turn: {trace.turn_index}</span>
    <span>mode: {trace.agents.writer.response_mode}</span>
  </div>

  {/* System prompt */}
  <AccordionSection title="System prompt" nested>
    <pre className="text-xs whitespace-pre-wrap">{llm.system_prompt}</pre>
  </AccordionSection>

  {/* User prompt */}
  <AccordionSection title="User prompt (полный контекст)" nested>
    <pre className="text-xs whitespace-pre-wrap">{llm.user_prompt}</pre>
  </AccordionSection>

  {/* LLM response */}
  <AccordionSection title={`LLM response | ${llm.model} | ${writerMs}ms`} nested>
    <pre className="text-xs whitespace-pre-wrap">{llm.llm_response_raw}</pre>
  </AccordionSection>

  {/* Кнопка копировать */}
  <button onClick={copyAll} className="text-xs text-blue-600 hover:underline mt-2">
    Скопировать всё полотно
  </button>

</AccordionSection>
```

#### Блок 4 — Модели, токены и стоимость (НОВЫЙ)

```tsx
<AccordionSection title={`Токены и стоимость | ${llm.tokens_total ?? 0} токенов | $${cost}`}>
  <div className="grid grid-cols-2 gap-2 text-xs">
    <MetaItem label="MODEL" value={llm.model} highlight />
    <MetaItem label="TEMPERATURE" value={llm.temperature} />
    <MetaItem label="MAX TOKENS" value={llm.max_tokens} />
    <MetaItem label="TOKENS prompt" value={llm.tokens_prompt ?? '—'} />
    <MetaItem label="TOKENS completion" value={llm.tokens_completion ?? '—'} />
    <MetaItem label="TOKENS total" value={llm.tokens_total ?? '—'} />
    <MetaItem label="СТОИМОСТЬ хода" value={`$${llm.estimated_cost_usd?.toFixed(6) ?? '—'}`} highlight />
    <MetaItem label="СТОИМОСТЬ сессии" value={`$${trace.session_dashboard?.total_cost_usd?.toFixed(6) ?? '—'}`} />
  </div>
</AccordionSection>
```

#### Блок 5 — Turn Diff (НОВЫЙ)

Показывать только если `turn_diff` присутствует и есть изменения.

```tsx
{trace.turn_diff && (
  <AccordionSection title="Turn diff">
    <div className="text-xs space-y-1">
      {diff.nervous_state_prev !== diff.nervous_state_curr && (
        <DiffRow label="nervous_state" prev={diff.nervous_state_prev} curr={diff.nervous_state_curr} />
      )}
      {diff.phase_prev !== diff.phase_curr && (
        <DiffRow label="phase" prev={diff.phase_prev} curr={diff.phase_curr} />
      )}
      <div>relation: <b>{diff.relation_to_thread}</b></div>
      <div>memory delta: {diff.memory_turns_delta >= 0 ? '+' : ''}{diff.memory_turns_delta} turns</div>
      <div>semantic delta: {diff.semantic_hits_delta >= 0 ? '+' : ''}{diff.semantic_hits_delta} hits</div>
    </div>
  </AccordionSection>
)}
```

`DiffRow` — inline компонент: `{prev} → {curr}` с цветами (серый→цветной).

#### Блок 6 — Аномалии (НОВЫЙ)

Показывать только если `anomalies.length > 0`. Цвет заголовка — жёлтый при WARN, красный при ERROR.

```tsx
{anomalies.length > 0 && (
  <AccordionSection title={`Аномалии [${anomalies.length}]`}
    headerClass={anomalies.some(a => a.severity === 'ERROR') ? 'text-red-600' : 'text-yellow-600'}>
    {anomalies.map(a => (
      <AnomalyRow key={a.code} anomaly={a} />
    ))}
  </AccordionSection>
)}
```

`AnomalyRow`: badge `WARN`/`ERROR` + code + message.

#### Блок 7 — Session Dashboard (НОВЫЙ)

```tsx
{dash && (
  <AccordionSection title="Session Dashboard">
    <div className="grid grid-cols-3 gap-2 text-xs">
      <MetaItem label="TURNS" value={dash.total_turns} />
      <MetaItem label="AVG LATENCY" value={`${dash.avg_latency_ms}ms`} />
      <MetaItem label="TOTAL COST" value={`$${dash.total_cost_usd.toFixed(6)}`} highlight />
      <MetaItem label="THREAD SWITCHES" value={dash.thread_switches} />
      <MetaItem label="SAFETY EVENTS" value={dash.safety_events} />
      <MetaItem label="BLOCKS" value={dash.validator_blocks} />
    </div>
    <div className="mt-2 text-xs">
      <span className="text-slate-500">STATE TRAJECTORY: </span>
      {dash.state_trajectory.map((s, i) => (
        <span key={i}>
          <StateBadge state={s} />
          {i < dash.state_trajectory.length - 1 && <span className="mx-1 text-slate-400">→</span>}
        </span>
      ))}
    </div>
  </AccordionSection>
)}
```

#### Вспомогательные компоненты (все в одном файле или рядом)

```tsx
// AccordionSection — переиспользуемый аккордеон с треугольником
const AccordionSection = ({ title, children, nested, headerClass, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={nested ? "ml-2 border-l pl-2" : "rounded-lg border bg-white p-2"}>
      <button onClick={() => setOpen(p => !p)}
        className={`w-full text-left text-xs font-semibold flex items-center gap-1 ${headerClass ?? ''}`}>
        <span>{open ? '▼' : '▶'}</span>
        <span>{title}</span>
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  );
};

// MetaItem — лейбл + значение
const MetaItem = ({ label, value, highlight }) => (
  <div className={`rounded px-2 py-1 ${highlight ? 'bg-slate-100' : ''}`}>
    <div className="text-slate-400 text-[10px] uppercase">{label}</div>
    <div className={`font-medium ${highlight ? 'text-slate-800' : 'text-slate-600'}`}>{value}</div>
  </div>
);

// StateBadge — цветной бейдж состояния
const STATE_COLORS = {
  calm: 'bg-green-100 text-green-700',
  anxious: 'bg-yellow-100 text-yellow-700',
  crisis: 'bg-red-100 text-red-700',
  curious: 'bg-blue-100 text-blue-700',
  confused: 'bg-purple-100 text-purple-700',
  neutral: 'bg-slate-100 text-slate-600',
};
const StateBadge = ({ state }) => (
  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${STATE_COLORS[state] ?? 'bg-slate-100 text-slate-600'}`}>
    {state}
  </span>
);
```

**Acceptance Criteria TASK-F2:**
- [ ] Все 7 блоков присутствуют в компоненте
- [ ] Каждый блок сворачивается/разворачивается треугольником независимо
- [ ] По умолчанию все блоки **свёрнуты** (кроме заголовка виджета)
- [ ] ChunkCard разворачивает полный текст чанка по клику
- [ ] Кнопка "Скопировать всё полотно" копирует system_prompt + user_prompt + response в буфер
- [ ] Аномалии отображаются только при наличии; при SLOW_WRITER заголовок жёлтый
- [ ] STATE TRAJECTORY отображается цветными бейджами со стрелками
- [ ] tsc --noEmit без ошибок

---

## 5. Порядок реализации

```
1. TASK-B2  → writer_agent.py — last_debug (10 мин)
2. TASK-B3  → memory_bundle.py + memory_retrieval.py — rag_query (5 мин)
3. TASK-B1  → orchestrator.py — расширить debug dict (20 мин)
4. TASK-B4  → session_store.py — накопление session stats (15 мин)
5. TASK-B5  → models.py + debug_routes.py — расширить endpoint (30 мин)
6. TASK-F1  → types/index.ts — новые интерфейсы (10 мин)
7. TASK-F2  → MultiAgentTraceWidget.tsx — полная переработка (90 мин)
```

**Суммарная оценка:** ~3 часа агента IDE.

---

## 6. Тесты

### Бэкенд

```python
# TEST-B-01: writer_agent.last_debug заполнен после write()
async def test_writer_last_debug():
    result = await writer_agent.write(mock_contract)
    assert "system_prompt" in writer_agent.last_debug
    assert "user_prompt" in writer_agent.last_debug
    assert "tokens_total" in writer_agent.last_debug
    assert writer_agent.last_debug["tokens_total"] > 0

# TEST-B-02: orchestrator возвращает semantic_hits_detail
async def test_orchestrator_semantic_hits_detail():
    result = await orchestrator.run(query="тест", user_id="u1")
    hits = result["debug"].get("semantic_hits_detail", [])
    assert isinstance(hits, list)
    if hits:
        assert "chunk_id" in hits[0]
        assert "score" in hits[0]
        assert "content_full" in hits[0]

# TEST-B-03: orchestrator возвращает writer промпты
async def test_orchestrator_writer_prompts():
    result = await orchestrator.run(query="тест", user_id="u1")
    assert "writer_system_prompt" in result["debug"]
    assert len(result["debug"]["writer_system_prompt"]) > 10

# TEST-B-04: session stats накапливаются
def test_session_stats_accumulation():
    store = SessionStore()
    store.accumulate_session_stats("sess1", {"tokens_total": 100, "nervous_state": "calm", "estimated_cost_usd": 0.001})
    store.accumulate_session_stats("sess1", {"tokens_total": 200, "nervous_state": "curious", "estimated_cost_usd": 0.002})
    stats = store.get_session_stats("sess1")
    assert stats["total_turns"] == 2
    assert stats["total_tokens"] == 300
    assert stats["state_trajectory"] == ["calm", "curious"]

# TEST-B-05: endpoint возвращает writer_llm секцию
def test_endpoint_writer_llm(client, dev_headers, session_id):
    r = client.get(f"/api/debug/session/{session_id}/multiagent-trace", headers=dev_headers)
    assert r.status_code == 200
    data = r.json()
    assert "writer_llm" in data
    assert "system_prompt" in data["writer_llm"]

# TEST-B-06: anomaly SLOW_WRITER генерируется
def test_anomaly_slow_writer(client, dev_headers, session_with_slow_writer):
    r = client.get(f"/api/debug/session/{session_with_slow_writer}/multiagent-trace", headers=dev_headers)
    anomalies = r.json().get("anomalies", [])
    assert any(a["code"] == "SLOW_WRITER" for a in anomalies)
```

### Фронтенд

```typescript
// TEST-F-01: Блок "Полотно LLM" рендерится
it('renders LLM canvas block', () => {
  render(<MultiAgentTraceWidget trace={mockTraceWithLLM} isExpanded={true} />);
  expect(screen.getByText(/Полотно LLM/)).toBeInTheDocument();
});

// TEST-F-02: ChunkCard разворачивает полный текст
it('expands chunk content on click', async () => {
  render(<MultiAgentTraceWidget trace={mockTraceWithChunks} isExpanded={true} />);
  // открыть Контекст памяти
  await userEvent.click(screen.getByText(/Контекст памяти/));
  // открыть Чанки в Writer
  await userEvent.click(screen.getByText(/Чанки в Writer/));
  // кликнуть на первый чанк
  await userEvent.click(screen.getAllByText(/score:/)[0]);
  expect(screen.getByText(/content_full_mock/)).toBeInTheDocument();
});

// TEST-F-03: Кнопка копирует полотно
it('copies LLM canvas to clipboard', async () => {
  const clipSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
  render(<MultiAgentTraceWidget trace={mockTraceWithLLM} isExpanded={true} />);
  await userEvent.click(screen.getByText(/Скопировать всё полотно/));
  expect(clipSpy).toHaveBeenCalledWith(expect.stringContaining(mockTraceWithLLM.writer_llm!.system_prompt));
});

// TEST-F-04: Session Dashboard отображает state_trajectory
it('renders state trajectory badges', () => {
  const traceWithDash = { ...mockTrace, session_dashboard: {
    state_trajectory: ['calm', 'curious', 'confused'],
    total_turns: 5, avg_latency_ms: 1100, total_cost_usd: 0.005,
    thread_switches: 0, safety_events: 0, validator_blocks: 0
  }};
  render(<MultiAgentTraceWidget trace={traceWithDash} isExpanded={true} />);
  expect(screen.getByText('calm')).toBeInTheDocument();
  expect(screen.getByText('curious')).toBeInTheDocument();
});

// TEST-F-05: Аномалия SLOW_WRITER показывает жёлтый заголовок
it('shows anomalies section for SLOW_WRITER', () => {
  const traceWithAnomaly = { ...mockTrace, anomalies: [{
    code: 'SLOW_WRITER', severity: 'WARN', message: 'Writer занял 580ms'
  }]};
  render(<MultiAgentTraceWidget trace={traceWithAnomaly} isExpanded={true} />);
  expect(screen.getByText(/Аномалии \[1\]/)).toBeInTheDocument();
  expect(screen.getByText(/Writer занял 580ms/)).toBeInTheDocument();
});
```

---

## 7. Acceptance Criteria (для владельца)

- [ ] **AC-1:** Под ответом NEO разворачивается виджет, все 7 блоков присутствуют
- [ ] **AC-2:** В блоке "Контекст памяти" → "История ходов" вижу полный текст всех turns которые бот держал в контексте
- [ ] **AC-3:** В блоке "Контекст памяти" → "Чанки в Writer" вижу список чанков; клик на чанк раскрывает полный текст
- [ ] **AC-4:** В блоке "Полотно LLM" → "System prompt" вижу ПОЛНЫЙ системный промпт Writer-агента
- [ ] **AC-5:** В блоке "Полотно LLM" → "User prompt" вижу весь контекст который улетел в OpenAI API
- [ ] **AC-6:** Кнопка "Скопировать всё полотно" копирует весь промпт в буфер обмена
- [ ] **AC-7:** В блоке "Токены и стоимость" вижу разбивку prompt/completion/total и цену хода в USD
- [ ] **AC-8:** В блоке "Session Dashboard" вижу STATE TRAJECTORY — цепочку состояний пользователя через весь диалог
- [ ] **AC-9:** При медленном Writer (> 60% времени) — в блоке "Аномалии" появляется SLOW_WRITER WARN
- [ ] **AC-10:** Все блоки по умолчанию свёрнуты; чат не перегружен

---

## 8. Что НЕ входит в PRD-026 Rev.2

- Удаление старого каскадного трейса (отдельная задача после полной миграции)
- Веб-AdminPage (PRD-027)
- Персистентное хранение трейсов в БД между перезапусками сервера

---

*PRD-026 Rev.2 v2.0 | NEO Bot | Эпоха 4 — Мультиагентность*
