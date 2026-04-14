# bot_agent/answer_adaptive.py
"""
Adaptive Answer Module - Phase 4
================================

Р“Р»Р°РІРЅР°СЏ С„СѓРЅРєС†РёСЏ Phase 4: answer_question_adaptive.

Р Р°СЃС€РёСЂСЏРµС‚ Phase 3 РїРѕР»РЅРѕС†РµРЅРЅС‹Рј СЃРѕРїСЂРѕРІРѕР¶РґРµРЅРёРµРј РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ:
- РљР»Р°СЃСЃРёС„РёРєР°С†РёСЏ СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (10 СЃРѕСЃС‚РѕСЏРЅРёР№)
- Р”РѕР»РіРѕСЃСЂРѕС‡РЅР°СЏ РїР°РјСЏС‚СЊ РґРёР°Р»РѕРіР°
- РџРѕСЃС‚СЂРѕРµРЅРёРµ РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹С… РїСѓС‚РµР№ С‚СЂР°РЅСЃС„РѕСЂРјР°С†РёРё
- РђРґР°РїС‚РёРІРЅС‹Рµ СЂРµРєРѕРјРµРЅРґР°С†РёРё РїРѕ СЃРѕСЃС‚РѕСЏРЅРёСЋ
- Р—Р°РїСЂРѕСЃ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
"""

import asyncio
import logging
import json
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime

from .data_loader import Block, data_loader
from .retriever import get_retriever
from .user_level_types import UserLevel
from .semantic_analyzer import SemanticAnalyzer
from .graph_client import graph_client
from .state_classifier import state_classifier, StateAnalysis, UserState
from .conversation_memory import get_conversation_memory
from .working_state import WorkingState
from .path_builder import path_builder
from .config import config
from .decision import (
    DecisionGate,
    build_mode_directive,
    detect_routing_signals,
    resolve_user_stage,
)
from .retrieval import ConfidenceScorer, HybridQueryBuilder, VoyageReranker
from .reranker_gate import should_rerank
from .response import ResponseFormatter, ResponseGenerator
from .feature_flags import feature_flags
from .contradiction_detector import detect_contradiction
from .progressive_rag import get_progressive_rag
from .diagnostics_classifier import diagnostics_classifier
from .route_resolver import route_resolver
from .memory_updater import memory_updater
from .prompt_registry_v2 import prompt_registry_v2
from .output_validator import output_validator
from .practice_selector import practice_selector
from .trace_schema import attach_trace_schema_status
from .onboarding_flow import (
    detect_phase8_signals,
    build_first_turn_instruction,
    build_mixed_query_instruction,
    build_user_correction_instruction,
    build_informational_guardrail_instruction,
)
from .adaptive_runtime.pipeline_utils import (
    _timed,
    _build_config_snapshot,
    _compute_anomalies,
    _build_state_trajectory,
    _store_blob,
    _run_coroutine_sync,
)
from .adaptive_runtime.response_utils import (
    _get_feedback_prompt_for_state,
    _build_partial_response,
    _build_error_response,
    _build_success_response,
    _build_fast_success_metadata,
    _build_full_success_metadata,
    _build_path_recommendation_if_enabled as _runtime_build_path_recommendation_if_enabled,
    _persist_turn_best_effort,
    _persist_turn,
    _save_session_summary_best_effort,
    _build_sources_from_blocks,
    _attach_debug_payload,
    _attach_success_observability,
    _handle_no_retrieval_partial_response as _runtime_handle_no_retrieval_partial_response,
    _handle_llm_generation_error_response as _runtime_handle_llm_generation_error_response,
)
from .adaptive_runtime.trace_helpers import (
    _init_debug_payloads,
    _strip_legacy_runtime_metadata,
    _strip_legacy_trace_fields,
    _log_retrieval_pairs,
    _log_blocks,
    _truncate_preview,
    _extract_block_trace_fields,
    _build_chunk_trace_item,
    _build_chunk_trace_lists_after_rerank,
    _recent_user_turns,
    _build_retrieval_detail,
    _build_retrieval_debug_details,
    _collect_progressive_feedback_blocks,
    _build_voyage_rerank_debug_payload,
    _build_routing_debug_payload,
    _attach_retrieval_observability as _runtime_attach_retrieval_observability,
    _build_llm_prompts,
    _prepare_llm_prompt_previews,
    _build_llm_call_trace,
    _update_session_token_metrics,
    _apply_output_validation_observability as _runtime_apply_output_validation_observability,
    _refresh_context_and_apply_trace_snapshot as _runtime_refresh_context_and_apply_trace_snapshot,
    _apply_memory_debug_info,
    _finalize_success_debug_trace,
    _finalize_failure_debug_trace,
)
from .adaptive_runtime.state_helpers import (
    SDClassificationResult,
    _fallback_state_analysis as _runtime_fallback_state_analysis,
    _fallback_sd_result as _runtime_fallback_sd_result,
    _resolve_path_user_level as _runtime_resolve_path_user_level,
    _classify_parallel as _runtime_classify_parallel,
    _build_state_context as _runtime_build_state_context,
    _compose_state_context as _runtime_compose_state_context,
    _depth_to_phase as _runtime_depth_to_phase,
    _mode_to_direction as _runtime_mode_to_direction,
    _derive_defense as _runtime_derive_defense,
    _build_working_state as _runtime_build_working_state,
    _looks_like_greeting as _runtime_looks_like_greeting,
    _looks_like_name_intro as _runtime_looks_like_name_intro,
    _should_use_fast_path as _runtime_should_use_fast_path,
    _detect_fast_path_reason as _runtime_detect_fast_path_reason,
    _build_fast_path_block as _runtime_build_fast_path_block,
    _set_working_state_best_effort as _runtime_set_working_state_best_effort,
)
from .adaptive_runtime.mode_policy_helpers import (
    MODE_PROMPT_MAP as _RUNTIME_MODE_PROMPT_MAP,
    resolve_mode_prompt as _runtime_resolve_mode_prompt,
    _derive_informational_mode_hint as _runtime_derive_informational_mode_hint,
    _diagnostics_v1_enabled as _runtime_diagnostics_v1_enabled,
    _deterministic_route_resolver_enabled as _runtime_deterministic_route_resolver_enabled,
    _prompt_stack_v2_enabled as _runtime_prompt_stack_v2_enabled,
    _output_validation_enabled as _runtime_output_validation_enabled,
    _informational_branch_enabled as _runtime_informational_branch_enabled,
    _apply_output_validation_policy as _runtime_apply_output_validation_policy,
)
from .adaptive_runtime.routing_stage_helpers import (
    _compute_diagnostics_v1 as _runtime_compute_diagnostics_v1,
    _build_contradiction_payload as _runtime_build_contradiction_payload,
    _resolve_pre_routing as _runtime_resolve_pre_routing,
    _apply_fast_path_debug_bootstrap as _runtime_apply_fast_path_debug_bootstrap,
    _build_state_context_mode_prompt as _runtime_build_state_context_mode_prompt,
    _build_phase8_context_suffix as _runtime_build_phase8_context_suffix,
    _build_fast_path_mode_directive as _runtime_build_fast_path_mode_directive,
    _resolve_practice_selection_context as _runtime_resolve_practice_selection_context,
    _attach_routing_stage_debug_trace as _runtime_attach_routing_stage_debug_trace,
)
from .adaptive_runtime.runtime_misc_helpers import (
    _estimate_cost as _runtime_estimate_cost,
    _sd_runtime_disabled as _runtime_sd_runtime_disabled,
    _build_start_command_response as _runtime_build_start_command_response,
    _load_runtime_memory_context as _runtime_load_runtime_memory_context,
    _generate_llm_with_trace as _runtime_generate_llm_with_trace,
    _run_validation_retry_generation as _runtime_run_validation_retry_generation,
    _collect_llm_session_metrics as _runtime_collect_llm_session_metrics,
    _build_prompt_stack_override as _runtime_build_prompt_stack_override,
    _run_llm_generation_cycle as _runtime_run_llm_generation_cycle,
)
from .adaptive_runtime.retrieval_stage_helpers import (
    _retrieve_blocks_with_degraded_mode as _runtime_retrieve_blocks_with_degraded_mode,
    _dedupe_and_apply_progressive_rag as _runtime_dedupe_and_apply_progressive_rag,
    _prepare_conditional_rerank as _runtime_prepare_conditional_rerank,
)

