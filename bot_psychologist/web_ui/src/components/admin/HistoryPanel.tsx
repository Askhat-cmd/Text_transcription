// components/admin/HistoryPanel.tsx
import React from 'react';
import type { HistoryEntry } from '../../types/admin.types';

interface Props { history: HistoryEntry[]; }

const TYPE_STYLES: Record<string, { label: string; cls: string }> = {
  config:       { label: 'config изменён', cls: 'bg-violet-100 text-violet-700' },
  config_reset: { label: 'config сброшен', cls: 'bg-gray-100   text-gray-600'   },
  prompt:       { label: 'промт изменён',  cls: 'bg-rose-100   text-rose-700'   },
  prompt_reset: { label: 'промт сброшен',  cls: 'bg-gray-100   text-gray-600'   },
};

export const HistoryPanel: React.FC<Props> = ({ history }) => {
  const sorted = [...history].reverse();

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
      {/* Шапка — indigo-градиент */}
      <div className="bg-gradient-to-r from-indigo-900 to-indigo-700 px-5 py-3">
        <h3 className="text-white font-semibold text-sm">🕐 История изменений</h3>
        <p className="text-indigo-300 text-xs mt-0.5">последние {history.length} записей</p>
      </div>

      {sorted.length === 0 ? (
        <div className="text-center text-gray-400 py-12 text-sm">
          История пуста — изменений ещё не было
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {sorted.map((entry, i) => {
            const style = TYPE_STYLES[entry.type] ?? {
              label: entry.type,
              cls: 'bg-gray-100 text-gray-600',
            };
            const ts = new Date(entry.timestamp).toLocaleString('ru-RU', {
              day: '2-digit', month: '2-digit', year: 'numeric',
              hour: '2-digit', minute: '2-digit', second: '2-digit',
            });
            return (
              <div
                key={i}
                className="flex items-start justify-between px-5 py-3.5
                           hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 px-2 py-0.5 rounded text-xs font-medium
                                   whitespace-nowrap ${style.cls}`}>
                    {style.label}
                  </span>
                  <div>
                    <p className="text-sm font-mono font-medium text-gray-800">
                      {entry.key}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      <span className="text-red-500 font-mono">{String(entry.old)}</span>
                      <span className="mx-1.5 text-gray-400">→</span>
                      <span className="text-emerald-600 font-mono">{String(entry.new)}</span>
                    </p>
                  </div>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap ml-4 mt-0.5">
                  {ts}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
