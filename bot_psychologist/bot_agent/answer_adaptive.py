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

import logging
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime

from .data_loader import data_loader
from .retriever import get_retriever
from .user_level_types import UserLevel
from .state_classifier import state_classifier, StateAnalysis
from .conversation_memory import get_conversation_memory
from .config import config
from .decision import (
    DecisionGate,
    detect_routing_signals,
    resolve_user_stage,
)
from .retrieval import ConfidenceScorer, VoyageReranker
from .response import ResponseFormatter, ResponseGenerator
from .feature_flags import feature_flags
from .contradiction_detector import detect_contradiction
from .diagnostics_classifier import diagnostics_classifier
from .route_resolver import route_resolver
from .memory_updater import memory_updater
from .prompt_registry_v2 import prompt_registry_v2
from .output_validator import output_validator
from .practice_selector import practice_selector
from .onboarding_flow import (
    detect_phase8_signals,
)
from .adaptive_runtime.pipeline_utils import (
    _timed,
    _build_config_snapshot,
    _run_coroutine_sync,
)
from .adaptive_runtime.response_utils import (
    _build_partial_response,
    _build_unhandled_exception_response as _runtime_build_unhandled_exception_response,
)
from .adaptive_runtime.trace_helpers import (
    _init_debug_payloads,
    _truncate_preview,
    _extract_block_trace_fields,
    _build_chunk_trace_item,
    _build_llm_prompts as _runtime_build_llm_prompts,
    _apply_memory_debug_info,
)
from .adaptive_runtime.state_helpers import (
    SDClassificationResult,
    _fallback_state_analysis as _runtime_fallback_state_analysis,
    _fallback_sd_result as _runtime_fallback_sd_result,
    _resolve_path_user_level as _runtime_resolve_path_user_level,
    _classify_parallel as _runtime_classify_parallel,
    _build_state_context as _runtime_build_state_context,
    _compose_state_context as _runtime_compose_state_context,
    _should_use_fast_path as _runtime_should_use_fast_path,
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
)
from .adaptive_runtime.runtime_misc_helpers import (
    _build_start_command_response as _runtime_build_start_command_response,
    _load_runtime_memory_context as _runtime_load_runtime_memory_context,
    _run_bootstrap_and_onboarding_guard as _runtime_run_bootstrap_and_onboarding_guard,
    _run_fast_path_stage as _runtime_run_fast_path_stage,
    _run_generation_and_success_stage as _runtime_run_generation_and_success_stage,
)
from .adaptive_runtime.retrieval_stage_helpers import (
    _run_retrieval_routing_context_stage as _runtime_run_retrieval_routing_context_stage,
)

logger = logging.getLogger(__name__)

PRACTICE_ALLOWED_ROUTES = {"practice", "reflect", "regulate"}
PRACTICE_SKIP_ROUTES = {"contact_hold", "contacthold", "presence", "crisis_hold"}

# Compatibility touchpoint for inventory tests/documentation.
MODE_PROMPT_MAP = _RUNTIME_MODE_PROMPT_MAP




def resolve_mode_prompt(user_state: str, cfg) -> Tuple[Optional[str], Optional[str]]:
    return _runtime_resolve_mode_prompt(user_state, cfg)


def _fallback_sd_result(reason: str = "fallback_on_error") -> SDClassificationResult:
    return _runtime_fallback_sd_result(reason)


def _output_validation_enabled() -> bool:
    return _runtime_output_validation_enabled()


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


def _resolve_path_user_level(_user_level: str) -> UserLevel:
    return _runtime_resolve_path_user_level(_user_level)


async def _classify_parallel(
    user_message: str,
    history_state: List[Dict],
) -> Tuple[StateAnalysis, SDClassificationResult]:
    # Compatibility touchpoint for phase8 runtime test harness monkeypatching.
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


def _should_use_fast_path(query: str, routing_result) -> bool:
    return _runtime_should_use_fast_path(query, routing_result)


