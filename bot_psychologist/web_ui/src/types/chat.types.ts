/**
 * Chat Types for Bot Psychologist Web UI
 *
 * Types for chat state management and UI components.
 */

import type { Source, PathRecommendation } from './api.types';

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  state?: string;
  confidence?: number;
  sources?: Source[];
  concepts?: string[];
  processingTime?: number;
  path?: PathRecommendation;
  feedbackPrompt?: string;
  userFeedback?: 'positive' | 'negative' | 'neutral';
  userRating?: number;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error?: string;
  currentUserState?: string;
}

export interface UserSettings {
  apiKey: string;
  userId: string;
  theme: 'light' | 'dark' | 'system';
  showSources: boolean;
  showPath: boolean;
  autoScroll: boolean;
  soundEnabled: boolean;
}

export interface ChatStore extends ChatState {
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | undefined) => void;
  setUserState: (state: string) => void;
  clearMessages: () => void;
  clearError: () => void;
}

export interface SettingsStore extends UserSettings {
  setApiKey: (key: string) => void;
  setUserId: (id: string) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSources: () => void;
  togglePath: () => void;
  toggleAutoScroll: () => void;
  toggleSound: () => void;
  resetSettings: () => void;
}

export type NewMessage = Omit<Message, 'id' | 'timestamp'>;
