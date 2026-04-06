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

export interface PromptStackUsageResponse {
  schema_version: string;
  prompt_stack_version: string;
  last_turn_available: boolean;
  last_turn: {
    session_id?: string | null;
    turn_number?: number | null;
    used_sections: string[];
  };
  sections: PromptMeta[];
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
  };
}

export interface AdminTraceTurnPayload {
  turn_id?: string | number | null;
  turn_number?: number | null;
  timestamp?: string | null;
  query?: string | null;
  diagnostics?: Record<string, unknown>;
  routing?: Record<string, unknown>;
  retrieval?: Record<string, unknown>;
  prompt_stack?: Record<string, unknown>;
  validation?: Record<string, unknown>;
  memory?: Record<string, unknown>;
  flags?: Record<string, unknown>;
  anomalies?: unknown[];
  degraded_mode?: boolean;
}

export interface AdminTraceLastResponse {
  schema_version: string;
  available: boolean;
  reason?: string;
  trace: AdminTraceTurnPayload | null;
}

export interface AdminTraceRecentResponse {
  schema_version: string;
  available: boolean;
  count: number;
  traces: AdminTraceTurnPayload[];
}
