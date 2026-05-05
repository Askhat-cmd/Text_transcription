import React, { useEffect } from 'react';

import { useOrchestrator } from '../../hooks/useOrchestrator';

const MODES: Array<{ key: 'multiagent_only' | 'full_multiagent'; label: string }> = [
  { key: 'multiagent_only', label: 'multiagent_only' },
  { key: 'full_multiagent', label: 'full_multiagent (alias)' },
];

export const OrchestratorTab: React.FC = () => {
  const {
    orchestratorConfig,
    isLoading,
    isSaving,
    error,
    successMessage,
    loadOrchestratorConfig,
    setPipelineMode,
  } = useOrchestrator();

  useEffect(() => {
    void loadOrchestratorConfig();
  }, [loadOrchestratorConfig]);

  const current = orchestratorConfig?.pipeline_mode ?? 'multiagent_only';
  const runtimeEntrypoint = orchestratorConfig?.runtime_entrypoint ?? 'multiagent_adapter';
  const legacy = orchestratorConfig?.legacy as Record<string, unknown> | undefined;

  return (
    <div className="mt-4 space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">Оркестратор</h3>
        {error && <p className="mt-2 text-xs text-rose-500">{error}</p>}
        {successMessage && <p className="mt-2 text-xs text-emerald-500">{successMessage}</p>}

        <div className="mt-3 flex flex-wrap gap-2">
          {MODES.map((mode) => (
            <button
              key={mode.key}
              type="button"
              disabled={isSaving || isLoading}
              onClick={() => {
                void setPipelineMode(mode.key);
              }}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                current === 'multiagent_only'
                  ? 'border-emerald-500 bg-emerald-100 text-emerald-700 dark:border-emerald-400 dark:bg-emerald-900/40 dark:text-emerald-300'
                  : 'border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <div className="mt-3 text-xs text-slate-600 dark:text-slate-300">
          active_runtime: <span className="font-mono">{orchestratorConfig?.active_runtime ?? 'multiagent'}</span>
        </div>
        <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
          runtime_entrypoint: <span className="font-mono">{runtimeEntrypoint}</span>
        </div>
        <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
          pipeline_mode: <span className="font-mono">{current}</span> <span className="text-slate-400">(read-only)</span>
        </div>
        <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
          pipeline_version: <span className="font-mono">{orchestratorConfig?.pipeline_version ?? 'multiagent_v1'}</span>
        </div>

        <div className="mt-2 rounded border border-slate-200 bg-slate-50 p-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          <div className="font-medium">legacy status</div>
          <div className="font-mono">fallback_enabled: {String(legacy?.fallback_enabled ?? false)}</div>
          <div className="font-mono">cascade_status: {String(legacy?.cascade_status ?? 'deprecated_retained_for_purge')}</div>
          <div className="font-mono">purge_planned_prd: {String(legacy?.purge_planned_prd ?? 'PRD-041')}</div>
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
