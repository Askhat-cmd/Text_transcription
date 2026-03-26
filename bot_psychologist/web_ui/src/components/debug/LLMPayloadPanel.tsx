import React, { useCallback, useState } from 'react';
import { storageService } from '../../services/storage.service';
import type { LLMPayloadTrace } from '../../types';

interface Props {
  sessionId?: string | null;
}

export const LLMPayloadPanel: React.FC<Props> = ({ sessionId }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<LLMPayloadTrace | null>(null);

  const loadPayload = useCallback(async () => {
    if (!sessionId || loading || payload) return;
    setLoading(true);
    setError(null);
    try {
      const apiKey = storageService.getApiKey();
      const headers = apiKey ? { 'X-API-Key': apiKey } : undefined;
      const res = await fetch(`/api/debug/session/${sessionId}/llm-payload`, {
        credentials: 'include',
        headers,
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = (await res.json()) as LLMPayloadTrace;
      setPayload(data);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Load failed';
      setError(`Не удалось загрузить полотно LLM: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId, loading, payload]);

  const onToggle = useCallback(
    (event: React.SyntheticEvent<HTMLDetailsElement>) => {
      const isOpen = event.currentTarget.open;
      setOpen(isOpen);
      if (isOpen) {
        void loadPayload();
      }
    },
    [loadPayload]
  );

  const copyAll = useCallback(async () => {
    if (!payload) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    } catch {
      // no-op
    }
  }, [payload]);

  if (!sessionId) return null;

  return (
    <details id="debug-llm-canvas" open={open} onToggle={onToggle}>
      <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
        Полотно LLM
      </summary>
      <div className="mt-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3 space-y-3">
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <span>session: {sessionId}</span>
          <button
            type="button"
            onClick={() => void copyAll()}
            disabled={!payload}
            className="ml-auto rounded px-2 py-1 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
          >
            Скопировать все
          </button>
        </div>

        {loading && <p className="text-[11px] text-slate-500">Загрузка...</p>}
        {error && <p className="text-[11px] text-rose-500">{error}</p>}

        {payload && (
          <>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">turn: {payload.turn_number ?? '—'}</div>
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">mode: {payload.recommended_mode ?? '—'}</div>
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">sd: {payload.sd_level ?? '—'}</div>
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">state: {payload.user_state ?? '—'}</div>
            </div>

            {payload.hybrid_query_preview && (
              <details>
                <summary className="cursor-pointer text-[11px] text-slate-500">Hybrid query</summary>
                <pre className="mt-1 font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
                  {payload.hybrid_query_preview}
                </pre>
              </details>
            )}

            <details open>
              <summary className="cursor-pointer text-[11px] text-slate-500">
                LLM calls ({payload.llm_calls.length})
              </summary>
              <div className="mt-2 space-y-2">
                {payload.llm_calls.map((call, idx) => (
                  <details key={`${call.step ?? 'call'}-${idx}`}>
                    <summary className="cursor-pointer text-[11px] text-slate-600 dark:text-slate-300">
                      {call.step ?? 'step'} | {call.model ?? 'model'} | {call.duration_ms ?? '—'}ms
                    </summary>
                    <div className="mt-1 space-y-2">
                      <pre className="font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
                        {call.system_prompt || '[пусто]'}
                      </pre>
                      <pre className="font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
                        {call.user_prompt || '[пусто]'}
                      </pre>
                      {call.response_preview && (
                        <pre className="font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
                          {call.response_preview}
                        </pre>
                      )}
                    </div>
                  </details>
                ))}
              </div>
            </details>

            {payload.memory_snapshot && (
              <details>
                <summary className="cursor-pointer text-[11px] text-slate-500">Memory snapshot</summary>
                <pre className="mt-1 font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
                  {payload.memory_snapshot}
                </pre>
              </details>
            )}
          </>
        )}
      </div>
    </details>
  );
};

