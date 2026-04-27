import React, { useState } from 'react';

import type {
  AnomalyItem,
  MultiAgentTraceData,
  SemanticHitTrace,
  SessionDashboardTrace,
  TurnDiffTrace,
} from '../../types';

interface MultiAgentTraceWidgetProps {
  trace: MultiAgentTraceData | null;
  isExpanded?: boolean;
  onToggle?: () => void;
  isLoading?: boolean;
}

interface AccordionSectionProps {
  title: string;
  children?: React.ReactNode;
  nested?: boolean;
  defaultOpen?: boolean;
  headerClass?: string;
}

const formatMoney = (value?: number | null): string => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  return value.toFixed(6);
};

const formatPercent = (value: number): string => `${Math.round(value * 100)}%`;

const hasDiffChanges = (diff: TurnDiffTrace | null | undefined): boolean => {
  if (!diff) return false;
  return (
    diff.nervous_state_prev !== diff.nervous_state_curr ||
    diff.phase_prev !== diff.phase_curr ||
    diff.memory_turns_delta !== 0 ||
    diff.semantic_hits_delta !== 0
  );
};

const AccordionSection: React.FC<AccordionSectionProps> = ({
  title,
  children,
  nested = false,
  defaultOpen = false,
  headerClass = '',
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`rounded-lg border border-slate-200 bg-white ${nested ? 'p-2' : 'p-3'}`}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`w-full text-left text-xs font-semibold flex items-center justify-between ${headerClass}`}
      >
        <span>{title}</span>
        <span className="text-slate-500">{open ? '▼' : '▶'}</span>
      </button>
      {open && <div className="mt-2">{children}</div>}
    </section>
  );
};

const MetaItem: React.FC<{ label: string; value: React.ReactNode; highlight?: boolean }> = ({
  label,
  value,
  highlight = false,
}) => (
  <div className={`rounded border p-2 ${highlight ? 'border-blue-300 bg-blue-50' : 'border-slate-200'}`}>
    <div className="text-[10px] text-slate-500">{label}</div>
    <div className="text-xs font-medium">{value}</div>
  </div>
);

const ChunkCard: React.FC<{ hit: SemanticHitTrace }> = ({ hit }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border rounded p-2 mb-1">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full text-left text-xs flex justify-between"
      >
        <span>{hit.source || hit.chunk_id || 'chunk'}</span>
        <span className="text-slate-400">
          score: {Number.isFinite(hit.score) ? hit.score.toFixed(3) : '0.000'} {open ? '▼' : '▶'}
        </span>
      </button>
      {open && <pre className="mt-1 text-xs whitespace-pre-wrap text-slate-600">{hit.content_full || '—'}</pre>}
    </div>
  );
};

const DiffRow: React.FC<{ label: string; prev?: string | null; curr?: string | null }> = ({ label, prev, curr }) => (
  <div className="text-xs">
    <span className="text-slate-500">{label}:</span>{' '}
    <span className="text-slate-400">{prev || '—'}</span>
    <span className="mx-1 text-slate-400">→</span>
    <span className="text-slate-700 font-medium">{curr || '—'}</span>
  </div>
);

