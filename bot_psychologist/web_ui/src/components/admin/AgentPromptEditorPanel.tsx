import React, { useEffect, useState } from 'react';

import { useAgents } from '../../hooks/useAgents';
import type { AgentId } from '../../types/admin.types';

const AGENT_OPTIONS: { id: AgentId; label: string }[] = [
  { id: 'writer', label: '✍️ Writer Agent' },
  { id: 'state_analyzer', label: '🧠 State Analyzer' },
  { id: 'thread_manager', label: '🧵 Thread Manager' },
];

export const AgentPromptEditorPanel: React.FC = () => {
  const {
    agentPrompts,
    isLoading,
    isSaving,
    error,
    successMessage,
    loadAgentPrompts,
    saveAgentPrompt,
    resetAgentPrompt,
  } = useAgents();

  const [selectedAgent, setSelectedAgent] = useState<'writer' | 'state_analyzer' | 'thread_manager'>('writer');
  const [selectedPromptKey, setSelectedPromptKey] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    void loadAgentPrompts(selectedAgent);
    setSelectedPromptKey(null);
    setEditText('');
    setIsDirty(false);
  }, [loadAgentPrompts, selectedAgent]);

  const handleSelectPrompt = (key: string) => {
    const prompt = agentPrompts.find((item) => item.key === key);
    if (!prompt) return;
    setSelectedPromptKey(key);
    setEditText(prompt.text);
    setIsDirty(false);
  };

  const handleSave = async () => {
    if (!selectedPromptKey) return;
    await saveAgentPrompt(selectedAgent, selectedPromptKey, editText);
    setIsDirty(false);
  };

  const handleReset = async () => {
    if (!selectedPromptKey) return;
    await resetAgentPrompt(selectedAgent, selectedPromptKey);
    setIsDirty(false);
  };

  return (
    <div className="flex h-full gap-4 p-4">
      <div className="w-56 flex-shrink-0 space-y-3">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">Агент</p>
          {AGENT_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setSelectedAgent(option.id as 'writer' | 'state_analyzer' | 'thread_manager')}
              className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                selectedAgent === option.id
                  ? 'bg-purple-500/20 text-purple-300'
                  : 'text-white/60 hover:bg-white/10'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">Промпты</p>
          {isLoading ? (
            <p className="text-xs text-white/40">Загрузка...</p>
          ) : (
            agentPrompts.map((prompt) => (
              <button
                key={prompt.key}
                type="button"
                onClick={() => handleSelectPrompt(prompt.key)}
                className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                  selectedPromptKey === prompt.key
                    ? 'bg-white/10 text-white'
                    : 'text-white/50 hover:bg-white/5'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="truncate">{prompt.key}</span>
                  {prompt.is_overridden && <span className="text-yellow-400">✎</span>}
                </div>
                <div className="text-white/30">{prompt.char_count} chars</div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3">
        {!selectedPromptKey ? (
          <div className="flex flex-1 items-center justify-center text-sm text-white/30">
            Выберите промпт из списка слева
          </div>
        ) : (
          <>
            {error && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
                {error}
              </div>
            )}
            {successMessage && (
              <div className="rounded-lg border border-green-500/20 bg-green-500/10 p-3 text-xs text-green-400">
                {successMessage}
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="font-mono text-sm text-white">{selectedPromptKey}</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void handleReset()}
                  disabled={isSaving}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/50 hover:bg-white/10"
                >
                  ↩ Сбросить
                </button>
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={isSaving || !isDirty}
                  className={`rounded-lg px-3 py-1.5 text-xs transition-colors ${
                    isDirty
                      ? 'border border-purple-500/40 bg-purple-500/30 text-purple-300'
                      : 'cursor-not-allowed border border-white/10 bg-white/5 text-white/30'
                  }`}
                >
                  {isSaving ? 'Сохранение...' : '✓ Сохранить'}
                </button>
              </div>
            </div>

            <textarea
              value={editText}
              onChange={(e) => {
                setEditText(e.target.value);
                const prompt = agentPrompts.find((item) => item.key === selectedPromptKey);
                setIsDirty(prompt != null && e.target.value !== prompt.text);
              }}
              className="min-h-[300px] w-full flex-1 resize-none rounded-lg border border-white/10 bg-black/40 p-3 font-mono text-xs text-white/80 focus:border-purple-500/50 focus:outline-none"
              spellCheck={false}
            />
          </>
        )}
      </div>
    </div>
  );
};
