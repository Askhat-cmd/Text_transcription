import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../hooks/useAdminConfig', () => ({
  useAdminConfig: () => ({
    configData: {
      groups: {
        memory: { label: 'Memory', params: {} },
        storage: { label: 'Storage', params: {} },
        runtime: { label: 'Runtime', params: {} },
      },
    },
    prompts: [],
    selectedPrompt: null,
    statusData: {
      degraded_mode: false,
      data_source: 'api',
      blocks_loaded: 10,
      version: 'test',
    },
    runtimeEffectiveData: {
      schema_version: 'v1',
      admin_schema_version: 'v1',
      prompt_stack_version: 'v1',
      active_runtime: 'multiagent',
      runtime_entrypoint: 'multiagent_adapter',
      pipeline_version: 'multiagent_v1',
      pipeline_mode: 'multiagent_only',
      pipeline_mode_read_only: true,
      legacy_modes_selectable: false,
      legacy: {
        fallback_enabled: false,
        fallback_used: false,
        cascade_available: false,
        cascade_status: 'deprecated_retained_for_purge',
        purge_planned_prd: 'PRD-041',
      },
      compatibility: {
        pipeline_mode: 'multiagent_only',
        pipeline_mode_read_only: true,
        legacy_modes_selectable: false,
        dialogue_profile_alias: {
          primary_profile: 'free_dialogue_default',
          legacy_alias: 'mvp_free_dialogue',
          modern_label: 'free_dialogue_default',
          surface_role: 'compatibility_only',
        },
        knowledge_graph: {
          enabled: false,
          status: 'disabled_legacy',
          surface_role: 'compatibility_only',
          note: 'Legacy graph subsystem is not a primary runtime control surface.',
        },
      },
      agents: {},
      status: {
        degraded_mode: false,
        data_source: 'api',
        blocks_loaded: 10,
        version: 'test',
      },
      feature_flags: { all: {}, groups: {} },
      diagnostics: {},
      routing: {},
      validation: { enabled: true, config_validation_status: { valid: true, errors: [] } },
      trace: { available: true },
      dialogue_profile: {
        value: 'mvp_free_dialogue',
        primary_profile: 'free_dialogue_default',
        legacy_alias: 'mvp_free_dialogue',
        legacy_alias_visible_in_runtime: false,
        allowed_values: ['safe_guided', 'mvp_free_dialogue'],
      },
      dialogue_policy: {
        version: 'unified_dialogue_policy_v2',
        profile_preset: 'free_dialogue_default',
        active_profile_alias: 'mvp_free_dialogue',
        writer_autonomy: 'high',
        effective_safety_floor: 'minimal_baseline',
        planner_authority: 'advisory',
        diagnostic_card_authority: 'advisory',
        writer_move_authority: 'writer_first',
        context_budget_chars: 4000,
        allow_practice_catalog: false,
        final_answer_directive_enabled: true,
        final_answer_acceptance_gate: {
          enabled: true,
          version: 'gate_v1',
          status_source: 'debug',
          quarantine_supported: true,
          retry_supported: true,
        },
        writer_context_package_role: 'single_context_package',
        writer_first_prompt_assembly_enabled: true,
        legacy_prompt_blocks_mode: 'source_signals_only',
        legacy_blocks_visible_to_writer: false,
        legacy_blocks_source_signals_only: true,
        diagnostic_center_role: 'advisory_context_only',
        planner_role: 'advisory_context_only',
        active_line_role: 'advisory_context_only',
        diagnostic_card_role: 'advisory_context_only',
        dialogue_act_resolver_enabled: true,
        last_offer_tracker_enabled: true,
        unanswered_question_tracker_enabled: true,
        style_state_enabled: true,
        broad_rollout_allowed: false,
        production_ready: false,
        human_like_answer_policy: { enabled: true, answer_style: 'human', default_depth: 'adaptive', question_is_optional: true },
        constraint_resolution: { planner_authority: 'advisory', overruled_constraints: [], overrule_reason: 'writer_first' },
        fresh_chat_context_policy_version: 'fresh_chat_v1',
        fresh_chat_rag_default: 'suppress_on_greeting_without_explicit_question',
        current_chat_reset_control: { endpoint: '/reset', scope: 'session_only', preserves_session_id: true },
        writer_context_package_version: 'writer_ctx_v1',
        web_chat_markdown_renderer: 'react_markdown_gfm',
        user_memory_profile_clear_control: { endpoint: '/history', scope: 'user_level', developer_visible: true },
      },
      philosophy_kernel: { enabled: true, version: 'kernel_v1', quote_policy: 'internal', practice_policy: 'gate_required', principles_count: 1, boundaries_count: 1, lenses: ['a'], selected_lenses_visible: true, prompt_budget: { max_kernel_chars: 1, max_combined_chars: 1 }, quality_calibration: { last_direct_passed: true, last_direct_cases_total: 1 } },
      writer_freedom_contract: { enabled: true, version: 'writer_contract_v1', freedom_level: 'mvp_free', mode_is_hint_not_cage: true, question_limit: 1, practice_requires_gate: true, writer_max_tokens: 2500, writer_target_tokens_default: 700, writer_target_tokens_expanded: 1500, writer_allow_long_answer: true },
      active_line: { enabled: true, version: 'active_line_v1', user_intent: 'runtime', continuity_mode: 'runtime', revoicing_policy: 'suppress', practice_suppression_active: true, last_quality_calibration: { last_direct_passed: true, last_direct_cases_total: 1 } },
      response_planner: { enabled: true, version: 'response_planner_v1', kind: 'deterministic', role: 'selector', advisory_mode: true, live_acceptance_requires_api_trace: true, last_quality_calibration: { last_direct_passed: true, last_direct_cases_total: 1 } },
      planner_drift_guard: { enabled: true, version: 'planner_drift_guard_v1', mode: 'observe_only', blocking_user_answers: false, window_size: 100, thresholds: { warning_violation_rate: 0.1, critical_rate: 0.03 }, mvp_expansion_exceptions: { answer_length_long_when_expansion_requested: true, numbered_list_when_expansion_requested: true, multi_block_answer_when_concept_explanation_full: true }, last_summary: { total: 1, warning_count: 0, critical_count: 0, threshold_status: 'ok' }, last_replay_status: { direct: 'passed', live: 'passed' } },
      guided_live_testing: { enabled: true, schema_version: 'live_v1', mode: 'developer_local', feedback_storage: 'file', raw_dialogue_saved_by_default: false, scenario_set: 'set', scenario_count: 1, last_session_summary_available: true },
      hybrid_retrieval_planner: { enabled: true, version: 'hybrid_retrieval_planner_v1_r1', mode: 'shadow', model: 'gpt-5-nano', max_tokens: 320, default_safe_mode: 'shadow', metadata_only: true, query_before_rag_supported: true, writer_final_author_preserved: true, allowed_modes: ['off', 'shadow', 'apply'], llm_optional_for_complex_cases: true, domain_specific_hardcoding_allowed: false },
    },
    diagnosticsEffectiveData: null,
    diagnosticCenterEffectiveData: null,
    isLoading: false,
    isSaving: false,
    error: null,
    promptError: null,
    successMessage: null,
    clearError: vi.fn(),
    loadConfig: vi.fn(),
    loadPrompts: vi.fn(),
    loadPromptDetail: vi.fn(),
    retryPromptDetailLoad: vi.fn(),
    loadRuntimeEffective: vi.fn(),
    loadDiagnosticsEffective: vi.fn(),
    loadDiagnosticCenterEffective: vi.fn(),
    saveDiagnosticCenterControl: vi.fn(),
    resetDiagnosticCenterControl: vi.fn(),
    loadStatus: vi.fn(),
    reloadKnowledgeBase: vi.fn(),
    saveConfigParam: vi.fn(),
    resetConfigParam: vi.fn(),
    resetAllConfig: vi.fn(),
    savePrompt: vi.fn(),
    resetPrompt: vi.fn(),
    resetAllPrompts: vi.fn(),
    exportOverrides: vi.fn(),
    importOverrides: vi.fn(),
  }),
}));

