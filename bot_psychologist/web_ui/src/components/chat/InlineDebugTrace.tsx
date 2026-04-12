import React, { useMemo, useState } from 'react';
import type { InlineTrace } from '../../types';
import { useDebugBlob } from '../../hooks/useDebugBlob';
import { StatusBar } from '../debug/StatusBar';
import { PipelineFunnel } from '../debug/PipelineFunnel';
import { AnomalyList } from '../debug/AnomalyList';
import { SessionDashboard } from '../debug/SessionDashboard';
import { TraceHistory } from '../debug/TraceHistory';
import { ConfigSnapshot } from '../debug/ConfigSnapshot';
import { ErrorView } from '../debug/ErrorView';
import { LLMPayloadPanel } from '../debug/LLMPayloadPanel';

interface Props {
  trace: InlineTrace;
}

const MODE_COLORS: Record<string, string> = {
  PRESENCE: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  CLARIFICATION: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  VALIDATION: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  THINKING: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
  INTERVENTION: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
  INTEGRATION: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
};

const formatNumber = (value: unknown, digits: number, fallback = '—'): string => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback;
  }
  return value.toFixed(digits);
};

const formatMs = (value?: number | null) => (typeof value === 'number' ? `${value}ms` : '—');

const ChunkRow: React.FC<{ chunk: any; passed?: boolean }> = ({ chunk, passed }) => {
  const [expanded, setExpanded] = useState(false);
  const isPassed = passed ?? chunk?.passed_filter ?? false;
  const fullText: string | undefined = chunk?.text ?? chunk?.full_text;
  const previewText: string | undefined = chunk?.preview;
  const hasMore = Boolean(fullText && fullText.length > (previewText?.length ?? 0));

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs space-y-1">
      <div className="flex items-center gap-2">
        <span className={isPassed ? 'text-emerald-600' : 'text-rose-500'}>{isPassed ? 'OK' : 'NO'}</span>
        <code className="font-mono font-semibold text-slate-700 dark:text-slate-300">{chunk?.block_id}</code>
        <span className="ml-auto text-slate-500 font-mono">
          {formatNumber(chunk?.score_initial ?? 0, 3)} {'>'} {formatNumber(chunk?.score_final ?? 0, 3)}
        </span>
      </div>
      {chunk?.filter_reason && !isPassed && (
        <div className="text-[10px] text-rose-500">{chunk.filter_reason}</div>
      )}
      {(previewText || fullText) && (
        <div>
          <p className="text-[11px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
            {expanded && fullText ? fullText : (previewText ?? fullText)}
          </p>
          {hasMore && (
            <button
              onClick={() => setExpanded((prev) => !prev)}
              className="mt-1 text-[10px] text-sky-500 hover:text-sky-700 dark:hover:text-sky-300 transition-colors"
            >
              {expanded ? '▲ Свернуть' : `▼ Развернуть (${fullText!.length} символов)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export const InlineDebugTrace: React.FC<Props> = ({ trace }) => {
  const { blobs, loading, fetchBlob } = useDebugBlob();
  const [openAnomalies, setOpenAnomalies] = useState<boolean>((trace.anomalies?.length ?? 0) > 0);
  const [panelOpen, setPanelOpen] = useState(false);

  const llmCalls = trace.llm_calls ?? [];  // Используется в tokenStats и LLM Calls секции
  const pipelineStages = trace.pipeline_stages ?? [];
  const totalStageMs = pipelineStages.reduce((sum, stage) => sum + (stage.duration_ms || 0), 0) || 1;

  // FIX 2b: tokenStats с fallback-агрегацией из llm_calls
  const tokenStats = useMemo(() => {
    const p = trace.tokens_prompt ?? (llmCalls.reduce((s, c) => s + (c.tokens_prompt ?? 0), 0) || null);
    const c = trace.tokens_completion ?? (llmCalls.reduce((s, c) => s + (c.tokens_completion ?? 0), 0) || null);
    const t = trace.tokens_total ?? ((p != null && c != null) ? p + c : null);
    return { prompt: p, completion: c, total: t };
  }, [trace.tokens_prompt, trace.tokens_completion, trace.tokens_total, llmCalls]);

  const recommendedMode = trace.recommended_mode || '—';
  const modeColor = MODE_COLORS[recommendedMode] || 'bg-slate-100 text-slate-700';
  const confidenceScore = typeof trace.confidence_score === 'number' ? trace.confidence_score : undefined;
  const confColor = confidenceScore != null
    ? confidenceScore >= 0.75
      ? 'text-emerald-600'
      : confidenceScore >= 0.5
        ? 'text-amber-500'
        : 'text-rose-500'
    : 'text-slate-500';

  const chunksRetrieved = trace.chunks_retrieved ?? [];
  const chunksAfter = trace.chunks_after_filter ?? [];

  const memoryTurns = trace.memory_turns ?? trace.memory_turns_content?.length ?? 0;
  const summaryLength = trace.summary_length ?? (trace.summary_text ? trace.summary_text.length : 0);
  const semanticHits = trace.semantic_hits ?? trace.semantic_hits_detail?.length ?? 0;

  const systemBlobId = trace.system_prompt_blob_id;
  const userBlobId = trace.user_prompt_blob_id;

  const memorySnapshotId = trace.memory_snapshot_blob_id;

  const stateTrajectory = useMemo(() => trace.state_trajectory ?? [], [trace.state_trajectory]);

  return (
    <div className="mt-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 text-xs">
      <div
        className="cursor-pointer select-none"
        onClick={() => setPanelOpen((prev) => !prev)}
        title={panelOpen ? 'Свернуть панель отладки' : 'Развернуть панель отладки'}
      >
        <StatusBar trace={trace} isExpanded={panelOpen} />
      </div>

      {panelOpen && (
        <div className="px-4 pb-4 pt-2 space-y-4">
        {trace.pipeline_error && (
          <div id="debug-error">
            <ErrorView error={trace.pipeline_error} />
          </div>
        )}

        <details id="debug-routing">
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            Роутинг и классификация
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Режим</p>
              <p className={`font-bold px-1 rounded ${modeColor}`}>{recommendedMode}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Правило</p>
              <p className="font-mono font-semibold text-slate-700 dark:text-slate-300">
                {trace.decision_rule_id ?? '—'}
              </p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Confidence</p>
              <p className={`font-bold ${confColor}`}>
                {confidenceScore != null ? formatNumber(confidenceScore, 3, '0.000') : '—'} ({trace.confidence_level ?? '—'})
              </p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Состояние</p>
              <p className="font-semibold text-slate-700 dark:text-slate-300">{trace.user_state ?? '—'}</p>
            </div>
            {trace.fast_path && (
              <div className="rounded-lg bg-amber-50 dark:bg-amber-900/30 px-3 py-2">
                <p className="text-[10px] text-amber-700 uppercase tracking-wide">Fast Path</p>
                <p className="font-semibold text-amber-800 dark:text-amber-200">
                  {trace.fast_path_reason ?? 'fast'}
                </p>
              </div>
            )}
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Block cap</p>
              <p className="font-semibold">{trace.block_cap ?? '—'}</p>
              <p className="text-[10px] text-slate-400">initial: {trace.blocks_initial ?? '—'} {'>'} cap: {trace.blocks_after_cap ?? '—'}</p>
            </div>
          </div>
        </details>

        <details id="debug-timeline">
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            Pipeline Timeline
          </summary>
          <div className="mt-2 space-y-2">
            {pipelineStages.length === 0 ? (
              <p className="text-slate-400">Нет данных</p>
            ) : (
              pipelineStages.map((stage) => {
                const width = Math.max((stage.duration_ms / totalStageMs) * 100, 2);
                const isSlow = stage.duration_ms > totalStageMs * 0.5;
                return (
                  <div key={stage.name} className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-500 w-28 truncate">{stage.label}</span>
                    <div className="flex-1 h-2 rounded bg-slate-100 dark:bg-slate-700 overflow-hidden">
                      <div
                        className={`h-2 ${stage.skipped ? 'bg-slate-300' : isSlow ? 'bg-rose-400' : 'bg-emerald-400'}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500 w-10 text-right">{stage.skipped ? 'skip' : formatMs(stage.duration_ms)}</span>
                  </div>
                );
              })
            )}
          </div>
        </details>

        <details id="debug-chunks">
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            Чанки и retrieval
          </summary>
          <PipelineFunnel trace={trace} />

          <div className="mt-3 space-y-2">
            <details>
              <summary className="cursor-pointer text-slate-500 text-[11px]">Chunks in response ({chunksAfter.length})</summary>
              <div className="mt-2 space-y-2">
                {chunksAfter.length === 0 ? (
                  <p className="text-slate-400">Нет чанков после фильтра</p>
                ) : (
                  chunksAfter.map((chunk, idx) => (
                    <ChunkRow key={`${chunk.block_id}-${idx}`} chunk={chunk} passed={true} />
                  ))
                )}
              </div>
            </details>

            <details>
              <summary className="cursor-pointer text-slate-500 text-[11px]">Все чанки ({chunksRetrieved.length})</summary>
              <div className="mt-2 space-y-2">
                {chunksRetrieved.length === 0 ? (
                  <p className="text-slate-400">Нет retrieved чанков</p>
                ) : (
                  chunksRetrieved.map((chunk, idx) => (
                    <ChunkRow key={`${chunk.block_id}-${idx}`} chunk={chunk} passed={chunk.passed_filter} />
                  ))
                )}
              </div>
            </details>
          </div>
        </details>

        {llmCalls.length > 0 && (
          <details id="debug-llm">
            <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
              LLM Calls ({llmCalls.length})
            </summary>
            <div className="mt-2 space-y-2">
              {llmCalls.map((call, idx) => {
                const callSystemId = call.system_prompt_blob_id ?? systemBlobId;
                const callUserId = call.user_prompt_blob_id ?? userBlobId;
                return (
                  <details key={`${call.step}-${idx}`} className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
                    <summary className="cursor-pointer px-3 py-2 flex items-center gap-2 text-xs select-none hover:bg-slate-50 dark:hover:bg-slate-700/50">
                      <span className="font-mono font-semibold text-slate-700 dark:text-slate-300 w-28 truncate">
                        {call.step}
                      </span>
                      <span className="text-sky-600 dark:text-sky-400 font-medium">
                        {call.model}
                      </span>
                      {call.tokens_total != null && (
                        <span className="ml-auto text-slate-500">tokens {call.tokens_total.toLocaleString()} tok</span>
                      )}
                      {call.duration_ms != null && (
                        <span className="text-slate-400">{call.duration_ms}ms</span>
                      )}
                    </summary>
                    <div className="px-3 py-2 border-t border-slate-200 dark:border-slate-700 space-y-2">
                      {(call.tokens_prompt != null || call.tokens_completion != null) && (
                        <div className="flex gap-4 text-[11px]">
                          <span className="text-slate-400">prompt: <b className="text-slate-600 dark:text-slate-300">{call.tokens_prompt ?? '—'}</b></span>
                          <span className="text-slate-400">completion: <b className="text-slate-600 dark:text-slate-300">{call.tokens_completion ?? '—'}</b></span>
                        </div>
                      )}
                      {call.system_prompt_preview && (
                        <div>
                          <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-0.5">System prompt (preview)</p>
                          <pre className="font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                            {call.system_prompt_preview}
                          </pre>
                        </div>
                      )}
                      {call.user_prompt_preview && (
                        <div>
                          <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-0.5">User prompt (preview)</p>
                          <pre className="font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                            {call.user_prompt_preview}
                          </pre>
                        </div>
                      )}
                      {call.response_preview && (
                        <div>
                          <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-0.5">Response (preview)</p>
                          <pre className="font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                            {call.response_preview}
                          </pre>
                        </div>
                      )}
                      {(callSystemId || callUserId) && (
                        <div className="space-y-2">
                          {callSystemId && (
                            <div>
                              <button
                                onClick={() => fetchBlob(callSystemId)}
                                className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                              >
                                Full system prompt {'>'}
                              </button>
                              {loading[callSystemId] && <span className="ml-2 text-[10px] text-slate-400">Loading...</span>}
                              {blobs[callSystemId] && (
                                <pre className="mt-1 font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                                  {blobs[callSystemId]}
                                </pre>
                              )}
                            </div>
                          )}
                          {callUserId && (
                            <div>
                              <button
                                onClick={() => fetchBlob(callUserId)}
                                className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                              >
                                Full user prompt {'>'}
                              </button>
                              {loading[callUserId] && <span className="ml-2 text-[10px] text-slate-400">Loading...</span>}
                              {blobs[callUserId] && (
                                <pre className="mt-1 font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-1.5">
                                  {blobs[callUserId]}
                                </pre>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </details>
                );
              })}
            </div>
          </details>
        )}

        <details id="debug-memory">
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            Контекст памяти
          </summary>
          <div className="mt-2 grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Turns</p>
              <p className="font-semibold">{memoryTurns}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Summary length</p>
              <p className="font-semibold">{summaryLength}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Semantic hits</p>
              <p className="font-semibold">{semanticHits}</p>
            </div>
          </div>

          <details className="mt-3">
            <summary className="cursor-pointer text-[11px] text-slate-500">Turns content</summary>
            <div className="mt-2 space-y-2">
              {trace.memory_turns_content && trace.memory_turns_content.length > 0 ? (
                trace.memory_turns_content.map((turn, idx) => (
                  <div key={`${turn.turn_index}-${idx}`} className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      <span>#{turn.turn_index}</span>
                      <span>{turn.role}</span>
                      {turn.state && <span className="text-violet-500">{turn.state}</span>}
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
                      {turn.text_preview}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-slate-400">Нет данных</p>
              )}
            </div>
          </details>

          <details className="mt-3">
            <summary className="cursor-pointer text-[11px] text-slate-500">Summary text</summary>
            <div className="mt-2">
              {trace.summary_text ? (
                <pre className="font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-2 border border-slate-200 dark:border-slate-700">
                  {trace.summary_text}
                </pre>
              ) : (
                <p className="text-slate-400">Summary отсутствует</p>
              )}
            </div>
          </details>

          <details className="mt-3">
            <summary className="cursor-pointer text-[11px] text-slate-500">Semantic hits detail</summary>
            <div className="mt-2 space-y-2">
              {trace.semantic_hits_detail && trace.semantic_hits_detail.length > 0 ? (
                trace.semantic_hits_detail.map((hit, idx) => (
                  <div key={`${hit.block_id}-${idx}`} className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      <span>{hit.block_id}</span>
                      <span className="ml-auto">{formatNumber(hit.score, 3, '0.000')}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
                      {hit.text_preview}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-slate-400">Нет semantic hits</p>
              )}
            </div>
          </details>

          <details className="mt-3">
            <summary className="cursor-pointer text-[11px] text-slate-500">Записано в память</summary>
            <div className="mt-2 space-y-2">
              {trace.context_written ? (
                <pre className="font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-2 border border-slate-200 dark:border-slate-700">
                  {trace.context_written}
                </pre>
              ) : (
                <p className="text-slate-400">Нет записи</p>
              )}
              {memorySnapshotId && (
                <div>
                  <button
                    onClick={() => fetchBlob(memorySnapshotId)}
                    className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    Full memory snapshot {'>'}
                  </button>
                  {loading[memorySnapshotId] && <span className="ml-2 text-[10px] text-slate-400">Loading...</span>}
                  {blobs[memorySnapshotId] && (
                    <pre className="mt-1 font-mono text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap bg-slate-50 dark:bg-slate-900 rounded p-2 border border-slate-200 dark:border-slate-700">
                      {blobs[memorySnapshotId]}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </details>

          {stateTrajectory.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">State trajectory</p>
              <div className="mt-1 flex gap-1 flex-wrap">
                {stateTrajectory.map((point, idx) => (
                  <span
                    key={`${point.turn}-${idx}`}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                  >
                    {point.state}
                  </span>
                ))}
              </div>
            </div>
          )}
        </details>

        <details id="debug-cost" open>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            Модели, токены и стоимость
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {trace.primary_model && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Primary (ответ)</p>
                <p className="font-mono font-semibold text-sky-600 dark:text-sky-400 text-[11px] truncate">
                  {trace.primary_model}
                </p>
              </div>
            )}
            {trace.classifier_model && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">State Router Model</p>
                <p className="font-mono font-semibold text-violet-600 dark:text-violet-400 text-[11px] truncate">
                  {trace.classifier_model}
                </p>
              </div>
            )}
            {trace.embedding_model && (
              <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Embedding</p>
                <p className="font-mono font-semibold text-emerald-600 dark:text-emerald-400 text-[11px] truncate">
                  {trace.embedding_model}
                </p>
              </div>
            )}
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Reranker</p>
              <p className="font-mono font-semibold text-[11px] truncate text-slate-700 dark:text-slate-300">
                {trace.reranker_enabled ? (trace.reranker_model ?? 'enabled') : 'off'}
              </p>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-800 px-3 py-2 col-span-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Токены</p>
              <div className="flex gap-4 text-xs">
                <span className="text-slate-500">prompt: <b className="text-slate-700 dark:text-slate-200">{tokenStats.prompt ?? '—'}</b></span>
                <span className="text-slate-500">completion: <b className="text-slate-700 dark:text-slate-200">{tokenStats.completion ?? '—'}</b></span>
                <span className="text-slate-500">total: <b className="text-amber-600 dark:text-amber-400 font-bold">{tokenStats.total ?? '—'}</b></span>
              </div>
              <div className="mt-1 flex gap-4 text-[11px] text-slate-500">
                <span>session tokens: <b className="text-slate-700 dark:text-slate-200">{trace.session_tokens_total ?? '—'}</b></span>
                <span>session turns: <b className="text-slate-700 dark:text-slate-200">{trace.session_turns ?? '—'}</b></span>
                <span className="ml-auto text-emerald-600 dark:text-emerald-400 font-bold">
                  {trace.estimated_cost_usd != null ? `\$${formatNumber(trace.estimated_cost_usd, 6, '0.000000')}` : '—'}
                </span>
              </div>
            </div>
          </div>
        </details>

        <details id="debug-anomalies" open={openAnomalies} onToggle={(e) => setOpenAnomalies(e.currentTarget.open)}>
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400 py-1 select-none">
            Anomalies
          </summary>
          <div className="mt-2">
            <AnomalyList trace={trace} />
          </div>
        </details>

        {trace.session_id && (
          <div id="debug-session">
            <SessionDashboard sessionId={trace.session_id} />
          </div>
        )}

        {trace.session_id && (
          <div id="debug-history">
            <TraceHistory sessionId={trace.session_id} />
          </div>
        )}

        <div id="debug-config">
          <ConfigSnapshot trace={trace} />
        </div>

        <LLMPayloadPanel sessionId={trace.session_id} />

        <div className="flex justify-end px-3 pb-2">
          <button
            onClick={() => {
              const json = JSON.stringify(trace, null, 2);
              const blob = new Blob([json], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `trace_turn${trace.turn_number ?? 'N'}_${Date.now()}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors select-none"
          >
            Export trace JSON
          </button>
        </div>
        </div>
      )}
    </div>
  );
};









