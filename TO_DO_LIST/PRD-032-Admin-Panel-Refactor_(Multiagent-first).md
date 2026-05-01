
# PRD-032: Admin Panel — Refactor для Эпохи 4 (Multiagent-first)

**Версия:** 1.0 | **Тип:** Major Refactor + Feature
**Предшественник:** PRD-031 (коммит f696a2e), PRD-031-patch (коммит 86029c5)
**Базовый коммит:** `86029c5cf38ea3ce8fac705113fb1b3b996cacf8`
**Статус:** 📋 Ready for implementation

***

## 1. Контекст и мотивация

Проект находится в **Эпохе 4**: мультиагентная система (`MULTIAGENT_ENABLED=on`) запущена параллельно старой каскадной с переключёнными флагами. Текущая Admin Panel унаследовала 7 вкладок из Эпох 1–3 (LLM, Retrieval, Diagnostics, Routing, Memory, Runtime, Compatibility) — все они управляют параметрами **каскадного** пайплайна, который больше не является основным. Новые вкладки (Агенты, Оркестратор, Треды) добавлены **поверх** старых, не заменяя их.

**Результат:** разработчик видит 11 вкладок, не понимает что активно прямо сейчас, не может быстро найти промпты агентов, метрики агентов пусты, а `Prompts` показывает `prompt_registry_v2` вместо промптов агентов.

***

## 2. Цели PRD-032

1. Сделать Admin Panel **multiagent-first**: главный экран — состояние мультиагентной системы
2. Подключить **`AgentPromptEditorPanel`** в отдельную вкладку "Агент-промпты"
3. Запустить **запись метрик** в `orchestrator.py` → данные в `AgentsTab` перестают быть нулями
4. Синхронизировать **`OrchestratorTab`** с реальными feature flags (`MULTIAGENT_ENABLED`)
5. Убрать legacy-вкладки в коллапс **"Устаревшее (Epoch 1–3)"**
6. Добавить **Dashboard-вкладку "Обзор"** как первый экран

***

## 3. Scope — что меняется, что не трогаем

### ✅ В скоупе

| Файл | Действие |
| :-- | :-- |
| `AdminPanel.tsx` | Рефакторинг TABS, новый таб `overview`, collapse legacy-табов, индикатор режима |
| `orchestrator.py` | Добавить вызов `POST /api/admin/agents/metrics/record` после каждого агента |
| `admin_routes.py` | Новый endpoint `GET /api/admin/overview` |
| `OrchestratorTab.tsx` | Синхронизация активного режима с `feature_flags.MULTIAGENT_ENABLED` |
| `adminConfig.service.ts` | Добавить `getOverview()` |
| `admin.types.ts` | Добавить `OverviewData`, `AgentMetricRecord` |
| `AdminOverviewTab.tsx` | **СОЗДАТЬ** — новый dashboard-компонент |
| Новая вкладка "Агент-промпты" | Переключить `Prompts` → `PromptEditorPanel` (legacy) + новая вкладка для `AgentPromptEditorPanel` |

### ❌ Не трогаем

- `AgentsTab.tsx`, `ThreadsTab.tsx`, `AgentPromptEditorPanel.tsx`, `useAgentStatus.ts`, `useOrchestrator.ts`, `useThreads.ts`, `useAgentPrompts.ts` — уже рабочие
- `PromptEditorPanel.tsx` — остаётся, переезжает в legacy-секцию
- Backend агентных routes (`admin_routes.py` — только добавление endpoint, без правки существующих)
- Все тесты из PRD-031

***

## 4. Архитектура изменений

### 4.1 Новая структура вкладок

```
БЫЛО (11 вкладок, порядок хаотичный):
LLM | Retrieval | Diagnostics | Routing | Память | Prompts | Runtime | [Compatibility] | Агенты | Оркестратор | Треды

СТАЛО (7 видимых + legacy-коллапс):
[⭐ Обзор] | [🤖 Агенты] | [🎭 Оркестратор] | [🧵 Треды] | [✏️ Агент-промпты] | [⚙️ Runtime] | [🧠 Память]
                                                                    ↓ details/summary
                                               [Устаревшее ▼] → LLM | Retrieval | Diagnostics | Routing | Prompts | Compatibility
```


