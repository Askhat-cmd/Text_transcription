# PRD-026 — Мультиагентный трейс-виджет NEO

**Версия:** 1.0  
**Статус:** Ready for implementation  
**Репозиторий:** https://github.com/Askhat-cmd/Text_transcription  
**Рабочая директория:** `bot_psychologist/`  
**Связанный PRD:** PRD-027 (Веб-AdminPage)  
**Дата:** 2026-04-26

---

## 1. Цель и контекст

### 1.1 Проблема

Текущий трейс-виджет в `ChatPage.tsx` → `ChatWindow` → `components/chat/` отображает данные **старой каскадной системы NEO** (Эпоха 3). Поля `recommended_mode`, `user_state`, `hybrid_query_text`, `chunks_retrieved`, `pipeline_stages`, `llm_calls[]`, `summary_text` — всё это артефакты старого пайплайна, которые новый `MultiAgentOrchestrator` не возвращает.

После перехода на Эпоху 4 (мультиагентность) трейс фактически **слепой**: разработчик не видит, что происходит внутри каждого из 5 агентов при обработке каждого запроса пользователя.

### 1.2 Цель PRD-026

Создать полностью рабочий мультиагентный трейс, который при каждом ответе NEO показывает:
- Что именно решил каждый агент (State Analyzer, Thread Manager, Memory Agent, Writer, Validator)
- Сколько времени занял каждый агент (латентность)
- Итоговые метрики: модель, токены, статус валидации
- Визуальные сигналы: safety alert, блокировка валидатора, смена нити

### 1.3 Принципы реализации

- **Additive only** — не удалять старые поля из debug_routes.py, только добавлять новые эндпоинты
- **Feature flag** — трейс-виджет переключается через `MULTIAGENT_ENABLED`
- **Не ломать** — старый трейс остаётся доступен при `MULTIAGENT_ENABLED=false`
- **Тайминги в оркестраторе** — добавляются как часть этого PRD (см. раздел 3.1)

---

## 2. Архитектура решения

### 2.1 Слои изменений

```
[orchestrator.py]          ← Слой 1: добавить тайминги агентов
      ↓
[api/chat_routes.py]       ← Слой 2: сохранять multiagent_debug в session store
      ↓
[api/debug_routes.py]      ← Слой 3: новый эндпоинт /multiagent-trace
      ↓
[api/models.py]            ← Слой 4: новые Pydantic-модели
      ↓
[web_ui/src/types/]        ← Слой 5: TypeScript-типы
      ↓
[web_ui/src/services/]     ← Слой 6: метод apiService
      ↓
[web_ui/src/components/]   ← Слой 7: MultiAgentTraceWidget.tsx
      ↓
[ChatWindow / useChat]     ← Слой 8: подключение нового виджета
```

### 2.2 Схема данных трейса (итоговый контракт)

```json
{
  "session_id": "string",
  "turn_index": 5,
  "pipeline_version": "multiagent_v1",
  "total_latency_ms": 1240,
  "agents": {
    "state_analyzer": {
      "latency_ms": 310,
      "nervous_state": "calm | anxious | crisis | neutral",
      "intent": "string",
      "safety_flag": false,
      "confidence": 0.87
    },
    "thread_manager": {
      "latency_ms": 45,
      "thread_id": "string",
      "phase": "exploring | deepening | closing",
      "relation_to_thread": "continue | new_thread",
      "continuity_score": 0.72
    },
    "memory_retrieval": {
      "latency_ms": 280,
      "context_turns": 4,
      "semantic_hits_count": 3,
      "has_relevant_knowledge": true
    },
    "writer": {
      "latency_ms": 580,
      "response_mode": "string",
      "tokens_used": 412,
      "model_used": "string"
    },
    "validator": {
      "latency_ms": 25,
      "is_blocked": false,
      "block_reason": null,
      "quality_flags": []
    }
  }
}
```

---

## 3. Задачи бэкенда

### TASK-B1: Добавить тайминги в orchestrator.py

