import React, { useEffect, useRef, useState } from 'react';

import { useAdminConfig } from '../../hooks/useAdminConfig';
import { useOrchestrator } from '../../hooks/useOrchestrator';
import { GROUP_COLORS } from '../../constants/adminColors';
import type { HistoryEntry } from '../../types/admin.types';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { PromptEditorPanel } from './PromptEditorPanel';
import { HistoryPanel } from './HistoryPanel';
import { AgentsTab } from './AgentsTab';
import { OrchestratorTab } from './OrchestratorTab';
import { ThreadsTab } from './ThreadsTab';
import { AgentPromptEditorPanel } from './AgentPromptEditorPanel';
import { AdminOverviewTab } from './AdminOverviewTab';

type Tab =
  | 'overview'
  | 'agents'
  | 'orchestrator'
  | 'threads'
  | 'agent_prompts'
  | 'runtime'
  | 'memory'
  | 'llm'
  | 'retrieval'
  | 'diagnostics'
  | 'routing'
  | 'prompts'
  | 'compatibility';

const PRIMARY_TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'overview', label: 'Overview', hoverColor: 'hover:bg-sky-500/20' },
  { key: 'agents', label: 'Agents', hoverColor: 'hover:bg-purple-500/20' },
  { key: 'orchestrator', label: 'Orchestrator', hoverColor: 'hover:bg-indigo-500/20' },
  { key: 'threads', label: 'Threads', hoverColor: 'hover:bg-teal-500/20' },
  { key: 'agent_prompts', label: 'Agent Prompts', hoverColor: 'hover:bg-fuchsia-500/20' },
  { key: 'runtime', label: 'Runtime', hoverColor: 'hover:bg-slate-500/20' },
  { key: 'memory', label: 'Memory', hoverColor: 'hover:bg-emerald-500/20' },
];

const ADVANCED_TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'llm', label: 'LLM', hoverColor: 'hover:bg-violet-500/20' },
  { key: 'retrieval', label: 'Retrieval', hoverColor: 'hover:bg-blue-500/20' },
  { key: 'diagnostics', label: 'Diagnostics', hoverColor: 'hover:bg-cyan-500/20' },
  { key: 'routing', label: 'Routing', hoverColor: 'hover:bg-cyan-500/20' },
  { key: 'prompts', label: 'Prompts', hoverColor: 'hover:bg-rose-500/20' },
  { key: 'compatibility', label: 'Compatibility', hoverColor: 'hover:bg-amber-500/20' },
];

const ROUTING_ADVANCED_KEYS = new Set([
  'FAST_DETECTOR_ENABLED',
  'FAST_DETECTOR_CONFIDENCE_THRESHOLD',
  'STATE_CLASSIFIER_ENABLED',
  'STATE_CLASSIFIER_CONFIDENCE_THRESHOLD',
]);

