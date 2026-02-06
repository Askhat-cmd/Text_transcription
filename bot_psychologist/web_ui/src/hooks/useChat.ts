/**
 * useChat Hook - Chat state management
 * 
 * Manages chat messages, loading state, and API interactions.
 */

import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Message, UserLevel } from '../types';
import { apiService } from '../services/api.service';

export interface UseChatOptions {
  userId: string;
  userLevel?: UserLevel;
  includePath?: boolean;
  includeFeedback?: boolean;
}

export interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  currentUserState: string | undefined;
  sendQuestion: (query: string) => Promise<void>;
  clearChat: () => void;
  addMessage: (role: 'user' | 'bot', content: string, metadata?: Partial<Message>) => Message;
  updateMessageFeedback: (messageId: string, feedback: 'positive' | 'negative' | 'neutral', rating?: number) => void;
  clearError: () => void;
}

export const useChat = (options: UseChatOptions): UseChatReturn => {
  const { 
    userId, 
    userLevel = 'beginner', 
    includePath = true, 
    includeFeedback = true 
  } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUserState, setCurrentUserState] = useState<string | undefined>();

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

  const sendQuestion = useCallback(async (query: string) => {
    if (!query.trim()) return;

    // Add user message
    addMessage('user', query);
    setIsLoading(true);
    setError(null);

    try {
      // API request
      const response = await apiService.askAdaptiveQuestion(
        query,
        userId,
        userLevel,
        includePath,
        includeFeedback
      );

      // Update user state
      if (response.state_analysis) {
        setCurrentUserState(response.state_analysis.primary_state);
      }

      // Add bot response
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to get response';
      setError(errorMessage);
      addMessage('bot', `❌ Ошибка: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  }, [userId, userLevel, includePath, includeFeedback, addMessage]);

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
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    currentUserState,
    sendQuestion,
    clearChat,
    addMessage,
    updateMessageFeedback,
    clearError,
  };
};


