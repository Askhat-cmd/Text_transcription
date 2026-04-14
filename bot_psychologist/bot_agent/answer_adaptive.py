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
    _build_fast_path_success_response as _runtime_build_fast_path_success_response,
    _build_full_path_success_response as _runtime_build_full_path_success_response,
    _build_unhandled_exception_response as _runtime_build_unhandled_exception_response,
    _run_full_path_success_stage as _runtime_run_full_path_success_stage,
    _persist_turn_best_effort,
    _persist_turn,
    _save_session_summary_best_effort,
    _build_sources_from_blocks,
    _attach_debug_payload,
    _attach_success_observability,
    _run_no_retrieval_stage as _runtime_run_no_retrieval_stage,
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
    _build_voyage_rerank_debug_payload,
    _build_routing_debug_payload,
    _prepare_adapted_blocks_and_attach_observability as _runtime_prepare_adapted_blocks_and_attach_observability,
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
    _run_state_and_pre_routing_pipeline as _runtime_run_state_and_pre_routing_pipeline,
    _apply_fast_path_debug_bootstrap as _runtime_apply_fast_path_debug_bootstrap,
    _build_phase8_context_suffix as _runtime_build_phase8_context_suffix,
    _build_fast_path_mode_directive as _runtime_build_fast_path_mode_directive,
    _resolve_routing_and_apply_block_cap as _runtime_resolve_routing_and_apply_block_cap,
    _finalize_routing_context_and_trace as _runtime_finalize_routing_context_and_trace,
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
    _format_and_validate_llm_answer as _runtime_format_and_validate_llm_answer,
    _run_full_path_llm_stage as _runtime_run_full_path_llm_stage,
    _run_fast_path_stage as _runtime_run_fast_path_stage,
)
from .adaptive_runtime.retrieval_stage_helpers import (
    _dedupe_and_apply_progressive_rag as _runtime_dedupe_and_apply_progressive_rag,
    _prepare_conditional_rerank as _runtime_prepare_conditional_rerank,
    _run_retrieval_and_rerank_stage as _runtime_run_retrieval_and_rerank_stage,
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


def _format_and_validate_llm_answer(**kwargs):
    return _runtime_format_and_validate_llm_answer(**kwargs)


def _run_full_path_llm_stage(**kwargs):
    return _runtime_run_full_path_llm_stage(**kwargs)


def _run_fast_path_stage(**kwargs):
    return _runtime_run_fast_path_stage(**kwargs)


def _dedupe_and_apply_progressive_rag(**kwargs):
    return _runtime_dedupe_and_apply_progressive_rag(**kwargs)


def _prepare_conditional_rerank(**kwargs):
    return _runtime_prepare_conditional_rerank(**kwargs)


def _run_retrieval_and_rerank_stage(**kwargs):
    return _runtime_run_retrieval_and_rerank_stage(**kwargs)


def _run_state_and_pre_routing_pipeline(**kwargs):
    return _runtime_run_state_and_pre_routing_pipeline(**kwargs)


def _resolve_routing_and_apply_block_cap(**kwargs):
    return _runtime_resolve_routing_and_apply_block_cap(**kwargs)


def _finalize_routing_context_and_trace(**kwargs):
    return _runtime_finalize_routing_context_and_trace(**kwargs)


def _build_path_recommendation_if_enabled(**kwargs):
    return _runtime_build_path_recommendation_if_enabled(**kwargs)


def _build_fast_path_success_response(**kwargs):
    return _runtime_build_fast_path_success_response(**kwargs)


def _build_full_path_success_response(**kwargs):
    return _runtime_build_full_path_success_response(**kwargs)


def _build_unhandled_exception_response(**kwargs):
    return _runtime_build_unhandled_exception_response(**kwargs)


def _run_full_path_success_stage(**kwargs):
    return _runtime_run_full_path_success_stage(**kwargs)


def _run_no_retrieval_stage(**kwargs):
    return _runtime_run_no_retrieval_stage(**kwargs)


def _handle_llm_generation_error_response(**kwargs):
    return _runtime_handle_llm_generation_error_response(**kwargs)


def _prepare_adapted_blocks_and_attach_observability(**kwargs):
    return _runtime_prepare_adapted_blocks_and_attach_observability(**kwargs)


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
        
        current_stage = "state_classifier"
        stage2 = _run_state_and_pre_routing_pipeline(
            query=query,
            memory=memory,
            config=config,
            phase8_signals=phase8_signals,
            debug_trace=debug_trace,
            debug_info=debug_info,
            pipeline_stages=pipeline_stages,
            timed_fn=_timed,
            run_coroutine_sync_fn=_run_coroutine_sync,
            state_classifier=state_classifier,
            classify_parallel_fn=_classify_parallel,
            fallback_state_analysis_fn=_fallback_state_analysis,
            fallback_sd_result_fn=_fallback_sd_result,
            resolve_user_stage_fn=resolve_user_stage,
            derive_informational_mode_hint_fn=_derive_informational_mode_hint,
            resolve_mode_prompt_fn=resolve_mode_prompt,
            logger=logger,
            diagnostics_v1_enabled=_diagnostics_v1_enabled(),
            deterministic_route_resolver_enabled=_deterministic_route_resolver_enabled(),
            informational_branch_enabled=_informational_branch_enabled(),
            diagnostics_classifier=diagnostics_classifier,
            detect_contradiction_fn=detect_contradiction,
            decision_gate_cls=DecisionGate,
            detect_routing_signals_fn=detect_routing_signals,
            should_use_fast_path_fn=_should_use_fast_path,
        )
        state_analysis = stage2["state_analysis"]
        sd_result = stage2["sd_result"]
        user_stage = stage2["user_stage"]
        informational_mode_hint = stage2["informational_mode_hint"]
        informational_mode = stage2["informational_mode"]
        mode_prompt_key = stage2["mode_prompt_key"]
        mode_prompt_override = stage2["mode_prompt_override"]
        use_new_diagnostics_v1 = stage2["use_new_diagnostics_v1"]
        use_deterministic_router = stage2["use_deterministic_router"]
        confidence_scorer = ConfidenceScorer()
        route_resolution_count = 0
        diagnostics_v1 = stage2["diagnostics_v1"]
        correction_protocol_active = stage2["correction_protocol_active"]
        contradiction_info = stage2["contradiction_info"]
        contradiction_hint = stage2["contradiction_hint"]
        decision_gate = stage2["decision_gate"]
        pre_routing_result = stage2["pre_routing_result"]
        fast_path_enabled = stage2["fast_path_enabled"]

        fast_path_stage = _run_fast_path_stage(
            fast_path_enabled=fast_path_enabled,
            logger=logger,
            pre_routing_result=pre_routing_result,
            debug_trace=debug_trace,
            query=query,
            detect_fast_path_reason_fn=_detect_fast_path_reason,
            truncate_preview_fn=_truncate_preview,
            config=config,
            pipeline_stages=pipeline_stages,
            apply_fast_path_debug_bootstrap_fn=_runtime_apply_fast_path_debug_bootstrap,
            build_fast_path_mode_directive_fn=_runtime_build_fast_path_mode_directive,
            informational_mode=informational_mode,
            build_mode_directive_fn=build_mode_directive,
            memory=memory,
            conversation_context=conversation_context,
            memory_context_bundle=memory_context_bundle,
            diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            refresh_context_and_apply_trace_snapshot_fn=_refresh_context_and_apply_trace_snapshot,
            build_fast_path_block_fn=_build_fast_path_block,
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            informational_branch_enabled=_informational_branch_enabled(),
            build_phase8_context_suffix_fn=_runtime_build_phase8_context_suffix,
            build_first_turn_instruction_fn=build_first_turn_instruction,
            build_mixed_query_instruction_fn=build_mixed_query_instruction,
            build_user_correction_instruction_fn=build_user_correction_instruction,
            build_informational_guardrail_instruction_fn=build_informational_guardrail_instruction,
            state_analysis=state_analysis,
            contradiction_hint=contradiction_hint,
            cross_session_context=cross_session_context,
            compose_state_context_fn=_compose_state_context,
            build_state_context_fn=_build_state_context,
            diagnostics_v1=diagnostics_v1,
            run_llm_generation_cycle_fn=_run_llm_generation_cycle,
            response_generator_cls=ResponseGenerator,
            sd_primary=sd_result.primary,
            session_store=session_store,
            user_id=user_id,
            mode_prompt_override=mode_prompt_override,
            prompt_stack_enabled=_prompt_stack_v2_enabled(),
            prompt_registry=prompt_registry_v2,
            build_prompt_stack_override_fn=_build_prompt_stack_override,
            prepare_llm_prompt_previews_fn=_prepare_llm_prompt_previews,
            generate_llm_with_trace_fn=_generate_llm_with_trace,
            build_llm_call_trace_fn=_build_llm_call_trace,
            format_and_validate_llm_answer_fn=_format_and_validate_llm_answer,
            response_formatter_cls=ResponseFormatter,
            run_validation_retry_generation_fn=_run_validation_retry_generation,
            apply_output_validation_policy_fn=_apply_output_validation_policy,
            apply_output_validation_observability_fn=_apply_output_validation_observability,
            set_working_state_best_effort_fn=_set_working_state_best_effort,
            include_feedback_prompt=include_feedback_prompt,
            mode_prompt_key=mode_prompt_key,
            memory_trace_metrics=memory_trace_metrics,
            schedule_summary_task=schedule_summary_task,
            start_time=start_time,
            debug_info=debug_info,
            llm_model_name=str(config.LLM_MODEL),
            collect_llm_session_metrics_fn=_collect_llm_session_metrics,
            update_session_token_metrics_fn=_update_session_token_metrics,
            persist_turn_fn=_persist_turn,
            get_feedback_prompt_for_state_fn=_get_feedback_prompt_for_state,
            build_fast_path_success_response_fn=_build_fast_path_success_response,
            build_success_response_fn=_build_success_response,
            build_fast_success_metadata_fn=_build_fast_success_metadata,
            output_validation_enabled=_output_validation_enabled(),
            attach_success_observability_fn=_attach_success_observability,
            strip_legacy_runtime_metadata_fn=_strip_legacy_runtime_metadata,
            attach_debug_payload_fn=_attach_debug_payload,
            finalize_success_debug_trace_fn=_finalize_success_debug_trace,
            estimate_cost_fn=_estimate_cost,
            compute_anomalies_fn=_compute_anomalies,
            attach_trace_schema_fn=attach_trace_schema_status,
            build_state_trajectory_fn=_build_state_trajectory,
            store_blob_fn=_store_blob,
            strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
        )
        if fast_path_stage is not None:
            return fast_path_stage["result"]

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
        retrieval_stage = _run_retrieval_and_rerank_stage(
            query=query,
            top_k=top_k,
            config=config,
            data_loader=data_loader,
            get_retriever_fn=get_retriever,
            timed_fn=_timed,
            detect_author_intent_fn=detect_author_intent,
            logger=logger,
            debug_trace=debug_trace,
            pipeline_stages=pipeline_stages,
            get_progressive_rag_fn=get_progressive_rag,
            dedupe_and_apply_progressive_rag_fn=_dedupe_and_apply_progressive_rag,
            log_retrieval_pairs_fn=_log_retrieval_pairs,
            prepare_conditional_rerank_fn=_prepare_conditional_rerank,
            use_deterministic_router=use_deterministic_router,
            diagnostics_v1=diagnostics_v1,
            pre_routing_result=pre_routing_result,
            feature_flag_enabled_fn=feature_flags.enabled,
            should_rerank_fn=should_rerank,
            voyage_reranker_cls=VoyageReranker,
            detect_routing_signals_fn=detect_routing_signals,
            state_analysis=state_analysis,
            memory=memory,
            hybrid_query=hybrid_query,
        )
        retrieved_blocks = retrieval_stage["retrieved_blocks"]
        initial_retrieved_blocks = retrieval_stage["initial_retrieved_blocks"]
        reranked_blocks_for_trace = retrieval_stage["reranked_blocks_for_trace"]
        progressive_rag = retrieval_stage["progressive_rag"]
        rerank_mode = retrieval_stage["rerank_mode"]
        conditional_reranker = retrieval_stage["conditional_reranker"]
        should_run_rerank = retrieval_stage["should_run_rerank"]
        rerank_reason = retrieval_stage["rerank_reason"]
        rerank_k = retrieval_stage["rerank_k"]
        rerank_applied = retrieval_stage["rerank_applied"]
        routing_signals = retrieval_stage["routing_signals"]
        if rerank_applied:
            current_stage = "rerank"

        routing_cap_stage = _resolve_routing_and_apply_block_cap(
            use_deterministic_router=use_deterministic_router,
            diagnostics_v1=diagnostics_v1,
            user_stage=user_stage,
            route_resolver=route_resolver,
            confidence_scorer=confidence_scorer,
            pre_routing_result=pre_routing_result,
            decision_gate=decision_gate,
            retrieved_blocks=retrieved_blocks,
            informational_branch_enabled_fn=_informational_branch_enabled,
            resolve_mode_prompt_fn=resolve_mode_prompt,
            config=config,
            log_retrieval_pairs_fn=_log_retrieval_pairs,
            build_mode_directive_fn=build_mode_directive,
            logger=logger,
        )
        routing_result = routing_cap_stage["routing_result"]
        block_cap = routing_cap_stage["block_cap"]
        route_resolution_count += int(routing_cap_stage["route_resolution_increment"])
        informational_mode = routing_cap_stage["informational_mode"]
        mode_prompt_key = routing_cap_stage["mode_prompt_key"]
        mode_prompt_override = routing_cap_stage["mode_prompt_override"]
        retrieved_blocks = routing_cap_stage["retrieved_blocks"]
        capped_retrieved_blocks = routing_cap_stage["capped_retrieved_blocks"]
        mode_directive = routing_cap_stage["mode_directive"]
        state_context_mode_prompt = routing_cap_stage["state_context_mode_prompt"]

        routing_context_stage = _finalize_routing_context_and_trace(
            informational_branch_enabled=_informational_branch_enabled(),
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            informational_mode=informational_mode,
            build_first_turn_instruction_fn=build_first_turn_instruction,
            build_mixed_query_instruction_fn=build_mixed_query_instruction,
            build_user_correction_instruction_fn=build_user_correction_instruction,
            build_informational_guardrail_instruction_fn=build_informational_guardrail_instruction,
            routing_result=routing_result,
            diagnostics_v1=diagnostics_v1,
            query=query,
            memory=memory,
            practice_selector=practice_selector,
            practice_allowed_routes=PRACTICE_ALLOWED_ROUTES,
            practice_skip_routes=PRACTICE_SKIP_ROUTES,
            logger=logger,
            debug_trace=debug_trace,
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
            mode_prompt_key=mode_prompt_key,
            conversation_context=conversation_context,
            memory_context_bundle=memory_context_bundle,
            refresh_context_and_apply_trace_snapshot_fn=_refresh_context_and_apply_trace_snapshot,
        )
        phase8_context_suffix = routing_context_stage["phase8_context_suffix"]
        selected_practice = routing_context_stage["selected_practice"]
        practice_alternatives = routing_context_stage["practice_alternatives"]
        practice_context_suffix = routing_context_stage["practice_context_suffix"]
        conversation_context = routing_context_stage["conversation_context"]

        if not retrieved_blocks:
            return _run_no_retrieval_stage(
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
                set_working_state_best_effort_fn=_set_working_state_best_effort,
                persist_turn_fn=_persist_turn,
                finalize_failure_debug_trace_fn=_finalize_failure_debug_trace,
                estimate_cost_fn=_estimate_cost,
                compute_anomalies_fn=_compute_anomalies,
                attach_trace_schema_fn=attach_trace_schema_status,
                build_state_trajectory_fn=_build_state_trajectory,
                store_blob_fn=_store_blob,
            )
        
        retrieval_observability_stage = _prepare_adapted_blocks_and_attach_observability(
            retrieved_blocks=retrieved_blocks,
            routing_signals=routing_signals,
            progressive_rag=progressive_rag,
            debug_trace=debug_trace,
            logger=logger,
            debug_info=debug_info,
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
        blocks = retrieval_observability_stage["blocks"]
        adapted_blocks = retrieval_observability_stage["adapted_blocks"]
        
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
        llm_stage = _run_full_path_llm_stage(
            query=query,
            adapted_blocks=adapted_blocks,
            conversation_context=conversation_context,
            routing_result=routing_result,
            state_context=state_context,
            sd_primary=sd_result.primary,
            config=config,
            session_store=session_store,
            user_id=user_id,
            mode_prompt_override=mode_prompt_override,
            informational_mode=informational_mode,
            diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            prompt_stack_enabled=_prompt_stack_v2_enabled(),
            prompt_registry=prompt_registry_v2,
            mode_prompt=mode_directive.prompt,
            debug_trace=debug_trace,
            pipeline_stages=pipeline_stages,
            run_llm_generation_cycle_fn=_run_llm_generation_cycle,
            response_generator_cls=ResponseGenerator,
            build_prompt_stack_override_fn=_build_prompt_stack_override,
            prepare_llm_prompt_previews_fn=_prepare_llm_prompt_previews,
            generate_llm_with_trace_fn=_generate_llm_with_trace,
            build_llm_call_trace_fn=_build_llm_call_trace,
            format_and_validate_llm_answer_fn=_format_and_validate_llm_answer,
            response_formatter_cls=ResponseFormatter,
            run_validation_retry_generation_fn=_run_validation_retry_generation,
            apply_output_validation_policy_fn=_apply_output_validation_policy,
            apply_output_validation_observability_fn=_apply_output_validation_observability,
            handle_llm_generation_error_response_fn=_handle_llm_generation_error_response,
            state_analysis=state_analysis,
            start_time=start_time,
            memory=memory,
            schedule_summary_task=schedule_summary_task,
            debug_info=debug_info,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
            finalize_failure_debug_trace_fn=_finalize_failure_debug_trace,
            estimate_cost_fn=_estimate_cost,
            compute_anomalies_fn=_compute_anomalies,
            attach_trace_schema_fn=attach_trace_schema_status,
            build_state_trajectory_fn=_build_state_trajectory,
            store_blob_fn=_store_blob,
            llm_model_name=str(config.LLM_MODEL),
            logger=logger,
        )
        if llm_stage["error_response"] is not None:
            return llm_stage["error_response"]
        llm_result = llm_stage["llm_result"]
        answer = llm_stage["answer"]

        # ================================================================
        # Р­РўРђРџ 5: РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ Р°РЅР°Р»РёР· Рё РёР·РІР»РµС‡РµРЅРёРµ РєРѕРЅС†РµРїС‚РѕРІ
        # ================================================================
        logger.debug("рџ”¬ Р­С‚Р°Рї 5: РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ Р°РЅР°Р»РёР·...")
        
        logger.debug("рџ›¤пёЏ Р­С‚Р°Рї 6: Р РµРєРѕРјРµРЅРґР°С†РёСЏ РїСѓС‚Рё...")
        logger.debug("рџ“ќ Р­С‚Р°Рї 7: РџРѕРґРіРѕС‚РѕРІРєР° РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё...")
        logger.debug("рџ’ѕ Р­С‚Р°Рї 8: РЎРѕС…СЂР°РЅРµРЅРёРµ РІ РїР°РјСЏС‚СЊ...")

        result = _run_full_path_success_stage(
            memory=memory,
            query=query,
            answer=answer,
            state_analysis=state_analysis,
            routing_result=routing_result,
            adapted_blocks=adapted_blocks,
            include_path_recommendation=include_path_recommendation,
            include_feedback_prompt=include_feedback_prompt,
            user_id=user_id,
            user_level_enum=path_level_enum,
            llm_result=llm_result,
            fallback_model_name=str(config.LLM_MODEL),
            schedule_summary_task=schedule_summary_task,
            collect_llm_session_metrics_fn=_collect_llm_session_metrics,
            update_session_token_metrics_fn=_update_session_token_metrics,
            set_working_state_best_effort_fn=_set_working_state_best_effort,
            build_path_recommendation_if_enabled_fn=_build_path_recommendation_if_enabled,
            get_feedback_prompt_for_state_fn=_get_feedback_prompt_for_state,
            persist_turn_fn=_persist_turn,
            save_session_summary_best_effort_fn=_save_session_summary_best_effort,
            semantic_analyzer_cls=SemanticAnalyzer,
            path_builder=path_builder,
            build_full_path_success_response_fn=_build_full_path_success_response,
            conversation_context=conversation_context,
            debug_info=debug_info,
            debug_trace=debug_trace,
            start_time=start_time,
            mode_directive_reason=mode_directive.reason,
            route_resolution_count=route_resolution_count,
            selected_practice=selected_practice,
            practice_alternatives=practice_alternatives,
            block_cap=block_cap,
            informational_mode=informational_mode,
            mode_prompt_key=mode_prompt_key,
            prompt_stack_v2_enabled=_prompt_stack_v2_enabled(),
            output_validation_enabled=_output_validation_enabled(),
            diagnostics_v1_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            contradiction_detected=bool(contradiction_info.get("has_contradiction", False)),
            cross_session_context_used=bool(cross_session_context),
            memory_context_bundle=memory_context_bundle,
            memory_trace_metrics=memory_trace_metrics,
            hybrid_query=hybrid_query,
            session_store=session_store,
            pipeline_stages=pipeline_stages,
            build_sources_from_blocks_fn=_build_sources_from_blocks,
            log_blocks_fn=_log_blocks,
            build_success_response_fn=_build_success_response,
            build_full_success_metadata_fn=_build_full_success_metadata,
            attach_success_observability_fn=_attach_success_observability,
            strip_legacy_runtime_metadata_fn=_strip_legacy_runtime_metadata,
            attach_debug_payload_fn=_attach_debug_payload,
            finalize_success_debug_trace_fn=_finalize_success_debug_trace,
            estimate_cost_fn=_estimate_cost,
            compute_anomalies_fn=_compute_anomalies,
            attach_trace_schema_fn=attach_trace_schema_status,
            build_state_trajectory_fn=_build_state_trajectory,
            store_blob_fn=_store_blob,
            strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
            logger=logger,
        )

        return result
    
    except Exception as e:
        logger.error(f"[ADAPTIVE] unhandled error: {e}", exc_info=True)
        response = _build_unhandled_exception_response(
            exception=e,
            state_analysis=state_analysis,
            start_time=start_time,
            user_id=user_id,
            query=query,
            schedule_summary_task=schedule_summary_task,
            debug_trace=debug_trace,
            current_stage=str(current_stage),
            session_store=session_store,
            pipeline_stages=pipeline_stages,
            llm_model_name=str(config.LLM_MODEL),
            build_error_response_fn=_build_error_response,
            get_conversation_memory_fn=get_conversation_memory,
            persist_turn_best_effort_fn=_persist_turn_best_effort,
            finalize_failure_debug_trace_fn=_finalize_failure_debug_trace,
            estimate_cost_fn=_estimate_cost,
            compute_anomalies_fn=_compute_anomalies,
            attach_trace_schema_fn=attach_trace_schema_status,
            build_state_trajectory_fn=_build_state_trajectory,
            store_blob_fn=_store_blob,
            strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
        )
        return response
