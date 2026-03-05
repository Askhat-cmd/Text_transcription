/**
 * useChat Hook - Chat state management
 *
 * Manages chat messages, loading state, and API interactions.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
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
  isThinking: boolean;
  streamingText: string;
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
  const [isThinking, setIsThinking] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [currentUserState, setCurrentUserState] = useState<string | undefined>();
  const [currentStateConfidence, setCurrentStateConfidence] = useState<number | undefined>();
  const messagesRef = useRef<Message[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

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

    const turnIndex = Math.floor(messagesRef.current.length / 2);
    const userMessageId = sessionId ? `${sessionId}-u-${turnIndex}` : uuidv4();
    const botMessageId = sessionId ? `${sessionId}-b-${turnIndex}` : uuidv4();

    addMessage('user', query, { id: userMessageId });
    setIsLoading(true);
    setIsThinking(true);
    setStreamingText('');
    setCurrentUserState(undefined);
    setCurrentStateConfidence(undefined);
    setError(null);

    try {
      let streamed = '';
      let doneMeta: any = null;
      let gotToken = false;

      await apiService.streamAdaptiveAnswer(
        query,
        userId,
        (token) => {
          gotToken = true;
          setIsThinking(false);
          streamed += token;
          setStreamingText(streamed);
        },
        (meta) => {
          doneMeta = meta;
        },
        (streamError) => {
          throw new Error(streamError);
        },
        {
          includePath,
          includeFeedback,
          sessionId,
        }
      );

      const finalText = streamed.trim() ? streamed : '...';
      addMessage('bot', finalText, {
        id: botMessageId,
        processingTime: doneMeta?.latency_ms ? doneMeta.latency_ms / 1000 : undefined,
        trace: doneMeta?.trace ?? undefined,
      });
      setStreamingText('');
      setIsThinking(false);
      setIsLoading(false);

      if (!gotToken && doneMeta?.mode) {
        // no-op placeholder for future metadata updates
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Не удалось получить ответ';
      setError(errorMessage);
      addMessage('bot', `Ошибка: ${errorMessage}`);
      setIsThinking(false);
      setIsLoading(false);
      setStreamingText('');
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
    isThinking,
    streamingText,
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

