import { useCallback, useState } from 'react';

import { adminConfigService } from '../services/adminConfig.service';
import type {
  AgentId,
  AgentStatus,
  AgentTrace,
  ThreadItem,
  OrchestratorConfig,
  AgentPrompt,
} from '../types/admin.types';

type ManagedAgentId = 'writer' | 'state_analyzer' | 'thread_manager';

export const useAgents = () => {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [orchestratorConfig, setOrchestratorConfig] = useState<OrchestratorConfig | null>(null);
  const [agentTraces, setAgentTraces] = useState<AgentTrace[]>([]);
  const [threads, setThreads] = useState<ThreadItem[]>([]);
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
    setError(null);
    setIsLoading(true);
    try {
      return await fn();
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setIsLoading(false);
    }
  };

  const withSaving = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    setError(null);
    setIsSaving(true);
    try {
      return await fn();
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setIsSaving(false);
    }
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

  const loadOrchestratorConfig = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getOrchestratorConfig());
    if (data) setOrchestratorConfig(data);
  }, []);

  const setPipelineMode = useCallback(async (mode: 'full_multiagent' | 'hybrid' | 'legacy_adaptive') => {
    const data = await withSaving(() => adminConfigService.patchOrchestratorConfig(mode));
    if (data) {
      await loadOrchestratorConfig();
      showSuccess(`✓ pipeline_mode: ${data.pipeline_mode}`);
    }
  }, [loadOrchestratorConfig, showSuccess]);

  const loadAgentTraces = useCallback(async (params?: { limit?: number; agent_id?: string }) => {
    const data = await withLoading(() => adminConfigService.getAgentTraces(params));
    if (data) setAgentTraces(data.traces);
  }, []);

  const loadThreads = useCallback(async (status: 'active' | 'archived' | 'all' = 'active', userId?: string, limit = 50) => {
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

  const loadAgentPrompts = useCallback(async (agentId: ManagedAgentId) => {
    const data = await withLoading(() => adminConfigService.getAgentPrompts(agentId));
    if (data) setAgentPrompts(data.prompts);
  }, []);

  const saveAgentPrompt = useCallback(async (agentId: ManagedAgentId, promptKey: string, text: string) => {
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
    agents,
    orchestratorConfig,
    agentTraces,
    threads,
    agentPrompts,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadAgentsStatus,
    toggleAgent,
    loadOrchestratorConfig,
    setPipelineMode,
    loadAgentTraces,
    loadThreads,
    deleteThread,
    loadAgentPrompts,
    saveAgentPrompt,
    resetAgentPrompt,
  };
};
