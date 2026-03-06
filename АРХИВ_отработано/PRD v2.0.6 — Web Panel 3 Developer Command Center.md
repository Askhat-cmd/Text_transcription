

***

# PRD v2.0.6 — Web Panel 3: "Developer Command Center"

**Проект:** `bot_psychologist` / `bot_agent` + `web_ui`
**Дата:** 2026-03-04
**Статус:** Ready for implementation
**Приоритет:** High
**Целевой исполнитель:** IDE Agent (Cursor / Windsurf / Copilot Workspace)

***

## 0. ЦЕЛЬ ДОКУМЕНТА И ПРИНЦИПЫ

Данный PRD является **единым авторитетным источником** для реализации Web Panel 3

### 0.1 Философия панели

> **"Разработчик должен понять что пошло не так за 10 секунд, не читая логи."**

Три принципа, которые не нарушаются ни одной реализацией:

- **Progressive disclosure**: L0 всегда видим, L1–L3 раскрываются по запросу. Никаких "простыней" по умолчанию.
- **Backend owns logic**: все флаги аномалий, вычисления, агрегации генерируются на бэкенде. Фронт — только рендеринг.
- **No payload bloat**: тяжёлые тексты (полные промпты, snapshot памяти) передаются только через `blob_id` + отдельный endpoint, никогда инлайново в основной ответ.


### 0.2 Архитектурная карта (итоговая структура)

```
InlineDebugTrace (debug mode only)
│
├── [L0] StatusBar          ← НОВОЕ (из v2.0.5)
│
├── [L1] Routing & SD
│     ├── сетка карточек: mode/state/SD/confidence/rule  ✅ существует
│     ├── fast_path + reason                              ← НОВОЕ
│     ├── block_cap / counts по стадиям                  ← НОВОЕ
│     └── 🎯 SD Classification detail                    ← из v2.0.4
│
├── [L2] Chunks
│     ├── pipeline funnel: initial→sd→stage→cap→final    ← НОВОЕ
│     └── hybrid_query_preview                           ← НОВОЕ
│
├── [L2] LLM Calls          ✅ существует (v2.0.3)
│     ├── prompt preview                                  ✅
│     └── "Full prompt" → blob endpoint                  ← из v2.0.4 (исправлено)
│
├── [L2] Models + Tokens    ✅ существует (v2.0.3)
│     └── Cost Estimator ($)                             ← НОВОЕ
│
├── [L2] Pipeline Timeline  ← из v2.0.4
│
├── [L2] Memory Context     ← из v2.0.4 (расширено)
│     ├── turns content, summary, semantic hits, written
│     └── state_trajectory                               ← из v2.0.5
│
├── [L2] Anomalies          ← из v2.0.5
│
├── [L3] Session Dashboard  ← НОВОЕ (из рекомендаций)
│
├── [L3] Trace History      ← НОВОЕ (из рекомендаций)
│
├── [L3] Config Snapshot    ← НОВОЕ (из рекомендаций)
│
├── [L3] Error View         ← НОВОЕ (из рекомендаций)
│
└── [L3] Export Trace       ← НОВОЕ (из рекомендаций)
```


***

## 1. SCOPE ИЗМЕНЕНИЙ

### 1.1 Бэкенд

| Файл | Изменение |
| :-- | :-- |
| `bot_agent/answer_adaptive.py` | Главный оркестратор: pipeline_stages, fast_path, counts, anomalies, config_snapshot, error capture |
| `bot_agent/conversation_memory.py` | Вернуть turns content, summary text, state_trajectory |
| `bot_agent/semantic_memory.py` | Вернуть детали semantic hits |
| `bot_agent/sd_classifier.py` | Вернуть полный SDClassificationDetail |
| `bot_agent/llm_answerer.py` | Передавать `blob_id` вместо полного текста промптов |
| `api/models.py` (или Pydantic-схемы) | Единый контракт `DebugTraceV206` + все вложенные модели |
| `api/routes/debug.py` (новый файл) | Blob endpoint + Session metrics endpoint |
| `api/session_store.py` (новый файл) | In-memory хранилище трейсов сессии (TTL 30 min) |

### 1.2 Фронтенд

| Файл | Изменение |
| :-- | :-- |
| `web_ui/src/types/chat.types.ts` | Полный контракт типов v2.0.6 |
| `web_ui/src/components/chat/InlineDebugTrace.tsx` | Основной компонент — расширение существующего |
| `web_ui/src/components/debug/StatusBar.tsx` | Новый компонент L0 |
| `web_ui/src/components/debug/AnomalyList.tsx` | Новый компонент |
| `web_ui/src/components/debug/PipelineFunnel.tsx` | Новый компонент |
| `web_ui/src/components/debug/SessionDashboard.tsx` | Новый компонент |
| `web_ui/src/components/debug/TraceHistory.tsx` | Новый компонент |
| `web_ui/src/components/debug/ConfigSnapshot.tsx` | Новый компонент |
| `web_ui/src/components/debug/ErrorView.tsx` | Новый компонент |
| `web_ui/src/hooks/useDebugBlob.ts` | Хук для on-demand загрузки blob'ов |
| `web_ui/src/hooks/useSessionTrace.ts` | Хук для session-level метрик |

### 1.3 НЕ ТРОГАТЬ (запрет для IDE агента)

