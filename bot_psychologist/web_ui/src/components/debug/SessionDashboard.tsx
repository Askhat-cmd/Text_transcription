import React from 'react';
import { useSessionTrace } from '../../hooks/useSessionTrace';

interface MetricCardProps {
  label: string;
  value: string | number;
  highlight?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, highlight }) => (
  <div className={`rounded-lg bg-white dark:bg-slate-800 px-3 py-2 ${highlight ? 'border border-amber-300 dark:border-amber-700' : ''}`}>
    <p className="text-[10px] text-slate-400 uppercase tracking-wide">{label}</p>
    <p className={`font-semibold ${highlight ? 'text-amber-600 dark:text-amber-300' : 'text-slate-700 dark:text-slate-200'}`}>{value}</p>
  </div>
);

export const SessionDashboard: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const { metrics } = useSessionTrace(sessionId);

  if (!metrics) return null;

  return (
    <details>
      <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
        Session Dashboard
      </summary>
      <div className="mt-2 grid grid-cols-3 gap-2">
        <MetricCard label="Turns" value={metrics.total_turns} />
        <MetricCard label="Fast Path" value={`${metrics.fast_path_pct}%`} />
        <MetricCard label="Avg LLM" value={`${metrics.avg_llm_time_ms}ms`} />
        <MetricCard label="Max LLM" value={`${metrics.max_llm_time_ms}ms`} />
        <MetricCard label="Стоимость" value={`$${metrics.total_cost_usd}`} highlight={metrics.total_cost_usd > 0.1} />
        {metrics.turns_with_anomalies > 0 && (
          <MetricCard
            label="Turns with anomalies"
            value={metrics.turns_with_anomalies}
            highlight
          />
        )}
      </div>
    </details>
  );
};

