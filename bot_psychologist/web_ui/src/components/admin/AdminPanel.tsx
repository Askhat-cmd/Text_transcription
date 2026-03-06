// components/admin/AdminPanel.tsx
// Главный компонент Admin Config Panel. Подключается к роутингу web_ui.

import React, { useState, useEffect, useRef } from 'react';
import { useAdminConfig } from '../../hooks/useAdminConfig';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { PromptEditorPanel } from './PromptEditorPanel';
import { HistoryPanel } from './HistoryPanel';
import type { HistoryEntry } from '../../types/admin.types';

type Tab = 'llm' | 'retrieval' | 'memory' | 'storage' | 'runtime' | 'prompts' | 'history';

const TABS: { key: Tab; label: string }[] = [
  { key: 'llm',       label: '🤖 LLM' },
  { key: 'retrieval', label: '🔍 Поиск' },
  { key: 'memory',    label: '🧠 Память' },
  { key: 'storage',   label: '🗄️ Хранилище' },
  { key: 'runtime',   label: '⚙️ Runtime' },
  { key: 'prompts',   label: '📝 Промты' },
  { key: 'history',   label: '🕐 История' },
];

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('llm');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData,
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
    savePrompt,
    resetPrompt,
    resetAllPrompts,
    exportOverrides,
    importOverrides,
  } = useAdminConfig();

  // Получаем текущее значение LLM_MODEL для блокировки температуры
  const currentLLMModel =
    (configData?.groups?.llm?.params?.LLM_MODEL?.value as string) ?? '';

  useEffect(() => {
    loadConfig();
    loadPrompts();
  }, []);

  useEffect(() => {
    if (activeTab === 'history') {
      import('../../services/adminConfig.service').then(({ adminConfigService }) => {
        adminConfigService.getHistory().then((data) => setHistory(data.history));
      });
    }
  }, [activeTab]);

  const handleResetConfigParam = async (key: string) => {
    if (key === '__all__') {
      await resetAllConfig();
    } else {
      await resetConfigParam(key);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await importOverrides(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              ⚙️ Admin Config Panel
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Горячее управление параметрами бота без рестарта сервера
            </p>
          </div>
          {/* Export / Import / Full Reset */}
          <div className="flex items-center gap-2">
            <button
              onClick={exportOverrides}
              className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              ↓ Экспорт
            </button>
            <label className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50 cursor-pointer">
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
                if (
                  window.confirm(
                    'Полный сброс: удалить ВСЕ overrides (и конфиг, и промты)?'
                  )
                ) {
                  const { adminConfigService } = await import(
                    '../../services/adminConfig.service'
                  );
                  await adminConfigService.resetAll();
                  await loadConfig();
                  await loadPrompts();
                }
              }}
              className="px-3 py-1.5 border border-red-200 rounded text-sm text-red-600 hover:bg-red-50"
            >
              🗑 Полный сброс
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="max-w-6xl mx-auto flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications */}
      <div className="max-w-6xl mx-auto px-6 pt-3">
        {error && (
          <div className="flex items-center justify-between px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
            <span>⚠ {error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">
              ✕
            </button>
          </div>
        )}
        {successMessage && (
          <div className="px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 mb-3">
            {successMessage}
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-6 pb-10">
        {isLoading && (
          <div className="text-center text-gray-400 py-12 text-sm">
            Загрузка...
          </div>
        )}

        {!isLoading && configData && (
          <>
            {/* ── Config tabs ── */}
            {(['llm', 'retrieval', 'memory', 'storage', 'runtime'] as const).includes(
              activeTab as any
            ) && (
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
                      currentLLMModel={currentLLMModel}
                    />
                  ))}
              </div>
            )}

            {/* ── Prompts tab ── */}
            {activeTab === 'prompts' && (
              <div className="mt-4 bg-white rounded-xl border border-gray-200 p-5 shadow-sm h-[70vh]">
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

            {/* ── History tab ── */}
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
