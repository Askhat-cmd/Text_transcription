import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminConfigService } from '../services/adminConfig.service';
import { useThreads } from './useThreads';

function mountHook() {
  let latest: ReturnType<typeof useThreads> | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useThreads();
    return null;
  }

  act(() => {
    root.render(React.createElement(Harness));
  });

  return {
    get state() {
      if (!latest) throw new Error('Hook state is not initialized');
      return latest;
    },
    cleanup() {
      act(() => root.unmount());
      container.remove();
    },
  };
}

describe('useThreads', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('loads threads', async () => {
    vi.spyOn(adminConfigService, 'getThreads').mockResolvedValue({
      threads: [{
        thread_id: 't1',
        user_id: 'u1',
        phase: 'clarify',
        response_mode: 'reflect',
        core_direction: 'self',
        turn_count: 1,
        created_at: '',
        last_updated_at: '',
        status: 'active',
      }],
      total: 1,
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.loadThreads();
    });

    expect(hook.state.threads).toHaveLength(1);
    hook.cleanup();
  });

  it('loads agent traces', async () => {
    vi.spyOn(adminConfigService, 'getAgentTraces').mockResolvedValue({
      traces: [{
        agent_id: 'writer',
        request_id: 'r1',
        user_id: 'u1',
        input_preview: 'in',
        output_preview: 'out',
        latency_ms: 12,
        timestamp: '',
      }],
      total: 1,
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.loadAgentTraces({ limit: 50 });
    });

    expect(hook.state.agentTraces).toHaveLength(1);
    expect(hook.state.agentTraces[0]?.agent_id).toBe('writer');
    hook.cleanup();
  });
});

