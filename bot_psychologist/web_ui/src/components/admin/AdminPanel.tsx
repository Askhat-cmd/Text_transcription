// components/admin/AdminPanel.tsx
// Главный компонент Admin Config Panel с новой цветовой схемой

import React, { useState, useEffect, useRef } from 'react';
import { useAdminConfig } from '../../hooks/useAdminConfig';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { PromptEditorPanel } from './PromptEditorPanel';
import { HistoryPanel } from './HistoryPanel';
import { GROUP_COLORS } from '../../constants/adminColors';
import type { HistoryEntry } from '../../types/admin.types';

type Tab =
  | 'llm'
  | 'retrieval'
  | 'diagnostics'
  | 'routing'
  | 'memory'
  | 'prompts'
  | 'runtime'
  | 'compatibility';

const TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'llm',       label: '🤖 LLM',       hoverColor: 'hover:bg-violet-500/20' },
  { key: 'retrieval', label: '🔍 Retrieval',  hoverColor: 'hover:bg-blue-500/20'   },
  { key: 'diagnostics', label: '🩺 Diagnostics', hoverColor: 'hover:bg-teal-500/20' },
  { key: 'routing',   label: '🧭 Routing', hoverColor: 'hover:bg-cyan-500/20'  },
  { key: 'memory',    label: '🧠 Память',     hoverColor: 'hover:bg-emerald-500/20'},
  { key: 'prompts',   label: '🧩 Prompts',     hoverColor: 'hover:bg-rose-500/20'   },
  { key: 'runtime',   label: '⚙️ Runtime',    hoverColor: 'hover:bg-slate-500/20'  },
  { key: 'compatibility',   label: '🧰 Compatibility',    hoverColor: 'hover:bg-amber-500/20' },
];

const DEPRECATED_ROUTING_KEYS = new Set([
  'SD_CLASSIFIER_ENABLED',
  'SD_CLASSIFIER_CONFIDENCE_THRESHOLD',
  'DECISION_GATE_RULE_THRESHOLD',
  'DECISION_GATE_LLM_ROUTER_ENABLED',
  'PROMPT_SD_OVERRIDES_BASE',
  'PROMPT_MODE_OVERRIDES_SD',
]);

const ROUTING_ADVANCED_KEYS = new Set([
  'FAST_DETECTOR_ENABLED',
  'FAST_DETECTOR_CONFIDENCE_THRESHOLD',
  'STATE_CLASSIFIER_ENABLED',
  'STATE_CLASSIFIER_CONFIDENCE_THRESHOLD',
]);

