// components/admin/PromptEditorPanel.tsx

import React, { useState, useEffect } from 'react';
import type { PromptDetail, PromptMeta } from '../../types/admin.types';

interface Props {
  prompts: PromptMeta[];
  selectedPrompt: PromptDetail | null;
  promptError?: string | null;
  onSelect: (name: string) => void;
  onRetryLoad: () => void;
  onSave: (name: string, text: string) => Promise<void>;
  onReset: (name: string) => Promise<void>;
  onResetAll: () => Promise<void>;
  isSaving: boolean;
}

export const PromptEditorPanel: React.FC<Props> = ({
  prompts,
  selectedPrompt,
  promptError,
  onSelect,
  onRetryLoad,
  onSave,
  onReset,
  onResetAll,
  isSaving,
}) => {
  const [draftText, setDraftText] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedPrompt) {
      setDraftText(selectedPrompt.text);
      setIsDirty(false);
      setShowDiff(false);
      setValidationError(null);
    }
  }, [selectedPrompt]);

  const handleTextChange = (value: string) => {
    setDraftText(value);
    setIsDirty(value !== selectedPrompt?.text);
    setValidationError(null);
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;
    if (selectedPrompt.editable === false) return;
    if (draftText.trim().length < 20) {
      setValidationError('Слишком короткий текст (минимум 20 символов).');
      return;
    }
    await onSave(selectedPrompt.name, draftText);
    setIsDirty(false);
  };

  const handleReset = async () => {
    if (!selectedPrompt) return;
    await onReset(selectedPrompt.name);
  };

  return (
    <div className="flex h-full gap-4">
      {/* Левая панель: список промтов */}
      <div className="w-64 flex-shrink-0">
        <div className="bg-gradient-to-r from-rose-900 to-rose-700 px-4 py-3
                        rounded-t-lg flex justify-between items-center mb-3 -mx-0">
          <h3 className="text-white font-semibold text-sm">📝 Промты</h3>
          <button
            onClick={onResetAll}
            disabled={isSaving}
            className="text-xs text-rose-300 hover:text-white transition-colors disabled:opacity-50"
          >
            ⟲ Все к дефолту
          </button>
        </div>
        <div className="space-y-1">
          {prompts.map((p) => (
            <button
              key={p.name}
              onClick={() => onSelect(p.name)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selectedPrompt?.name === p.name
                  ? 'bg-rose-50 border border-rose-200 text-rose-800'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium truncate">{p.label}</span>
                <div className="flex items-center gap-1">
                  {p.editable === false && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                      RO
                    </span>
                  )}
                  {p.is_overridden && (
                    <span className="ml-1 w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                  )}
                </div>
              </div>
              <div className="text-xs text-gray-400 truncate mt-0.5">
                {p.char_count} симв. • {p.version ?? 'v2'}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Правая панель: редактор */}
      <div className="flex-1 flex flex-col">
        {promptError && (
          <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700 flex items-center justify-between">
            <span>{promptError}</span>
            <button
              onClick={onRetryLoad}
              className="ml-3 px-2 py-1 rounded border border-amber-300 text-amber-700 hover:bg-amber-100"
            >
              Повторить
            </button>
          </div>
        )}
        {selectedPrompt ? (
          <>
            {/* Заголовок редактора */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-800">
                  {selectedPrompt.label}
                </h3>
                <p className="text-xs text-gray-400">
                  {draftText.length} символов
                  {selectedPrompt.is_overridden && (
                    <span className="ml-2 text-amber-600 font-medium">
                      • override активен
                    </span>
                  )}
                  {isDirty && (
                    <span className="ml-2 text-blue-600 font-medium">
                      • не сохранено
                    </span>
                  )}
                  <span className="ml-2 text-slate-500">• {selectedPrompt.version ?? 'v2'}</span>
                  {selectedPrompt.editable === false && (
                    <span className="ml-2 text-slate-500 font-medium">• read-only runtime section</span>
                  )}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDiff(!showDiff)}
                  className={`px-3 py-1.5 rounded text-sm border transition-colors ${
                    showDiff
                      ? 'bg-rose-800 text-white border-rose-800'
                      : 'border-rose-200 text-rose-600 hover:bg-rose-50'
                  }`}
                >
                  {showDiff ? 'Скрыть оригинал' : 'Показать оригинал'}
                </button>
                {selectedPrompt.is_overridden && selectedPrompt.editable !== false && (
                  <button
                    onClick={handleReset}
                    disabled={isSaving}
                    className="px-3 py-1.5 rounded text-sm border border-rose-300 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                  >
                    ↩ Вернуть оригинал
                  </button>
                )}
                <button
                  onClick={handleSave}
                  disabled={isSaving || !isDirty || selectedPrompt.editable === false}
                  className="px-3 py-1.5 bg-rose-600 text-white rounded text-sm hover:bg-rose-700 disabled:opacity-50"
                >
                  {isSaving ? 'Сохранение...' : '✓ Сохранить'}
                </button>
              </div>
            </div>

            {validationError && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {validationError}
              </div>
            )}

            {/* Режим diff: два блока рядом */}
            {showDiff ? (
              <div className="flex gap-3 flex-1 min-h-0">
                <div className="flex-1 flex flex-col">
                  <p className="text-xs text-gray-500 mb-1 font-medium">
                    Оригинал (.md файл)
                  </p>
                  <textarea
                    readOnly
                    value={selectedPrompt.default_text}
                    className="flex-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono bg-gray-50 text-gray-500 resize-none"
                  />
                </div>
                <div className="flex-1 flex flex-col">
                  <p className="text-xs text-rose-600 mb-1 font-medium">
                    Текущая версия (редактирование)
                  </p>
                  <textarea
                    value={draftText}
                    onChange={(e) => handleTextChange(e.target.value)}
                    readOnly={selectedPrompt.editable === false}
                    className="flex-1 w-full px-3 py-2 border border-blue-300 rounded-lg text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
              </div>
            ) : (
              /* Обычный режим: один редактор */
              <textarea
                value={draftText}
                onChange={(e) => handleTextChange(e.target.value)}
                readOnly={selectedPrompt.editable === false}
                className="flex-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="Текст промта..."
              />
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Выберите промт из списка слева
          </div>
        )}
      </div>
    </div>
  );
};
