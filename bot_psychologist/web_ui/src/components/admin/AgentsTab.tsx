import React, { useEffect, useMemo, useState } from 'react';

import { useAgents } from '../../hooks/useAgents';
import type { AgentId } from '../../types/admin.types';
import { AgentCard } from './AgentCard';

const AGENT_OPTIONS: Array<{ value: AgentId | ''; label: string }> = [
  { value: '', label: 'Все агенты' },
  { value: 'state_analyzer', label: 'state_analyzer' },
  { value: 'thread_manager', label: 'thread_manager' },
  { value: 'memory_retrieval', label: 'memory_retrieval' },
  { value: 'writer', label: 'writer' },
  { value: 'validator', label: 'validator' },
];

export const AgentsTab: React.FC = () => {
  const {
    agents,
    agentTraces,
    isLoading,
    isSaving,
    error,
    successMessage,
    loadAgentsStatus,
    loadAgentTraces,
    toggleAgent,
  } = useAgents();

  const [traceAgentFilter, setTraceAgentFilter] = useState<AgentId | ''>('');

  useEffect(() => {
    void loadAgentsStatus();
    void loadAgentTraces({ limit: 50 });
  }, [loadAgentTraces, loadAgentsStatus]);

  useEffect(() => {
    void loadAgentTraces({ limit: 50, agent_id: traceAgentFilter || undefined });
  }, [loadAgentTraces, traceAgentFilter]);

  const sortedAgents = useMemo(() => [...agents].sort((a, b) => a.id.localeCompare(b.id)), [agents]);

  return (
    <div className="mt-4 space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">🤖 Статус агентов</h3>
          <button
            type="button"
            className="ml-auto rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
            onClick={() => {
              void loadAgentsStatus();
              void loadAgentTraces({ limit: 50, agent_id: traceAgentFilter || undefined });
            }}
          >
            Обновить
          </button>
        </div>
        {error && <p className="mt-2 text-xs text-rose-500">{error}</p>}
        {successMessage && <p className="mt-2 text-xs text-emerald-500">{successMessage}</p>}
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800">
          Загрузка...
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {sortedAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              isSaving={isSaving}
              onToggle={(enabled) => {
                void toggleAgent(agent.id, enabled);
              }}
            />
          ))}
          {sortedAgents.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300">
              Нет данных по агентам.
            </div>
          )}
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Последние трассы агентов</h4>
          <select
            value={traceAgentFilter}
            onChange={(e) => setTraceAgentFilter(e.target.value as AgentId | '')}
            className="ml-auto rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          >
            {AGENT_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div className="mt-3 space-y-2">
          {agentTraces.map((trace, idx) => (
            <div
              key={`${trace.request_id || 'req'}-${idx}`}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-slate-700 dark:text-slate-200">{trace.agent_id}</span>
                <span className="text-slate-500">{trace.latency_ms}ms</span>
                <span className="ml-auto text-slate-400">
                  {trace.timestamp ? new Date(trace.timestamp).toLocaleString('ru-RU') : '—'}
                </span>
              </div>
              <p className="mt-1 text-slate-600 dark:text-slate-300">
                in: {trace.input_preview || '—'}
              </p>
              <p className="mt-1 text-slate-600 dark:text-slate-300">
                out: {trace.output_preview || '—'}
              </p>
              {trace.error && <p className="mt-1 text-rose-500">error: {trace.error}</p>}
            </div>
          ))}
          {agentTraces.length === 0 && (
            <p className="text-xs text-slate-500">Нет трасс для выбранного фильтра.</p>
          )}
        </div>
      </section>
    </div>
  );
};