const ROUTE_TAXONOMY = [
  'safe_override',
  'regulate',
  'reflect',
  'practice',
  'inform',
  'contact_hold',
];

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('llm');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showCompatibility, setShowCompatibility] = useState(false);
  const [apiKey, setApiKey] = useState<string>(
    () => localStorage.getItem('devApiKey') || ''
  );
  const [showApiKey, setShowApiKey] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData, prompts, selectedPrompt,
    statusData,
    runtimeEffectiveData,
    diagnosticsEffectiveData,
    isLoading, isSaving, error, promptError, successMessage,
    clearError, loadConfig, loadPrompts, loadPromptDetail,
    retryPromptDetailLoad,
    loadRuntimeEffective,
    loadDiagnosticsEffective,
    loadStatus, reloadKnowledgeBase,
    saveConfigParam, resetConfigParam, resetAllConfig,
    savePrompt, resetPrompt, resetAllPrompts,
    exportOverrides, importOverrides,
  } = useAdminConfig();

  useEffect(() => {
    if (apiKey) localStorage.setItem('devApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => {
    loadConfig();
    loadPrompts();
    loadStatus();
    loadRuntimeEffective();
    loadDiagnosticsEffective();
  }, []);

  useEffect(() => {
    if (activeTab !== 'compatibility') return;
    import('../../services/adminConfig.service').then(({ adminConfigService }) => {
      adminConfigService.getHistory().then((data) => setHistory(data.history));
    });
  }, [activeTab]);

  useEffect(() => {
    if (!showCompatibility && activeTab === 'compatibility') {
      setActiveTab('runtime');
    }
  }, [showCompatibility, activeTab]);

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
  const retrievalGroup = configData?.groups?.retrieval;
  const memoryGroup = configData?.groups?.memory;
  const filteredRoutingGroup = routingGroup
    ? {
        ...routingGroup,
        params: Object.fromEntries(
          Object.entries(routingGroup.params).filter(([key]) => !DEPRECATED_ROUTING_KEYS.has(key))
        ),
      }
    : null;
  const routingPolicyGroup = filteredRoutingGroup
    ? {
        ...filteredRoutingGroup,
        params: Object.fromEntries(
          Object.entries(filteredRoutingGroup.params).filter(([key]) => !ROUTING_ADVANCED_KEYS.has(key))
        ),
      }
    : null;
  const routingAdvancedGroup = filteredRoutingGroup
    ? {
        ...filteredRoutingGroup,
        label: '⚙️ Advanced Routing Controls',
        params: Object.fromEntries(
          Object.entries(filteredRoutingGroup.params).filter(([key]) => ROUTING_ADVANCED_KEYS.has(key))
        ),
      }
    : null;

  const paramValue = (group: any, key: string): string => {
    if (!group?.params?.[key]) return 'n/a';
    const value = group.params[key].value;
    if (typeof value === 'boolean') return value ? 'on' : 'off';
    return String(value);
  };
  const routingValue = (key: string, fallback = 'n/a'): string => {
    const value = runtimeEffectiveData?.routing?.[key];
    if (typeof value === 'boolean') return value ? 'on' : 'off';
    if (value === undefined || value === null) return fallback;
    return String(value);
  };
  const visibleTabs = showCompatibility
    ? TABS
    : TABS.filter((tab) => tab.key !== 'compatibility');
  return (
    <div className="min-h-screen bg-slate-100">

      {/* ── Header: тёмный градиент ── */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-700 px-6 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col gap-3">
            {/* Верхняя строка: заголовок + API ключ */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">
                  ⚙️ Admin Config Panel
                </h1>
                <p className="text-sm text-slate-400 mt-0.5">
                  Горячее управление параметрами без рестарта сервера
                </p>
              </div>

              {/* API Key */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="dev-key-001"
                    className="w-48 px-3 py-1.5 bg-slate-800 border border-slate-600 rounded
                               text-sm text-slate-200 placeholder-slate-500
                               focus:outline-none focus:ring-2 focus:ring-violet-400"
                  />
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
                  >
                    {showApiKey ? '🙈' : '👁️'}
                  </button>
                </div>
                <span className={`text-xs px-2 py-1 rounded font-medium ${
                  apiKey
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {apiKey ? '✓' : '✕'}
                </span>
              </div>
            </div>

            {/* Нижняя строка: кнопки действий */}
            <div className="flex items-center gap-2">
              <button
                onClick={exportOverrides}
                className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300
                           hover:bg-slate-600 transition-colors"
              >
                ↓ Экспорт
              </button>
              <label className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300
                                 hover:bg-slate-600 transition-colors cursor-pointer">
                ↑ Импорт
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
                  if (!window.confirm('Полный сброс: удалить ВСЕ overrides (конфиг + промты)?')) return;
                  const { adminConfigService } = await import('../../services/adminConfig.service');
                  await adminConfigService.resetAll();
                  await loadConfig();
                  await loadPrompts();
                }}
                className="px-3 py-1.5 border border-red-500/40 rounded text-sm text-red-400
                           hover:bg-red-500/20 transition-colors"
              >
                🗑 Полный сброс
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tabs: тёмная полоса ── */}
      <div className="bg-slate-800 px-6 shadow-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <div className="flex gap-1">
            {visibleTabs.map((tab) => (
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
          <details className="relative">
            <summary className="list-none cursor-pointer px-3 py-1.5 text-xs border border-slate-600 rounded text-slate-300 hover:bg-slate-700">
              Advanced
            </summary>
            <div className="absolute right-0 mt-1 w-52 rounded border border-slate-700 bg-slate-900 p-2 shadow-lg z-20">
              <button
                onClick={() => setShowCompatibility((prev) => !prev)}
                className="w-full text-left text-xs text-slate-200 hover:bg-slate-800 rounded px-2 py-1"
              >
                {showCompatibility ? 'Hide Compatibility tab' : 'Show Compatibility tab'}
              </button>
            </div>
          </details>
        </div>
      </div>

      {/* ── Notifications ── */}
      <div className="max-w-6xl mx-auto px-6 pt-3">
        {error && (
          <div className="flex items-center justify-between px-4 py-3
                          bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
            <span>⚠ {error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">✕</button>
          </div>
        )}
        {successMessage && (
          <div className="px-4 py-3 bg-emerald-50 border border-emerald-200
                          rounded-lg text-sm text-emerald-700 mb-3">
            ✓ {successMessage}
          </div>
        )}
      </div>

      {/* ── Main content ── */}
      <div className="max-w-6xl mx-auto px-6 pb-10">
        {isLoading && (
          <div className="text-center text-slate-400 py-12 text-sm">Загрузка...</div>
        )}

        {!isLoading && configData && (
          <>
            {(['llm', 'retrieval', 'memory', 'runtime'] as const)
              .includes(activeTab as any) && (
              <div className="mt-4 space-y-4">
                {activeTab === 'retrieval' && retrievalGroup && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                    <h3 className="font-semibold text-slate-800 mb-2">Retrieval Pipeline (Neo)</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                      <div>Initial top-k: <span className="font-medium">{paramValue(retrievalGroup, 'TOP_K_BLOCKS')}</span></div>
                      <div>Min relevance: <span className="font-medium">{paramValue(retrievalGroup, 'MIN_RELEVANCE_SCORE')}</span></div>
                      <div>Rerank enabled: <span className="font-medium">{paramValue(retrievalGroup, 'VOYAGE_ENABLED')}</span></div>
                      <div>Rerank model/top-k: <span className="font-medium">{paramValue(retrievalGroup, 'VOYAGE_MODEL')} / {paramValue(retrievalGroup, 'VOYAGE_TOP_K')}</span></div>
                      <div>Final cap (high): <span className="font-medium">{paramValue(retrievalGroup, 'CONFIDENCE_CAP_HIGH')}</span></div>
                      <div>Data source: <span className="font-medium">{statusData?.data_source ?? 'n/a'}</span></div>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      Stage order: initial retrieval → rerank → confidence cap → final blocks to LLM.
                    </p>
                    {statusData?.degraded_mode && (
                      <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                        Degraded mode active: retrieval fallback policy is in effect.
                      </p>
                    )}
                  </div>
                )}
                {activeTab === 'memory' && memoryGroup && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                    <h3 className="font-semibold text-slate-800 mb-2">Memory Model v1.1</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                      <div>History depth: <span className="font-medium">{paramValue(memoryGroup, 'CONVERSATION_HISTORY_DEPTH')}</span></div>
                      <div>Max context: <span className="font-medium">{paramValue(memoryGroup, 'MAX_CONTEXT_SIZE')}</span></div>
                      <div>Semantic memory: <span className="font-medium">{paramValue(memoryGroup, 'ENABLE_SEMANTIC_MEMORY')}</span></div>
                      <div>Semantic top-k: <span className="font-medium">{paramValue(memoryGroup, 'SEMANTIC_SEARCH_TOP_K')}</span></div>
                      <div>Summary enabled: <span className="font-medium">{paramValue(memoryGroup, 'ENABLE_CONVERSATION_SUMMARY')}</span></div>
                      <div>Summary interval/max: <span className="font-medium">{paramValue(memoryGroup, 'SUMMARY_UPDATE_INTERVAL')} / {paramValue(memoryGroup, 'SUMMARY_MAX_CHARS')}</span></div>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      Snapshot schema v1.1 + staleness/fallback policy are runtime-managed and exposed via trace.
                    </p>
                  </div>
                )}
                {activeTab === 'runtime' && statusData && (
                  <div className="space-y-4">
                    <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                      <h3 className="font-semibold text-slate-800 mb-3">Effective Runtime Truth</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-600">
                        <div className="rounded border border-slate-200 p-3">
                          <div className="font-medium text-slate-700 mb-1">Schema / Versions</div>
                          <div>schema_version: <span className="font-medium">{runtimeEffectiveData?.schema_version ?? 'n/a'}</span></div>
                          <div>admin_schema_version: <span className="font-medium">{runtimeEffectiveData?.admin_schema_version ?? 'n/a'}</span></div>
                          <div>prompt_stack_version: <span className="font-medium">{runtimeEffectiveData?.prompt_stack_version ?? 'n/a'}</span></div>
                        </div>
                        <div className="rounded border border-slate-200 p-3">
                          <div className="font-medium text-slate-700 mb-1">Diagnostics / Routing</div>
                          <div>diagnostics contract: <span className="font-medium">{String(runtimeEffectiveData?.diagnostics?.contract ?? 'n/a')}</span></div>
                          <div>diagnostics enabled: <span className="font-medium">{String(runtimeEffectiveData?.diagnostics?.enabled ?? 'n/a')}</span></div>
                          <div>deterministic resolver: <span className="font-medium">{routingValue('deterministic_resolver_enabled')}</span></div>
                          <div>false-inform protection: <span className="font-medium">{routingValue('false_inform_protection_enabled')}</span></div>
                        </div>
                        <div className="rounded border border-slate-200 p-3">
                          <div className="font-medium text-slate-700 mb-1">Trace / Validation</div>
                          <div>trace available: <span className="font-medium">{runtimeEffectiveData?.trace?.available ? 'yes' : 'no'}</span></div>
                          <div>config valid: <span className="font-medium">{runtimeEffectiveData?.validation?.config_validation_status?.valid ? 'true' : 'false'}</span></div>
                          <div className="text-xs text-slate-500 mt-1">
                            Deep message-level diagnostics are available in developer trace inside chat.
                          </div>
                        </div>
                        <div className="rounded border border-slate-200 p-3">
                          <div className="font-medium text-slate-700 mb-1">Grouped Feature Flags</div>
                          <div className="space-y-1">
                            {Object.entries(runtimeEffectiveData?.feature_flags?.groups ?? {}).map(([groupName, flags]) => (
                              <div key={groupName}>
                                <span className="font-medium">{groupName}</span>: {Object.entries(flags).map(([flag, enabled]) => `${flag}=${enabled ? 'on' : 'off'}`).join(', ')}
                              </div>
                            ))}
                            {Object.keys(runtimeEffectiveData?.feature_flags?.groups ?? {}).length === 0 && (
                              <div>n/a</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                      <h3 className="font-semibold text-slate-800 mb-3">Системный статус</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                        <div>Режим данных: <span className="font-medium">{statusData.data_source}</span></div>
                        <div>Блоков в памяти: <span className="font-medium">{statusData.blocks_loaded}</span></div>
                        <div>DEGRADED_MODE: <span className="font-medium">{statusData.degraded_mode ? 'Активен' : 'ОК'}</span></div>
                        <div>Версия: <span className="font-medium">{statusData.version}</span></div>
                      </div>
                      {statusData.feature_flags && (
                        <div className="mt-3 border-t border-slate-200 pt-3">
                          <h4 className="font-medium text-slate-700 mb-2">Raw Feature Flags</h4>
                          <div className="grid grid-cols-2 gap-1 text-xs text-slate-600">
                            {Object.entries(statusData.feature_flags).map(([flag, enabled]) => (
                              <div key={flag}>
                                {flag}: <span className="font-medium">{enabled ? 'on' : 'off'}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="mt-3">
                        <button
                          onClick={reloadKnowledgeBase}
                          disabled={isSaving}
                          className="px-3 py-1.5 rounded bg-slate-700 text-white text-sm hover:bg-slate-800 disabled:opacity-50"
                        >
                          🔄 Перезагрузить базу знаний
                        </button>
                      </div>
                    </div>
                  </div>
                )}
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
              </div>
            )}


            {activeTab === 'diagnostics' && (
              <div className="mt-4 bg-white rounded-xl border border-slate-200 shadow-md p-5 space-y-3">
                <h3 className="text-lg font-semibold text-slate-800">Diagnostics v1</h3>
                <p className="text-sm text-slate-600">
                  System-level policy surface for diagnostics contract. No per-message snapshots are shown here.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Active Diagnostics Contract</div>
                    <div className="text-slate-600 mt-1 space-y-1">
                      <div>contract: <span className="font-medium">{String(diagnosticsEffectiveData?.active_contract?.contract_version ?? 'diagnostics-v1')}</span></div>
                      <div>interaction policy: <span className="font-medium">{String(diagnosticsEffectiveData?.active_contract?.interaction_mode_policy ?? 'system-level')}</span></div>
                      <div>nervous system taxonomy: <span className="font-medium">{String(diagnosticsEffectiveData?.active_contract?.nervous_system_taxonomy ?? 'n/a')}</span></div>
                      <div>request function taxonomy: <span className="font-medium">{String(diagnosticsEffectiveData?.active_contract?.request_function_taxonomy ?? 'n/a')}</span></div>
                    </div>
                  </div>
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Current Behavior Policies</div>
                    <div className="text-slate-600 mt-1 space-y-1">
                      <div>informational narrowing: <span className="font-medium">{diagnosticsEffectiveData?.policies?.informational_narrowing_enabled ? 'on' : 'off'}</span></div>
                      <div>mixed query handling: <span className="font-medium">{diagnosticsEffectiveData?.policies?.mixed_query_handling_enabled ? 'on' : 'off'}</span></div>
                      <div>user correction protocol: <span className="font-medium">{diagnosticsEffectiveData?.policies?.user_correction_protocol_enabled ? 'on' : 'off'}</span></div>
                      <div>first-turn richness: <span className="font-medium">{diagnosticsEffectiveData?.policies?.first_turn_richness_policy_enabled ? 'on' : 'off'}</span></div>
                    </div>
                  </div>
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Inform/Mixed/User Correction</div>
                    <div className="text-slate-600 mt-1">
                      Policies below are system-level controls. Detailed per-turn diagnostics are delegated
                      to developer trace in chat mode.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'routing' && filteredRoutingGroup && (
              <div className="mt-4 space-y-4">
                <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                  <h3 className="font-semibold text-slate-800 mb-2">Neo Route Taxonomy</h3>
                  <div className="text-sm text-slate-600">{ROUTE_TAXONOMY.join(' • ')}</div>
                  <p className="mt-2 text-xs text-slate-500">
                    Legacy Decision Gate and SD routing controls are moved out of primary routing surface.
                  </p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                  <h3 className="font-semibold text-slate-800 mb-2">Current Routing Policy</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-slate-600">
                    <div>deterministic resolver: <span className="font-medium">{routingValue('deterministic_resolver_enabled')}</span></div>
                    <div>false-inform protection: <span className="font-medium">{routingValue('false_inform_protection_enabled')}</span></div>
                    <div>curiosity decoupling: <span className="font-medium">{routingValue('curiosity_decoupling_enabled')}</span></div>
                    <div>practice trigger guard: <span className="font-medium">{routingValue('practice_trigger_guard_enabled')}</span></div>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 text-sm text-slate-600">
                    <div className="font-medium text-slate-700">False-Inform Protection</div>
                    <div className="mt-1">
                      Защита от неверного перехода в informational ветку: <span className="font-medium">{routingValue('false_inform_protection_enabled')}</span>
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 text-sm text-slate-600">
                    <div className="font-medium text-slate-700">Curiosity Decoupling</div>
                    <div className="mt-1">
                      `curious` больше не принуждает informational override.
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 text-sm text-slate-600">
                    <div className="font-medium text-slate-700">Practice Trigger Rules</div>
                    <div className="mt-1">
                      Practice route включается только при валидных диагностических сигналах и safety-приоритете.
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 text-sm text-slate-600">
                    <div className="font-medium text-slate-700">Safety Override Priority</div>
                    <div className="mt-1">
                      `safe_override` имеет приоритет над остальными route-ветками.
                    </div>
                  </div>
                </div>
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
                    <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-700">
                      Advanced Routing Controls
                    </summary>
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
              <div className="mt-4 bg-white rounded-xl border border-slate-200
                              p-5 shadow-md h-[70vh]">
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
                <div>
                  <HistoryPanel history={history} />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