- `config.py` — только чтение для config_snapshot, не изменять
- `state_classifier.py` — не изменять логику
- `response_formatter.py` — не изменять
- `Message.tsx`, `MessageList.tsx`, `ChatPage.tsx` — не изменять
- Существующие Pydantic-поля — только добавлять, не переименовывать, не удалять
- `context_written` — **существующее поле, не создавать дублирующее** `context_written_to_memory`

***

## 2. DATA CONTRACT: ЕДИНАЯ СХЕМА v2.0.6

### 2.1 Разрешение противоречий из v2.0.4 / v2.0.5

| Конфликт | Решение |
| :-- | :-- |
| `system_prompt_full` инлайново vs `blob_id` | **Победил `blob_id`**. `system_prompt_full` в `LLMCallInfo` не добавляется. Только `system_prompt_blob_id` и `user_prompt_blob_id`. |
| `context_written_to_memory` (v2.0.4) vs `context_written` (существующее) | **Используем существующее `context_written`**. Новое поле не создаём. UI читает `trace.context_written`. |
| `state_trajectory` из `dict` vs из `memory.turns` (объекты) | **Читать из `memory.turns` (объекты)**, не из `get_last_turns()` который возвращает dict без поля `state`. |

### 2.2 Pydantic-схемы (бэкенд)

```python
# api/models.py  —  ДОБАВИТЬ к существующим моделям

from pydantic import BaseModel, Field
from typing import Optional, Literal


# --- Вложенные модели ---

class MemoryTurnPreview(BaseModel):
    turn_index: int
    role: str                        # "user" | "bot"
    text_preview: str                # первые 150 символов
    state: Optional[str] = None      # из memory.turns (объект, не dict)

class SemanticHitDetail(BaseModel):
    block_id: str
    score: float
    text_preview: str                # первые 150 символов
    source: Optional[str] = None

class SDClassificationDetail(BaseModel):
    method: str                      # "keyword" | "llm" | "fallback"
    primary: str                     # "GREEN" | "YELLOW" | "RED"
    secondary: Optional[str] = None
    confidence: float
    indicator: str                   # ключевое слово/фраза-триггер
    allowed_levels: list[str]        # ["GREEN", "YELLOW"]

class PipelineStage(BaseModel):
    name: str          # "state_classifier" | "sd_classifier" | "retrieval" |
                       # "sd_filter" | "stage_filter" | "rerank" | "llm" | "format"
    label: str         # Человекочитаемое: "Классификатор состояния", "SD фильтр" …
    duration_ms: int
    skipped: bool = False

class AnomalyFlag(BaseModel):
    code: str          # константа, см. раздел 3.3
    severity: Literal["info", "warn", "error"]
    message: str       # человекочитаемое объяснение
    target: Optional[str] = None  # anchor: "chunks" | "memory" | "llm" | "sd"

class StateTrajectoryPoint(BaseModel):
    turn: int
    state: str
    confidence: Optional[float] = None

class ConfigSnapshot(BaseModel):
    """Значения конфигурации на момент запроса — для воспроизведения."""
    conversation_history_depth: int
    max_context_size: int
    semantic_search_top_k: int
    sd_confidence_threshold: float
    fast_path_enabled: bool
    rerank_enabled: bool
    model_name: str

class PipelineError(BaseModel):
    """Заполняется только при исключении в пайплайне."""
    stage: str
    exception_type: str
    message: str
    partial_trace_available: bool


# --- Расширение основного trace ---
# ДОБАВИТЬ к существующему DebugTrace / InlineTrace

class DebugTraceV206Extension(BaseModel):
    # --- Fast path ---
    fast_path: Optional[bool] = None
    fast_path_reason: Optional[str] = None  # "greeting"|"short_query"|"name_intro"|"other"

    # --- Routing ---
    decision_rule_id: Optional[str] = None
    mode_reason: Optional[str] = None
    block_cap: Optional[int] = None
    blocks_initial: Optional[int] = None
    blocks_after_sd: Optional[int] = None
    blocks_after_stage: Optional[int] = None
    blocks_after_cap: Optional[int] = None

    # --- Hybrid query ---
    hybrid_query_preview: Optional[str] = None  # max 400 chars

    # --- SD detail ---
    sd_detail: Optional[SDClassificationDetail] = None

    # --- Memory ---
    memory_turns_content: list[MemoryTurnPreview] = Field(default_factory=list)
    summary_text: Optional[str] = None
    semantic_hits_detail: list[SemanticHitDetail] = Field(default_factory=list)
    # НЕ создавать context_written_to_memory — читать из существующего context_written

    # --- State trajectory ---
    state_secondary: list[str] = Field(default_factory=list)
    state_trajectory: list[StateTrajectoryPoint] = Field(default_factory=list)

    # --- Pipeline ---
    pipeline_stages: list[PipelineStage] = Field(default_factory=list)

    # --- Anomalies ---
    anomalies: list[AnomalyFlag] = Field(default_factory=list)

    # --- Blobs (on-demand, не инлайн) ---
    system_prompt_blob_id: Optional[str] = None
    user_prompt_blob_id: Optional[str] = None
    memory_snapshot_blob_id: Optional[str] = None

    # --- Config snapshot ---
    config_snapshot: Optional[ConfigSnapshot] = None

    # --- Cost ---
    estimated_cost_usd: Optional[float] = None  # сумма по всем LLM calls

    # --- Error ---
    pipeline_error: Optional[PipelineError] = None

    # --- Session meta (для TraceHistory) ---
    session_id: Optional[str] = None
    turn_number: Optional[int] = None      # порядковый номер в сессии
```


