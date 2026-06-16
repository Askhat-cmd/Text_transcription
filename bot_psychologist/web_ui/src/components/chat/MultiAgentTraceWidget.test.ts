import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MultiAgentTraceData } from '../../types';
import { MultiAgentTraceWidget } from './MultiAgentTraceWidget';

function createTrace(): MultiAgentTraceData {
  return {
    session_id: 'session-12345678',
    turn_index: 2,
    pipeline_version: 'multiagent_v1',
    total_latency_ms: 1240,
    agents: {
      state_analyzer: {
        latency_ms: 310,
        nervous_state: 'calm',
        intent: 'support',
        safety_flag: false,
        confidence: 0.87,
      },
      thread_manager: {
        latency_ms: 45,
        thread_id: 'th-1',
        phase: 'exploring',
        relation_to_thread: 'continue',
        continuity_score: 0.72,
      },
      memory_retrieval: {
        latency_ms: 280,
        context_turns: 2,
        semantic_hits_count: 1,
        has_relevant_knowledge: true,
      },
      writer: {
        latency_ms: 580,
        response_mode: 'validate',
        tokens_used: 412,
        model_used: 'gpt-5-mini',
      },
      validator: {
        latency_ms: 25,
        is_blocked: false,
        block_reason: null,
        quality_flags: [],
      },
    },
    memory_context: {
      conversation_context: 'User: привет\nAssistant: привет!\n---',
      rag_query: 'привет поддержка',
      hybrid_retrieval: {
        planner_version: 'hybrid_retrieval_planner_v1_r1',
        planner_mode: 'shadow',
        planner_model: 'gpt-5-nano',
        planner_max_tokens: 320,
        retrieval_action: 'query_kb',
        planned_composed_query: 'паника контроль механизм',
        executed_rag_query: 'паника контроль механизм',
        legacy_rag_query: 'привет поддержка',
        query_before_rag_proof: true,
        needed_chunk_types: ['mechanism', 'concept'],
        mechanism_hints: ['panic_regulation'],
        depth_level_hint: 1,
        safety_layer_required: false,
        allowed_use_filter_hint: ['writer_support'],
        constraints_for_writer: ['no_theory'],
        retrieval_gap_reason: '',
        writer_can_ignore_rag: true,
        rag_skipped_reason: '',
        llm_called: false,
        llm_reason: 'universal_gate_resolved',
        fallback_used: false,
        universal_gate: 'clear_kb_ask',
      },
      semantic_hits: [
        {
          chunk_id: 'c1',
          source: 'lecture_1',
          score: 0.912,
          content_preview: 'safe_preview_mock',
          content_full: 'content_full_mock',
        },
      ],
      user_profile_patterns: ['pattern_1'],
      user_profile_values: ['value_1'],
      memory_written_preview: 'user: привет\nassistant: привет',
    },
    writer_llm: {
      system_prompt: 'SYSTEM PROMPT MOCK',
      user_prompt: 'USER PROMPT MOCK',
      llm_response_raw: 'LLM RESPONSE MOCK',
      model: 'gpt-5-mini',
      temperature: 0.7,
      max_tokens: 600,
      tokens_prompt: 300,
      tokens_completion: 112,
      tokens_total: 412,
      estimated_cost_usd: 0.000149,
    },
    turn_diff: {
      nervous_state_prev: 'curious',
      nervous_state_curr: 'calm',
      phase_prev: 'exploring',
      phase_curr: 'deepening',
      relation_to_thread: 'continue',
      memory_turns_delta: 1,
      semantic_hits_delta: 1,
    },
    anomalies: [
      {
        code: 'SLOW_WRITER',
        severity: 'WARN',
        message: 'Writer занял 580ms',
      },
    ],
    session_dashboard: {
      total_turns: 5,
      avg_latency_ms: 1100,
      total_cost_usd: 0.005,
      state_trajectory: ['calm', 'curious', 'confused'],
      thread_switches: 0,
      safety_events: 0,
      validator_blocks: 0,
    },
    hybrid_retrieval_plan: {
      retrieval_action: 'query_kb',
      needed_chunk_types: ['mechanism', 'concept'],
      mechanism_hints: ['panic_regulation'],
      constraints_for_writer: ['no_theory'],
    },
    hybrid_retrieval_planner_version: 'hybrid_retrieval_planner_v1_r1',
    hybrid_retrieval_planner_mode: 'shadow',
    hybrid_retrieval_plan_valid: true,
    hybrid_retrieval_plan_error: null,
    hybrid_retrieval_universal_gate: 'clear_kb_ask',
    hybrid_retrieval_llm_called: false,
    hybrid_retrieval_llm_reason: 'universal_gate_resolved',
    hybrid_retrieval_fallback_used: false,
    planned_composed_query: 'паника контроль механизм',
    executed_rag_query: 'паника контроль механизм',
    legacy_rag_query: 'привет поддержка',
    query_before_rag_proof: true,
    retrieval_action: 'query_kb',
    rag_skipped_reason: '',
    needed_chunk_types: ['mechanism', 'concept'],
    mechanism_hints: ['panic_regulation'],
    retrieval_gap_reason: '',
    writer_can_ignore_rag: true,
    depth_level_hint: 1,
    safety_layer_required: false,
    allowed_use_filter_hint: ['writer_support'],
    constraints_for_writer: ['no_theory'],
    planner_model: 'gpt-5-nano',
    planner_max_tokens: 320,
    overlay_shadow: {
      schema_version: 'overlay_shadow_trace_v1',
      enabled: true,
      status: 'ok',
      mode: 'trace_only',
      overlay_source_prd: 'PRD-047.20',
      batch_id: 'batch_1',
      overlay_item_count: 12,
      used_for_writer: false,
      used_for_retrieval_execution: false,
      would_help: true,
      match_count: 1,
      warnings: ['non_live_overlay_source'],
      safety_flags: ['trace_only'],
      matched_candidates: [
        {
          candidate_id: 'cand-1',
          chunk_type: 'mechanism',
          score: 4.25,
          matched_terms: ['контроль', 'страх'],
          focus_tags: ['control_as_safety'],
          safe_user_translation_preview: 'Избегание может быть попыткой защиты.',
          allowed_writer_use_preview: 'Только как мягкая гипотеза.',
        },
      ],
    },
  };
}