**Файл:** `bot_psychologist/bot_agent/multiagent/orchestrator.py`

**Описание:** Обернуть каждый вызов агента в `time.perf_counter()`. Добавить `timings` dict в возвращаемый `debug`-словарь.

**Реализация:**

```python
import time

async def run(self, *, query: str, user_id: str) -> dict:
    query = self._normalize_query(query)
    t_total_start = time.perf_counter()

    current_thread = thread_storage.load_active(user_id)
    archived_threads = thread_storage.load_archived(user_id)

    # State Analyzer
    t0 = time.perf_counter()
    state_snapshot = await state_analyzer_agent.analyze(
        user_message=query,
        previous_thread=current_thread,
    )
    t_state = int((time.perf_counter() - t0) * 1000)

    # Thread Manager
    t0 = time.perf_counter()
    updated_thread = await thread_manager_agent.update(
        user_message=query,
        state_snapshot=state_snapshot,
        user_id=user_id,
        current_thread=current_thread,
        archived_threads=archived_threads,
    )
    t_thread = int((time.perf_counter() - t0) * 1000)

    if updated_thread.relation_to_thread == "new_thread" and current_thread is not None:
        thread_storage.archive_thread(current_thread, reason="new_thread")
    thread_storage.save_active(updated_thread)

    # Memory Retrieval
    t0 = time.perf_counter()
    memory_bundle = await memory_retrieval_agent.assemble(
        user_message=query,
        thread_state=updated_thread,
        user_id=user_id,
    )
    t_memory = int((time.perf_counter() - t0) * 1000)

    # Writer
    writer_contract = WriterContract(
        user_message=query,
        thread_state=updated_thread,
        memory_bundle=memory_bundle,
    )
    t0 = time.perf_counter()
    draft_answer = await writer_agent.write(writer_contract)
    t_writer = int((time.perf_counter() - t0) * 1000)

    # Validator
    t0 = time.perf_counter()
    validation_result = validator_agent.validate(draft_answer, writer_contract)
    t_validator = int((time.perf_counter() - t0) * 1000)

    if validation_result.is_blocked:
        final_answer = validation_result.safe_replacement or draft_answer
    else:
        final_answer = draft_answer

    asyncio.create_task(
        memory_retrieval_agent.update(
            user_id=user_id,
            user_message=query,
            assistant_response=final_answer,
            thread_state=updated_thread,
        )
    )

    total_latency = int((time.perf_counter() - t_total_start) * 1000)

    return {
        "status": "ok",
        "answer": final_answer,
        "thread_id": updated_thread.thread_id,
        "phase": updated_thread.phase,
        "response_mode": updated_thread.response_mode,
        "relation_to_thread": updated_thread.relation_to_thread,
        "continuity_score": updated_thread.continuity_score,
        "debug": {
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "total_latency_ms": total_latency,
            "nervous_state": state_snapshot.nervous_state,
            "intent": state_snapshot.intent,
            "safety_flag": state_snapshot.safety_flag,
            "confidence": state_snapshot.confidence,
            "thread_id": updated_thread.thread_id,
            "phase": updated_thread.phase,
            "relation_to_thread": updated_thread.relation_to_thread,
            "continuity_score": updated_thread.continuity_score,
            "has_relevant_knowledge": memory_bundle.has_relevant_knowledge,
            "context_turns": memory_bundle.context_turns,
            "semantic_hits_count": len(memory_bundle.semantic_hits),
            "validator_blocked": validation_result.is_blocked,
            "validator_block_reason": validation_result.block_reason,
            "validator_quality_flags": validation_result.quality_flags,
            "timings": {
                "state_analyzer_ms": t_state,
                "thread_manager_ms": t_thread,
                "memory_retrieval_ms": t_memory,
                "writer_ms": t_writer,
                "validator_ms": t_validator,
            },
        },
    }
```

