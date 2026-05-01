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

  const loadAgentPrompts = useCallback(async (agentId: ManagedAgentId) => {
    const data = await withLoading(() => adminConfigService.getAgentPrompts(agentId));
    if (data) setAgentPrompts(data.prompts);
  }, []);

  const saveAgentPrompt = useCallback(async (
    agentId: ManagedAgentId,
    promptKey: string,
    text: string,
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
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadAgentPrompts,
    saveAgentPrompt,
    resetAgentPrompt,
  };
};