const ADVANCED_TAB_KEYS = new Set<Tab>(['llm', 'retrieval', 'diagnostics', 'routing', 'prompts', 'compatibility']);

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [legacyOpen, setLegacyOpen] = useState(false);
  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem('devApiKey') || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData,
    prompts,
    selectedPrompt,
    statusData,
    diagnosticsEffectiveData,
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
    loadRuntimeEffective,
    loadDiagnosticsEffective,
    loadStatus,
    reloadKnowledgeBase,
    saveConfigParam,
    resetConfigParam,
    resetAllConfig,
    savePrompt,
    resetPrompt,
    resetAllPrompts,
    exportOverrides,
    importOverrides,
  } = useAdminConfig();

  const { orchestratorConfig, loadOrchestratorConfig } = useOrchestrator();

  useEffect(() => {
    if (apiKey) localStorage.setItem('devApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => {
    loadConfig();
    loadPrompts();
    loadStatus();
    loadRuntimeEffective();
    loadDiagnosticsEffective();
    void loadOrchestratorConfig();
  }, []);

  useEffect(() => {
    if (activeTab !== 'compatibility') return;
    import('../../services/adminConfig.service').then(({ adminConfigService }) => {
      adminConfigService.getHistory().then((data) => setHistory(data.history));
    });
  }, [activeTab]);

  useEffect(() => {
    if (ADVANCED_TAB_KEYS.has(activeTab)) {
      setLegacyOpen(true);
    }
  }, [activeTab]);

  const handleResetConfigParam = async (key: string) => {
    if (key === '__all__') await resetAllConfig();
    else await resetConfigParam(key);
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await importOverrides(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const routingGroup = configData?.groups?.routing;
  const filteredRoutingGroup = routingGroup ?? null;
  const routingPolicyGroup = filteredRoutingGroup
    ? {
        ...filteredRoutingGroup,
        params: Object.fromEntries(
          Object.entries(filteredRoutingGroup.params).filter(([key]) => !ROUTING_ADVANCED_KEYS.has(key)),
        ),
      }
    : null;
  const routingAdvancedGroup = filteredRoutingGroup
    ? {
        ...filteredRoutingGroup,
        label: 'Advanced Routing Controls',
        params: Object.fromEntries(
          Object.entries(filteredRoutingGroup.params).filter(([key]) => ROUTING_ADVANCED_KEYS.has(key)),
        ),
      }
    : null;

  const pipelineBadgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  const runtimeEntrypoint = orchestratorConfig?.runtime_entrypoint ?? 'multiagent_adapter';

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="bg-gradient-to-r from-slate-900 to-slate-700 px-6 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">Admin Config Panel</h1>
                <p className="text-sm text-slate-400 mt-0.5">Multiagent-first control surface</p>
                <div className="mt-2">
                  <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${pipelineBadgeClass}`}>
                    multiagent
                  </span>
                  <span className="ml-2 inline-flex items-center rounded border border-slate-500/50 bg-slate-700/30 px-2 py-0.5 text-xs text-slate-200">
                    entrypoint: {runtimeEntrypoint}
                  </span>
                  <span className="ml-2 inline-flex items-center rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                    legacy fallback: disabled
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="dev-key-001"
                    className="w-48 px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-400"
                  />
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
                  >
                    {showApiKey ? 'hide' : 'show'}
                  </button>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded font-medium ${
                    apiKey
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}
                >
                  {apiKey ? 'ok' : 'empty'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={exportOverrides}
                className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300 hover:bg-slate-600 transition-colors"
              >
                Export
              </button>
              <label className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300 hover:bg-slate-600 transition-colors cursor-pointer">
                Import
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={handleImportFile}
                />
              </label>
              <button
                onClick={async () => {
                  if (!window.confirm('Full reset: delete all overrides (config + prompts)?')) return;
                  const { adminConfigService } = await import('../../services/adminConfig.service');
                  await adminConfigService.resetAll();
                  await loadConfig();
                  await loadPrompts();
                }}
                className="px-3 py-1.5 border border-red-500/40 rounded text-sm text-red-400 hover:bg-red-500/20 transition-colors"
              >
                Full reset
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-800 px-6 shadow-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <div className="flex gap-1">
            {PRIMARY_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                  activeTab === tab.key
                    ? 'border-violet-400 text-white bg-white/5'
                    : `border-transparent text-slate-400 ${tab.hoverColor} hover:text-white`
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <details className="relative" open={legacyOpen} onToggle={(e) => setLegacyOpen((e.target as HTMLDetailsElement).open)}>
            <summary className="list-none cursor-pointer px-3 py-1.5 text-xs border border-slate-600 rounded text-slate-300 hover:bg-slate-700">
              Advanced Controls
            </summary>
            <div className="absolute right-0 mt-1 w-[34rem] rounded border border-slate-700 bg-slate-900 p-2 shadow-lg z-20">
              <div className="flex flex-wrap gap-1">
                {ADVANCED_TABS.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-3 py-1.5 text-xs rounded transition-all ${
                      activeTab === tab.key ? 'bg-white/10 text-white' : `text-slate-300 ${tab.hoverColor} hover:text-white`
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </details>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 pt-3">
        {error && (
          <div className="flex items-center justify-between px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
            <span>{error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">x</button>
          </div>
        )}
        {successMessage && (
          <div className="px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700 mb-3">
            {successMessage}
          </div>
        )}
      </div>

      <div className="max-w-6xl mx-auto px-6 pb-10">
        {isLoading && <div className="text-center text-slate-400 py-12 text-sm">Loading...</div>}

        {!isLoading && configData && (
          <>
            {activeTab === 'overview' && <AdminOverviewTab />}
            {activeTab === 'agents' && <AgentsTab />}
            {activeTab === 'orchestrator' && <OrchestratorTab />}
            {activeTab === 'threads' && <ThreadsTab />}
            {activeTab === 'agent_prompts' && (
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-900 shadow-md h-[70vh] overflow-hidden">
                <AgentPromptEditorPanel />
              </div>
            )}

            {(activeTab === 'llm' || activeTab === 'retrieval' || activeTab === 'memory' || activeTab === 'runtime') && (
              <div className="mt-4 space-y-4">
                {Object.entries(configData.groups)
                  .filter(([groupKey]) => groupKey === activeTab)
                  .map(([groupKey, group]) => (
                    <ConfigGroupPanel
                      key={groupKey}
                      groupKey={groupKey}
                      group={group}
                      onSave={saveConfigParam}
                      onReset={handleResetConfigParam}
                      isSaving={isSaving}
                      accentColor={GROUP_COLORS[groupKey] ?? 'blue'}
                    />
                  ))}

                {activeTab === 'runtime' && statusData && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                    <h3 className="font-semibold text-slate-800 mb-3">System Status</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                      <div>data_source: <span className="font-medium">{statusData.data_source}</span></div>
                      <div>blocks_loaded: <span className="font-medium">{statusData.blocks_loaded}</span></div>
                      <div>degraded_mode: <span className="font-medium">{statusData.degraded_mode ? 'on' : 'off'}</span></div>
                      <div>version: <span className="font-medium">{statusData.version}</span></div>
                    </div>
                    <div className="mt-3">
                      <button
                        onClick={reloadKnowledgeBase}
                        disabled={isSaving}
                        className="px-3 py-1.5 rounded bg-slate-700 text-white text-sm hover:bg-slate-800 disabled:opacity-50"
                      >
                        Reload knowledge base
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'diagnostics' && (
              <div className="mt-4 bg-white rounded-xl border border-slate-200 shadow-md p-5 space-y-3">
                <h3 className="text-lg font-semibold text-slate-800">Diagnostics v1</h3>
                <div className="text-sm text-slate-600">Policy-level diagnostics surface.</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Contract</div>
                    <div>contract: {String(diagnosticsEffectiveData?.active_contract?.contract_version ?? 'n/a')}</div>
                    <div>interaction policy: {String(diagnosticsEffectiveData?.active_contract?.interaction_mode_policy ?? 'n/a')}</div>
                  </div>
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Policies</div>
                    <div>informational narrowing: {diagnosticsEffectiveData?.policies?.informational_narrowing_enabled ? 'on' : 'off'}</div>
                    <div>mixed query handling: {diagnosticsEffectiveData?.policies?.mixed_query_handling_enabled ? 'on' : 'off'}</div>
                    <div>user correction protocol: {diagnosticsEffectiveData?.policies?.user_correction_protocol_enabled ? 'on' : 'off'}</div>
                    <div>first-turn richness: {diagnosticsEffectiveData?.policies?.first_turn_richness_policy_enabled ? 'on' : 'off'}</div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'routing' && filteredRoutingGroup && (
              <div className="mt-4 space-y-4">
                {routingPolicyGroup && Object.keys(routingPolicyGroup.params).length > 0 && (
                  <ConfigGroupPanel
                    groupKey="routing"
                    group={routingPolicyGroup}
                    onSave={saveConfigParam}
                    onReset={handleResetConfigParam}
                    isSaving={isSaving}
                    accentColor={GROUP_COLORS.routing ?? 'cyan'}
                  />
                )}
                {routingAdvancedGroup && Object.keys(routingAdvancedGroup.params).length > 0 && (
                  <details className="bg-white rounded-xl border border-slate-200 shadow-sm">
                    <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-700">Advanced Routing Controls</summary>
                    <div className="px-4 pb-4">
                      <ConfigGroupPanel
                        groupKey="routing-advanced"
                        group={routingAdvancedGroup}
                        onSave={saveConfigParam}
                        onReset={handleResetConfigParam}
                        isSaving={isSaving}
                        accentColor={GROUP_COLORS.routing ?? 'cyan'}
                      />
                    </div>
                  </details>
                )}
              </div>
            )}

            {activeTab === 'prompts' && (
              <div className="mt-4 bg-white rounded-xl border border-slate-200 p-5 shadow-md h-[70vh]">
                <PromptEditorPanel
                  prompts={prompts}
                  selectedPrompt={selectedPrompt}
                  promptError={promptError}
                  onSelect={loadPromptDetail}
                  onRetryLoad={retryPromptDetailLoad}
                  onSave={savePrompt}
                  onReset={resetPrompt}
                  onResetAll={resetAllPrompts}
                  isSaving={isSaving}
                />
              </div>
            )}

            {activeTab === 'compatibility' && (
              <div className="mt-4 space-y-4">
                {configData.groups.storage && (
                  <ConfigGroupPanel
                    groupKey="storage"
                    group={configData.groups.storage}
                    onSave={saveConfigParam}
                    onReset={handleResetConfigParam}
                    isSaving={isSaving}
                    accentColor={GROUP_COLORS.storage ?? 'amber'}
                  />
                )}
                <HistoryPanel history={history} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
