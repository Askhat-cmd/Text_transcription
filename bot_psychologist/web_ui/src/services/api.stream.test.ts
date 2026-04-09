import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiService } from './api.service';

type StreamLine = string;

function buildResponseFromLines(lines: StreamLine[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const line of lines) {
        controller.enqueue(encoder.encode(`${line}\n`));
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
  });

  it('accumulates all chunks into full text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromLines([
          'data: {"text":"Первый абзац."}',
          'data: {"text":" Второй абзац."}',
          'data: {"text":" Третий абзац."}',
          'data: [DONE]',
        ])
      )
    );

    let finalText = '';
    await apiService.streamAdaptiveAnswer(
      'тест',
      'u1',
      (acc) => {
        finalText = acc;
      },
      (meta) => {
        finalText = meta.answer ?? finalText;
      }
    );

    expect(finalText).toBe('Первый абзац. Второй абзац. Третий абзац.');
  });

  it('onToken receives accumulated text (not delta)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromLines([
          'data: {"token":"A"}',
          'data: {"token":"B"}',
          'data: {"token":"C"}',
          'data: [DONE]',
        ])
      )
    );

    const chunks: string[] = [];
    await apiService.streamAdaptiveAnswer(
      'тест',
      'u1',
      (acc) => chunks.push(acc),
      () => undefined
    );

    expect(chunks).toEqual(['A', 'AB', 'ABC']);
  });

  it('preserves cyrillic across byte chunk boundaries', async () => {
    const encoder = new TextEncoder();
    const payloadBytes = encoder.encode('data: {"text":"осознание"}\n');
    const split = Math.floor(payloadBytes.length / 2);
    const chunk1 = payloadBytes.slice(0, split);
    const chunk2 = payloadBytes.slice(split);
    const doneBytes = encoder.encode('data: [DONE]\n');

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(buildResponseFromChunks([chunk1, chunk2, doneBytes]))
    );

    let result = '';
    await apiService.streamAdaptiveAnswer(
      'тест',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      }
    );

    expect(result).toBe('осознание');
  });

  it('ignores keep-alive comments and handles plain-text chunks', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        buildResponseFromLines([
          ': keep-alive',
          'data: Привет',
          ': ping',
          'data:  мир',
          'data: done',
        ])
      )
    );

    let result = '';
    await apiService.streamAdaptiveAnswer(
      'тест',
      'u1',
      () => undefined,
      (meta) => {
        result = meta.answer ?? '';
      }
    );

    expect(result).toBe('Привет мир');
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
                buildResponseFromLines(['data: {"text":"ответ"}', 'data: [DONE]'])
              );
            }, 24000);
          })
      )
    );

    let errorMessage = '';
    let result = '';
    const promise = apiService.streamAdaptiveAnswer(
      'тест',
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
    expect(result).toBe('ответ');
  });

  it('handles AbortError with user-friendly message', async () => {
    const err = new Error('aborted');
    err.name = 'AbortError';
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(err));

    let errorMessage = '';
    await apiService.streamAdaptiveAnswer(
      'тест',
      'u1',
      () => undefined,
      () => undefined,
      (message) => {
        errorMessage = message;
      }
    );

    expect(errorMessage.toLowerCase()).toContain('время ожидания');
  });
});

