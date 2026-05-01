
# PRD-031-patch: Рефакторинг useAgents → 4 специализированных хука

**Версия:** 1.0 | **Тип:** Refactor (no new features, no backend changes)
**Предшественник:** PRD-031 (коммит f696a2e)

***

## Что меняется

| Файл | Действие |
| :-- | :-- |
| `hooks/useAgents.ts` | **УДАЛИТЬ** |
| `hooks/useAgentStatus.ts` | **СОЗДАТЬ** |
| `hooks/useOrchestrator.ts` | **СОЗДАТЬ** |
| `hooks/useThreads.ts` | **СОЗДАТЬ** |
| `hooks/useAgentPrompts.ts` | **СОЗДАТЬ** |
| `hooks/useAgents.test.ts` | **УДАЛИТЬ** → заменить 4 файлами |
| 4 компонента (`AgentsTab`, `OrchestratorTab`, `ThreadsTab`, `AgentPromptEditorPanel`) | **PATCH: 1 строка импорта** |

**НЕ ТРОГАТЬ:** `admin_routes.py`, `admin.types.ts`, `adminConfig.service.ts`, `AdminPanel.tsx`, debug-компоненты.

***

## Задача 1: `hooks/useAgentStatus.ts` — CREATE

```typescript
import { useCallback, useState } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type { AgentId, AgentStatus } from '../types/admin.types';

export const useAgentStatus = () => {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = useCallback((message: string) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(null), 2500);
  }, []);

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsLoading(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsLoading(false); }
  };

  const withSaving = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsSaving(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsSaving(false); }
  };

  const loadAgentsStatus = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getAgentsStatus());
    if (data) setAgents(data.agents);
  }, []);

  const toggleAgent = useCallback(async (agentId: AgentId, enabled: boolean) => {
    const data = await withSaving(() => adminConfigService.toggleAgent(agentId, enabled));
    if (data) {
      await loadAgentsStatus();
      showSuccess(`✓ ${data.agent_id}: ${data.enabled ? 'enabled' : 'disabled'}`);
    }
  }, [loadAgentsStatus, showSuccess]);

  const clearError = useCallback(() => setError(null), []);

  return {
    agents,
    isLoading, isSaving, error, successMessage, clearError,
    loadAgentsStatus, toggleAgent,
  };
};
```


***

## Задача 2: `hooks/useOrchestrator.ts` — CREATE

```typescript
import { useCallback, useState } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type { OrchestratorConfig } from '../types/admin.types';

type PipelineMode = 'full_multiagent' | 'hybrid' | 'legacy_adaptive';

export const useOrchestrator = () => {
  const [orchestratorConfig, setOrchestratorConfig] = useState<OrchestratorConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = useCallback((message: string) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(null), 2500);
  }, []);

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsLoading(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsLoading(false); }
  };

  const withSaving = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsSaving(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsSaving(false); }
  };

  const loadOrchestratorConfig = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getOrchestratorConfig());
    if (data) setOrchestratorConfig(data);
  }, []);

  const setPipelineMode = useCallback(async (mode: PipelineMode) => {
    const data = await withSaving(() => adminConfigService.patchOrchestratorConfig(mode));
    if (data) {
      await loadOrchestratorConfig();
      showSuccess(`✓ pipeline_mode: ${data.pipeline_mode}`);
    }
  }, [loadOrchestratorConfig, showSuccess]);

  const clearError = useCallback(() => setError(null), []);

  return {
    orchestratorConfig,
    isLoading, isSaving, error, successMessage, clearError,
    loadOrchestratorConfig, setPipelineMode,
  };
};
```


***

## Задача 3: `hooks/useThreads.ts` — CREATE

```typescript
import { useCallback, useState } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type { AgentTrace, ThreadItem } from '../types/admin.types';

export const useThreads = () => {
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [agentTraces, setAgentTraces] = useState<AgentTrace[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = useCallback((message: string) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(null), 2500);
  }, []);

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsLoading(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsLoading(false); }
  };

  const withSaving = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsSaving(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsSaving(false); }
  };

  const loadThreads = useCallback(async (
    status: 'active' | 'archived' | 'all' = 'active',
    userId?: string,
    limit = 50,
  ) => {
    const data = await withLoading(() => adminConfigService.getThreads(status, userId, limit));
    if (data) setThreads(data.threads);
  }, []);

  const deleteThread = useCallback(async (userId: string) => {
    const data = await withSaving(() => adminConfigService.deleteThread(userId));
    if (data) {
      await loadThreads('active');
      showSuccess(`✓ удалён тред: ${userId}`);
    }
  }, [loadThreads, showSuccess]);

  const loadAgentTraces = useCallback(async (params?: { limit?: number; agent_id?: string }) => {
    const data = await withLoading(() => adminConfigService.getAgentTraces(params));
    if (data) setAgentTraces(data.traces);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    threads, agentTraces,
    isLoading, isSaving, error, successMessage, clearError,
    loadThreads, deleteThread, loadAgentTraces,
  };
};
```


