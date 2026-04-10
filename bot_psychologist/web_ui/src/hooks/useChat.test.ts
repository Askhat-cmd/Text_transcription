import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiService } from '../services/api.service';
import { useChat, type UseChatOptions, type UseChatReturn } from './useChat';

function mountUseChat(options: UseChatOptions) {
  let latest: UseChatReturn | null = null;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Harness() {
    latest = useChat(options);
    return null;
  }

  act(() => {
    root.render(React.createElement(Harness));
  });

  const getState = (): UseChatReturn => {
    if (!latest) {
      throw new Error('Hook state is not initialized');
    }
    return latest;
  };

  return {
    get state(): UseChatReturn {
      return getState();
    },
    async sendQuestion(query: string): Promise<void> {
      const state = getState();
      await act(async () => {
        await state.sendQuestion(query);
      });
    },
    cleanup(): void {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

describe('useChat stream finalization', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('finalizes with meta.answer when present', async () => {
    vi.spyOn(apiService, 'streamAdaptiveAnswer').mockImplementation(
      async (_query, _userId, onToken, onDone) => {
        onToken('partial');
        onDone?.({ answer: 'Full final answer', latency_ms: 120 });
      }
    );

    const harness = mountUseChat({ userId: 'u1' });
    await harness.sendQuestion('test');

    const botMessages = harness.state.messages.filter((msg) => msg.role === 'bot');
    expect(botMessages).toHaveLength(1);
    expect(botMessages[0]?.content).toBe('Full final answer');

    harness.cleanup();
  });

  it('falls back to streamed text in degraded completion', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(apiService, 'streamAdaptiveAnswer').mockImplementation(
      async (_query, _userId, onToken, onDone) => {
        onToken('degraded fallback');
        onDone?.({});
      }
    );

    const harness = mountUseChat({ userId: 'u1' });
    await harness.sendQuestion('test');

    const botMessages = harness.state.messages.filter((msg) => msg.role === 'bot');
    expect(botMessages).toHaveLength(1);
    expect(botMessages[0]?.content).toBe('degraded fallback');
    if (import.meta.env.DEV) {
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('finalized without done.answer')
      );
    }

    harness.cleanup();
  });

  it('does not duplicate final bot message', async () => {
    vi.spyOn(apiService, 'streamAdaptiveAnswer').mockImplementation(
      async (_query, _userId, onToken, onDone) => {
        onToken('draft');
        onDone?.({ answer: 'single bot message' });
      }
    );

    const harness = mountUseChat({ userId: 'u1' });
    await harness.sendQuestion('test');

    const botMessages = harness.state.messages.filter((msg) => msg.role === 'bot');
    expect(botMessages).toHaveLength(1);
    expect(botMessages[0]?.content).toBe('single bot message');

    harness.cleanup();
  });

  it('clears streamingText after finalization', async () => {
    vi.spyOn(apiService, 'streamAdaptiveAnswer').mockImplementation(
      async (_query, _userId, onToken, onDone) => {
        onToken('temporary');
        onDone?.({ answer: 'final' });
      }
    );

    const harness = mountUseChat({ userId: 'u1' });
    await harness.sendQuestion('test');

    expect(harness.state.streamingText).toBe('');
    expect(harness.state.isLoading).toBe(false);
    expect(harness.state.isThinking).toBe(false);

    harness.cleanup();
  });
});
