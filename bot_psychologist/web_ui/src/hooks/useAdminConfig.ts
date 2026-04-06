// hooks/useAdminConfig.ts

import { useState, useCallback } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type {
  AdminConfigResponse,
  PromptMeta,
  PromptDetail,
  AdminStatusResponse,
  AdminRuntimeEffectiveResponse,
  AdminDiagnosticsEffectiveResponse,
  AdminTraceLastResponse,
  AdminTraceRecentResponse,
  PromptStackUsageResponse,
} from '../types/admin.types';

export const useAdminConfig = () => {
  const [configData, setConfigData] = useState<AdminConfigResponse | null>(null);
  const [prompts, setPrompts] = useState<PromptMeta[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [lastPromptName, setLastPromptName] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [statusData, setStatusData] = useState<AdminStatusResponse | null>(null);
  const [runtimeEffectiveData, setRuntimeEffectiveData] =
    useState<AdminRuntimeEffectiveResponse | null>(null);
  const [diagnosticsEffectiveData, setDiagnosticsEffectiveData] =
    useState<AdminDiagnosticsEffectiveResponse | null>(null);
  const [traceLastData, setTraceLastData] = useState<AdminTraceLastResponse | null>(null);
  const [traceRecentData, setTraceRecentData] = useState<AdminTraceRecentResponse | null>(null);
  const [promptUsageData, setPromptUsageData] = useState<PromptStackUsageResponse | null>(null);

  const clearError = useCallback(() => {
    setError(null);
    setPromptError(null);
  }, []);

  const showSuccess = useCallback((msg: string) => {
    setSuccessMessage(msg);
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

  // ── Config ──────────────────────────────────────────────────────────

  const loadConfig = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getConfig());
    if (data) setConfigData(data);
  }, []);

  const saveConfigParam = useCallback(
    async (key: string, value: unknown) => {
      await withSaving(() => adminConfigService.setConfigParam(key, value));
      await loadConfig();
      showSuccess(`✓ ${key} сохранён`);
    },
    [loadConfig, showSuccess]
  );

  const resetConfigParam = useCallback(
    async (key: string) => {
      if (!window.confirm('Сбросить параметр к дефолту?')) return;
      await withSaving(() => adminConfigService.resetConfigParam(key));
      await loadConfig();
      showSuccess(`↩ ${key} сброшен к дефолту`);
    },
    [loadConfig, showSuccess]
  );

  const resetAllConfig = useCallback(async () => {
    if (!window.confirm('Сбросить ВСЕ параметры конфига к дефолтам?')) return;
    await withSaving(() => adminConfigService.resetAllConfig());
    await loadConfig();
    showSuccess('↩ Все параметры конфига сброшены');
  }, [loadConfig, showSuccess]);

  const loadStatus = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getStatus());
    if (data) setStatusData(data);
  }, []);

  const loadRuntimeEffective = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getRuntimeEffective());
    if (data) setRuntimeEffectiveData(data);
  }, []);

  const loadDiagnosticsEffective = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getDiagnosticsEffective());
    if (data) setDiagnosticsEffectiveData(data);
  }, []);

  const loadTraceLast = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getTraceLast());
    if (data) setTraceLastData(data);
  }, []);

  const loadTraceRecent = useCallback(async (limit = 10) => {
    const data = await withLoading(() => adminConfigService.getTraceRecent(limit));
    if (data) setTraceRecentData(data);
  }, []);

  const loadPromptUsage = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getPromptStackUsage());
    if (data) setPromptUsageData(data);
  }, []);

  const reloadKnowledgeBase = useCallback(async () => {
    const result = await withSaving(() => adminConfigService.reloadData());
    if (result) {
      await loadStatus();
      await loadRuntimeEffective();
      await loadDiagnosticsEffective();
      await loadTraceLast();
      await loadTraceRecent(10);
      await loadPromptUsage();
      showSuccess('✓ База знаний перезагружена');
    }
  }, [
    loadDiagnosticsEffective,
    loadPromptUsage,
    loadRuntimeEffective,
    loadStatus,
    loadTraceLast,
    loadTraceRecent,
    showSuccess,
  ]);

  // ── Prompts ─────────────────────────────────────────────────────────

  const loadPrompts = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getPrompts());
    if (data) {
      setPrompts(data);
      setPromptError(null);
    }
  }, []);

  const loadPromptDetail = useCallback(async (name: string) => {
    setLastPromptName(name);
    setPromptError(null);
    const data = await withLoading(() => adminConfigService.getPrompt(name));
    if (data) {
      setSelectedPrompt(data);
      setPromptError(null);
      return;
    }
    setSelectedPrompt(null);
    setPromptError('Не удалось загрузить секцию prompt stack v2. Проверь backend и нажми «Повторить».');
  }, []);

  const retryPromptDetailLoad = useCallback(async () => {
    if (!lastPromptName) return;
    await loadPromptDetail(lastPromptName);
  }, [lastPromptName, loadPromptDetail]);

  const savePrompt = useCallback(
    async (name: string, text: string) => {
      const updated = await withSaving(() =>
        adminConfigService.setPrompt(name, text)
      );
      if (updated) {
        setSelectedPrompt(updated);
        await loadPrompts();
        showSuccess('✓ Промт сохранён');
      }
    },
    [loadPrompts, showSuccess]
  );

  const resetPrompt = useCallback(
    async (name: string) => {
      if (!window.confirm('Сбросить промт к оригиналу из .md файла?')) return;
      const updated = await withSaving(() =>
        adminConfigService.resetPrompt(name)
      );
      if (updated) {
        setSelectedPrompt(updated);
        await loadPrompts();
        showSuccess('↩ Промт сброшен к дефолту');
      }
    },
    [loadPrompts, showSuccess]
  );

  const resetAllPrompts = useCallback(async () => {
    if (!window.confirm('Сбросить ВСЕ промты к оригиналам?')) return;
    await withSaving(() => adminConfigService.resetAllPrompts());
    await loadPrompts();
    if (selectedPrompt) await loadPromptDetail(selectedPrompt.name);
    showSuccess('↩ Все промты сброшены');
  }, [loadPrompts, selectedPrompt, loadPromptDetail, showSuccess]);

  // ── Export / Import ─────────────────────────────────────────────────

  const exportOverrides = useCallback(async () => {
    const data = await adminConfigService.exportOverrides();
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `admin_overrides_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showSuccess('✓ Файл скачан');
  }, [showSuccess]);

  const importOverrides = useCallback(
    async (file: File) => {
      const text = await file.text();
      const data = JSON.parse(text);
      await withSaving(() => adminConfigService.importOverrides(data));
      await loadConfig();
      await loadPrompts();
      showSuccess('✓ Настройки импортированы');
    },
    [loadConfig, loadPrompts, showSuccess]
  );

  return {
    configData,
    statusData,
    runtimeEffectiveData,
    diagnosticsEffectiveData,
    traceLastData,
    traceRecentData,
    promptUsageData,
    prompts,
    selectedPrompt,
    isLoading,
    isSaving,
    error,
    promptError,
    successMessage,
    clearError,
    loadConfig,
    loadPrompts,
    loadPromptDetail,
    retryPromptDetailLoad,
    saveConfigParam,
    resetConfigParam,
    resetAllConfig,
    loadStatus,
    loadRuntimeEffective,
    loadDiagnosticsEffective,
    loadTraceLast,
    loadTraceRecent,
    loadPromptUsage,
    reloadKnowledgeBase,
    savePrompt,
    resetPrompt,
    resetAllPrompts,
    exportOverrides,
    importOverrides,
  };
};