const AnomalyRow: React.FC<{ anomaly: AnomalyItem }> = ({ anomaly }) => {
  const isError = String(anomaly.severity || '').toUpperCase() === 'ERROR';
  return (
    <div className={`rounded border p-2 text-xs ${isError ? 'border-red-300 bg-red-50' : 'border-yellow-300 bg-yellow-50'}`}>
      <div className="flex items-center gap-2">
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${isError ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
          {String(anomaly.severity || 'WARN').toUpperCase()}
        </span>
        <span className="font-semibold">{anomaly.code}</span>
      </div>
      <div className="mt-1 text-slate-700">{anomaly.message}</div>
    </div>
  );
};

const StateBadge: React.FC<{ state: string }> = ({ state }) => (
  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-700">
    {state}
  </span>
);

function getHeaderStatus(trace: MultiAgentTraceData): {
  label: string;
  className: string;
  badgeClassName: string;
} {
  if (trace.agents.validator.is_blocked) {
    return {
      label: 'ERROR',
      className: 'bg-red-50 border-red-300',
      badgeClassName: 'bg-red-100 text-red-700',
    };
  }
  if (trace.agents.state_analyzer.safety_flag || (trace.anomalies || []).length > 0) {
    return {
      label: 'WARN',
      className: 'bg-yellow-50 border-yellow-300',
      badgeClassName: 'bg-yellow-100 text-yellow-700',
    };
  }
  return {
    label: 'OK',
    className: 'bg-slate-50 border-slate-200',
    badgeClassName: 'bg-emerald-100 text-emerald-700',
  };
}

export const MultiAgentTraceWidget: React.FC<MultiAgentTraceWidgetProps> = ({
  trace,
  isExpanded,
  onToggle,
  isLoading = false,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const expanded = isExpanded ?? internalExpanded;

  if (isLoading && !trace) {
    return (
      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 animate-pulse">
        <div className="h-4 w-56 rounded bg-slate-200 mb-3" />
        <div className="h-3 w-full rounded bg-slate-200 mb-2" />
        <div className="h-3 w-5/6 rounded bg-slate-200" />
      </div>
    );
  }
  if (!trace) return null;

  const status = getHeaderStatus(trace);
  const memory = trace.memory_context;
  const llm = trace.writer_llm;
  const diff = trace.turn_diff;
  const anomalies = trace.anomalies || [];
  const dash: SessionDashboardTrace | null | undefined = trace.session_dashboard;
  const totalLatency = Math.max(trace.total_latency_ms, 1);

  const timeline = [
    { key: 'state', label: 'State', ms: Math.max(trace.agents.state_analyzer.latency_ms, 0), className: 'bg-blue-500' },
    { key: 'thread', label: 'Thread', ms: Math.max(trace.agents.thread_manager.latency_ms, 0), className: 'bg-slate-500' },
    { key: 'memory', label: 'Memory', ms: Math.max(trace.agents.memory_retrieval.latency_ms, 0), className: 'bg-emerald-500' },
    { key: 'writer', label: 'Writer', ms: Math.max(trace.agents.writer.latency_ms, 0), className: 'bg-violet-500' },
    { key: 'validator', label: 'Validator', ms: Math.max(trace.agents.validator.latency_ms, 0), className: 'bg-orange-500' },
  ];

  const toggleExpanded = () => {
    if (onToggle) {
      onToggle();
      return;
    }
    setInternalExpanded((prev) => !prev);
  };

  const copyAll = async (): Promise<void> => {
    const payload = [
      `session_id=${trace.session_id}`,
      `turn_index=${trace.turn_index ?? '—'}`,
      `pipeline_version=${trace.pipeline_version}`,
      `model=${llm?.model || trace.agents.writer.model_used || '—'}`,
      '',
      '=== SYSTEM PROMPT ===',
      llm?.system_prompt || '—',
      '',
      '=== USER PROMPT ===',
      llm?.user_prompt || '—',
      '',
      '=== LLM RESPONSE ===',
      llm?.llm_response_raw || '—',
    ].join('\n');
    try {
      await navigator.clipboard.writeText(payload);
    } catch {
      // Ошибка clipboard не критична для рендера.
    }
  };

  return (
    <div className={`mt-3 rounded-xl border p-3 ${status.className}`}>
      <button type="button" onClick={toggleExpanded} className="w-full flex items-center justify-between gap-3 text-left">
        <div className="text-xs font-semibold text-slate-700">
          Pipeline NEO | {trace.pipeline_version} | {trace.total_latency_ms}ms
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${status.badgeClassName}`}>{status.label}</span>
          <span className="text-xs text-slate-600">{expanded ? '▼' : '▶'}</span>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2">
          <AccordionSection title="Мультиагентный пайплайн">
            <div className="space-y-2">
              <AccordionSection title={`State Analyzer | ${trace.agents.state_analyzer.latency_ms}ms`} nested>
                <div className="text-xs space-y-1">
                  <div>nervous_state: {trace.agents.state_analyzer.nervous_state}</div>
                  <div>intent: {trace.agents.state_analyzer.intent || '—'}</div>
                  <div>confidence: {formatPercent(trace.agents.state_analyzer.confidence)}</div>
                  <div>safety_flag: {trace.agents.state_analyzer.safety_flag ? 'true' : 'false'}</div>
                </div>
              </AccordionSection>

              <AccordionSection title={`Thread Manager | ${trace.agents.thread_manager.latency_ms}ms`} nested>
                <div className="text-xs space-y-1">
                  <div>thread_id: {trace.agents.thread_manager.thread_id || '—'}</div>
                  <div>phase: {trace.agents.thread_manager.phase}</div>
                  <div>relation: {trace.agents.thread_manager.relation_to_thread}</div>
                  <div>continuity: {formatPercent(trace.agents.thread_manager.continuity_score)}</div>
                  {trace.agents.thread_manager.relation_to_thread === 'new_thread' && (
                    <div className="text-[10px] inline-flex rounded-full px-2 py-0.5 bg-blue-100 text-blue-700 font-semibold">NEW THREAD</div>
                  )}
                </div>
              </AccordionSection>

              <AccordionSection title={`Memory Agent | ${trace.agents.memory_retrieval.latency_ms}ms`} nested>
                <div className="text-xs space-y-1">
                  <div>context_turns: {trace.agents.memory_retrieval.context_turns}</div>
                  <div>semantic_hits: {trace.agents.memory_retrieval.semantic_hits_count}</div>
                  <div>has_relevant_knowledge: {trace.agents.memory_retrieval.has_relevant_knowledge ? 'true' : 'false'}</div>
                  <div>rag_query: {memory?.rag_query || '—'}</div>
                </div>
              </AccordionSection>

              <AccordionSection title={`Writer | ${trace.agents.writer.latency_ms}ms`} nested>
                <div className="text-xs space-y-1">
                  <div>response_mode: {trace.agents.writer.response_mode || '—'}</div>
                  <div>tokens_used: {trace.agents.writer.tokens_used ?? llm?.tokens_total ?? '—'}</div>
                  <div>model_used: {trace.agents.writer.model_used ?? llm?.model ?? '—'}</div>
                </div>
              </AccordionSection>

              <AccordionSection title={`Validator | ${trace.agents.validator.latency_ms}ms`} nested>
                <div className="text-xs space-y-1">
                  <div>is_blocked: {trace.agents.validator.is_blocked ? 'true' : 'false'}</div>
                  <div>block_reason: {trace.agents.validator.block_reason || '—'}</div>
                  <div>quality_flags: {trace.agents.validator.quality_flags.length > 0 ? trace.agents.validator.quality_flags.join(', ') : 'none'}</div>
                </div>
              </AccordionSection>

              <div className="rounded-lg border border-slate-200 bg-white p-2">
                <div className="text-xs font-semibold mb-2">Latency timeline</div>
                <div className="w-full h-2 rounded overflow-hidden flex" role="progressbar" aria-label="Latency timeline">
                  {timeline.map((segment) => {
                    const width = `${Math.max(1, Math.round((segment.ms / totalLatency) * 100))}%`;
                    return <div key={segment.key} className={segment.className} style={{ width }} />;
                  })}
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-slate-600">
                  {timeline.map((segment) => (
                    <span key={`${segment.key}-legend`}>
                      {segment.label} {Math.round((segment.ms / totalLatency) * 100)}%
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </AccordionSection>

          {memory && (
            <AccordionSection title={`Контекст памяти | turns: ${trace.agents.memory_retrieval.context_turns} | hits: ${(memory.semantic_hits || []).length}`}>
              <div className="space-y-2">
                <AccordionSection title={`История ходов (${trace.agents.memory_retrieval.context_turns})`} nested>
                  <pre className="text-xs whitespace-pre-wrap">{memory.conversation_context || '—'}</pre>
                </AccordionSection>

                <AccordionSection title={`Чанки в Writer (${(memory.semantic_hits || []).length})`} nested>
                  {(memory.semantic_hits || []).length > 0 ? (
                    memory.semantic_hits.map((hit) => <ChunkCard key={hit.chunk_id || `${hit.source}-${hit.score}`} hit={hit} />)
                  ) : (
                    <div className="text-xs text-slate-500">Нет релевантных чанков</div>
                  )}
                </AccordionSection>

                <AccordionSection title="RAG query" nested>
                  <code className="text-xs whitespace-pre-wrap">{memory.rag_query || '—'}</code>
                </AccordionSection>

                <AccordionSection title="User Profile" nested>
                  <div className="text-xs space-y-1">
                    <div>Паттерны: {(memory.user_profile_patterns || []).join(', ') || '—'}</div>
                    <div>Ценности: {(memory.user_profile_values || []).join(', ') || '—'}</div>
                  </div>
                </AccordionSection>

                <AccordionSection title="Записано в память" nested>
                  <pre className="text-xs whitespace-pre-wrap">{memory.memory_written_preview || '—'}</pre>
                </AccordionSection>
              </div>
            </AccordionSection>
          )}

          {llm && (
            <AccordionSection title={`Полотно LLM | ${llm.model || trace.agents.writer.model_used || '—'} | tokens: ${llm.tokens_total ?? '—'}`}>
              <div className="space-y-2">
                <div className="flex flex-wrap gap-4 text-xs">
                  <span>session: {trace.session_id.slice(0, 8)}...</span>
                  <span>turn: {trace.turn_index ?? '—'}</span>
                  <span>mode: {trace.agents.writer.response_mode || '—'}</span>
                </div>

                <AccordionSection title="System prompt" nested>
                  <pre className="text-xs whitespace-pre-wrap">{llm.system_prompt || '—'}</pre>
                </AccordionSection>

                <AccordionSection title="User prompt (полный контекст)" nested>
                  <pre className="text-xs whitespace-pre-wrap">{llm.user_prompt || '—'}</pre>
                </AccordionSection>

                <AccordionSection title={`LLM response | ${llm.model || '—'} | ${trace.agents.writer.latency_ms}ms`} nested>
                  <pre className="text-xs whitespace-pre-wrap">{llm.llm_response_raw || '—'}</pre>
                </AccordionSection>

                <button type="button" onClick={() => void copyAll()} className="text-xs text-blue-600 hover:underline mt-2">
                  Скопировать всё полотно
                </button>
              </div>
            </AccordionSection>
          )}

          {llm && (
            <AccordionSection title={`Токены и стоимость | ${llm.tokens_total ?? 0} токенов | $${formatMoney(llm.estimated_cost_usd)}`}>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <MetaItem label="MODEL" value={llm.model || trace.agents.writer.model_used || '—'} highlight />
                <MetaItem label="TEMPERATURE" value={llm.temperature ?? '—'} />
                <MetaItem label="MAX TOKENS" value={llm.max_tokens ?? '—'} />
                <MetaItem label="TOKENS prompt" value={llm.tokens_prompt ?? '—'} />
                <MetaItem label="TOKENS completion" value={llm.tokens_completion ?? '—'} />
                <MetaItem label="TOKENS total" value={llm.tokens_total ?? '—'} />
                <MetaItem label="СТОИМОСТЬ хода" value={`$${formatMoney(llm.estimated_cost_usd)}`} highlight />
                <MetaItem label="СТОИМОСТЬ сессии" value={`$${formatMoney(dash?.total_cost_usd)}`} />
              </div>
            </AccordionSection>
          )}

          {hasDiffChanges(diff) && diff && (
            <AccordionSection title="Turn diff">
              <div className="space-y-1">
                {diff.nervous_state_prev !== diff.nervous_state_curr && (
                  <DiffRow label="nervous_state" prev={diff.nervous_state_prev} curr={diff.nervous_state_curr} />
                )}
                {diff.phase_prev !== diff.phase_curr && (
                  <DiffRow label="phase" prev={diff.phase_prev} curr={diff.phase_curr} />
                )}
                <div className="text-xs">
                  relation: <b>{diff.relation_to_thread || '—'}</b>
                </div>
                <div className="text-xs">memory delta: {diff.memory_turns_delta >= 0 ? '+' : ''}{diff.memory_turns_delta} turns</div>
                <div className="text-xs">semantic delta: {diff.semantic_hits_delta >= 0 ? '+' : ''}{diff.semantic_hits_delta} hits</div>
              </div>
            </AccordionSection>
          )}

          {anomalies.length > 0 && (
            <AccordionSection
              title={`Аномалии [${anomalies.length}]`}
              headerClass={anomalies.some((item) => String(item.severity).toUpperCase() === 'ERROR') ? 'text-red-600' : 'text-yellow-600'}
            >
              <div className="space-y-2">
                {anomalies.map((item, index) => (
                  <AnomalyRow key={`${item.code}-${index}`} anomaly={item} />
                ))}
              </div>
            </AccordionSection>
          )}

          {dash && (
            <AccordionSection title="Session Dashboard">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <MetaItem label="TURNS" value={dash.total_turns} />
                <MetaItem label="AVG LATENCY" value={`${dash.avg_latency_ms}ms`} />
                <MetaItem label="TOTAL COST" value={`$${formatMoney(dash.total_cost_usd)}`} highlight />
                <MetaItem label="THREAD SWITCHES" value={dash.thread_switches} />
                <MetaItem label="SAFETY EVENTS" value={dash.safety_events} />
                <MetaItem label="BLOCKS" value={dash.validator_blocks} />
              </div>
              <div className="mt-2 text-xs">
                <span className="text-slate-500">STATE TRAJECTORY: </span>
                {(dash.state_trajectory || []).map((state, index) => (
                  <span key={`${state}-${index}`}>
                    <StateBadge state={state} />
                    {index < dash.state_trajectory.length - 1 && <span className="mx-1 text-slate-400">→</span>}
                  </span>
                ))}
              </div>
            </AccordionSection>
          )}
        </div>
      )}
    </div>
  );
};

export default MultiAgentTraceWidget;
