import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MessageItem } from './Message';
import { apiService, TraceUnavailableError } from '../../services/api.service';

function mountMessage(element: React.ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  act(() => {
    root.render(element);
  });

  return {
    container,
    cleanup(): void {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

describe('MessageItem trace availability', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    localStorage.clear();
    apiService.setAPIKey('dev-key-001');
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('shows owner-visible unavailable notice when exact trace is missing', async () => {
    vi.useFakeTimers();
    vi.spyOn(apiService, 'getMultiAgentTrace').mockRejectedValue(
      new TraceUnavailableError('No multiagent trace found for requested turn', {
        status: 'unavailable',
        requested_turn_index: 5,
        reason_code: 'requested_turn_missing',
        reason: 'Exact trace for turn 5 is unavailable for this session scope',
        available_turn_indices: [1, 2, 3],
      })
    );

    const mounted = mountMessage(
      React.createElement(MessageItem, {
        sessionId: 'sess-1',
        message: {
          id: 'sess-1-b-4',
          role: 'bot',
          content: 'answer',
          timestamp: new Date('2026-06-30T12:00:00Z'),
          turnNumber: 5,
        },
      })
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(mounted.container.textContent).toContain('Trace unavailable');
    expect(mounted.container.textContent).toContain('Exact trace for turn 5 is unavailable');
    expect(mounted.container.textContent).toContain('available turns: 1, 2, 3');

    mounted.cleanup();
    vi.useRealTimers();
  });
});
