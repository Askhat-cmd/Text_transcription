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

  const withLoading = async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
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

  const withSaving = async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
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

  const clearError = useCallback(() => setError(null), []);

  return {
    agents,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadAgentsStatus,
    toggleAgent,
  };
};

