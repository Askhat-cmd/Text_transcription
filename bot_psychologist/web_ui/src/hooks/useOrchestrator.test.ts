import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminConfigService } from '../services/adminConfig.service';
import { useOrchestrator } from './useOrchestrator';

function mountHook() {
  let latest: ReturnType<typeof useOrchestrator> | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useOrchestrator();
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

describe('useOrchestrator', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('loads orchestrator config', async () => {
    vi.spyOn(adminConfigService, 'getOrchestratorConfig').mockResolvedValue({
      pipeline_mode: 'multiagent_only',
      pipeline_version: 'multiagent_v1',
      active_runtime: 'multiagent',
      agents_enabled: {
        state_analyzer: true,
        thread_manager: true,
        memory_retrieval: true,
        writer: true,
        validator: true,
      },
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.loadOrchestratorConfig();
    });

    expect(hook.state.orchestratorConfig?.pipeline_mode).toBe('multiagent_only');
    hook.cleanup();
  });

  it('updates pipeline mode using full_multiagent alias', async () => {
    vi.spyOn(adminConfigService, 'patchOrchestratorConfig').mockResolvedValue({
      status: 'ok',
      pipeline_mode: 'multiagent_only',
      pipeline_mode_alias_received: 'full_multiagent',
    });
    vi.spyOn(adminConfigService, 'getOrchestratorConfig').mockResolvedValue({
      pipeline_mode: 'multiagent_only',
      pipeline_version: 'multiagent_v1',
      active_runtime: 'multiagent',
      agents_enabled: {
        state_analyzer: true,
        thread_manager: true,
        memory_retrieval: true,
        writer: true,
        validator: true,
      },
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.setPipelineMode('full_multiagent');
    });

    expect(hook.state.orchestratorConfig?.pipeline_mode).toBe('multiagent_only');
    expect(hook.state.successMessage).toContain('pipeline_mode');
    hook.cleanup();
  });
});
