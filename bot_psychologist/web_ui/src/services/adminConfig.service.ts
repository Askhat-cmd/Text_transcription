// services/adminConfig.service.ts

import type {
  AdminConfigResponse,
  ConfigParam,
  PromptMeta,
  PromptDetail,
  HistoryEntry,
  AdminOverridesExport,
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
    request<PromptMeta[]>('GET', '/prompts'),
  getPrompt: (name: string) =>
    request<PromptDetail>('GET', `/prompts/${name}`),
  setPrompt: (name: string, text: string) =>
    request<PromptDetail>('PUT', `/prompts/${name}`, { text }),
  resetPrompt: (name: string) =>
    request<PromptDetail>('DELETE', `/prompts/${name}`),
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
};
