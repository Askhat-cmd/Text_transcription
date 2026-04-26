import React, { useState } from 'react';

import type { MultiAgentTraceData } from '../../types';

interface MultiAgentTraceWidgetProps {
  trace: MultiAgentTraceData | null;
  isExpanded?: boolean;
  onToggle?: () => void;
  isLoading?: boolean;
}

type SectionKey =
  | 'state_analyzer'
  | 'thread_manager'
  | 'memory_retrieval'
  | 'writer'
  | 'validator';

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function getHeaderStatus(trace: MultiAgentTraceData) {
  if (trace.agents.state_analyzer.safety_flag) {
    return {
      label: 'SAFETY ALERT',
      className: 'bg-red-50 border-red-400',
      badgeClassName: 'bg-red-100 text-red-700',
    };
  }
  if (trace.agents.validator.is_blocked) {
    return {
      label: 'BLOCKED',
      className: 'bg-yellow-50 border-yellow-400',
      badgeClassName: 'bg-yellow-100 text-yellow-700',
    };
  }
  if (trace.agents.thread_manager.relation_to_thread === 'new_thread') {
    return {
      label: 'NEW THREAD',
      className: 'bg-blue-50 border-blue-300',
      badgeClassName: 'bg-blue-100 text-blue-700',
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
  const [openSections, setOpenSections] = useState<Record<SectionKey, boolean>>({
    state_analyzer: true,
    thread_manager: true,
    memory_retrieval: true,
    writer: true,
    validator: true,
  });

  const expanded = isExpanded ?? internalExpanded;
  const toggleExpanded = () => {
    if (onToggle) {
      onToggle();
      return;
    }
    setInternalExpanded((prev) => !prev);
  };

  if (isLoading && !trace) {
    return (
      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 animate-pulse">
        <div className="h-4 w-56 rounded bg-slate-200 mb-3" />
        <div className="h-3 w-full rounded bg-slate-200 mb-2" />
        <div className="h-3 w-5/6 rounded bg-slate-200" />
      </div>
    );
  }

  if (!trace) {
    return null;
  }

  const status = getHeaderStatus(trace);
  const totalLatency = Math.max(trace.total_latency_ms, 1);
  const timelineSegments = [
    {
      key: 'state',
      label: 'State',
      ms: Math.max(trace.agents.state_analyzer.latency_ms, 0),
      className: 'bg-blue-500',
    },
    {
      key: 'thread',
      label: 'Thread',
      ms: Math.max(trace.agents.thread_manager.latency_ms, 0),
      className: 'bg-slate-500',
    },
    {
      key: 'memory',
      label: 'Memory',
      ms: Math.max(trace.agents.memory_retrieval.latency_ms, 0),
      className: 'bg-emerald-500',
    },
    {
      key: 'writer',
      label: 'Writer',
      ms: Math.max(trace.agents.writer.latency_ms, 0),
      className: 'bg-violet-500',
    },
    {
      key: 'validator',
      label: 'Validator',
      ms: Math.max(trace.agents.validator.latency_ms, 0),
      className: 'bg-orange-500',
    },
  ];

  const toggleSection = (key: SectionKey) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className={`mt-3 rounded-xl border p-3 ${status.className}`}>
      <button
        type="button"
        onClick={toggleExpanded}
        className="w-full flex items-center justify-between gap-3 text-left"
      >
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-700">
            Pipeline NEO | {trace.pipeline_version} | {trace.total_latency_ms}ms
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${status.badgeClassName}`}>
            {status.label}
          </span>
          <span className="text-xs text-slate-600">{expanded ? '▼' : '▶'}</span>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2">
          <section className="rounded-lg border border-slate-200 bg-white p-2">
            <button type="button" className="w-full text-left text-xs font-semibold" onClick={() => toggleSection('state_analyzer')}>
              State Analyzer | {trace.agents.state_analyzer.latency_ms}ms
            </button>
            {openSections.state_analyzer && (
              <div className="mt-1 text-xs text-slate-700 space-y-1">
                <div>nervous_state: {trace.agents.state_analyzer.nervous_state}</div>
                <div>intent: {trace.agents.state_analyzer.intent || '—'}</div>
                <div>confidence: {formatPercent(trace.agents.state_analyzer.confidence)}</div>
                <div>safety_flag: {trace.agents.state_analyzer.safety_flag ? 'true' : 'false'}</div>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-2">
            <button type="button" className="w-full text-left text-xs font-semibold" onClick={() => toggleSection('thread_manager')}>
              Thread Manager | {trace.agents.thread_manager.latency_ms}ms
            </button>
            {openSections.thread_manager && (
              <div className="mt-1 text-xs text-slate-700 space-y-1">
                <div>thread_id: {trace.agents.thread_manager.thread_id || '—'}</div>
                <div>phase: {trace.agents.thread_manager.phase}</div>
                <div>relation: {trace.agents.thread_manager.relation_to_thread}</div>
                <div>continuity: {formatPercent(trace.agents.thread_manager.continuity_score)}</div>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-2">
            <button type="button" className="w-full text-left text-xs font-semibold" onClick={() => toggleSection('memory_retrieval')}>
              Memory Agent | {trace.agents.memory_retrieval.latency_ms}ms
            </button>
            {openSections.memory_retrieval && (
              <div className="mt-1 text-xs text-slate-700 space-y-1">
                <div>context_turns: {trace.agents.memory_retrieval.context_turns}</div>
                <div>semantic_hits: {trace.agents.memory_retrieval.semantic_hits_count}</div>
                <div>has_relevant_knowledge: {trace.agents.memory_retrieval.has_relevant_knowledge ? 'true' : 'false'}</div>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-2">
            <button type="button" className="w-full text-left text-xs font-semibold" onClick={() => toggleSection('writer')}>
              Writer | {trace.agents.writer.latency_ms}ms
            </button>
            {openSections.writer && (
              <div className="mt-1 text-xs text-slate-700 space-y-1">
                <div>response_mode: {trace.agents.writer.response_mode || '—'}</div>
                <div>tokens_used: {trace.agents.writer.tokens_used ?? '—'}</div>
                <div>model_used: {trace.agents.writer.model_used ?? '—'}</div>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-2">
            <button type="button" className="w-full text-left text-xs font-semibold" onClick={() => toggleSection('validator')}>
              Validator | {trace.agents.validator.latency_ms}ms
            </button>
            {openSections.validator && (
              <div className="mt-1 text-xs text-slate-700 space-y-1">
                <div>is_blocked: {trace.agents.validator.is_blocked ? 'true' : 'false'}</div>
                <div>block_reason: {trace.agents.validator.block_reason || '—'}</div>
                <div>quality_flags: {trace.agents.validator.quality_flags.length > 0 ? trace.agents.validator.quality_flags.join(', ') : 'none'}</div>
              </div>
            )}
          </section>

          <div className="rounded-lg border border-slate-200 bg-white p-2">
            <div className="text-xs font-semibold mb-2">Latency timeline</div>
            <div className="w-full h-2 rounded overflow-hidden flex" role="progressbar" aria-label="Latency timeline">
              {timelineSegments.map((segment) => {
                const width = `${Math.max(1, Math.round((segment.ms / totalLatency) * 100))}%`;
                return <div key={segment.key} className={segment.className} style={{ width }} />;
              })}
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-slate-600">
              {timelineSegments.map((segment) => (
                <span key={`${segment.key}-legend`}>
                  {segment.label} {Math.round((segment.ms / totalLatency) * 100)}%
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MultiAgentTraceWidget;
