import React from 'react';
import type { InlineTrace } from '../../types';

export const ConfigSnapshot: React.FC<{ trace: InlineTrace }> = ({ trace }) => {
  const snapshot = trace.config_snapshot;
  if (!snapshot) return null;

  const entries: Array<[string, string | number | boolean]> = [
    ['CONVERSATION_HISTORY_DEPTH', snapshot.conversation_history_depth],
    ['MAX_CONTEXT_SIZE', snapshot.max_context_size],
    ['SEMANTIC_SEARCH_TOP_K', snapshot.semantic_search_top_k],
    ['FAST_PATH_ENABLED', snapshot.fast_path_enabled],
    ['RERANK_ENABLED', snapshot.rerank_enabled],
    ['MODEL_NAME', snapshot.model_name],
  ];

  return (
    <details>
      <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
        Config Snapshot
      </summary>
      <div className="mt-2 grid grid-cols-2 gap-2">
        {entries.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">{label}</p>
            <p className="font-mono text-[11px] text-slate-700 dark:text-slate-300">
              {String(value)}
            </p>
          </div>
        ))}
      </div>
    </details>
  );
};

