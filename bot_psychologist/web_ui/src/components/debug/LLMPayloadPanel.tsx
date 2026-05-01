import React, { useCallback, useState } from 'react';
import { storageService } from '../../services/storage.service';
import type { LLMPayloadCall, LLMPayloadTrace } from '../../types';

interface Props {
  sessionId?: string | null;
}

const copyText = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value);
  } catch {
    // no-op
  }
};

const CallSection: React.FC<{ call: LLMPayloadCall }> = ({ call }) => {
  const callTitle = `${call.step ?? 'step'} | ${call.model ?? 'model'} | ${call.duration_ms ?? '—'}ms`;

  return (
    <details className="rounded-lg border border-slate-200 dark:border-slate-700 p-2">
      <summary className="cursor-pointer text-[11px] text-slate-700 dark:text-slate-300 select-none">
        {callTitle}
      </summary>

      <div className="mt-2 space-y-2">
        <div className="flex gap-4 text-[10px] text-slate-500">
          <span>prompt: <b className="text-slate-700 dark:text-slate-300">{call.tokens_prompt ?? '—'}</b></span>
          <span>completion: <b className="text-slate-700 dark:text-slate-300">{call.tokens_completion ?? '—'}</b></span>
          <span>total: <b className="text-amber-600 dark:text-amber-400">{call.tokens_total ?? '—'}</b></span>
          <button
            type="button"
            className="ml-auto text-[10px] text-sky-600 hover:text-sky-700 dark:text-sky-400"
            onClick={() => void copyText(JSON.stringify(call, null, 2))}
          >
            Копировать call
          </button>
        </div>

        <details>
          <summary className="cursor-pointer text-[11px] text-slate-500">System prompt</summary>
          <button
            type="button"
            className="mt-1 text-[10px] text-sky-600 hover:text-sky-700 dark:text-sky-400"
            onClick={() => void copyText(call.system_prompt || '')}
          >
            Копировать section
          </button>
          <pre className="mt-1 font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
            {call.system_prompt || '[пусто]'}
          </pre>
        </details>

        <details>
          <summary className="cursor-pointer text-[11px] text-slate-500">User prompt</summary>
          <button
            type="button"
            className="mt-1 text-[10px] text-sky-600 hover:text-sky-700 dark:text-sky-400"
            onClick={() => void copyText(call.user_prompt || '')}
          >
            Копировать section
          </button>
          <pre className="mt-1 font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
            {call.user_prompt || '[пусто]'}
          </pre>
        </details>

        <details>
          <summary className="cursor-pointer text-[11px] text-slate-500">Response preview</summary>
          <button
            type="button"
            className="mt-1 text-[10px] text-sky-600 hover:text-sky-700 dark:text-sky-400"
            onClick={() => void copyText(call.response_preview || '')}
          >
            Копировать section
          </button>
          <pre className="mt-1 font-mono text-[10px] whitespace-pre-wrap rounded bg-slate-50 dark:bg-slate-900 p-2 border border-slate-200 dark:border-slate-700">
            {call.response_preview || '[пусто]'}
          </pre>
        </details>
      </div>
    </details>
  );
};

export const LLMPayloadPanel: React.FC<Props> = ({ sessionId }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<LLMPayloadTrace | null>(null);

  const loadPayload = useCallback(async () => {
    if (!sessionId || loading || payload) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const apiKey = storageService.getApiKey();
      const headers = apiKey ? { 'X-API-Key': apiKey } : undefined;
      const res = await fetch(`/api/debug/session/${sessionId}/llm-payload?format=flat`, {
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
    if (!payload) {
      return;
    }
    await copyText(JSON.stringify(payload, null, 2));
  }, [payload]);

  if (!sessionId) {
    return null;
  }

  return (
    <details id={`debug-llm-canvas-${sessionId}`} open={open} onToggle={onToggle}>
      <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
        Полотно LLM
      </summary>

      <div className="mt-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3 space-y-3">
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <span>session: {sessionId}</span>
          {payload?.agent_id && (
            <span className="rounded bg-purple-500/10 px-2 py-0.5 text-purple-400/90">
              agent: {payload.agent_id}
            </span>
          )}
          <button
            type="button"
            onClick={() => void copyAll()}
            disabled={!payload}
            className="ml-auto rounded px-2 py-1 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
          >
            Копировать все
          </button>
        </div>

        {loading && <p className="text-[11px] text-slate-500">Загрузка...</p>}
        {error && <p className="text-[11px] text-rose-500">{error}</p>}

        {payload && (
          <>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">turn: {payload.turn_number ?? '—'}</div>
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">mode: {payload.recommended_mode ?? '—'}</div>
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">state: {payload.user_state ?? '—'}</div>
              <div className="rounded bg-slate-50 dark:bg-slate-900 p-2">chunks: {payload.chunks_count ?? '—'}</div>
            </div>

            {payload.hybrid_query_preview && (
              <details>
                <summary className="cursor-pointer text-[11px] text-slate-500">Hybrid query</summary>
                <button
                  type="button"
                  className="mt-1 text-[10px] text-sky-600 hover:text-sky-700 dark:text-sky-400"
                  onClick={() => void copyText(payload.hybrid_query_preview || '')}
                >
                  Копировать section
                </button>
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
                  <CallSection key={`${call.step ?? 'call'}-${idx}`} call={call} />
                ))}
              </div>
            </details>

            {payload.memory_snapshot && (
              <details>
                <summary className="cursor-pointer text-[11px] text-slate-500">Memory snapshot</summary>
                <button
                  type="button"
                  className="mt-1 text-[10px] text-sky-600 hover:text-sky-700 dark:text-sky-400"
                  onClick={() => void copyText(payload.memory_snapshot || '')}
                >
                  Копировать section
                </button>
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
