import React, { useEffect, useMemo, useState } from 'react';

import { useAgentStatus } from '../../hooks/useAgentStatus';
import { useAgentLLMConfig } from '../../hooks/useAgentLLMConfig';
import { useThreads } from '../../hooks/useThreads';
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
    isLoading,
    isSaving,
    error,
    successMessage,
    loadAgentsStatus,
    toggleAgent,
  } = useAgentStatus();
  const {
    data: llmConfig,
    isLoading: llmLoading,
    isSaving: llmSaving,
    error: llmError,
    setModel,
    resetModel,
  } = useAgentLLMConfig();
  const {
    agentTraces,
    loadAgentTraces,
  } = useThreads();

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
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">🧠 Модели агентов</h4>
          {(llmLoading || llmSaving) && (
            <span className="ml-auto text-xs text-slate-500">Обновление...</span>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Изменения применяются к следующему запросу без перезапуска сервера.
        </p>
        {llmError && <p className="mt-2 text-xs text-rose-500">{llmError}</p>}
        {llmConfig && (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-left dark:border-slate-700">
                  <th className="px-2 py-2 font-semibold text-slate-700 dark:text-slate-200">Агент</th>
                  <th className="px-2 py-2 font-semibold text-slate-700 dark:text-slate-200">Активная модель</th>
                  <th className="px-2 py-2 font-semibold text-slate-700 dark:text-slate-200">Дефолт</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody>
                {Object.entries(llmConfig.agents).map(([agentId, cfg]) => (
                  <tr key={agentId} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-2 py-2 align-middle">
                      <code className="text-slate-700 dark:text-slate-200">{agentId}</code>
                    </td>
                    <td className="px-2 py-2 align-middle">
                      <div className="flex items-center gap-2">
                        <select
                          value={cfg.model}
                          onChange={(e) => {
                            void setModel(agentId, e.target.value);
                          }}
                          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                          disabled={llmSaving}
                        >
                          {llmConfig.allowed_models.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                        {cfg.is_overridden && (
                          <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                            изменено
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-2 align-middle">
                      <code className="text-slate-500 dark:text-slate-400">{cfg.default_model}</code>
                    </td>
                    <td className="px-2 py-2 align-middle">
                      {cfg.is_overridden && (
                        <button
                          type="button"
                          className="rounded border border-slate-300 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                          onClick={() => {
                            void resetModel(agentId);
                          }}
                          disabled={llmSaving}
                          title="Вернуть к дефолту"
                        >
                          ↩ Сброс
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

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
