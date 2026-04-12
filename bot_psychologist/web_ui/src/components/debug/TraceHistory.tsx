import React, { useMemo } from 'react';
import { useSessionTrace } from '../../hooks/useSessionTrace';
import type { InlineTrace } from '../../types';

const formatMs = (value?: number | null) => (typeof value === 'number' ? `${value}ms` : '—');

const traceLabel = (trace: InlineTrace) => {
  const turn = trace.turn_number ?? '—';
  const mode = trace.recommended_mode ?? '—';
  const state = trace.user_state ?? '—';
  return `#${turn} · ${mode} · ${state}`;
};

export const TraceHistory: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const { traces } = useSessionTrace(sessionId);

  const ordered = useMemo(() => {
    const list = Array.isArray(traces) ? [...traces] : [];
    return list.sort((a, b) => (a.turn_number ?? 0) - (b.turn_number ?? 0));
  }, [traces]);

  if (!ordered.length) return null;

  return (
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
            {trace.fast_path && (
              <span className="text-[10px] text-amber-600 dark:text-amber-300">FAST</span>
            )}
            {trace.anomalies && trace.anomalies.length > 0 && (
              <span className="text-[10px] text-rose-600 dark:text-rose-300">
                Anom {trace.anomalies.length}
              </span>
            )}
          </div>
        ))}
      </div>
    </details>
  );
};

