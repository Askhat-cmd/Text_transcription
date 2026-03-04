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

const SDChip: React.FC<{ level: string; count: number }> = ({ level, count }) => {
  const colors: Record<string, string> = {
    GREEN: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    YELLOW: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    RED: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  };
  const color = colors[level] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300';
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${color}`}>
      {level}: {count}
    </span>
  );
};

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
        <MetricCard label="Стоимость" value={`$${metrics.total_cost_usd}`} highlight={metrics.total_cost_usd > 0.1} />
        <div className="col-span-2 rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">SD уровни</p>
          <div className="flex gap-2 flex-wrap">
            <SDChip level="GREEN" count={metrics.sd_distribution.GREEN} />
            <SDChip level="YELLOW" count={metrics.sd_distribution.YELLOW} />
            <SDChip level="RED" count={metrics.sd_distribution.RED} />
          </div>
        </div>
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

