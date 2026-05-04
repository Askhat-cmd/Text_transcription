// types/admin.types.ts

export type ParamType = 'int' | 'int_or_null' | 'float' | 'bool' | 'select' | 'string';

export interface ConfigParam {
  value: number | boolean | string | null;
  default: number | boolean | string | null;
  is_overridden: boolean;
  type: ParamType;
  min?: number;
  max?: number;
  options?: string[];
  group: string;
  label: string;
  note?: string;  // подсказка под полем
}

export interface ConfigGroup {
  label: string;
  params: Record<string, ConfigParam>;
}

export interface AdminConfigResponse {
  groups: Record<string, ConfigGroup>;
}

export interface PromptMeta {
  name: string;
  label: string;
  preview: string;
  is_overridden: boolean;
  char_count: number;
  editable?: boolean;
  is_legacy?: boolean;
  source?: string;
  stack_version?: string;
  variants?: string[];
  version?: string;
  updated_at?: string | null;
  legacy_prompt_name?: string | null;
  derived_from?: string | null;
  read_only_reason?: string | null;
  usage_markers?: {
    used_in_last_turn?: boolean;
  };
}

export interface PromptDetail extends PromptMeta {
  text: string;
  default_text: string;
}

export type HistoryEntryType =
  | 'config'
  | 'config_reset'
  | 'prompt'
  | 'prompt_reset';

export interface HistoryEntry {
  key: string;
  type: HistoryEntryType;
  old: unknown;
  new: unknown;
  timestamp: string;
}

export interface AdminOverridesExport {
  config: Record<string, unknown>;
  prompts: Record<string, string | null>;
  meta: { last_modified: string; modified_by: string };
  history: HistoryEntry[];
}

export interface AdminStatusResponse {
  degraded_mode: boolean;
  data_source: string;
  blocks_loaded: number;
  version: string;
  feature_flags?: Record<string, boolean>;
}

export interface DiagnosticsPolicies {
  informational_narrowing_enabled: boolean;
  mixed_query_handling_enabled: boolean;
  user_correction_protocol_enabled: boolean;
  first_turn_richness_policy_enabled: boolean;
  curiosity_decoupling_enabled: boolean;
}

export interface AdminDiagnosticsEffectiveResponse {
  schema_version: string;
  contract: string;
  policies: DiagnosticsPolicies;
  active_contract: Record<string, unknown>;
  last_snapshot: Record<string, unknown>;
  trace_available: boolean;
}

export interface AdminRuntimeEffectiveResponse {
  schema_version: string;
  admin_schema_version: string;
  prompt_stack_version: string;
  status: AdminStatusResponse;
  feature_flags: {
    all: Record<string, boolean>;
    groups: Record<string, Record<string, boolean>>;
  };
  diagnostics: Record<string, unknown>;
  routing: Record<string, unknown>;
  validation: {
    enabled: boolean;
    config_validation_status: {
      valid: boolean;
      errors: string[];
    };
  };
  trace: {
    available: boolean;
    developer_trace_supported?: boolean;
    developer_trace_enabled?: boolean;
    developer_trace_mode_available?: boolean;
  };
}

export type AgentId =
  | 'state_analyzer'
  | 'thread_manager'
  | 'memory_retrieval'
  | 'writer'
  | 'validator';

export interface AgentStatus {
  id: AgentId;
  enabled: boolean;
  call_count: number;
  avg_latency_ms: number;
  error_count: number;
  error_rate: number;
  last_run?: string | null;
}

export interface AgentsStatusResponse {
  pipeline_version: string;
  agents: AgentStatus[];
}

export interface OrchestratorConfig {
  pipeline_mode: 'full_multiagent' | 'hybrid' | 'legacy_adaptive';
  actual_pipeline_mode?: 'full_multiagent' | 'hybrid' | 'legacy_adaptive';
  env_flags?: Record<string, string>;
  agents_enabled: Record<AgentId, boolean>;
  pipeline_version: string;
}

export interface AgentTrace {
  agent_id: string;
  request_id: string;
  user_id: string;
  input_preview: string;
  output_preview: string;
  latency_ms: number;
  error?: string | null;
  timestamp: string;
}

export interface AgentTracesResponse {
  traces: AgentTrace[];
  total: number;
}

export interface ThreadItem {
  thread_id: string;
  user_id: string;
  phase?: string;
  response_mode?: string;
  core_direction?: string;
  turn_count?: number;
  created_at?: string;
  last_updated_at?: string;
  status: 'active' | 'archived';
  open_loops_count?: number;
  closed_loops_count?: number;
  final_phase?: string;
  archived_at?: string;
  archive_reason?: string;
}

export interface ThreadsResponse {
  threads: ThreadItem[];
  total: number;
}

export interface AgentPrompt {
  key: string;
  text: string;
  default_text: string;
  is_overridden: boolean;
  char_count: number;
}

export interface AgentPromptsResponse {
  agent_id: 'writer' | 'state_analyzer' | 'thread_manager';
  prompts: AgentPrompt[];
}

export interface AgentLLMEntry {
  model: string;
  default_model: string;
  is_overridden: boolean;
  temperature: number;
  default_temperature: number;
  is_temperature_overridden: boolean;
}

export interface AgentLLMConfigResponse {
  agents: { [agentId: string]: AgentLLMEntry };
  allowed_models: string[];
}

export type PipelineMode = 'full_multiagent' | 'hybrid' | 'legacy_adaptive';

export interface AgentOverviewStatus {
  agent_id: string;
  enabled: boolean;
  calls: number;
  errors: number;
  avg_ms: number;
  last_run: string | null;
}

export interface RecentTrace {
  agent_id: string;
  request_id: string;
  user_id: string;
  input_preview: string;
  output_preview: string;
  latency_ms: number;
  error?: string | null;
  timestamp: string;
}

export interface OverviewData {
  pipeline_mode: PipelineMode;
  feature_flags: Record<string, string>;
  agents: AgentOverviewStatus[];
  recent_traces: RecentTrace[];
  server_time: string;
  schema_version: string;
}
