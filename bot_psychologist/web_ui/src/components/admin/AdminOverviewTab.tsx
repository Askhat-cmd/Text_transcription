import React, { useEffect, useMemo, useState } from 'react';

import { adminConfigService } from '../../services/adminConfig.service';
import type { OverviewData } from '../../types/admin.types';

const modeBadgeClass: Record<string, string> = {
  multiagent_only: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

export const AdminOverviewTab: React.FC = () => {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminConfigService.getOverview();
      setOverview(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadOverview();
  }, []);

  const totals = useMemo(() => {
    if (!overview) return { calls: 0, errors: 0 };
    return overview.agents.reduce(
      (acc, item) => ({ calls: acc.calls + (item.calls || 0), errors: acc.errors + (item.errors || 0) }),
      { calls: 0, errors: 0 },
    );
  }, [overview]);
  const effectiveMode = overview?.pipeline_mode ?? 'multiagent_only';

  return (
    <div className="mt-4 space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">Обзор мультиагентного runtime</h3>
          <button
            type="button"
            onClick={() => void loadOverview()}
            className="ml-auto rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Обновить
          </button>
        </div>

        {error && <p className="mt-2 text-xs text-rose-500">{error}</p>}
        {isLoading && <p className="mt-2 text-xs text-slate-500">Загрузка...</p>}

        {overview && (
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="text-xs text-slate-500">Pipeline mode</div>
              <div className="mt-1">
                <span className={`rounded border px-2 py-0.5 text-xs font-medium ${modeBadgeClass[effectiveMode || ''] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                  {effectiveMode}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-500">entrypoint: {overview.runtime_entrypoint ?? 'multiagent_adapter'}</div>
              <div className="mt-1 text-xs text-slate-500">legacy fallback: disabled</div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="text-xs text-slate-500">Агенты</div>
              <div className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100">{overview.agents.length}</div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="text-xs text-slate-500">Calls</div>
              <div className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100">{totals.calls}</div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="text-xs text-slate-500">Errors</div>
              <div className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100">{totals.errors}</div>
            </div>
          </div>
        )}
      </section>

      {overview && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Последние трассы агентов</h4>
          <div className="mt-3 space-y-2">
            {overview.recent_traces.map((trace, idx) => (
              <div key={`${trace.timestamp}-${idx}`} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-700 dark:text-slate-200">{trace.agent_id}</span>
                  <span className="text-slate-500">{trace.latency_ms}ms</span>
                  <span className="ml-auto text-slate-400">{trace.timestamp ? new Date(trace.timestamp).toLocaleString('ru-RU') : '—'}</span>
                </div>
                <p className="mt-1 text-slate-600 dark:text-slate-300">in: {trace.input_preview || '—'}</p>
                <p className="mt-1 text-slate-600 dark:text-slate-300">out: {trace.output_preview || '—'}</p>
                {trace.error && <p className="mt-1 text-rose-500">error: {trace.error}</p>}
              </div>
            ))}
            {overview.recent_traces.length === 0 && <p className="text-xs text-slate-500">Нет трасс.</p>}
          </div>
        </section>
      )}
    </div>
  );
};
