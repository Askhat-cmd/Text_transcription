import React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ChatWindow } from './ChatWindow';

vi.mock('./InputBox', () => ({
  default: () => null,
}));

vi.mock('./MessageList', () => ({
  default: () => null,
}));

vi.mock('./TypingIndicator', () => ({
  default: () => null,
}));

vi.mock('../debug/SessionTracePanel', () => ({
  SessionTracePanel: () => null,
}));

describe('ChatWindow markdown rendering', () => {
  let container: HTMLDivElement;
  let root: Root;

  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => undefined;
  }

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root.unmount();
      });
    }
    container?.remove();
  });

  it('renders streaming markdown as formatted DOM, not plain markdown text', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root.render(
        React.createElement(ChatWindow, {
          messages: [{ id: 'u1', role: 'user', content: 'test', timestamp: new Date() }],
          isLoading: false,
          streamingText: '**Заголовок**\n\n- пункт один\n- пункт два',
          onSendMessage: () => undefined,
        })
      );
    });

    expect(container.querySelector('strong')?.textContent).toBe('Заголовок');
    const items = Array.from(container.querySelectorAll('li')).map((node) => node.textContent?.trim());
    expect(items).toEqual(['пункт один', 'пункт два']);
    expect(container.textContent).not.toContain('**Заголовок**');
  });
});