**Acceptance Criteria TASK-B1:**
- [ ] `debug.timings` присутствует в каждом ответе оркестратора
- [ ] Каждый из 5 ключей (`state_analyzer_ms`, `thread_manager_ms`, `memory_retrieval_ms`, `writer_ms`, `validator_ms`) — целое число в миллисекундах
- [ ] `debug.total_latency_ms` ≥ сумма всех agent timings (разница = overhead хранилища)
- [ ] `debug.pipeline_version == "multiagent_v1"`

---

### TASK-B2: Новые Pydantic-модели в models.py

**Файл:** `bot_psychologist/api/models.py`

**Добавить следующие модели** (не удалять существующие):

```python
from pydantic import BaseModel
from typing import Optional, List

class AgentTimings(BaseModel):
    state_analyzer_ms: int = 0
    thread_manager_ms: int = 0
    memory_retrieval_ms: int = 0
    writer_ms: int = 0
    validator_ms: int = 0

class StateAnalyzerTrace(BaseModel):
    latency_ms: int
    nervous_state: str
    intent: str
    safety_flag: bool
    confidence: float

class ThreadManagerTrace(BaseModel):
    latency_ms: int
    thread_id: str
    phase: str
    relation_to_thread: str
    continuity_score: float

class MemoryRetrievalTrace(BaseModel):
    latency_ms: int
    context_turns: int
    semantic_hits_count: int
    has_relevant_knowledge: bool

class WriterTrace(BaseModel):
    latency_ms: int
    response_mode: str
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None

class ValidatorTrace(BaseModel):
    latency_ms: int
    is_blocked: bool
    block_reason: Optional[str] = None
    quality_flags: List[str] = []

class MultiAgentPipelineTrace(BaseModel):
    state_analyzer: StateAnalyzerTrace
    thread_manager: ThreadManagerTrace
    memory_retrieval: MemoryRetrievalTrace
    writer: WriterTrace
    validator: ValidatorTrace

class MultiAgentTraceResponse(BaseModel):
    session_id: str
    turn_index: Optional[int]
    pipeline_version: str
    total_latency_ms: int
    agents: MultiAgentPipelineTrace
```

**Acceptance Criteria TASK-B2:**
- [ ] Все модели импортируются без ошибок
- [ ] Валидация через `MultiAgentTraceResponse(**data)` проходит с реальными данными оркестратора

---

### TASK-B3: Сохранение multiagent debug в session store

**Файл:** `bot_psychologist/api/chat_routes.py` (или файл, где обрабатывается ответ оркестратора)

**Описание:** После получения ответа от `orchestrator.run()` сохранять `result["debug"]` в session store под ключом `multiagent_debug_{turn_index}`, чтобы эндпоинт трейса мог его достать.

**Логика:**
```python
result = await orchestrator.run(query=user_message, user_id=user_id)
debug_payload = result.get("debug", {})
if debug_payload.get("multiagent_enabled"):
    store.save_multiagent_debug(
        session_id=session_id,
        turn_index=turn_index,
        debug=debug_payload,
    )
```

**Метод `save_multiagent_debug` добавить в `session_store.py`:**
```python
def save_multiagent_debug(self, session_id: str, turn_index: int, debug: dict) -> None:
    key = f"ma_debug_{session_id}_{turn_index}"
    self._store[key] = debug  # используется существующий механизм хранилища

def get_multiagent_debug(self, session_id: str, turn_index: int) -> dict | None:
    key = f"ma_debug_{session_id}_{turn_index}"
    return self._store.get(key)

def get_latest_multiagent_debug(self, session_id: str) -> dict | None:
    # возвращает debug с максимальным turn_index для данной сессии
    prefix = f"ma_debug_{session_id}_"
    matches = {k: v for k, v in self._store.items() if k.startswith(prefix)}
    if not matches:
        return None
    latest_key = max(matches.keys(), key=lambda k: int(k.split("_")[-1]))
    return matches[latest_key]
```

