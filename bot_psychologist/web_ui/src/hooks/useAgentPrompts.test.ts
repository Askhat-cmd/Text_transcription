import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminConfigService } from '../services/adminConfig.service';
import { useAgentPrompts } from './useAgentPrompts';

function mountHook() {
  let latest: ReturnType<typeof useAgentPrompts> | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useAgentPrompts();
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

describe('useAgentPrompts', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('loads prompts for selected agent', async () => {
    vi.spyOn(adminConfigService, 'getAgentPrompts').mockResolvedValue({
      agent_id: 'writer',
      prompts: [{
        key: 'SYSTEM_PROMPT',
        text: 'text',
        default_text: 'text',
        is_overridden: false,
        char_count: 4,
      }],
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.loadAgentPrompts('writer');
    });

    expect(hook.state.agentPrompts).toHaveLength(1);
    expect(hook.state.agentPrompts[0]?.key).toBe('SYSTEM_PROMPT');
    hook.cleanup();
  });

  it('saves prompt and reloads prompts', async () => {
    vi.spyOn(adminConfigService, 'updateAgentPrompt').mockResolvedValue({
      status: 'ok',
      agent_id: 'writer',
      prompt_key: 'SYSTEM_PROMPT',
      is_overridden: true,
      char_count: 12,
    });
    vi.spyOn(adminConfigService, 'getAgentPrompts').mockResolvedValue({
      agent_id: 'writer',
      prompts: [{
        key: 'SYSTEM_PROMPT',
        text: 'updated text',
        default_text: 'text',
        is_overridden: true,
        char_count: 12,
      }],
    });

    const hook = mountHook();
    await act(async () => {
      await hook.state.saveAgentPrompt('writer', 'SYSTEM_PROMPT', 'updated text');
    });

    expect(hook.state.agentPrompts[0]?.text).toBe('updated text');
    expect(hook.state.successMessage).toContain('сохранён');
    hook.cleanup();
  });
});
