import React, { useEffect } from 'react';

import { useAgents } from '../../hooks/useAgents';

const MODES: Array<{ key: 'full_multiagent' | 'hybrid' | 'legacy_adaptive'; label: string }> = [
  { key: 'full_multiagent', label: 'full_multiagent' },
  { key: 'hybrid', label: 'hybrid' },
  { key: 'legacy_adaptive', label: 'legacy_adaptive' },
];

export const OrchestratorTab: React.FC = () => {
  const {
    orchestratorConfig,
    isLoading,
    isSaving,
    error,
    successMessage,
    loadOrchestratorConfig,
    loadAgentsStatus,
    setPipelineMode,
  } = useAgents();

  useEffect(() => {
    void loadOrchestratorConfig();
    void loadAgentsStatus();
  }, [loadAgentsStatus, loadOrchestratorConfig]);

  const current = orchestratorConfig?.pipeline_mode;

  return (
    <div className="mt-4 space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">🎭 Оркестратор</h3>
        {error && <p className="mt-2 text-xs text-rose-500">{error}</p>}
        {successMessage && <p className="mt-2 text-xs text-emerald-500">{successMessage}</p>}

        <div className="mt-3 flex flex-wrap gap-2">
          {MODES.map((mode) => (
            <button
              key={mode.key}
              type="button"
              disabled={isSaving || isLoading}
              onClick={() => {
                if (current === mode.key) return;
                void setPipelineMode(mode.key);
              }}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                current === mode.key
                  ? 'border-indigo-500 bg-indigo-100 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-900/40 dark:text-indigo-300'
                  : 'border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <div className="mt-3 text-xs text-slate-600 dark:text-slate-300">
          pipeline_version: <span className="font-mono">{orchestratorConfig?.pipeline_version ?? '—'}</span>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Состояние агентных флагов</h4>
        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
          {Object.entries(orchestratorConfig?.agents_enabled ?? {}).map(([agentId, enabled]) => (
            <div key={agentId} className="rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
              <span className="font-mono text-slate-700 dark:text-slate-200">{agentId}</span>
              <span
                className={`ml-2 rounded px-1.5 py-0.5 ${
                  enabled
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300'
                }`}
              >
                {enabled ? 'enabled' : 'disabled'}
              </span>
            </div>
          ))}
          {Object.keys(orchestratorConfig?.agents_enabled ?? {}).length === 0 && (
            <p className="text-xs text-slate-500">Нет данных.</p>
          )}
        </div>
      </section>
    </div>
  );
};