***

## Задача 4: `hooks/useAgentPrompts.ts` — CREATE

```typescript
import { useCallback, useState } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type { AgentPrompt } from '../types/admin.types';

type ManagedAgentId = 'writer' | 'state_analyzer' | 'thread_manager';

export const useAgentPrompts = () => {
  const [agentPrompts, setAgentPrompts] = useState<AgentPrompt[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = useCallback((message: string) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(null), 2500);
  }, []);

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsLoading(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsLoading(false); }
  };

  const withSaving = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null); setIsSaving(true);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setIsSaving(false); }
  };

  const loadAgentPrompts = useCallback(async (agentId: ManagedAgentId) => {
    const data = await withLoading(() => adminConfigService.getAgentPrompts(agentId));
    if (data) setAgentPrompts(data.prompts);
  }, []);

  const saveAgentPrompt = useCallback(async (
    agentId: ManagedAgentId, promptKey: string, text: string,
  ) => {
    const data = await withSaving(() => adminConfigService.updateAgentPrompt(agentId, promptKey, text));
    if (data) {
      await loadAgentPrompts(agentId);
      showSuccess(`✓ сохранён промпт: ${data.prompt_key}`);
    }
  }, [loadAgentPrompts, showSuccess]);

  const resetAgentPrompt = useCallback(async (agentId: ManagedAgentId, promptKey: string) => {
    const data = await withSaving(() => adminConfigService.resetAgentPrompt(agentId, promptKey));
    if (data) {
      await loadAgentPrompts(agentId);
      showSuccess(`↩ сброшен промпт: ${data.prompt_key}`);
    }
  }, [loadAgentPrompts, showSuccess]);

  const clearError = useCallback(() => setError(null), []);

  return {
    agentPrompts,
    isLoading, isSaving, error, successMessage, clearError,
    loadAgentPrompts, saveAgentPrompt, resetAgentPrompt,
  };
};
```


***

## Задача 5–9: Патчи компонентов (по 2 строки каждый)

```diff
// AgentsTab.tsx
- import { useAgents } from '../../hooks/useAgents';
+ import { useAgentStatus } from '../../hooks/useAgentStatus';
- const { agents, isLoading, error, loadAgentsStatus, toggleAgent } = useAgents();
+ const { agents, isLoading, error, loadAgentsStatus, toggleAgent } = useAgentStatus();

// OrchestratorTab.tsx
- import { useAgents } from '../../hooks/useAgents';
+ import { useOrchestrator } from '../../hooks/useOrchestrator';
- const { orchestratorConfig, isLoading, isSaving, error, successMessage,
-         loadOrchestratorConfig, setPipelineMode } = useAgents();
+ const { orchestratorConfig, isLoading, isSaving, error, successMessage,
+         loadOrchestratorConfig, setPipelineMode } = useOrchestrator();

// ThreadsTab.tsx
- import { useAgents } from '../../hooks/useAgents';
+ import { useThreads } from '../../hooks/useThreads';
- const { threads, isLoading, isSaving, error, loadThreads, deleteThread } = useAgents();
+ const { threads, isLoading, isSaving, error, loadThreads, deleteThread } = useThreads();

// AgentPromptEditorPanel.tsx
- import { useAgents } from '../../hooks/useAgents';
+ import { useAgentPrompts } from '../../hooks/useAgentPrompts';
- const { agentPrompts, isLoading, isSaving, error, successMessage,
-         loadAgentPrompts, saveAgentPrompt, resetAgentPrompt } = useAgents();
+ const { agentPrompts, isLoading, isSaving, error, successMessage,
+         loadAgentPrompts, saveAgentPrompt, resetAgentPrompt } = useAgentPrompts();
```


***

## Порядок выполнения

```
Шаг 1-4  — Создать 4 новых хука
Шаг 5-8  — Обновить импорты в 4 компонентах
Шаг 9    — npx tsc --noEmit → OK
Шаг 10   — УДАЛИТЬ useAgents.ts
Шаг 11   — npx tsc --noEmit → снова OK (нет других импортов)
Шаг 12   — УДАЛИТЬ useAgents.test.ts, создать 4 новых теста
Шаг 13   — npm run test → все тесты зелёные
```

**⚠️ Критично:** удалять `useAgents.ts` только на шаге 10, строго после патча всех компонентов.

***

## Финальный чеклист

- [ ] 4 новых хука созданы
- [ ] 4 компонента обновлены (только строка импорта)
- [ ] `useAgents.ts` удалён
- [ ] `npx tsc --noEmit` — OK
- [ ] `npm run test` — 8 новых тестов зелёные
- [ ] Все 3 вкладки AdminPanel работают без изменений

*PRD-031-patch v1.0 — готов к передаче агенту IDE*