### 2.3 TypeScript-типы (фронтенд)

```typescript
// web_ui/src/types/chat.types.ts  —  ДОБАВИТЬ к существующим типам

export interface MemoryTurnPreview {
  turn_index: number;
  role: string;
  text_preview: string;
  state?: string | null;
}

export interface SemanticHitDetail {
  block_id: string;
  score: number;
  text_preview: string;
  source?: string | null;
}

export interface SDClassificationDetail {
  method: string;
  primary: string;
  secondary?: string | null;
  confidence: number;
  indicator: string;
  allowed_levels: string[];
}

export interface PipelineStage {
  name: string;
  label: string;
  duration_ms: number;
  skipped?: boolean;
}

export interface AnomalyFlag {
  code: string;
  severity: 'info' | 'warn' | 'error';
  message: string;
  target?: string | null;
}

export interface StateTrajectoryPoint {
  turn: number;
  state: string;
  confidence?: number | null;
}

export interface ConfigSnapshot {
  conversation_history_depth: number;
  max_context_size: number;
  semantic_search_top_k: number;
  sd_confidence_threshold: number;
  fast_path_enabled: boolean;
  rerank_enabled: boolean;
  model_name: string;
}

export interface PipelineError {
  stage: string;
  exception_type: string;
  message: string;
  partial_trace_available: boolean;
}

// Расширение существующего InlineTrace:
// (добавить поля к уже существующему интерфейсу)
export interface InlineTraceV206Extension {
  fast_path?: boolean;
  fast_path_reason?: string | null;
  decision_rule_id?: string | null;
  mode_reason?: string | null;
  block_cap?: number | null;
  blocks_initial?: number | null;
  blocks_after_sd?: number | null;
  blocks_after_stage?: number | null;
  blocks_after_cap?: number | null;
  hybrid_query_preview?: string | null;
  sd_detail?: SDClassificationDetail | null;
  memory_turns_content?: MemoryTurnPreview[];
  summary_text?: string | null;
  semantic_hits_detail?: SemanticHitDetail[];
  state_secondary?: string[];
  state_trajectory?: StateTrajectoryPoint[];
  pipeline_stages?: PipelineStage[];
  anomalies?: AnomalyFlag[];
  system_prompt_blob_id?: string | null;
  user_prompt_blob_id?: string | null;
  memory_snapshot_blob_id?: string | null;
  config_snapshot?: ConfigSnapshot | null;
  estimated_cost_usd?: number | null;
  pipeline_error?: PipelineError | null;
  session_id?: string | null;
  turn_number?: number | null;
}
```


***

## 3. БЭКЕНД: ДЕТАЛЬНАЯ РЕАЛИЗАЦИЯ

### 3.1 Файл: `answer_adaptive.py` — сбор всех метрик