**Acceptance Criteria TASK-B3:**
- [ ] После каждого ответа оркестратора `debug` сохраняется в store
- [ ] `get_latest_multiagent_debug(session_id)` возвращает debug последнего хода
- [ ] При `MULTIAGENT_ENABLED=false` — сохранение не происходит (guard через `debug.get("multiagent_enabled")`)

---

### TASK-B4: Новый эндпоинт в debug_routes.py

**Файл:** `bot_psychologist/api/debug_routes.py`

**Добавить** (не удалять старые маршруты):

```python
@router.get("/session/{session_id}/multiagent-trace", response_model=MultiAgentTraceResponse)
async def get_multiagent_trace(
    session_id: str,
    turn_index: Optional[int] = Query(default=None),
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=403, detail="Debug access denied")

    if turn_index is not None:
        debug = store.get_multiagent_debug(session_id, turn_index)
    else:
        debug = store.get_latest_multiagent_debug(session_id)

    if not debug:
        raise HTTPException(status_code=404, detail="Multiagent trace not found for this session")

    if not debug.get("multiagent_enabled"):
        raise HTTPException(status_code=409, detail="Session was processed by legacy pipeline")

    timings = debug.get("timings", {})

    return MultiAgentTraceResponse(
        session_id=session_id,
        turn_index=debug.get("turn_index"),
        pipeline_version=debug.get("pipeline_version", "multiagent_v1"),
        total_latency_ms=debug.get("total_latency_ms", 0),
        agents=MultiAgentPipelineTrace(
            state_analyzer=StateAnalyzerTrace(
                latency_ms=timings.get("state_analyzer_ms", 0),
                nervous_state=debug.get("nervous_state", "neutral"),
                intent=debug.get("intent", ""),
                safety_flag=bool(debug.get("safety_flag", False)),
                confidence=float(debug.get("confidence", 0.0)),
            ),
            thread_manager=ThreadManagerTrace(
                latency_ms=timings.get("thread_manager_ms", 0),
                thread_id=debug.get("thread_id", ""),
                phase=debug.get("phase", "exploring"),
                relation_to_thread=debug.get("relation_to_thread", "continue"),
                continuity_score=float(debug.get("continuity_score", 0.0)),
            ),
            memory_retrieval=MemoryRetrievalTrace(
                latency_ms=timings.get("memory_retrieval_ms", 0),
                context_turns=int(debug.get("context_turns", 0)),
                semantic_hits_count=int(debug.get("semantic_hits_count", 0)),
                has_relevant_knowledge=bool(debug.get("has_relevant_knowledge", False)),
            ),
            writer=WriterTrace(
                latency_ms=timings.get("writer_ms", 0),
                response_mode=debug.get("response_mode", ""),
                tokens_used=debug.get("tokens_used"),
                model_used=debug.get("model_used"),
            ),
            validator=ValidatorTrace(
                latency_ms=timings.get("validator_ms", 0),
                is_blocked=bool(debug.get("validator_blocked", False)),
                block_reason=debug.get("validator_block_reason"),
                quality_flags=list(debug.get("validator_quality_flags") or []),
            ),
        ),
    )
```

**Acceptance Criteria TASK-B4:**
- [ ] `GET /api/debug/session/{id}/multiagent-trace` возвращает 200 с корректным JSON
- [ ] `GET /api/debug/session/{id}/multiagent-trace?turn_index=3` возвращает конкретный ход
- [ ] Без dev API key — 403
- [ ] Для legacy-сессии — 409 с понятным сообщением
- [ ] Если сессия не найдена — 404

---

## 4. Задачи фронтенда

### TASK-F1: TypeScript-тип MultiAgentTrace

**Файл:** `bot_psychologist/web_ui/src/types/index.ts` (или `trace.types.ts` если уже разнесено)

**Добавить** (не удалять существующие типы):

