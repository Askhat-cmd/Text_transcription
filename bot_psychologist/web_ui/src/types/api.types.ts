/**
 * API Types for Bot Psychologist Web UI
 *
 * Types matching the FastAPI backend models from Phase 5.
 */

// ===== ENUMS =====

export type FeedbackType = 'positive' | 'negative' | 'neutral';

// ===== REQUEST TYPES =====

export interface AskQuestionRequest {
  query: string;
  user_id?: string;
  session_id?: string;
  include_path?: boolean;
  include_feedback_prompt?: boolean;
  debug?: boolean;
}

export interface FeedbackRequest {
  user_id: string;
  turn_index: number;
  feedback: FeedbackType;
  rating?: number;  // 1-5
  comment?: string;
}

export interface GetUserHistoryRequest {
  user_id: string;
  last_n_turns?: number;
}

export interface GetStatsRequest {
  user_id?: string;
  time_range_days?: number;
}

export interface CreateSessionRequest {
  title?: string;
}

// ===== RESPONSE TYPES =====

export interface Source {
  block_id: string;
  title: string;
  youtube_link: string;
  start: number | string;  // Can be seconds (int) or timecode string
  end: number | string;    // Can be seconds (int) or timecode string
  block_type: string;
  complexity_score: number;
}

export interface StateAnalysis {
  primary_state: string;
  confidence: number;
  emotional_tone: string;
  recommendations: string[];
}

export interface PathStep {
  step_number: number;
  title: string;
  duration_weeks: number;
  practices: string[];
  key_concepts: string[];
}

export interface PathRecommendation {
  current_state: string;
  target_state: string;
  key_focus: string;
  steps_count: number;
  total_duration_weeks: number;
  first_step?: PathStep;
}

export interface AnswerResponse {
  status: string;
  answer: string;
  concepts: string[];
  sources: Source[];
  metadata: Record<string, unknown>;
  timestamp: string;
  processing_time_seconds: number;
}

export interface AdaptiveAnswerResponse {
  status: string;
  answer: string;
  state_analysis: StateAnalysis;
  path_recommendation?: PathRecommendation;
  feedback_prompt: string;
  concepts: string[];
  sources: Source[];
  conversation_context: string;
  metadata: Record<string, unknown>;
  timestamp: string;
  processing_time_seconds: number;
}

export interface ConversationTurn {
  timestamp: string;
  user_input: string;
  user_state?: string;
  bot_response: string;
  blocks_used: number;
  concepts: string[];
  user_feedback?: string;
  user_rating?: number;
}

export interface UserHistoryResponse {
  user_id: string;
  total_turns: number;
  turns: ConversationTurn[];
  primary_interests: string[];
  average_rating: number;
  last_interaction?: string;
}

export interface ChatSessionInfo {
  session_id: string;
  user_id: string;
  created_at: string;
  last_active: string;
  status: string;
  title: string;
  turns_count: number;
  last_user_input?: string;
  last_bot_response?: string;
  last_turn_timestamp?: string;
}

export interface UserSessionsResponse {
  user_id: string;
  total_sessions: number;
  sessions: ChatSessionInfo[];
}

export interface DeleteSessionResponse {
  status: string;
  message: string;
  user_id: string;
  session_id: string;
}

export interface FeedbackResponse {
  status: string;
  message: string;
  user_id: string;
  turn_index: number;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  modules: Record<string, boolean>;
}

export interface ErrorResponse {
  status: string;
  error: string;
  detail?: string;
  timestamp: string;
}

export interface StatsResponse {
  total_users: number;
  total_questions: number;
  average_processing_time: number;
  top_states: Record<string, number>;
  top_interests: string[];
  feedback_stats: Record<string, number>;
  timestamp: string;
}