### 4.2 Индикатор режима в шапке

Рядом с кнопкой API-ключа добавить badge:

- `⚡ multiagent_v1` (зелёный) — когда `MULTIAGENT_ENABLED=on`
- `⚠️ legacy mode` (жёлтый) — когда `LEGACY_PIPELINE_ENABLED=on && MULTIAGENT_ENABLED=off`
- `🔀 hybrid` (синий) — когда оба активны

***

## 5. Детальные задачи


***

### TASK-1: Backend — endpoint `/api/admin/overview`

**Файл:** `bot_psychologist/api/admin_routes.py`

**Добавить** новый route (не изменяя существующих):

```python
@router.get("/overview")
async def get_admin_overview(
    _user=Depends(require_dev_access),
    orchestrator=Depends(get_orchestrator),
    config_service=Depends(get_config_service),
):
    """Dashboard overview: активный режим, статус агентов, последние трейсы."""
    import os
    from datetime import datetime, timezone

    feature_flags = {
        "MULTIAGENT_ENABLED": os.getenv("MULTIAGENT_ENABLED", "off") == "on",
        "LEGACY_PIPELINE_ENABLED": os.getenv("LEGACY_PIPELINE_ENABLED", "off") == "on",
        "NEO_MINDBOT_ENABLED": os.getenv("NEO_MINDBOT_ENABLED", "off") == "on",
    }

    # Определяем активный режим
    if feature_flags["MULTIAGENT_ENABLED"] and not feature_flags["LEGACY_PIPELINE_ENABLED"]:
        pipeline_mode = "full_multiagent"
    elif feature_flags["MULTIAGENT_ENABLED"] and feature_flags["LEGACY_PIPELINE_ENABLED"]:
        pipeline_mode = "hybrid"
    else:
        pipeline_mode = "legacy"

    # Статус агентов из orchestrator
    agents_status = []
    if hasattr(orchestrator, "agent_registry"):
        for agent_id, agent in orchestrator.agent_registry.items():
            metrics = getattr(orchestrator, "_agent_metrics", {}).get(agent_id, {})
            agents_status.append({
                "agent_id": agent_id,
                "enabled": getattr(agent, "enabled", True),
                "calls": metrics.get("calls", 0),
                "errors": metrics.get("errors", 0),
                "avg_ms": metrics.get("avg_ms", 0),
                "last_run": metrics.get("last_run"),
            })

    # Последние 5 трейсов
    recent_traces = []
    if hasattr(orchestrator, "_agent_traces"):
        recent_traces = sorted(
            orchestrator._agent_traces[-5:],
            key=lambda t: t.get("ts", ""),
            reverse=True,
        )

    return {
        "pipeline_mode": pipeline_mode,
        "feature_flags": feature_flags,
        "agents": agents_status,
        "recent_traces": recent_traces,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "schema_version": config_service.get_schema_version() if hasattr(config_service, "get_schema_version") else "n/a",
    }
```


***

### TASK-2: Backend — запись метрик в `orchestrator.py`

**Файл:** `bot_psychologist/orchestrator.py` (или аналогичный файл с классом orchestrator)

Найти метод вызова агентов (обычно `async def run_agent(...)` или внутри `async def process(...)`). Добавить замер времени и запись:

```python
# В начале файла добавить импорт
import time

# Инициализация хранилища метрик в __init__:
self._agent_metrics: dict[str, dict] = {}
self._agent_traces: list[dict] = []

# Обёртка вызова каждого агента — добавить вокруг существующего вызова:
async def _run_agent_with_metrics(self, agent_id: str, agent, *args, **kwargs):
    """Обёртка: замер времени + запись метрик после каждого агента."""
    if agent_id not in self._agent_metrics:
        self._agent_metrics[agent_id] = {
            "calls": 0, "errors": 0, "total_ms": 0, "avg_ms": 0, "last_run": None
        }
    
    t_start = time.monotonic()
    error_occurred = False
    result = None
    
    try:
        result = await agent.run(*args, **kwargs)
    except Exception as e:
        error_occurred = True
        self._agent_metrics[agent_id]["errors"] += 1
        raise
    finally:
        elapsed_ms = round((time.monotonic() - t_start) * 1000)
        m = self._agent_metrics[agent_id]
        m["calls"] += 1
        m["total_ms"] += elapsed_ms
        m["avg_ms"] = round(m["total_ms"] / m["calls"])
        m["last_run"] = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
        
        # Пишем трейс (храним последние 100)
        trace_entry = {
            "ts": m["last_run"],
            "agent_id": agent_id,
            "duration_ms": elapsed_ms,
            "error": error_occurred,
        }
        self._agent_traces.append(trace_entry)
        if len(self._agent_traces) > 100:
            self._agent_traces = self._agent_traces[-100:]
    
    return result
```

