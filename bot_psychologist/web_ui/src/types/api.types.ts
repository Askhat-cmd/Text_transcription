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
  rating?: number; // 1-5
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
  start: number | string; // Can be seconds (int) or timecode string
  end: number | string; // Can be seconds (int) or timecode string
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

export interface ChunkTraceItem {
  block_id: string;
  title: string;
  emotional_tone: string;
  score_initial: number;
  score_final: number;
  passed_filter: boolean;
  filter_reason: string;
  preview: string;
  text?: string | null;
}

export interface MemoryTurnPreview {
  turn_index: number;
  role: string;
  text_preview: string;
  state?: string | null;
}

export interface SemanticHitDetail {
  block_id: string;
  score: number;
  text_preview: string;
  source?: string | null;
}

export interface PipelineStage {
  name: string;
  label: string;
  duration_ms: number;
  skipped?: boolean;
}

export interface AnomalyFlag {
  code: string;
  severity: 'info' | 'warn' | 'error';
  message: string;
  target?: string | null;
}

export interface StateTrajectoryPoint {
  turn: number;
  state: string;
  confidence?: number | null;
}

export interface ConfigSnapshot {
  conversation_history_depth: number;
  max_context_size: number;
  semantic_search_top_k: number;
  fast_path_enabled: boolean;
  rerank_enabled: boolean;
  model_name: string;
}

export interface PipelineError {
  stage: string;
  exception_type: string;
  message: string;
  partial_trace_available: boolean;
}

export interface LLMCallTrace {
  step: string;
  model: string;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  tokens_total?: number | null;
  duration_ms?: number | null;
  system_prompt_preview?: string | null;
  user_prompt_preview?: string | null;
  response_preview?: string | null;
  tokens_used?: number | null;
  system_prompt_blob_id?: string | null;
  user_prompt_blob_id?: string | null;
}

export interface TurnDiffMemoryDelta {
  turns_added: number;
  summary_changed: boolean;
  semantic_hits_delta: number;
}

export interface TurnDiff {
  route_changed: boolean;
  state_changed: boolean;
  config_changed_keys: string[];
  memory_delta: TurnDiffMemoryDelta;
}

export interface DebugTrace {
  trace_contract_version?: string | null;
  chunks_retrieved: ChunkTraceItem[];
  chunks_after_filter?: ChunkTraceItem[];
  llm_calls: LLMCallTrace[];
  context_written_to_memory: string;
  context_written?: string | null;
  total_duration_ms: number;
  primary_model?: string | null;
  classifier_model?: string | null;
  embedding_model?: string | null;
  reranker_model?: string | null;
  reranker_enabled?: boolean;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  tokens_total?: number | null;
  session_tokens_prompt?: number | null;
  session_tokens_completion?: number | null;
  session_tokens_total?: number | null;
  session_cost_usd?: number | null;
  session_turns?: number | null;
  fast_path?: boolean | null;
  fast_path_reason?: string | null;
  decision_rule_id?: string | null;
  mode_reason?: string | null;
  block_cap?: number | null;
  blocks_initial?: number | null;
  blocks_after_cap?: number | null;
  hybrid_query_preview?: string | null;
  hybrid_query_text?: string | null;
  hybrid_query_len?: number | null;
  context_mode?: string | null;
  memory_turns?: number | null;
  memory_turns_content?: MemoryTurnPreview[];
  summary_text?: string | null;
  summary_length?: number | null;
  summary_last_turn?: number | null;
  summary_pending_turn?: number | null;
  summary_used?: boolean | null;
  semantic_hits?: number | null;
  semantic_hits_detail?: SemanticHitDetail[];
  state_secondary?: string[];
  state_trajectory?: StateTrajectoryPoint[];
  pipeline_stages?: PipelineStage[];
  anomalies?: AnomalyFlag[];
  system_prompt_blob_id?: string | null;
  user_prompt_blob_id?: string | null;
  memory_snapshot_blob_id?: string | null;
  config_snapshot?: ConfigSnapshot | null;
  estimated_cost_usd?: number | null;
  pipeline_error?: PipelineError | null;
  session_id?: string | null;
  turn_number?: number | null;
  user_state?: string | null;
  recommended_mode?: string | null;
  confidence_score?: number | null;
  confidence_level?: string | null;
  turn_diff?: TurnDiff | null;
}

export interface LLMPayloadCall {
  step?: string | null;
  model?: string | null;
  duration_ms?: number | null;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  tokens_total?: number | null;
  system_prompt?: string | null;
  user_prompt?: string | null;
  response_preview?: string | null;
}

export interface LLMPayloadTrace {
  session_id: string;
  turn_number?: number | null;
  recommended_mode?: string | null;
  user_state?: string | null;
  agent_id?: string | null;
  hybrid_query_preview?: string | null;
  chunks_count?: number;
  llm_calls: LLMPayloadCall[];
  memory_snapshot?: string | null;
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
  trace?: DebugTrace | null;
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


