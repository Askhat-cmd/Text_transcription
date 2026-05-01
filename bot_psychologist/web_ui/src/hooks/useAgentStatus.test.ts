import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminConfigService } from '../services/adminConfig.service';
import { useAgentStatus } from './useAgentStatus';

function mountHook() {
  let latest: ReturnType<typeof useAgentStatus> | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useAgentStatus();
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

describe('useAgentStatus', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('loads agents status', async () => {
    vi.spyOn(adminConfigService, 'getAgentsStatus').mockResolvedValue({
      pipeline_version: 'multiagent_v1',
      agents: [{
        id: 'writer',
        enabled: true,
        call_count: 1,
        avg_latency_ms: 12,
        error_count: 0,
        error_rate: 0,
        last_run: null,
      }],
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.loadAgentsStatus();
    });

    expect(hook.state.agents).toHaveLength(1);
    expect(hook.state.agents[0]?.id).toBe('writer');
    hook.cleanup();
  });

  it('toggles agent and reloads status', async () => {
    vi.spyOn(adminConfigService, 'toggleAgent').mockResolvedValue({
      status: 'ok',
      agent_id: 'writer',
      enabled: false,
    });
    vi.spyOn(adminConfigService, 'getAgentsStatus').mockResolvedValue({
      pipeline_version: 'multiagent_v1',
      agents: [{
        id: 'writer',
        enabled: false,
        call_count: 1,
        avg_latency_ms: 12,
        error_count: 0,
        error_rate: 0,
        last_run: null,
      }],
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.toggleAgent('writer', false);
    });

    expect(hook.state.agents[0]?.enabled).toBe(false);
    expect(hook.state.successMessage).toContain('writer');
    hook.cleanup();
  });
});