```typescript
export interface AgentTimings {
  state_analyzer_ms: number;
  thread_manager_ms: number;
  memory_retrieval_ms: number;
  writer_ms: number;
  validator_ms: number;
}

export interface StateAnalyzerTrace {
  latency_ms: number;
  nervous_state: 'calm' | 'anxious' | 'crisis' | 'neutral' | string;
  intent: string;
  safety_flag: boolean;
  confidence: number;
}

export interface ThreadManagerTrace {
  latency_ms: number;
  thread_id: string;
  phase: 'exploring' | 'deepening' | 'closing' | string;
  relation_to_thread: 'continue' | 'new_thread';
  continuity_score: number;
}

export interface MemoryRetrievalTrace {
  latency_ms: number;
  context_turns: number;
  semantic_hits_count: number;
  has_relevant_knowledge: boolean;
}

export interface WriterTrace {
  latency_ms: number;
  response_mode: string;
  tokens_used?: number;
  model_used?: string;
}

export interface ValidatorTrace {
  latency_ms: number;
  is_blocked: boolean;
  block_reason?: string | null;
  quality_flags: string[];
}

export interface MultiAgentPipelineTrace {
  state_analyzer: StateAnalyzerTrace;
  thread_manager: ThreadManagerTrace;
  memory_retrieval: MemoryRetrievalTrace;
  writer: WriterTrace;
  validator: ValidatorTrace;
}

export interface MultiAgentTraceData {
  session_id: string;
  turn_index?: number;
  pipeline_version: string;
  total_latency_ms: number;
  agents: MultiAgentPipelineTrace;
}
```

**Acceptance Criteria TASK-F1:**
- [ ] Типы экспортируются без ошибок TypeScript
- [ ] `MultiAgentTraceData` полностью совпадает с `MultiAgentTraceResponse` из бэкенда

---

### TASK-F2: Метод в apiService

**Файл:** `bot_psychologist/web_ui/src/services/api.service.ts`

**Добавить метод** (не удалять существующие):

```typescript
async getMultiAgentTrace(
  sessionId: string,
  turnIndex?: number
): Promise<MultiAgentTraceData> {
  const params = turnIndex !== undefined ? `?turn_index=${turnIndex}` : '';
  const response = await this.get<MultiAgentTraceData>(
    `/debug/session/${sessionId}/multiagent-trace${params}`
  );
  return response;
}
```

**Acceptance Criteria TASK-F2:**
- [ ] Метод вызывается без ошибок TypeScript
- [ ] При 404 — пробрасывает ошибку (не глотает)
- [ ] При 409 (legacy) — ошибка содержит `"legacy pipeline"` в message

---

### TASK-F3: Компонент MultiAgentTraceWidget.tsx

**Файл:** `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`

**Описание:** Новый React-компонент, встраивается под сообщением бота вместо (или рядом с) текущим трейс-виджетом при `MULTIAGENT_ENABLED`.

#### 3.1 Props

```typescript
interface MultiAgentTraceWidgetProps {
  trace: MultiAgentTraceData;
  isExpanded?: boolean;
  onToggle?: () => void;
}
```

#### 3.2 Структура виджета

```
┌─────────────────────────────────────────────────────────┐
│ 🤖 Pipeline NEO  •  multiagent_v1  •  1240ms  [▼/▲]    │
│  [🔴 SAFETY] / [🟡 BLOCKED] / [🟢 OK]                   │
├─────────────────────────────────────────────────────────┤
│ [State Analyzer 310ms]  nervous: calm  intent: support  │
│   confidence: 87%   safety: ✅                          │
├─────────────────────────────────────────────────────────┤
│ [Thread Manager 45ms]  phase: exploring  → continue     │
│   thread_id: abc123   continuity: 72%                   │
├─────────────────────────────────────────────────────────┤
│ [Memory Agent 280ms]  turns: 4  hits: 3  knowledge: ✅  │
├─────────────────────────────────────────────────────────┤
│ [Writer 580ms]  mode: empathic   tokens: 412            │
│   model: gpt-4o-mini                                    │
├─────────────────────────────────────────────────────────┤
│ [Validator 25ms]  ✅ Passed   flags: none               │
└─────────────────────────────────────────────────────────┘
```

#### 3.3 Цветовая семантика

