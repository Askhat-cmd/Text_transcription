import React, { useEffect, useRef, useState } from 'react';

import { useAdminConfig } from '../../hooks/useAdminConfig';
import { useOrchestrator } from '../../hooks/useOrchestrator';
import { GROUP_COLORS } from '../../constants/adminColors';
import type { HistoryEntry } from '../../types/admin.types';
import { ConfigGroupPanel } from './ConfigGroupPanel';
import { HistoryPanel } from './HistoryPanel';
import { AgentsTab } from './AgentsTab';
import { OrchestratorTab } from './OrchestratorTab';
import { ThreadsTab } from './ThreadsTab';
import { AgentPromptEditorPanel } from './AgentPromptEditorPanel';
import { AdminOverviewTab } from './AdminOverviewTab';
import { DiagnosticCenterTab } from './DiagnosticCenterTab';

type Tab =
  | 'overview'
  | 'agents'
  | 'orchestrator'
  | 'threads'
  | 'agent_prompts'
  | 'runtime'
  | 'diagnostic_center'
  | 'memory'
  | 'compatibility';

const PRIMARY_TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'overview', label: 'Overview', hoverColor: 'hover:bg-sky-500/20' },
  { key: 'agents', label: 'Agents', hoverColor: 'hover:bg-purple-500/20' },
  { key: 'orchestrator', label: 'Orchestrator', hoverColor: 'hover:bg-indigo-500/20' },
  { key: 'threads', label: 'Threads', hoverColor: 'hover:bg-teal-500/20' },
  { key: 'agent_prompts', label: 'Agent Prompts', hoverColor: 'hover:bg-fuchsia-500/20' },
  { key: 'runtime', label: 'Runtime', hoverColor: 'hover:bg-slate-500/20' },
  { key: 'diagnostic_center', label: 'Diagnostic Center', hoverColor: 'hover:bg-orange-500/20' },
  { key: 'memory', label: 'Memory', hoverColor: 'hover:bg-emerald-500/20' },
];

const ADVANCED_TABS: { key: Tab; label: string; hoverColor: string }[] = [
  { key: 'compatibility', label: 'Compatibility', hoverColor: 'hover:bg-amber-500/20' },
];

