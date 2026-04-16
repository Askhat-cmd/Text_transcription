"""Shared response helpers extracted from response_utils (Wave 140)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state_classifier import StateAnalysis, UserState


def _get_feedback_prompt_for_state(state: UserState) -> str:
    """Return feedback follow-up prompt based on detected user state."""
    prompts = {
        UserState.UNAWARE: "РЎС‚Р°Р»Рѕ Р»Рё РїРѕРЅСЏС‚РЅРµРµ, Рѕ С‡С‘Рј СЂРµС‡СЊ? Р§С‚Рѕ РѕСЃС‚Р°Р»РѕСЃСЊ РЅРµРїРѕРЅСЏС‚РЅС‹Рј?",
        UserState.CURIOUS: "РҐРѕС‚РёС‚Рµ СѓР·РЅР°С‚СЊ С‡С‚Рѕ-С‚Рѕ РµС‰С‘ РїРѕ СЌС‚РѕР№ С‚РµРјРµ?",
        UserState.OVERWHELMED: "РќРµ СЃР»РёС€РєРѕРј Р»Рё РјРЅРѕРіРѕ РёРЅС„РѕСЂРјР°С†РёРё? РќСѓР¶РЅРѕ Р»Рё СѓРїСЂРѕСЃС‚РёС‚СЊ?",
        UserState.RESISTANT: "Р•СЃС‚СЊ Р»Рё С‡С‚Рѕ-С‚Рѕ, СЃ С‡РµРј РІС‹ РЅРµ СЃРѕРіР»Р°СЃРЅС‹? Р”Р°РІР°Р№С‚Рµ РѕР±СЃСѓРґРёРј.",
        UserState.CONFUSED: "РџСЂРѕСЏСЃРЅРёР»РѕСЃСЊ Р»Рё РѕР±СЉСЏСЃРЅРµРЅРёРµ? Р•СЃР»Рё РЅРµС‚, РєР°РєР°СЏ С‡Р°СЃС‚СЊ РІСЃС‘ РµС‰С‘ РЅРµРїРѕРЅСЏС‚РЅР°?",
        UserState.COMMITTED: "Р“РѕС‚РѕРІС‹ Р»Рё РІС‹ РЅР°С‡Р°С‚СЊ РїСЂР°РєС‚РёРєСѓ? РљР°РєР°СЏ РїРѕРґРґРµСЂР¶РєР° РЅСѓР¶РЅР°?",
        UserState.PRACTICING: "РљР°Рє РёРґС‘С‚ РїСЂР°РєС‚РёРєР°? Р•СЃС‚СЊ Р»Рё СЃР»РѕР¶РЅРѕСЃС‚Рё?",
        UserState.STAGNANT: "Р§С‚Рѕ, РїРѕ-РІР°С€РµРјСѓ, РјРµС€Р°РµС‚ РїСЂРѕРґРІРёР¶РµРЅРёСЋ? РџРѕРїСЂРѕР±СѓРµРј РЅР°Р№С‚Рё РЅРѕРІС‹Р№ РїРѕРґС…РѕРґ?",
        UserState.BREAKTHROUGH: "РџРѕР·РґСЂР°РІР»СЏСЋ СЃ РёРЅСЃР°Р№С‚РѕРј! РљР°Рє РїР»Р°РЅРёСЂСѓРµС‚Рµ РїСЂРёРјРµРЅРёС‚СЊ СЌС‚Рѕ РїРѕРЅРёРјР°РЅРёРµ?",
        UserState.INTEGRATED: "РљР°Рє СЌС‚Рѕ Р·РЅР°РЅРёРµ РїСЂРѕСЏРІР»СЏРµС‚СЃСЏ РІ РІР°С€РµР№ Р¶РёР·РЅРё?",
    }
    return prompts.get(state, "Р‘С‹Р» Р»Рё СЌС‚РѕС‚ РѕС‚РІРµС‚ РїРѕР»РµР·РµРЅ? РћС†РµРЅРёС‚Рµ РѕС‚ 1 РґРѕ 5.")


def _serialize_state_analysis(state_analysis: Optional[StateAnalysis]) -> Optional[Dict[str, Any]]:
    if state_analysis is None:
        return None
    return {
        "primary_state": state_analysis.primary_state.value,
        "confidence": state_analysis.confidence,
        "secondary_states": [s.value for s in state_analysis.secondary_states],
        "emotional_tone": state_analysis.emotional_tone,
        "depth": state_analysis.depth,
        "recommendations": state_analysis.recommendations,
    }


def _build_success_response(
    *,
    answer: str,
    state_analysis: StateAnalysis,
    path_recommendation: Optional[Dict[str, Any]],
    conversation_context: str,
    feedback_prompt: str,
    sources: List[Dict[str, Any]],
    concepts: List[str],
    metadata: Dict[str, Any],
    elapsed_time: float,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "answer": answer,
        "state_analysis": _serialize_state_analysis(state_analysis),
        "path_recommendation": path_recommendation,
        "conversation_context": conversation_context,
        "feedback_prompt": feedback_prompt,
        "sources": sources,
        "concepts": concepts,
        "metadata": metadata,
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": round(elapsed_time, 2),
    }

def _build_fast_success_metadata(
    *,
    user_id: str,
    state_analysis: StateAnalysis,
    routing_result,
    mode_reason: str,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    memory_context_mode: str,
    memory_trace_metrics: Dict[str, Any],
    summary_length: int,
    summary_last_turn: Optional[int],
    summary_pending_turn: Optional[int],
    memory_turns: int,
    hybrid_query_len: int,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    session_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "blocks_used": 0,
        "state": state_analysis.primary_state.value,
        "conversation_turns": memory_turns,
        "recommended_mode": routing_result.mode,
        "route_track": getattr(routing_result, "track", "direct"),
        "route_tone": getattr(routing_result, "tone", "minimal"),
        "decision_rule_id": routing_result.decision.rule_id,
        "confidence_score": routing_result.confidence_score,
        "confidence_level": routing_result.confidence_level,
        "mode_reason": mode_reason,
        "prompt_stack_v2_enabled": prompt_stack_v2_enabled,
        "output_validation_enabled": output_validation_enabled,
        "retrieval_block_cap": 0,
        "fast_path": True,
        "informational_mode": informational_mode,
        "applied_mode_prompt": mode_prompt_key if informational_mode else None,
        "summary_used": memory_trace_metrics["summary_used"],
        "summary_length": summary_length,
        "summary_last_turn": summary_last_turn,
        "context_mode": memory_context_mode,
        "summary_pending_turn": summary_pending_turn,
        "semantic_hits": memory_trace_metrics["semantic_hits"],
        "memory_turns": memory_turns,
        "hybrid_query_len": hybrid_query_len,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "session_tokens_prompt": session_metrics.get("session_tokens_prompt"),
        "session_tokens_completion": session_metrics.get("session_tokens_completion"),
        "session_tokens_total": session_metrics.get("session_tokens_total"),
        "session_cost_usd": session_metrics.get("session_cost_usd"),
        "session_turns": session_metrics.get("session_turns"),
    }

def _build_full_success_metadata(
    *,
    user_id: str,
    state_analysis: StateAnalysis,
    routing_result,
    mode_reason: str,
    route_resolution_count: int,
    blocks_used: int,
    selected_practice: Optional[str],
    practice_alternatives: List[str],
    retrieval_block_cap: int,
    informational_mode: bool,
    mode_prompt_key: Optional[str],
    prompt_stack_v2_enabled: bool,
    output_validation_enabled: bool,
    diagnostics_v1_payload: Optional[Dict[str, Any]],
    contradiction_detected: bool,
    cross_session_context_used: bool,
    memory_context_mode: str,
    memory_trace_metrics: Dict[str, Any],
    summary_length: int,
    summary_last_turn: Optional[int],
    summary_pending_turn: Optional[int],
    memory_turns: int,
    hybrid_query_len: int,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    session_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "blocks_used": blocks_used,
        "state": state_analysis.primary_state.value,
        "conversation_turns": memory_turns,
        "recommended_mode": routing_result.mode,
        "route_track": getattr(routing_result, "track", "direct"),
        "route_tone": getattr(routing_result, "tone", "minimal"),
        "resolved_route": getattr(routing_result, "route", None),
        "decision_rule_id": routing_result.decision.rule_id,
        "confidence_score": routing_result.confidence_score,
        "confidence_level": routing_result.confidence_level,
        "mode_reason": mode_reason,
        "route_resolution_count": route_resolution_count,
        "prompt_stack_v2_enabled": prompt_stack_v2_enabled,
        "output_validation_enabled": output_validation_enabled,
        "selected_practice": selected_practice,
        "practice_alternatives": practice_alternatives,
        "retrieval_block_cap": retrieval_block_cap,
        "informational_mode": informational_mode,
        "applied_mode_prompt": mode_prompt_key if informational_mode else None,
        "diagnostics_v1": diagnostics_v1_payload,
        "contradiction_detected": contradiction_detected,
        "cross_session_context_used": cross_session_context_used,
        "summary_used": memory_trace_metrics["summary_used"],
        "summary_length": summary_length,
        "summary_last_turn": summary_last_turn,
        "context_mode": memory_context_mode,
        "summary_pending_turn": summary_pending_turn,
        "semantic_hits": memory_trace_metrics["semantic_hits"],
        "memory_turns": memory_turns,
        "hybrid_query_len": hybrid_query_len,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_total,
        "session_tokens_prompt": session_metrics.get("session_tokens_prompt"),
        "session_tokens_completion": session_metrics.get("session_tokens_completion"),
        "session_tokens_total": session_metrics.get("session_tokens_total"),
        "session_cost_usd": session_metrics.get("session_cost_usd"),
        "session_turns": session_metrics.get("session_turns"),
    }

def _build_path_recommendation_if_enabled(
    *,
    include_path_recommendation: bool,
    state_analysis: StateAnalysis,
    route_name: str,
    path_builder_blocked_routes,
    user_id: str,
    user_level_enum,
    memory,
    path_builder,
    logger,
) -> Optional[Dict[str, Any]]:
    should_build_path = (
        include_path_recommendation
        and state_analysis.primary_state != UserState.INTEGRATED
        and route_name not in path_builder_blocked_routes
    )
    if not should_build_path:
        return None

    try:
        personal_path = path_builder.build_path(
            user_id=user_id,
            state_analysis=state_analysis,
            user_level=user_level_enum,
            memory=memory,
        )
        if not personal_path:
            return None
        return {
            "current_state": personal_path.current_state.value,
            "target_state": personal_path.target_state.value,
            "key_focus": personal_path.key_focus,
            "steps_count": len(personal_path.path_steps),
            "total_duration_weeks": personal_path.total_duration_weeks,
            "adaptation_notes": personal_path.adaptation_notes,
            "first_step": {
                "title": personal_path.path_steps[0].title if personal_path.path_steps else "",
                "duration_weeks": (
                    personal_path.path_steps[0].duration_weeks if personal_path.path_steps else 0
                ),
                "practices": (
                    personal_path.path_steps[0].practices[:3] if personal_path.path_steps else []
                ),
            }
            if personal_path.path_steps
            else None,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("[PATH_BUILDER] recommendation skipped: %s", exc)
        return None

def _persist_turn(
    *,
    memory,
    user_input: str,
    bot_response: str,
    user_state: Optional[str] = None,
    blocks_used: int = 0,
    concepts: Optional[List[str]] = None,
    schedule_summary_task: bool = True,
) -> None:
    memory.add_turn(
        user_input=user_input,
        bot_response=bot_response,
        user_state=user_state,
        blocks_used=blocks_used,
        concepts=concepts or [],
        schedule_summary_task=schedule_summary_task,
    )

def _save_session_summary_best_effort(
    *,
    memory,
    user_id: str,
    query: str,
    answer: str,
    state_end: str,
    concepts: Optional[List[str]] = None,
    logger=None,
) -> None:
    try:
        primary_interests = memory.get_primary_interests()
        key_themes: List[str] = []
        for item in (concepts or []) + primary_interests:
            text = str(item).strip()
            if text and text not in key_themes:
                key_themes.append(text)

        if hasattr(memory, "save_session_summary"):
            memory.save_session_summary(
                user_id=getattr(memory, "owner_user_id", user_id),
                summary={
                    "session_id": user_id,
                    "date": datetime.now().date().isoformat(),
                    "key_themes": key_themes[:3],
                    "state_end": state_end,
                    "notable_moments": [
                        f"Р—Р°РїСЂРѕСЃ: {str(query or '')[:140]}",
                        f"РћС‚РІРµС‚: {str(answer or '')[:140]}",
                    ],
                },
            )
    except Exception as exc:
        if logger is not None:
            logger.warning("[MEMORY] save_session_summary skipped: %s", exc)

def _build_sources_from_blocks(blocks: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "block_id": b.block_id,
            "title": b.title,
            "document_title": b.document_title,
            "youtube_link": b.youtube_link,
            "start": b.start,
            "end": b.end,
            "block_type": getattr(b, "block_type", "unknown"),
            "complexity_score": getattr(b, "complexity_score", 0),
        }
        for b in blocks
    ]

def _attach_debug_payload(
    *,
    result: Dict[str, Any],
    debug_info: Optional[Dict[str, Any]],
    memory,
    elapsed_time: float,
    llm_result: Optional[Dict[str, Any]] = None,
    retrieval_details: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> None:
    if debug_info is None:
        return
    debug_info["memory_summary"] = memory.get_summary()
    debug_info["total_time"] = elapsed_time
    debug_info["llm_tokens"] = (llm_result or {}).get("tokens_used", 0)
    if retrieval_details is not None:
        result.setdefault("metadata", {})["retrieval_details"] = retrieval_details
    if sources is not None:
        result.setdefault("metadata", {})["sources"] = sources
    result["debug"] = debug_info

def _attach_success_observability(
    *,
    result: Dict[str, Any],
    strip_legacy_runtime_metadata,
    attach_debug_payload,
    debug_info: Optional[Dict[str, Any]],
    memory,
    elapsed_time: float,
    llm_result: Optional[Dict[str, Any]],
    retrieval_details: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    debug_trace: Optional[Dict[str, Any]] = None,
    finalize_success_debug_trace=None,
    finalize_success_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    result["metadata"] = strip_legacy_runtime_metadata(result.get("metadata", {}))
    attach_debug_payload(
        result=result,
        debug_info=debug_info,
        memory=memory,
        elapsed_time=elapsed_time,
        llm_result=llm_result,
        retrieval_details=retrieval_details,
        sources=sources,
    )
    if debug_trace is not None and finalize_success_debug_trace is not None:
        debug_trace = finalize_success_debug_trace(
            debug_trace,
            **(finalize_success_kwargs or {}),
        )
        result["debug_trace"] = debug_trace
    return debug_trace

