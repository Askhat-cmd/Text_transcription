import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiService, TraceUnavailableError } from '../services/api.service';
import { useMultiAgentTrace } from './useMultiAgentTrace';

function mountUseMultiAgentTrace(
  sessionId: string | undefined,
  messageId: string,
  turnNumber: number | undefined,
  enabled: boolean
) {
  let latest: ReturnType<typeof useMultiAgentTrace> | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useMultiAgentTrace(sessionId, messageId, turnNumber, enabled);
    return null;
  }

  act(() => {
    root.render(React.createElement(Harness));
  });

  const flush = async (): Promise<void> => {
    await act(async () => {
      await Promise.resolve();
    });
  };

  return {
    get state() {
      if (!latest) {
        throw new Error('Hook state is not initialized');
      }
      return latest;
    },
    flush,
    cleanup(): void {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

describe('useMultiAgentTrace', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('prefers explicit turnNumber over legacy message-id parsing', async () => {
    const getTraceSpy = vi.spyOn(apiService, 'getMultiAgentTrace').mockResolvedValue({
      turn_index: 5,
      trace_availability: {
        status: 'available',
        resolved_turn_index: 5,
      },
    } as any);

    const harness = mountUseMultiAgentTrace('sess-1', 'sess-1-b-0', 5, true);
    await harness.flush();

    expect(getTraceSpy).toHaveBeenCalledWith('sess-1', 5);
    expect(harness.state.trace?.turn_index).toBe(5);
    expect(harness.state.availability?.status).toBe('available');

    harness.cleanup();
  });

  it('rejects mismatched trace turn instead of showing another turn canvas', async () => {
    vi.spyOn(apiService, 'getMultiAgentTrace').mockResolvedValue({
      turn_index: 2,
    } as any);

    const harness = mountUseMultiAgentTrace('sess-1', 'sess-1-b-0', 5, true);
    await harness.flush();

    expect(harness.state.trace).toBeNull();
    expect(harness.state.availability?.reason_code).toBe('turn_mismatch');
    expect(harness.state.error).toContain('expected 5, got 2');

    harness.cleanup();
  });

  it('surfaces structured unavailable state after retries are exhausted', async () => {
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

    const harness = mountUseMultiAgentTrace('sess-1', 'sess-1-b-4', 5, true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    await harness.flush();

    expect(harness.state.trace).toBeNull();
    expect(harness.state.availability?.status).toBe('unavailable');
    expect(harness.state.availability?.reason_code).toBe('requested_turn_missing');
    expect(harness.state.error).toContain('requested turn');

    harness.cleanup();
    vi.useRealTimers();
  });
});
