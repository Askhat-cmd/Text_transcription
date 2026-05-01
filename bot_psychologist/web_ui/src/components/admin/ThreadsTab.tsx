import React, { useEffect, useState } from 'react';

import { useAgents } from '../../hooks/useAgents';

export const ThreadsTab: React.FC = () => {
  const {
    threads,
    isLoading,
    isSaving,
    error,
    successMessage,
    loadThreads,
    deleteThread,
  } = useAgents();

  const [statusFilter, setStatusFilter] = useState<'active' | 'archived' | 'all'>('active');
  const [userFilter, setUserFilter] = useState('');

  useEffect(() => {
    void loadThreads(statusFilter, userFilter || undefined, 100);
  }, [loadThreads, statusFilter, userFilter]);

  return (
    <div className="mt-4 space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">🧵 Треды</h3>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as 'active' | 'archived' | 'all')}
            className="ml-auto rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          >
            <option value="active">active</option>
            <option value="archived">archived</option>
            <option value="all">all</option>
          </select>
          <input
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            placeholder="user_id фильтр"
            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          />
          <button
            type="button"
            onClick={() => void loadThreads(statusFilter, userFilter || undefined, 100)}
            className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Обновить
          </button>
        </div>

        {error && <p className="mt-2 text-xs text-rose-500">{error}</p>}
        {successMessage && <p className="mt-2 text-xs text-emerald-500">{successMessage}</p>}

        {isLoading ? (
          <p className="mt-3 text-sm text-slate-500">Загрузка...</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-xs text-slate-700 dark:text-slate-200">
              <thead>
                <tr className="border-b border-slate-200 text-left dark:border-slate-700">
                  <th className="pb-2 pr-3">User</th>
                  <th className="pb-2 pr-3">Thread</th>
                  <th className="pb-2 pr-3">Phase</th>
                  <th className="pb-2 pr-3">Mode</th>
                  <th className="pb-2 pr-3 text-right">Turns</th>
                  <th className="pb-2 pr-3 text-right">Loops</th>
                  <th className="pb-2 pr-3">Updated</th>
                  {statusFilter !== 'archived' && <th className="pb-2 text-right">Действие</th>}
                </tr>
              </thead>
              <tbody>
                {threads.map((thread) => (
                  <tr key={`${thread.user_id}-${thread.thread_id}`} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 pr-3 font-mono text-[11px]">{thread.user_id}</td>
                    <td className="py-2 pr-3 font-mono text-[11px]">{thread.thread_id?.slice(0, 10)}…</td>
                    <td className="py-2 pr-3">{thread.phase || thread.final_phase || '—'}</td>
                    <td className="py-2 pr-3">{thread.response_mode || '—'}</td>
                    <td className="py-2 pr-3 text-right">{thread.turn_count ?? '—'}</td>
                    <td className="py-2 pr-3 text-right">
                      {thread.open_loops_count !== undefined ? `${thread.open_loops_count}/${thread.closed_loops_count ?? 0}` : '—'}
                    </td>
                    <td className="py-2 pr-3 text-slate-500">
                      {thread.last_updated_at
                        ? new Date(thread.last_updated_at).toLocaleString('ru-RU')
                        : thread.archived_at
                          ? new Date(thread.archived_at).toLocaleString('ru-RU')
                          : '—'}
                    </td>
                    {statusFilter !== 'archived' && thread.status === 'active' && (
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          disabled={isSaving}
                          onClick={() => {
                            if (!window.confirm(`Удалить активный тред пользователя ${thread.user_id}?`)) return;
                            void deleteThread(thread.user_id);
                          }}
                          className="rounded px-2 py-0.5 text-xs text-rose-500 hover:bg-rose-50 disabled:opacity-50 dark:hover:bg-rose-900/30"
                        >
                          Удалить
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>

            {threads.length === 0 && (
              <p className="mt-2 text-xs text-slate-500">Нет тредов для выбранного фильтра.</p>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