function renderWidget(element: React.ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);
  act(() => {
    root.render(element);
  });
  return {
    container,
    root,
    cleanup() {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function rerenderWidget(root: Root, element: React.ReactElement): void {
  act(() => {
    root.render(element);
  });
}

function clickButtonContains(container: HTMLElement, text: string): void {
  const target = Array.from(container.querySelectorAll('button')).find((btn) =>
    (btn.textContent || '').includes(text)
  );
  expect(target).toBeTruthy();
  act(() => {
    target?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

describe('MultiAgentTraceWidget (rev2)', () => {
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('renders collapsed header by default', () => {
    const harness = renderWidget(React.createElement(MultiAgentTraceWidget, { trace: createTrace() }));
    expect(harness.container.textContent).toContain('Pipeline NEO');
    expect(harness.container.textContent).toContain('1240ms');
    expect(harness.container.textContent).not.toContain('Мультиагентный пайплайн');
    harness.cleanup();
  });

  it('renders LLM canvas block in expanded mode', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Полотно LLM');
    clickButtonContains(harness.container, 'Полотно LLM');
    clickButtonContains(harness.container, 'System prompt');
    expect(harness.container.textContent).toContain('SYSTEM PROMPT MOCK');
    harness.cleanup();
  });

  it('expands chunk card and shows safe preview content', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );

    clickButtonContains(harness.container, 'Контекст памяти');
    clickButtonContains(harness.container, 'Чанки в Writer');
    clickButtonContains(harness.container, 'score:');

    expect(harness.container.textContent).toContain('safe_preview_mock');
    harness.cleanup();
  });

  it('falls back to content_full when preview is empty', () => {
    const trace = createTrace();
    const hits = trace.memory_context?.semantic_hits;
    expect(Array.isArray(hits) && hits.length > 0).toBe(true);
    if (!hits || hits.length === 0) {
      throw new Error('semantic hits missing in trace fixture');
    }
    hits[0].content_preview = '';
    hits[0].content_full = 'content_full_fallback';
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace,
        isExpanded: true,
      })
    );

    clickButtonContains(harness.container, 'Контекст памяти');
    clickButtonContains(harness.container, 'Чанки в Writer');
    clickButtonContains(harness.container, 'score:');

    expect(harness.container.textContent).toContain('content_full_fallback');
    harness.cleanup();
  });

  it('copies llm canvas to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    clickButtonContains(harness.container, 'Полотно LLM');
    const copyButton = Array.from(harness.container.querySelectorAll('button')).find((btn) =>
      (btn.textContent || '').includes('Скопировать всё полотно')
    );
    expect(copyButton).toBeTruthy();
    await act(async () => {
      copyButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText.mock.calls[0][0]).toContain('SYSTEM PROMPT MOCK');
    harness.cleanup();
  });

  it('renders session dashboard trajectory and anomalies', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Session Dashboard');
    clickButtonContains(harness.container, 'Session Dashboard');
    clickButtonContains(harness.container, 'Аномалии');
    expect(harness.container.textContent).toContain('calm');
    expect(harness.container.textContent).toContain('SLOW_WRITER');
    harness.cleanup();
  });

  it('renders hybrid retrieval visibility block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Hybrid Retrieval');
    clickButtonContains(harness.container, 'Hybrid Retrieval');
    clickButtonContains(harness.container, 'Queries');
    clickButtonContains(harness.container, 'Planner metadata');
    expect(harness.container.textContent).toContain('gpt-5-nano');
    expect(harness.container.textContent).toContain('паника контроль механизм');
    expect(harness.container.textContent).toContain('panic_regulation');
    harness.cleanup();
  });

  it('renders overlay shadow trace block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Overlay Shadow');
    clickButtonContains(harness.container, 'Overlay Shadow');
    clickButtonContains(harness.container, 'Overlay summary');
    clickButtonContains(harness.container, 'Matched candidates');
    expect(harness.container.textContent).toContain('PRD-047.20');
    expect(harness.container.textContent).toContain('control_as_safety');
    expect(harness.container.textContent).toContain('non_live_overlay_source');
    harness.cleanup();
  });

  it('handles loading-to-trace transition without hook crash', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: null,
        isLoading: true,
      })
    );
    expect(harness.container.textContent).toContain('');

    rerenderWidget(
      harness.root,
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isLoading: false,
      })
    );
    expect(harness.container.textContent).toContain('Pipeline NEO');
    harness.cleanup();
  });
});
