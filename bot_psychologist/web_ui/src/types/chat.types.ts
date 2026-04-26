/**
 * Chat Types for Bot Psychologist Web UI
 *
 * Types for chat state management and UI components.
 */

import type { Source, PathRecommendation, DebugTrace, LLMCallTrace } from './api.types';

export interface TraceBlock {
  block_id: string;
  score: number;
  text: string;
  source: string;
  stage: string;
  passed: boolean;
  filter_reason?: string;
}

export type LLMCallInfo = LLMCallTrace;

export type InlineTrace = Partial<DebugTrace> & {
  blocks?: TraceBlock[];
  signals?: Record<string, number>;
  prompt_overlay?: string;
};

export interface StateAnalyzerTrace {
  latency_ms: number;
  nervous_state: 'calm' | 'anxious' | 'crisis' | 'neutral' | string;
  intent: string;
  safety_flag: boolean;
  confidence: number;
}

export interface ThreadManagerTrace {
  latency_ms: number;
  thread_id: string;
  phase: 'exploring' | 'deepening' | 'closing' | string;
  relation_to_thread: 'continue' | 'new_thread' | string;
  continuity_score: number;
}

export interface MemoryRetrievalTrace {
  latency_ms: number;
  context_turns: number;
  semantic_hits_count: number;
  has_relevant_knowledge: boolean;
}

export interface WriterTrace {
  latency_ms: number;
  response_mode: string;
  tokens_used?: number | null;
  model_used?: string | null;
}

export interface ValidatorTrace {
  latency_ms: number;
  is_blocked: boolean;
  block_reason?: string | null;
  quality_flags: string[];
}

export interface MultiAgentPipelineTrace {
  state_analyzer: StateAnalyzerTrace;
  thread_manager: ThreadManagerTrace;
  memory_retrieval: MemoryRetrievalTrace;
  writer: WriterTrace;
  validator: ValidatorTrace;
}

export interface MultiAgentTraceData {
  session_id: string;
  turn_index?: number | null;
  pipeline_version: string;
  total_latency_ms: number;
  agents: MultiAgentPipelineTrace;
}

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
  trace?: InlineTrace | null;
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
  includeFeedbackPrompt: boolean;
  autoScroll: boolean;
  compactMode: boolean;
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