```python
import time
import uuid

# ─── HELPER ───────────────────────────────────────────────────────────────────

def _timed(name: str, label: str, fn, *args, **kwargs):
    """Обёртка для замера времени этапа пайплайна."""
    t = time.perf_counter()
    result = fn(*args, **kwargs)
    ms = int((time.perf_counter() - t) * 1000)
    return result, PipelineStage(name=name, label=label, duration_ms=ms)


def _build_config_snapshot(config) -> ConfigSnapshot:
    """Снимок конфигурации на момент запроса."""
    return ConfigSnapshot(
        conversation_history_depth=config.CONVERSATION_HISTORY_DEPTH,
        max_context_size=config.MAX_CONTEXT_SIZE,
        semantic_search_top_k=config.SEMANTIC_SEARCH_TOP_K,
        sd_confidence_threshold=getattr(config, "SD_CONFIDENCE_THRESHOLD", 0.5),
        fast_path_enabled=getattr(config, "FAST_PATH_ENABLED", True),
        rerank_enabled=getattr(config, "RERANK_ENABLED", False),
        model_name=config.LLM_MODEL_NAME,
    )


# ─── ANOMALY ENGINE ───────────────────────────────────────────────────────────

def _compute_anomalies(trace) -> list[AnomalyFlag]:
    """
    Вызывается в конце пайплайна.
    Бизнес-логика аномалий живёт ТОЛЬКО здесь, фронт не дублирует.
    """
    flags = []

    if trace.sd_detail and trace.sd_detail.method == "fallback":
        flags.append(AnomalyFlag(
            code="SD_FALLBACK",
            severity="warn",
            message="SD классификатор использовал fallback — результат ненадёжен",
            target="sd"
        ))

    if (trace.blocks_after_cap == 0
            and trace.fast_path is not True):
        flags.append(AnomalyFlag(
            code="NO_BLOCKS_TO_LLM",
            severity="error",
            message="LLM получил 0 блоков — ответ без контекста",
            target="chunks"
        ))

    if (trace.blocks_after_sd == 0
            and (trace.blocks_initial or 0) > 0):
        flags.append(AnomalyFlag(
            code="SD_FILTER_TOO_STRICT",
            severity="warn",
            message="SD-фильтр отсеял ВСЕ блоки при наличии retrieval-результатов",
            target="chunks"
        ))

    if (trace.semantic_hits == 0
            and (trace.memory_turns or 0) > 5):
        flags.append(AnomalyFlag(
            code="SEMANTIC_NOT_TRIGGERED",
            severity="info",
            message="Семантический поиск вернул 0 результатов при богатой памяти (>5 turns)",
            target="memory"
        ))

    if trace.fast_path is True:
        query_len = len((trace.hybrid_query_preview or "").split())
        if query_len > 15:
            flags.append(AnomalyFlag(
                code="UNEXPECTED_FAST_PATH",
                severity="warn",
                message=f"Fast path при длинном запросе ({query_len} слов) — проверь логику",
                target="sd"
            ))

    if trace.pipeline_stages:
        total_ms = sum(s.duration_ms for s in trace.pipeline_stages) or 1
        for stage in trace.pipeline_stages:
            if stage.duration_ms > total_ms * 0.5:
                flags.append(AnomalyFlag(
                    code="SLOW_STAGE",
                    severity="warn",
                    message=f"Этап '{stage.label}' занял {stage.duration_ms}ms "
                            f"({stage.duration_ms/total_ms*100:.0f}% общего времени)",
                    target="timeline"
                ))

    if trace.hybrid_query_preview:
        snapshot = trace.config_snapshot
        if snapshot and len(trace.hybrid_query_preview) > snapshot.max_context_size * 0.9:
            flags.append(AnomalyFlag(
                code="CONTEXT_BLOAT_RISK",
                severity="warn",
                message="Hybrid query близок к лимиту MAX_CONTEXT_SIZE",
                target="chunks"
            ))

    return flags


# ─── STATE TRAJECTORY ─────────────────────────────────────────────────────────

def _build_state_trajectory(memory, depth: int = 10) -> list[StateTrajectoryPoint]:
    """
    ВАЖНО: читаем из memory.turns (объекты), НЕ из get_last_turns() который
    возвращает dict без поля state.
    """
    result = []
    turns = memory.turns[-depth:] if hasattr(memory, 'turns') else []
    for i, turn in enumerate(turns):
        state = getattr(turn, 'user_state', None) or getattr(turn, 'state', None)
        if state:
            result.append(StateTrajectoryPoint(
                turn=i,
                state=str(state),
                confidence=getattr(turn, 'state_confidence', None)
            ))
    return result


# ─── BLOB STORE ───────────────────────────────────────────────────────────────

def _store_blob(session_store, session_id: str, content: str) -> str:
    """Сохраняет тяжёлый текст и возвращает blob_id."""
    blob_id = f"{session_id}:{uuid.uuid4().hex[:8]}"
    session_store.set_blob(blob_id, content, ttl_seconds=1800)
    return blob_id


# ─── COST ESTIMATOR ───────────────────────────────────────────────────────────

COST_PER_1K_TOKENS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "default": {"input": 0.001, "output": 0.002},
}

def _estimate_cost(llm_calls: list, model_name: str) -> float:
    rates = COST_PER_1K_TOKENS.get(model_name, COST_PER_1K_TOKENS["default"])
    total = 0.0
    for call in llm_calls:
        input_tokens = getattr(call, 'prompt_tokens', 0) or 0
        output_tokens = getattr(call, 'completion_tokens', 0) or 0
        total += (input_tokens / 1000) * rates["input"]
        total += (output_tokens / 1000) * rates["output"]
    return round(total, 6)
```


### 3.2 Файл: `api/routes/debug.py` — новые endpoints

```python
from fastapi import APIRouter, HTTPException, Depends
from api.session_store import SessionStore

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/blob/{blob_id}")
async def get_blob(blob_id: str, store: SessionStore = Depends()):
    """
    On-demand загрузка тяжёлых данных (полные промпты, snapshot памяти).
    Доступен только в debug/admin режиме (проверяется middleware).
    """
    content = store.get_blob(blob_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Blob not found or expired")
    # Простая санитизация PII
    content = _sanitize_pii(content)
    return {"blob_id": blob_id, "content": content}


@router.get("/session/{session_id}/metrics")
async def get_session_metrics(session_id: str, store: SessionStore = Depends()):
    """
    Агрегированные метрики по сессии для Session Dashboard.
    """
    traces = store.get_session_traces(session_id)
    if not traces:
        raise HTTPException(status_code=404, detail="Session not found")
    return _aggregate_session_metrics(traces)


@router.get("/session/{session_id}/traces")
async def get_session_traces(session_id: str, store: SessionStore = Depends()):
    """
    Список всех трейсов сессии для Trace History.
    """
    traces = store.get_session_traces(session_id)
    return {"session_id": session_id, "traces": traces}


def _sanitize_pii(text: str) -> str:
    """Маскировка email и телефонов перед отдачей в UI."""
    import re
    text = re.sub(r'\b[\w.+-]+@[\w-]+\.\w{2,}\b', '[email]', text)
    text = re.sub(r'\b\+?[\d\s\-()]{10,15}\b', '[phone]', text)
    return text


def _aggregate_session_metrics(traces: list) -> dict:
    total = len(traces)
    fast_path_count = sum(1 for t in traces if t.get('fast_path'))
    sd_levels = [t.get('sd_level', 'unknown') for t in traces]
    llm_times = [t.get('total_duration_ms', 0) for t in traces]
    costs = [t.get('estimated_cost_usd', 0) or 0 for t in traces]
    anomaly_counts = [len(t.get('anomalies', [])) for t in traces]

    return {
        "total_turns": total,
        "fast_path_pct": round(fast_path_count / total * 100, 1) if total else 0,
        "sd_distribution": {
            "GREEN": sd_levels.count("GREEN"),
            "YELLOW": sd_levels.count("YELLOW"),
            "RED": sd_levels.count("RED"),
        },
        "avg_llm_time_ms": round(sum(llm_times) / total) if total else 0,
        "max_llm_time_ms": max(llm_times) if llm_times else 0,
        "total_cost_usd": round(sum(costs), 6),
        "turns_with_anomalies": sum(1 for c in anomaly_counts if c > 0),
        "anomaly_turns_indices": [
            i for i, c in enumerate(anomaly_counts) if c > 0
        ],
    }
```