| Условие | Цвет заголовка | Иконка |
|---|---|---|
| `safety_flag === true` | `bg-red-100 border-red-400` | 🔴 SAFETY ALERT |
| `validator.is_blocked === true` | `bg-yellow-100 border-yellow-400` | 🟡 BLOCKED |
| `relation_to_thread === "new_thread"` | `bg-blue-50 border-blue-300` | 🔵 NEW THREAD |
| всё ок | `bg-slate-50 border-slate-200` | 🟢 OK |

#### 3.4 Timeline-бар латентности

Под виджетом отображается горизонтальный прогресс-бар, где каждый сегмент = пропорциональное время агента:
```
[State █████ 25%][Thread █ 4%][Memory ██████ 23%][Writer ██████████ 47%][Val █ 2%]
```
Цвета сегментов: синий / серый / зелёный / фиолетовый / оранжевый.

#### 3.5 Skeleton-лоадер

При `isLoading=true` виджет показывает placeholder-строки (анимированный pulse), не пустой блок.

#### 3.6 Поведение collapse/expand

- По умолчанию: **свёрнут** (показывается только заголовок-строка с total latency и статусом)
- Клик на заголовок — разворачивает все секции
- Каждая секция агента коллапсируется отдельно (accordion)

**Acceptance Criteria TASK-F3:**
- [ ] Компонент рендерится без ошибок с mock-данными
- [ ] В свёрнутом состоянии виден только заголовок (total_latency, pipeline_version, статус)
- [ ] Клик разворачивает все 5 секций агентов
- [ ] `safety_flag=true` → заголовок красный
- [ ] `validator.is_blocked=true` → заголовок жёлтый, в секции Validator виден `block_reason`
- [ ] `relation_to_thread="new_thread"` → синий бейдж "NEW THREAD" в секции Thread Manager
- [ ] Timeline-бар отображает корректные пропорции (суммарно = total_latency_ms)
- [ ] При `trace=null` — компонент возвращает `null` (не крашится)

---

### TASK-F4: Интеграция виджета в ChatWindow / сообщения бота

**Файл:** `bot_psychologist/web_ui/src/components/chat/ChatWindow.tsx` (или компонент, рендерящий `BotMessage`)

**Описание:** При `MULTIAGENT_ENABLED` и наличии dev-ключа — под каждым ответом бота показывать `<MultiAgentTraceWidget>`.

**Логика показа:**
```typescript
// В компоненте BotMessage или аналогичном:
const [maTrace, setMaTrace] = useState<MultiAgentTraceData | null>(null);
const [isTraceExpanded, setIsTraceExpanded] = useState(false);

useEffect(() => {
  if (!sessionId || !isDevMode) return;
  apiService.getMultiAgentTrace(sessionId)
    .then(setMaTrace)
    .catch(() => setMaTrace(null)); // не крашим, тихо скипаем
}, [sessionId, message.id]);

// В JSX:
{maTrace && (
  <MultiAgentTraceWidget
    trace={maTrace}
    isExpanded={isTraceExpanded}
    onToggle={() => setIsTraceExpanded(prev => !prev)}
  />
)}
```

**Важно:** `isDevMode` определяется по наличию dev API key (уже есть в `is_dev_key` на бэкенде, фронт должен это знать через существующий `apiService`).

**Acceptance Criteria TASK-F4:**
- [ ] Виджет появляется под ответом бота при dev-ключе
- [ ] Обычный пользователь (без dev-ключа) виджет не видит
- [ ] При ошибке fetch — виджет тихо скрывается (no crash)
- [ ] Старый трейс-виджет продолжает работать при `MULTIAGENT_ENABLED=false`

---

### TASK-F5: Хук useMultiAgentTrace

**Файл:** `bot_psychologist/web_ui/src/hooks/useMultiAgentTrace.ts`

**Описание:** Хук инкапсулирует логику загрузки и кэширования мультиагентного трейса.

