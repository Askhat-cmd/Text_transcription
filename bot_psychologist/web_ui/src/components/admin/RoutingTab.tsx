import React, { useEffect, useMemo, useState } from 'react';
import type { ConfigGroup } from '../../types/admin.types';

interface RoutingTabProps {
  group: ConfigGroup;
  onSave: (key: string, value: unknown) => Promise<void>;
  isSaving: boolean;
}

type LayerField = {
  key: string;
  label: string;
  kind: 'bool' | 'float';
  warningOnDisable?: boolean;
};

const LAYERS: Array<{ title: string; fields: LayerField[] }> = [
  {
    title: '🧠 Режим свободного собеседника',
    fields: [
      { key: 'FREE_CONVERSATION_MODE', label: 'Включить FREE_CONVERSATION_MODE', kind: 'bool' },
    ],
  },
  {
    title: '⚡ Слой 1: Fast Detector',
    fields: [
      { key: 'FAST_DETECTOR_ENABLED', label: 'Fast detector включен', kind: 'bool' },
      { key: 'FAST_DETECTOR_CONFIDENCE_THRESHOLD', label: 'Порог уверенности', kind: 'float' },
    ],
  },
  {
    title: '🟢 Слой 2: State Classifier',
    fields: [
      {
        key: 'STATE_CLASSIFIER_ENABLED',
        label: 'State classifier включен',
        kind: 'bool',
        warningOnDisable: true,
      },
      {
        key: 'STATE_CLASSIFIER_CONFIDENCE_THRESHOLD',
        label: 'Порог уверенности',
        kind: 'float',
      },
    ],
  },
  {
    title: '🟡 Слой 3: SD Classifier',
    fields: [
      {
        key: 'SD_CLASSIFIER_ENABLED',
        label: 'SD classifier включен',
        kind: 'bool',
        warningOnDisable: true,
      },
      {
        key: 'SD_CLASSIFIER_CONFIDENCE_THRESHOLD',
        label: 'Порог уверенности',
        kind: 'float',
      },
    ],
  },
  {
    title: '🟠 Слой 4: Decision Gate',
    fields: [
      { key: 'DECISION_GATE_RULE_THRESHOLD', label: 'Rule threshold', kind: 'float' },
      { key: 'DECISION_GATE_LLM_ROUTER_ENABLED', label: 'LLM Router при конфликте', kind: 'bool' },
    ],
  },
  {
    title: '🔴 Слой 5: Path/Prompt Priority',
    fields: [
      { key: 'PROMPT_SD_OVERRIDES_BASE', label: 'SD-промпт перекрывает base', kind: 'bool' },
      { key: 'PROMPT_MODE_OVERRIDES_SD', label: 'Mode-директива перекрывает SD', kind: 'bool' },
    ],
  },
];

export const RoutingTab: React.FC<RoutingTabProps> = ({ group, onSave, isSaving }) => {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState<Set<string>>(new Set());

  useEffect(() => {
    const next: Record<string, unknown> = {};
    Object.entries(group.params).forEach(([key, param]) => {
      next[key] = param.value;
    });
    setDrafts(next);
    setDirty(new Set());
  }, [group]);

  const availableLayers = useMemo(
    () =>
      LAYERS.filter((layer) =>
        layer.fields.some((field) => Object.prototype.hasOwnProperty.call(group.params, field.key))
      ),
    [group.params]
  );

  const updateDraft = (key: string, value: unknown) => {
    setDrafts((prev) => ({ ...prev, [key]: value }));
    setDirty((prev) => new Set(prev).add(key));
  };

  const saveKey = async (key: string) => {
    await onSave(key, drafts[key]);
    setDirty((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  };

  const saveAll = async () => {
    for (const key of Array.from(dirty)) {
      await onSave(key, drafts[key]);
    }
    setDirty(new Set());
  };

  const handleBoolChange = (field: LayerField, checked: boolean) => {
    if (field.warningOnDisable && !checked) {
      const ok = window.confirm(
        'Отключение этого слоя снижает качество психологической поддержки. Продолжить?'
      );
      if (!ok) return;
    }
    updateDraft(field.key, checked);
  };

  return (
    <div className="space-y-4 mt-4">
      {dirty.size > 0 && (
        <div className="flex justify-end">
          <button
            onClick={saveAll}
            disabled={isSaving}
            className="px-3 py-1.5 rounded bg-indigo-600 text-white text-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            Сохранить все ({dirty.size})
          </button>
        </div>
      )}

      {availableLayers.map((layer) => (
        <div key={layer.title} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
          <h3 className="font-semibold text-slate-800 mb-3">{layer.title}</h3>
          <div className="space-y-3">
            {layer.fields.map((field) => {
              const param = group.params[field.key];
              if (!param) return null;
              const value = drafts[field.key];

              return (
                <div key={field.key} className="grid grid-cols-[1fr_auto] items-center gap-3">
                  <div>
                    <label className="text-sm text-slate-700 font-medium">{field.label}</label>
                    {param.note && <p className="text-xs text-slate-400 mt-1">{param.note}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    {field.kind === 'bool' ? (
                      <input
                        type="checkbox"
                        checked={Boolean(value)}
                        onChange={(e) => handleBoolChange(field, e.target.checked)}
                        className="w-4 h-4"
                      />
                    ) : (
                      <input
                        type="number"
                        min={param.min}
                        max={param.max}
                        step={0.05}
                        value={String(value ?? '')}
                        onChange={(e) => updateDraft(field.key, parseFloat(e.target.value))}
                        className="w-28 px-2 py-1 border border-slate-300 rounded text-sm"
                      />
                    )}
                    {dirty.has(field.key) && (
                      <button
                        onClick={() => saveKey(field.key)}
                        disabled={isSaving}
                        className="px-2 py-1 rounded bg-indigo-600 text-white text-xs hover:bg-indigo-700 disabled:opacity-50"
                      >
                        ✓
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