### 3.3 Файл: `api/session_store.py` — новый файл

```python
import time
from collections import defaultdict
from threading import Lock


class SessionStore:
    """
    In-memory хранилище трейсов и blob'ов сессии.
    TTL по умолчанию: 30 минут.
    Не использовать в production с горизонтальным масштабированием
    (заменить на Redis при необходимости).
    """
    def __init__(self):
        self._blobs: dict[str, tuple[str, float]] = {}  # {id: (content, expires_at)}
        self._traces: dict[str, list] = defaultdict(list)  # {session_id: [trace_dict]}
        self._lock = Lock()

    def set_blob(self, blob_id: str, content: str, ttl_seconds: int = 1800):
        with self._lock:
            self._blobs[blob_id] = (content, time.time() + ttl_seconds)

    def get_blob(self, blob_id: str) -> str | None:
        with self._lock:
            entry = self._blobs.get(blob_id)
            if entry and entry[^1] > time.time():
                return entry[^0]
            return None

    def append_trace(self, session_id: str, trace_dict: dict):
        with self._lock:
            self._traces[session_id].append(trace_dict)

    def get_session_traces(self, session_id: str) -> list:
        with self._lock:
            return list(self._traces.get(session_id, []))

    def cleanup_expired(self):
        """Вызывать периодически (например, через APScheduler)."""
        now = time.time()
        with self._lock:
            self._blobs = {k: v for k, v in self._blobs.items() if v[^1] > now}
```


***

## 4. АНОМАЛИИ: ПОЛНЫЙ КАТАЛОГ КОДОВ

| Код | Severity | Условие | Target |
| :-- | :-- | :-- | :-- |
| `SD_FALLBACK` | warn | `sd_detail.method == "fallback"` | `sd` |
| `NO_BLOCKS_TO_LLM` | error | `blocks_after_cap == 0` AND `fast_path != true` | `chunks` |
| `SD_FILTER_TOO_STRICT` | warn | `blocks_after_sd == 0` AND `blocks_initial > 0` | `chunks` |
| `SEMANTIC_NOT_TRIGGERED` | info | `semantic_hits == 0` AND `memory_turns > 5` | `memory` |
| `UNEXPECTED_FAST_PATH` | warn | `fast_path == true` AND query tokens > 15 | `sd` |
| `SLOW_STAGE` | warn | Любой stage > 50% total_duration | `timeline` |
| `CONTEXT_BLOAT_RISK` | warn | `len(hybrid_query_preview) > MAX_CONTEXT_SIZE * 0.9` | `chunks` |
| `PIPELINE_EXCEPTION` | error | `pipeline_error != null` | `error` |
| `SD_LOW_CONFIDENCE` | info | `sd_detail.confidence < sd_confidence_threshold` | `sd` |
| `EMPTY_MEMORY` | info | `memory_turns == 0` AND `turn_number > 3` | `memory` |


***

## 5. ФРОНТЕНД: КОМПОНЕНТЫ

### 5.1 `StatusBar.tsx` — L0, всегда видим

```tsx
// web_ui/src/components/debug/StatusBar.tsx

interface StatusBarProps {
  trace: InlineTrace;  // существующий тип + V206 extension
}

export const StatusBar: React.FC<StatusBarProps> = ({ trace }) => {
  const anomalyCount = trace.anomalies?.length ?? 0;
  const hasError = trace.pipeline_error != null;

  const chips = [
    trace.fast_path && { label: '⚡ FAST PATH', color: 'amber', anchor: 'routing' },
    { label: `MODE: ${trace.mode ?? '—'}`, color: 'slate', anchor: 'routing' },
    { label: `STATE: ${trace.user_state ?? '—'}`, color: 'violet', anchor: 'memory' },
    { label: `SD: ${trace.sd_level ?? '—'} · ${trace.sd_detail?.confidence?.toFixed(2) ?? '—'}`,
      color: sdColor(trace.sd_level), anchor: 'sd' },
    { label: `CHUNKS: ${trace.blocks_after_cap ?? trace.chunks_retrieved ?? '—'} / cap ${trace.block_cap ?? '—'}`,
      color: 'sky', anchor: 'chunks' },
    { label: `HITS: ${trace.semantic_hits ?? 0}`, color: 'teal', anchor: 'memory' },
    { label: `LLM: ${trace.total_duration_ms ? `${trace.total_duration_ms}ms` : '—'}`,
      color: 'slate', anchor: 'llm' },
    anomalyCount > 0 && {
      label: `⚠️ ${anomalyCount}`,
      color: hasError ? 'red' : 'orange',
      anchor: 'anomalies'
    },
  ].filter(Boolean);

  return (
    <div className="flex flex-wrap gap-1.5 px-3 py-2 bg-slate-50 dark:bg-slate-900
                    border-b border-slate-200 dark:border-slate-700 rounded-t-lg">
      {chips.map((chip, i) => (
        <a key={i} href={`#debug-${chip.anchor}`}
           className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full
                       cursor-pointer hover:opacity-80 transition-opacity
                       ${chipColors[chip.color]}`}>
          {chip.label}
        </a>
      ))}
    </div>
  );
};

const chipColors: Record<string, string> = {
  amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  violet: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300',
  sky: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
  teal: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300',
  red: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  orange: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  green: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

function sdColor(level?: string | null) {
  return level === 'GREEN' ? 'green' : level === 'YELLOW' ? 'amber' : level === 'RED' ? 'red' : 'slate';
}
```


