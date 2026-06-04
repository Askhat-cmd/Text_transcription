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
  active_runtime: 'multiagent';
  runtime_entrypoint: 'multiagent_adapter' | 'answer_adaptive_deprecated_shim';
  pipeline_version: string;
  pipeline_mode: 'multiagent_only';
  pipeline_mode_read_only: boolean;
  pipeline_mode_legacy_value?: string | null;
  legacy_modes_selectable: boolean;
  legacy: {
    fallback_enabled: boolean;
    fallback_used: boolean;
    cascade_available: boolean;
    cascade_status: 'deprecated_retained_for_purge';
    purge_planned_prd: 'PRD-041';
  };
  compatibility: {
    pipeline_mode: 'multiagent_only';
    pipeline_mode_legacy_value?: string | null;
    pipeline_mode_read_only: boolean;
    legacy_modes_selectable: boolean;
  };
  agents: Record<string, Record<string, unknown>>;
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
  philosophy_kernel?: {
    enabled: boolean;
    version: string;
    kernel_enabled?: boolean;
    kernel_version?: string;
    selected_lenses_visible?: boolean;
    identity?: {
      bot_identity?: string;
      role?: string;
    };
    quote_policy?: string;
    practice_policy?: string;
    principles_count?: number;
    boundaries_count?: number;
    lenses?: string[];
    prompt_budget?: {
      max_kernel_chars?: number;
      max_freedom_chars?: number;
      max_combined_chars?: number;
      max_selected_lenses?: number;
    };
    quality_calibration?: {
      last_prd?: string;
      last_direct_passed?: boolean;
      last_direct_cases_total?: number;
      last_direct_cases_failed?: number;
      artifact_found?: boolean;
    };
  };
  writer_freedom_contract?: {
    enabled: boolean;
    version: string;
    freedom_level?: string;
    mode_is_hint_not_cage?: boolean;
    question_limit?: number;
    practice_requires_gate?: boolean;
    writer_max_tokens?: number;
    writer_target_tokens_default?: number;
    writer_target_tokens_expanded?: number;
    writer_allow_long_answer?: boolean;
  };
  dialogue_profile?: {
    value?: string;
    allowed_values?: string[];
    scope?: string;
    description?: string;
    developer_local_only?: boolean;
    warning?: string;
  };
  dialogue_policy?: {
    profile?: string;
    writer_autonomy?: string;
    planner_authority?: string;
    diagnostic_card_authority?: string;
    writer_move_authority?: string;
    active_line_authority?: string;
    context_budget_chars?: number;
    allow_numbered_lists?: boolean;
    allow_examples?: boolean;
    allow_practice_catalog?: boolean;
    human_like_answer_policy?: {
      enabled?: boolean;
      answer_style?: string;
      default_depth?: string;
      allow_long_answers?: boolean;
      allow_lists?: boolean;
      allow_examples?: boolean;
      allow_direct_answer?: boolean;
      question_is_optional?: boolean;
      do_not_force_question_at_end?: boolean;
      do_not_force_practice_frame?: boolean;
      do_not_force_max_sentences?: boolean;
      respect_user_requested_format?: boolean;
      sarcasm_and_dissatisfaction_repair?: boolean;
      direct_answer_repair_when_user_complains?: boolean;
    };
    constraint_resolution?: {
      profile?: string;
      planner_authority?: string;
      overruled_constraints?: string[];
      overrule_reason?: string;
    };
    writer_runtime_max_tokens_effective?: number;
    final_answer_directive_enabled?: boolean;
    final_answer_directive_version?: string;
    diagnostic_center_role?: string;
    planner_role?: string;
    active_line_role?: string;
    diagnostic_card_role?: string;
    legacy_prompt_blocks_mode?: string;
    writer_first_prompt_assembly_enabled?: boolean;
    fresh_chat_context_policy_version?: string;
    writer_context_package_version?: string;
    fresh_chat_rag_default?: string;
    current_chat_reset_control?: {
      endpoint?: string;
      scope?: string;
      preserves_session_id?: boolean;
    };
    user_memory_profile_clear_control?: {
      endpoint?: string;
      scope?: string;
      developer_visible?: boolean;
    };
    web_chat_markdown_renderer?: string;
  };
  active_line?: {
    enabled?: boolean;
    version?: string;
    user_intent?: string;
    continuity_mode?: string;
    revoicing_policy?: string;
    practice_suppression_active?: boolean;
    last_quality_calibration?: {
      last_prd?: string;
      last_direct_passed?: boolean;
      last_direct_cases_total?: number;
      last_direct_cases_failed?: number;
      artifact_found?: boolean;
    };
  };
  response_planner?: {
    enabled?: boolean;
    version?: string;
    kind?: string;
    role?: string;
    advisory_mode?: boolean;
    live_acceptance_requires_api_trace?: boolean;
    last_quality_calibration?: {
      last_prd?: string;
      last_direct_passed?: boolean;
      last_direct_cases_total?: number;
      last_direct_cases_failed?: number;
      artifact_found?: boolean;
    };
  };
  planner_drift_guard?: {
    enabled?: boolean;
    version?: string;
    mode?: string;
    blocking_user_answers?: boolean;
    window_size?: number;
    thresholds?: {
      warning_violation_rate?: number;
      critical_rate?: number;
    };
    mvp_expansion_exceptions?: {
      answer_length_long_when_expansion_requested?: boolean;
      numbered_list_when_expansion_requested?: boolean;
      multi_block_answer_when_concept_explanation_full?: boolean;
    };
    last_summary?: {
      total?: number;
      ok_count?: number;
      warning_count?: number;
      critical_count?: number;
      violation_rate?: number;
      critical_rate?: number;
      threshold_status?: string;
    };
    last_replay_status?: {
      prd?: string;
      direct?: string;
      live?: string;
    };
  };
  guided_live_testing?: {
    enabled?: boolean;
    schema_version?: string;
    mode?: string;
    feedback_storage?: string;
    raw_dialogue_saved_by_default?: boolean;
    scenario_set?: string;
    scenario_count?: number;
    last_session_summary_available?: boolean;
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
  active_runtime: 'multiagent';
  runtime_entrypoint?: 'multiagent_adapter' | 'answer_adaptive_deprecated_shim';
  pipeline_mode?: 'multiagent_only';
  pipeline_mode_read_only?: boolean;
  legacy?: Record<string, unknown>;
  agent_contract?: Record<string, Record<string, unknown>>;
  agents: AgentStatus[];
}

