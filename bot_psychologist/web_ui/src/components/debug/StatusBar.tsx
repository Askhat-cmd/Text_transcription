import React from 'react';
import type { InlineTrace } from '../../types';

interface StatusBarProps {
  trace: InlineTrace;
}

const chipColors: Record<string, string> = {
  amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  violet: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300',
  sky: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
  teal: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300',
  red: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  orange: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  green: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

function sdColor(level?: string | null) {
  const normalized = (level || '').toUpperCase();
  if (normalized === 'GREEN') return 'green';
  if (normalized === 'YELLOW') return 'amber';
  if (normalized === 'RED') return 'red';
  return 'slate';
}

export const StatusBar: React.FC<StatusBarProps> = ({ trace }) => {
  const anomalyCount = trace.anomalies?.length ?? 0;
  const hasError = trace.pipeline_error != null;
  const sdLevel = trace.sd_level || trace.sd_classification?.primary || '—';
  const mode = trace.recommended_mode || '—';
  const blocksAfterCap = trace.blocks_after_cap ?? trace.chunks_after_filter?.length ?? trace.chunks_after_sd_filter?.length ?? trace.chunks_retrieved?.length;
  const blockCap = trace.block_cap ?? '—';
  const semanticHits = trace.semantic_hits ?? trace.semantic_hits_detail?.length ?? 0;

  const chips = [
    trace.fast_path && { label: 'FAST PATH', color: 'amber', anchor: 'routing' },
    { label: `MODE: ${mode}`, color: 'slate', anchor: 'routing' },
    { label: `STATE: ${trace.user_state ?? '—'}`, color: 'violet', anchor: 'memory' },
    {
      label: `SD: ${sdLevel} · ${trace.sd_detail?.confidence?.toFixed?.(2) ?? trace.sd_classification?.confidence?.toFixed?.(2) ?? '—'}`,
      color: sdColor(sdLevel),
      anchor: 'sd',
    },
    {
      label: `CHUNKS: ${blocksAfterCap ?? '—'} / cap ${blockCap}`,
      color: 'sky',
      anchor: 'chunks',
    },
    { label: `HITS: ${semanticHits}`, color: 'teal', anchor: 'memory' },
    {
      label: `LLM: ${trace.total_duration_ms ? `${trace.total_duration_ms}ms` : '—'}`,
      color: 'slate',
      anchor: 'llm',
    },
    anomalyCount > 0 && {
      label: `WARN ${anomalyCount}`,
      color: hasError ? 'red' : 'orange',
      anchor: 'anomalies',
    },
  ].filter(Boolean) as Array<{ label: string; color: string; anchor: string }>;

  return (
    <div className="flex flex-wrap gap-1.5 px-3 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 rounded-t-lg">
      {chips.map((chip, i) => (
        <a
          key={`${chip.anchor}-${i}`}
          href={`#debug-${chip.anchor}`}
          className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full cursor-pointer hover:opacity-80 transition-opacity ${chipColors[chip.color]}`}
        >
          {chip.label}
        </a>
      ))}
    </div>
  );
};