### 5.2 `PipelineFunnel.tsx` — воронка чанков

```tsx
// web_ui/src/components/debug/PipelineFunnel.tsx

interface FunnelStage {
  label: string;
  count: number;
  color: string;
}

export const PipelineFunnel: React.FC<{ trace: InlineTrace }> = ({ trace }) => {
  const stages: FunnelStage[] = [
    { label: 'Initial', count: trace.blocks_initial ?? 0, color: 'bg-sky-400' },
    { label: 'After SD', count: trace.blocks_after_sd ?? 0, color: 'bg-violet-400' },
    { label: 'After Stage', count: trace.blocks_after_stage ?? 0, color: 'bg-amber-400' },
    { label: 'To LLM', count: trace.blocks_after_cap ?? 0, color: 'bg-emerald-400' },
  ].filter(s => s.count != null);

  const max = Math.max(...stages.map(s => s.count), 1);

  return (
    <div className="mt-2 space-y-1">
      {stages.map((stage) => (
        <div key={stage.label} className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 w-20 shrink-0">{stage.label}</span>
          <div className="flex-1 h-2.5 rounded bg-slate-100 dark:bg-slate-700 overflow-hidden">
            <div className={`h-2.5 rounded ${stage.color} transition-all`}
                 style={{ width: `${(stage.count / max) * 100}%` }} />
          </div>
          <span className="text-[11px] font-mono font-bold text-slate-600
                           dark:text-slate-300 w-6 text-right">{stage.count}</span>
        </div>
      ))}
      {trace.hybrid_query_preview && (
        <details className="mt-1">
          <summary className="cursor-pointer text-[10px] text-slate-400 select-none py-0.5">
            Hybrid query preview →
          </summary>
          <p className="mt-1 text-[10px] font-mono text-slate-500 dark:text-slate-400
                        bg-slate-50 dark:bg-slate-900 rounded p-2 border
                        border-slate-200 dark:border-slate-700 whitespace-pre-wrap">
            {trace.hybrid_query_preview}
          </p>
        </details>
      )}
    </div>
  );
};
```


### 5.3 `useDebugBlob.ts` — хук для on-demand загрузки

```typescript
// web_ui/src/hooks/useDebugBlob.ts

import { useState, useCallback } from 'react';

export function useDebugBlob() {
  const [blobs, setBlobs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const fetchBlob = useCallback(async (blobId: string) => {
    if (blobs[blobId] || loading[blobId]) return;
    setLoading(prev => ({ ...prev, [blobId]: true }));
    try {
      const res = await fetch(`/api/debug/blob/${blobId}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Blob not found');
      const data = await res.json();
      setBlobs(prev => ({ ...prev, [blobId]: data.content }));
    } catch (e) {
      setBlobs(prev => ({ ...prev, [blobId]: '[Ошибка загрузки]' }));
    } finally {
      setLoading(prev => ({ ...prev, [blobId]: false }));
    }
  }, [blobs, loading]);

  return { blobs, loading, fetchBlob };
}
```


### 5.4 `SessionDashboard.tsx` — L3, агрегированные метрики

```tsx
// web_ui/src/components/debug/SessionDashboard.tsx

export const SessionDashboard: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);

  useEffect(() => {
    fetch(`/api/debug/session/${sessionId}/metrics`, { credentials: 'include' })
      .then(r => r.json())
      .then(setMetrics);
  }, [sessionId]);

  if (!metrics) return null;

  return (
    <details>
      <summary className="cursor-pointer font-semibold text-slate-600
                           dark:text-slate-400 py-1 select-none">
        📊 Session Dashboard
      </summary>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {/* Total turns */}
        <MetricCard label="Turns" value={metrics.total_turns} />
        {/* Fast path % */}
        <MetricCard label="Fast Path" value={`${metrics.fast_path_pct}%`} />
        {/* Avg LLM time */}
        <MetricCard label="Avg LLM" value={`${metrics.avg_llm_time_ms}ms`} />
        {/* Total cost */}
        <MetricCard label="Стоимость" value={`$${metrics.total_cost_usd}`}
                    highlight={metrics.total_cost_usd > 0.1} />
        {/* SD distribution */}
        <div className="col-span-2 rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">SD уровни</p>
          <div className="flex gap-2">
            <SDChip level="GREEN" count={metrics.sd_distribution.GREEN} />
            <SDChip level="YELLOW" count={metrics.sd_distribution.YELLOW} />
            <SDChip level="RED" count={metrics.sd_distribution.RED} />
          </div>
        </div>
        {/* Turns with anomalies */}
        {metrics.turns_with_anomalies > 0 && (
          <MetricCard
            label="⚠️ Turn'ы с аномалиями"
            value={metrics.turns_with_anomalies}
            highlight
          />
        )}
      </div>
    </details>
  );
};
```


### 5.5 `ErrorView.tsx` — отображение ошибок пайплайна

```tsx
// web_ui/src/components/debug/ErrorView.tsx

