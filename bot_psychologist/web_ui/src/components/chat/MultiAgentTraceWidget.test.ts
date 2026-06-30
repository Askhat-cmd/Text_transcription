import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MultiAgentTraceData } from '../../types';
import { MultiAgentTraceWidget } from './MultiAgentTraceWidget';

function createTrace(): MultiAgentTraceData {
  return {
    session_id: 'session-12345678',
    turn_index: 2,
    pipeline_version: 'multiagent_v1',
    total_latency_ms: 1240,
    agents: {
      state_analyzer: {
        latency_ms: 310,
        nervous_state: 'calm',
        intent: 'support',
        safety_flag: false,
        confidence: 0.87,
      },
      thread_manager: {
        latency_ms: 45,
        thread_id: 'th-1',
        phase: 'exploring',
        relation_to_thread: 'continue',
        continuity_score: 0.72,
      },
      memory_retrieval: {
        latency_ms: 280,
        context_turns: 2,
        semantic_hits_count: 1,
        has_relevant_knowledge: true,
      },
      writer: {
        latency_ms: 580,
        response_mode: 'validate',
        tokens_used: 412,
        model_used: 'gpt-5-mini',
      },
      validator: {
        latency_ms: 25,
        is_blocked: false,
        block_reason: null,
        quality_flags: [],
      },
    },
    memory_context: {
      conversation_context: 'User: привет\nAssistant: привет!\n---',
      rag_query: 'привет поддержка',
      hybrid_retrieval: {
        planner_version: 'hybrid_retrieval_planner_v1_r1',
        planner_mode: 'shadow',
        planner_model: 'gpt-5-nano',
        planner_max_tokens: 320,
        retrieval_action: 'query_kb',
        planned_composed_query: 'паника контроль механизм',
        executed_rag_query: 'паника контроль механизм',
        legacy_rag_query: 'привет поддержка',
        query_before_rag_proof: true,
        needed_chunk_types: ['mechanism', 'concept'],
        mechanism_hints: ['panic_regulation'],
        depth_level_hint: 1,
        safety_layer_required: false,
        allowed_use_filter_hint: ['writer_support'],
        constraints_for_writer: ['no_theory'],
        retrieval_gap_reason: '',
        writer_can_ignore_rag: true,
        rag_skipped_reason: '',
        llm_called: false,
        llm_reason: 'universal_gate_resolved',
        fallback_used: false,
        universal_gate: 'clear_kb_ask',
        planner_status: 'valid',
        fallback_scope: 'none',
        production_query_source: 'current_turn_focus_v1',
        production_answer_affected: false,
      },
      semantic_hits: [
        {
          chunk_id: 'c1',
          source: 'lecture_1',
          score: 0.912,
          content_preview: 'safe_preview_mock',
          content_full: 'content_full_mock',
        },
      ],
      user_profile_patterns: ['pattern_1'],
      user_profile_values: ['value_1'],
      memory_written_preview: 'user: привет\nassistant: привет',
    },
    writer_llm: {
      system_prompt: 'SYSTEM PROMPT MOCK',
      user_prompt: 'USER PROMPT MOCK',
      llm_response_raw: 'LLM RESPONSE MOCK',
      model: 'gpt-5-mini',
      temperature: 0.7,
      max_tokens: 600,
      tokens_prompt: 300,
      tokens_completion: 112,
      tokens_total: 412,
      estimated_cost_usd: 0.000149,
    },
    turn_diff: {
      nervous_state_prev: 'curious',
      nervous_state_curr: 'calm',
      phase_prev: 'exploring',
      phase_curr: 'deepening',
      relation_to_thread: 'continue',
      memory_turns_delta: 1,
      semantic_hits_delta: 1,
    },
    anomalies: [
      {
        code: 'SLOW_WRITER',
        severity: 'WARN',
        message: 'Writer занял 580ms',
      },
    ],
    session_dashboard: {
      total_turns: 5,
      avg_latency_ms: 1100,
      total_cost_usd: 0.005,
      state_trajectory: ['calm', 'curious', 'confused'],
      thread_switches: 0,
      safety_events: 0,
      validator_blocks: 0,
    },
    hybrid_retrieval_plan: {
      retrieval_action: 'query_kb',
      needed_chunk_types: ['mechanism', 'concept'],
      mechanism_hints: ['panic_regulation'],
      constraints_for_writer: ['no_theory'],
    },
    hybrid_retrieval_planner_version: 'hybrid_retrieval_planner_v1_r1',
    hybrid_retrieval_planner_mode: 'shadow',
    hybrid_retrieval_plan_valid: true,
    hybrid_retrieval_plan_error: null,
    hybrid_retrieval_universal_gate: 'clear_kb_ask',
    hybrid_retrieval_llm_called: false,
    hybrid_retrieval_llm_reason: 'universal_gate_resolved',
    hybrid_retrieval_fallback_used: false,
    hybrid_retrieval_planner_status: 'valid',
    hybrid_retrieval_fallback_scope: 'none',
    hybrid_retrieval_owner_severity: 'info',
    hybrid_retrieval_production_query_source: 'current_turn_focus_v1',
    hybrid_retrieval_production_answer_affected: false,
    planned_composed_query: 'паника контроль механизм',
    executed_rag_query: 'паника контроль механизм',
    legacy_rag_query: 'привет поддержка',
    query_before_rag_proof: true,
    retrieval_action: 'query_kb',
    rag_skipped_reason: '',
    needed_chunk_types: ['mechanism', 'concept'],
    mechanism_hints: ['panic_regulation'],
    retrieval_gap_reason: '',
    writer_can_ignore_rag: true,
    depth_level_hint: 1,
    safety_layer_required: false,
    allowed_use_filter_hint: ['writer_support'],
    constraints_for_writer: ['no_theory'],
    planner_model: 'gpt-5-nano',
    planner_max_tokens: 320,
    overlay_shadow: {
      schema_version: 'overlay_shadow_trace_v1',
      enabled: true,
      status: 'ok',
      mode: 'trace_only',
      overlay_source_prd: 'PRD-047.20',
      batch_id: 'batch_1',
      overlay_item_count: 12,
      used_for_writer: false,
      used_for_retrieval_execution: false,
      would_help: true,
      match_count: 1,
      warnings: ['non_live_overlay_source'],
      safety_flags: ['trace_only'],
      matched_candidates: [
        {
          candidate_id: 'cand-1',
          chunk_type: 'mechanism',
          score: 4.25,
          matched_terms: ['контроль', 'страх'],
          focus_tags: ['control_as_safety'],
          safe_user_translation_preview: 'Избегание может быть попыткой защиты.',
          allowed_writer_use_preview: 'Только как мягкая гипотеза.',
        },
      ],
    },
    runtime_config_trace: {
      schema_version: 'runtime_config_trace_v1',
      app_env: 'local',
      backend_pid: 4242,
      backend_start_time: '2026-06-17T10:00:00+00:00',
      semantic_cards_pilot_enabled: true,
      semantic_cards_pilot_enabled_source: 'env',
      semantic_cards_pilot_raw_value: 'true',
      semantic_cards_pack_id: 'semantic_cards_pilot_v1',
      semantic_cards_loaded_count: 12,
      writer_kb_payload_enabled: true,
      writer_kb_payload_enabled_source: 'default_local',
      overlay_shadow_trace_enabled: false,
      debug_trace_enabled: true,
    },
    retrieval_query_build_trace: {
      schema_version: 'retrieval_query_build_trace_v1',
      enabled: true,
      primary_path: 'current_turn_focus_v1',
      raw_user_query: 'а что такое программа несовершенное я?',
      planned_query: 'программа несовершенное',
      canonical_query: 'программа несовершенное я',
      executed_query: 'программа несовершенное я',
      current_turn_focus_status: 'clean',
      planner_query_used: true,
      previous_user_query_included: false,
      previous_user_query_inclusion_reason: 'standalone_current_knowledge_question',
      inherited_topic_used: false,
      inherited_topic_reason: 'none',
      inherited_topic: '',
      dedupe_applied: false,
      duplicate_fragment_count: 0,
      truncation_applied: false,
      truncation_strategy: 'none',
      query_truncated_mid_word: false,
      fallback_reason: '',
    },
    writer_kb_payload_trace: {
      schema_version: 'writer_kb_payload_trace_v1',
      enabled: true,
      configured_enabled: true,
      configured_source: 'default_local',
      status: 'structured_payload_used',
      primary_path: 'writer_kb_payload_v1',
      payload_version: 'writer_kb_payload_v1',
      input_rag_for_writer_count: 1,
      payload_chunk_count: 1,
      total_original_char_count: 2480,
      total_sent_char_count: 1260,
      payload_sent_to_writer_char_count: 1260,
      payload_display_preview_char_count: 500,
      payload_display_is_preview: true,
      payload_full_text_sent_to_writer: true,
      payload_full_text_exposed_in_web_trace: false,
      truncated_chunk_count: 1,
      mid_sentence_cut_count: 0,
      overlay_metadata_used_count: 0,
      fallback_reason: '',
      fallback_is_primary: false,
      warning: '',
      chunk_summaries: [
        {
          chunk_id: 'semantic_card:program_imperfect_self_v1',
          source_doc: 'semantic_cards_pilot_v1',
          chunk_type: 'concept',
          quote_policy: 'paraphrase_only',
          allowed_use: ['direct_to_writer'],
          payload_item_origin: 'semantic_card',
          semantic_card_id: 'program_imperfect_self_v1',
          semantic_card_pack_id: 'semantic_cards_pilot_v1',
          sent_to_writer: true,
          inclusion_reason: 'selected_for_writer_payload',
          writer_can_ignore: true,
          applied_as_authority: false,
        },
      ],
      warnings: [],
      blockers: [],
    },
    runtime_truth_trace_v1: {
      trace_version: 'runtime_truth_trace_v1',
      current_user_message: 'привет',
      dialogue_act: 'support_request',
      answer_obligation: 'answer_concrete_situation',
      latest_must_answer: 'привет',
      retrieval_query_source: 'current_turn_focus_v1',
      retrieved_candidates_count: 2,
      trace_only_candidates_count: 1,
      filtered_out_for_writer_count: 1,
      writer_visible_payload_count: 1,
      actual_writer_payload_count: 1,
      writer_visible_payload_ids: ['semantic_card:program_imperfect_self_v1'],
      writer_visible_payload_types: ['concept'],
      payload_decision_reason: 'structured_payload_used',
      grounding_visibility_reason: 'direct_knowledge_question',
      legacy_fallback_scope: 'none',
      planner_shadow_status: 'valid',
      planner_fallback_scope: 'none',
      production_query_source: 'current_turn_focus_v1',
      json_decode_error_affected_production_answer: false,
      production_answer_affected_by_shadow_planner: false,
      writer_can_ignore_grounding: true,
      broad_kb_visible: true,
      narrow_grounding_visible: false,
      source_chunk_match_trace_v1: {
        enabled: true,
        explicit_knowledge_question: true,
        source_match_expected: 'yes',
        focus_terms: ['программа', 'несовершенное'],
        raw_source_top_k_count: 3,
        runtime_candidate_top_k_count: 2,
        writer_payload_count: 1,
        loss_stage: 'none',
        loss_reason: '',
        best_raw_match: {
          chunk_id: 'semantic_card:program_imperfect_self_v1',
          source_doc: 'semantic_cards_pilot_v1',
          rank: 1,
          score: 0.91,
          near_exact_match: true,
          matched_terms_or_phrase: ['программа', 'несовершенное'],
          sent_to_writer: true,
          filter_reason: '',
          payload_position: 1,
        },
        best_runtime_match: {
          chunk_id: 'semantic_card:program_imperfect_self_v1',
          source_doc: 'semantic_cards_pilot_v1',
          rank: 1,
          score: 0.91,
          near_exact_match: true,
          matched_terms_or_phrase: ['программа', 'несовершенное'],
          sent_to_writer: true,
          filter_reason: '',
          payload_position: 1,
        },
        payload_match: {
          chunk_id: 'semantic_card:program_imperfect_self_v1',
          source_doc: 'semantic_cards_pilot_v1',
          rank: 1,
          score: 0.91,
          near_exact_match: true,
          matched_terms_or_phrase: ['программа', 'несовершенное'],
          sent_to_writer: true,
          filter_reason: '',
          payload_position: 1,
        },
      },
      filtered_out_for_writer: [
        {
          item_id: 'trace-only-hit',
          origin: 'memory_semantic_hit',
          chunk_type: 'concept',
          source_doc: 'lecture_1',
          sent_to_writer: false,
          filter_reason: 'not_selected_for_writer',
        },
      ],
    },
    semantic_cards_pilot: {
      schema_version: 'semantic_cards_pilot_trace_v1',
      enabled: true,
      enabled_requested: true,
      enabled_source: 'env',
      runtime_mode: 'local',
      pack_id: 'semantic_cards_pilot_v1',
      loaded_card_count: 12,
      adapter_enabled: true,
      writer_payload_enabled: true,
      authority: 'advisory_only',
      selected_card_count: 1,
      selected_card_ids: ['program_imperfect_self_v1'],
      selection_reason: 'title/core_thesis/current_turn_overlap',
      writer_can_ignore: true,
      applied_as_authority: false,
      suppressed_reason: '',
      writer_payload_enriched: true,
      status: 'selected',
      error: '',
      candidate_scores: [
        {
          card_id: 'program_imperfect_self_v1',
          score: 4,
          reasons: ['current_turn_overlap', 'topic_alias'],
        },
      ],
    },
    future_graduation_notes: {
      schema_version: 'writer_kb_payload_future_graduation_notes_v1',
      payload_source: 'legacy_selected_hit',
      structured_payload_used: true,
      legacy_semantic_hits_used: false,
      truncation_strategy: 'paragraph_then_sentence_boundary',
    },
  };
}

