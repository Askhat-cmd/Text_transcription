import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminConfigService } from '../services/adminConfig.service';
import { useAgents } from './useAgents';

function mountUseAgents() {
  let latest: ReturnType<typeof useAgents> | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useAgents();
    return null;
  }

  act(() => {
    root.render(React.createElement(Harness));
  });

  const getState = () => {
    if (!latest) throw new Error('Hook state is not initialized');
    return latest;
  };

  return {
    get state() {
      return getState();
    },
    cleanup() {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

describe('useAgents', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('loadAgentsStatus populates agents', async () => {
    vi.spyOn(adminConfigService, 'getAgentsStatus').mockResolvedValue({
      pipeline_version: 'multiagent_v1',
      agents: [
        {
          id: 'writer',
          enabled: true,
          call_count: 5,
          avg_latency_ms: 900,
          error_count: 0,
          error_rate: 0,
          last_run: null,
        },
      ],
    });

    const harness = mountUseAgents();
    await act(async () => {
      await harness.state.loadAgentsStatus();
    });

    expect(harness.state.agents[0]?.id).toBe('writer');
    harness.cleanup();
  });

  it('loadOrchestratorConfig sets config', async () => {
    vi.spyOn(adminConfigService, 'getOrchestratorConfig').mockResolvedValue({
      pipeline_mode: 'full_multiagent',
      agents_enabled: {
        state_analyzer: true,
        thread_manager: true,
        memory_retrieval: true,
        writer: true,
        validator: true,
      },
      pipeline_version: 'multiagent_v1',
    });

    const harness = mountUseAgents();
    await act(async () => {
      await harness.state.loadOrchestratorConfig();
    });

    expect(harness.state.orchestratorConfig?.pipeline_mode).toBe('full_multiagent');
    harness.cleanup();
  });

  it('sets error on network failure', async () => {
    vi.spyOn(adminConfigService, 'getAgentsStatus').mockRejectedValue(new Error('Network Error'));

    const harness = mountUseAgents();
    await act(async () => {
      await harness.state.loadAgentsStatus();
    });

    expect(harness.state.error).toBe('Network Error');
    harness.cleanup();
  });

  it('loadThreads populates threads', async () => {
    vi.spyOn(adminConfigService, 'getThreads').mockResolvedValue({
      threads: [
        {
          thread_id: 't1',
          user_id: 'u1',
          phase: 'middle',
          response_mode: 'empathic',
          core_direction: 'stress',
          turn_count: 3,
          created_at: '',
          last_updated_at: '',
          status: 'active',
        },
      ],
      total: 1,
    });

    const harness = mountUseAgents();
    await act(async () => {
      await harness.state.loadThreads('active');
    });

    expect(harness.state.threads).toHaveLength(1);
    harness.cleanup();
  });
});
