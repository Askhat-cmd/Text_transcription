// hooks/useAdminConfig.ts

import { useState, useCallback } from 'react';
import { adminConfigService } from '../services/adminConfig.service';
import type {
  AdminConfigResponse,
  PromptMeta,
  PromptDetail,
  AdminStatusResponse,
} from '../types/admin.types';

export const useAdminConfig = () => {
  const [configData, setConfigData] = useState<AdminConfigResponse | null>(null);
  const [prompts, setPrompts] = useState<PromptMeta[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [statusData, setStatusData] = useState<AdminStatusResponse | null>(null);

  const clearError = useCallback(() => setError(null), []);

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

  const reloadKnowledgeBase = useCallback(async () => {
    const result = await withSaving(() => adminConfigService.reloadData());
    if (result) {
      await loadStatus();
      showSuccess('✓ База знаний перезагружена');
    }
  }, [loadStatus, showSuccess]);

  // ── Prompts ─────────────────────────────────────────────────────────

  const loadPrompts = useCallback(async () => {
    const data = await withLoading(() => adminConfigService.getPrompts());
    if (data) setPrompts(data);
  }, []);

  const loadPromptDetail = useCallback(async (name: string) => {
    const data = await withLoading(() => adminConfigService.getPrompt(name));
    if (data) setSelectedPrompt(data);
  }, []);

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
    prompts,
    selectedPrompt,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadConfig,
    loadPrompts,
    loadPromptDetail,
    saveConfigParam,
    resetConfigParam,
    resetAllConfig,
    loadStatus,
    reloadKnowledgeBase,
    savePrompt,
    resetPrompt,
    resetAllPrompts,
    exportOverrides,
    importOverrides,
  };
};
