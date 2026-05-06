import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiService } from '../services/api.service';
import ChatPage from './ChatPage';

vi.mock('../components/chat', async () => {
  const ReactModule = await import('react');

  return {
    ChatWindow: (props: any) => ReactModule.createElement(
      'div',
      null,
      ReactModule.createElement(
        'button',
        {
          type: 'button',
          onClick: () => props.onSendMessage('persist message'),
        },
        'Send mocked message',
      ),
      ReactModule.createElement(
        'div',
        { 'data-testid': 'messages' },
        (props.messages || []).map((message: any) => message.content).join(' | '),
      ),
    ),
  };
});

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

async function waitFor(predicate: () => boolean, timeoutMs: number = 2000): Promise<void> {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeoutMs) {
      throw new Error('waitFor timeout');
    }
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

function clickButtonByText(container: HTMLElement, text: string): void {
  const buttons = Array.from(container.querySelectorAll('button'));
  const target = buttons.find((button) => button.textContent?.includes(text));
  if (!target) {
    throw new Error(`Button not found: ${text}`);
  }
  target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

describe('ChatPage session persistence', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    localStorage.setItem('bot_api_key', 'test-key-001');
    localStorage.setItem('bot_user_id', 'user_test');
    apiService.setAPIKey('test-key-001');
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('ignores stale history response when switching back to new chat', async () => {
    const oldHistoryDeferred = deferred<any>();
    const newSessionId = 'session-new';
    const oldSessionId = 'session-old';

    vi.spyOn(apiService, 'getUserSessions')
      .mockResolvedValueOnce({
        user_id: 'user_test',
        total_sessions: 2,
        sessions: [
          {
            session_id: newSessionId,
            user_id: 'user_test',
            created_at: '2026-05-06T08:00:00Z',
            last_active: '2026-05-06T09:00:00Z',
            status: 'active',
            title: 'Session New',
            turns_count: 0,
            last_user_input: null,
            last_bot_response: null,
            last_turn_timestamp: null,
          },
          {
            session_id: oldSessionId,
            user_id: 'user_test',
            created_at: '2026-05-05T08:00:00Z',
            last_active: '2026-05-05T09:00:00Z',
            status: 'active',
            title: 'Session Old',
            turns_count: 1,
            last_user_input: 'old user',
            last_bot_response: 'old bot',
            last_turn_timestamp: '2026-05-05T09:00:00Z',
          },
        ],
      } as any)
      .mockResolvedValueOnce({
        user_id: 'user_test',
        total_sessions: 2,
        sessions: [
          {
            session_id: newSessionId,
            user_id: 'user_test',
            created_at: '2026-05-06T08:00:00Z',
            last_active: '2026-05-06T09:01:00Z',
            status: 'active',
            title: 'persist message',
            turns_count: 1,
            last_user_input: 'persist message',
            last_bot_response: 'bot reply persist',
            last_turn_timestamp: '2026-05-06T09:01:00Z',
          },
          {
            session_id: oldSessionId,
            user_id: 'user_test',
            created_at: '2026-05-05T08:00:00Z',
            last_active: '2026-05-05T09:00:00Z',
            status: 'active',
            title: 'Session Old',
            turns_count: 1,
            last_user_input: 'old user',
            last_bot_response: 'old bot',
            last_turn_timestamp: '2026-05-05T09:00:00Z',
          },
        ],
      } as any);

    vi.spyOn(apiService, 'streamAdaptiveAnswer').mockImplementation(
      async (_query, _userId, onToken, onDone) => {
        onToken('bot reply persist');
        onDone?.({ answer: 'bot reply persist' });
      },
    );

    vi.spyOn(apiService, 'getUserHistory').mockImplementation(async (sessionId: string) => {
      if (sessionId === newSessionId) {
        return {
          user_id: 'user_test',
          total_turns: 1,
          turns: [
            {
              timestamp: '2026-05-06T09:01:00Z',
              user_input: 'persist message',
              user_state: 'calm',
              bot_response: 'bot reply persist',
              blocks_used: 0,
              concepts: [],
              user_feedback: null,
              user_rating: null,
            },
          ],
          primary_interests: [],
          average_rating: 0,
          last_interaction: '2026-05-06T09:01:00Z',
        } as any;
      }

      if (sessionId === oldSessionId) {
        return oldHistoryDeferred.promise;
      }

      return {
        user_id: 'user_test',
        total_turns: 0,
        turns: [],
        primary_interests: [],
        average_rating: 0,
        last_interaction: null,
      } as any;
    });

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root: Root = createRoot(container);

    await act(async () => {
      root.render(
        React.createElement(
          MemoryRouter,
          { initialEntries: ['/chat?user_id=user_test'] },
          React.createElement(
            Routes,
            null,
            React.createElement(Route, {
              path: '/chat',
              element: React.createElement(ChatPage),
            }),
          ),
        ),
      );
    });

    await waitFor(() => container.textContent?.includes('persist message') === true);

    await act(async () => {
      clickButtonByText(container, 'Send mocked message');
    });

    await waitFor(() => container.textContent?.includes('bot reply persist') === true);
    await waitFor(() => container.textContent?.includes('persist message') === true);

    await act(async () => {
      clickButtonByText(container, 'Session Old');
      clickButtonByText(container, 'persist message');
    });

    await act(async () => {
      oldHistoryDeferred.resolve({
        user_id: 'user_test',
        total_turns: 1,
        turns: [
          {
            timestamp: '2026-05-05T09:00:00Z',
            user_input: 'old user',
            user_state: 'old',
            bot_response: 'old bot',
            blocks_used: 0,
            concepts: [],
            user_feedback: null,
            user_rating: null,
          },
        ],
        primary_interests: [],
        average_rating: 0,
        last_interaction: '2026-05-05T09:00:00Z',
      } as any);
      await oldHistoryDeferred.promise;
    });

    await waitFor(() => container.textContent?.includes('persist message') === true);
    expect(container.textContent).toContain('persist message');
    expect(container.textContent).toContain('bot reply persist');
    expect(container.textContent).not.toContain('old user | old bot');

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });
});
