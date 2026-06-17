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

// Legacy debug payload kept for API compatibility; active message trace UI is multiagent-only.
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

export interface SemanticHitTrace {
  chunk_id: string;
  source: string;
  score: number;
  content_preview: string;
  content_full: string;
}

export interface MemoryContextTrace {
  conversation_context: string;
  rag_query: string;
  hybrid_retrieval?: {
    planner_version?: string;
    planner_mode?: string;
    planner_model?: string;
    planner_max_tokens?: number | null;
    retrieval_action?: string;
    planned_composed_query?: string;
    executed_rag_query?: string;
    legacy_rag_query?: string;
    query_before_rag_proof?: boolean;
    needed_chunk_types?: string[];
    mechanism_hints?: string[];
    depth_level_hint?: number | null;
    safety_layer_required?: boolean | null;
    allowed_use_filter_hint?: string[];
    constraints_for_writer?: string[];
    retrieval_gap_reason?: string;
    writer_can_ignore_rag?: boolean | null;
    rag_skipped_reason?: string;
    llm_called?: boolean | null;
    llm_reason?: string;
    fallback_used?: boolean | null;
    universal_gate?: string;
  } | null;
  semantic_hits: SemanticHitTrace[];
  user_profile_patterns: string[];
  user_profile_values: string[];
  memory_written_preview: string;
}

export interface WriterLLMTrace {
  system_prompt: string;
  user_prompt: string;
  llm_response_raw: string;
  model: string;
  temperature: number;
  max_tokens: number;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  tokens_total?: number | null;
  estimated_cost_usd?: number | null;
}

export interface TurnDiffTrace {
  nervous_state_prev?: string | null;
  nervous_state_curr: string;
  phase_prev?: string | null;
  phase_curr: string;
  relation_to_thread: string;
  memory_turns_delta: number;
  semantic_hits_delta: number;
}

export interface AnomalyItem {
  code: string;
  severity: string;
  message: string;
}

export interface SessionDashboardTrace {
  total_turns: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  state_trajectory: string[];
  thread_switches: number;
  safety_events: number;
  validator_blocks: number;
}

export interface MultiAgentTraceData {
  session_id: string;
  turn_index?: number | null;
  pipeline_version: string;
  total_latency_ms: number;
  agents: MultiAgentPipelineTrace;
  memory_context?: MemoryContextTrace;
  writer_llm?: WriterLLMTrace;
  turn_diff?: TurnDiffTrace | null;
  anomalies?: AnomalyItem[];
  session_dashboard?: SessionDashboardTrace | null;
  hybrid_retrieval_plan?: Record<string, unknown> | null;
  hybrid_retrieval_planner_version?: string | null;
  hybrid_retrieval_planner_mode?: string | null;
  hybrid_retrieval_plan_valid?: boolean | null;
  hybrid_retrieval_plan_error?: string | null;
  hybrid_retrieval_universal_gate?: string | null;
  hybrid_retrieval_llm_called?: boolean | null;
  hybrid_retrieval_llm_reason?: string | null;
  hybrid_retrieval_fallback_used?: boolean | null;
  planned_composed_query?: string | null;
  executed_rag_query?: string | null;
  legacy_rag_query?: string | null;
  query_before_rag_proof?: boolean | null;
  retrieval_action?: string | null;
  rag_skipped_reason?: string | null;
  needed_chunk_types?: string[];
  mechanism_hints?: string[];
  retrieval_gap_reason?: string | null;
  writer_can_ignore_rag?: boolean | null;
  depth_level_hint?: number | null;
  safety_layer_required?: boolean | null;
  allowed_use_filter_hint?: string[];
  constraints_for_writer?: string[];
  planner_model?: string | null;
  planner_max_tokens?: number | null;
  overlay_shadow?: Record<string, unknown> | null;
  runtime_config_trace?: Record<string, unknown> | null;
  writer_kb_payload_trace?: Record<string, unknown> | null;
  future_graduation_notes?: Record<string, unknown> | null;
  live_turn_evidence?: Record<string, unknown> | null;
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