const ADVANCED_TAB_KEYS = new Set<Tab>(['compatibility']);

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [legacyOpen, setLegacyOpen] = useState(false);
  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem('devApiKey') || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    configData,
    statusData,
    runtimeEffectiveData,
    diagnosticCenterEffectiveData,
    isLoading,
    isSaving,
    error,
    successMessage,
    clearError,
    loadConfig,
    loadPrompts,
    loadRuntimeEffective,
    loadDiagnosticsEffective,
    loadDiagnosticCenterEffective,
    saveDiagnosticCenterControl,
    resetDiagnosticCenterControl,
    loadStatus,
    reloadKnowledgeBase,
    saveConfigParam,
    resetConfigParam,
    resetAllConfig,
    exportOverrides,
    importOverrides,
  } = useAdminConfig();

  const { orchestratorConfig, loadOrchestratorConfig } = useOrchestrator();

  useEffect(() => {
    if (apiKey) localStorage.setItem('devApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => {
    loadConfig();
    loadPrompts();
    loadStatus();
    loadRuntimeEffective();
    loadDiagnosticsEffective();
    loadDiagnosticCenterEffective();
    void loadOrchestratorConfig();
  }, []);

  useEffect(() => {
    if (activeTab !== 'compatibility') return;
    import('../../services/adminConfig.service').then(({ adminConfigService }) => {
      adminConfigService.getHistory().then((data) => setHistory(data.history));
    });
  }, [activeTab]);

  useEffect(() => {
    if (ADVANCED_TAB_KEYS.has(activeTab)) {
      setLegacyOpen(true);
    }
  }, [activeTab]);

  const handleResetConfigParam = async (key: string) => {
    if (key === '__all__') await resetAllConfig();
    else await resetConfigParam(key);
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await importOverrides(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const pipelineBadgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  const runtimeEntrypoint = orchestratorConfig?.runtime_entrypoint ?? 'multiagent_adapter';

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="bg-gradient-to-r from-slate-900 to-slate-700 px-6 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">Admin Config Panel</h1>
                <p className="text-sm text-slate-400 mt-0.5">Multiagent-first control surface</p>
                <div className="mt-2">
                  <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${pipelineBadgeClass}`}>
                    multiagent
                  </span>
                  <span className="ml-2 inline-flex items-center rounded border border-slate-500/50 bg-slate-700/30 px-2 py-0.5 text-xs text-slate-200">
                    entrypoint: {runtimeEntrypoint}
                  </span>
                  <span className="ml-2 inline-flex items-center rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                    legacy fallback: disabled
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="dev-key-001"
                    className="w-48 px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-400"
                  />
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
                  >
                    {showApiKey ? 'hide' : 'show'}
                  </button>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded font-medium ${
                    apiKey
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}
                >
                  {apiKey ? 'ok' : 'empty'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={exportOverrides}
                className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300 hover:bg-slate-600 transition-colors"
              >
                Export
              </button>
              <label className="px-3 py-1.5 border border-slate-500 rounded text-sm text-slate-300 hover:bg-slate-600 transition-colors cursor-pointer">
                Import
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={handleImportFile}
                />
              </label>
              <button
                onClick={async () => {
                  if (!window.confirm('Full reset: delete all overrides (config + prompts)?')) return;
                  const { adminConfigService } = await import('../../services/adminConfig.service');
                  await adminConfigService.resetAll();
                  await loadConfig();
                  await loadPrompts();
                }}
                className="px-3 py-1.5 border border-red-500/40 rounded text-sm text-red-400 hover:bg-red-500/20 transition-colors"
              >
                Full reset
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-800 px-6 shadow-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <div className="flex gap-1">
            {PRIMARY_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                  activeTab === tab.key
                    ? 'border-violet-400 text-white bg-white/5'
                    : `border-transparent text-slate-400 ${tab.hoverColor} hover:text-white`
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <details className="relative" open={legacyOpen} onToggle={(e) => setLegacyOpen((e.target as HTMLDetailsElement).open)}>
            <summary className="list-none cursor-pointer px-3 py-1.5 text-xs border border-slate-600 rounded text-slate-300 hover:bg-slate-700">
              Advanced Controls
            </summary>
            <div className="absolute right-0 mt-1 w-[34rem] rounded border border-slate-700 bg-slate-900 p-2 shadow-lg z-20">
              <div className="flex flex-wrap gap-1">
                {ADVANCED_TABS.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-3 py-1.5 text-xs rounded transition-all ${
                      activeTab === tab.key ? 'bg-white/10 text-white' : `text-slate-300 ${tab.hoverColor} hover:text-white`
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </details>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 pt-3">
        {error && (
          <div className="flex items-center justify-between px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
            <span>{error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">x</button>
          </div>
        )}
        {successMessage && (
          <div className="px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700 mb-3">
            {successMessage}
          </div>
        )}
      </div>

      <div className="max-w-6xl mx-auto px-6 pb-10">
        {isLoading && <div className="text-center text-slate-400 py-12 text-sm">Loading...</div>}

        {!isLoading && configData && (
          <>
            {activeTab === 'overview' && <AdminOverviewTab />}
            {activeTab === 'agents' && <AgentsTab />}
            {activeTab === 'orchestrator' && <OrchestratorTab />}
            {activeTab === 'threads' && <ThreadsTab />}
            {activeTab === 'diagnostic_center' && (
              <DiagnosticCenterTab
                data={diagnosticCenterEffectiveData}
                onRefresh={loadDiagnosticCenterEffective}
                onSave={saveDiagnosticCenterControl}
                onReset={resetDiagnosticCenterControl}
                isSaving={isSaving}
              />
            )}
            {activeTab === 'agent_prompts' && (
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-900 shadow-md h-[70vh] overflow-hidden">
                <AgentPromptEditorPanel />
              </div>
            )}

            {(activeTab === 'memory' || activeTab === 'runtime') && (
              <div className="mt-4 space-y-4">
                {activeTab === 'memory' &&
                  Object.entries(configData.groups)
                    .filter(([groupKey]) => groupKey === activeTab)
                    .map(([groupKey, group]) => (
                      <ConfigGroupPanel
                        key={groupKey}
                        groupKey={groupKey}
                        group={group}
                        onSave={saveConfigParam}
                        onReset={handleResetConfigParam}
                        isSaving={isSaving}
                        accentColor={GROUP_COLORS[groupKey] ?? 'blue'}
                      />
                    ))}

                {activeTab === 'runtime' && statusData && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                    <h3 className="font-semibold text-slate-800 mb-3">System Status</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
                      <div>data_source: <span className="font-medium">{statusData.data_source}</span></div>
                      <div>blocks_loaded: <span className="font-medium">{statusData.blocks_loaded}</span></div>
                      <div>degraded_mode: <span className="font-medium">{statusData.degraded_mode ? 'on' : 'off'}</span></div>
                      <div>version: <span className="font-medium">{statusData.version}</span></div>
                    </div>
                    <div className="mt-3">
                      <button
                        onClick={reloadKnowledgeBase}
                        disabled={isSaving}
                        className="px-3 py-1.5 rounded bg-slate-700 text-white text-sm hover:bg-slate-800 disabled:opacity-50"
                      >
                        Reload knowledge base
                      </button>
                    </div>
                  </div>
                )}

                {activeTab === 'runtime' && runtimeEffectiveData && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4">
                    <h3 className="font-semibold text-slate-800 mb-3">Philosophy Kernel / Writer Freedom (Effective)</h3>
                    <div className="grid grid-cols-1 md:grid-cols-6 gap-3 text-sm text-slate-700">
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Philosophy Kernel</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.philosophy_kernel?.enabled))}</div>
                        <div>version: {runtimeEffectiveData.philosophy_kernel?.version ?? 'n/a'}</div>
                        <div>quote_policy: {runtimeEffectiveData.philosophy_kernel?.quote_policy ?? 'n/a'}</div>
                        <div>practice_policy: {runtimeEffectiveData.philosophy_kernel?.practice_policy ?? 'n/a'}</div>
                        <div>principles_count: {runtimeEffectiveData.philosophy_kernel?.principles_count ?? 0}</div>
                        <div>boundaries_count: {runtimeEffectiveData.philosophy_kernel?.boundaries_count ?? 0}</div>
                        <div>lenses: {(runtimeEffectiveData.philosophy_kernel?.lenses ?? []).join(', ') || 'n/a'}</div>
                        <div>selected_lenses_visible: {String(Boolean(runtimeEffectiveData.philosophy_kernel?.selected_lenses_visible))}</div>
                        <div>budget.max_kernel_chars: {runtimeEffectiveData.philosophy_kernel?.prompt_budget?.max_kernel_chars ?? 'n/a'}</div>
                        <div>budget.max_combined_chars: {runtimeEffectiveData.philosophy_kernel?.prompt_budget?.max_combined_chars ?? 'n/a'}</div>
                        <div>quality.last_prd: {runtimeEffectiveData.philosophy_kernel?.quality_calibration?.last_prd ?? 'n/a'}</div>
                        <div>quality.last_direct_passed: {String(Boolean(runtimeEffectiveData.philosophy_kernel?.quality_calibration?.last_direct_passed))}</div>
                        <div>quality.last_direct_cases_total: {runtimeEffectiveData.philosophy_kernel?.quality_calibration?.last_direct_cases_total ?? 0}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Writer Freedom Contract</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.writer_freedom_contract?.enabled))}</div>
                        <div>version: {runtimeEffectiveData.writer_freedom_contract?.version ?? 'n/a'}</div>
                        <div>freedom_level: {runtimeEffectiveData.writer_freedom_contract?.freedom_level ?? 'n/a'}</div>
                        <div>mode_is_hint_not_cage: {String(Boolean(runtimeEffectiveData.writer_freedom_contract?.mode_is_hint_not_cage))}</div>
                        <div>question_limit: {runtimeEffectiveData.writer_freedom_contract?.question_limit ?? 1}</div>
                        <div>practice_requires_gate: {String(Boolean(runtimeEffectiveData.writer_freedom_contract?.practice_requires_gate))}</div>
                        <div>writer_max_tokens: {runtimeEffectiveData.writer_freedom_contract?.writer_max_tokens ?? 'n/a'}</div>
                        <div>writer_target_tokens_default: {runtimeEffectiveData.writer_freedom_contract?.writer_target_tokens_default ?? 'n/a'}</div>
                        <div>writer_target_tokens_expanded: {runtimeEffectiveData.writer_freedom_contract?.writer_target_tokens_expanded ?? 'n/a'}</div>
                        <div>writer_allow_long_answer: {String(Boolean(runtimeEffectiveData.writer_freedom_contract?.writer_allow_long_answer))}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Dialogue Profile Preset / Alias</div>
                        <div className="text-xs text-slate-500">
                          Profiles are presets resolved by unified_dialogue_policy_v2, not separate runtime paths.
                        </div>
                        <div>Unified Policy: {runtimeEffectiveData.dialogue_policy?.version ?? 'n/a'}</div>
                        <div>primary_profile: {runtimeEffectiveData.dialogue_profile?.primary_profile ?? runtimeEffectiveData.dialogue_profile?.profile_preset ?? 'guided'}</div>
                        <div>legacy_alias: {runtimeEffectiveData.dialogue_profile?.legacy_alias ?? runtimeEffectiveData.dialogue_policy?.active_profile_alias ?? 'n/a'}</div>
                        <div>legacy_alias_visible_in_runtime: {String(Boolean(runtimeEffectiveData.dialogue_profile?.legacy_alias_visible_in_runtime))}</div>
                        <div>profile_preset: {runtimeEffectiveData.dialogue_policy?.profile_preset ?? 'n/a'}</div>
                        <div>allowed_values: {(runtimeEffectiveData.dialogue_profile?.allowed_values ?? []).join(', ') || 'n/a'}</div>
                        <div>scope: {runtimeEffectiveData.dialogue_profile?.scope ?? 'n/a'}</div>
                        <div>developer_local_only: {String(Boolean(runtimeEffectiveData.dialogue_profile?.developer_local_only))}</div>
                        <div>description: {runtimeEffectiveData.dialogue_profile?.description ?? 'n/a'}</div>
                        <div>effective.writer_autonomy: {runtimeEffectiveData.dialogue_policy?.writer_autonomy ?? 'n/a'}</div>
                        <div>effective.safety_floor: {runtimeEffectiveData.dialogue_policy?.effective_safety_floor ?? 'n/a'}</div>
                        <div>effective.planner_authority: {runtimeEffectiveData.dialogue_policy?.planner_authority ?? 'n/a'}</div>
                        <div>effective.diagnostic_card_authority: {runtimeEffectiveData.dialogue_policy?.diagnostic_card_authority ?? 'n/a'}</div>
                        <div>effective.writer_move_authority: {runtimeEffectiveData.dialogue_policy?.writer_move_authority ?? 'n/a'}</div>
                        <div>effective.context_budget_chars: {runtimeEffectiveData.dialogue_policy?.context_budget_chars ?? 'n/a'}</div>
                        <div>effective.allow_practice_catalog: {String(Boolean(runtimeEffectiveData.dialogue_policy?.allow_practice_catalog))}</div>
                        <div>final_answer_directive_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.final_answer_directive_enabled))}</div>
                        <div>final_answer_directive_version: {runtimeEffectiveData.dialogue_policy?.final_answer_directive_version ?? 'n/a'}</div>
                        <div>final_answer_directive_role: {runtimeEffectiveData.dialogue_policy?.final_answer_directive_role ?? 'n/a'}</div>
                        <div>final_answer_acceptance_gate.enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.final_answer_acceptance_gate?.enabled))}</div>
                        <div>final_answer_acceptance_gate.version: {runtimeEffectiveData.dialogue_policy?.final_answer_acceptance_gate?.version ?? 'n/a'}</div>
                        <div>final_answer_acceptance_gate.status_source: {runtimeEffectiveData.dialogue_policy?.final_answer_acceptance_gate?.status_source ?? 'n/a'}</div>
                        <div>final_answer_acceptance_gate.quarantine_supported: {String(Boolean(runtimeEffectiveData.dialogue_policy?.final_answer_acceptance_gate?.quarantine_supported))}</div>
                        <div>final_answer_acceptance_gate.retry_supported: {String(Boolean(runtimeEffectiveData.dialogue_policy?.final_answer_acceptance_gate?.retry_supported))}</div>
                        <div>writer_context_package_role: {runtimeEffectiveData.dialogue_policy?.writer_context_package_role ?? 'n/a'}</div>
                        <div>writer_first_prompt_assembly_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.writer_first_prompt_assembly_enabled))}</div>
                        <div>legacy_prompt_blocks_mode: {runtimeEffectiveData.dialogue_policy?.legacy_prompt_blocks_mode ?? 'n/a'}</div>
                        <div>legacy_blocks_visible_to_writer: {String(Boolean(runtimeEffectiveData.dialogue_policy?.legacy_blocks_visible_to_writer))}</div>
                        <div>legacy_blocks_source_signals_only: {String(Boolean(runtimeEffectiveData.dialogue_policy?.legacy_blocks_source_signals_only))}</div>
                        <div>diagnostic_center_role: {runtimeEffectiveData.dialogue_policy?.diagnostic_center_role ?? 'n/a'} (advisory-only boundary)</div>
                        <div>planner_role: {runtimeEffectiveData.dialogue_policy?.planner_role ?? 'n/a'}</div>
                        <div>active_line_role: {runtimeEffectiveData.dialogue_policy?.active_line_role ?? 'n/a'}</div>
                        <div>diagnostic_card_role: {runtimeEffectiveData.dialogue_policy?.diagnostic_card_role ?? 'n/a'}</div>
                        <div>dialogue_act_resolver_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.dialogue_act_resolver_enabled))}</div>
                        <div>last_offer_tracker_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.last_offer_tracker_enabled))}</div>
                        <div>unanswered_question_tracker_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.unanswered_question_tracker_enabled))}</div>
                        <div>style_state_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.style_state_enabled))}</div>
                        <div>broad_rollout_allowed: {String(Boolean(runtimeEffectiveData.dialogue_policy?.broad_rollout_allowed))}</div>
                        <div>production_ready: {String(Boolean(runtimeEffectiveData.dialogue_policy?.production_ready))}</div>
                        <div>human_like.enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.human_like_answer_policy?.enabled))}</div>
                        <div>human_like.answer_style: {runtimeEffectiveData.dialogue_policy?.human_like_answer_policy?.answer_style ?? 'n/a'}</div>
                        <div>human_like.default_depth: {runtimeEffectiveData.dialogue_policy?.human_like_answer_policy?.default_depth ?? 'n/a'}</div>
                        <div>human_like.question_is_optional: {String(Boolean(runtimeEffectiveData.dialogue_policy?.human_like_answer_policy?.question_is_optional))}</div>
                        <div>constraint.planner_authority: {runtimeEffectiveData.dialogue_policy?.constraint_resolution?.planner_authority ?? 'n/a'}</div>
                        <div>constraint.overruled_constraints: {(runtimeEffectiveData.dialogue_policy?.constraint_resolution?.overruled_constraints ?? []).join(', ') || 'none'}</div>
                        <div>constraint.overrule_reason: {runtimeEffectiveData.dialogue_policy?.constraint_resolution?.overrule_reason ?? 'n/a'}</div>
                        {runtimeEffectiveData.dialogue_profile?.warning && (
                          <div className="mt-1 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                            {runtimeEffectiveData.dialogue_profile.warning}
                          </div>
                        )}
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Active Line</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.active_line?.enabled))}</div>
                        <div>version: {runtimeEffectiveData.active_line?.version ?? 'n/a'}</div>
                        <div>user_intent: {runtimeEffectiveData.active_line?.user_intent ?? 'n/a'}</div>
                        <div>continuity_mode: {runtimeEffectiveData.active_line?.continuity_mode ?? 'n/a'}</div>
                        <div>revoicing_policy: {runtimeEffectiveData.active_line?.revoicing_policy ?? 'n/a'}</div>
                        <div>practice_suppression_active: {String(Boolean(runtimeEffectiveData.active_line?.practice_suppression_active))}</div>
                        <div>quality.last_prd: {runtimeEffectiveData.active_line?.last_quality_calibration?.last_prd ?? 'n/a'}</div>
                        <div>quality.last_direct_passed: {String(Boolean(runtimeEffectiveData.active_line?.last_quality_calibration?.last_direct_passed))}</div>
                        <div>quality.last_direct_cases_total: {runtimeEffectiveData.active_line?.last_quality_calibration?.last_direct_cases_total ?? 0}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Response Planner</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.response_planner?.enabled))}</div>
                        <div>version: {runtimeEffectiveData.response_planner?.version ?? 'n/a'}</div>
                        <div>kind: {runtimeEffectiveData.response_planner?.kind ?? 'n/a'}</div>
                        <div>role: {runtimeEffectiveData.response_planner?.role ?? 'n/a'}</div>
                        <div>advisory_mode: {String(Boolean(runtimeEffectiveData.response_planner?.advisory_mode))}</div>
                        <div>live_acceptance_requires_api_trace: {String(Boolean(runtimeEffectiveData.response_planner?.live_acceptance_requires_api_trace))}</div>
                        <div>quality.last_prd: {runtimeEffectiveData.response_planner?.last_quality_calibration?.last_prd ?? 'n/a'}</div>
                        <div>quality.last_direct_passed: {String(Boolean(runtimeEffectiveData.response_planner?.last_quality_calibration?.last_direct_passed))}</div>
                        <div>quality.last_direct_cases_total: {runtimeEffectiveData.response_planner?.last_quality_calibration?.last_direct_cases_total ?? 0}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Planner Drift Guard</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.planner_drift_guard?.enabled))}</div>
                        <div>version: {runtimeEffectiveData.planner_drift_guard?.version ?? 'n/a'}</div>
                        <div>mode: {runtimeEffectiveData.planner_drift_guard?.mode ?? 'n/a'}</div>
                        <div>blocking_user_answers: {String(Boolean(runtimeEffectiveData.planner_drift_guard?.blocking_user_answers))}</div>
                        <div>window_size: {runtimeEffectiveData.planner_drift_guard?.window_size ?? 0}</div>
                        <div>threshold.warning_violation_rate: {runtimeEffectiveData.planner_drift_guard?.thresholds?.warning_violation_rate ?? 'n/a'}</div>
                        <div>threshold.critical_rate: {runtimeEffectiveData.planner_drift_guard?.thresholds?.critical_rate ?? 'n/a'}</div>
                        <div>summary.total: {runtimeEffectiveData.planner_drift_guard?.last_summary?.total ?? 0}</div>
                        <div>summary.warning_count: {runtimeEffectiveData.planner_drift_guard?.last_summary?.warning_count ?? 0}</div>
                        <div>summary.critical_count: {runtimeEffectiveData.planner_drift_guard?.last_summary?.critical_count ?? 0}</div>
                        <div>summary.threshold_status: {runtimeEffectiveData.planner_drift_guard?.last_summary?.threshold_status ?? 'n/a'}</div>
                        <div>mvp_expansion.answer_length_long_when_expansion_requested: {String(Boolean(runtimeEffectiveData.planner_drift_guard?.mvp_expansion_exceptions?.answer_length_long_when_expansion_requested))}</div>
                        <div>mvp_expansion.numbered_list_when_expansion_requested: {String(Boolean(runtimeEffectiveData.planner_drift_guard?.mvp_expansion_exceptions?.numbered_list_when_expansion_requested))}</div>
                        <div>mvp_expansion.multi_block_answer_when_concept_explanation_full: {String(Boolean(runtimeEffectiveData.planner_drift_guard?.mvp_expansion_exceptions?.multi_block_answer_when_concept_explanation_full))}</div>
                        <div>replay.direct: {runtimeEffectiveData.planner_drift_guard?.last_replay_status?.direct ?? 'n/a'}</div>
                        <div>replay.live: {runtimeEffectiveData.planner_drift_guard?.last_replay_status?.live ?? 'n/a'}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Guided Live Testing</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.guided_live_testing?.enabled))}</div>
                        <div>schema_version: {runtimeEffectiveData.guided_live_testing?.schema_version ?? 'n/a'}</div>
                        <div>mode: {runtimeEffectiveData.guided_live_testing?.mode ?? 'n/a'}</div>
                        <div>feedback_storage: {runtimeEffectiveData.guided_live_testing?.feedback_storage ?? 'n/a'}</div>
                        <div>raw_dialogue_saved_by_default: {String(Boolean(runtimeEffectiveData.guided_live_testing?.raw_dialogue_saved_by_default))}</div>
                        <div>scenario_set: {runtimeEffectiveData.guided_live_testing?.scenario_set ?? 'n/a'}</div>
                        <div>scenario_count: {runtimeEffectiveData.guided_live_testing?.scenario_count ?? 0}</div>
                        <div>last_session_summary_available: {String(Boolean(runtimeEffectiveData.guided_live_testing?.last_session_summary_available))}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3" data-testid="hf2-fresh-chat-runtime">
                        <div className="font-medium">Fresh Chat Isolation</div>
                        <div>policy_version: {runtimeEffectiveData.dialogue_policy?.fresh_chat_context_policy_version ?? 'n/a'}</div>
                        <div>rag_default: {runtimeEffectiveData.dialogue_policy?.fresh_chat_rag_default ?? 'n/a'}</div>
                        <div>current_chat_reset.endpoint: {runtimeEffectiveData.dialogue_policy?.current_chat_reset_control?.endpoint ?? 'n/a'}</div>
                        <div>current_chat_reset.scope: {runtimeEffectiveData.dialogue_policy?.current_chat_reset_control?.scope ?? 'n/a'}</div>
                        <div>
                          current_chat_reset.preserves_session_id:{' '}
                          {String(Boolean(runtimeEffectiveData.dialogue_policy?.current_chat_reset_control?.preserves_session_id))}
                        </div>
                      </div>
                      <div className="rounded border border-slate-200 p-3" data-testid="hf2-writer-context-runtime">
                        <div className="font-medium">Writer Context Gate</div>
                        <div>package_version: {runtimeEffectiveData.dialogue_policy?.writer_context_package_version ?? 'n/a'}</div>
                        <div>markdown_renderer: {runtimeEffectiveData.dialogue_policy?.web_chat_markdown_renderer ?? 'n/a'}</div>
                        <div>legacy_prompt_blocks_mode: {runtimeEffectiveData.dialogue_policy?.legacy_prompt_blocks_mode ?? 'n/a'}</div>
                        <div>
                          final_answer_directive_enabled: {String(Boolean(runtimeEffectiveData.dialogue_policy?.final_answer_directive_enabled))}
                        </div>
                        <div>
                          writer_first_prompt_assembly_enabled:{' '}
                          {String(Boolean(runtimeEffectiveData.dialogue_policy?.writer_first_prompt_assembly_enabled))}
                        </div>
                      </div>
                      <div className="rounded border border-slate-200 p-3" data-testid="hf1-semantic-cards-runtime">
                        <div className="font-medium">Semantic Cards Pilot</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.enabled))}</div>
                        <div>enabled_requested: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.enabled_requested))}</div>
                        <div>enabled_source: {runtimeEffectiveData.semantic_cards_pilot?.enabled_source ?? 'n/a'}</div>
                        <div>runtime_mode: {runtimeEffectiveData.semantic_cards_pilot?.runtime_mode ?? 'n/a'}</div>
                        <div>pack_id: {runtimeEffectiveData.semantic_cards_pilot?.pack_id ?? 'n/a'}</div>
                        <div>loaded_card_count: {runtimeEffectiveData.semantic_cards_pilot?.loaded_card_count ?? 0}</div>
                        <div>adapter_enabled: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.adapter_enabled))}</div>
                        <div>writer_payload_enabled: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.writer_payload_enabled))}</div>
                        <div>writer_payload_enabled_source: {runtimeEffectiveData.semantic_cards_pilot?.writer_payload_enabled_source ?? 'n/a'}</div>
                        <div>selection_surface: {runtimeEffectiveData.semantic_cards_pilot?.selection_surface ?? 'n/a'}</div>
                        <div>selected_cards_visible_in_turn_trace: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.selected_cards_visible_in_turn_trace))}</div>
                        <div>last_selected_count: {runtimeEffectiveData.semantic_cards_pilot?.last_selected_count ?? 'n/a'}</div>
                        <div>last_selected_ids: {(runtimeEffectiveData.semantic_cards_pilot?.last_selected_ids ?? []).join(', ') || 'n/a'}</div>
                        <div>authority: {runtimeEffectiveData.semantic_cards_pilot?.authority ?? 'n/a'}</div>
                        <div>writer_can_ignore: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.writer_can_ignore))}</div>
                        <div>applied_as_authority: {String(Boolean(runtimeEffectiveData.semantic_cards_pilot?.applied_as_authority))}</div>
                        <div>status: {runtimeEffectiveData.semantic_cards_pilot?.status ?? 'n/a'}</div>
                        <div>reason: {runtimeEffectiveData.semantic_cards_pilot?.reason ?? 'n/a'}</div>
                        <div>error: {runtimeEffectiveData.semantic_cards_pilot?.error ?? 'n/a'}</div>
                        <div className="mt-2 rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-900">
                          Semantic cards stay advisory-only. Per-turn selected card IDs are visible in chat trace, not applied as runtime authority.
                        </div>
                      </div>
                      <div className="rounded border border-slate-200 p-3" data-testid="hf2-memory-controls-runtime">
                        <div className="font-medium">Memory Controls</div>
                        <div>clear_profile.endpoint: {runtimeEffectiveData.dialogue_policy?.user_memory_profile_clear_control?.endpoint ?? 'n/a'}</div>
                        <div>clear_profile.scope: {runtimeEffectiveData.dialogue_policy?.user_memory_profile_clear_control?.scope ?? 'n/a'}</div>
                        <div>
                          clear_profile.developer_visible:{' '}
                          {String(Boolean(runtimeEffectiveData.dialogue_policy?.user_memory_profile_clear_control?.developer_visible))}
                        </div>
                        <div className="mt-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                          Current chat reset is session-only. Memory profile clear stays developer-visible only.
                        </div>
                      </div>
                      <div className="rounded border border-slate-200 p-3" data-testid="hf2-hybrid-retrieval-runtime">
                        <div className="font-medium">Hybrid Retrieval Planner</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.hybrid_retrieval_planner?.enabled))}</div>
                        <div>version: {runtimeEffectiveData.hybrid_retrieval_planner?.version ?? 'n/a'}</div>
                        <div>mode: {runtimeEffectiveData.hybrid_retrieval_planner?.mode ?? 'n/a'}</div>
                        <div>model: {runtimeEffectiveData.hybrid_retrieval_planner?.model ?? 'n/a'}</div>
                        <div>max_tokens: {runtimeEffectiveData.hybrid_retrieval_planner?.max_tokens ?? 'n/a'}</div>
                        <div>default_safe_mode: {runtimeEffectiveData.hybrid_retrieval_planner?.default_safe_mode ?? 'n/a'}</div>
                        <div>metadata_only: {String(Boolean(runtimeEffectiveData.hybrid_retrieval_planner?.metadata_only))}</div>
                        <div>query_before_rag_supported: {String(Boolean(runtimeEffectiveData.hybrid_retrieval_planner?.query_before_rag_supported))}</div>
                        <div>writer_final_author_preserved: {String(Boolean(runtimeEffectiveData.hybrid_retrieval_planner?.writer_final_author_preserved))}</div>
                        <div>allowed_modes: {(runtimeEffectiveData.hybrid_retrieval_planner?.allowed_modes ?? []).join(', ') || 'n/a'}</div>
                        <div>llm_optional_for_complex_cases: {String(Boolean(runtimeEffectiveData.hybrid_retrieval_planner?.llm_optional_for_complex_cases))}</div>
                        <div className="mt-2 rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-900">
                          Visibility-only developer surface. Planner metadata is observable here; Writer remains final author.
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'compatibility' && (
              <div className="mt-4 space-y-4">
                {runtimeEffectiveData && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-md p-4" data-testid="hf2-compatibility-runtime-status">
                    <h3 className="font-semibold text-slate-800 mb-3">Compatibility / Legacy Status</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-700">
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Dialogue Profile Alias</div>
                        <div>primary_profile: {runtimeEffectiveData.compatibility?.dialogue_profile_alias?.primary_profile ?? 'n/a'}</div>
                        <div>legacy_alias: {runtimeEffectiveData.compatibility?.dialogue_profile_alias?.legacy_alias ?? 'n/a'}</div>
                        <div>modern_label: {runtimeEffectiveData.compatibility?.dialogue_profile_alias?.modern_label ?? 'n/a'}</div>
                        <div>surface_role: {runtimeEffectiveData.compatibility?.dialogue_profile_alias?.surface_role ?? 'n/a'}</div>
                      </div>
                      <div className="rounded border border-slate-200 p-3">
                        <div className="font-medium">Knowledge Graph</div>
                        <div>enabled: {String(Boolean(runtimeEffectiveData.compatibility?.knowledge_graph?.enabled))}</div>
                        <div>status: {runtimeEffectiveData.compatibility?.knowledge_graph?.status ?? 'n/a'}</div>
                        <div>surface_role: {runtimeEffectiveData.compatibility?.knowledge_graph?.surface_role ?? 'n/a'}</div>
                        <div className="mt-1 text-xs text-slate-500">{runtimeEffectiveData.compatibility?.knowledge_graph?.note ?? 'n/a'}</div>
                      </div>
                    </div>
                    <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                      Advanced Controls is compatibility-only in HF2-R2. Duplicate legacy sub-tabs were removed from the primary admin navigation.
                    </div>
                  </div>
                )}
                {configData.groups.storage && (
                  <ConfigGroupPanel
                    groupKey="storage"
                    group={configData.groups.storage}
                    onSave={saveConfigParam}
                    onReset={handleResetConfigParam}
                    isSaving={isSaving}
                    accentColor={GROUP_COLORS.storage ?? 'amber'}
                  />
                )}
                <HistoryPanel history={history} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
