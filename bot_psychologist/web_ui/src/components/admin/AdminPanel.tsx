// components/admin/AdminPanel.tsx
// Главный компонент Admin Config Panel с новой цветовой схемой

import React, { useState, useEffect, useRef } from 'react';
import { useAdminConfig } from '../../hooks/useAdminConfig';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { PromptEditorPanel } from './PromptEditorPanel';
import { HistoryPanel } from './HistoryPanel';
import { GROUP_COLORS } from '../../constants/adminColors';
import type { HistoryEntry } from '../../types/admin.types';

type Tab = 'llm' | 'retrieval' | 'memory' | 'storage' | 'runtime' | 'prompts' | 'history';

const TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'llm',       label: '🤖 LLM',       hoverColor: 'hover:bg-violet-500/20' },
  { key: 'retrieval', label: '🔍 Поиск',      hoverColor: 'hover:bg-blue-500/20'   },
  { key: 'memory',    label: '🧠 Память',     hoverColor: 'hover:bg-emerald-500/20'},
  { key: 'storage',   label: '🗄️ Хранилище', hoverColor: 'hover:bg-amber-500/20'  },
  { key: 'runtime',   label: '⚙️ Runtime',    hoverColor: 'hover:bg-slate-500/20'  },
  { key: 'prompts',   label: '📝 Промты',     hoverColor: 'hover:bg-rose-500/20'   },
  { key: 'history',   label: '🕐 История',    hoverColor: 'hover:bg-indigo-500/20' },
];

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('llm');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [apiKey, setApiKey] = useState<string>(
    () => localStorage.getItem('devApiKey') || ''
  );
  const [showApiKey, setShowApiKey] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData, prompts, selectedPrompt,
    isLoading, isSaving, error, successMessage,
    clearError, loadConfig, loadPrompts, loadPromptDetail,
    saveConfigParam, resetConfigParam, resetAllConfig,
    savePrompt, resetPrompt, resetAllPrompts,
    exportOverrides, importOverrides,
  } = useAdminConfig();

  useEffect(() => {
    if (apiKey) localStorage.setItem('devApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => { loadConfig(); loadPrompts(); }, []);

  useEffect(() => {
    if (activeTab !== 'history') return;
    import('../../services/adminConfig.service').then(({ adminConfigService }) => {
      adminConfigService.getHistory().then((data) => setHistory(data.history));
    });
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
        <div className="max-w-6xl mx-auto flex gap-1">
          {TABS.map((tab) => (
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
            {(['llm', 'retrieval', 'memory', 'storage', 'runtime'] as const)
              .includes(activeTab as any) && (
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
              </div>
            )}

            {activeTab === 'prompts' && (
              <div className="mt-4 bg-white rounded-xl border border-slate-200
                              p-5 shadow-md h-[70vh]">
                <PromptEditorPanel
                  prompts={prompts}
                  selectedPrompt={selectedPrompt}
                  onSelect={loadPromptDetail}
                  onSave={savePrompt}
                  onReset={resetPrompt}
                  onResetAll={resetAllPrompts}
                  isSaving={isSaving}
                />
              </div>
            )}

            {activeTab === 'history' && (
              <div className="mt-4">
                <HistoryPanel history={history} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
