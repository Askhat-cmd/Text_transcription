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
  | 'trace'
  | 'compatibility';

const TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'llm',       label: '🤖 LLM',       hoverColor: 'hover:bg-violet-500/20' },
  { key: 'retrieval', label: '🔍 Retrieval',  hoverColor: 'hover:bg-blue-500/20'   },
  { key: 'diagnostics', label: '🩺 Diagnostics', hoverColor: 'hover:bg-teal-500/20' },
  { key: 'routing',   label: '🧭 Routing', hoverColor: 'hover:bg-cyan-500/20'  },
  { key: 'memory',    label: '🧠 Память',     hoverColor: 'hover:bg-emerald-500/20'},
  { key: 'prompts',   label: '🧩 Prompts',     hoverColor: 'hover:bg-rose-500/20'   },
  { key: 'runtime',   label: '⚙️ Runtime',    hoverColor: 'hover:bg-slate-500/20'  },
  { key: 'trace',   label: '🧪 Trace / Debug',    hoverColor: 'hover:bg-indigo-500/20' },
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
    isLoading, isSaving, error, promptError, successMessage,
    clearError, loadConfig, loadPrompts, loadPromptDetail,
    retryPromptDetailLoad,
    loadStatus, reloadKnowledgeBase,
    saveConfigParam, resetConfigParam, resetAllConfig,
    savePrompt, resetPrompt, resetAllPrompts,
    exportOverrides, importOverrides,
  } = useAdminConfig();

  useEffect(() => {
    if (apiKey) localStorage.setItem('devApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => { loadConfig(); loadPrompts(); loadStatus(); }, []);

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

  const paramValue = (group: any, key: string): string => {
    if (!group?.params?.[key]) return 'n/a';
    const value = group.params[key].value;
    if (typeof value === 'boolean') return value ? 'on' : 'off';
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
              <button
                onClick={() => setShowCompatibility((prev) => !prev)}
                className={`px-3 py-1.5 border rounded text-sm transition-colors ${
                  showCompatibility
                    ? 'border-amber-400 text-amber-300 hover:bg-amber-500/20'
                    : 'border-slate-500 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {showCompatibility ? 'Скрыть Compatibility' : 'Показать Compatibility'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tabs: тёмная полоса ── */}
      <div className="bg-slate-800 px-6 shadow-md">
        <div className="max-w-6xl mx-auto flex gap-1">
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
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                    <h3 className="font-semibold text-slate-800 mb-3">Статус системы</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                      <div>Режим данных: <span className="font-medium">{statusData.data_source}</span></div>
                      <div>Блоков в памяти: <span className="font-medium">{statusData.blocks_loaded}</span></div>
                      <div>DEGRADED_MODE: <span className="font-medium">{statusData.degraded_mode ? 'Активен' : 'ОК'}</span></div>
                      <div>Версия: <span className="font-medium">{statusData.version}</span></div>
                    </div>
                    {statusData.feature_flags && (
                      <div className="mt-3 border-t border-slate-200 pt-3">
                        <h4 className="font-medium text-slate-700 mb-2">Feature Flags</h4>
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
                  Операционная поверхность для диагностики поведения Neo runtime.
                  SD/user-level legacy контролы убраны из primary tabs.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Interaction Model</div>
                    <div className="text-slate-600 mt-1">nervous_system_state • request_function • informational narrowing</div>
                  </div>
                  <div className="rounded border border-slate-200 p-3">
                    <div className="font-medium text-slate-700">Routing Taxonomy</div>
                    <div className="text-slate-600 mt-1">{ROUTE_TAXONOMY.join(' • ')}</div>
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
                <ConfigGroupPanel
                  groupKey="routing"
                  group={filteredRoutingGroup}
                  onSave={saveConfigParam}
                  onReset={handleResetConfigParam}
                  isSaving={isSaving}
                  accentColor={GROUP_COLORS.routing ?? 'cyan'}
                />
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

            {activeTab === 'trace' && (
              <div className="mt-4">
                <div className="bg-white rounded-xl border border-slate-200 shadow-md p-5 space-y-2">
                  <h3 className="text-lg font-semibold text-slate-800">Trace / Debug</h3>
                  <p className="text-sm text-slate-600">
                    Трейс запроса показывается в карточке ответа веб-UI. Здесь фиксируется
                    диагностический срез по runtime/status для операторской проверки.
                  </p>
                  <div className="text-sm text-slate-700">
                    Последний status: {statusData ? `${statusData.version} • ${statusData.data_source}` : 'n/a'}
                  </div>
                </div>
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
