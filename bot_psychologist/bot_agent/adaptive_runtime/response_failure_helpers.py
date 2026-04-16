"""Response failure/no-retrieval helpers extracted from response_utils (Wave 138)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state_classifier import StateAnalysis


def _build_partial_response(
    message: str,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
) -> Dict:
    """Build partial response payload when no blocks are retrieved."""
    return {
        "status": "partial",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value,
            "confidence": state_analysis.confidence,
            "emotional_tone": state_analysis.emotional_tone,
            "recommendations": state_analysis.recommendations,
        }
        if state_analysis
        else None,
        "path_recommendation": None,
        "conversation_context": memory.get_adaptive_context_text(query) if memory else "",
        "feedback_prompt": "РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРµСЂРµС„РѕСЂРјСѓР»РёСЂРѕРІР°С‚СЊ РІРѕРїСЂРѕСЃ.",
        "sources": [],
        "concepts": [],
        "metadata": {"conversation_turns": len(memory.turns) if memory else 0},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
    }

def _build_error_response(
    message: str,
    state_analysis: StateAnalysis,
    start_time: datetime,
) -> Dict:
    """Build error response payload for safe failure mode."""
    return {
        "status": "error",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value if state_analysis else "unknown",
            "confidence": state_analysis.confidence if state_analysis else 0,
        }
        if state_analysis
        else None,
        "path_recommendation": None,
        "conversation_context": "",
        "feedback_prompt": "",
        "sources": [],
        "concepts": [],
        "metadata": {},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
    }

def _persist_turn_best_effort(
    *,
    memory,
    user_input: str,
    bot_response: str,
    user_state: Optional[str] = None,
    blocks_used: int = 0,
    concepts: Optional[List[str]] = None,
    schedule_summary_task: bool = True,
) -> None:
    try:
        memory.add_turn(
            user_input=user_input,
            bot_response=bot_response,
            user_state=user_state,
            blocks_used=blocks_used,
            concepts=concepts or [],
            schedule_summary_task=schedule_summary_task,
        )
    except Exception:
        pass

def _handle_no_retrieval_partial_response(
    *,
    message: str,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
    routing_result,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    user_id: str,
    pipeline_stages: List[Dict[str, Any]],
    model_used: str,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    append_stages: List[Dict[str, Any]],
    set_working_state_best_effort,
    persist_turn,
    finalize_failure_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
) -> Dict[str, Any]:
    response = _build_partial_response(
        message,
        state_analysis,
        memory,
        start_time,
        query,
    )
    set_working_state_best_effort(
        memory=memory,
        state_analysis=state_analysis,
        routing_result=routing_result,
        log_prefix="[ADAPTIVE] working_state update failed (partial):",
    )
    persist_turn(
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
        debug_trace = finalize_failure_debug_trace(
            debug_trace,
            memory=memory,
            start_time=start_time,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=model_used,
            estimate_cost=estimate_cost,
            compute_anomalies=compute_anomalies,
            attach_trace_schema=attach_trace_schema,
            build_state_trajectory=build_state_trajectory,
            store_blob=store_blob,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
            blocks_after_cap=0,
            append_stages=append_stages,
        )
        response["debug_trace"] = debug_trace
    return response

def _run_no_retrieval_stage(
    *,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
    routing_result,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    user_id: str,
    pipeline_stages: List[Dict[str, Any]],
    model_used: str,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
    set_working_state_best_effort,
    persist_turn,
    finalize_failure_debug_trace,
    estimate_cost,
    compute_anomalies,
    attach_trace_schema,
    build_state_trajectory,
    store_blob,
) -> Dict[str, Any]:
    return _handle_no_retrieval_partial_response(
        message=(
            "Р С™ РЎРѓР С•Р В¶Р В°Р В»Р ВµР Р…Р С‘РЎР‹, РЎР‚Р ВµР В»Р ВµР Р†Р В°Р Р…РЎвЂљР Р…РЎвЂ№Р в„– Р СР В°РЎвЂљР ВµРЎР‚Р С‘Р В°Р В» "
            "Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…. Р СџР С•Р С—РЎР‚Р С•Р В±РЎС“Р в„–РЎвЂљР Вµ Р С—Р ВµРЎР‚Р ВµРЎвЂћР С•РЎР‚Р СРЎС“Р В»Р С‘РЎР‚Р С•Р Р†Р В°РЎвЂљРЎРЉ "
            "Р Р†Р С•Р С—РЎР‚Р С•РЎРѓ."
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
        model_used=model_used,
        initial_retrieved_blocks=initial_retrieved_blocks,
        reranked_blocks_for_trace=reranked_blocks_for_trace,
        append_stages=[
            {"name": "llm", "label": "LLM", "duration_ms": 0, "skipped": True},
            {
                "name": "format",
                "label": "Р В¤Р С•РЎР‚Р СР В°РЎвЂљР С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С‘Р Вµ",
                "duration_ms": 0,
                "skipped": True,
            },
        ],
        set_working_state_best_effort=set_working_state_best_effort,
        persist_turn=persist_turn,
        finalize_failure_debug_trace=finalize_failure_debug_trace,
        estimate_cost=estimate_cost,
        compute_anomalies=compute_anomalies,
        attach_trace_schema=attach_trace_schema,
        build_state_trajectory=build_state_trajectory,
        store_blob=store_blob,
    )

def _handle_llm_generation_error_response(
    *,
    llm_error: str,
    state_analysis: StateAnalysis,
    start_time: datetime,
    memory,
    query: str,
    schedule_summary_task: bool,
    debug_info: Optional[Dict[str, Any]],
    debug_trace: Optional[Dict[str, Any]],
    session_store,
    user_id: str,
    pipeline_stages: List[Dict[str, Any]],
    model_used: str,
    initial_retrieved_blocks,
    reranked_blocks_for_trace,
) -> Dict[str, Any]:
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .pricing_helpers import _estimate_cost as _runtime_estimate_cost
    from .trace_helpers import _finalize_failure_debug_trace as _runtime_finalize_failure_debug_trace

    response = _build_error_response(
        f"Р С›РЎв‚¬Р С‘Р В±Р С”Р В° Р С—РЎР‚Р С‘ Р С–Р ВµР Р…Р ВµРЎР‚Р В°РЎвЂ Р С‘Р С‘ Р С•РЎвЂљР Р†Р ВµРЎвЂљР В°: {llm_error}",
        state_analysis,
        start_time,
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
        debug_trace = _runtime_finalize_failure_debug_trace(
            debug_trace,
            memory=memory,
            start_time=start_time,
            session_store=session_store,
            user_id=user_id,
            pipeline_stages=pipeline_stages,
            model_used=model_used,
            estimate_cost=_runtime_estimate_cost,
            compute_anomalies=_runtime_compute_anomalies,
            attach_trace_schema=_runtime_attach_trace_schema_status,
            build_state_trajectory=_runtime_build_state_trajectory,
            store_blob=_runtime_store_blob,
            initial_retrieved_blocks=initial_retrieved_blocks,
            reranked_blocks_for_trace=reranked_blocks_for_trace,
        )
        response["debug_trace"] = debug_trace

    return response

def _build_unhandled_exception_response(
    *,
    exception: Exception,
    state_analysis: Optional[StateAnalysis],
    start_time: datetime,
    user_id: str,
    query: str,
    schedule_summary_task: bool,
    debug_trace: Optional[Dict[str, Any]],
    current_stage: str,
    session_store,
    pipeline_stages: List[Dict[str, Any]],
    llm_model_name: str,
) -> Dict[str, Any]:
    from ..conversation_memory import get_conversation_memory as _runtime_get_conversation_memory
    from ..trace_schema import attach_trace_schema_status as _runtime_attach_trace_schema_status
    from .pipeline_utils import (
        _build_state_trajectory as _runtime_build_state_trajectory,
        _compute_anomalies as _runtime_compute_anomalies,
        _store_blob as _runtime_store_blob,
    )
    from .pricing_helpers import _estimate_cost as _runtime_estimate_cost
    from .trace_helpers import (
        _finalize_failure_debug_trace as _runtime_finalize_failure_debug_trace,
        _strip_legacy_trace_fields as _runtime_strip_legacy_trace_fields,
    )

    response = _build_error_response(
        f"РџСЂРѕРёР·РѕС€Р»Р° РѕС€РёР±РєР° РїСЂРё РѕР±СЂР°Р±РѕС‚РєРµ Р·Р°РїСЂРѕСЃР°: {str(exception)}",
        state_analysis,
        start_time,
    )
    response["metadata"] = {"user_id": user_id}

    try:
        memory = _runtime_get_conversation_memory(user_id)
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
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "partial_trace_available": True,
        }
        try:
            memory = _runtime_get_conversation_memory(user_id)
            debug_trace = _runtime_finalize_failure_debug_trace(
                debug_trace,
                memory=memory,
                start_time=start_time,
                session_store=session_store,
                user_id=user_id,
                pipeline_stages=pipeline_stages,
                model_used=llm_model_name,
                estimate_cost=_runtime_estimate_cost,
                compute_anomalies=_runtime_compute_anomalies,
                attach_trace_schema=_runtime_attach_trace_schema_status,
                build_state_trajectory=_runtime_build_state_trajectory,
                store_blob=_runtime_store_blob,
                include_chunks=False,
                include_total_duration=False,
                strip_legacy_trace_fields=_runtime_strip_legacy_trace_fields,
            )
        except Exception:
            pass
        response["debug_trace"] = debug_trace

    return response

