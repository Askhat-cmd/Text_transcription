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
    _persist_turn_best_effort,
    _persist_turn,
    _save_session_summary_best_effort,
    _build_sources_from_blocks,
    _attach_debug_payload,
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
    _log_context_build,
    _build_retrieval_detail,
    _build_retrieval_debug_details,
    _build_llm_prompts,
    _build_llm_prompt_previews,
    _build_llm_call_trace,
    _update_session_token_metrics,
    _build_memory_context_snapshot,
    _refresh_runtime_memory_snapshot,
    _apply_memory_debug_info,
    _apply_trace_memory_snapshot,
    _finalize_trace_payload,
    _finalize_success_debug_trace,
)
from .adaptive_runtime.state_helpers import (
    SDClassificationResult,
    _fallback_state_analysis as _runtime_fallback_state_analysis,
    _fallback_sd_result as _runtime_fallback_sd_result,
    _resolve_path_user_level as _runtime_resolve_path_user_level,
    _classify_parallel as _runtime_classify_parallel,
    _build_state_context as _runtime_build_state_context,
    _depth_to_phase as _runtime_depth_to_phase,
    _mode_to_direction as _runtime_mode_to_direction,
    _derive_defense as _runtime_derive_defense,
    _build_working_state as _runtime_build_working_state,
    _looks_like_greeting as _runtime_looks_like_greeting,
    _looks_like_name_intro as _runtime_looks_like_name_intro,
    _should_use_fast_path as _runtime_should_use_fast_path,
    _detect_fast_path_reason as _runtime_detect_fast_path_reason,
    _build_fast_path_block as _runtime_build_fast_path_block,
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
from .adaptive_runtime.runtime_misc_helpers import (
    _estimate_cost as _runtime_estimate_cost,
    _sd_runtime_disabled as _runtime_sd_runtime_disabled,
    _build_start_command_response as _runtime_build_start_command_response,
    _load_runtime_memory_context as _runtime_load_runtime_memory_context,
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

        diagnostics_v1 = None
        correction_protocol_active = False
        if use_new_diagnostics_v1:
            diagnostics_v1 = diagnostics_classifier.classify(
                query=query,
                state_analysis=state_analysis,
                informational_mode_hint=informational_mode_hint,
            )
            correction_protocol_active = bool(
                _informational_branch_enabled()
                and phase8_signals is not None
                and phase8_signals.user_correction
            )
            if correction_protocol_active:
                recalibrated = diagnostics_v1.as_dict()
                confidence = dict(recalibrated.get("confidence") or {})
                confidence["interaction_mode"] = min(
                    float(confidence.get("interaction_mode", 0.6) or 0.6),
                    0.6,
                )
                confidence["request_function"] = min(
                    float(confidence.get("request_function", 0.6) or 0.6),
                    0.6,
                )
                recalibrated["confidence"] = confidence
                recalibrated["request_function"] = "validation"
                diagnostics_v1 = diagnostics_classifier.sanitize(recalibrated)
            if debug_trace is not None:
                debug_trace["diagnostics_v1"] = diagnostics_v1.as_dict()
                debug_trace["route_strategy"] = (
                    "deterministic_v1" if use_deterministic_router else "decision_gate_v0"
                )
                debug_trace["user_correction_protocol"] = correction_protocol_active
            if debug_info is not None:
                debug_info["diagnostics_v1"] = diagnostics_v1.as_dict()

        contradiction_info = detect_contradiction(query)
        contradiction_hint = (
            str(contradiction_info.get("suggestion", ""))
            if contradiction_info.get("has_contradiction")
            else ""
        )

        if debug_trace is not None:
            debug_trace["contradiction"] = contradiction_info

        decision_gate = None if use_deterministic_router else DecisionGate()
        pre_routing_result = None
        if use_deterministic_router:
            # Phase 4: one deterministic route per turn; fast path is disabled.
            fast_path_enabled = False
            logger.info("[ROUTING_V1] deterministic resolver enabled; FAST_PATH disabled")
        else:
            pre_routing_signals = detect_routing_signals(query, [], state_analysis, memory=memory)
            pre_routing_signals["contradiction_detected"] = bool(
                contradiction_info.get("has_contradiction", False)
            )
            pre_routing_signals["contradiction_suggestion"] = contradiction_hint
            pre_routing_result = decision_gate.route(pre_routing_signals, user_stage=user_stage)
            fast_path_enabled = _should_use_fast_path(query, pre_routing_result)
            if informational_mode and fast_path_enabled:
                # For true informational route we prefer full retrieval context over compact fast-path.
                fast_path_enabled = False
                logger.info(
                    "[FAST_PATH] disabled for informational route (user_state=%s)",
                    state_analysis.primary_state.value,
                )
            logger.info(
                "[CONFIDENCE] score=%.4f level=%s -> FAST_PATH: %s",
                pre_routing_result.confidence_score,
                pre_routing_result.confidence_level,
                "yes" if fast_path_enabled else "no",
            )

        if fast_path_enabled:
            logger.info(
                "[FAST_PATH] enabled mode=%s reason=%s",
                pre_routing_result.mode,
                pre_routing_result.decision.reason,
            )
            if debug_trace is not None:
                debug_trace["fast_path"] = True
                debug_trace["fast_path_reason"] = _detect_fast_path_reason(query, pre_routing_result)
                debug_trace["recommended_mode"] = pre_routing_result.mode
                debug_trace["route_track"] = getattr(pre_routing_result, "track", "direct")
                debug_trace["route_tone"] = getattr(pre_routing_result, "tone", "minimal")
                debug_trace["routing_result"] = {
                    "mode": pre_routing_result.mode,
                    "track": getattr(pre_routing_result, "track", "direct"),
                    "tone": getattr(pre_routing_result, "tone", "minimal"),
                }
                debug_trace["decision_rule_id"] = pre_routing_result.decision.rule_id
                debug_trace["confidence_score"] = pre_routing_result.confidence_score
                debug_trace["confidence_level"] = pre_routing_result.confidence_level
                debug_trace["mode_reason"] = pre_routing_result.decision.reason
                debug_trace["block_cap"] = 0
                debug_trace["blocks_initial"] = 0
                debug_trace["blocks_after_cap"] = 0
                debug_trace["hybrid_query_preview"] = _truncate_preview(query, 400)
                debug_trace["hybrid_query_len"] = len(query or "")
                debug_trace["hybrid_query_text"] = (
                    query
                    if bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True))
                    else _truncate_preview(query, 1200)
                )

                for stage_name, label in [
                    ("retrieval", "Retrieval"),
                    ("rerank", "Rerank"),
                ]:
                    pipeline_stages.append(
                        {"name": stage_name, "label": label, "duration_ms": 0, "skipped": True}
                    )
            mode_directive = build_mode_directive(
                mode=pre_routing_result.mode,
                confidence_level=pre_routing_result.confidence_level,
                reason=pre_routing_result.decision.reason,
                forbid=pre_routing_result.decision.forbid,
            )
            state_context_mode_prompt = (
                "Р Р•Р–Рњ: INFORMATIONAL\nР”Р°Р№ РїРѕР»РЅС‹Р№ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅС‹Р№ РѕС‚РІРµС‚ РїРѕ С‚РµРјРµ."
                if informational_mode
                else mode_directive.prompt
            )
            refreshed_context, snapshot_payload = _refresh_runtime_memory_snapshot(
                memory=memory,
                diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
                route=getattr(pre_routing_result, "route", None) if pre_routing_result else None,
            )
            if refreshed_context:
                conversation_context = refreshed_context
            if debug_trace is not None and isinstance(snapshot_payload, dict):
                debug_trace["snapshot_v12"] = snapshot_payload
                debug_trace["snapshot_v11"] = snapshot_payload
            _log_context_build(memory, conversation_context, memory_context_bundle)
            if debug_trace is not None:
                debug_trace["context_mode"] = (
                    "summary"
                    if bool(getattr(memory_context_bundle, "summary_used", False))
                    else "full"
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
            fast_phase8_parts: List[str] = []
            if _informational_branch_enabled():
                if phase8_signals is not None and phase8_signals.first_turn:
                    fast_phase8_parts.append(build_first_turn_instruction())
                if phase8_signals is not None and phase8_signals.mixed_query:
                    fast_phase8_parts.append(build_mixed_query_instruction())
                if correction_protocol_active:
                    fast_phase8_parts.append(build_user_correction_instruction())
                if informational_mode:
                    fast_phase8_parts.append(build_informational_guardrail_instruction())
            fast_phase8_suffix = "\n\n".join(part for part in fast_phase8_parts if part.strip())
            if fast_phase8_suffix:
                state_context = f"{state_context}\n\n{fast_phase8_suffix}"
            response_generator = ResponseGenerator()
            prompt_stack_meta: Dict[str, Any] = {"enabled": False}
            system_prompt_override: Optional[str] = None
            if _prompt_stack_v2_enabled():
                prompt_build = prompt_registry_v2.build(
                    query=query,
                    blocks=[fast_block],
                    conversation_context=conversation_context,
                    additional_system_context=state_context,
                    route=getattr(pre_routing_result, "route", "") if pre_routing_result else "",
                    mode=pre_routing_result.mode if pre_routing_result else "PRESENCE",
                    diagnostics=diagnostics_v1.as_dict() if diagnostics_v1 else None,
                    mode_prompt_override=mode_prompt_override if informational_mode else None,
                    first_turn=bool(phase8_signals.first_turn) if phase8_signals else False,
                    mixed_query_bridge=bool(phase8_signals.mixed_query) if phase8_signals else False,
                    user_correction_protocol=bool(correction_protocol_active),
                )
                system_prompt_override = prompt_build.system_prompt
                prompt_stack_meta = {"enabled": True, **prompt_build.as_dict()}
            llm_system_preview = ""
            llm_user_preview = ""
            system_blob_id = None
            user_blob_id = None
            if debug_trace is not None:
                if system_prompt_override is not None:
                    full_system_prompt = system_prompt_override
                    full_user_prompt = response_generator.answerer.build_context_prompt(
                        [fast_block],
                        query,
                        conversation_history=conversation_context,
                    )
                else:
                    full_system_prompt, full_user_prompt = _build_llm_prompts(
                        response_generator=response_generator,
                        query=query,
                        blocks=[fast_block],
                        conversation_context=conversation_context,
                        sd_level=sd_result.primary,
                        mode_prompt=mode_directive.prompt,
                        additional_system_context=state_context,
                        mode_prompt_override=mode_prompt_override,
                        mode_overrides_sd=informational_mode,
                    )
                llm_system_preview = _truncate_preview(full_system_prompt, 300)
                llm_user_preview = _truncate_preview(full_user_prompt, 300)
                debug_trace["prompt_stack_v2"] = prompt_stack_meta

            llm_started = datetime.now()
            llm_result = {}
            llm_error = None
            try:
                current_stage = "llm"
                llm_result = response_generator.generate(
                    query,
                    [fast_block],
                    conversation_context=conversation_context,
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    forbid=pre_routing_result.decision.forbid,
                    additional_system_context=state_context,
                    sd_level=sd_result.primary,
                    model=config.LLM_MODEL,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.get_mode_max_tokens(pre_routing_result.mode),
                    system_prompt_blob_id=system_blob_id,
                    user_prompt_blob_id=user_blob_id,
                    session_store=session_store,
                    session_id=user_id,
                    mode_prompt_override=mode_prompt_override,
                    mode_overrides_sd=informational_mode,
                    system_prompt_override=system_prompt_override,
                )
            except Exception as llm_exc:
                llm_error = str(llm_exc)
                raise
            finally:
                if debug_trace is not None:
                    call_info = (
                        llm_result.get("llm_call_info")
                        if isinstance(llm_result, dict) and isinstance(llm_result.get("llm_call_info"), dict)
                        else {}
                    )
                    debug_trace["system_prompt_blob_id"] = call_info.get("system_prompt_blob_id")
                    debug_trace["user_prompt_blob_id"] = call_info.get("user_prompt_blob_id")
                    pipeline_stages.append(
                        {
                            "name": "llm",
                            "label": "LLM",
                            "duration_ms": int((datetime.now() - llm_started).total_seconds() * 1000),
                            "skipped": False,
                        }
                    )
                    debug_trace["llm_calls"].append(
                        _build_llm_call_trace(
                            llm_result=llm_result if isinstance(llm_result, dict) else {},
                            step="answer",
                            system_prompt_preview=llm_system_preview,
                            user_prompt_preview=llm_user_preview,
                            fallback_error=llm_error,
                            duration_ms=int((datetime.now() - llm_started).total_seconds() * 1000),
                            system_prompt_blob_id=system_blob_id,
                            user_prompt_blob_id=user_blob_id,
                        )
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
                retry_query = f"{query}\n\n[VALIDATION_HINT]\n{hint}"
                retry_result = response_generator.generate(
                    retry_query,
                    [fast_block],
                    conversation_context=conversation_context,
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    forbid=pre_routing_result.decision.forbid,
                    additional_system_context=state_context,
                    sd_level=sd_result.primary,
                    model=config.LLM_MODEL,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.get_mode_max_tokens(pre_routing_result.mode),
                    session_store=session_store,
                    session_id=user_id,
                    mode_prompt_override=mode_prompt_override,
                    mode_overrides_sd=informational_mode,
                    system_prompt_override=system_prompt_override,
                )
                retry_result["answer"] = formatter.format_answer(
                    str(retry_result.get("answer") or ""),
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    user_message=query,
                    informational_mode=informational_mode,
                )
                return retry_result

            answer, validation_meta, validation_retry_result = _apply_output_validation_policy(
                answer=answer,
                query=query,
                route=getattr(pre_routing_result, "route", ""),
                mode=pre_routing_result.mode,
                generate_retry_fn=_retry_fast_validation,
            )
            if isinstance(validation_retry_result, dict):
                llm_result["validation_retry_llm"] = validation_retry_result.get("llm_call_info")
            if debug_trace is not None:
                debug_trace["output_validation"] = validation_meta
                pipeline_stages.append(
                    {"name": "format", "label": "Formatting", "duration_ms": 0, "skipped": False}
                )
                pipeline_stages.append(
                    {"name": "validate", "label": "Validation", "duration_ms": 0, "skipped": False}
                )

            try:
                memory.set_working_state(
                    _build_working_state(
                        state_analysis=state_analysis,
                        routing_result=pre_routing_result,
                        memory=memory,
                    )
                )
            except Exception as exc:
                logger.warning(f"[FAST_PATH] working_state update failed: {exc}")

            tokens_prompt = llm_result.get("tokens_prompt") if isinstance(llm_result, dict) else None
            tokens_completion = llm_result.get("tokens_completion") if isinstance(llm_result, dict) else None
            tokens_total = llm_result.get("tokens_total") if isinstance(llm_result, dict) else None
            model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else config.LLM_MODEL
            session_metrics = _update_session_token_metrics(
                memory=memory,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                model_name=str(model_used),
            )

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
            _attach_debug_payload(
                result=result,
                debug_info=debug_info,
                memory=memory,
                elapsed_time=elapsed_time,
                llm_result=llm_result,
            )
            if debug_trace is not None:
                debug_trace = _finalize_success_debug_trace(
                    debug_trace,
                    elapsed_time=elapsed_time,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    tokens_total=tokens_total,
                    session_metrics=session_metrics,
                    memory=memory,
                    memory_trace_metrics=memory_trace_metrics,
                    start_time=start_time,
                    session_store=session_store,
                    user_id=user_id,
                    pipeline_stages=pipeline_stages,
                    model_used=str(model_used),
                    estimate_cost_fn=_estimate_cost,
                    compute_anomalies_fn=_compute_anomalies,
                    attach_trace_schema_fn=attach_trace_schema_status,
                    build_state_trajectory_fn=_build_state_trajectory,
                    store_blob_fn=_store_blob,
                    strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
                    aggregate_from_llm_calls=False,
                    include_summary_pending=True,
                )
                result["debug_trace"] = debug_trace

            result["metadata"] = _strip_legacy_runtime_metadata(result.get("metadata", {}))
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

        retrieval_degraded_reason = None
        try:
            retriever = get_retriever()
        except Exception as exc:
            logger.warning("[RETRIEVAL] get_retriever failed, degraded mode enabled: %s", exc)
            retriever = None
            retrieval_degraded_reason = "retriever_init_failed"
        current_stage = "retrieval"

        author_id_filter = None
        author_map = {}
        if config.AUTHOR_BLEND_MODE in {"single", "blend"}:
            for block in data_loader.get_all_blocks():
                if block.author and block.author_id:
                    author_map[block.author] = block.author_id

            if author_map:
                from .semantic_analyzer import detect_author_intent
                author_name = detect_author_intent(query, list(author_map.keys()))
                if author_name:
                    author_id_filter = author_map.get(author_name)
                    logger.info("[RETRIEVAL] author intent detected: %s (%s)", author_name, author_id_filter)


        if retriever is None:
            raw_retrieved_blocks = []
            stage = {"name": "retrieval", "label": "Retrieval (degraded)", "duration_ms": 0, "skipped": True}
        else:
            try:
                if config.AUTHOR_BLEND_MODE == "blend" and author_map:
                    raw_retrieved_blocks = []
                    for author_id in author_map.values():
                        raw_retrieved_blocks.extend(
                            retriever.retrieve(
                                hybrid_query,
                                top_k=3,
                                author_id=author_id,
                            )
                        )
                    stage = {"name": "retrieval", "label": "Retrieval (blend)", "duration_ms": 0, "skipped": False}
                else:
                    raw_retrieved_blocks, stage = _timed(
                        "retrieval",
                        "Retrieval",
                        retriever.retrieve,
                        hybrid_query,
                        top_k=top_k,
                        author_id=author_id_filter,
                    )
            except Exception as exc:
                logger.warning("[RETRIEVAL] retrieve failed, degraded mode enabled: %s", exc)
                raw_retrieved_blocks = []
                retrieval_degraded_reason = "retrieval_failed"
                stage = {"name": "retrieval", "label": "Retrieval (degraded)", "duration_ms": 0, "skipped": True}

        if debug_trace is not None:
            pipeline_stages.append(stage)
            if retrieval_degraded_reason:
                debug_trace["retrieval_degraded_reason"] = retrieval_degraded_reason
        
        # Р”РµРґСѓРїР»РёРєР°С†РёСЏ Р±Р»РѕРєРѕРІ РїРѕ block_id РґРѕ SD filter
        seen_ids = set()
        deduped_blocks = []
        for block, score in raw_retrieved_blocks:
            if block.block_id not in seen_ids:
                seen_ids.add(block.block_id)
                deduped_blocks.append((block, score))
        
        if len(deduped_blocks) < len(raw_retrieved_blocks):
            logger.info(
                f"[RETRIEVAL] Deduped {len(raw_retrieved_blocks) - len(deduped_blocks)} duplicate blocks "
                f"({len(raw_retrieved_blocks)} -> {len(deduped_blocks)})"
            )
        raw_retrieved_blocks = deduped_blocks

        progressive_rag = get_progressive_rag(str(config.BOT_DB_PATH))
        try:
            raw_retrieved_blocks = progressive_rag.rerank_by_weights(raw_retrieved_blocks)
            if debug_trace is not None:
                debug_trace["progressive_rag_enabled"] = True
        except Exception as exc:
            logger.warning(f"[PROGRESSIVE_RAG] rerank_by_weights failed: {exc}")
            if debug_trace is not None:
                debug_trace["progressive_rag_enabled"] = False
                debug_trace["progressive_rag_error"] = str(exc)
        
        _log_retrieval_pairs("Initial retrieval", raw_retrieved_blocks, limit=10)
        retrieved_blocks = list(raw_retrieved_blocks)
        initial_retrieved_blocks = list(raw_retrieved_blocks)
        if use_deterministic_router and diagnostics_v1 is not None:
            rerank_mode = (
                "CLARIFICATION" if diagnostics_v1.interaction_mode == "informational" else "PRESENCE"
            )
            rerank_confidence = (
                float(diagnostics_v1.confidence.interaction_mode)
                + float(diagnostics_v1.confidence.nervous_system_state)
                + float(diagnostics_v1.confidence.request_function)
            ) / 3.0
        else:
            # Wave 4 migration step: for rerank gating reuse already-computed pre-routing result.
            rerank_mode = pre_routing_result.mode if pre_routing_result is not None else "PRESENCE"
            rerank_confidence = (
                float(pre_routing_result.confidence_score)
                if pre_routing_result is not None
                else 0.5
            )
        conditional_reranker = feature_flags.enabled("ENABLE_CONDITIONAL_RERANKER")
        rerank_flags = {
            "legacy_always_on": bool(
                config.VOYAGE_ENABLED and (not conditional_reranker or not config.RERANKER_ENABLED)
            ),
            "RERANKER_ENABLED": bool(config.RERANKER_ENABLED and conditional_reranker),
            "RERANKER_CONFIDENCE_THRESHOLD": float(config.RERANKER_CONFIDENCE_THRESHOLD),
            "RERANKER_MODE_WHITELIST": str(config.RERANKER_MODE_WHITELIST),
            "RERANKER_BLOCK_THRESHOLD": int(config.RERANKER_BLOCK_THRESHOLD),
        }
        should_run_rerank, rerank_reason = should_rerank(
            confidence_score=rerank_confidence,
            routing_mode=rerank_mode,
            retrieved_block_count=len(retrieved_blocks),
            flags=rerank_flags,
        )
        rerank_k = min(len(retrieved_blocks), max(1, min(top_k, config.VOYAGE_TOP_K)))
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
        state_context_mode_prompt = (
            "Р Р•Р–Рњ: INFORMATIONAL\nР”Р°Р№ РїРѕР»РЅС‹Р№ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅС‹Р№ РѕС‚РІРµС‚ РїРѕ С‚РµРјРµ."
            if informational_mode
            else mode_directive.prompt
        )
        phase8_context_parts: List[str] = []
        if _informational_branch_enabled():
            if phase8_signals is not None and phase8_signals.first_turn:
                phase8_context_parts.append(build_first_turn_instruction())
            if phase8_signals is not None and phase8_signals.mixed_query:
                phase8_context_parts.append(build_mixed_query_instruction())
            if correction_protocol_active:
                phase8_context_parts.append(build_user_correction_instruction())
            if informational_mode:
                phase8_context_parts.append(build_informational_guardrail_instruction())
        phase8_context_suffix = "\n\n".join(part for part in phase8_context_parts if part.strip())
        selected_practice: Optional[Dict[str, Any]] = None
        practice_alternatives: List[Dict[str, Any]] = []
        practice_context_suffix = ""
        resolved_route = str(getattr(routing_result, "route", "") or "").strip().lower()
        practice_routing_enabled = (
            resolved_route in PRACTICE_ALLOWED_ROUTES
            and resolved_route not in PRACTICE_SKIP_ROUTES
        )
        if practice_routing_enabled:
            try:
                diagnostics_payload = diagnostics_v1.as_dict() if diagnostics_v1 else {}
                selection = practice_selector.select(
                    route=resolved_route,
                    nervous_system_state=str(
                        diagnostics_payload.get("nervous_system_state")
                        or "window"
                    ),
                    request_function=str(
                        diagnostics_payload.get("request_function")
                        or "understand"
                    ),
                    core_theme=str(diagnostics_payload.get("core_theme") or query),
                    last_practice_channel=str(memory.metadata.get("last_practice_channel") or ""),
                    safety_flags=[],
                )
                if selection.primary is not None:
                    selected_practice = selection.primary.as_dict()
                    practice_alternatives = [item.as_dict() for item in selection.alternatives]
                    memory.metadata["last_practice_channel"] = selection.primary.entry.channel
                    practice_context_suffix = (
                        "\n\nPRACTICE_SUGGESTION:\n"
                        f"- title: {selection.primary.entry.title}\n"
                        f"- channel: {selection.primary.entry.channel}\n"
                        f"- instruction: {selection.primary.entry.instruction}\n"
                        f"- micro_tuning: {selection.primary.entry.micro_tuning}\n"
                        f"- closure: {selection.primary.entry.closure}\n"
                        f"- time_limit_minutes: {selection.primary.entry.time_limit_minutes}"
                    )
            except Exception as exc:
                logger.warning("[PRACTICE] selection skipped: %s", exc)
        elif resolved_route in PRACTICE_SKIP_ROUTES:
            logger.info("[PRACTICE] skipped by route policy for route=%s", resolved_route)
        else:
            logger.info("[PRACTICE] skipped for route=%s", resolved_route or "unknown")

        if debug_trace is not None:
            debug_trace["recommended_mode"] = routing_result.mode
            debug_trace["route_track"] = getattr(routing_result, "track", "direct")
            debug_trace["route_tone"] = getattr(routing_result, "tone", "minimal")
            debug_trace["routing_result"] = {
                "mode": routing_result.mode,
                "track": getattr(routing_result, "track", "direct"),
                "tone": getattr(routing_result, "tone", "minimal"),
            }
            debug_trace["resolved_route"] = getattr(routing_result, "route", None)
            debug_trace["decision_rule_id"] = routing_result.decision.rule_id
            debug_trace["confidence_score"] = routing_result.confidence_score
            debug_trace["confidence_level"] = routing_result.confidence_level
            debug_trace["mode_reason"] = mode_directive.reason
            debug_trace["block_cap"] = block_cap
            debug_trace["blocks_initial"] = len(initial_retrieved_blocks)
            debug_trace["hybrid_query_preview"] = _truncate_preview(hybrid_query, 400)
            debug_trace["hybrid_query_len"] = len(hybrid_query)
            debug_trace["hybrid_query_text"] = (
                hybrid_query
                if bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True))
                else _truncate_preview(hybrid_query, 1200)
            )
            debug_trace["rerank_should_run"] = bool(should_run_rerank)
            debug_trace["rerank_reason"] = rerank_reason
            debug_trace["rerank_applied"] = bool(rerank_applied)
            debug_trace["route_resolution_count"] = route_resolution_count
            debug_trace["informational_mode"] = informational_mode
            debug_trace["applied_mode_prompt"] = mode_prompt_key if informational_mode else None
            debug_trace["phase8_context_suffix"] = phase8_context_suffix
            debug_trace["user_correction_protocol"] = correction_protocol_active
            debug_trace["selected_practice"] = selected_practice
            debug_trace["practice_alternatives"] = practice_alternatives

        refreshed_context, snapshot_payload = _refresh_runtime_memory_snapshot(
            memory=memory,
            diagnostics_payload=diagnostics_v1.as_dict() if diagnostics_v1 else None,
            route=getattr(routing_result, "route", None),
        )
        if refreshed_context:
            conversation_context = refreshed_context
        if debug_trace is not None and isinstance(snapshot_payload, dict):
            debug_trace["snapshot_v12"] = snapshot_payload
            debug_trace["snapshot_v11"] = snapshot_payload
        _log_context_build(memory, conversation_context, memory_context_bundle)
        if debug_trace is not None:
            debug_trace["context_mode"] = (
                "summary"
                if bool(getattr(memory_context_bundle, "summary_used", False))
                else "full"
            )

        if not retrieved_blocks:
            response = _build_partial_response(
                "Рљ СЃРѕР¶Р°Р»РµРЅРёСЋ, СЂРµР»РµРІР°РЅС‚РЅС‹Р№ РјР°С‚РµСЂРёР°Р» РЅРµ РЅР°Р№РґРµРЅ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРµСЂРµС„РѕСЂРјСѓР»РёСЂРѕРІР°С‚СЊ РІРѕРїСЂРѕСЃ.",
                state_analysis,
                memory,
                start_time,
                query
            )
            try:
                memory.set_working_state(
                    _build_working_state(
                        state_analysis=state_analysis,
                        routing_result=routing_result,
                        memory=memory,
                    )
                )
            except Exception as exc:
                logger.warning(f"[ADAPTIVE] working_state update failed (partial): {exc}")
            _persist_turn(
                memory=memory,
                user_input=query,
                bot_response=response.get("answer", ""),
                user_state=state_analysis.primary_state.value if state_analysis else None,
                blocks_used=0,
                concepts=[],
                schedule_summary_task=schedule_summary_task,
            )
            if debug_info is not None:
                debug_info["memory_summary"] = memory.get_summary()
                debug_info["total_time"] = (datetime.now() - start_time).total_seconds()
                response["debug"] = debug_info
            if debug_trace is not None:
                chunks_retrieved, chunks_after_rerank = _build_chunk_trace_lists_after_rerank(
                    initial_retrieved=initial_retrieved_blocks,
                    reranked=reranked_blocks_for_trace,
                )
                debug_trace["chunks_retrieved"] = chunks_retrieved
                debug_trace["chunks_after_filter"] = chunks_after_rerank
                debug_trace["blocks_after_cap"] = 0
                pipeline_stages.append(
                    {"name": "llm", "label": "LLM", "duration_ms": 0, "skipped": True}
                )
                pipeline_stages.append(
                    {"name": "format", "label": "Р¤РѕСЂРјР°С‚РёСЂРѕРІР°РЅРёРµ", "duration_ms": 0, "skipped": True}
                )
                _apply_trace_memory_snapshot(
                    debug_trace,
                    memory=memory,
                    start_time=start_time,
                    session_store=session_store,
                    user_id=user_id,
                    build_state_trajectory_fn=_build_state_trajectory,
                    store_blob_fn=_store_blob,
                )
                debug_trace["estimated_cost_usd"] = _estimate_cost(
                    debug_trace.get("llm_calls", []),
                    str(config.LLM_MODEL),
                )
                debug_trace = _finalize_trace_payload(
                    debug_trace,
                    pipeline_stages=pipeline_stages,
                    compute_anomalies_fn=_compute_anomalies,
                    attach_trace_schema_fn=attach_trace_schema_status,
                )
                response["debug_trace"] = debug_trace
            return response
        
        blocks = [block for block, score in retrieved_blocks]
        adapted_blocks = list(blocks)

        if not adapted_blocks:
            adapted_blocks = blocks[:3]  # fallback
        if debug_trace is not None:
            debug_trace["blocks_after_cap"] = len(adapted_blocks)

        if routing_signals.get("positive_feedback_signal"):
            boosted_ids: List[str] = []
            for block in adapted_blocks[:3]:
                block_id = str(getattr(block, "block_id", "")).strip()
                if not block_id:
                    continue
                progressive_rag.record_positive_feedback(block_id)
                boosted_ids.append(block_id)
            if boosted_ids:
                logger.info("[PROGRESSIVE_RAG] positive feedback -> boosted blocks: %s", boosted_ids)
            if debug_trace is not None:
                debug_trace["progressive_rag_feedback_blocks"] = boosted_ids
        
        if debug_info is not None:
            debug_info["blocks_found"] = len(retrieved_blocks)
            debug_info["blocks_after_filter"] = len(adapted_blocks)
            debug_info["hybrid_query"] = hybrid_query
            debug_info["retrieval_details"] = _build_retrieval_debug_details(
                initial_retrieved_blocks=initial_retrieved_blocks,
                reranked_blocks_for_trace=reranked_blocks_for_trace,
                capped_retrieved_blocks=capped_retrieved_blocks,
                adapted_blocks=adapted_blocks,
                build_retrieval_detail_fn=_build_retrieval_detail,
            )
            debug_info["voyage_rerank"] = {
                "enabled": bool(
                    config.VOYAGE_ENABLED
                    or (feature_flags.enabled("ENABLE_CONDITIONAL_RERANKER") and config.RERANKER_ENABLED)
                ),
                "top_k": rerank_k,
                "should_run": bool(should_run_rerank),
                "reason": rerank_reason,
                "applied": bool(rerank_applied),
                "confidence_block_cap": block_cap,
            }
            debug_info["routing"] = {
                "mode": routing_result.mode,
                "track": getattr(routing_result, "track", "direct"),
                "tone": getattr(routing_result, "tone", "minimal"),
                "route": getattr(routing_result, "route", None),
                "rule_id": routing_result.decision.rule_id,
                "reason": routing_result.decision.reason,
                "confidence_score": routing_result.confidence_score,
                "confidence_level": routing_result.confidence_level,
                "route_resolution_count": route_resolution_count,
            }
        if debug_trace is not None:
            chunks_retrieved, chunks_after_rerank = _build_chunk_trace_lists_after_rerank(
                initial_retrieved=initial_retrieved_blocks,
                reranked=reranked_blocks_for_trace,
            )
            debug_trace["chunks_retrieved"] = chunks_retrieved
            debug_trace["chunks_after_filter"] = chunks_after_rerank
        
        # ================================================================
        # Р­РўРђРџ 4: Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р° СЃ РєРѕРЅС‚РµРєСЃС‚РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ
        # ================================================================
        logger.debug("рџ¤– Р­С‚Р°Рї 4: Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р°...")
        
        # Р”РѕР±Р°РІРёС‚СЊ РєРѕРЅС‚РµРєСЃС‚ СЃРѕСЃС‚РѕСЏРЅРёСЏ
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
        if phase8_context_suffix:
            state_context = f"{state_context}\n\n{phase8_context_suffix}"
        if practice_context_suffix:
            state_context = f"{state_context}{practice_context_suffix}"

        # Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚Р° (СЃ СѓС‡С‘С‚РѕРј РёСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіР°)
        response_generator = ResponseGenerator()
        prompt_stack_meta: Dict[str, Any] = {"enabled": False}
        system_prompt_override: Optional[str] = None
        if _prompt_stack_v2_enabled():
            prompt_build = prompt_registry_v2.build(
                query=query,
                blocks=adapted_blocks,
                conversation_context=conversation_context,
                additional_system_context=state_context,
                route=getattr(routing_result, "route", ""),
                mode=routing_result.mode,
                diagnostics=diagnostics_v1.as_dict() if diagnostics_v1 else None,
                mode_prompt_override=mode_prompt_override if informational_mode else None,
                first_turn=bool(phase8_signals.first_turn) if phase8_signals else False,
                mixed_query_bridge=bool(phase8_signals.mixed_query) if phase8_signals else False,
                user_correction_protocol=bool(correction_protocol_active),
            )
            system_prompt_override = prompt_build.system_prompt
            prompt_stack_meta = {"enabled": True, **prompt_build.as_dict()}
        llm_system_preview = ""
        llm_user_preview = ""
        system_blob_id = None
        user_blob_id = None
        if debug_trace is not None:
            if system_prompt_override is not None:
                full_system_prompt = system_prompt_override
                full_user_prompt = response_generator.answerer.build_context_prompt(
                    adapted_blocks,
                    query,
                    conversation_history=conversation_context,
                )
            else:
                full_system_prompt, full_user_prompt = _build_llm_prompts(
                    response_generator=response_generator,
                    query=query,
                    blocks=adapted_blocks,
                    conversation_context=conversation_context,
                    sd_level=sd_result.primary,
                    mode_prompt=mode_directive.prompt,
                    additional_system_context=state_context,
                    mode_prompt_override=mode_prompt_override,
                    mode_overrides_sd=informational_mode,
                )
            llm_system_preview = _truncate_preview(full_system_prompt, 300)
            llm_user_preview = _truncate_preview(full_user_prompt, 300)
            debug_trace["prompt_stack_v2"] = prompt_stack_meta

        llm_started = datetime.now()
        llm_result = {}
        llm_error = None
        try:
            current_stage = "llm"
            llm_result = response_generator.generate(
                query,
                adapted_blocks,
                conversation_context=conversation_context,
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                forbid=routing_result.decision.forbid,
                additional_system_context=state_context,
                sd_level=sd_result.primary,
                model=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.get_mode_max_tokens(routing_result.mode),
                system_prompt_blob_id=system_blob_id,
                user_prompt_blob_id=user_blob_id,
                session_store=session_store,
                session_id=user_id,
                mode_prompt_override=mode_prompt_override,
                mode_overrides_sd=informational_mode,
                system_prompt_override=system_prompt_override,
            )
        except Exception as llm_exc:
            llm_error = str(llm_exc)
            raise
        finally:
            if debug_trace is not None:
                call_info = (
                    llm_result.get("llm_call_info")
                    if isinstance(llm_result, dict) and isinstance(llm_result.get("llm_call_info"), dict)
                    else {}
                )
                debug_trace["system_prompt_blob_id"] = call_info.get("system_prompt_blob_id")
                debug_trace["user_prompt_blob_id"] = call_info.get("user_prompt_blob_id")
                pipeline_stages.append(
                    {
                        "name": "llm",
                        "label": "LLM",
                        "duration_ms": int((datetime.now() - llm_started).total_seconds() * 1000),
                        "skipped": False,
                    }
                )
                debug_trace["llm_calls"].append(
                    _build_llm_call_trace(
                        llm_result=llm_result if isinstance(llm_result, dict) else {},
                        step="answer",
                        system_prompt_preview=llm_system_preview,
                        user_prompt_preview=llm_user_preview,
                        fallback_error=llm_error,
                        duration_ms=int((datetime.now() - llm_started).total_seconds() * 1000),
                        system_prompt_blob_id=system_blob_id,
                        user_prompt_blob_id=user_blob_id,
                    )
                )
        
        if llm_result.get("error") and llm_result["error"] not in ["no_blocks"]:
            logger.error(f"[ADAPTIVE] LLM error: {llm_result['error']}")
            response = _build_error_response(
                f"РћС€РёР±РєР° РїСЂРё РіРµРЅРµСЂР°С†РёРё РѕС‚РІРµС‚Р°: {llm_result['error']}",
                state_analysis,
                start_time
            )
            _persist_turn_best_effort(
                memory=memory,
                user_input=query,
                bot_response=response.get("answer", ""),
                user_state=state_analysis.primary_state.value if state_analysis else None,
                blocks_used=0,
                concepts=[],
                schedule_summary_task=schedule_summary_task,
            )
            if debug_info is not None:
                debug_info["memory_summary"] = memory.get_summary()
                debug_info["total_time"] = (datetime.now() - start_time).total_seconds()
                response["debug"] = debug_info
            if debug_trace is not None:
                chunks_retrieved, chunks_after_rerank = _build_chunk_trace_lists_after_rerank(
                    initial_retrieved=initial_retrieved_blocks,
                    reranked=reranked_blocks_for_trace,
                )
                debug_trace["chunks_retrieved"] = chunks_retrieved
                debug_trace["chunks_after_filter"] = chunks_after_rerank
                _apply_trace_memory_snapshot(
                    debug_trace,
                    memory=memory,
                    start_time=start_time,
                    session_store=session_store,
                    user_id=user_id,
                    build_state_trajectory_fn=_build_state_trajectory,
                    store_blob_fn=_store_blob,
                )
                debug_trace["estimated_cost_usd"] = _estimate_cost(
                    debug_trace.get("llm_calls", []),
                    str(config.LLM_MODEL),
                )
                debug_trace = _finalize_trace_payload(
                    debug_trace,
                    pipeline_stages=pipeline_stages,
                    compute_anomalies_fn=_compute_anomalies,
                    attach_trace_schema_fn=attach_trace_schema_status,
                )
                response["debug_trace"] = debug_trace
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
            retry_query = f"{query}\n\n[VALIDATION_HINT]\n{hint}"
            retry_result = response_generator.generate(
                retry_query,
                adapted_blocks,
                conversation_context=conversation_context,
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                forbid=routing_result.decision.forbid,
                additional_system_context=state_context,
                sd_level=sd_result.primary,
                model=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.get_mode_max_tokens(routing_result.mode),
                session_store=session_store,
                session_id=user_id,
                mode_prompt_override=mode_prompt_override,
                mode_overrides_sd=informational_mode,
                system_prompt_override=system_prompt_override,
            )
            retry_result["answer"] = formatter.format_answer(
                str(retry_result.get("answer") or ""),
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                user_message=query,
                informational_mode=informational_mode,
            )
            return retry_result

        answer, validation_meta, validation_retry_result = _apply_output_validation_policy(
            answer=answer,
            query=query,
            route=getattr(routing_result, "route", ""),
            mode=routing_result.mode,
            generate_retry_fn=_retry_validation,
        )
        if isinstance(validation_retry_result, dict):
            llm_result["validation_retry_llm"] = validation_retry_result.get("llm_call_info")
            retry_call_info = validation_retry_result.get("llm_call_info")
            if debug_trace is not None and isinstance(retry_call_info, dict):
                debug_trace.setdefault("llm_calls", []).append(
                    {
                        "step": "answer_retry",
                        "model": retry_call_info.get("model", config.LLM_MODEL),
                        "system_prompt_preview": retry_call_info.get("system_prompt_preview"),
                        "user_prompt_preview": retry_call_info.get("user_prompt_preview"),
                        "response_preview": retry_call_info.get("response_preview"),
                        "tokens_prompt": retry_call_info.get("tokens_prompt"),
                        "tokens_completion": retry_call_info.get("tokens_completion"),
                        "tokens_total": retry_call_info.get("tokens_total"),
                        "duration_ms": retry_call_info.get("duration_ms"),
                        "system_prompt_blob_id": retry_call_info.get("system_prompt_blob_id"),
                        "user_prompt_blob_id": retry_call_info.get("user_prompt_blob_id"),
                        "memory_snapshot_blob_id": None,
                        "blob_error": retry_call_info.get("blob_error"),
                    }
                )
        if debug_trace is not None:
            debug_trace["output_validation"] = validation_meta
            pipeline_stages.append(
                {"name": "format", "label": "Formatting", "duration_ms": 0, "skipped": False}
            )
            pipeline_stages.append(
                {"name": "validate", "label": "Validation", "duration_ms": 0, "skipped": False}
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
        should_build_path = (
            include_path_recommendation
            and state_analysis.primary_state != UserState.INTEGRATED
            and route_name not in path_builder_blocked_routes
        )
        if should_build_path:
            try:
                personal_path = path_builder.build_path(
                    user_id=user_id,
                    state_analysis=state_analysis,
                    user_level=path_level_enum,
                    memory=memory
                )
                
                path_recommendation = {
                    "current_state": personal_path.current_state.value,
                    "target_state": personal_path.target_state.value,
                    "key_focus": personal_path.key_focus,
                    "steps_count": len(personal_path.path_steps),
                    "total_duration_weeks": personal_path.total_duration_weeks,
                    "adaptation_notes": personal_path.adaptation_notes,
                    "first_step": {
                        "title": personal_path.path_steps[0].title if personal_path.path_steps else "",
                        "duration_weeks": personal_path.path_steps[0].duration_weeks if personal_path.path_steps else 0,
                        "practices": personal_path.path_steps[0].practices[:3] if personal_path.path_steps else []
                    } if personal_path.path_steps else None
                }
            except Exception as e:
                logger.warning(f"вљ пёЏ РћС€РёР±РєР° РїРѕСЃС‚СЂРѕРµРЅРёСЏ РїСѓС‚Рё: {e}")
                path_recommendation = None
        
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
        
        try:
            memory.set_working_state(
                _build_working_state(
                    state_analysis=state_analysis,
                    routing_result=routing_result,
                    memory=memory,
                )
            )
        except Exception as exc:
            logger.warning(f"[ADAPTIVE] working_state update failed: {exc}")

        tokens_prompt = llm_result.get("tokens_prompt") if isinstance(llm_result, dict) else None
        tokens_completion = llm_result.get("tokens_completion") if isinstance(llm_result, dict) else None
        tokens_total = llm_result.get("tokens_total") if isinstance(llm_result, dict) else None
        model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else config.LLM_MODEL
        session_metrics = _update_session_token_metrics(
            memory=memory,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            model_name=str(model_used),
        )

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

        result["metadata"] = _strip_legacy_runtime_metadata(result.get("metadata", {}))
        
        _attach_debug_payload(
            result=result,
            debug_info=debug_info,
            memory=memory,
            elapsed_time=elapsed_time,
            llm_result=llm_result,
            retrieval_details=(debug_info or {}).get("retrieval_details", {}),
            sources=sources,
        )
        if debug_trace is not None:
            debug_trace = _finalize_success_debug_trace(
                debug_trace,
                elapsed_time=elapsed_time,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                session_metrics=session_metrics,
                memory=memory,
                memory_trace_metrics=memory_trace_metrics,
                start_time=start_time,
                session_store=session_store,
                user_id=user_id,
                pipeline_stages=pipeline_stages,
                model_used=str(model_used),
                estimate_cost_fn=_estimate_cost,
                compute_anomalies_fn=_compute_anomalies,
                attach_trace_schema_fn=attach_trace_schema_status,
                build_state_trajectory_fn=_build_state_trajectory,
                store_blob_fn=_store_blob,
                strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
                aggregate_from_llm_calls=True,
                include_summary_pending=True,
            )
            result["debug_trace"] = debug_trace
        
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
                _apply_trace_memory_snapshot(
                    debug_trace,
                    memory=memory,
                    start_time=start_time,
                    session_store=session_store,
                    user_id=user_id,
                    build_state_trajectory_fn=_build_state_trajectory,
                    store_blob_fn=_store_blob,
                    include_total_duration=False,
                )
            except Exception:
                pass
            debug_trace = _finalize_trace_payload(
                debug_trace,
                pipeline_stages=pipeline_stages,
                compute_anomalies_fn=_compute_anomalies,
                attach_trace_schema_fn=attach_trace_schema_status,
                strip_legacy_trace_fields_fn=_strip_legacy_trace_fields,
            )
            response["debug_trace"] = debug_trace
        return response
