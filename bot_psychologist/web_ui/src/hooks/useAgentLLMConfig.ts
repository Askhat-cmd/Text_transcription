import { useCallback, useEffect, useState } from 'react';

import { adminConfigService } from '../services/adminConfig.service';
import type { AgentLLMConfigResponse } from '../types/admin.types';

export const useAgentLLMConfig = () => {
  const [data, setData] = useState<AgentLLMConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const payload = await adminConfigService.getAgentLLMConfig();
      setData(payload);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setModel = useCallback(async (agentId: string, model: string) => {
    setIsSaving(true);
    setError(null);
    try {
      await adminConfigService.patchAgentLLMConfig(agentId, { model });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [load]);

  const setTemperature = useCallback(async (agentId: string, temperature: number) => {
    setIsSaving(true);
    setError(null);
    try {
      await adminConfigService.patchAgentLLMConfig(agentId, { temperature });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [load]);

  const resetModel = useCallback(async (agentId: string) => {
    setIsSaving(true);
    setError(null);
    try {
      await adminConfigService.resetAgentLLMConfig(agentId);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsSaving(false);
    }
  }, [load]);

  return {
    data,
    isLoading,
    isSaving,
    error,
    setModel,
    setTemperature,
    resetModel,
    reload: load,
  };
};