def _build_llm_prompts(
    *,
    response_generator,
    query: str,
    blocks,
    conversation_context: str,
    user_level_adapter=None,
    sd_level: Optional[str] = None,
    mode_prompt: str,
    additional_system_context: str,
    mode_prompt_override: Optional[str] = None,
    mode_overrides_sd: bool = False,
):
    """Compatibility export retained for regression contract tests."""
    return _runtime_build_llm_prompts(
        response_generator=response_generator,
        query=query,
        blocks=blocks,
        conversation_context=conversation_context,
        user_level_adapter=user_level_adapter,
        sd_level=str(sd_level or ""),
        mode_prompt=mode_prompt,
        additional_system_context=additional_system_context,
        mode_prompt_override=mode_prompt_override,
        mode_overrides_sd=mode_overrides_sd,
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
    llm_model_name = str(config.LLM_MODEL)
    prompt_stack_enabled = _runtime_prompt_stack_v2_enabled()
    output_validation_enabled = _output_validation_enabled()
    informational_branch_enabled = _runtime_informational_branch_enabled()
    diagnostics_v1_enabled = _runtime_diagnostics_v1_enabled()
    deterministic_route_resolver_enabled = _runtime_deterministic_route_resolver_enabled()
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
    level_adapter = None  # compatibility sentinel: level-based prompting stays disabled
    build_start_command_response_fn = lambda **kwargs: _runtime_build_start_command_response(
        logger=logger,
        **kwargs,
    )
    current_stage = "init"
    try:
        # ================================================================
        # Р­РўРђРџ 1: Р—Р°РіСЂСѓР·РєР° РґР°РЅРЅС‹С… Рё РїР°РјСЏС‚Рё
        # ================================================================
        logger.debug("рџ“љ Р­С‚Р°Рї 1: Р—Р°РіСЂСѓР·РєР° РґР°РЅРЅС‹С… Рё РїР°РјСЏС‚Рё...")
        
        bootstrap = _runtime_run_bootstrap_and_onboarding_guard(
            user_id=user_id,
            user_level=user_level,
            query=query,
            start_time=start_time,
            schedule_summary_task=schedule_summary_task,
            debug_trace=debug_trace,
            debug_info=debug_info,
            load_runtime_memory_context_fn=_runtime_load_runtime_memory_context,
            data_loader=data_loader,
            get_conversation_memory_fn=get_conversation_memory,
            memory_updater=memory_updater,
            config=config,
            detect_phase8_signals_fn=detect_phase8_signals,
            informational_branch_enabled=informational_branch_enabled,
            build_start_command_response_fn=build_start_command_response_fn,
            truncate_preview_fn=_truncate_preview,
            apply_memory_debug_info_fn=_apply_memory_debug_info,
            resolve_path_user_level_fn=_resolve_path_user_level,
        )
        memory = bootstrap["memory"]
        memory_context_bundle = bootstrap["memory_context_bundle"]
        conversation_context = bootstrap["conversation_context"]
        cross_session_context = bootstrap["cross_session_context"]
        memory_trace_metrics = bootstrap["memory_trace_metrics"]
        phase8_signals = bootstrap["phase8_signals"]
        path_level_enum = bootstrap["path_level_enum"]
        start_command_response = bootstrap["start_command_response"]
        _ = level_adapter
        if start_command_response is not None:
            return start_command_response
        
        # ================================================================
        # Р­РўРђРџ 2: РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        # ================================================================
        logger.debug("рџЋЇ Р­С‚Р°Рї 2: РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ...")
        
        current_stage = "state_classifier"
        stage2 = _runtime_run_state_and_pre_routing_pipeline(
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
            fallback_state_analysis_fn=_runtime_fallback_state_analysis,
            fallback_sd_result_fn=_fallback_sd_result,
            resolve_user_stage_fn=resolve_user_stage,
            derive_informational_mode_hint_fn=_runtime_derive_informational_mode_hint,
            resolve_mode_prompt_fn=resolve_mode_prompt,
            logger=logger,
            diagnostics_v1_enabled=diagnostics_v1_enabled,
            deterministic_route_resolver_enabled=deterministic_route_resolver_enabled,
            informational_branch_enabled=informational_branch_enabled,
            diagnostics_classifier=diagnostics_classifier,
            detect_contradiction_fn=detect_contradiction,
            decision_gate_cls=DecisionGate,
            detect_routing_signals_fn=detect_routing_signals,
            should_use_fast_path_fn=_should_use_fast_path,
        )
        state_analysis = stage2["state_analysis"]
        sd_result = stage2["sd_result"]
        user_stage = stage2["user_stage"]
        informational_mode = stage2["informational_mode"]
        mode_prompt_key = stage2["mode_prompt_key"]
        mode_prompt_override = stage2["mode_prompt_override"]
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

        fast_path_stage = _runtime_run_fast_path_stage(
            fast_path_enabled=fast_path_enabled,
            logger=logger,
            pre_routing_result=pre_routing_result,
            debug_trace=debug_trace,
            query=query,
            truncate_preview_fn=_truncate_preview,
            config=config,
            pipeline_stages=pipeline_stages,
            informational_mode=informational_mode,
            memory=memory,
            conversation_context=conversation_context,
            memory_context_bundle=memory_context_bundle,
            diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            informational_branch_enabled=informational_branch_enabled,
            state_analysis=state_analysis,
            contradiction_hint=contradiction_hint,
            cross_session_context=cross_session_context,
            diagnostics_v1=diagnostics_v1,
            response_generator_cls=ResponseGenerator,
            sd_primary=sd_result.primary,
            session_store=session_store,
            user_id=user_id,
            mode_prompt_override=mode_prompt_override,
            prompt_stack_enabled=prompt_stack_enabled,
            prompt_registry=prompt_registry_v2,
            response_formatter_cls=ResponseFormatter,
            include_feedback_prompt=include_feedback_prompt,
            mode_prompt_key=mode_prompt_key,
            memory_trace_metrics=memory_trace_metrics,
            schedule_summary_task=schedule_summary_task,
            start_time=start_time,
            debug_info=debug_info,
            llm_model_name=llm_model_name,
            output_validation_enabled=output_validation_enabled,
        )
        if fast_path_stage is not None:
            return fast_path_stage["result"]

        if debug_trace is not None and debug_trace.get("fast_path") is None:
            debug_trace["fast_path"] = False
        
        # ================================================================
        # Р­РўРђРџ 3: РџРѕРёСЃРє СЂРµР»РµРІР°РЅС‚РЅС‹С… Р±Р»РѕРєРѕРІ
        # ================================================================
        logger.debug("рџ”Ќ Р­С‚Р°Рї 3: РџРѕРёСЃРє Р±Р»РѕРєРѕРІ...")

        current_stage = "retrieval"
        stage3 = _runtime_run_retrieval_routing_context_stage(
            query=query,
            top_k=top_k,
            config=config,
            data_loader=data_loader,
            get_retriever_fn=get_retriever,
            logger=logger,
            debug_trace=debug_trace,
            pipeline_stages=pipeline_stages,
            use_deterministic_router=use_deterministic_router,
            diagnostics_v1=diagnostics_v1,
            pre_routing_result=pre_routing_result,
            voyage_reranker_cls=VoyageReranker,
            detect_routing_signals_fn=detect_routing_signals,
            state_analysis=state_analysis,
            memory=memory,
            conversation_context=conversation_context,
            user_stage=user_stage,
            route_resolver=route_resolver,
            confidence_scorer=confidence_scorer,
            decision_gate=decision_gate,
            informational_branch_enabled=informational_branch_enabled,
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            practice_selector=practice_selector,
            practice_allowed_routes=PRACTICE_ALLOWED_ROUTES,
            practice_skip_routes=PRACTICE_SKIP_ROUTES,
            memory_context_bundle=memory_context_bundle,
            mode_prompt_key=mode_prompt_key,
            route_resolution_count=route_resolution_count,
            start_time=start_time,
            schedule_summary_task=schedule_summary_task,
            debug_info=debug_info,
            session_store=session_store,
            user_id=user_id,
            model_used=llm_model_name,
        )
        current_stage = stage3["current_stage"]
        if stage3["early_response"] is not None:
            return stage3["early_response"]
        hybrid_query = stage3["hybrid_query"]
        initial_retrieved_blocks = stage3["initial_retrieved_blocks"]
        reranked_blocks_for_trace = stage3["reranked_blocks_for_trace"]
        routing_result = stage3["routing_result"]
        block_cap = stage3["block_cap"]
        route_resolution_count = stage3["route_resolution_count"]
        informational_mode = stage3["informational_mode"]
        mode_prompt_key = stage3["mode_prompt_key"]
        mode_prompt_override = stage3["mode_prompt_override"]
        mode_directive = stage3["mode_directive"]
        state_context_mode_prompt = stage3["state_context_mode_prompt"]
        phase8_context_suffix = stage3["phase8_context_suffix"]
        selected_practice = stage3["selected_practice"]
        practice_alternatives = stage3["practice_alternatives"]
        practice_context_suffix = stage3["practice_context_suffix"]
        conversation_context = stage3["conversation_context"]
        adapted_blocks = stage3["adapted_blocks"]
        
        stage4 = _runtime_run_generation_and_success_stage(
            query=query,
            state_analysis=state_analysis,
            routing_result=routing_result,
            diagnostics_v1=diagnostics_v1,
            contradiction_hint=contradiction_hint,
            contradiction_info=contradiction_info,
            cross_session_context=cross_session_context,
            phase8_context_suffix=phase8_context_suffix,
            practice_context_suffix=practice_context_suffix,
            state_context_mode_prompt=state_context_mode_prompt,
            adapted_blocks=adapted_blocks,
            sd_primary=sd_result.primary,
            config=config,
            session_store=session_store,
            user_id=user_id,
            mode_prompt_override=mode_prompt_override,
            informational_mode=informational_mode,
            phase8_signals=phase8_signals,
            correction_protocol_active=correction_protocol_active,
            prompt_stack_enabled=prompt_stack_enabled,
            prompt_registry=prompt_registry_v2,
            mode_directive=mode_directive,
            debug_trace=debug_trace,
            pipeline_stages=pipeline_stages,
            response_generator_cls=ResponseGenerator,
            response_formatter_cls=ResponseFormatter,
            start_time=start_time,
            memory=memory,
            schedule_summary_task=schedule_summary_task,
            debug_info=debug_info,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
            llm_model_name=llm_model_name,
            logger=logger,
            include_path_recommendation=include_path_recommendation,
            include_feedback_prompt=include_feedback_prompt,
            user_level_enum=path_level_enum,
            conversation_context=conversation_context,
            mode_prompt_key=mode_prompt_key,
            route_resolution_count=route_resolution_count,
            selected_practice=selected_practice,
            practice_alternatives=practice_alternatives,
            block_cap=block_cap,
            output_validation_enabled=output_validation_enabled,
            memory_context_bundle=memory_context_bundle,
            memory_trace_metrics=memory_trace_metrics,
            hybrid_query=hybrid_query,
        )
        current_stage = stage4["current_stage"]
        return stage4["result"]
    
    except Exception as e:
        logger.error(f"[ADAPTIVE] unhandled error: {e}", exc_info=True)
        response = _runtime_build_unhandled_exception_response(
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
            llm_model_name=llm_model_name,
        )
        return response
