import { useCallback, useState } from 'react';

import { adminConfigService } from '../services/adminConfig.service';
import type { OrchestratorConfig } from '../types/admin.types';

type PipelineMode = 'multiagent_only' | 'full_multiagent';

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
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadOrchestratorConfig,
    setPipelineMode,
  };
};