export const ErrorView: React.FC<{ error: PipelineError }> = ({ error }) => (
  <div className="rounded-lg border border-red-300 dark:border-red-700
                  bg-red-50 dark:bg-red-900/20 px-4 py-3 mt-2">
    <div className="flex items-center gap-2 mb-2">
      <span className="text-red-600 dark:text-red-400 font-bold text-xs uppercase">
        ❌ Pipeline Error
      </span>
      <code className="text-[10px] font-mono bg-red-100 dark:bg-red-900/40
                       text-red-700 dark:text-red-300 px-1.5 py-0.5 rounded">
        {error.stage}
      </code>
    </div>
    <p className="text-[11px] text-red-800 dark:text-red-300 font-mono mb-1">
      {error.exception_type}: {error.message}
    </p>
    {error.partial_trace_available && (
      <p className="text-[10px] text-red-500 dark:text-red-400">
        ℹ️ Частичный трейс доступен — данные до точки сбоя показаны выше
      </p>
    )}
  </div>
);
```


### 5.6 Export кнопка (добавить в `InlineDebugTrace.tsx`)

```tsx
// Добавить в конец InlineDebugTrace компонента, перед закрывающим тегом

<div className="flex justify-end px-3 pb-2">
  <button
    onClick={() => {
      const json = JSON.stringify(trace, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trace_turn${trace.turn_number ?? 'N'}_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }}
    className="text-[10px] text-slate-400 hover:text-slate-600
               dark:hover:text-slate-200 transition-colors select-none"
  >
    ⬇ Export trace JSON
  </button>
</div>
```


***

## 6. ИТОГОВАЯ СТРУКТУРА ПАНЕЛИ (финальная)

```
InlineDebugTrace [debug mode only]
│
├── [L0] ──────────── StatusBar (чипы-якоря + ⚠️N) ─────────── всегда видим
│
├── [L1] id="debug-error" ──── ErrorView (если pipeline_error) ← ERROR FIRST
│
├── [L1] id="debug-routing" ── Роутинг и SD
│     ├── карточки: mode / rule / confidence / state / SD     ✅
│     ├── fast_path chip + reason                             ← НОВОЕ
│     ├── block_cap + blocks funnel preview                   ← НОВОЕ
│     └── <details> SD Classification Detail                  ← v2.0.4
│
├── [L2] id="debug-chunks" ─── Чанки
│     ├── PipelineFunnel (initial→sd→stage→cap)               ← НОВОЕ
│     └── hybrid_query_preview                                ← НОВОЕ
│
├── [L2] id="debug-llm" ────── LLM Calls                      ✅ v2.0.3
│     ├── preview + duration + tokens                         ✅
│     └── "Full prompt →" (useDebugBlob → blob endpoint)      ← v2.0.4 (исправлено)
│
├── [L2] id="debug-cost" ───── Модели + Токены + Cost ($)      ✅ + НОВОЕ
│
├── [L2] id="debug-timeline" ─ Pipeline Timeline               ← v2.0.4
│
├── [L2] id="debug-memory" ─── Контекст памяти
│     ├── числа: turns / summary_length / hits                ✅
│     ├── <details> Turns content (text previews)             ← v2.0.4
│     ├── <details> Summary text                              ← v2.0.4
│     ├── <details> Semantic hits detail                      ← v2.0.4
│     ├── <details> Записано в память (context_written)       ← v2.0.4
│     └── State trajectory (mini-bar последних N turn'ов)     ← v2.0.5
│
├── [L2] id="debug-anomalies" ─ Anomalies                      ← v2.0.5
│     └── список AnomalyFlag с jump-to якорями
│
├── [L3] id="debug-session" ── Session Dashboard               ← НОВОЕ
│
├── [L3] id="debug-history" ── Trace History (список turn'ов)  ← НОВОЕ
│
├── [L3] id="debug-config" ─── Config Snapshot                 ← НОВОЕ
│
└── ─────────────────── [⬇ Export trace JSON] ──────────────── ← НОВОЕ
```


***

## 7. ТЕСТИРОВАНИЕ

### 7.1 Функциональные тесты

- [ ] **L0 StatusBar**: появляется в debug режиме со всеми чипами; каждый чип-якорь скроллит к нужной секции
- [ ] **ErrorView**: при искусственном exception в `answer_adaptive.py` — показывается красный блок с `stage` и `message`
- [ ] **Fast Path**: `fast_path=true` отображается в StatusBar и в Routing; объясняет отсутствие chunks
- [ ] **PipelineFunnel**: воронка показывает все 4 стадии; при `blocks_after_sd=0` виден "обрыв"
- [ ] **Hybrid query preview**: отличается от исходного `user_message` (т.к. собирается HybridQueryBuilder'ом)
- [ ] **SD Classification Detail**: `method`, `indicator`, `confidence`, `allowed_levels` отображаются
- [ ] **Pipeline Timeline**: полоски пропорциональны; самая долгая > 50% — красная
- [ ] **Memory turns**: читаются из `memory.turns` (объекты), поле `state` не пустое
- [ ] **State trajectory**: мини-строка показывает последние N состояний после 3+ сообщений
- [ ] **Anomaly engine**: `SD_FALLBACK` генерируется при method=fallback; `NO_BLOCKS_TO_LLM` при 0 блоках
- [ ] **Full prompt blob**: кнопка "Full prompt →" делает fetch на `/api/debug/blob/{id}`; текст появляется по клику, не при загрузке
- [ ] **Cost estimator**: поле `estimated_cost_usd` > 0 после LLM вызова; отображается в секции токенов
- [ ] **Session Dashboard**: после 3+ сообщений показывает `total_turns`, `fast_path_pct`, `sd_distribution`
- [ ] **Export JSON**: скачивается файл `trace_turnN_*.json` с полным trace объектом
- [ ] **Config Snapshot**: отображает значения из `config.py` которые были актуальны на момент запроса
- [ ] **PII sanitization**: email и телефон в blob-контенте заменяются на `[email]` / `[phone]`


### 7.2 Нагрузочные тесты

- [ ] Payload ответа в debug режиме (L0–L2, без blob'ов) вырос не более чем на **15 KB** относительно v2.0.3
- [ ] Blob не включён в основной ответ API — проверить Network tab в DevTools
- [ ] `SessionStore.cleanup_expired()` освобождает память при TTL истечении


### 7.3 Регрессионные тесты

- [ ] **Обычный (user) режим**: панель полностью скрыта, никакие debug-поля не попадают в ответ
- [ ] Существующие секции (LLM Calls, Models, Tokens) работают без изменений
- [ ] `npm run lint` — 0 ошибок
- [ ] `npm run build` — успешная сборка без warnings

***

## 8. DEFINITION OF DONE (v2.0.6)

### Backend

- [ ] `DebugTraceV206Extension` добавлен в Pydantic-схемы без нарушения существующих полей
- [ ] `context_written` используется существующее — `context_written_to_memory` **не создан**
- [ ] `system_prompt_blob_id` / `user_prompt_blob_id` — полные тексты только через blob endpoint
- [ ] `state_trajectory` читает из `memory.turns` (объекты), не из `get_last_turns()` dict
- [ ] Anomaly engine вызывается в конце каждого пайплайна и пишет в `trace.anomalies`
- [ ] `ConfigSnapshot` заполняется из реальных значений `config.py`
- [ ] `estimated_cost_usd` вычисляется на бэкенде по токенам LLM calls
- [ ] `pipeline_error` заполняется при exception, пайплайн не падает (graceful degradation)
- [ ] `/api/debug/blob/{id}` и `/api/debug/session/{id}/metrics` реализованы и защищены
- [ ] `SessionStore` сохраняет трейсы с TTL 30 минут; `cleanup_expired()` вызывается


### Frontend

- [ ] Все TypeScript-интерфейсы добавлены в `chat.types.ts`
- [ ] `StatusBar.tsx` реализован с якорями на все секции
- [ ] `PipelineFunnel.tsx` отображает воронку blocks
- [ ] `AnomalyList` компонент реализован с jump-to навигацией
- [ ] `useDebugBlob.ts` хук реализован — промпты загружаются только по клику
- [ ] `SessionDashboard.tsx` показывает агрегированные метрики сессии
- [ ] `ErrorView.tsx` отображается первым при `pipeline_error != null`
- [ ] Export trace JSON кнопка работает
- [ ] `ConfigSnapshot` секция отображает конфигурацию
- [ ] Auto-раскрытие anomalies при `anomalies.length > 0`, остальное свёрнуто
- [ ] Обычный (user) режим: панель не отображается, регрессия не нарушена

***

## 9. ПРИОРИТИЗАЦИЯ ДЛЯ IDE АГЕНТА

Реализовывать строго в этом порядке:


| \# | Задача | Сложность | Ценность |
| :-- | :-- | :-- | :-- |
| 1 | Data contract: Pydantic + TS типы | S | Разблокирует всё остальное |
| 2 | Backend: `answer_adaptive.py` — pipeline_stages, fast_path, counts, anomalies | M | Ядро системы |
| 3 | Backend: memory turns + trajectory (из объектов, не dict) | M | Критично для отладки памяти |
| 4 | Backend: blob store + endpoints | M | Разблокирует full prompts |
| 5 | Frontend: StatusBar L0 | S | Мгновенная ценность |
| 6 | Frontend: PipelineFunnel + SD detail + Timeline | M | Визуализация pipeline |
| 7 | Frontend: AnomalyList с jump-to | S | Быстрая навигация |
| 8 | Frontend: ErrorView | S | Safety net |
| 9 | Frontend: Full prompt via useDebugBlob | S | Заменяет старый inline подход |
| 10 | Frontend: Cost estimator | XS | Быстрая победа |
| 11 | Backend + Frontend: Session Dashboard | L | Сессионный контекст |
| 12 | Frontend: Export JSON | XS | Быстрая победа |
| 13 | Frontend: Config Snapshot | XS | Быстрая победа |
| 14 | PII sanitization в blob endpoint | S | Безопасность |


