import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiService } from './api.service';

interface SSEEvent {
  event?: string;
  dataLines: string[];
}

function buildSSEStream(
  events: SSEEvent[],
  options?: { terminateWithBlankLine?: boolean }
): string {
  let raw = events
    .map((event) => {
      const lines: string[] = [];
      if (event.event && event.event !== 'message') {
        lines.push(`event: ${event.event}`);
      }
      for (const dataLine of event.dataLines) {
        lines.push(`data: ${dataLine}`);
      }
      return `${lines.join('\n')}\n\n`;
    })
    .join('');

  if (options?.terminateWithBlankLine === false && raw.endsWith('\n\n')) {
    raw = raw.slice(0, -2);
  }
  return raw;
}

function buildResponseFromSSE(raw: string): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      if (raw.length > 0) {
        controller.enqueue(encoder.encode(raw));
      }
      controller.close();
    },
  });
  return new Response(stream, { status: 200, statusText: 'OK' });
}

function buildResponseFromChunks(chunks: Uint8Array[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(chunk);
      }
      controller.close();
    },
  });
  return new Response(stream, { status: 200, statusText: 'OK' });
}

describe('APIService.streamAdaptiveAnswer', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('accumulates all chunks into full text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromSSE(
          buildSSEStream([
            { dataLines: ['{"text":"First paragraph."}'] },
            { dataLines: ['{"text":" Second paragraph."}'] },
            { dataLines: ['{"text":" Third paragraph."}'] },
            { dataLines: ['[DONE]'] },
          ])
        )
      )
    );

    let finalText = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      (acc) => {
        finalText = acc;
      },
      (meta) => {
        finalText = meta.answer ?? finalText;
      }
    );

    expect(finalText).toBe('First paragraph. Second paragraph. Third paragraph.');
  });

  it('onToken receives accumulated text (not delta)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromSSE(
          buildSSEStream([
            { dataLines: ['{"token":"A"}'] },
            { dataLines: ['{"token":"B"}'] },
            { dataLines: ['{"token":"C"}'] },
            { dataLines: ['[DONE]'] },
          ])
        )
      )
    );

    const chunks: string[] = [];
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      (acc) => chunks.push(acc),
      () => undefined
    );

    expect(chunks).toEqual(['A', 'AB', 'ABC']);
  });

  it('preserves cyrillic across byte chunk boundaries', async () => {
    const answer = 'осознание';
    const encoder = new TextEncoder();
    const raw = buildSSEStream([
      { dataLines: [`{"done":true,"answer":"${answer}"}`] },
    ]);
    const payloadBytes = encoder.encode(raw);
    const split = Math.floor(payloadBytes.length / 2);
    const chunk1 = payloadBytes.slice(0, split);
    const chunk2 = payloadBytes.slice(split);

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(buildResponseFromChunks([chunk1, chunk2]))
    );

    let result = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      }
    );

    expect(result).toBe(answer);
  });

  it('ignores keep-alive comments and handles plain-text chunks', async () => {
    const raw = [
      ': keep-alive',
      '',
      'data: Hello',
      '',
      ': ping',
      '',
      'data:  world',
      '',
      'data: done',
      '',
    ].join('\n');

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(buildResponseFromSSE(raw)));

    let result = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      }
    );

    expect(result).toBe('Hello world');
  });

  it('does not timeout on 24-second stream when timeout is 60s', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => {
              resolve(
                buildResponseFromSSE(
                  buildSSEStream([
                    { dataLines: ['{"text":"reply"}'] },
                    { dataLines: ['[DONE]'] },
                  ])
                )
              );
            }, 24000);
          })
      )
    );

    let errorMessage = '';
    let result = '';
    const promise = apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      },
      (message) => {
        errorMessage = message;
      }
    );

    await vi.advanceTimersByTimeAsync(24000);
    await promise;
    vi.useRealTimers();

    expect(errorMessage).toBe('');
    expect(result).toBe('reply');
  });

  it('handles AbortError with user-friendly message', async () => {
    const err = new Error('aborted');
    err.name = 'AbortError';
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(err));

    let errorMessage = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      () => undefined,
      (message) => {
        errorMessage = message;
      }
    );

    expect(errorMessage.toLowerCase()).toContain('время ожидания');
  });

  it('uses done.answer as final source of truth when tokens are partial', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromSSE(
          buildSSEStream([
            { dataLines: ['{"token":"partial"}'] },
            { dataLines: ['{"done":true,"answer":"final complete answer"}'] },
          ])
        )
      )
    );

    let result = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      }
    );

    expect(result).toBe('final complete answer');
  });

  it('parses trace from separate SSE event and attaches it to done meta', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromSSE(
          buildSSEStream([
            { dataLines: ['{"token":"answer"}'] },
            { dataLines: ['{"done":true,"answer":"answer","mode":"PRESENCE","latency_ms":123}'] },
            { event: 'trace', dataLines: ['{"recommended_mode":"PRESENCE","turn_number":7}'] },
          ])
        )
      )
    );

    let doneMeta: any = null;
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        doneMeta = meta;
      }
    );

    expect(doneMeta?.mode).toBe('PRESENCE');
    expect(doneMeta?.latency_ms).toBe(123);
    expect(doneMeta?.trace?.turn_number).toBe(7);
    expect(doneMeta?.answer).toBe('answer');
  });

  it('flushes final event at EOF when stream has no trailing blank line', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromSSE(
          buildSSEStream(
            [{ dataLines: ['{"done":true,"answer":"eof answer"}'] }],
            { terminateWithBlankLine: false }
          )
        )
      )
    );

    let result = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      }
    );

    expect(result).toBe('eof answer');
  });

  it('returns degraded completion when done marker is missing but tokens exist', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromSSE(
          buildSSEStream([
            { dataLines: ['{"token":"degraded"}'] },
            { dataLines: ['{"token":" answer"}'] },
          ])
        )
      )
    );

    let result = '';
    let errorMessage = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      },
      (message) => {
        errorMessage = message;
      }
    );

    expect(result).toBe('degraded answer');
    expect(errorMessage).toBe('');
    if (import.meta.env.DEV) {
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('completed without done marker'),
        expect.anything()
      );
    }
  });

  it('calls onError for empty stream without done marker', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(buildResponseFromSSE('')));

    let result = '';
    let errorMessage = '';
    await apiService.streamAdaptiveAnswer(
      'test',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      },
      (message) => {
        errorMessage = message;
      }
    );

    expect(result).toBe('');
    expect(errorMessage).toContain('Empty stream');
  });

  // @invalid-sse-fixture
  it('documents invalid single-\\n fixture vs valid RFC8895 framing', () => {
    const invalidFixture = 'data: {"token":"A"}\ndata: {"done":true}\n';
    const validFixture = 'data: {"token":"A"}\n\ndata: {"done":true}\n\n';

    expect(invalidFixture).not.toBe(validFixture);
  });
});
