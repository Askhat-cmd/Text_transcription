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
    threads,
    agentTraces,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadThreads,
    deleteThread,
    loadAgentTraces,
  };
};

