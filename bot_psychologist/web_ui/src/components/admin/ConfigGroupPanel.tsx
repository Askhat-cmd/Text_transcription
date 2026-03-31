// components/admin/ConfigGroupPanel.tsx
import React, { useState, useEffect } from 'react';
import type { ConfigGroup } from '../../types/admin.types';
import { ACCENT_CLASSES, type AccentKey } from '../../constants/adminColors';

interface Props {
  groupKey: string;
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  isSaving: boolean;
  accentColor?: string; // 'violet' | 'blue' | 'emerald' | 'amber' | 'slate'
}

const REASONING_PREFIXES = ['gpt-5', 'o1', 'o3', 'o4'];
const isReasoningModel = (model: string): boolean =>
  REASONING_PREFIXES.some((p) => model.startsWith(p));

export const ConfigGroupPanel: React.FC<Props> = ({
  groupKey: _groupKey,
  group,
  onSave,
  onReset,
  isSaving,
  accentColor = 'blue',
}) => {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set());

  const accentKey: AccentKey =
    accentColor in ACCENT_CLASSES ? (accentColor as AccentKey) : 'blue';
  const accent = ACCENT_CLASSES[accentKey];

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

    // FIX B1: читаем из локального drafts, не из внешнего prop
    const isTemperatureBlocked =
      key === 'LLM_TEMPERATURE' &&
      isReasoningModel(String(drafts['LLM_MODEL'] ?? ''));

    const baseClass =
      'w-full px-3 py-1.5 rounded border text-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ' +
      (param.is_overridden && !dirtyKeys.has(key)
        ? `${accent.override} ${accent.ring}`
        : `border-gray-200 bg-white ${accent.ring}`);

    if (isTemperatureBlocked) {
      return (
        <div className="flex items-center gap-2">
          <input
            className={`${baseClass} opacity-40 cursor-not-allowed`}
            value={String(draft)}
            disabled
          />
          <span className="text-xs text-gray-400 italic whitespace-nowrap">
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
            className="w-4 h-4 rounded"
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
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    }

    if (param.type === 'int_or_null') {
      const isUnlimited = draft === null;
      const fallbackValue = Number(param.default ?? param.min ?? 1024);
      return (
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={isUnlimited}
              onChange={(e) =>
                handleChange(key, e.target.checked ? null : (typeof param.default === 'number' ? param.default : fallbackValue))
              }
              className="w-4 h-4 rounded"
            />
            Без ограничений токенов
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              className={`${baseClass} ${isUnlimited ? 'opacity-40 cursor-not-allowed' : ''}`}
              value={String(isUnlimited ? '' : draft ?? '')}
              min={param.min}
              max={param.max}
              step={1}
              disabled={isUnlimited}
              onChange={(e) => handleChange(key, parseInt(e.target.value, 10))}
            />
            <span className="text-xs text-gray-400 whitespace-nowrap">
              [{param.min} – {param.max}] / null
            </span>
          </div>
        </div>
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
    <div className={`bg-white rounded-xl border-l-4 ${accent.border} shadow-md overflow-hidden`}>
      {/* Заголовок карточки */}
      <div className="flex justify-between items-center px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span className={`text-lg px-2 py-1 rounded-lg ${accent.icon}`}>
            {group.label.split(' ')[0]}
          </span>
          <h3 className="font-semibold text-gray-800 text-base">
            {group.label.split(' ').slice(1).join(' ')}
          </h3>
        </div>
        <div className="flex gap-2">
          {dirtyKeys.size > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={isSaving}
              className={`px-3 py-1 rounded text-sm font-medium
                         ${accent.saveBtn} disabled:opacity-50 transition-colors`}
            >
              Сохранить все ({dirtyKeys.size})
            </button>
          )}
          <button
            onClick={() => onReset('__all__')}
            disabled={isSaving}
            className="px-3 py-1 bg-gray-100 text-gray-500 rounded text-sm
                       hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            ↩ Сбросить группу
          </button>
        </div>
      </div>

      {/* Параметры */}
      <div className="px-5 py-4 space-y-5">
        {Object.entries(group.params).map(([key, param]) => (
          <div key={key} className="grid grid-cols-[1fr_auto] gap-x-3 items-start">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <label className="text-sm font-medium text-gray-700">
                  {param.label}
                </label>
                {param.is_overridden && !dirtyKeys.has(key) && (
                  <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700
                                   rounded text-xs font-medium">
                    override
                  </span>
                )}
                {dirtyKeys.has(key) && (
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${accent.badge}`}>
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
                  Дефолт: <span className="font-mono">{String(param.default)}</span>
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1 pt-6">
              {dirtyKeys.has(key) && (
                <button
                  onClick={() => handleSave(key)}
                  disabled={isSaving}
                  className={`px-2 py-1 rounded text-xs
                             ${accent.checkBtn} disabled:opacity-50 transition-colors`}
                >
                  ✓
                </button>
              )}
              {param.is_overridden && (
                <button
                  onClick={() => onReset(key)}
                  disabled={isSaving}
                  title="Сбросить к дефолту"
                  className="px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs
                             hover:bg-gray-200 disabled:opacity-50 transition-colors"
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