**Важно:** найти все места где вызываются агенты вида `await agent.run(...)` или `await self.writer_agent.run(...)` и заменить на `await self._run_agent_with_metrics("agent_id", agent, ...)`.

***

### TASK-3: Backend — синхронизация `OrchestratorConfig` с env-флагами

**Файл:** `bot_psychologist/api/admin_routes.py`

В существующем endpoint `GET /api/admin/orchestrator/config` добавить поле `actual_pipeline_mode` из env (не из DB-override):

```python
# В существующем обработчике get_orchestrator_config добавить:
import os
actual_mode = "full_multiagent" if os.getenv("MULTIAGENT_ENABLED","off")=="on" else "legacy"
# Добавить в ответ:
response_data["actual_pipeline_mode"] = actual_mode
response_data["env_flags"] = {
    "MULTIAGENT_ENABLED": os.getenv("MULTIAGENT_ENABLED", "off"),
    "LEGACY_PIPELINE_ENABLED": os.getenv("LEGACY_PIPELINE_ENABLED", "off"),
}
```


***

### TASK-4: Frontend — `admin.types.ts` — новые типы

**Файл:** `bot_psychologist/web_ui/src/types/admin.types.ts`

Добавить в конец файла (не изменяя существующих типов):

```typescript
// ── PRD-032: Overview Dashboard ──────────────────────────────────────────────

export type PipelineMode = 'full_multiagent' | 'hybrid' | 'legacy';

export interface AgentOverviewStatus {
  agent_id: string;
  enabled: boolean;
  calls: number;
  errors: number;
  avg_ms: number;
  last_run: string | null;
}

export interface RecentTrace {
  ts: string;
  agent_id: string;
  duration_ms: number;
  error: boolean;
}

export interface OverviewData {
  pipeline_mode: PipelineMode;
  feature_flags: Record<string, boolean>;
  agents: AgentOverviewStatus[];
  recent_traces: RecentTrace[];
  server_time: string;
  schema_version: string;
}

// ── PRD-032: OrchestratorConfig extended ─────────────────────────────────────
export interface OrchestratorConfigExtended extends OrchestratorConfig {
  actual_pipeline_mode?: PipelineMode;
  env_flags?: Record<string, string>;
}
```


***

### TASK-5: Frontend — `adminConfig.service.ts` — метод `getOverview`

**Файл:** `bot_psychologist/web_ui/src/services/adminConfig.service.ts`

Добавить метод в класс `AdminConfigService`:

```typescript
async getOverview(): Promise<OverviewData> {
  const res = await this.get<OverviewData>('/admin/overview');
  return res;
}
```


***

### TASK-6: Frontend — `AdminOverviewTab.tsx` — СОЗДАТЬ

