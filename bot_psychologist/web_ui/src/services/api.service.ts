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

class APIService {
  private api: AxiosInstance;
  private apiKey: string = '';

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1',
      timeout: 60000,
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
    includePath: boolean = true,
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
        'Unknown error occurred';
      return new Error(message);
    }
    return error instanceof Error ? error : new Error('Unknown error');
  }
}

export const apiService = new APIService();