export interface OrchestratorConfig {
  pipeline_mode: 'multiagent_only';
  actual_pipeline_mode?: 'multiagent_only';
  active_runtime: 'multiagent';
  runtime_entrypoint?: 'multiagent_adapter' | 'answer_adaptive_deprecated_shim';
  legacy?: Record<string, unknown>;
  compatibility?: {
    pipeline_mode: 'multiagent_only';
    pipeline_mode_legacy_value?: string | null;
    pipeline_mode_read_only: boolean;
    legacy_modes_selectable: boolean;
  };
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
  kind?: string;
  llm_model_effective?: boolean;
  note?: string;
}

export interface AgentLLMConfigResponse {
  agents: { [agentId: string]: AgentLLMEntry };
  allowed_models: string[];
}

export type PipelineMode = 'multiagent_only';

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
  active_runtime: 'multiagent';
  runtime_entrypoint?: 'multiagent_adapter' | 'answer_adaptive_deprecated_shim';
  legacy?: Record<string, unknown>;
  compatibility?: Record<string, unknown>;
  agent_contract?: Record<string, Record<string, unknown>>;
  feature_flags: Record<string, string>;
  agents: AgentOverviewStatus[];
  recent_traces: RecentTrace[];
  server_time: string;
  schema_version: string;
}

export interface DiagnosticCenterBoundaryFlags {
  broad_rollout_allowed: boolean;
  production_ready: boolean;
  normal_user_activation_allowed: boolean;
  external_users_allowed: boolean;
}

export interface DiagnosticCenterControlState {
  mode: string;
  force_disabled: boolean;
  allowlist_user_ids: string[];
  developer_all_users_enabled: boolean;
  updated_at: string;
  updated_by: string;
  reason: string;
}

export interface DiagnosticCenterEffectiveResponse {
  schema_version: string;
  status: string;
  current_mode: string;
  effective_active: boolean;
  force_disabled: boolean;
  kill_switch_available: boolean;
  single_developer_project: boolean;
  available_modes: string[];
  developer_identity: {
    creator_user_id: string;
    developer_user_ids: string[];
    allowlist_user_ids: string[];
  };
  boundary_flags: DiagnosticCenterBoundaryFlags;
  scope: {
    runtime_scope: string;
    external_rollout_scope: string;
    note: string;
  };
  last_evidence: {
    last_prd: string;
    diagnostic_center_track_status: string;
    recommended_runner_timeout_sec: number;
  };
  control_state: DiagnosticCenterControlState;
  warnings: string[];
}

export interface DiagnosticCenterControlUpdateRequest {
  mode: string;
  force_disabled: boolean;
  allowlist_user_ids: string[];
  reason?: string;
}