```typescript
interface UseMultiAgentTraceResult {
  trace: MultiAgentTraceData | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useMultiAgentTrace(
  sessionId: string | undefined,
  messageId: string,
  enabled: boolean
): UseMultiAgentTraceResult {
  const [trace, setTrace] = useState<MultiAgentTraceData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!sessionId || !enabled) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiService.getMultiAgentTrace(sessionId);
      setTrace(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Trace unavailable');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, enabled]);

  useEffect(() => { void fetch(); }, [fetch]);

  return { trace, isLoading, error, refetch: fetch };
}
```

**Acceptance Criteria TASK-F5:**
- [ ] При `enabled=false` хук не делает запросов
- [ ] `isLoading=true` пока идёт fetch
- [ ] При 404/409 — `error` заполнен, `trace=null`
- [ ] `refetch()` повторно загружает данные

---

## 5. Порядок реализации (sequence)

```
1. TASK-B1  → orchestrator.py — тайминги (5 мин, риск: низкий)
2. TASK-B2  → models.py — Pydantic-модели (10 мин, риск: низкий)
3. TASK-B3  → session_store.py + chat_routes.py — сохранение debug (20 мин, риск: средний)
4. TASK-B4  → debug_routes.py — новый эндпоинт (15 мин, риск: низкий)
5. TASK-F1  → types/ — TypeScript-типы (5 мин, риск: низкий)
6. TASK-F2  → api.service.ts — метод (5 мин, риск: низкий)
7. TASK-F5  → useMultiAgentTrace.ts — хук (15 мин, риск: низкий)
8. TASK-F3  → MultiAgentTraceWidget.tsx — компонент (60 мин, риск: средний)
9. TASK-F4  → интеграция в ChatWindow (20 мин, риск: средний)
```

**Суммарная оценка:** ~2.5–3 часа работы агента IDE.

---

## 6. Тесты

### 6.1 Бэкенд (pytest)

**Файл:** `bot_psychologist/tests/test_multiagent_trace.py`

```python
# TEST-B-01: Orchestrator возвращает тайминги
async def test_orchestrator_returns_timings():
    result = await orchestrator.run(query="тест", user_id="test_user")
    assert "timings" in result["debug"]
    timings = result["debug"]["timings"]
    assert "state_analyzer_ms" in timings
    assert "writer_ms" in timings
    assert all(isinstance(v, int) for v in timings.values())

# TEST-B-02: Тайминги > 0
async def test_orchestrator_timings_positive():
    result = await orchestrator.run(query="как дела?", user_id="test_user")
    timings = result["debug"]["timings"]
    assert timings["writer_ms"] > 0

# TEST-B-03: pipeline_version корректен
async def test_orchestrator_pipeline_version():
    result = await orchestrator.run(query="тест", user_id="test_user")
    assert result["debug"]["pipeline_version"] == "multiagent_v1"

# TEST-B-04: Эндпоинт /multiagent-trace возвращает 200
def test_multiagent_trace_endpoint(client, dev_headers, session_with_debug):
    response = client.get(
        f"/api/debug/session/{session_with_debug}/multiagent-trace",
        headers=dev_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "state_analyzer" in data["agents"]

# TEST-B-05: Без dev ключа — 403
def test_multiagent_trace_no_dev_key(client, user_headers, session_with_debug):
    response = client.get(
        f"/api/debug/session/{session_with_debug}/multiagent-trace",
        headers=user_headers
    )
    assert response.status_code == 403

# TEST-B-06: Несуществующая сессия — 404
def test_multiagent_trace_not_found(client, dev_headers):
    response = client.get(
        "/api/debug/session/nonexistent_xyz/multiagent-trace",
        headers=dev_headers
    )
    assert response.status_code == 404

# TEST-B-07: Pydantic-модель валидирует реальные данные
def test_multiagent_trace_response_model():
    data = { ... }  # реальные данные из orchestrator.run()
    parsed = MultiAgentTraceResponse(**data)
    assert parsed.pipeline_version == "multiagent_v1"
```