function renderWidget(element: React.ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root: Root = createRoot(container);
  act(() => {
    root.render(element);
  });
  return {
    container,
    root,
    cleanup() {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function rerenderWidget(root: Root, element: React.ReactElement): void {
  act(() => {
    root.render(element);
  });
}

function clickButtonContains(container: HTMLElement, text: string): void {
  const target = Array.from(container.querySelectorAll('button')).find((btn) =>
    (btn.textContent || '').includes(text)
  );
  expect(target).toBeTruthy();
  act(() => {
    target?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

describe('MultiAgentTraceWidget (rev2)', () => {
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });

  it('renders collapsed header by default', () => {
    const harness = renderWidget(React.createElement(MultiAgentTraceWidget, { trace: createTrace() }));
    expect(harness.container.textContent).toContain('Pipeline NEO');
    expect(harness.container.textContent).toContain('1240ms');
    expect(harness.container.textContent).not.toContain('Мультиагентный пайплайн');
    harness.cleanup();
  });

  it('renders LLM canvas block in expanded mode', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Полотно LLM');
    clickButtonContains(harness.container, 'Полотно LLM');
    clickButtonContains(harness.container, 'System prompt');
    expect(harness.container.textContent).toContain('SYSTEM PROMPT MOCK');
    harness.cleanup();
  });

  it('renders writer kb payload runtime parity fields', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    clickButtonContains(harness.container, 'Writer KB Payload');
    clickButtonContains(harness.container, 'Effective runtime config');
    expect(harness.container.textContent).toContain('writer_kb_payload_v1');
    expect(harness.container.textContent).toContain('default_local');
    expect(harness.container.textContent).toContain('4242');
    expect(harness.container.textContent).toContain('semantic_cards_pilot_v1');
    expect(harness.container.textContent).toContain('12');
    expect(harness.container.textContent).toContain('500');
    harness.cleanup();
  });

  it('renders runtime truth trace with writer-visible payload proof', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    clickButtonContains(harness.container, 'Runtime Truth Trace');
    clickButtonContains(harness.container, 'Writer-visible payload proof');
    expect(harness.container.textContent).toContain('runtime_truth_trace_v1');
    expect(harness.container.textContent).toContain('WRITER PAYLOAD');
    expect(harness.container.textContent).toContain('semantic_card:program_imperfect_self_v1');
    expect(harness.container.textContent).toContain('JSON ERROR AFFECTED PROD');
    harness.cleanup();
  });

  it('renders source chunk match proof when available', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    clickButtonContains(harness.container, 'Runtime Truth Trace');
    clickButtonContains(harness.container, 'Source chunk match proof');
    expect(harness.container.textContent).toContain('semantic_card:program_imperfect_self_v1');
    expect(harness.container.textContent).toContain('loss_stage:');
    harness.cleanup();
  });

  it('expands chunk card and shows safe preview content', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );

    clickButtonContains(harness.container, 'Контекст памяти');
    clickButtonContains(harness.container, 'Retrieval candidates / trace-only');
    clickButtonContains(harness.container, 'score:');

    expect(harness.container.textContent).toContain('Diagnostic candidate list only');
    expect(harness.container.textContent).toContain('safe_preview_mock');
    harness.cleanup();
  });

  it('falls back to content_full when preview is empty', () => {
    const trace = createTrace();
    const hits = trace.memory_context?.semantic_hits;
    expect(Array.isArray(hits) && hits.length > 0).toBe(true);
    if (!hits || hits.length === 0) {
      throw new Error('semantic hits missing in trace fixture');
    }
    hits[0].content_preview = '';
    hits[0].content_full = 'content_full_fallback';
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace,
        isExpanded: true,
      })
    );

    clickButtonContains(harness.container, 'Контекст памяти');
    clickButtonContains(harness.container, 'Retrieval candidates / trace-only');
    clickButtonContains(harness.container, 'score:');

    expect(harness.container.textContent).toContain('content_full_fallback');
    harness.cleanup();
  });

  it('copies llm canvas to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    clickButtonContains(harness.container, 'Полотно LLM');
    const copyButton = Array.from(harness.container.querySelectorAll('button')).find((btn) =>
      (btn.textContent || '').includes('Скопировать всё полотно')
    );
    expect(copyButton).toBeTruthy();
    await act(async () => {
      copyButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText.mock.calls[0][0]).toContain('SYSTEM PROMPT MOCK');
    harness.cleanup();
  });

  it('renders session dashboard trajectory and anomalies', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Session Dashboard');
    clickButtonContains(harness.container, 'Session Dashboard');
    clickButtonContains(harness.container, 'Аномалии');
    expect(harness.container.textContent).toContain('calm');
    expect(harness.container.textContent).toContain('SLOW_WRITER');
    harness.cleanup();
  });

  it('renders hybrid retrieval visibility block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Hybrid Retrieval');
    clickButtonContains(harness.container, 'Hybrid Retrieval');
    clickButtonContains(harness.container, 'Queries');
    clickButtonContains(harness.container, 'Planner metadata');
    expect(harness.container.textContent).toContain('gpt-5-nano');
    expect(harness.container.textContent).toContain('паника контроль механизм');
    expect(harness.container.textContent).toContain('panic_regulation');
    harness.cleanup();
  });

  it('renders overlay shadow trace block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Overlay Shadow');
    clickButtonContains(harness.container, 'Overlay Shadow');
    clickButtonContains(harness.container, 'Overlay summary');
    clickButtonContains(harness.container, 'Matched candidates');
    expect(harness.container.textContent).toContain('PRD-047.20');
    expect(harness.container.textContent).toContain('control_as_safety');
    expect(harness.container.textContent).toContain('non_live_overlay_source');
    harness.cleanup();
  });

  it('renders writer kb payload trace block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Writer KB Payload');
    clickButtonContains(harness.container, 'Writer KB Payload');
    clickButtonContains(harness.container, 'Payload warnings');
    clickButtonContains(harness.container, 'Payload chunks');
    clickButtonContains(harness.container, 'Future graduation notes');
    expect(harness.container.textContent).toContain('writer_kb_payload_trace_v1');
    expect(harness.container.textContent).toContain('semantic_card:program_imperfect_self_v1');
    expect(harness.container.textContent).toContain('payload_item_origin');
    expect(harness.container.textContent).toContain('paragraph_then_sentence_boundary');
    harness.cleanup();
  });

  it('renders semantic cards pilot trace block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Semantic Cards Pilot');
    clickButtonContains(harness.container, 'Semantic Cards Pilot');
    clickButtonContains(harness.container, 'Selection details');
    clickButtonContains(harness.container, 'Selected card ids');
    clickButtonContains(harness.container, 'Candidate scores');
    expect(harness.container.textContent).toContain('semantic_cards_pilot_v1');
    expect(harness.container.textContent).toContain('program_imperfect_self_v1');
    expect(harness.container.textContent).toContain('advisory_only');
    harness.cleanup();
  });

  it('renders retrieval query build trace block', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isExpanded: true,
      })
    );
    expect(harness.container.textContent).toContain('Retrieval Query Build');
    clickButtonContains(harness.container, 'Retrieval Query Build');
    clickButtonContains(harness.container, 'Query details');
    clickButtonContains(harness.container, 'Context reasons');
    expect(harness.container.textContent).toContain('current_turn_focus_v1');
    expect(harness.container.textContent).toContain('standalone_current_knowledge_question');
    harness.cleanup();
  });

  it('handles loading-to-trace transition without hook crash', () => {
    const harness = renderWidget(
      React.createElement(MultiAgentTraceWidget, {
        trace: null,
        isLoading: true,
      })
    );
    expect(harness.container.textContent).toContain('');

    rerenderWidget(
      harness.root,
      React.createElement(MultiAgentTraceWidget, {
        trace: createTrace(),
        isLoading: false,
      })
    );
    expect(harness.container.textContent).toContain('Pipeline NEO');
    harness.cleanup();
  });
});
