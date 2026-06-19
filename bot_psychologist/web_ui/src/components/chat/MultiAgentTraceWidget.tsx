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
        <span className="text-slate-500">{open ? '▾' : '▸'}</span>
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
  const safePreview = hit.content_preview || hit.content_full || '—';
  return (
    <div className="border rounded p-2 mb-1">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full text-left text-xs flex justify-between"
      >
        <span>{hit.source || hit.chunk_id || 'chunk'}</span>
        <span className="text-slate-400">
          score: {Number.isFinite(hit.score) ? hit.score.toFixed(3) : '0.000'} {open ? '▾' : '▸'}
        </span>
      </button>
      {open && <pre className="mt-1 text-xs whitespace-pre-wrap text-slate-600">{safePreview}</pre>}
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
  const hybrid = memory?.hybrid_retrieval || null;
  const overlayShadow = trace.overlay_shadow && typeof trace.overlay_shadow === 'object'
    ? (trace.overlay_shadow as Record<string, unknown>)
    : null;
  const runtimeConfigTrace = trace.runtime_config_trace && typeof trace.runtime_config_trace === 'object'
    ? (trace.runtime_config_trace as Record<string, unknown>)
    : null;
  const retrievalQueryBuildTrace = trace.retrieval_query_build_trace && typeof trace.retrieval_query_build_trace === 'object'
    ? (trace.retrieval_query_build_trace as Record<string, unknown>)
    : null;
  const writerKbPayloadTrace = trace.writer_kb_payload_trace && typeof trace.writer_kb_payload_trace === 'object'
    ? (trace.writer_kb_payload_trace as Record<string, unknown>)
    : null;
  const semanticCardsTrace = trace.semantic_cards_pilot && typeof trace.semantic_cards_pilot === 'object'
    ? (trace.semantic_cards_pilot as Record<string, unknown>)
    : null;
  const futureGraduationNotes = trace.future_graduation_notes && typeof trace.future_graduation_notes === 'object'
    ? (trace.future_graduation_notes as Record<string, unknown>)
    : null;
  const hybridSummaryAvailable = Boolean(
    trace.hybrid_retrieval_planner_version ||
      trace.hybrid_retrieval_plan ||
      hybrid ||
      trace.planned_composed_query ||
      trace.executed_rag_query
  );
  const overlayShadowAvailable = Boolean(overlayShadow);
  const retrievalQueryBuildAvailable = Boolean(retrievalQueryBuildTrace);
  const writerKbPayloadAvailable = Boolean(writerKbPayloadTrace);
  const semanticCardsAvailable = Boolean(semanticCardsTrace);

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
      // Clipboard failure is non-critical for trace rendering.
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
          <span className="text-xs text-slate-600">{expanded ? '▾' : '▸'}</span>
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

          <AccordionSection
            title={
              hybridSummaryAvailable
                ? `Hybrid Retrieval | ${trace.hybrid_retrieval_planner_mode || hybrid?.planner_mode || 'n/a'} | ${trace.retrieval_action || hybrid?.retrieval_action || 'n/a'}`
                : 'Hybrid Retrieval | not available for this turn'
            }
          >
            {hybridSummaryAvailable ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <MetaItem label="VERSION" value={trace.hybrid_retrieval_planner_version || hybrid?.planner_version || '—'} />
                  <MetaItem label="MODE" value={trace.hybrid_retrieval_planner_mode || hybrid?.planner_mode || '—'} highlight />
                  <MetaItem label="MODEL" value={trace.planner_model || hybrid?.planner_model || '—'} />
                  <MetaItem label="MAX TOKENS" value={trace.planner_max_tokens ?? hybrid?.planner_max_tokens ?? '—'} />
                  <MetaItem label="ACTION" value={trace.retrieval_action || hybrid?.retrieval_action || '—'} highlight />
                  <MetaItem label="UNIVERSAL GATE" value={trace.hybrid_retrieval_universal_gate || hybrid?.universal_gate || '—'} />
                  <MetaItem label="PLAN VALID" value={trace.hybrid_retrieval_plan_valid == null ? '—' : String(Boolean(trace.hybrid_retrieval_plan_valid))} />
                  <MetaItem label="FALLBACK USED" value={trace.hybrid_retrieval_fallback_used == null ? String(Boolean(hybrid?.fallback_used)) : String(Boolean(trace.hybrid_retrieval_fallback_used))} />
                  <MetaItem label="LLM CALLED" value={trace.hybrid_retrieval_llm_called == null ? String(Boolean(hybrid?.llm_called)) : String(Boolean(trace.hybrid_retrieval_llm_called))} />
                  <MetaItem label="WRITER CAN IGNORE RAG" value={trace.writer_can_ignore_rag == null ? String(Boolean(hybrid?.writer_can_ignore_rag)) : String(Boolean(trace.writer_can_ignore_rag))} />
                </div>

                <AccordionSection title="Queries" nested>
                  <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">planned:</span> {trace.planned_composed_query || hybrid?.planned_composed_query || '—'}</div>
                    <div><span className="text-slate-500">executed:</span> {trace.executed_rag_query || hybrid?.executed_rag_query || '—'}</div>
                    <div><span className="text-slate-500">legacy:</span> {trace.legacy_rag_query || hybrid?.legacy_rag_query || '—'}</div>
                    <div><span className="text-slate-500">query_before_rag_proof:</span> {String(Boolean(trace.query_before_rag_proof ?? hybrid?.query_before_rag_proof))}</div>
                    <div><span className="text-slate-500">rag_skipped_reason:</span> {trace.rag_skipped_reason || hybrid?.rag_skipped_reason || '—'}</div>
                    <div><span className="text-slate-500">plan_error:</span> {trace.hybrid_retrieval_plan_error || '—'}</div>
                    <div><span className="text-slate-500">llm_reason:</span> {trace.hybrid_retrieval_llm_reason || hybrid?.llm_reason || '—'}</div>
                  </div>
                </AccordionSection>

                <AccordionSection title="Planner metadata" nested>
                  <div className="space-y-1 text-xs">
                    <div>needed_chunk_types: {(trace.needed_chunk_types || hybrid?.needed_chunk_types || []).join(', ') || '—'}</div>
                    <div>mechanism_hints: {(trace.mechanism_hints || hybrid?.mechanism_hints || []).join(', ') || '—'}</div>
                    <div>allowed_use_filter_hint: {(trace.allowed_use_filter_hint || hybrid?.allowed_use_filter_hint || []).join(', ') || '—'}</div>
                    <div>constraints_for_writer: {(trace.constraints_for_writer || hybrid?.constraints_for_writer || []).join(', ') || '—'}</div>
                    <div>depth_level_hint: {trace.depth_level_hint ?? hybrid?.depth_level_hint ?? '—'}</div>
                    <div>safety_layer_required: {String(Boolean(trace.safety_layer_required ?? hybrid?.safety_layer_required))}</div>
                    <div>retrieval_gap_reason: {trace.retrieval_gap_reason || hybrid?.retrieval_gap_reason || '—'}</div>
                  </div>
                </AccordionSection>
              </div>
            ) : (
              <div className="text-xs text-slate-500">Hybrid Retrieval: not available for this turn</div>
            )}
          </AccordionSection>

          {retrievalQueryBuildAvailable && (
            <AccordionSection
              title={`Retrieval Query Build | ${String(retrievalQueryBuildTrace?.primary_path || 'unknown')} | ${String(retrievalQueryBuildTrace?.current_turn_focus_status || 'n/a')}`}
            >
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <MetaItem label="ENABLED" value={String(Boolean(retrievalQueryBuildTrace?.enabled))} />
                  <MetaItem label="PRIMARY PATH" value={String(retrievalQueryBuildTrace?.primary_path || '—')} highlight />
                  <MetaItem label="PLANNER QUERY USED" value={String(Boolean(retrievalQueryBuildTrace?.planner_query_used))} />
                  <MetaItem label="STATUS" value={String(retrievalQueryBuildTrace?.current_turn_focus_status || '—')} />
                  <MetaItem label="DEDUPE APPLIED" value={String(Boolean(retrievalQueryBuildTrace?.dedupe_applied))} />
                  <MetaItem label="DUPLICATE COUNT" value={String(retrievalQueryBuildTrace?.duplicate_fragment_count ?? 0)} />
                  <MetaItem label="TRUNCATION" value={String(Boolean(retrievalQueryBuildTrace?.truncation_applied))} />
                  <MetaItem label="MID-WORD CUT" value={String(Boolean(retrievalQueryBuildTrace?.query_truncated_mid_word))} />
                </div>

                <AccordionSection title="Query details" nested>
                  <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">raw_user_query:</span> {String(retrievalQueryBuildTrace?.raw_user_query || '—')}</div>
                    <div><span className="text-slate-500">planned_query:</span> {String(retrievalQueryBuildTrace?.planned_query || '—')}</div>
                    <div><span className="text-slate-500">canonical_query:</span> {String(retrievalQueryBuildTrace?.canonical_query || '—')}</div>
                    <div><span className="text-slate-500">executed_query:</span> {String(retrievalQueryBuildTrace?.executed_query || '—')}</div>
                    <div><span className="text-slate-500">truncation_strategy:</span> {String(retrievalQueryBuildTrace?.truncation_strategy || '—')}</div>
                    <div><span className="text-slate-500">fallback_reason:</span> {String(retrievalQueryBuildTrace?.fallback_reason || '—')}</div>
                  </div>
                </AccordionSection>

                <AccordionSection title="Context reasons" nested>
                  <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">previous_user_query_included:</span> {String(Boolean(retrievalQueryBuildTrace?.previous_user_query_included))}</div>
                    <div><span className="text-slate-500">previous_user_query_inclusion_reason:</span> {String(retrievalQueryBuildTrace?.previous_user_query_inclusion_reason || '—')}</div>
                    <div><span className="text-slate-500">inherited_topic_used:</span> {String(Boolean(retrievalQueryBuildTrace?.inherited_topic_used))}</div>
                    <div><span className="text-slate-500">inherited_topic_reason:</span> {String(retrievalQueryBuildTrace?.inherited_topic_reason || '—')}</div>
                    <div><span className="text-slate-500">inherited_topic:</span> {String(retrievalQueryBuildTrace?.inherited_topic || '—')}</div>
                  </div>
                </AccordionSection>
              </div>
            </AccordionSection>
          )}

          {writerKbPayloadAvailable && (
            <AccordionSection
              title={`Writer KB Payload | ${String(writerKbPayloadTrace?.primary_path || (writerKbPayloadTrace?.enabled ? 'enabled' : 'disabled'))} | chunks ${String(writerKbPayloadTrace?.payload_chunk_count ?? 0)}`}
            >
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <MetaItem label="TRACE VERSION" value={String(writerKbPayloadTrace?.schema_version || '—')} />
                  <MetaItem label="PRIMARY PATH" value={String(writerKbPayloadTrace?.primary_path || '—')} highlight />
                  <MetaItem label="STATUS" value={String(writerKbPayloadTrace?.status || '—')} />
                  <MetaItem label="INPUT RAG COUNT" value={String(writerKbPayloadTrace?.input_rag_for_writer_count ?? 0)} />
                  <MetaItem label="PAYLOAD CHUNKS" value={String(writerKbPayloadTrace?.payload_chunk_count ?? 0)} highlight />
                  <MetaItem label="TOTAL SENT CHARS" value={String(writerKbPayloadTrace?.total_sent_char_count ?? 0)} />
                  <MetaItem label="SENT TO WRITER" value={String(writerKbPayloadTrace?.payload_sent_to_writer_char_count ?? 0)} />
                  <MetaItem label="TRACE PREVIEW CHARS" value={String(writerKbPayloadTrace?.payload_display_preview_char_count ?? 0)} />
                  <MetaItem label="DISPLAY IS PREVIEW" value={String(Boolean(writerKbPayloadTrace?.payload_display_is_preview))} />
                  <MetaItem label="TRUNCATED CHUNKS" value={String(writerKbPayloadTrace?.truncated_chunk_count ?? 0)} />
                  <MetaItem label="MID-SENTENCE CUTS" value={String(writerKbPayloadTrace?.mid_sentence_cut_count ?? 0)} />
                  <MetaItem label="OVERLAY USED" value={String(writerKbPayloadTrace?.overlay_metadata_used_count ?? 0)} />
                  <MetaItem label="FALLBACK PRIMARY" value={String(Boolean(writerKbPayloadTrace?.fallback_is_primary))} />
                </div>

                {runtimeConfigTrace && (
                  <AccordionSection title="Effective runtime config" nested>
                    <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">app_env:</span> {String(runtimeConfigTrace.app_env || '—')}</div>
                    <div><span className="text-slate-500">backend_pid:</span> {String(runtimeConfigTrace.backend_pid || '—')}</div>
                    <div><span className="text-slate-500">backend_start_time:</span> {String(runtimeConfigTrace.backend_start_time || '—')}</div>
                      <div><span className="text-slate-500">writer_kb_payload_enabled:</span> {String(Boolean(runtimeConfigTrace.writer_kb_payload_enabled))}</div>
                      <div><span className="text-slate-500">writer_kb_payload_enabled_source:</span> {String(runtimeConfigTrace.writer_kb_payload_enabled_source || '—')}</div>
                      <div><span className="text-slate-500">overlay_shadow_trace_enabled:</span> {String(Boolean(runtimeConfigTrace.overlay_shadow_trace_enabled))}</div>
                      <div><span className="text-slate-500">debug_trace_enabled:</span> {String(Boolean(runtimeConfigTrace.debug_trace_enabled))}</div>
                    </div>
                  </AccordionSection>
                )}

                <AccordionSection title="Payload path" nested>
                  <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">payload_version:</span> {String(writerKbPayloadTrace?.payload_version || '—')}</div>
                    <div><span className="text-slate-500">fallback_reason:</span> {String(writerKbPayloadTrace?.fallback_reason || '—')}</div>
                    <div><span className="text-slate-500">warning:</span> {String(writerKbPayloadTrace?.warning || '—')}</div>
                    <div><span className="text-slate-500">configured_source:</span> {String(writerKbPayloadTrace?.configured_source || '—')}</div>
                    <div><span className="text-slate-500">full_text_sent_to_writer:</span> {String(Boolean(writerKbPayloadTrace?.payload_full_text_sent_to_writer))}</div>
                    <div><span className="text-slate-500">full_text_exposed_in_web_trace:</span> {String(Boolean(writerKbPayloadTrace?.payload_full_text_exposed_in_web_trace))}</div>
                  </div>
                </AccordionSection>

                <AccordionSection title="Payload warnings" nested>
                  <div className="text-xs">
                    {Array.isArray(writerKbPayloadTrace?.warnings)
                      ? (writerKbPayloadTrace?.warnings as unknown[]).join(', ') || '—'
                      : '—'}
                  </div>
                </AccordionSection>

                <AccordionSection title="Payload chunks" nested>
                  {Array.isArray(writerKbPayloadTrace?.chunk_summaries) && (writerKbPayloadTrace?.chunk_summaries as unknown[]).length > 0 ? (
                    <div className="space-y-2">
                      {(writerKbPayloadTrace?.chunk_summaries as Array<Record<string, unknown>>).map((item, index) => (
                        <div
                          key={String(item.chunk_id || index)}
                          className="rounded-lg border border-slate-200 bg-white p-2 text-xs space-y-1"
                        >
                          <div className="font-semibold text-slate-700">
                            {String(item.chunk_id || '—')}
                          </div>
                          <div><span className="text-slate-500">source_doc:</span> {String(item.source_doc || '—')}</div>
                          <div><span className="text-slate-500">chunk_type:</span> {String(item.chunk_type || '—')}</div>
                          <div><span className="text-slate-500">quote_policy:</span> {String(item.quote_policy || '—')}</div>
                          <div><span className="text-slate-500">allowed_use:</span> {Array.isArray(item.allowed_use) ? item.allowed_use.join(', ') || '—' : '—'}</div>
                          <div><span className="text-slate-500">payload_item_origin:</span> {String(item.payload_item_origin || '—')}</div>
                          <div><span className="text-slate-500">semantic_card_id:</span> {String(item.semantic_card_id || '—')}</div>
                          <div><span className="text-slate-500">semantic_card_pack_id:</span> {String(item.semantic_card_pack_id || '—')}</div>
                          <div><span className="text-slate-500">writer_can_ignore:</span> {String(Boolean(item.writer_can_ignore))}</div>
                          <div><span className="text-slate-500">applied_as_authority:</span> {String(Boolean(item.applied_as_authority))}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500">No structured payload chunks for this turn</div>
                  )}
                </AccordionSection>

                {futureGraduationNotes && (
                  <AccordionSection title="Future graduation notes" nested>
                    <div className="space-y-1 text-xs">
                      <div><span className="text-slate-500">payload_source:</span> {String(futureGraduationNotes.payload_source || '—')}</div>
                      <div><span className="text-slate-500">legacy_semantic_hits_used:</span> {String(Boolean(futureGraduationNotes.legacy_semantic_hits_used))}</div>
                      <div><span className="text-slate-500">structured_payload_used:</span> {String(Boolean(futureGraduationNotes.structured_payload_used))}</div>
                      <div><span className="text-slate-500">truncation_strategy:</span> {String(futureGraduationNotes.truncation_strategy || '—')}</div>
                    </div>
                  </AccordionSection>
                )}
              </div>
            </AccordionSection>
          )}

          {semanticCardsAvailable && (
            <AccordionSection
              title={`Semantic Cards Pilot | ${String(semanticCardsTrace?.enabled ? 'enabled' : 'disabled')} | cards ${String(semanticCardsTrace?.selected_card_count ?? 0)}`}
            >
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <MetaItem label="TRACE VERSION" value={String(semanticCardsTrace?.schema_version || '—')} />
                  <MetaItem label="STATUS" value={String(semanticCardsTrace?.status || '—')} highlight />
                  <MetaItem label="PACK ID" value={String(semanticCardsTrace?.pack_id || '—')} />
                  <MetaItem label="LOADED CARDS" value={String(semanticCardsTrace?.loaded_card_count ?? 0)} />
                  <MetaItem label="SELECTED COUNT" value={String(semanticCardsTrace?.selected_card_count ?? 0)} highlight />
                  <MetaItem label="ENABLED SOURCE" value={String(semanticCardsTrace?.enabled_source || '—')} />
                  <MetaItem label="ADAPTER ENABLED" value={String(Boolean(semanticCardsTrace?.adapter_enabled))} />
                  <MetaItem label="WRITER PAYLOAD ENRICHED" value={String(Boolean(semanticCardsTrace?.writer_payload_enriched))} />
                  <MetaItem label="WRITER CAN IGNORE" value={String(Boolean(semanticCardsTrace?.writer_can_ignore))} />
                  <MetaItem label="APPLIED AS AUTHORITY" value={String(Boolean(semanticCardsTrace?.applied_as_authority))} />
                </div>

                <AccordionSection title="Selection details" nested>
                  <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">selection_reason:</span> {String(semanticCardsTrace?.selection_reason || '—')}</div>
                    <div><span className="text-slate-500">suppressed_reason:</span> {String(semanticCardsTrace?.suppressed_reason || '—')}</div>
                    <div><span className="text-slate-500">authority:</span> {String(semanticCardsTrace?.authority || '—')}</div>
                    <div><span className="text-slate-500">runtime_mode:</span> {String(semanticCardsTrace?.runtime_mode || '—')}</div>
                    <div><span className="text-slate-500">error:</span> {String(semanticCardsTrace?.error || '—')}</div>
                  </div>
                </AccordionSection>

                <AccordionSection title="Selected card ids" nested>
                  <div className="text-xs">
                    {Array.isArray(semanticCardsTrace?.selected_card_ids)
                      ? (semanticCardsTrace?.selected_card_ids as unknown[]).join(', ') || '—'
                      : '—'}
                  </div>
                </AccordionSection>

                <AccordionSection title="Candidate scores" nested>
                  {Array.isArray(semanticCardsTrace?.candidate_scores) && (semanticCardsTrace?.candidate_scores as unknown[]).length > 0 ? (
                    <div className="space-y-2">
                      {(semanticCardsTrace?.candidate_scores as Array<Record<string, unknown>>).map((item, index) => (
                        <div key={String(item.card_id || index)} className="rounded-lg border border-slate-200 bg-white p-2 text-xs space-y-1">
                          <div className="font-semibold text-slate-700">{String(item.card_id || '—')}</div>
                          <div><span className="text-slate-500">score:</span> {String(item.score ?? '0')}</div>
                          <div><span className="text-slate-500">reasons:</span> {Array.isArray(item.reasons) ? item.reasons.join(', ') || '—' : '—'}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500">No candidate scores recorded for this turn</div>
                  )}
                </AccordionSection>
              </div>
            </AccordionSection>
          )}

          {overlayShadowAvailable && (
            <AccordionSection
              title={`Overlay Shadow | ${String(overlayShadow?.mode || 'trace_only')} | ${String(overlayShadow?.status || (overlayShadow?.enabled ? 'ok' : 'disabled'))}`}
            >
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <MetaItem label="ENABLED" value={String(Boolean(overlayShadow?.enabled))} />
                  <MetaItem label="WOULD HELP" value={String(Boolean(overlayShadow?.would_help))} highlight />
                  <MetaItem label="MODE" value={String(overlayShadow?.mode || 'trace_only')} />
                  <MetaItem label="MATCH COUNT" value={String(overlayShadow?.match_count ?? 0)} />
                  <MetaItem label="WRITER VISIBLE" value={String(Boolean(overlayShadow?.used_for_writer))} />
                  <MetaItem label="RETRIEVAL AUTHORITY" value={String(Boolean(overlayShadow?.used_for_retrieval_execution))} />
                </div>

                <AccordionSection title="Overlay summary" nested>
                  <div className="space-y-1 text-xs">
                    <div><span className="text-slate-500">source_prd:</span> {String(overlayShadow?.overlay_source_prd || '—')}</div>
                    <div><span className="text-slate-500">batch_id:</span> {String(overlayShadow?.batch_id || '—')}</div>
                    <div><span className="text-slate-500">overlay_item_count:</span> {String(overlayShadow?.overlay_item_count ?? '—')}</div>
                    <div><span className="text-slate-500">reason:</span> {String(overlayShadow?.reason || '—')}</div>
                    <div><span className="text-slate-500">warnings:</span> {Array.isArray(overlayShadow?.warnings) ? (overlayShadow?.warnings as unknown[]).join(', ') || '—' : '—'}</div>
                    <div><span className="text-slate-500">safety_flags:</span> {Array.isArray(overlayShadow?.safety_flags) ? (overlayShadow?.safety_flags as unknown[]).join(', ') || '—' : '—'}</div>
                  </div>
                </AccordionSection>

                <AccordionSection title="Matched candidates" nested>
                  {Array.isArray(overlayShadow?.matched_candidates) && (overlayShadow?.matched_candidates as unknown[]).length > 0 ? (
                    <div className="space-y-2">
                      {(overlayShadow?.matched_candidates as Array<Record<string, unknown>>).map((item, index) => (
                        <div
                          key={String(item.candidate_id || index)}
                          className="rounded-lg border border-slate-200 bg-white p-2 text-xs space-y-1"
                        >
                          <div className="font-semibold text-slate-700">
                            {String(item.chunk_type || 'unknown')} | score {String(item.score ?? '0')}
                          </div>
                          <div><span className="text-slate-500">candidate_id:</span> {String(item.candidate_id || '—')}</div>
                          <div><span className="text-slate-500">matched_terms:</span> {Array.isArray(item.matched_terms) ? item.matched_terms.join(', ') || '—' : '—'}</div>
                          <div><span className="text-slate-500">focus_tags:</span> {Array.isArray(item.focus_tags) ? item.focus_tags.join(', ') || '—' : '—'}</div>
                          <div><span className="text-slate-500">safe_translation:</span> {String(item.safe_user_translation_preview || '—')}</div>
                          <div><span className="text-slate-500">allowed_writer_use:</span> {String(item.allowed_writer_use_preview || '—')}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500">No overlay matches for this turn</div>
                  )}
                </AccordionSection>
              </div>
            </AccordionSection>
          )}

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

