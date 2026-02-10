/**
 * useChat Hook - Chat state management
 *
 * Manages chat messages, loading state, and API interactions.
 */

import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Message } from '../types';
import { apiService } from '../services/api.service';

export interface UseChatOptions {
  userId: string;
  includePath?: boolean;
  includeFeedback?: boolean;
  sessionId?: string;
}

export interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  currentUserState: string | undefined;
  currentStateConfidence: number | undefined;
  sendQuestion: (query: string) => Promise<void>;
  clearChat: () => void;
  replaceMessages: (messages: Message[]) => void;
  addMessage: (role: 'user' | 'bot', content: string, metadata?: Partial<Message>) => Message;
  updateMessageFeedback: (messageId: string, feedback: 'positive' | 'negative' | 'neutral', rating?: number) => void;
  clearError: () => void;
}

function normalizeMessage(message: Message): Message {
  return {
    ...message,
    timestamp: message.timestamp instanceof Date ? message.timestamp : new Date(message.timestamp),
  };
}

function getLastBotMessage(messages: Message[]): Message | undefined {
  return messages.slice().reverse().find((item) => item.role === 'bot');
}

export const useChat = (options: UseChatOptions): UseChatReturn => {
  const {
    userId,
    includePath = true,
    includeFeedback = true,
    sessionId,
  } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUserState, setCurrentUserState] = useState<string | undefined>();
  const [currentStateConfidence, setCurrentStateConfidence] = useState<number | undefined>();

  const addMessage = useCallback((
    role: 'user' | 'bot',
    content: string,
    metadata?: Partial<Message>
  ): Message => {
    const message: Message = {
      id: uuidv4(),
      role,
      content,
      timestamp: new Date(),
      ...metadata,
    };
    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  const replaceMessages = useCallback((nextMessages: Message[]) => {
    const normalized = nextMessages.map(normalizeMessage);
    setMessages(normalized);

    const lastBotMessage = getLastBotMessage(normalized);
    setCurrentUserState(lastBotMessage?.state);
    setCurrentStateConfidence(lastBotMessage?.confidence);

    setIsLoading(false);
    setError(null);
  }, []);

  const sendQuestion = useCallback(async (query: string) => {
    if (!query.trim()) return;

    addMessage('user', query);
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.askAdaptiveQuestion(
        query,
        userId,
        includePath,
        includeFeedback,
        sessionId
      );

      if (response.state_analysis) {
        setCurrentUserState(response.state_analysis.primary_state);
        setCurrentStateConfidence(response.state_analysis.confidence);
      }

      addMessage('bot', response.answer, {
        state: response.state_analysis?.primary_state,
        confidence: response.state_analysis?.confidence,
        sources: response.sources,
        concepts: response.concepts,
        processingTime: response.processing_time_seconds,
        path: response.path_recommendation,
        feedbackPrompt: response.feedback_prompt,
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Не удалось получить ответ';
      setError(errorMessage);
      addMessage('bot', `Ошибка: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [userId, includePath, includeFeedback, sessionId, addMessage]);

  const updateMessageFeedback = useCallback((
    messageId: string,
    feedback: 'positive' | 'negative' | 'neutral',
    rating?: number
  ) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? { ...msg, userFeedback: feedback, userRating: rating }
          : msg
      )
    );
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    setCurrentUserState(undefined);
    setCurrentStateConfidence(undefined);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    currentUserState,
    currentStateConfidence,
    sendQuestion,
    clearChat,
    replaceMessages,
    addMessage,
    updateMessageFeedback,
    clearError,
  };
};

