import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it } from 'vitest';

import type { MultiAgentTraceData } from '../../types';
import { MultiAgentTraceWidget } from './MultiAgentTraceWidget';

function createTrace(): MultiAgentTraceData {
  return {
    session_id: 's-1',
    turn_index: 1,
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
        context_turns: 4,
        semantic_hits_count: 3,
        has_relevant_knowledge: true,
      },
      writer: {
        latency_ms: 580,
        response_mode: 'presence',
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

describe('MultiAgentTraceWidget', () => {
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('renders collapsed header with total latency by default', () => {
    const trace = createTrace();
    const harness = renderWidget(React.createElement(MultiAgentTraceWidget, { trace }));

    expect(harness.container.textContent).toContain('1240ms');
    expect(harness.container.textContent).not.toContain('State Analyzer');

    harness.cleanup();
  });

  it('expands sections on header click', () => {
    const trace = createTrace();
    const harness = renderWidget(React.createElement(MultiAgentTraceWidget, { trace }));
    const button = harness.container.querySelector('button');
    expect(button).not.toBeNull();

    act(() => {
      button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(harness.container.textContent).toContain('State Analyzer');
    expect(harness.container.textContent).toContain('Validator');

    harness.cleanup();
  });

  it('shows red header class when safety flag is true', () => {
    const trace = createTrace();
    trace.agents.state_analyzer.safety_flag = true;
    const harness = renderWidget(React.createElement(MultiAgentTraceWidget, { trace }));

    const firstBlock = harness.container.firstElementChild as HTMLElement | null;
    expect(firstBlock?.className || '').toContain('border-red-400');

    harness.cleanup();
  });

  it('shows validator block reason when blocked and expanded', () => {
    const trace = createTrace();
    trace.agents.validator.is_blocked = true;
    trace.agents.validator.block_reason = 'unsafe content';
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace,
        isExpanded: true,
      })
    );

    expect(harness.container.textContent).toContain('unsafe content');

    harness.cleanup();
  });

  it('returns null when trace is null', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: null,
      })
    );

    expect(harness.container.firstElementChild).toBeNull();

    harness.cleanup();
  });

  it('renders latency timeline progressbar in expanded mode', () => {
    const trace = createTrace();
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace,
        isExpanded: true,
      })
    );

    const bar = harness.container.querySelector('[role="progressbar"]');
    expect(bar).not.toBeNull();

    harness.cleanup();
  });

  it('does not crash when trace toggles null -> object -> null', () => {
    const trace = createTrace();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root: Root = createRoot(container);

    expect(() => {
      act(() => {
        root.render(React.createElement(MultiAgentTraceWidget, { trace: null, isLoading: true }));
      });
      act(() => {
        root.render(React.createElement(MultiAgentTraceWidget, { trace }));
      });
      act(() => {
        root.render(React.createElement(MultiAgentTraceWidget, { trace: null }));
      });
    }).not.toThrow();

    act(() => {
      root.unmount();
    });
    container.remove();
  });
});