### 6.2 Фронтенд (Vitest / React Testing Library)

**Файл:** `bot_psychologist/web_ui/src/components/chat/__tests__/MultiAgentTraceWidget.test.tsx`

```typescript
// TEST-F-01: Рендер в свёрнутом состоянии
it('renders collapsed header with total latency', () => {
  render(<MultiAgentTraceWidget trace={mockTrace} />);
  expect(screen.getByText(/1240ms/)).toBeInTheDocument();
  expect(screen.queryByText(/State Analyzer/)).not.toBeVisible();
});

// TEST-F-02: Expand по клику
it('expands on header click', async () => {
  render(<MultiAgentTraceWidget trace={mockTrace} />);
  await userEvent.click(screen.getByRole('button', { name: /pipeline/i }));
  expect(screen.getByText(/State Analyzer/)).toBeVisible();
});

// TEST-F-03: Safety flag = красный заголовок
it('shows red header when safety_flag is true', () => {
  const dangerTrace = { ...mockTrace, agents: { ...mockTrace.agents,
    state_analyzer: { ...mockTrace.agents.state_analyzer, safety_flag: true }
  }};
  const { container } = render(<MultiAgentTraceWidget trace={dangerTrace} />);
  expect(container.firstChild).toHaveClass('border-red-400');
});

// TEST-F-04: validator blocked = жёлтый заголовок
it('shows yellow header when validator is blocked', () => {
  const blockedTrace = { ...mockTrace, agents: { ...mockTrace.agents,
    validator: { ...mockTrace.agents.validator, is_blocked: true, block_reason: 'unsafe content' }
  }};
  render(<MultiAgentTraceWidget trace={blockedTrace} />);
  expect(screen.getByText(/unsafe content/)).toBeInTheDocument();
});

// TEST-F-05: null trace — не крашится
it('returns null for null trace gracefully', () => {
  const { container } = render(<MultiAgentTraceWidget trace={null as any} />);
  expect(container.firstChild).toBeNull();
});

// TEST-F-06: Timeline бар отображается
it('renders latency timeline bar', () => {
  render(<MultiAgentTraceWidget trace={mockTrace} isExpanded={true} />);
  expect(screen.getByRole('progressbar')).toBeInTheDocument();
});
```

---

## 7. Acceptance Criteria (итоговые, для владельца)

После реализации и деплоя владелец проверяет вручную:

- [ ] **AC-1:** Отправить любое сообщение → под ответом NEO виден трейс-виджет (в dev-режиме)
- [ ] **AC-2:** Виджет показывает 5 секций агентов с реальными данными, не mock
- [ ] **AC-3:** В секции State Analyzer виден `nervous_state` и `confidence` текущего сообщения
- [ ] **AC-4:** В секции Thread Manager виден `phase` и `relation_to_thread`; при новой теме — бейдж "NEW THREAD"
- [ ] **AC-5:** Timeline-бар пропорционально отражает время каждого агента
- [ ] **AC-6:** Написать сообщение с потенциально опасным содержанием → заголовок виджета красный, `safety_flag=true`
- [ ] **AC-7:** Обычный пользователь (без dev-ключа) трейс не видит
- [ ] **AC-8:** При `MULTIAGENT_ENABLED=false` — старый трейс-виджет работает без изменений
- [ ] **AC-9:** `GET /api/debug/session/{id}/multiagent-trace` через curl/Postman возвращает корректный JSON
- [ ] **AC-10:** В консоли браузера нет ошибок TypeScript и React-ошибок

---

## 8. Что НЕ входит в PRD-026

- Удаление старой каскадной системы из кода (это отдельная задача Эпохи 5)
- Веб-AdminPage с управлением агентами (PRD-027)
- Персистентное хранение трейсов в БД (трейс живёт в памяти в рамках сессии)
- История трейсов предыдущих ходов в одном диалоге (только последний ход)

---

*PRD-026 v1.0 | NEO Bot | Эпоха 4 — Мультиагентность*
