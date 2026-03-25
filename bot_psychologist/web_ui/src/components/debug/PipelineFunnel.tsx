import React from 'react';
import type { InlineTrace } from '../../types';

interface FunnelStage {
  label: string;
  count: number;
  color: string;
}

export const PipelineFunnel: React.FC<{ trace: InlineTrace }> = ({ trace }) => {
  const stages: FunnelStage[] = [
    { label: 'Initial', count: trace.blocks_initial ?? 0, color: 'bg-sky-400' },
    { label: 'To LLM', count: trace.blocks_after_cap ?? 0, color: 'bg-emerald-400' },
  ].filter((stage) => stage.count != null);

  const max = Math.max(...stages.map((stage) => stage.count), 1);

  return (
    <div className="mt-2 space-y-1">
      {stages.map((stage) => (
        <div key={stage.label} className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 w-20 shrink-0">{stage.label}</span>
          <div className="flex-1 h-2.5 rounded bg-slate-100 dark:bg-slate-700 overflow-hidden">
            <div
              className={`h-2.5 rounded ${stage.color} transition-all`}
              style={{ width: `${(stage.count / max) * 100}%` }}
            />
          </div>
          <span className="text-[11px] font-mono font-bold text-slate-600 dark:text-slate-300 w-6 text-right">
            {stage.count}
          </span>
        </div>
      ))}
      {trace.hybrid_query_preview && (
        <details className="mt-1">
          <summary className="cursor-pointer text-[10px] text-slate-400 select-none py-0.5">
            Hybrid query preview {'>'}
          </summary>
          <p className="mt-1 text-[10px] font-mono text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 rounded p-2 border border-slate-200 dark:border-slate-700 whitespace-pre-wrap">
            {trace.hybrid_query_preview}
          </p>
        </details>
      )}
    </div>
  );
};

