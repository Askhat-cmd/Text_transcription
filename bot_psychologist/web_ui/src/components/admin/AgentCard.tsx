import React from 'react';

import type { AgentStatus } from '../../types/admin.types';

interface Props {
  agent: AgentStatus;
  isSaving: boolean;
  onToggle: (enabled: boolean) => void;
}

export const AgentCard: React.FC<Props> = ({ agent, isSaving, onToggle }) => {
  const errorPct = `${(agent.error_rate * 100).toFixed(1)}%`;

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800 dark:text-slate-100">{agent.id}</h4>
        <span
          className={`rounded px-2 py-0.5 text-[11px] font-medium ${
            agent.enabled
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
              : 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300'
          }`}
        >
          {agent.enabled ? 'enabled' : 'disabled'}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-300">
        <div>calls: <b>{agent.call_count}</b></div>
        <div>avg: <b>{agent.avg_latency_ms}ms</b></div>
        <div>errors: <b>{agent.error_count}</b></div>
        <div>error rate: <b>{errorPct}</b></div>
      </div>

      <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
        last run: {agent.last_run ? new Date(agent.last_run).toLocaleString('ru-RU') : '—'}
      </div>

      <div className="mt-3">
        <button
          type="button"
          disabled={isSaving}
          onClick={() => onToggle(!agent.enabled)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          {agent.enabled ? 'Disable' : 'Enable'}
        </button>
      </div>
    </article>
  );
};
