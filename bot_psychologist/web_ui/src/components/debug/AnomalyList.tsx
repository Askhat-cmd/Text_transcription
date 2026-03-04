import React from 'react';
import type { InlineTrace } from '../../types';

const severityColors: Record<string, string> = {
  info: 'text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700',
  warn: 'text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700',
  error: 'text-red-700 dark:text-red-300 border-red-200 dark:border-red-700',
};

export const AnomalyList: React.FC<{ trace: InlineTrace }> = ({ trace }) => {
  const anomalies = trace.anomalies ?? [];
  if (anomalies.length === 0) {
    return (
      <p className="text-[11px] text-slate-400 px-2">Аномалий не обнаружено</p>
    );
  }

  return (
    <div className="space-y-2">
      {anomalies.map((item, idx) => {
        const color = severityColors[item.severity] || severityColors.info;
        const anchor = item.target ? `#debug-${item.target}` : undefined;
        return (
          <div
            key={`${item.code}-${idx}`}
            className={`rounded-lg border px-3 py-2 text-[11px] ${color}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono font-bold uppercase">{item.code}</span>
              <span className="text-[10px] uppercase tracking-wide">{item.severity}</span>
              {anchor && (
                <a
                  href={anchor}
                  className="ml-auto text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  перейти
                </a>
              )}
            </div>
            <p className="text-slate-700 dark:text-slate-300">{item.message}</p>
          </div>
        );
      })}
    </div>
  );
};
