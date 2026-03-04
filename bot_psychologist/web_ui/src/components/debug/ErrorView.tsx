import React from 'react';
import type { PipelineError } from '../../types/api.types';

export const ErrorView: React.FC<{ error: PipelineError }> = ({ error }) => (
  <div className="rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 px-4 py-3 mt-2">
    <div className="flex items-center gap-2 mb-2">
      <span className="text-red-600 dark:text-red-400 font-bold text-xs uppercase">
        Pipeline Error
      </span>
      <code className="text-[10px] font-mono bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 px-1.5 py-0.5 rounded">
        {error.stage}
      </code>
    </div>
    <p className="text-[11px] text-red-800 dark:text-red-300 font-mono mb-1">
      {error.exception_type}: {error.message}
    </p>
    {error.partial_trace_available && (
      <p className="text-[10px] text-red-500 dark:text-red-400">
        Partial trace available - data shown above
      </p>
    )}
  </div>
);


