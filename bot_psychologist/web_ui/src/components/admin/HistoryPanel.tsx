// components/admin/HistoryPanel.tsx

import React from 'react';
import type { HistoryEntry } from '../../types/admin.types';

const typeLabel: Record<string, { text: string; color: string }> = {
  config:       { text: 'config изменён',  color: 'bg-blue-100 text-blue-700' },
  config_reset: { text: 'config сброшен',  color: 'bg-gray-100 text-gray-600' },
  prompt:       { text: 'промт изменён',   color: 'bg-amber-100 text-amber-700' },
  prompt_reset: { text: 'промт сброшен',   color: 'bg-gray-100 text-gray-600' },
};

interface Props {
  history: HistoryEntry[];
}

export const HistoryPanel: React.FC<Props> = ({ history }) => {
  const sorted = [...history].reverse(); // последние сверху

  if (sorted.length === 0) {
    return (
      <div className="text-center text-gray-400 text-sm py-12">
        История изменений пуста
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sorted.map((entry, i) => {
        const badge = typeLabel[entry.type] ?? {
          text: entry.type,
          color: 'bg-gray-100 text-gray-600',
        };
        return (
          <div
            key={i}
            className="flex items-start gap-3 px-4 py-3 bg-white rounded-lg border border-gray-100 hover:border-gray-200"
          >
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 mt-0.5 ${badge.color}`}
            >
              {badge.text}
            </span>
            <div className="flex-1 min-w-0">
              <span className="font-mono text-sm font-semibold text-gray-800">
                {entry.key}
              </span>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
                <span className="font-mono bg-red-50 text-red-600 px-1 rounded">
                  {String(entry.old)}
                </span>
                <span>→</span>
                <span className="font-mono bg-green-50 text-green-700 px-1 rounded">
                  {String(entry.new)}
                </span>
              </div>
            </div>
            <span className="text-xs text-gray-400 flex-shrink-0 whitespace-nowrap">
              {new Date(entry.timestamp).toLocaleString('ru-RU')}
            </span>
          </div>
        );
      })}
    </div>
  );
};