logger = logging.getLogger(__name__)

PRACTICE_ALLOWED_ROUTES = {"practice", "reflect", "regulate"}
PRACTICE_SKIP_ROUTES = {"contact_hold", "contacthold", "presence", "crisis_hold"}

# Compatibility touchpoint for inventory tests/documentation.
MODE_PROMPT_MAP = _RUNTIME_MODE_PROMPT_MAP




def resolve_mode_prompt(user_state: str, cfg) -> Tuple[Optional[str], Optional[str]]:
    return _runtime_resolve_mode_prompt(user_state, cfg)


def _derive_informational_mode_hint(phase8_signals, query: str) -> bool:
    return _runtime_derive_informational_mode_hint(phase8_signals, query)


def _estimate_cost(llm_calls: List[Dict], model_name: str) -> float:
    return _runtime_estimate_cost(llm_calls, model_name)


def _detect_fast_path_reason(query: str, routing_result) -> str:
    return _runtime_detect_fast_path_reason(query, routing_result)


def _fallback_state_analysis() -> StateAnalysis:
    return _runtime_fallback_state_analysis()


def _fallback_sd_result(reason: str = "fallback_on_error") -> SDClassificationResult:
    return _runtime_fallback_sd_result(reason)


def _sd_runtime_disabled() -> bool:
    return _runtime_sd_runtime_disabled()


def _diagnostics_v1_enabled() -> bool:
    return _runtime_diagnostics_v1_enabled()


def _deterministic_route_resolver_enabled() -> bool:
    return _runtime_deterministic_route_resolver_enabled()


def _prompt_stack_v2_enabled() -> bool:
    return _runtime_prompt_stack_v2_enabled()


def _output_validation_enabled() -> bool:
    return _runtime_output_validation_enabled()


def _informational_branch_enabled() -> bool:
    return _runtime_informational_branch_enabled()




def _apply_output_validation_policy(
    *,
    answer: str,
    query: str = "",
    route: str,
    mode: str,
    generate_retry_fn=None,
) -> Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
    return _runtime_apply_output_validation_policy(
        answer=answer,
        query=query,
        route=route,
        mode=mode,
        validator=output_validator,
        force_enabled=_output_validation_enabled(),
        generate_retry_fn=generate_retry_fn,
    )


def _build_start_command_response(
    *,
    user_id: str,
    user_level: str,
    query: str,
    memory,
    start_time: datetime,
    schedule_summary_task: bool = True,
) -> Dict[str, Any]:
    return _runtime_build_start_command_response(
        user_id=user_id,
        user_level=user_level,
        query=query,
        memory=memory,
        start_time=start_time,
        schedule_summary_task=schedule_summary_task,
        logger=logger,
    )


def _generate_llm_with_trace(**kwargs):
    return _runtime_generate_llm_with_trace(**kwargs)


def _run_validation_retry_generation(**kwargs):
    return _runtime_run_validation_retry_generation(**kwargs)


def _collect_llm_session_metrics(**kwargs):
    return _runtime_collect_llm_session_metrics(**kwargs)


def _build_prompt_stack_override(**kwargs):
    return _runtime_build_prompt_stack_override(**kwargs)


def _run_llm_generation_cycle(**kwargs):
    return _runtime_run_llm_generation_cycle(**kwargs)


def _retrieve_blocks_with_degraded_mode(**kwargs):
    return _runtime_retrieve_blocks_with_degraded_mode(**kwargs)


def _dedupe_and_apply_progressive_rag(**kwargs):
    return _runtime_dedupe_and_apply_progressive_rag(**kwargs)


def _prepare_conditional_rerank(**kwargs):
    return _runtime_prepare_conditional_rerank(**kwargs)


def _resolve_practice_selection_context(**kwargs):
    return _runtime_resolve_practice_selection_context(**kwargs)


def _attach_routing_stage_debug_trace(**kwargs):
    return _runtime_attach_routing_stage_debug_trace(**kwargs)


def _build_path_recommendation_if_enabled(**kwargs):
    return _runtime_build_path_recommendation_if_enabled(**kwargs)


def _handle_no_retrieval_partial_response(**kwargs):
    return _runtime_handle_no_retrieval_partial_response(**kwargs)


def _handle_llm_generation_error_response(**kwargs):
    return _runtime_handle_llm_generation_error_response(**kwargs)


def _attach_retrieval_observability(**kwargs):
    return _runtime_attach_retrieval_observability(**kwargs)


def _compose_state_context(**kwargs):
    return _runtime_compose_state_context(**kwargs)


def _refresh_context_and_apply_trace_snapshot(**kwargs):
    return _runtime_refresh_context_and_apply_trace_snapshot(**kwargs)


def _apply_output_validation_observability(**kwargs):
    return _runtime_apply_output_validation_observability(**kwargs)


def _resolve_path_user_level(_user_level: str) -> UserLevel:
    return _runtime_resolve_path_user_level(_user_level)


async def _classify_parallel(
    user_message: str,
    history_state: List[Dict],
) -> Tuple[StateAnalysis, SDClassificationResult]:
    return await _runtime_classify_parallel(user_message, history_state)


def _build_state_context(
    state_analysis: StateAnalysis,
    mode_prompt: str,
    nervous_system_state: str = "window",
    request_function: str = "understand",
    contradiction_suggestion: str = "",
    cross_session_context: str = "",
) -> str:
    return _runtime_build_state_context(
        state_analysis=state_analysis,
        mode_prompt=mode_prompt,
        nervous_system_state=nervous_system_state,
        request_function=request_function,
        contradiction_suggestion=contradiction_suggestion,
        cross_session_context=cross_session_context,
    )


def _depth_to_phase(depth: str) -> str:
    return _runtime_depth_to_phase(depth)


def _mode_to_direction(mode: str) -> str:
    return _runtime_mode_to_direction(mode)


def _derive_defense(state_value: str) -> Optional[str]:
    return _runtime_derive_defense(state_value)


def _build_working_state(
    *,
    state_analysis: StateAnalysis,
    routing_result,
    memory,
) -> WorkingState:
    return _runtime_build_working_state(
        state_analysis=state_analysis,
        routing_result=routing_result,
        memory=memory,
    )


def _set_working_state_best_effort(
    *,
    memory,
    state_analysis: StateAnalysis,
    routing_result,
    log_prefix: str,
) -> None:
    return _runtime_set_working_state_best_effort(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=routing_result,
        build_working_state_fn=_build_working_state,
        logger=logger,
        log_prefix=log_prefix,
    )


def _looks_like_greeting(query: str) -> bool:
    return _runtime_looks_like_greeting(query)

def _looks_like_name_intro(query: str) -> bool:
    return _runtime_looks_like_name_intro(query)

def _should_use_fast_path(query: str, routing_result) -> bool:
    return _runtime_should_use_fast_path(query, routing_result)

def _build_fast_path_block(
    *,
    query: str,
    conversation_context: str,
    state_analysis: StateAnalysis,
) -> Block:
    return _runtime_build_fast_path_block(
        query=query,
        conversation_context=conversation_context,
        state_analysis=state_analysis,
    )

