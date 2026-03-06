// components/admin/ConfigGroupPanel.tsx

import React, { useState, useEffect } from 'react';
import type { ConfigGroup } from '../../types/admin.types';

interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
  currentLLMModel?: string; // для блокировки температуры при reasoning-моделях
}

// Reasoning-модели не поддерживают температуру
const REASONING_PREFIXES = ['gpt-5', 'o1', 'o3', 'o4'];
const isReasoningModel = (model: string) =>
  REASONING_PREFIXES.some((p) => model.startsWith(p));

export const ConfigGroupPanel: React.FC<Props> = ({
  groupKey: _groupKey,
  group,
  onSave,
  onReset,
  isSaving,
  currentLLMModel = '',
}) => {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    const init: Record<string, unknown> = {};
    Object.entries(group.params).forEach(([key, param]) => {
      init[key] = param.value;
    });
    setDrafts(init);
    setDirtyKeys(new Set());
  }, [group]);

  const handleChange = (key: string, value: unknown) => {
    setDrafts((prev) => ({ ...prev, [key]: value }));
    setDirtyKeys((prev) => new Set(prev).add(key));
  };

  const handleSave = async (key: string) => {
    await onSave(key, drafts[key]);
    setDirtyKeys((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  };

  const handleSaveAll = async () => {
    for (const key of Array.from(dirtyKeys)) {
      await onSave(key, drafts[key]);
    }
    setDirtyKeys(new Set());
  };

  const renderInput = (key: string, param: ConfigGroup['params'][string]) => {
    const draft = drafts[key];
    const isTemperatureBlocked =
      key === 'LLM_TEMPERATURE' && isReasoningModel(currentLLMModel);

    const baseClass =
      'w-full px-3 py-1.5 rounded border text-sm ' +
      (param.is_overridden && !dirtyKeys.has(key)
        ? 'border-amber-400 bg-amber-50'
        : 'border-gray-300 bg-white');

    if (isTemperatureBlocked) {
      return (
        <div className="flex items-center gap-2">
          <input
            className={`${baseClass} opacity-40 cursor-not-allowed`}
            value={String(draft)}
            disabled
          />
          <span className="text-xs text-gray-400 italic">
            н/п для reasoning-модели
          </span>
        </div>
      );
    }

    if (param.type === 'bool') {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(draft)}
            onChange={(e) => handleChange(key, e.target.checked)}
            className="w-4 h-4 rounded accent-blue-600"
          />
          <span className="text-sm text-gray-600">
            {Boolean(draft) ? 'Включено' : 'Выключено'}
          </span>
        </label>
      );
    }

    if (param.type === 'select' && param.options) {
      return (
        <select
          className={baseClass}
          value={String(draft)}
          onChange={(e) => handleChange(key, e.target.value)}
        >
          {param.options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );
    }

    if (param.type === 'int' || param.type === 'float') {
      return (
        <div className="flex items-center gap-2">
          <input
            type="number"
            className={baseClass}
            value={String(draft)}
            min={param.min}
            max={param.max}
            step={param.type === 'float' ? 0.05 : 1}
            onChange={(e) =>
              handleChange(
                key,
                param.type === 'float'
                  ? parseFloat(e.target.value)
                  : parseInt(e.target.value, 10)
              )
            }
          />
          <span className="text-xs text-gray-400 whitespace-nowrap">
            [{param.min} – {param.max}]
          </span>
        </div>
      );
    }

    return (
      <input
        type="text"
        className={baseClass}
        value={String(draft)}
        onChange={(e) => handleChange(key, e.target.value)}
      />
    );
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      {/* Заголовок группы */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-gray-800 text-base">{group.label}</h3>
        <div className="flex gap-2">
          {dirtyKeys.size > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={isSaving}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Сохранить все ({dirtyKeys.size})
            </button>
          )}
          <button
            onClick={() => onReset('__all__')}
            disabled={isSaving}
            className="px-3 py-1 bg-gray-100 text-gray-600 rounded text-sm hover:bg-gray-200 disabled:opacity-50"
          >
            ↩ Сбросить группу
          </button>
        </div>
      </div>

      {/* Список параметров */}
      <div className="space-y-4">
        {Object.entries(group.params).map(([key, param]) => (
          <div key={key} className="grid grid-cols-[1fr_auto] gap-x-3 items-start">
            {/* Левая колонка: лейбл + инпут + подсказки */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <label className="text-sm font-medium text-gray-700">
                  {param.label}
                </label>
                {param.is_overridden && !dirtyKeys.has(key) && (
                  <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                    override
                  </span>
                )}
                {dirtyKeys.has(key) && (
                  <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                    изменено
                  </span>
                )}
              </div>
              {renderInput(key, param)}
              {param.note && (
                <p className="text-xs text-gray-400 mt-1 italic">{param.note}</p>
              )}
              {param.is_overridden && (
                <p className="text-xs text-gray-400 mt-0.5">
                  Дефолт:{' '}
                  <span className="font-mono">{String(param.default)}</span>
                </p>
              )}
            </div>

            {/* Правая колонка: кнопки */}
            <div className="flex flex-col gap-1 pt-6">
              {dirtyKeys.has(key) && (
                <button
                  onClick={() => handleSave(key)}
                  disabled={isSaving}
                  className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50"
                >
                  ✓
                </button>
              )}
              {param.is_overridden && (
                <button
                  onClick={() => onReset(key)}
                  disabled={isSaving}
                  className="px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs hover:bg-gray-200 disabled:opacity-50"
                  title="Сбросить к дефолту"
                >
                  ↩
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