**Файл:** `bot_psychologist/web_ui/src/components/admin/AdminOverviewTab.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { adminConfigService } from '../../services/adminConfig.service';
import type { OverviewData, PipelineMode } from '../../types/admin.types';

const MODE_BADGE: Record<PipelineMode, { label: string; classes: string }> = {
  full_multiagent: {
    label: '⚡ full_multiagent',
    classes: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  },
  hybrid: {
    label: '🔀 hybrid',
    classes: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  },
  legacy: {
    label: '⚠️ legacy',
    classes: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  },
};

export const AdminOverviewTab: React.FC = () => {
  const [data, setData] = useState<OverviewData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await adminConfigService.getOverview();
      setData(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (isLoading) return <div className="text-slate-400 py-8 text-center text-sm">Загрузка...</div>;
  if (error) return <div className="text-red-500 py-8 text-center text-sm">Ошибка: {error}</div>;
  if (!data) return null;

  const badge = MODE_BADGE[data.pipeline_mode];

  return (
    <div className="mt-4 space-y-4">
      {/* Pipeline mode */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-md p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-800">Активный пайплайн</h3>
          <button onClick={load} className="text-xs text-slate-400 hover:text-slate-600">
            🔄 Обновить
          </button>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1.5 rounded-full text-sm font-medium border ${badge.classes}`}>
            {badge.label}
          </span>
          <span className="text-sm text-slate-500">schema: {data.schema_version}</span>
          <span className="text-sm text-slate-500 ml-auto">
            {new Date(data.server_time).toLocaleTimeString('ru-RU')}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(data.feature_flags).map(([flag, enabled]) => (
            <span
              key={flag}
              className={`text-xs px-2 py-0.5 rounded border font-mono ${
                enabled
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-500 border-slate-200'
              }`}
            >
              {flag}={enabled ? 'on' : 'off'}
            </span>
          ))}
        </div>
      </div>

      {/* Agents grid */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-md p-5">
        <h3 className="font-semibold text-slate-800 mb-3">Агенты</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {data.agents.map((agent) => (
            <div
              key={agent.agent_id}
              className="rounded-lg border border-slate-200 p-3 space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">{agent.agent_id}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                  agent.enabled
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-red-100 text-red-600'
                }`}>
                  {agent.enabled ? 'enabled' : 'disabled'}
                </span>
              </div>
              <div className="text-xs text-slate-500 grid grid-cols-2 gap-x-2">
                <span>calls: <b className="text-slate-700">{agent.calls}</b></span>
                <span>avg: <b className="text-slate-700">{agent.avg_ms}ms</b></span>
                <span>errors: <b className={agent.errors > 0 ? 'text-red-600' : 'text-slate-700'}>{agent.errors}</b></span>
                <span>last: <b className="text-slate-700">
                  {agent.last_run
                    ? new Date(agent.last_run).toLocaleTimeString('ru-RU')
                    : '—'}
                </b></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent traces */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-md p-5">
        <h3 className="font-semibold text-slate-800 mb-3">Последние трейсы агентов</h3>
        {data.recent_traces.length === 0 ? (
          <p className="text-sm text-slate-400">Трейсов ещё нет — запросы не отправлялись.</p>
        ) : (
          <table className="w-full text-xs text-slate-600">
            <thead>
              <tr className="text-left border-b border-slate-100">
                <th className="pb-1 font-medium text-slate-500">Время</th>
                <th className="pb-1 font-medium text-slate-500">Агент</th>
                <th className="pb-1 font-medium text-slate-500">ms</th>
                <th className="pb-1 font-medium text-slate-500">Статус</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_traces.map((trace, i) => (
                <tr key={i} className="border-b border-slate-50">
                  <td className="py-1">{new Date(trace.ts).toLocaleTimeString('ru-RU')}</td>
                  <td className="py-1 font-mono">{trace.agent_id}</td>
                  <td className="py-1">{trace.duration_ms}</td>
                  <td className="py-1">
                    {trace.error
                      ? <span className="text-red-500">❌ error</span>
                      : <span className="text-emerald-600">✓ ok</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
```


***

### TASK-7: Frontend — `OrchestratorTab.tsx` — синхронизация с env

**Файл:** `bot_psychologist/web_ui/src/components/admin/OrchestratorTab.tsx`

Добавить отображение `actual_pipeline_mode` (реального из env) отдельно от UI-переключателя:

```typescript
// Добавить в JSX под заголовком "Оркестратор", перед кнопками режима:
{orchestratorConfig?.actual_pipeline_mode && (
  <div className="mb-3 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded px-3 py-2">
    <span className="font-medium">Реальный режим (env):</span>{' '}
    <span className={`font-mono font-semibold ${
      orchestratorConfig.actual_pipeline_mode === 'full_multiagent'
        ? 'text-emerald-600'
        : orchestratorConfig.actual_pipeline_mode === 'hybrid'
        ? 'text-blue-600'
        : 'text-amber-600'
    }`}>
      {orchestratorConfig.actual_pipeline_mode}
    </span>
    {orchestratorConfig.env_flags && (
      <span className="ml-2 text-slate-400">
        (MULTIAGENT={orchestratorConfig.env_flags.MULTIAGENT_ENABLED},
        LEGACY={orchestratorConfig.env_flags.LEGACY_PIPELINE_ENABLED})
      </span>
    )}
  </div>
)}
```


***

### TASK-8: Frontend — `AdminPanel.tsx` — рефакторинг TABS + шапка

**Файл:** `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`

**Шаг 8.1 — Новый TABS-массив:**

```typescript
// Заменить существующий TABS и тип Tab на:
type Tab =
  | 'overview'
  | 'agents'
  | 'orchestrator'
  | 'threads'
  | 'agent_prompts'
  | 'runtime'
  | 'memory'
  // legacy (hidden by default):
  | 'llm'
  | 'retrieval'
  | 'diagnostics'
  | 'routing'
  | 'prompts'
  | 'compatibility';

const MULTIAGENT_TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'overview',      label: '⭐ Обзор',         hoverColor: 'hover:bg-emerald-500/20' },
  { key: 'agents',        label: '🤖 Агенты',         hoverColor: 'hover:bg-purple-500/20'  },
  { key: 'orchestrator',  label: '🎭 Оркестратор',    hoverColor: 'hover:bg-indigo-500/20'  },
  { key: 'threads',       label: '🧵 Треды',           hoverColor: 'hover:bg-teal-500/20'    },
  { key: 'agent_prompts', label: '✏️ Агент-промпты',  hoverColor: 'hover:bg-rose-500/20'    },
  { key: 'runtime',       label: '⚙️ Runtime',        hoverColor: 'hover:bg-slate-500/20'   },
  { key: 'memory',        label: '🧠 Память',          hoverColor: 'hover:bg-emerald-500/20' },
];

const LEGACY_TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'llm',           label: '🤖 LLM',            hoverColor: 'hover:bg-violet-500/20'  },
  { key: 'retrieval',     label: '🔍 Retrieval',       hoverColor: 'hover:bg-blue-500/20'    },
  { key: 'diagnostics',   label: '🩺 Diagnostics',     hoverColor: 'hover:bg-teal-500/20'    },
  { key: 'routing',       label: '🧭 Routing',         hoverColor: 'hover:bg-cyan-500/20'    },
  { key: 'prompts',       label: '🧩 Prompts (legacy)',hoverColor: 'hover:bg-rose-500/20'    },
  { key: 'compatibility', label: '🧰 Compatibility',   hoverColor: 'hover:bg-amber-500/20'   },
];
```

**Шаг 8.2 — Импорты:**

```typescript
// Добавить в импорты:
import { AdminOverviewTab } from './AdminOverviewTab';
import { AgentPromptEditorPanel } from './AgentPromptEditorPanel';
```

**Шаг 8.3 — Шапка: индикатор режима**

В JSX шапки, рядом с полем API-ключа добавить `PipelineBadge`:

```typescript
// Добавить state в компонент:
const [pipelineMode, setPipelineMode] = useState<string | null>(null);

// Добавить в useEffect начальной загрузки:
adminConfigService.getOverview()
  .then((d) => setPipelineMode(d.pipeline_mode))
  .catch(() => {});

// В JSX шапки (рядом с API-key input):
{pipelineMode && (
  <span className={`text-xs px-2 py-1 rounded border font-medium ${
    pipelineMode === 'full_multiagent'
      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : pipelineMode === 'hybrid'
      ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  }`}>
    {pipelineMode === 'full_multiagent' ? '⚡ multiagent_v1'
      : pipelineMode === 'hybrid' ? '🔀 hybrid'
      : '⚠️ legacy mode'}
  </span>
)}
```

**Шаг 8.4 — Таб-бар с legacy-коллапсом:**

Заменить блок рендера tabs на:

```typescript
<div className="bg-slate-800 px-6 shadow-md">
  <div className="max-w-6xl mx-auto flex items-center gap-1 flex-wrap py-1">
    {/* Основные вкладки */}
    {MULTIAGENT_TABS.map((tab) => (
      <button
        key={tab.key}
        onClick={() => setActiveTab(tab.key)}
        className={`px-4 py-3 text-sm font-medium border-b-2 transition-all ${
          activeTab === tab.key
            ? 'border-violet-400 text-white bg-white/5'
            : `border-transparent text-slate-400 ${tab.hoverColor} hover:text-white`
        }`}
      >
        {tab.label}
      </button>
    ))}

    {/* Legacy-коллапс */}
    <details className="relative ml-2">
      <summary className="list-none cursor-pointer px-3 py-2 text-xs border border-slate-600 rounded text-slate-500 hover:bg-slate-700 select-none">
        Устаревшее ▾
      </summary>
      <div className="absolute top-full left-0 mt-1 flex flex-col gap-1 bg-slate-900 border border-slate-700 rounded p-2 shadow-xl z-20 min-w-max">
        <p className="text-xs text-slate-500 px-2 pb-1 border-b border-slate-700 mb-1">
          Epoch 1–3 (каскадный пайплайн)
        </p>
        {LEGACY_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-xs rounded text-left transition-all ${
              activeTab === tab.key
                ? 'bg-white/10 text-white'
                : `text-slate-400 ${tab.hoverColor} hover:text-white`
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </details>
  </div>
</div>
```

**Шаг 8.5 — Рендер нового контента:**

В блок `{/* Main content */}` добавить рядом с `{activeTab === 'agents' && <AgentsTab />}`:

```typescript
{activeTab === 'overview'      && <AdminOverviewTab />}
{activeTab === 'agent_prompts' && (
  <div className="mt-4 bg-white rounded-xl border border-slate-200 shadow-md p-5 h-[70vh]">
    <AgentPromptEditorPanel />
  </div>
)}
```


***

## 6. Тесты

### 6.1 Backend-тесты

**Файл:** `bot_psychologist/tests/test_admin_overview.py` — СОЗДАТЬ

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

class TestAdminOverviewEndpoint:
    """GET /api/admin/overview"""

    async def test_overview_returns_pipeline_mode_multiagent(self, client: AsyncClient, dev_headers):
        with patch.dict("os.environ", {"MULTIAGENT_ENABLED": "on", "LEGACY_PIPELINE_ENABLED": "off"}):
            resp = await client.get("/api/admin/overview", headers=dev_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_mode"] == "full_multiagent"

    async def test_overview_returns_pipeline_mode_hybrid(self, client: AsyncClient, dev_headers):
        with patch.dict("os.environ", {"MULTIAGENT_ENABLED": "on", "LEGACY_PIPELINE_ENABLED": "on"}):
            resp = await client.get("/api/admin/overview", headers=dev_headers)
        assert resp.status_code == 200
        assert resp.json()["pipeline_mode"] == "hybrid"

    async def test_overview_returns_pipeline_mode_legacy(self, client: AsyncClient, dev_headers):
        with patch.dict("os.environ", {"MULTIAGENT_ENABLED": "off", "LEGACY_PIPELINE_ENABLED": "on"}):
            resp = await client.get("/api/admin/overview", headers=dev_headers)
        assert resp.status_code == 200
        assert resp.json()["pipeline_mode"] == "legacy"

    async def test_overview_contains_agents_list(self, client: AsyncClient, dev_headers):
        resp = await client.get("/api/admin/overview", headers=dev_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    async def test_overview_contains_recent_traces(self, client: AsyncClient, dev_headers):
        resp = await client.get("/api/admin/overview", headers=dev_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "recent_traces" in data
        assert isinstance(data["recent_traces"], list)

    async def test_overview_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/admin/overview")
        assert resp.status_code in (401, 403)

    async def test_overview_feature_flags_present(self, client: AsyncClient, dev_headers):
        resp = await client.get("/api/admin/overview", headers=dev_headers)
        data = resp.json()
        assert "feature_flags" in data
        assert "MULTIAGENT_ENABLED" in data["feature_flags"]

    async def test_overview_server_time_iso(self, client: AsyncClient, dev_headers):
        resp = await client.get("/api/admin/overview", headers=dev_headers)
        from datetime import datetime
        data = resp.json()
        # должен парситься как ISO datetime
        datetime.fromisoformat(data["server_time"].replace("Z", "+00:00"))
```


### 6.2 Backend-тесты метрик оркестратора

**Файл:** `bot_psychologist/tests/test_orchestrator_metrics.py` — СОЗДАТЬ

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

class TestOrchestratorMetrics:
    """Проверяем, что _run_agent_with_metrics пишет данные в _agent_metrics."""

    async def test_metrics_increment_on_success(self, orchestrator):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value={"result": "ok"})
        
        await orchestrator._run_agent_with_metrics("test_agent", mock_agent)
        
        assert orchestrator._agent_metrics["test_agent"]["calls"] == 1
        assert orchestrator._agent_metrics["test_agent"]["errors"] == 0
        assert orchestrator._agent_metrics["test_agent"]["avg_ms"] >= 0

    async def test_metrics_increment_errors_on_exception(self, orchestrator):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("agent failed"))
        
        with pytest.raises(RuntimeError):
            await orchestrator._run_agent_with_metrics("fail_agent", mock_agent)
        
        assert orchestrator._agent_metrics["fail_agent"]["errors"] == 1
        assert orchestrator._agent_metrics["fail_agent"]["calls"] == 1

    async def test_traces_written(self, orchestrator):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value={})
        
        await orchestrator._run_agent_with_metrics("trace_agent", mock_agent)
        
        assert len(orchestrator._agent_traces) >= 1
        last = orchestrator._agent_traces[-1]
        assert last["agent_id"] == "trace_agent"
        assert "ts" in last
        assert "duration_ms" in last

    async def test_traces_capped_at_100(self, orchestrator):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value={})
        
        for _ in range(110):
            await orchestrator._run_agent_with_metrics("capped_agent", mock_agent)
        
        assert len(orchestrator._agent_traces) == 100

    async def test_avg_ms_calculated_correctly(self, orchestrator):
        import asyncio
        mock_agent = MagicMock()
        
        call_count = 0
        async def mock_run(*a, **kw):
            nonlocal call_count
            call_count += 1
            return {}
        
        mock_agent.run = mock_run
        
        await orchestrator._run_agent_with_metrics("avg_agent", mock_agent)
        await orchestrator._run_agent_with_metrics("avg_agent", mock_agent)
        
        m = orchestrator._agent_metrics["avg_agent"]
        assert m["calls"] == 2
        assert m["avg_ms"] == round(m["total_ms"] / 2)
```


### 6.3 Frontend-тесты

**Файл:** `bot_psychologist/web_ui/src/components/admin/AdminOverviewTab.test.tsx` — СОЗДАТЬ

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AdminOverviewTab } from './AdminOverviewTab';
import { adminConfigService } from '../../services/adminConfig.service';

vi.mock('../../services/adminConfig.service', () => ({
  adminConfigService: { getOverview: vi.fn() },
}));

const mockOverview = {
  pipeline_mode: 'full_multiagent' as const,
  feature_flags: { MULTIAGENT_ENABLED: true, LEGACY_PIPELINE_ENABLED: false },
  agents: [
    { agent_id: 'writer', enabled: true, calls: 42, errors: 1, avg_ms: 230, last_run: '2026-05-01T12:00:00Z' },
    { agent_id: 'state_analyzer', enabled: true, calls: 38, errors: 0, avg_ms: 95, last_run: null },
  ],
  recent_traces: [
    { ts: '2026-05-01T12:01:00Z', agent_id: 'writer', duration_ms: 210, error: false },
  ],
  server_time: '2026-05-01T12:02:00Z',
  schema_version: '10.5.1',
};

describe('AdminOverviewTab', () => {
  beforeEach(() => {
    vi.mocked(adminConfigService.getOverview).mockResolvedValue(mockOverview);
  });

  it('показывает badge full_multiagent', async () => {
    render(<AdminOverviewTab />);
    await waitFor(() => expect(screen.getByText(/full_multiagent/)).toBeInTheDocument());
  });

  it('отображает карточки агентов', async () => {
    render(<AdminOverviewTab />);
    await waitFor(() => {
      expect(screen.getByText('writer')).toBeInTheDocument();
      expect(screen.getByText('state_analyzer')).toBeInTheDocument();
    });
  });

  it('показывает calls и avg_ms для агентов', async () => {
    render(<AdminOverviewTab />);
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument(); // calls writer
      expect(screen.getByText('230ms')).toBeInTheDocument(); // avg writer
    });
  });

  it('показывает трейсы', async () => {
    render(<AdminOverviewTab />);
    await waitFor(() => {
      expect(screen.getByText('✓ ok')).toBeInTheDocument();
      expect(screen.getByText('210')).toBeInTheDocument();
    });
  });

  it('показывает feature flags', async () => {
    render(<AdminOverviewTab />);
    await waitFor(() => {
      expect(screen.getByText(/MULTIAGENT_ENABLED=on/)).toBeInTheDocument();
      expect(screen.getByText(/LEGACY_PIPELINE_ENABLED=off/)).toBeInTheDocument();
    });
  });
});
```


***

## 7. Порядок выполнения (чеклист агента)

```
── BACKEND ──────────────────────────────────────────────────────────────
[ ] TASK-1  admin_routes.py: добавить GET /api/admin/overview
[ ] TASK-2  orchestrator.py: добавить _run_agent_with_metrics + _agent_metrics + _agent_traces
[ ] TASK-3  admin_routes.py: дополнить GET /orchestrator/config полями actual_pipeline_mode, env_flags
[ ] CHECK   pytest -q tests/test_admin_overview.py → 8 passed
[ ] CHECK   pytest -q tests/test_orchestrator_metrics.py → 5 passed

── FRONTEND TYPES/SERVICE ───────────────────────────────────────────────
[ ] TASK-4  admin.types.ts: добавить OverviewData, AgentOverviewStatus, RecentTrace, PipelineMode
[ ] TASK-5  adminConfig.service.ts: добавить getOverview()
[ ] CHECK   npx tsc --noEmit → OK

── FRONTEND COMPONENTS ──────────────────────────────────────────────────
[ ] TASK-6  AdminOverviewTab.tsx: СОЗДАТЬ
[ ] TASK-7  OrchestratorTab.tsx: добавить actual_pipeline_mode badge
[ ] TASK-8  AdminPanel.tsx: рефакторинг TABS + шапка + рендер новых вкладок
[ ] CHECK   npx tsc --noEmit → OK

── TESTS ────────────────────────────────────────────────────────────────
[ ] СОЗДАТЬ test_admin_overview.py
[ ] СОЗДАТЬ test_orchestrator_metrics.py
[ ] СОЗДАТЬ AdminOverviewTab.test.tsx
[ ] CHECK   pytest -q tests/test_admin_overview.py tests/test_orchestrator_metrics.py → 13 passed
[ ] CHECK   npm run test -- --run src/components/admin/AdminOverviewTab.test.tsx → 5 passed

── ФИНАЛ ────────────────────────────────────────────────────────────────
[ ] npm run lint (tsc --noEmit) → OK
[ ] Открыть localhost:3000/admin → первая вкладка "⭐ Обзор"
[ ] Убедиться что вкладки LLM/Retrieval/Diagnostics/Routing скрыты под "Устаревшее ▾"
[ ] Убедиться что badge в шапке показывает реальный режим из env
[ ] Отправить тестовый запрос в чат → перейти в Обзор → calls > 0 у агентов
```


***

## 8. Примечания для агента

**⚠️ Критично при TASK-2:** Файл `orchestrator.py` может называться иначе (`multiagent_orchestrator.py`, `pipeline_orchestrator.py`). Найди класс с методом `process()` или `run()` который вызывает агентов последовательно — он правильный. Не создавай новый класс, только добавляй метод и инициализацию в `__init__`.

**⚠️ Критично при TASK-8:** Тип `Tab` и массив `TABS` существуют в `AdminPanel.tsx` начиная со строки ~20. Нужно полностью заменить их двумя массивами `MULTIAGENT_TABS` и `LEGACY_TABS`. Тип `Tab` расширить новыми ключами `overview` и `agent_prompts`.

**⚠️ Не удалять:** `PromptEditorPanel.tsx` — он остаётся в legacy-вкладке `prompts`. Новая вкладка `agent_prompts` рендерит `AgentPromptEditorPanel.tsx`.

*PRD-032 v1.0 — готов к передаче агенту IDE*