def answer_question_adaptive(
    query: str,
    user_id: str = "default",
    user_level: str = "beginner",
    include_path_recommendation: bool = False,
    include_feedback_prompt: bool = True,
    top_k: Optional[int] = None,
    debug: bool = False,
    session_store=None,
    schedule_summary_task: bool = True,
) -> Dict:
    """
    Phase 4: РђРґР°РїС‚РёРІРЅС‹Р№ QA СЃ СѓС‡РµС‚РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ Рё РёСЃС‚РѕСЂРёРё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
    
    Р­С‚Р°РїС‹ РѕР±СЂР°Р±РѕС‚РєРё:
        1. Р—Р°РіСЂСѓР·РєР° РґР°РЅРЅС‹С… Рё РїР°РјСЏС‚Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        2. РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        3. РџРѕРёСЃРє СЂРµР»РµРІР°РЅС‚РЅС‹С… Р±Р»РѕРєРѕРІ
        4. Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р° СЃ РєРѕРЅС‚РµРєСЃС‚РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ
        5. РџРѕСЃС‚СЂРѕРµРЅРёРµ СЂРµРєРѕРјРµРЅРґР°С†РёРё РїСѓС‚Рё
        6. РџРѕРґРіРѕС‚РѕРІРєР° Р·Р°РїСЂРѕСЃР° РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
        7. РЎРѕС…СЂР°РЅРµРЅРёРµ РІ РїР°РјСЏС‚СЊ
    
    Args:
        query: Р’РѕРїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        user_id: ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (РґР»СЏ РїР°РјСЏС‚Рё)
        user_level: РЈСЂРѕРІРµРЅСЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (beginner/intermediate/advanced)
        include_path_recommendation: Р’РєР»СЋС‡Р°С‚СЊ Р»Рё СЂРµРєРѕРјРµРЅРґР°С†РёСЋ РїСѓС‚Рё
        include_feedback_prompt: Р—Р°РїСЂР°С€РёРІР°С‚СЊ Р»Рё РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ
        top_k: РљРѕР»РёС‡РµСЃС‚РІРѕ Р±Р»РѕРєРѕРІ РґР»СЏ РїРѕРёСЃРєР°
        debug: РћС‚Р»Р°РґРѕС‡РЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ
    
    Returns:
        Dict СЃ СЂР°СЃС€РёСЂРµРЅРЅС‹РјРё РїРѕР»СЏРјРё Phase 4:
            - status: "success" | "error" | "partial"
            - answer: str вЂ” РѕС‚РІРµС‚
            - state_analysis: Dict вЂ” Р°РЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ
            - path_recommendation: Optional[Dict] вЂ” СЂРµРєРѕРјРµРЅРґСѓРµРјС‹Р№ РїСѓС‚СЊ
            - conversation_context: str вЂ” РєРѕРЅС‚РµРєСЃС‚ РёСЃС‚РѕСЂРёРё
            - feedback_prompt: str вЂ” Р·Р°РїСЂРѕСЃ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
            - sources: List[Dict]
            - concepts: List[str]
            - metadata: Dict
            - timestamp: str
            - processing_time_seconds: float
            - debug: Optional[Dict]
    """
    
    logger.info(f"[ADAPTIVE] new request user_id={user_id} query='{query[:50]}...'")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    pipeline_stages: List[Dict] = []
    debug_info, debug_trace = _init_debug_payloads(
        debug=debug,
        user_id=user_id,
        pipeline_stages=pipeline_stages,
        config_snapshot=_build_config_snapshot(config),
    )
    conversation_context = ""
    memory_context_bundle = None
    phase8_signals = None
    level_adapter = None  # legacy compatibility marker: level-based prompting is disabled
    
    current_stage = "init"
    try:
        # ================================================================
        # Р­РўРђРџ 1: Р—Р°РіСЂСѓР·РєР° РґР°РЅРЅС‹С… Рё РїР°РјСЏС‚Рё
        # ================================================================
        logger.debug("рџ“љ Р­С‚Р°Рї 1: Р—Р°РіСЂСѓР·РєР° РґР°РЅРЅС‹С… Рё РїР°РјСЏС‚Рё...")
        
        stage1 = _runtime_load_runtime_memory_context(
            user_id=user_id,
            query=query,
            data_loader=data_loader,
            get_conversation_memory_fn=get_conversation_memory,
            memory_updater=memory_updater,
            config=config,
        )
        memory = stage1["memory"]
        memory_context_bundle = stage1["memory_context_bundle"]
        conversation_context = stage1["conversation_context"]
        cross_session_context = stage1["cross_session_context"]
        context_turns = stage1["context_turns"]
        memory_trace_metrics = stage1["memory_trace_metrics"]
        if memory_context_bundle is not None:
            memory_trace_metrics["summary_staleness"] = memory_context_bundle.staleness
            memory_trace_metrics["memory_strategy"] = memory_context_bundle.strategy
        if debug_trace is not None:
            debug_trace["turn_number"] = len(memory.turns) + 1
            debug_trace["cross_session_context"] = _truncate_preview(cross_session_context, 500)
            debug_trace["memory_strategy"] = memory_context_bundle.strategy if memory_context_bundle else None
            debug_trace["summary_staleness"] = (
                memory_context_bundle.staleness if memory_context_bundle else None
            )
            _apply_memory_debug_info(debug_trace, memory, memory_trace_metrics)

        phase8_signals = detect_phase8_signals(query=query, turns_count=len(memory.turns))
        if debug_trace is not None:
            debug_trace["phase8_signals"] = phase8_signals.as_dict()
        if _informational_branch_enabled() and phase8_signals.start_command:
            return _build_start_command_response(
                user_id=user_id,
                user_level=user_level,
                query=query,
                memory=memory,
                start_time=start_time,
                schedule_summary_task=schedule_summary_task,
            )
        
        # Phase 3: user level adapter removed from active runtime.
        _ = level_adapter
        path_level_enum = _resolve_path_user_level(user_level)
        
        if debug_info is not None:
            debug_info["user_id"] = user_id
            debug_info["memory_turns"] = len(memory.turns)
        
        # ================================================================
        # Р­РўРђРџ 2: РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        # ================================================================
        logger.debug("рџЋЇ Р­С‚Р°Рї 2: РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ...")
        
        # РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґР»СЏ РєРѕРЅС‚РµРєСЃС‚Р° Р°РЅР°Р»РёР·Р°
        conversation_history = [
            {"role": "user", "content": turn.user_input}
            for turn in memory.get_last_turns(config.CONVERSATION_HISTORY_DEPTH)
        ]
        
        if debug_trace is not None:
            current_stage = "state_classifier"
            try:
                state_analysis, stage = _timed(
                    "state_classifier",
                    "РљР»Р°СЃСЃРёС„РёРєР°С‚РѕСЂ СЃРѕСЃС‚РѕСЏРЅРёСЏ",
                    _run_coroutine_sync,
                    state_classifier.classify(
                        query,
                        conversation_history=conversation_history,
                    ),
                )
                pipeline_stages.append(stage)
            except Exception as exc:
                logger.warning(
                    "[CLASSIFY] StateClassifier failed: %s. Using fallback.",
                    exc,
                )
                state_analysis = _fallback_state_analysis()
                pipeline_stages.append(
                    {
                        "name": "state_classifier",
                        "label": "РљР»Р°СЃСЃРёС„РёРєР°С‚РѕСЂ СЃРѕСЃС‚РѕСЏРЅРёСЏ",
                        "duration_ms": 0,
                        "skipped": False,
                    }
                )
            sd_result = _fallback_sd_result("disabled_by_design")
        else:
            state_analysis, sd_result = _run_coroutine_sync(
                _classify_parallel(
                    query,
                    conversation_history,
                )
            )
        user_stage = resolve_user_stage(memory, state_analysis)
        informational_mode_hint = _derive_informational_mode_hint(phase8_signals, query)
        informational_mode = informational_mode_hint
        mode_prompt_key, mode_prompt_override = resolve_mode_prompt(
            "informational" if informational_mode else "",
            config,
        )

        logger.info("STATE ANALYSIS ready conf=%.2f", float(state_analysis.confidence))

        if debug_info is not None:
            debug_info["state_analysis"] = {
                "primary": state_analysis.primary_state.value,
                "confidence": state_analysis.confidence,
                "secondary": [s.value for s in state_analysis.secondary_states],
                "emotional_tone": state_analysis.emotional_tone,
                "depth": state_analysis.depth,
                "user_stage": user_stage,
            }

        if debug_trace is not None:
            debug_trace["state_secondary"] = [s.value for s in state_analysis.secondary_states]
            debug_trace["user_state"] = state_analysis.primary_state.value
            debug_trace["informational_mode_hint"] = informational_mode_hint
            debug_trace["informational_mode"] = informational_mode
            debug_trace["applied_mode_prompt"] = mode_prompt_key if informational_mode else None

        use_new_diagnostics_v1 = _diagnostics_v1_enabled()
        use_deterministic_router = (
            _deterministic_route_resolver_enabled() and use_new_diagnostics_v1
        )
        confidence_scorer = ConfidenceScorer()
        route_resolution_count = 0

        diagnostics_v1, correction_protocol_active = _runtime_compute_diagnostics_v1(
            query=query,
            state_analysis=state_analysis,
            informational_mode_hint=informational_mode_hint,
            phase8_signals=phase8_signals,
            informational_branch_enabled=_informational_branch_enabled(),
            use_new_diagnostics_v1=use_new_diagnostics_v1,
            use_deterministic_router=use_deterministic_router,
            diagnostics_classifier=diagnostics_classifier,
            debug_trace=debug_trace,
            debug_info=debug_info,
        )

        contradiction_info, contradiction_hint = _runtime_build_contradiction_payload(
            query=query,
            detect_contradiction_fn=detect_contradiction,
            debug_trace=debug_trace,
        )

        decision_gate, pre_routing_result, fast_path_enabled = _runtime_resolve_pre_routing(
            use_deterministic_router=use_deterministic_router,
            query=query,
            state_analysis=state_analysis,
            memory=memory,
            user_stage=user_stage,
            informational_mode=informational_mode,
            contradiction_info=contradiction_info,
            contradiction_hint=contradiction_hint,
            decision_gate_cls=DecisionGate,
            detect_routing_signals_fn=detect_routing_signals,
            should_use_fast_path_fn=_should_use_fast_path,
            logger=logger,
        )

        if fast_path_enabled:
            logger.info(
                "[FAST_PATH] enabled mode=%s reason=%s",
                pre_routing_result.mode,
                pre_routing_result.decision.reason,
            )
            _runtime_apply_fast_path_debug_bootstrap(
                debug_trace=debug_trace,
                query=query,
                pre_routing_result=pre_routing_result,
                detect_fast_path_reason_fn=_detect_fast_path_reason,
                truncate_preview_fn=_truncate_preview,
                config=config,
                pipeline_stages=pipeline_stages,
            )
            mode_directive, state_context_mode_prompt = _runtime_build_fast_path_mode_directive(
                pre_routing_result=pre_routing_result,
                informational_mode=informational_mode,
                build_mode_directive_fn=build_mode_directive,
            )
            conversation_context = _refresh_context_and_apply_trace_snapshot(
                memory=memory,
                conversation_context=conversation_context,
                memory_context_bundle=memory_context_bundle,
                debug_trace=debug_trace,
                diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
                route=(
                    getattr(pre_routing_result, "route", None)
                    if pre_routing_result
                    else None
                ),
            )
            fast_block = _build_fast_path_block(
                query=query,
                conversation_context=conversation_context,
                state_analysis=state_analysis,
            )
            state_context = _build_state_context(
                state_analysis,
                state_context_mode_prompt,
                nervous_system_state=(
                    diagnostics_v1.nervous_system_state if diagnostics_v1 else "window"
                ),
                request_function=(
                    diagnostics_v1.request_function if diagnostics_v1 else "understand"
                ),
                contradiction_suggestion=contradiction_hint,
                cross_session_context=cross_session_context,
            )
            fast_phase8_suffix = _runtime_build_phase8_context_suffix(
                informational_branch_enabled=_informational_branch_enabled(),
                phase8_signals=phase8_signals,
                correction_protocol_active=correction_protocol_active,
                informational_mode=informational_mode,
                build_first_turn_instruction_fn=build_first_turn_instruction,
                build_mixed_query_instruction_fn=build_mixed_query_instruction,
                build_user_correction_instruction_fn=build_user_correction_instruction,
                build_informational_guardrail_instruction_fn=build_informational_guardrail_instruction,
            )
            if fast_phase8_suffix:
                state_context = f"{state_context}\n\n{fast_phase8_suffix}"
            current_stage = "llm"
            llm_result, response_generator, _, system_prompt_override = _run_llm_generation_cycle(
                response_generator_cls=ResponseGenerator,
                query=query,
                blocks=[fast_block],
                conversation_context=conversation_context,
                mode=pre_routing_result.mode,
                confidence_level=pre_routing_result.confidence_level,
                forbid=pre_routing_result.decision.forbid,
                additional_system_context=state_context,
                sd_level=sd_result.primary,
                config=config,
                session_store=session_store,
                session_id=user_id,
                mode_prompt_override=mode_prompt_override,
                informational_mode=informational_mode,
                route=getattr(pre_routing_result, "route", "") if pre_routing_result else "",
                diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
                phase8_signals=phase8_signals,
                correction_protocol_active=correction_protocol_active,
                prompt_stack_enabled=_prompt_stack_v2_enabled(),
                prompt_registry=prompt_registry_v2,
                mode_prompt=mode_directive.prompt,
                debug_trace=debug_trace,
                pipeline_stages=pipeline_stages,
                build_prompt_stack_override_fn=_build_prompt_stack_override,
                prepare_llm_prompt_previews_fn=_prepare_llm_prompt_previews,
                generate_llm_with_trace_fn=_generate_llm_with_trace,
                build_llm_call_trace_fn=_build_llm_call_trace,
            )
            answer = llm_result.get("answer", "")
            formatter = ResponseFormatter()
            answer = formatter.format_answer(
                answer,
                mode=pre_routing_result.mode,
                confidence_level=pre_routing_result.confidence_level,
                user_message=query,
                informational_mode=informational_mode,
            )

            def _retry_fast_validation(hint: str) -> Dict[str, Any]:
                return _run_validation_retry_generation(
                    response_generator=response_generator,
                    query=query,
                    hint=hint,
                    blocks=[fast_block],
                    conversation_context=conversation_context,
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    forbid=pre_routing_result.decision.forbid,
                    additional_system_context=state_context,
                    sd_level=sd_result.primary,
                    config=config,
                    session_store=session_store,
                    session_id=user_id,
                    mode_prompt_override=mode_prompt_override,
                    informational_mode=informational_mode,
                    system_prompt_override=system_prompt_override,
                    format_answer_fn=lambda raw_answer: formatter.format_answer(
                        raw_answer,
                        mode=pre_routing_result.mode,
                        confidence_level=pre_routing_result.confidence_level,
                        user_message=query,
                        informational_mode=informational_mode,
                    ),
                )

            answer, validation_meta, validation_retry_result = _apply_output_validation_policy(
                answer=answer,
                query=query,
                route=getattr(pre_routing_result, "route", ""),
                mode=pre_routing_result.mode,
                generate_retry_fn=_retry_fast_validation,
            )
            _apply_output_validation_observability(
                validation_meta=validation_meta,
                validation_retry_result=validation_retry_result,
                llm_result=llm_result,
                debug_trace=debug_trace,
                pipeline_stages=pipeline_stages,
                fallback_model_name=str(config.LLM_MODEL),
                include_retry_llm_trace=False,
            )

            _set_working_state_best_effort(
                memory=memory,
                state_analysis=state_analysis,
                routing_result=pre_routing_result,
                log_prefix="[FAST_PATH] working_state update failed:",
            )

            llm_metrics = _collect_llm_session_metrics(
                memory=memory,
                llm_result=llm_result if isinstance(llm_result, dict) else {},
                fallback_model_name=config.LLM_MODEL,
                update_session_token_metrics_fn=_update_session_token_metrics,
            )
            tokens_prompt = llm_metrics["tokens_prompt"]
            tokens_completion = llm_metrics["tokens_completion"]
            tokens_total = llm_metrics["tokens_total"]
            model_used = llm_metrics["model_used"]
            session_metrics = llm_metrics["session_metrics"]

            _persist_turn(
                memory=memory,
                user_input=query,
                bot_response=answer,
                user_state=state_analysis.primary_state.value,
                blocks_used=0,
                concepts=[],
                schedule_summary_task=schedule_summary_task,
            )

            memory_turns = len(memory.turns)
            summary_length = len(memory.summary) if memory.summary else 0
            summary_last_turn = memory.summary_updated_at
            elapsed_time = (datetime.now() - start_time).total_seconds()
            feedback_prompt = ""
            if include_feedback_prompt:
                feedback_prompt = _get_feedback_prompt_for_state(state_analysis.primary_state)

            result = _build_success_response(
                answer=answer,
                state_analysis=state_analysis,
                path_recommendation=None,
                conversation_context=conversation_context,
                feedback_prompt=feedback_prompt,
                sources=[],
                concepts=[],
                metadata=_build_fast_success_metadata(
                    user_id=user_id,
                    state_analysis=state_analysis,
                    routing_result=pre_routing_result,
                    mode_reason=mode_directive.reason,
                    informational_mode=informational_mode,
                    mode_prompt_key=mode_prompt_key,
                    prompt_stack_v2_enabled=_prompt_stack_v2_enabled(),
                    output_validation_enabled=_output_validation_enabled(),
                    memory_context_mode=(
                        "summary"
                        if bool(getattr(memory_context_bundle, "summary_used", False))
                        else "full"
                    ),
                    memory_trace_metrics=memory_trace_metrics,
                    summary_length=summary_length,
                    summary_last_turn=summary_last_turn,
                    summary_pending_turn=memory.metadata.get("summary_pending_turn"),
                    memory_turns=memory_turns,
                    hybrid_query_len=len(query or ""),
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    tokens_total=tokens_total,
                    session_metrics=session_metrics,
                ),
                elapsed_time=elapsed_time,
            )
            if debug_info is not None:
                debug_info["fast_path"] = True
                debug_info["routing"] = {
                    "mode": pre_routing_result.mode,
                    "track": getattr(pre_routing_result, "track", "direct"),
                    "tone": getattr(pre_routing_result, "tone", "minimal"),
                    "rule_id": pre_routing_result.decision.rule_id,
                    "reason": pre_routing_result.decision.reason,
                    "confidence_score": pre_routing_result.confidence_score,
                    "confidence_level": pre_routing_result.confidence_level,
                }
            debug_trace = _attach_success_observability(
                result=result,
                strip_legacy_runtime_metadata_fn=_strip_legacy_runtime_metadata,
                attach_debug_payload_fn=_attach_debug_payload,
                debug_info=debug_info,
                memory=memory,
                elapsed_time=elapsed_time,
                llm_result=llm_result,
                debug_trace=debug_trace,
                finalize_success_debug_trace_fn=_finalize_success_debug_trace,
                finalize_success_kwargs={
                    "elapsed_time": elapsed_time,
                    "tokens_prompt": tokens_prompt,
                    "tokens_completion": tokens_completion,
                    "tokens_total": tokens_total,
                    "session_metrics": session_metrics,
                    "memory": memory,
                    "memory_trace_metrics": memory_trace_metrics,
                    "start_time": start_time,
                    "session_store": session_store,
                    "user_id": user_id,
                    "pipeline_stages": pipeline_stages,
                    "model_used": str(model_used),
                    "estimate_cost_fn": _estimate_cost,
                    "compute_anomalies_fn": _compute_anomalies,
                    "attach_trace_schema_fn": attach_trace_schema_status,
                    "build_state_trajectory_fn": _build_state_trajectory,
                    "store_blob_fn": _store_blob,
                    "strip_legacy_trace_fields_fn": _strip_legacy_trace_fields,
                    "aggregate_from_llm_calls": False,
                    "include_summary_pending": True,
                },
            )
            logger.info(f"[ADAPTIVE] fast-path response ready in {elapsed_time:.2f}s")
            return result

        if debug_trace is not None and debug_trace.get("fast_path") is None:
            debug_trace["fast_path"] = False
        
        # ================================================================
        # Р­РўРђРџ 3: РџРѕРёСЃРє СЂРµР»РµРІР°РЅС‚РЅС‹С… Р±Р»РѕРєРѕРІ
        # ================================================================
        logger.debug("рџ”Ќ Р­С‚Р°Рї 3: РџРѕРёСЃРє Р±Р»РѕРєРѕРІ...")

        retrieval_working_state = {
            "nss": (
                diagnostics_v1.nervous_system_state
                if diagnostics_v1
                else "window"
            ),
            "request_function": (
                diagnostics_v1.request_function
                if diagnostics_v1
                else "understand"
            ),
            "confidence": float(getattr(state_analysis, "confidence", 0.0) or 0.0),
        }
        query_builder = HybridQueryBuilder(max_chars=config.MAX_CONTEXT_SIZE + 1200)
        recent_user_turns = _recent_user_turns(memory, limit=2)
        hybrid_query = query_builder.build_query(
            current_question=query,
            conversation_summary=memory.summary or "",
            working_state=retrieval_working_state,
            short_term_context=conversation_context,
            latest_user_turns=recent_user_turns,
        )
        logger.info(
            "[RETRIEVAL] built hybrid_query len=%s (orig_query len=%s)",
            len(hybrid_query),
            len(query),
        )

        current_stage = "retrieval"
        from .semantic_analyzer import detect_author_intent
        retrieval_stage = _retrieve_blocks_with_degraded_mode(
            query=query,
            hybrid_query=hybrid_query,
            top_k=top_k,
            config=config,
            data_loader=data_loader,
            get_retriever_fn=get_retriever,
            timed_fn=_timed,
            detect_author_intent_fn=detect_author_intent,
            logger=logger,
        )
        raw_retrieved_blocks = retrieval_stage["raw_retrieved_blocks"]
        stage = retrieval_stage["stage"]
        retrieval_degraded_reason = retrieval_stage["retrieval_degraded_reason"]

        if debug_trace is not None:
            pipeline_stages.append(stage)
            if retrieval_degraded_reason:
                debug_trace["retrieval_degraded_reason"] = retrieval_degraded_reason
        
        progressive_rag = get_progressive_rag(str(config.BOT_DB_PATH))
        raw_retrieved_blocks = _dedupe_and_apply_progressive_rag(
            raw_retrieved_blocks=raw_retrieved_blocks,
            progressive_rag=progressive_rag,
            debug_trace=debug_trace,
            logger=logger,
        )
        
        _log_retrieval_pairs("Initial retrieval", raw_retrieved_blocks, limit=10)
        retrieved_blocks = list(raw_retrieved_blocks)
        initial_retrieved_blocks = list(raw_retrieved_blocks)
        rerank_prep = _prepare_conditional_rerank(
            retrieved_blocks=retrieved_blocks,
            top_k=top_k,
            config=config,
            use_deterministic_router=use_deterministic_router,
            diagnostics_v1=diagnostics_v1,
            pre_routing_result=pre_routing_result,
            feature_flag_enabled_fn=feature_flags.enabled,
            should_rerank_fn=should_rerank,
        )
        rerank_mode = rerank_prep["rerank_mode"]
        conditional_reranker = rerank_prep["conditional_reranker"]
        should_run_rerank = rerank_prep["should_run_rerank"]
        rerank_reason = rerank_prep["rerank_reason"]
        rerank_k = rerank_prep["rerank_k"]
        rerank_applied = False
        if should_run_rerank and rerank_k > 0:
            reranker = VoyageReranker(
                model=config.VOYAGE_MODEL,
                enabled=bool(config.VOYAGE_ENABLED or (conditional_reranker and config.RERANKER_ENABLED)),
            )
            current_stage = "rerank"
            reranked, rerank_stage = _timed(
                "rerank",
                "Rerank",
                reranker.rerank_pairs,
                query,
                retrieved_blocks,
                top_k=rerank_k,
            )
            rerank_applied = True
            if debug_trace is not None:
                pipeline_stages.append(rerank_stage)
            if reranked:
                retrieved_blocks = reranked
                voyage_active = bool(
                    (config.VOYAGE_ENABLED or (conditional_reranker and config.RERANKER_ENABLED))
                    and config.VOYAGE_API_KEY
                )
                if voyage_active:
                    logger.info("[VOYAGE] rerank success, top_k=%s", rerank_k)
                else:
                    logger.info("[VOYAGE] rerank skipped (disabled)")
        else:
            if debug_trace is not None:
                pipeline_stages.append(
                    {"name": "rerank", "label": "Rerank", "duration_ms": 0, "skipped": True}
                )
            logger.info("[RERANK] skipped: %s", rerank_reason)
        reranked_blocks_for_trace = list(retrieved_blocks)
        routing_signals = detect_routing_signals(query, retrieved_blocks, state_analysis, memory=memory)

        if use_deterministic_router and diagnostics_v1 is not None:
            practice_candidate_score = (
                0.75 if diagnostics_v1.request_function == "solution" else 0.0
            )
            routing_result = route_resolver.resolve(
                diagnostics=diagnostics_v1,
                safety_override=False,
                practice_candidate_score=practice_candidate_score,
                user_stage=user_stage,
            )
            route_resolution_count += 1
            block_cap = confidence_scorer.suggest_block_cap(
                len(retrieved_blocks),
                routing_result.confidence_level,
            )
        else:
            # Wave 4 contract: non-deterministic path uses one DecisionGate result per turn.
            if pre_routing_result is None:
                raise RuntimeError("pre_routing_result is missing in non-deterministic routing flow")
            routing_result = pre_routing_result
            block_cap = decision_gate.scorer.suggest_block_cap(
                len(retrieved_blocks),
                routing_result.confidence_level,
            )
        if _informational_branch_enabled():
            informational_mode = str(getattr(routing_result, "route", "") or "").lower() == "inform"
        else:
            informational_mode = False
        mode_prompt_key, mode_prompt_override = resolve_mode_prompt(
            "informational" if informational_mode else "",
            config,
        )
        stage_count_before_cap = len(retrieved_blocks)
        retrieved_blocks = retrieved_blocks[:block_cap]
        capped_retrieved_blocks = list(retrieved_blocks)
        logger.info(
            f"[RETRIEVAL] confidence_cap={block_cap} (before={stage_count_before_cap})"
        )
        _log_retrieval_pairs("After confidence cap", retrieved_blocks, limit=10)
        mode_directive = build_mode_directive(
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
            reason=routing_result.decision.reason,
            forbid=routing_result.decision.forbid,
        )
        logger.info(
            "ROUTING nss=%s fn=%s route=%s",
            diagnostics_v1.nervous_system_state if diagnostics_v1 else "window",
            diagnostics_v1.request_function if diagnostics_v1 else "understand",
            getattr(routing_result, "route", "reflect"),
        )
        state_context_mode_prompt = _runtime_build_state_context_mode_prompt(
            informational_mode=informational_mode,
            fallback_prompt=mode_directive.prompt,
        )
        phase8_context_suffix = _runtime_build_phase8_context_suffix(
            informational_branch_enabled=_informational_branch_enabled(),
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            informational_mode=informational_mode,
            build_first_turn_instruction_fn=build_first_turn_instruction,
            build_mixed_query_instruction_fn=build_mixed_query_instruction,
            build_user_correction_instruction_fn=build_user_correction_instruction,
            build_informational_guardrail_instruction_fn=build_informational_guardrail_instruction,
        )
        selected_practice, practice_alternatives, practice_context_suffix = (
            _resolve_practice_selection_context(
                routing_result=routing_result,
                diagnostics_v1=diagnostics_v1,
                query=query,
                memory=memory,
                practice_selector=practice_selector,
                practice_allowed_routes=PRACTICE_ALLOWED_ROUTES,
                practice_skip_routes=PRACTICE_SKIP_ROUTES,
                logger=logger,
            )
        )

        _attach_routing_stage_debug_trace(
            debug_trace=debug_trace,
            routing_result=routing_result,
            mode_reason=mode_directive.reason,
            block_cap=block_cap,
            initial_retrieved_blocks=initial_retrieved_blocks,
            hybrid_query=hybrid_query,
            include_full_content=bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True)),
            truncate_preview_fn=_truncate_preview,
            should_run_rerank=bool(should_run_rerank),
            rerank_reason=rerank_reason,
            rerank_applied=bool(rerank_applied),
            route_resolution_count=route_resolution_count,
            informational_mode=informational_mode,
            mode_prompt_key=mode_prompt_key,
            phase8_context_suffix=phase8_context_suffix,
            correction_protocol_active=correction_protocol_active,
            selected_practice=selected_practice,
            practice_alternatives=practice_alternatives,
        )

        conversation_context = _refresh_context_and_apply_trace_snapshot(
            memory=memory,
            conversation_context=conversation_context,
            memory_context_bundle=memory_context_bundle,
            debug_trace=debug_trace,
            diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            route=getattr(routing_result, "route", None),
        )

        if not retrieved_blocks:
            return _handle_no_retrieval_partial_response(
                message=(
                    "Рљ СЃРѕР¶Р°Р»РµРЅРёСЋ, СЂРµР»РµРІР°РЅС‚РЅС‹Р№ РјР°С‚РµСЂРёР°Р» "
                    "РЅРµ РЅР°Р№РґРµРЅ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРµСЂРµС„РѕСЂРјСѓР»РёСЂРѕРІР°С‚СЊ "
                    "РІРѕРїСЂРѕСЃ."
                ),
                state_analysis=state_analysis,
                memory=memory,
                start_time=start_time,
                query=query,
                routing_result=routing_result,
                schedule_summary_task=schedule_summary_task,
                debug_info=debug_info,
                debug_trace=debug_trace,
                session_store=session_store,
                user_id=user_id,
                pipeline_stages=pipeline_stages,
                model_used=str(config.LLM_MODEL),
                initial_retrieved_blocks=initial_retrieved_blocks,
                reranked_blocks_for_trace=reranked_blocks_for_trace,
                append_stages=[
                    {"name": "llm", "label": "LLM", "duration_ms": 0, "skipped": True},
                    {
                        "name": "format",
                        "label": "Р¤РѕСЂРјР°С‚РёСЂРѕРІР°РЅРёРµ",
                        "duration_ms": 0,
                        "skipped": True,
                    },
                ],
                set_working_state_best_effort_fn=_set_working_state_best_effort,
                persist_turn_fn=_persist_turn,
                finalize_failure_debug_trace_fn=_finalize_failure_debug_trace,
                estimate_cost_fn=_estimate_cost,
                compute_anomalies_fn=_compute_anomalies,
                attach_trace_schema_fn=attach_trace_schema_status,
                build_state_trajectory_fn=_build_state_trajectory,
                store_blob_fn=_store_blob,
            )
        
        blocks = [block for block, score in retrieved_blocks]
        adapted_blocks = list(blocks)

        if not adapted_blocks:
            adapted_blocks = blocks[:3]  # fallback
        if debug_trace is not None:
            debug_trace["blocks_after_cap"] = len(adapted_blocks)

        if routing_signals.get("positive_feedback_signal"):
            boosted_ids = _collect_progressive_feedback_blocks(
                adapted_blocks=adapted_blocks,
                progressive_rag=progressive_rag,
                limit=3,
            )
            if boosted_ids:
                logger.info("[PROGRESSIVE_RAG] positive feedback -> boosted blocks: %s", boosted_ids)
            if debug_trace is not None:
                debug_trace["progressive_rag_feedback_blocks"] = boosted_ids
        
        _attach_retrieval_observability(
            debug_info=debug_info,
            debug_trace=debug_trace,
            retrieved_blocks=retrieved_blocks,
            adapted_blocks=adapted_blocks,
            hybrid_query=hybrid_query,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
            capped_retrieved_blocks=capped_retrieved_blocks,
            rerank_k=rerank_k,
            should_run_rerank=should_run_rerank,
            rerank_reason=rerank_reason,
            rerank_applied=rerank_applied,
            block_cap=block_cap,
            routing_result=routing_result,
            route_resolution_count=route_resolution_count,
            build_retrieval_debug_details_fn=_build_retrieval_debug_details,
            build_retrieval_detail_fn=_build_retrieval_detail,
            build_voyage_rerank_debug_payload_fn=_build_voyage_rerank_debug_payload,
            build_routing_debug_payload_fn=_build_routing_debug_payload,
            build_chunk_trace_lists_after_rerank_fn=_build_chunk_trace_lists_after_rerank,
        )
        
        # ================================================================
        # Р­РўРђРџ 4: Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р° СЃ РєРѕРЅС‚РµРєСЃС‚РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ
        # ================================================================
        logger.debug("рџ¤– Р­С‚Р°Рї 4: Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р°...")
        
        # Р”РѕР±Р°РІРёС‚СЊ РєРѕРЅС‚РµРєСЃС‚ СЃРѕСЃС‚РѕСЏРЅРёСЏ
        state_context = _compose_state_context(
            state_analysis=state_analysis,
            mode_prompt=state_context_mode_prompt,
            nervous_system_state=(
                diagnostics_v1.nervous_system_state if diagnostics_v1 else "window"
            ),
            request_function=(
                diagnostics_v1.request_function if diagnostics_v1 else "understand"
            ),
            contradiction_suggestion=contradiction_hint,
            cross_session_context=cross_session_context,
            phase8_context_suffix=phase8_context_suffix,
            practice_context_suffix=practice_context_suffix,
            build_state_context_fn=_build_state_context,
        )

        # Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р° (СЃ СѓС‡С‘С‚РѕРј РёСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіР°)
        current_stage = "llm"
        llm_result, response_generator, _, system_prompt_override = _run_llm_generation_cycle(
            response_generator_cls=ResponseGenerator,
            query=query,
            blocks=adapted_blocks,
            conversation_context=conversation_context,
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
            forbid=routing_result.decision.forbid,
            additional_system_context=state_context,
            sd_level=sd_result.primary,
            config=config,
            session_store=session_store,
            session_id=user_id,
            mode_prompt_override=mode_prompt_override,
            informational_mode=informational_mode,
            route=getattr(routing_result, "route", ""),
            diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            prompt_stack_enabled=_prompt_stack_v2_enabled(),
            prompt_registry=prompt_registry_v2,
            mode_prompt=mode_directive.prompt,
            debug_trace=debug_trace,
            pipeline_stages=pipeline_stages,
            build_prompt_stack_override_fn=_build_prompt_stack_override,
            prepare_llm_prompt_previews_fn=_prepare_llm_prompt_previews,
            generate_llm_with_trace_fn=_generate_llm_with_trace,
            build_llm_call_trace_fn=_build_llm_call_trace,
        )
        
        if llm_result.get("error") and llm_result["error"] not in ["no_blocks"]:
            logger.error(f"[ADAPTIVE] LLM error: {llm_result['error']}")
            response = _handle_llm_generation_error_response(
                llm_error=str(llm_result.get("error", "")),
                state_analysis=state_analysis,
                start_time=start_time,
                memory=memory,
                query=query,
                schedule_summary_task=schedule_summary_task,
                debug_info=debug_info,
                debug_trace=debug_trace,
                session_store=session_store,
                user_id=user_id,
                pipeline_stages=pipeline_stages,
                model_used=str(config.LLM_MODEL),
                initial_retrieved_blocks=initial_retrieved_blocks,
                reranked_blocks_for_trace=reranked_blocks_for_trace,
                finalize_failure_debug_trace_fn=_finalize_failure_debug_trace,
                estimate_cost_fn=_estimate_cost,
                compute_anomalies_fn=_compute_anomalies,
                attach_trace_schema_fn=attach_trace_schema_status,
                build_state_trajectory_fn=_build_state_trajectory,
                store_blob_fn=_store_blob,
            )
            return response
        
        answer = llm_result["answer"]
        formatter = ResponseFormatter()
        answer = formatter.format_answer(
            answer,
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
            user_message=query,
            informational_mode=informational_mode,
        )

        def _retry_validation(hint: str) -> Dict[str, Any]:
            return _run_validation_retry_generation(
                response_generator=response_generator,
                query=query,
                hint=hint,
                blocks=adapted_blocks,
                conversation_context=conversation_context,
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                forbid=routing_result.decision.forbid,
                additional_system_context=state_context,
                sd_level=sd_result.primary,
                config=config,
                session_store=session_store,
                session_id=user_id,
                mode_prompt_override=mode_prompt_override,
                informational_mode=informational_mode,
                system_prompt_override=system_prompt_override,
                format_answer_fn=lambda raw_answer: formatter.format_answer(
                    raw_answer,
                    mode=routing_result.mode,
                    confidence_level=routing_result.confidence_level,
                    user_message=query,
                    informational_mode=informational_mode,
                ),
            )

        answer, validation_meta, validation_retry_result = _apply_output_validation_policy(
            answer=answer,
            query=query,
            route=getattr(routing_result, "route", ""),
            mode=routing_result.mode,
            generate_retry_fn=_retry_validation,
        )
        _apply_output_validation_observability(
            validation_meta=validation_meta,
            validation_retry_result=validation_retry_result,
            llm_result=llm_result,
            debug_trace=debug_trace,
            pipeline_stages=pipeline_stages,
            fallback_model_name=str(config.LLM_MODEL),
            include_retry_llm_trace=True,
        )

        # ================================================================
        # Р­РўРђРџ 5: РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ Р°РЅР°Р»РёР· Рё РёР·РІР»РµС‡РµРЅРёРµ РєРѕРЅС†РµРїС‚РѕРІ
        # ================================================================
        logger.debug("рџ”¬ Р­С‚Р°Рї 5: РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ Р°РЅР°Р»РёР·...")
        
        semantic_analyzer = SemanticAnalyzer()
        semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
        concepts = semantic_data.get("primary_concepts", [])
        
        # ================================================================
        # Р­РўРђРџ 6: Р РµРєРѕРјРµРЅРґР°С†РёСЏ РїСѓС‚Рё (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)
        # ================================================================
        logger.debug("рџ›¤пёЏ Р­С‚Р°Рї 6: Р РµРєРѕРјРµРЅРґР°С†РёСЏ РїСѓС‚Рё...")
        
        path_recommendation = None
        route_name = str(getattr(routing_result, "route", "") or "").lower()
        path_builder_blocked_routes = {"inform", "reflect", "contact_hold", "regulate"}
        path_recommendation = _build_path_recommendation_if_enabled(
            include_path_recommendation=include_path_recommendation,
            state_analysis=state_analysis,
            route_name=route_name,
            path_builder_blocked_routes=path_builder_blocked_routes,
            user_id=user_id,
            user_level_enum=path_level_enum,
            memory=memory,
            path_builder=path_builder,
            logger=logger,
        )
        
        # ================================================================
        # Р­РўРђРџ 7: РџРѕРґРіРѕС‚РѕРІРєР° Р·Р°РїСЂРѕСЃР° РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
        # ================================================================
        logger.debug("рџ“ќ Р­С‚Р°Рї 7: РџРѕРґРіРѕС‚РѕРІРєР° РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё...")
        
        feedback_prompt = ""
        if include_feedback_prompt:
            feedback_prompt = _get_feedback_prompt_for_state(state_analysis.primary_state)
        
        # ================================================================
        # Р­РўРђРџ 8: РЎРѕС…СЂР°РЅРµРЅРёРµ РІ РїР°РјСЏС‚СЊ
        # ================================================================
        logger.debug("рџ’ѕ Р­С‚Р°Рї 8: РЎРѕС…СЂР°РЅРµРЅРёРµ РІ РїР°РјСЏС‚СЊ...")
        
        _set_working_state_best_effort(
            memory=memory,
            state_analysis=state_analysis,
            routing_result=routing_result,
            log_prefix="[ADAPTIVE] working_state update failed:",
        )

        llm_metrics = _collect_llm_session_metrics(
            memory=memory,
            llm_result=llm_result if isinstance(llm_result, dict) else {},
            fallback_model_name=config.LLM_MODEL,
            update_session_token_metrics_fn=_update_session_token_metrics,
        )
        tokens_prompt = llm_metrics["tokens_prompt"]
        tokens_completion = llm_metrics["tokens_completion"]
        tokens_total = llm_metrics["tokens_total"]
        model_used = llm_metrics["model_used"]
        session_metrics = llm_metrics["session_metrics"]

        _persist_turn(
            memory=memory,
            user_input=query,
            bot_response=answer,
            user_state=state_analysis.primary_state.value,
            blocks_used=len(adapted_blocks),
            concepts=concepts,
            schedule_summary_task=schedule_summary_task,
        )
        _save_session_summary_best_effort(
            memory=memory,
            user_id=user_id,
            query=query,
            answer=answer,
            state_end=state_analysis.primary_state.value,
            concepts=concepts,
            logger=logger,
        )
        
        # ================================================================
        # Р¤РќРђР›Р¬РќР«Р™ Р Р•Р—РЈР›Р¬РўРђРў
        # ================================================================
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        sources = _build_sources_from_blocks(adapted_blocks)
        _log_blocks("SOURCES", adapted_blocks, limit=10)
        
        result = _build_success_response(
            answer=answer,
            state_analysis=state_analysis,
            path_recommendation=path_recommendation,
            conversation_context=conversation_context,
            feedback_prompt=feedback_prompt,
            sources=sources,
            concepts=concepts,
            metadata=_build_full_success_metadata(
                user_id=user_id,
                state_analysis=state_analysis,
                routing_result=routing_result,
                mode_reason=mode_directive.reason,
                route_resolution_count=route_resolution_count,
                blocks_used=len(adapted_blocks),
                selected_practice=selected_practice,
                practice_alternatives=practice_alternatives,
                retrieval_block_cap=block_cap,
                informational_mode=informational_mode,
                mode_prompt_key=mode_prompt_key,
                prompt_stack_v2_enabled=_prompt_stack_v2_enabled(),
                output_validation_enabled=_output_validation_enabled(),
                diagnostics_v1_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
                contradiction_detected=bool(contradiction_info.get("has_contradiction", False)),
                cross_session_context_used=bool(cross_session_context),
                memory_context_mode=(
                    "summary"
                    if bool(getattr(memory_context_bundle, "summary_used", False))
                    else "full"
                ),
                memory_trace_metrics=memory_trace_metrics,
                summary_length=len(memory.summary) if memory.summary else 0,
                summary_last_turn=memory.summary_updated_at,
                summary_pending_turn=memory.metadata.get("summary_pending_turn"),
                memory_turns=len(memory.turns),
                hybrid_query_len=len(hybrid_query),
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                session_metrics=session_metrics,
            ),
            elapsed_time=elapsed_time,
        )

        debug_trace = _attach_success_observability(
            result=result,
            strip_legacy_runtime_metadata_fn=_strip_legacy_runtime_metadata,
            attach_debug_payload_fn=_attach_debug_payload,
            debug_info=debug_info,
            memory=memory,
            elapsed_time=elapsed_time,
            llm_result=llm_result,
            retrieval_details=(debug_info or {}).get("retrieval_details", {}),
            sources=sources,
            debug_trace=debug_trace,
            finalize_success_debug_trace_fn=_finalize_success_debug_trace,
            finalize_success_kwargs={
                "elapsed_time": elapsed_time,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "tokens_total": tokens_total,
                "session_metrics": session_metrics,
                "memory": memory,
                "memory_trace_metrics": memory_trace_metrics,
                "start_time": start_time,
                "session_store": session_store,
                "user_id": user_id,
                "pipeline_stages": pipeline_stages,
                "model_used": str(model_used),
                "estimate_cost_fn": _estimate_cost,
                "compute_anomalies_fn": _compute_anomalies,
                "attach_trace_schema_fn": attach_trace_schema_status,
                "build_state_trajectory_fn": _build_state_trajectory,
                "store_blob_fn": _store_blob,
                "strip_legacy_trace_fields_fn": _strip_legacy_trace_fields,
                "aggregate_from_llm_calls": True,
                "include_summary_pending": True,
            },
        )
        
        logger.info(f"[ADAPTIVE] response ready in {elapsed_time:.2f}s")
        
        return result
    
    except Exception as e:
        logger.error(f"[ADAPTIVE] unhandled error: {e}", exc_info=True)
        response = _build_error_response(
            f"Произошла ошибка при обработке запроса: {str(e)}",
            state_analysis,
            start_time,
        )
        response["metadata"] = {"user_id": user_id}
        try:
            memory = get_conversation_memory(user_id)
            _persist_turn_best_effort(
                memory=memory,
                user_input=query,
                bot_response=response["answer"],
                blocks_used=0,
                schedule_summary_task=schedule_summary_task,
            )
        except Exception:
            pass
        if debug_trace is not None:
            debug_trace["pipeline_error"] = {
                "stage": str(current_stage),
                "exception_type": type(e).__name__,
                "message": str(e),
                "partial_trace_available": True,
            }
            try:
                memory = get_conversation_memory(user_id)
                debug_trace = _finalize_failure_debug_trace(
                    debug_trace,
                    memory=memory,
                    start_time=start_time,
                    session_store=session_store,
                    user_id=user_id,
                    pipeline_stages=pipeline_stages,
                    model_used=str(config.LLM_MODEL),
                    estimate_cost_fn=_estimate_cost,
                    compute_anomalies_fn=_compute_anomalies,
                    attach_trace_schema_fn=attach_trace_schema_status,
                    build_state_trajectory_fn=_build_state_trajectory,
                    store_blob_fn=_store_blob,
                    include_chunks=False,
                    include_total_duration=False,
                    strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
                )
            except Exception:
                pass
            response["debug_trace"] = debug_trace
        return response
