/**
 * API Service for Bot Psychologist Web UI
 *
 * Handles all HTTP requests to the FastAPI backend.
 */

import axios, { type AxiosInstance, type AxiosError } from 'axios';
import type {
  AdaptiveAnswerResponse,
  AnswerResponse,
  UserHistoryResponse,
  FeedbackRequest,
  FeedbackResponse,
  StatsResponse,
  HealthCheckResponse,
  UserSessionsResponse,
  ChatSessionInfo,
  CreateSessionRequest,
  DeleteSessionResponse,
} from '../types/api.types';
import type { InlineTrace } from '../types';

class APIService {
  private api: AxiosInstance;
  private apiKey: string = '';

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1',
      timeout: 120000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.api.interceptors.request.use((config) => {
      if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey;
      }
      return config;
    });

    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 403) {
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );

    const savedKey = localStorage.getItem('bot_api_key');
    if (savedKey) {
      this.apiKey = savedKey;
    }
  }

  setAPIKey(key: string): void {
    this.apiKey = key;
    localStorage.setItem('bot_api_key', key);
  }

  getAPIKey(): string {
    return this.apiKey;
  }

  hasAPIKey(): boolean {
    return Boolean(this.apiKey);
  }

  clearAPIKey(): void {
    this.apiKey = '';
    localStorage.removeItem('bot_api_key');
  }

  private handleAuthError(): void {
    localStorage.removeItem('bot_api_key');
    console.warn('API key is invalid or expired');
  }

  // === QUESTION ENDPOINTS ===

  async askAdaptiveQuestion(
    query: string,
    userId: string,
    userLevel: 'beginner' | 'intermediate' | 'advanced' = 'beginner',
    includePath: boolean = false,
    includeFeedback: boolean = true,
    sessionId?: string
  ): Promise<AdaptiveAnswerResponse> {
    try {
      const response = await this.api.post<AdaptiveAnswerResponse>(
        '/questions/adaptive',
        {
          query,
          user_id: userId,
          session_id: sessionId,
          user_level: userLevel,
          include_path: includePath,
          include_feedback_prompt: includeFeedback,
          debug: false,
        }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async streamAdaptiveAnswer(
    query: string,
    userId: string,
    onToken: (token: string) => void,
    onDone?: (meta: { mode?: string; sd_level?: string; latency_ms?: number; trace?: InlineTrace; answer?: string }) => void,
    onError?: (message: string) => void,
    options?: {
      includePath?: boolean;
      includeFeedback?: boolean;
      sessionId?: string;
      userLevel?: 'beginner' | 'intermediate' | 'advanced';
      maxRetries?: number;
    }
  ): Promise<void> {
    const baseUrl = this.api.defaults.baseURL || '';
    const endpoint = `${baseUrl.replace(/\/$/, '')}/questions/adaptive-stream`;
    const maxRetries = options?.maxRetries ?? 3;
    const timeoutFromEnv = Number(import.meta.env.VITE_STREAM_TIMEOUT_MS ?? 60000);
    const streamTimeoutMs = Number.isFinite(timeoutFromEnv) && timeoutFromEnv > 0
      ? timeoutFromEnv
      : 60000;

    let attempt = 0;

    const attemptStream = async (): Promise<void> => {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), streamTimeoutMs);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(this.apiKey ? { 'X-API-Key': this.apiKey } : {}),
          },
          body: JSON.stringify({
            query,
            user_id: userId,
            session_id: options?.sessionId,
            user_level: options?.userLevel ?? 'beginner',
            include_path: options?.includePath ?? false,
            include_feedback_prompt: options?.includeFeedback ?? true,
            debug: false,
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          if (response.status === 403) {
            this.handleAuthError();
          }
          const message = `Streaming error: ${response.status} ${response.statusText}`;
          onError?.(message);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let fullText = '';
        let doneReceived = false;
        let tracePayload: InlineTrace | undefined;
        let doneMetaPayload: { mode?: string; sd_level?: string; latency_ms?: number; answer?: string } | null = null;

        const finalizeDone = (): void => {
          if (!doneReceived) {
            return;
          }
          const finalAnswer = doneMetaPayload?.answer?.trim()
            ? doneMetaPayload.answer
            : fullText;
          if (!doneMetaPayload?.answer?.trim() && import.meta.env.DEV) {
            console.warn('[SSE] finalizeDone fallback to accumulated fullText', {
              accumulated_length: fullText.length,
            });
          }
          onDone?.({
            mode: doneMetaPayload?.mode,
            sd_level: doneMetaPayload?.sd_level,
            latency_ms: doneMetaPayload?.latency_ms,
            trace: tracePayload,
            answer: finalAnswer,
          });
        };

        const processEventPayload = (eventType: string, data: string): void => {
          if (!data.trim()) {
            return;
          }

          if (eventType === 'trace') {
            try {
              tracePayload = JSON.parse(data) as InlineTrace;
            } catch {
              if (import.meta.env.DEV) {
                console.warn('[SSE] failed to parse trace payload', data);
              }
            }
            return;
          }

          const doneMarker = data.trim().toLowerCase();
          if (doneMarker === '[done]' || doneMarker === 'done') {
            doneReceived = true;
            if (!doneMetaPayload) {
              doneMetaPayload = { answer: fullText };
            }
            return;
          }

          type StreamPayload = {
            token?: string;
            text?: string;
            content?: string;
            delta?: string;
            done?: boolean;
            error?: string;
            answer?: string;
            answer_fallback?: string;
            mode?: string;
            sd_level?: string;
            latency_ms?: number;
            trace?: InlineTrace;
          };
          let payload: StreamPayload | null = null;

          try {
            payload = JSON.parse(data) as StreamPayload;
          } catch {
            if (eventType === 'trace') {
              return;
            }
            fullText += data;
            onToken(fullText);
            return;
          }

          if (payload && payload.error) {
            throw new Error(payload.error);
          }

          if (!payload) {
            return;
          }

          const delta = payload.token ?? payload.text ?? payload.content ?? payload.delta ?? '';
          if (delta) {
            fullText += String(delta);
            onToken(fullText);
          }

          if (payload.done) {
            const fallback = payload.answer_fallback ?? payload.answer ?? '';
            if (!fullText.trim() && typeof fallback === 'string' && fallback.trim()) {
              fullText = fallback;
              onToken(fullText);
            }
            doneMetaPayload = {
              mode: payload.mode,
              sd_level: payload.sd_level,
              latency_ms: payload.latency_ms,
              answer: fullText,
            };
            if (payload.trace) {
              tracePayload = payload.trace;
            }
            doneReceived = true;
          }
        };
        let currentEventType = 'message';
        let currentDataLines: string[] = [];

        const flushEvent = (): void => {
          if (currentDataLines.length === 0) {
            currentEventType = 'message';
            return;
          }
          const payload = currentDataLines.join('\n');
          processEventPayload(currentEventType, payload);
          currentEventType = 'message';
          currentDataLines = [];
        };

        const processRawLine = (rawLine: string): void => {
          const line = rawLine.replace(/\r$/, '');
          if (line.length === 0) {
            if (currentDataLines.length > 0) {
              flushEvent();
            }
            return;
          }
          if (line.startsWith(':')) {
            return;
          }
          if (line.startsWith('event:')) {
            const type = line.slice(6).trim();
            currentEventType = type || 'message';
            return;
          }
          if (line.startsWith('data:')) {
            let data = line.slice(5);
            if (data.startsWith(' ')) {
              data = data.slice(1);
            }
            currentDataLines.push(data);
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (value) {
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
              processRawLine(line);
            }
          }
          if (done) break;
        }

        if (buffer.length > 0) {
          processRawLine(buffer);
        }
        if (currentDataLines.length > 0) {
          if (import.meta.env.DEV) {
            console.warn('[SSE] EOF flush: stream ended without trailing blank line');
          }
          flushEvent();
        }

        if (doneReceived) {
          finalizeDone();
        } else if (fullText.length > 0) {
          if (import.meta.env.DEV) {
            console.warn('[SSE] completed without done marker, fallback to accumulated fullText', {
              accumulated_length: fullText.length,
            });
          }
          onDone?.({ trace: tracePayload, answer: fullText });
        } else {
          if (import.meta.env.DEV) {
            console.warn('[SSE] empty final answer: no done marker and no accumulated text');
          }
          onError?.('Empty stream: no response received');
        }
      } catch (err) {
        window.clearTimeout(timeoutId);
        if (err instanceof Error && err.name === 'AbortError') {
          onError?.('Превышено время ожидания ответа. Попробуйте ещё раз.');
          return;
        }
        if (attempt < maxRetries) {
          attempt += 1;
          console.warn(`[SSE] Read error, retrying (attempt ${attempt})`);
          return attemptStream();
        }
        const message = err instanceof Error ? err.message : 'Stream read error';
        onError?.(message);
      } finally {
        window.clearTimeout(timeoutId);
      }
    };

    await attemptStream();
  }

  async askBasicQuestion(query: string): Promise<AnswerResponse> {
    try {
      const response = await this.api.post<AnswerResponse>(
        '/questions/basic',
        { query }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async askSagAwareQuestion(query: string): Promise<AnswerResponse> {
    try {
      const response = await this.api.post<AnswerResponse>(
        '/questions/sag-aware',
        { query }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async askGraphQuestion(query: string): Promise<AnswerResponse> {
    try {
      const response = await this.api.post<AnswerResponse>(
        '/questions/graph-powered',
        { query }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === CHAT SESSIONS ===

  async getUserSessions(userId: string, limit: number = 100): Promise<UserSessionsResponse> {
    try {
      const response = await this.api.get<UserSessionsResponse>(
        `/users/${encodeURIComponent(userId)}/sessions`,
        {
          params: { limit },
        }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async createUserSession(userId: string, title?: string): Promise<ChatSessionInfo> {
    try {
      const payload: CreateSessionRequest = {};
      if (title && title.trim()) {
        payload.title = title.trim();
      }
      const response = await this.api.post<ChatSessionInfo>(
        `/users/${encodeURIComponent(userId)}/sessions`,
        payload
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async deleteUserSession(userId: string, sessionId: string): Promise<DeleteSessionResponse> {
    try {
      const response = await this.api.delete<DeleteSessionResponse>(
        `/users/${encodeURIComponent(userId)}/sessions/${encodeURIComponent(sessionId)}`
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === USER ENDPOINTS ===

  async getUserHistory(userId: string, lastNTurns: number = 10): Promise<UserHistoryResponse> {
    try {
      const response = await this.api.get<UserHistoryResponse>(
        `/users/${encodeURIComponent(userId)}/history`,
        {
          params: { last_n_turns: lastNTurns },
        }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === FEEDBACK ENDPOINTS ===

  async submitFeedback(feedback: FeedbackRequest): Promise<FeedbackResponse> {
    try {
      const response = await this.api.post<FeedbackResponse>(
        '/feedback',
        feedback
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === STATS ENDPOINTS ===

  async getStatistics(): Promise<StatsResponse> {
    try {
      const response = await this.api.get<StatsResponse>('/stats');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === HEALTH CHECK ===

  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const response = await this.api.get<HealthCheckResponse>('/health');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // === ERROR HANDLING ===

  private handleError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<{ detail?: string; error?: string }>;
      const message =
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.error ||
        axiosError.message ||
        'Произошла неизвестная ошибка';
      return new Error(message);
    }
    return error instanceof Error ? error : new Error('Неизвестная ошибка');
  }
}

export const apiService = new APIService();
