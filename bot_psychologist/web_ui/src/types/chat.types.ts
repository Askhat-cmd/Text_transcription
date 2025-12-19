/**
 * Chat Types for Bot Psychologist Web UI
 * 
 * Types for chat state management and UI components.
 */

import type { Source, PathRecommendation, UserLevel } from './api.types';

export interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  // Bot message specific fields
  state?: string;
  confidence?: number;
  sources?: Source[];
  concepts?: string[];
  processingTime?: number;
  path?: PathRecommendation;
  feedbackPrompt?: string;
  // Feedback fields
  userFeedback?: 'positive' | 'negative' | 'neutral';
  userRating?: number;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error?: string;
  currentUserState?: string;
  userLevel: UserLevel;
}

export interface UserSettings {
  apiKey: string;
  userId: string;
  userLevel: UserLevel;
  theme: 'light' | 'dark' | 'system';
  showSources: boolean;
  showPath: boolean;
  autoScroll: boolean;
  soundEnabled: boolean;
}

export interface ChatStore extends ChatState {
  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | undefined) => void;
  setUserState: (state: string) => void;
  setUserLevel: (level: UserLevel) => void;
  clearMessages: () => void;
  clearError: () => void;
}

export interface SettingsStore extends UserSettings {
  // Actions
  setApiKey: (key: string) => void;
  setUserId: (id: string) => void;
  setUserLevel: (level: UserLevel) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSources: () => void;
  togglePath: () => void;
  toggleAutoScroll: () => void;
  toggleSound: () => void;
  resetSettings: () => void;
}

// Helper type for message creation
export type NewMessage = Omit<Message, 'id' | 'timestamp'>;
