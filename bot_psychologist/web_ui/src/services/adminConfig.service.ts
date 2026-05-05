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
  AgentsStatusResponse,
  OrchestratorConfig,
  AgentTracesResponse,
  ThreadsResponse,
  AgentPromptsResponse,
  AgentLLMConfigResponse,
  OverviewData,
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
  reloadData: () =>
    request<{ status: string; blocks_loaded: number; data_source: string; degraded_mode: boolean }>(
      'POST',
      '/reload-data'
    ),

  // Multiagent
  getAgentsStatus: () =>
    request<AgentsStatusResponse>('GET', '/agents/status'),
  toggleAgent: (agentId: string, enabled: boolean) =>
    request<{ status: string; agent_id: string; enabled: boolean }>('POST', `/agents/${agentId}/toggle`, { enabled }),
  recordAgentMetric: (body: { agent_id: string; latency_ms?: number; error?: boolean }) =>
    request<{ status: string }>('POST', '/agents/metrics/record', body),

  getOrchestratorConfig: () =>
    request<OrchestratorConfig>('GET', '/orchestrator/config'),
  getOverview: () =>
    request<OverviewData>('GET', '/overview'),
  patchOrchestratorConfig: (pipeline_mode: 'multiagent_only' | 'full_multiagent') =>
    request<{ status: string; pipeline_mode: 'multiagent_only'; pipeline_mode_alias_received?: string }>(
      'PATCH',
      '/orchestrator/config',
      { pipeline_mode }
    ),

  getAgentTraces: (params?: { limit?: number; agent_id?: string }) => {
    const search = new URLSearchParams();
    if (params?.limit != null) search.set('limit', String(params.limit));
    if (params?.agent_id) search.set('agent_id', params.agent_id);
    const query = search.toString();
    return request<AgentTracesResponse>('GET', `/agents/traces${query ? `?${query}` : ''}`);
  },
  recordAgentTrace: (body: {
    agent_id: string;
    request_id?: string;
    user_id?: string;
    input_preview?: string;
    output_preview?: string;
    latency_ms?: number;
    error?: string | null;
  }) => request<{ status: string }>('POST', '/agents/traces/record', body),

  getThreads: (status: 'active' | 'archived' | 'all' = 'active', user_id?: string, limit = 50) => {
    const search = new URLSearchParams();
    search.set('status', status);
    search.set('limit', String(limit));
    if (user_id) search.set('user_id', user_id);
    return request<ThreadsResponse>('GET', `/threads?${search.toString()}`);
  },
  deleteThread: (userId: string) =>
    request<{ status: string; user_id: string; deleted: string }>('DELETE', `/threads/${userId}`),

  getAgentPrompts: (agentId: 'writer' | 'state_analyzer' | 'thread_manager') =>
    request<AgentPromptsResponse>('GET', `/agents/${agentId}/prompts`),
  updateAgentPrompt: (agentId: 'writer' | 'state_analyzer' | 'thread_manager', promptKey: string, text: string) =>
    request<{ status: string; agent_id: string; prompt_key: string; is_overridden: boolean; char_count: number }>(
      'PUT',
      `/agents/${agentId}/prompts/${promptKey}`,
      { text }
    ),
  resetAgentPrompt: (agentId: 'writer' | 'state_analyzer' | 'thread_manager', promptKey: string) =>
    request<{ status: string; agent_id: string; prompt_key: string; is_overridden: boolean }>(
      'POST',
      `/agents/${agentId}/prompts/${promptKey}/reset`
    ),

  getAgentLLMConfig: () =>
    request<AgentLLMConfigResponse>('GET', '/agents/llm-config'),
  patchAgentLLMConfig: (agentId: string, payload: { model?: string; temperature?: number }) =>
    request<{
      status: string;
      agent_id: string;
      model: string;
      temperature: number;
      is_overridden: boolean;
      is_temperature_overridden: boolean;
    }>(
      'PATCH',
      `/agents/${agentId}/llm-config`,
      payload
    ),
  resetAgentLLMConfig: (agentId: string) =>
    request<{
      status: string;
      agent_id: string;
      model: string;
      temperature: number;
      is_overridden: boolean;
      is_temperature_overridden: boolean;
    }>(
      'POST',
      `/agents/${agentId}/llm-config/reset`
    ),
};