vi.mock('../../hooks/useOrchestrator', () => ({
  useOrchestrator: () => ({
    orchestratorConfig: { runtime_entrypoint: 'multiagent_adapter' },
    loadOrchestratorConfig: vi.fn(),
  }),
}));

vi.mock('../../services/adminConfig.service', () => ({
  adminConfigService: {
    getHistory: vi.fn().mockResolvedValue({ history: [] }),
    resetAll: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('./ConfigGroupPanel', () => ({
  ConfigGroupPanel: ({ groupKey }: { groupKey: string }) => React.createElement('div', null, `ConfigGroup:${groupKey}`),
}));
vi.mock('./PromptEditorPanel', () => ({ PromptEditorPanel: () => React.createElement('div', null, 'PromptEditor') }));
vi.mock('./HistoryPanel', () => ({ HistoryPanel: () => React.createElement('div', null, 'HistoryPanel') }));
vi.mock('./AgentsTab', () => ({ AgentsTab: () => React.createElement('div', null, 'AgentsTab') }));
vi.mock('./OrchestratorTab', () => ({ OrchestratorTab: () => React.createElement('div', null, 'OrchestratorTab') }));
vi.mock('./ThreadsTab', () => ({ ThreadsTab: () => React.createElement('div', null, 'ThreadsTab') }));
vi.mock('./AgentPromptEditorPanel', () => ({ AgentPromptEditorPanel: () => React.createElement('div', null, 'AgentPromptEditorPanel') }));
vi.mock('./AdminOverviewTab', () => ({ AdminOverviewTab: () => React.createElement('div', null, 'AdminOverviewTab') }));
vi.mock('./DiagnosticCenterTab', () => ({ DiagnosticCenterTab: () => React.createElement('div', null, 'DiagnosticCenterTab') }));

import { AdminPanel } from './AdminPanel';

function renderNode(element: React.ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);
  act(() => {
    root.render(element);
  });
  return {
    container,
    cleanup() {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function clickByText(container: HTMLElement, text: string): void {
  const target = Array.from(container.querySelectorAll('button')).find((button) => (button.textContent || '').includes(text));
  expect(target).toBeTruthy();
  act(() => {
    target?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

describe('AdminPanel HF2-R2 visibility', () => {
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    localStorage.setItem('devApiKey', 'dev-key-001');
  });

  it('shows runtime hybrid retrieval block and compatibility-only advanced controls', async () => {
    const harness = renderNode(React.createElement(AdminPanel));

    clickByText(harness.container, 'Runtime');
    expect(harness.container.textContent).toContain('Hybrid Retrieval Planner');
    expect(harness.container.textContent).toContain('gpt-5-nano');
    expect(harness.container.textContent).not.toContain('ConfigGroup:runtime');

    const summary = harness.container.querySelector('summary');
    expect(summary?.textContent).toContain('Advanced Controls');
    act(() => {
      summary?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    const buttonLabels = Array.from(harness.container.querySelectorAll('button')).map((button) => (button.textContent || '').trim());
    expect(buttonLabels).toContain('Compatibility');
    expect(buttonLabels).not.toContain('Retrieval');
    expect(buttonLabels).not.toContain('Routing');

    clickByText(harness.container, 'Compatibility');
    expect(harness.container.textContent).toContain('Compatibility / Legacy Status');
    expect(harness.container.textContent).toContain('disabled_legacy');
    expect(harness.container.textContent).toContain('mvp_free_dialogue');

    harness.cleanup();
  });
});
