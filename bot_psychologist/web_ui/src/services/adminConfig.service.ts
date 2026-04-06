// services/adminConfig.service.ts

import type {
  AdminConfigResponse,
  ConfigParam,
  PromptMeta,
  PromptDetail,
  HistoryEntry,
  AdminOverridesExport,
  AdminStatusResponse,
  AdminRuntimeEffectiveResponse,
  AdminDiagnosticsEffectiveResponse,
  AdminTraceLastResponse,
  AdminTraceRecentResponse,
  PromptStackUsageResponse,
} from '../types/admin.types';

// Получаем API-ключ из localStorage (так же как и остальные запросы приложения)
function getDevApiKey(): string {
  return localStorage.getItem('devApiKey') ?? '';
}

const BASE = '/api/admin';

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': getDevApiKey(),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const adminConfigService = {
  // Config
  getConfig: () =>
    request<AdminConfigResponse>('GET', '/config'),
  setConfigParam: (key: string, value: unknown) =>
    request<ConfigParam>('PUT', '/config', { key, value }),
  resetConfigParam: (key: string) =>
    request<{ key: string; value: unknown; is_overridden: false }>(
      'DELETE', `/config/${key}`
    ),
  resetAllConfig: () =>
    request<{ status: string }>('POST', '/config/reset-all'),

  // Prompts
  getPrompts: () =>
    request<PromptMeta[]>('GET', '/prompts/stack-v2'),
  getPrompt: (name: string) =>
    request<PromptDetail>('GET', `/prompts/stack-v2/${name}`),
  getPromptStackUsage: () =>
    request<PromptStackUsageResponse>('GET', '/prompts/stack-v2/usage'),
  setPrompt: (name: string, text: string) =>
    request<PromptDetail>('PUT', `/prompts/stack-v2/${name}`, { text }),
  resetPrompt: (name: string) =>
    request<PromptDetail>('POST', `/prompts/stack-v2/${name}/reset`),
  resetAllPrompts: () =>
    request<{ status: string }>('POST', '/prompts/reset-all'),

  // History
  getHistory: () =>
    request<{ history: HistoryEntry[] }>('GET', '/history'),

  // Export / Import
  exportOverrides: () =>
    request<AdminOverridesExport>('GET', '/export'),
  importOverrides: (data: AdminOverridesExport) =>
    request<{ status: string; config_keys: number; prompt_overrides: number }>(
      'POST', '/import', data
    ),

  // Full reset
  resetAll: () =>
    request<{ status: string }>('POST', '/reset-all'),

  // Runtime status
  getStatus: () =>
    request<AdminStatusResponse>('GET', '/status'),
  getRuntimeEffective: () =>
    request<AdminRuntimeEffectiveResponse>('GET', '/runtime/effective'),
  getDiagnosticsEffective: () =>
    request<AdminDiagnosticsEffectiveResponse>('GET', '/diagnostics/effective'),
  getTraceLast: () =>
    request<AdminTraceLastResponse>('GET', '/trace/last'),
  getTraceRecent: (limit = 10) =>
    request<AdminTraceRecentResponse>('GET', `/trace/recent?limit=${limit}`),
  reloadData: () =>
    request<{ status: string; blocks_loaded: number; data_source: string; degraded_mode: boolean }>(
      'POST',
      '/reload-data'
    ),
};
