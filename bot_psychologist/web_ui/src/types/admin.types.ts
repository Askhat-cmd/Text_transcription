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
}
