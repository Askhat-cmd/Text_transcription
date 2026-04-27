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
      semantic_hits: [
        {
          chunk_id: 'c1',
          source: 'lecture_1',
          score: 0.912,
          content_preview: 'preview',
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

  it('expands chunk card and shows full content', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );

    clickButtonContains(harness.container, 'Контекст памяти');
    clickButtonContains(harness.container, 'Чанки в Writer');
    clickButtonContains(harness.container, 'score:');

    expect(harness.container.textContent).toContain('content_full_mock');
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
