import React, { useMemo } from 'react';
import { useSessionTrace } from '../../hooks/useSessionTrace';
import type { InlineTrace } from '../../types';

interface Props {
  sessionId?: string | null;
}

const formatMs = (value?: number | null) => (typeof value === 'number' ? `${value}ms` : '—');

const formatMoney = (value: number) => `$${value.toFixed(6)}`;

const traceLabel = (trace: InlineTrace) => {
  const turn = trace.turn_number ?? '—';
  const mode = trace.recommended_mode ?? '—';
  const state = trace.user_state ?? '—';
  return `#${turn} · ${mode} · ${state}`;
};

export const SessionTracePanel: React.FC<Props> = ({ sessionId }) => {
  const { metrics, traces } = useSessionTrace(sessionId);

  const ordered = useMemo(() => {
    const list = Array.isArray(traces) ? [...traces] : [];
    return list.sort((a, b) => (a.turn_number ?? 0) - (b.turn_number ?? 0));
  }, [traces]);

  const latestTrace = ordered.length > 0 ? ordered[ordered.length - 1] : null;
  const prevTrace = ordered.length > 1 ? ordered[ordered.length - 2] : null;

  const configSnapshot = latestTrace?.config_snapshot ?? null;
  const changedConfigKeys = useMemo(() => {
    if (!configSnapshot) {
      return [];
    }
    const prev = prevTrace?.config_snapshot ?? null;
    const keys: Array<keyof typeof configSnapshot> = [
      'conversation_history_depth',
      'max_context_size',
      'semantic_search_top_k',
      'fast_path_enabled',
      'rerank_enabled',
      'model_name',
    ];
    if (!prev) {
      return [];
    }
    return keys.filter((key) => prev[key] !== configSnapshot[key]);
  }, [configSnapshot, prevTrace]);

  if (!sessionId || !metrics || ordered.length === 0) {
    return null;
  }

  const configEntries: Array<[string, string | number | boolean]> = configSnapshot
    ? [
      ['CONVERSATION_HISTORY_DEPTH', configSnapshot.conversation_history_depth],
      ['MAX_CONTEXT_SIZE', configSnapshot.max_context_size],
      ['SEMANTIC_SEARCH_TOP_K', configSnapshot.semantic_search_top_k],
      ['FAST_PATH_ENABLED', configSnapshot.fast_path_enabled],
      ['RERANK_ENABLED', configSnapshot.rerank_enabled],
      ['MODEL_NAME', configSnapshot.model_name],
    ]
    : [];

  return (
    <section id="session-trace-panel" className="mt-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 p-4 space-y-3">
      <details>
        <summary className="cursor-pointer font-semibold text-slate-700 dark:text-slate-200 select-none">
          Session Trace Panel
        </summary>
        <div className="mt-3 space-y-3">
          <details open>
            <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
              Session Totals
            </summary>
            <div className="mt-2 grid grid-cols-2 md:grid-cols-5 gap-2">
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Prompt</p>
                <p className="font-semibold text-slate-700 dark:text-slate-200">{metrics.total_prompt_tokens.toLocaleString()}</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Completion</p>
                <p className="font-semibold text-slate-700 dark:text-slate-200">{metrics.total_completion_tokens.toLocaleString()}</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Total tokens</p>
                <p className="font-semibold text-amber-600 dark:text-amber-400">{metrics.total_tokens.toLocaleString()}</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Стоимость</p>
                <p className="font-semibold text-emerald-600 dark:text-emerald-400">{formatMoney(metrics.total_cost_usd)}</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Turns</p>
                <p className="font-semibold text-slate-700 dark:text-slate-200">{metrics.total_turns}</p>
              </div>
            </div>
          </details>

          <details>
            <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
              Session Dashboard
            </summary>
            <div className="mt-2 grid grid-cols-2 md:grid-cols-5 gap-2">
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Fast Path</p>
                <p className="font-semibold">{metrics.fast_path_pct}%</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Avg LLM</p>
                <p className="font-semibold">{metrics.avg_llm_time_ms}ms</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Max LLM</p>
                <p className="font-semibold">{metrics.max_llm_time_ms}ms</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Turns w/ anomalies</p>
                <p className="font-semibold">{metrics.turns_with_anomalies}</p>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Anomaly indices</p>
                <p className="font-semibold text-[11px]">
                  {metrics.anomaly_turns_indices.length ? metrics.anomaly_turns_indices.join(', ') : '—'}
                </p>
              </div>
            </div>
          </details>

          <details>
            <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
              Trace History
            </summary>
            <div className="mt-2 space-y-1">
              {ordered.map((trace, idx) => (
                <div
                  key={`${trace.turn_number ?? idx}`}
                  className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 bg-white dark:bg-slate-800"
                >
                  <span className="text-[11px] font-mono text-slate-600 dark:text-slate-300">
                    {traceLabel(trace)}
                  </span>
                  <span className="ml-auto text-[10px] text-slate-400">{formatMs(trace.total_duration_ms)}</span>
                  {trace.anomalies && trace.anomalies.filter((item) => item.severity !== 'info').length > 0 && (
                    <span className="text-[10px] text-rose-600 dark:text-rose-300">
                      Warn {trace.anomalies.filter((item) => item.severity !== 'info').length}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </details>

          {configSnapshot && (
            <details>
              <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
                Config Snapshot
              </summary>
              <div className="mt-2 space-y-2">
                <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2">
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide">Changed keys vs previous turn</p>
                  <p className="mt-1 text-[11px] text-slate-600 dark:text-slate-300">
                    {changedConfigKeys.length ? changedConfigKeys.join(', ') : 'Нет изменений'}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {configEntries.map(([label, value]) => (
                    <div key={label} className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                      <p className="text-[10px] text-slate-400 uppercase tracking-wide">{label}</p>
                      <p className="font-mono text-[11px] text-slate-700 dark:text-slate-300">
                        {String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          )}
        </div>
      </details>
    </section>
  );
};
