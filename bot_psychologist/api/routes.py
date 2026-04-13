# api/routes.py
"""
API Routes for Bot Psychologist API (Phase 5)

REST endpoints РґР»СЏ РІСЃРµС… С„СѓРЅРєС†РёР№ Phase 1-4.
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

# Р”РѕР±Р°РІРёС‚СЊ РїСѓС‚СЊ Рє bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_agent import answer_question_adaptive
from bot_agent.llm_streaming import stream_answer_tokens
from bot_agent.config import config
from bot_agent.data_loader import data_loader
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.storage import SessionManager

from .models import (
    AskQuestionRequest, FeedbackRequest,
    AnswerResponse, AdaptiveAnswerResponse, FeedbackResponse,
    UserHistoryResponse, UserSummaryResponse, DeleteHistoryResponse, StatsResponse,
    SessionInfoResponse, ArchiveSessionsResponse,
    ChatSessionInfoResponse, UserSessionsResponse, CreateSessionRequest, DeleteSessionResponse,
    SourceResponse, StateAnalysisResponse, PathStepResponse, PathRecommendationResponse,
    ConversationTurnResponse, DebugTrace, ChunkTraceItem, LLMCallTrace
)
from .auth import verify_api_key, is_dev_key
from .dependencies import get_data_loader, get_graph_client, get_retriever
from .session_store import get_session_store, SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["bot"])

# Р“Р»РѕР±Р°Р»СЊРЅР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР° (РІ production РёСЃРїРѕР»СЊР·СѓР№ Р‘Р”)
_stats = {
    "total_users_approx": 0,
    "total_questions": 0,
    "total_processing_time": 0.0,
    "states_count": {},
    "interests_count": {}
}
_STATS_USER_LIMIT = 10_000
_seen_users: set[str] = set()


def _record_user(user_id: str) -> None:
    if user_id in _seen_users:
        return
    if len(_seen_users) >= _STATS_USER_LIMIT:
        _seen_users.clear()
    _seen_users.add(user_id)
    _stats["total_users_approx"] += 1


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_token_triplet(trace_payload: Dict[str, Any]) -> tuple[int, int, int]:
    llm_calls = trace_payload.get("llm_calls") if isinstance(trace_payload.get("llm_calls"), list) else []
    prompt = trace_payload.get("tokens_prompt")
    completion = trace_payload.get("tokens_completion")
    total = trace_payload.get("tokens_total")

    if prompt is None and llm_calls:
        prompt = sum(_coerce_int(call.get("tokens_prompt")) for call in llm_calls if isinstance(call, dict))
    if completion is None and llm_calls:
        completion = sum(_coerce_int(call.get("tokens_completion")) for call in llm_calls if isinstance(call, dict))
    if total is None and llm_calls:
        total = sum(_coerce_int(call.get("tokens_total")) for call in llm_calls if isinstance(call, dict))

    prompt_value = _coerce_int(prompt, 0)
    completion_value = _coerce_int(completion, 0)
    total_value = _coerce_int(total, prompt_value + completion_value)
    return prompt_value, completion_value, total_value


def _build_turn_diff(previous_trace: Optional[Dict[str, Any]], current_trace: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(previous_trace, dict):
        return {
            "route_changed": False,
            "state_changed": False,
            "config_changed_keys": [],
            "memory_delta": {
                "turns_added": 0,
                "summary_changed": False,
                "semantic_hits_delta": 0,
            },
        }

    prev_config = previous_trace.get("config_snapshot") if isinstance(previous_trace.get("config_snapshot"), dict) else {}
    curr_config = current_trace.get("config_snapshot") if isinstance(current_trace.get("config_snapshot"), dict) else {}
    config_keys = sorted(set(prev_config.keys()) | set(curr_config.keys()))
    config_changed_keys = [
        key for key in config_keys if prev_config.get(key) != curr_config.get(key)
    ]

    prev_memory_turns = _coerce_int(previous_trace.get("memory_turns"), 0)
    curr_memory_turns = _coerce_int(current_trace.get("memory_turns"), 0)
    prev_semantic_hits = _coerce_int(previous_trace.get("semantic_hits"), 0)
    curr_semantic_hits = _coerce_int(current_trace.get("semantic_hits"), 0)

    summary_changed = (
        previous_trace.get("summary_text") != current_trace.get("summary_text")
        or previous_trace.get("summary_last_turn") != current_trace.get("summary_last_turn")
    )

    return {
        "route_changed": previous_trace.get("recommended_mode") != current_trace.get("recommended_mode"),
        "state_changed": previous_trace.get("user_state") != current_trace.get("user_state"),
        "config_changed_keys": config_changed_keys,
        "memory_delta": {
            "turns_added": curr_memory_turns - prev_memory_turns,
            "summary_changed": bool(summary_changed),
            "semantic_hits_delta": curr_semantic_hits - prev_semantic_hits,
        },
    }


def _enrich_trace_for_storage(
    *,
    previous_trace: Optional[Dict[str, Any]],
    trace_payload: Dict[str, Any],
) -> Dict[str, Any]:
    enriched = _strip_legacy_trace_fields(trace_payload)
    prompt, completion, total = _extract_token_triplet(enriched)
    if enriched.get("tokens_prompt") is None:
        enriched["tokens_prompt"] = prompt
    if enriched.get("tokens_completion") is None:
        enriched["tokens_completion"] = completion
    if enriched.get("tokens_total") is None:
        enriched["tokens_total"] = total
    enriched["turn_diff"] = _build_turn_diff(previous_trace, enriched)
    return enriched


def _append_trace_with_resolved_session(
    *,
    store: SessionStore,
    default_session_key: str,
    trace_payload: dict,
) -> dict:
    """
    Persist trace under runtime session id when available.

    In Neo runtime the effective session id can differ from request user_id.
    UI debug surfaces use trace.session_id, so we keep both keys for
    backward compatibility.
    """
    resolved_session_key = str(trace_payload.get("session_id") or "").strip() or default_session_key
    previous = store.get_session_traces(resolved_session_key)
    previous_trace = previous[-1] if previous else None
    trace_enriched = _enrich_trace_for_storage(previous_trace=previous_trace, trace_payload=trace_payload)

    store.append_trace(resolved_session_key, trace_enriched)
    if resolved_session_key != default_session_key:
        store.append_trace(default_session_key, trace_enriched)

    return trace_enriched


def _to_chunk_trace_item(raw_chunk: dict, passed_default: bool) -> ChunkTraceItem:
    score_initial = float(raw_chunk.get("score_initial", raw_chunk.get("score", 0.0) or 0.0))
    score_final = float(raw_chunk.get("score_final", raw_chunk.get("score", score_initial) or score_initial))
    passed_filter = bool(raw_chunk.get("passed_filter", passed_default))
    chunk_text = raw_chunk.get("text") or raw_chunk.get("full_text")
    preview = (
        raw_chunk.get("preview")
        or raw_chunk.get("content")
        or raw_chunk.get("summary")
        or ""
    )
    return ChunkTraceItem(
        block_id=str(raw_chunk.get("block_id", "")),
        title=str(raw_chunk.get("title", "")),
        emotional_tone=str(raw_chunk.get("emotional_tone") or ""),
        score_initial=score_initial,
        score_final=score_final,
        passed_filter=passed_filter,
        filter_reason=str(raw_chunk.get("filter_reason") or ""),
        preview=str(preview)[:120],
        text=str(chunk_text) if chunk_text is not None else None,
    )


def _strip_legacy_trace_fields(raw_trace: dict) -> dict:
    trace = dict(raw_trace or {})

    for key in (
        "sd_classification",
        "sd_detail",
        "sd_level",
        "sd_secondary",
        "sd_confidence",
        "sd_method",
        "sd_allowed_blocks",
        "user_level",
        "user_level_adapter_applied",
    ):
        trace.pop(key, None)

    config_snapshot = trace.get("config_snapshot")
    if isinstance(config_snapshot, dict):
        cleaned_snapshot = dict(config_snapshot)
        for key in ("user_level", "sd_confidence_threshold"):
            cleaned_snapshot.pop(key, None)
        trace["config_snapshot"] = cleaned_snapshot

    trace["trace_contract_version"] = "v2"

    return trace


_LEGACY_RUNTIME_METADATA_KEYS = (
    "user_level",
    "user_level_adapter_applied",
    "sd_level",
    "sd_secondary",
    "sd_confidence",
    "sd_method",
    "sd_allowed_blocks",
    "decision_rule_id",
    "mode_reason",
    "confidence_level",
    "confidence_score",
)


def _strip_legacy_runtime_metadata(raw_metadata: dict) -> dict:
    metadata = dict(raw_metadata or {})
    for key in _LEGACY_RUNTIME_METADATA_KEYS:
        metadata.pop(key, None)
    return metadata


def _to_sources(raw_sources: list[dict]) -> list[SourceResponse]:
    return [
        SourceResponse(
            block_id=src.get("block_id", ""),
            title=src.get("title", ""),
            youtube_link=src.get("youtube_link", ""),
            start=src.get("start", 0),
            end=src.get("end", 0),
            block_type=src.get("block_type", "unknown"),
            complexity_score=src.get("complexity_score", 0.0),
        )
        for src in (raw_sources or [])
    ]


def _build_answer_response_from_adaptive(result: dict) -> AnswerResponse:
    metadata = _strip_legacy_runtime_metadata(result.get("metadata", {}) or {})
    return AnswerResponse(
        status=result.get("status", "success"),
        answer=result.get("answer", ""),
        concepts=result.get("concepts", []),
        sources=_to_sources(result.get("sources", [])),
        recommended_mode=metadata.get("recommended_mode"),
        decision_rule_id=metadata.get("decision_rule_id"),
        confidence_level=metadata.get("confidence_level"),
        confidence_score=metadata.get("confidence_score"),
        metadata=metadata,
        timestamp=datetime.now().isoformat(),
        processing_time_seconds=result.get("processing_time_seconds", 0),
    )


def _run_neo_compat_answer(
    *,
    request: AskQuestionRequest,
    session_store: SessionStore | None = None,
) -> dict:
    session_key = request.session_id or request.user_id
    return answer_question_adaptive(
        request.query,
        user_id=session_key,
        include_path_recommendation=False,
        include_feedback_prompt=False,
        debug=request.debug,
        session_store=session_store,
    )


# ===== QUESTIONS ENDPOINTS =====

@router.post(
    "/questions/basic",
    response_model=AnswerResponse,
    summary="Phase 1: Р‘Р°Р·РѕРІС‹Р№ QA",
    description="Р‘Р°Р·РѕРІС‹Р№ РІРѕРїСЂРѕСЃ-РѕС‚РІРµС‚ (Phase 1)"
)
async def ask_basic_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 1:** Р‘Р°Р·РѕРІС‹Р№ QA Р±РµР· Р°РґР°РїС‚Р°С†РёРё.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - GPT LLM
    - РџСЂРѕСЃС‚РѕР№ РѕС‚РІРµС‚
    
    **РџСЂРёРјРµСЂ:**
    ```
    {
      "query": "Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?",
      "user_id": "user_123"
    }
    ```
    """
    
    logger.info(f"[NEO_COMPAT] Basic endpoint routed to adaptive runtime: {request.query[:50]}...")

    try:
        result = _run_neo_compat_answer(request=request)
        _record_user(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        return _build_answer_response_from_adaptive(result)

    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/basic-with-semantic",
    response_model=AnswerResponse,
    summary="Phase 1: QA + Semantic Memory",
    description="Basic QA with semantic memory and summary"
)
async def ask_basic_question_with_semantic(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Phase 1 enhanced: basic QA with memory.
    """
    logger.info(f"[NEO_COMPAT] Basic+Semantic endpoint routed to adaptive runtime: {request.query[:50]}...")

    try:
        result = _run_neo_compat_answer(request=request)
        _record_user(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        return _build_answer_response_from_adaptive(result)
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/graph-powered",
    response_model=AnswerResponse,
    summary="Phase 3: Knowledge Graph QA",
    description="QA СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј Knowledge Graph"
)
async def ask_graph_powered_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    """
    **Phase 3:** Graph-powered QA СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј Knowledge Graph.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - Knowledge Graph (95 СѓР·Р»РѕРІ, 2182 СЃРІСЏР·Рё)
    - Concept hierarchy
    - РџСЂР°РєС‚РёРєРё РёР· РіСЂР°С„Р°
    """
    
    logger.info(f"[NEO_COMPAT] Graph-powered endpoint routed to adaptive runtime: {request.query[:50]}...")

    try:
        result = _run_neo_compat_answer(request=request, session_store=store)
        _record_user(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        return _build_answer_response_from_adaptive(result)

    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/adaptive",
    response_model=AdaptiveAnswerResponse,
    response_model_exclude_none=True,
    summary="Phase 4: Adaptive QA",
    description="РџРѕР»РЅРѕСЃС‚СЊСЋ Р°РґР°РїС‚РёРІРЅС‹Р№ QA СЃ Р°РЅР°Р»РёР·РѕРј СЃРѕСЃС‚РѕСЏРЅРёСЏ Рё РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹РјРё РїСѓС‚СЏРјРё"
)
async def ask_adaptive_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key),
    _data_loader=Depends(get_data_loader),
    _graph_client=Depends(get_graph_client),
    _retriever=Depends(get_retriever),
    store: SessionStore = Depends(get_session_store),
):
    """
    **Phase 4:** РџРѕР»РЅРѕСЃС‚СЊСЋ Р°РґР°РїС‚РёРІРЅС‹Р№ QA.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - State Classification (10 СЃРѕСЃС‚РѕСЏРЅРёР№)
    - Conversation Memory (РёСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіР°)
    - Personal Path Building (РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ РїСѓС‚Рё)
    - Р’СЃРµ РІРѕР·РјРѕР¶РЅРѕСЃС‚Рё Phase 1-3
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - РђРґР°РїС‚РёРІРЅС‹Р№ РѕС‚РІРµС‚
    - РђРЅР°Р»РёР· СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    - Р РµРєРѕРјРµРЅРґР°С†РёСЋ РїРµСЂСЃРѕРЅР°Р»СЊРЅРѕРіРѕ РїСѓС‚Рё
    - РђРґР°РїС‚РёРІРЅС‹Р№ Р·Р°РїСЂРѕСЃ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
    """
    
    logger.info(f"[ADAPTIVE] Adaptive question: {request.query[:50]}... (user: {request.user_id})")

    try:
        session_key = request.session_id or request.user_id

        # Dev-ключ автоматически включает debug-режим
        if is_dev_key(api_key):
            request.debug = True

        if request.session_id:
            try:
                session_manager = SessionManager(str(config.BOT_DB_PATH))
                session_manager.create_session(
                    session_id=session_key,
                    user_id=request.user_id,
                    metadata={
                        "source": "api",
                        "owner_user_id": request.user_id,
                    },
                )
            except Exception as exc:
                logger.warning(f"⚠️ Failed to pre-create session {session_key}: {exc}")

        result = answer_question_adaptive(
            request.query,
            user_id=session_key,
            include_path_recommendation=request.include_path,
            include_feedback_prompt=request.include_feedback_prompt,
            debug=request.debug,
            session_store=store,
        )
        
        # РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ
        _record_user(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        state = result.get("state_analysis", {}).get("primary_state", "unknown")
        _stats["states_count"][state] = _stats["states_count"].get(state, 0) + 1
        
        # РџСЂРµРѕР±СЂР°Р·РѕРІР°С‚СЊ sources
        sources = []
        for src in result.get("sources", []):
            sources.append(SourceResponse(
                block_id=src.get("block_id", ""),
                title=src.get("title", ""),
                youtube_link=src.get("youtube_link", ""),
                start=src.get("start", 0),
                end=src.get("end", 0),
                block_type=src.get("block_type", "unknown"),
                complexity_score=src.get("complexity_score", 0.0)
            ))
        
        # РџРѕСЃС‚СЂРѕРёС‚СЊ state_analysis
        state_analysis_data = result.get("state_analysis", {})
        state_analysis = StateAnalysisResponse(
            primary_state=state_analysis_data.get("primary_state", "unknown"),
            confidence=state_analysis_data.get("confidence", 0),
            emotional_tone=state_analysis_data.get("emotional_tone", ""),
            recommendations=state_analysis_data.get("recommendations", [])
        )
        
        # РџРѕСЃС‚СЂРѕРёС‚СЊ path_recommendation
        path_rec = result.get("path_recommendation")
        path_recommendation = None
        if path_rec:
            first_step = path_rec.get("first_step")
            first_step_response = None
            if first_step:
                first_step_response = PathStepResponse(
                    step_number=first_step.get("step_number", 1),
                    title=first_step.get("title", ""),
                    duration_weeks=first_step.get("duration_weeks", 1),
                    practices=first_step.get("practices", []),
                    key_concepts=first_step.get("key_concepts", [])
                )
            path_recommendation = PathRecommendationResponse(
                current_state=path_rec.get("current_state", ""),
                target_state=path_rec.get("target_state", ""),
                key_focus=path_rec.get("key_focus", ""),
                steps_count=path_rec.get("steps_count", 0),
                total_duration_weeks=path_rec.get("total_duration_weeks", 0),
                first_step=first_step_response
            )
        
        response_metadata = _strip_legacy_runtime_metadata(result.get("metadata", {}))
        response_metadata["user_id"] = request.user_id
        response_metadata["session_id"] = session_key

        trace = None
        if request.debug:
            raw = result.get("debug_trace") or result.get("debug")
            try:
                metadata = result.get("metadata", {}) or {}
                raw_dict = raw if isinstance(raw, dict) else {}

                chunks_retrieved_raw = []
                chunks_after_raw = []
                llm_calls_raw = []
                context_written = ""
                total_duration_ms = int(float(result.get("processing_time_seconds", 0) or 0) * 1000)

                retrieval_details = raw_dict.get("retrieval_details", {}) or {}
                chunks_retrieved_raw = (
                    raw_dict.get("chunks_retrieved")
                    or retrieval_details.get("initial_retrieval")
                    or []
                )
                chunks_after_raw = (
                    raw_dict.get("chunks_after_filter")
                    or retrieval_details.get("after_rerank")
                    or []
                )
                llm_calls_raw = raw_dict.get("llm_calls") or []
                context_written = raw_dict.get("context_written") or result.get("conversation_context", "")
                total_duration_ms = int(
                    raw_dict.get("total_duration_ms")
                    or float(raw_dict.get("total_time", result.get("processing_time_seconds", 0)) or 0) * 1000
                )

                chunks_retrieved = []
                for c in chunks_retrieved_raw:
                    if isinstance(c, ChunkTraceItem):
                        chunks_retrieved.append(c)
                    elif isinstance(c, dict):
                        chunks_retrieved.append(_to_chunk_trace_item(c, passed_default=False))

                chunks_after_filter_raw = raw_dict.get("chunks_after_filter") or chunks_after_raw or []
                chunks_after_filter = []
                for c in chunks_after_filter_raw:
                    if isinstance(c, ChunkTraceItem):
                        chunks_after_filter.append(c)
                    elif isinstance(c, dict):
                        chunks_after_filter.append(_to_chunk_trace_item(c, passed_default=True))

                # Fallback: если в debug нет чанков, но есть финальные sources — показываем их как прошедшие фильтр.
                if not chunks_retrieved and not chunks_after_filter:
                    source_chunks = []
                    for src in result.get("sources", []) or []:
                        if isinstance(src, dict):
                            source_chunks.append(_to_chunk_trace_item(
                                {
                                    "block_id": src.get("block_id", ""),
                                    "title": src.get("title", ""),
                                    "score": 0.0,
                                    "emotional_tone": "",
                                    "passed_filter": True,
                                    "preview": "",
                                },
                                passed_default=True,
                            ))
                    chunks_after_filter = source_chunks

                llm_calls = []
                for c in llm_calls_raw:
                    if not isinstance(c, dict):
                        continue
                    try:
                        llm_calls.append(LLMCallTrace(**c))
                    except Exception as llm_exc:
                        logger.warning(f"[DEBUG_TRACE] Invalid LLM call trace item skipped: {llm_exc}")

                trace_payload = {
                    "trace_contract_version": "v2",
                    "chunks_retrieved": chunks_retrieved,
                    "chunks_after_filter": chunks_after_filter,
                    "llm_calls": llm_calls,
                    "context_written_to_memory": context_written,
                    "context_written": raw_dict.get("context_written") or context_written,
                    "total_duration_ms": total_duration_ms,
                    "primary_model": config.LLM_MODEL,
                    "classifier_model": config.CLASSIFIER_MODEL,
                    "embedding_model": config.EMBEDDING_MODEL,
                    "reranker_model": config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None,
                    "reranker_enabled": bool(config.VOYAGE_ENABLED),
                    "tokens_prompt": metadata.get("tokens_prompt"),
                    "tokens_completion": metadata.get("tokens_completion"),
                    "tokens_total": metadata.get("tokens_total"),
                    "session_tokens_prompt": metadata.get("session_tokens_prompt"),
                    "session_tokens_completion": metadata.get("session_tokens_completion"),
                    "session_tokens_total": metadata.get("session_tokens_total"),
                    "session_cost_usd": metadata.get("session_cost_usd"),
                    "session_turns": metadata.get("session_turns"),
                    "decision_rule_id": (
                        str(metadata.get("decision_rule_id"))
                        if metadata.get("decision_rule_id") is not None
                        else None
                    ),
                    "mode_reason": metadata.get("mode_reason"),
                    "user_state": state_analysis.primary_state,
                    "recommended_mode": metadata.get("recommended_mode"),
                    "confidence_score": metadata.get("confidence_score"),
                    "confidence_level": metadata.get("confidence_level"),
                    "informational_mode": metadata.get("informational_mode"),
                    "applied_mode_prompt": metadata.get("applied_mode_prompt"),
                    "session_id": session_key,
                    "memory_turns": metadata.get("memory_turns"),
                    "summary_length": metadata.get("summary_length"),
                    "summary_last_turn": metadata.get("summary_last_turn"),
                    "summary_pending_turn": metadata.get("summary_pending_turn"),
                    "summary_used": metadata.get("summary_used"),
                    "semantic_hits": metadata.get("semantic_hits"),
                    "context_mode": metadata.get("context_mode"),
                    "hybrid_query_len": metadata.get("hybrid_query_len"),
                }

                # Extensions from debug trace (v2.0.6)
                for key in [
                    "fast_path",
                    "fast_path_reason",
                    "block_cap",
                    "blocks_initial",
                    "blocks_after_cap",
                    "hybrid_query_preview",
                    "hybrid_query_text",
                    "hybrid_query_len",
                    "context_mode",
                    "memory_turns_content",
                    "summary_text",
                    "summary_length",
                    "summary_last_turn",
                    "summary_pending_turn",
                    "summary_used",
                    "memory_turns",
                    "semantic_hits",
                    "semantic_hits_detail",
                    "state_secondary",
                    "state_trajectory",
                    "pipeline_stages",
                    "anomalies",
                    "system_prompt_blob_id",
                    "user_prompt_blob_id",
                    "memory_snapshot_blob_id",
                    "config_snapshot",
                    "estimated_cost_usd",
                    "pipeline_error",
                    "turn_number",
                    "user_state",
                    "recommended_mode",
                    "confidence_score",
                    "confidence_level",
                    "informational_mode",
                    "applied_mode_prompt",
                    "turn_diff",
                ]:
                    if key in raw_dict and raw_dict.get(key) is not None:
                        if key == "config_snapshot" and isinstance(raw_dict.get(key), dict):
                            trace_payload[key] = _strip_legacy_trace_fields(
                                {"config_snapshot": raw_dict.get(key)},
                            ).get("config_snapshot")
                        else:
                            trace_payload[key] = raw_dict.get(key)

                if trace_payload.get("decision_rule_id") is not None:
                    trace_payload["decision_rule_id"] = str(trace_payload.get("decision_rule_id"))

                trace_payload = _strip_legacy_trace_fields(trace_payload)

                trace = DebugTrace(**trace_payload)

                if llm_calls_raw and trace.tokens_total is None:
                    tokens_total = [
                        c.get("tokens_total")
                        for c in llm_calls_raw
                        if isinstance(c, dict) and c.get("tokens_total")
                    ]
                    if tokens_total:
                        trace.tokens_total = sum(int(t) for t in tokens_total)
                    answer_call = next(
                        (c for c in llm_calls_raw if isinstance(c, dict) and c.get("step") == "answer"),
                        None,
                    )
                    if answer_call:
                        trace.tokens_prompt = answer_call.get("tokens_prompt")
                        trace.tokens_completion = answer_call.get("tokens_completion")

                raw_session_tokens = raw_dict.get("session_tokens_total")
                raw_session_tokens_prompt = raw_dict.get("session_tokens_prompt")
                raw_session_tokens_completion = raw_dict.get("session_tokens_completion")
                raw_session_cost = raw_dict.get("session_cost_usd")
                raw_session_turns = raw_dict.get("session_turns")
                if raw_session_tokens is not None:
                    trace.session_tokens_total = raw_session_tokens
                if raw_session_tokens_prompt is not None:
                    trace.session_tokens_prompt = raw_session_tokens_prompt
                if raw_session_tokens_completion is not None:
                    trace.session_tokens_completion = raw_session_tokens_completion
                if raw_session_cost is not None:
                    trace.session_cost_usd = raw_session_cost
                if raw_session_turns is not None:
                    trace.session_turns = raw_session_turns

                try:
                    trace_payload_stored = _append_trace_with_resolved_session(
                        store=store,
                        default_session_key=session_key,
                        trace_payload=trace.model_dump(exclude_none=True),
                    )
                    trace = DebugTrace(**trace_payload_stored)
                except Exception as store_exc:
                    logger.warning(f"[DEBUG_TRACE] Failed to store trace: {store_exc}")
            except Exception as trace_exc:
                logger.warning(f"[DEBUG_TRACE] Failed to build trace: {trace_exc}")
                trace = None

        return AdaptiveAnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            state_analysis=state_analysis,
            path_recommendation=path_recommendation,
            feedback_prompt=result.get("feedback_prompt", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            conversation_context=result.get("conversation_context", ""),
            recommended_mode=response_metadata.get("recommended_mode"),
            decision_rule_id=response_metadata.get("decision_rule_id"),
            confidence_level=response_metadata.get("confidence_level"),
            confidence_score=response_metadata.get("confidence_score"),
            metadata=response_metadata,
            trace=trace,
            timestamp=datetime.now().isoformat(),
            processing_time_seconds=result.get("processing_time_seconds", 0)
        )
    
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/adaptive-stream",
    summary="Phase 4: Adaptive QA (streaming)",
    description="Streaming SSE endpoint for adaptive answers"
)
async def ask_adaptive_question_stream(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key),
    _data_loader=Depends(get_data_loader),
    store: SessionStore = Depends(get_session_store),
):
    if not config.ENABLE_STREAMING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming is disabled",
        )

    logger.info(f"[ADAPTIVE-STREAM] query: {request.query[:50]}... (user: {request.user_id})")

    session_key = request.session_id or request.user_id

    if is_dev_key(api_key):
        request.debug = True

    if request.session_id:
        try:
            session_manager = SessionManager(str(config.BOT_DB_PATH))
            session_manager.create_session(
                session_id=session_key,
                user_id=request.user_id,
                metadata={
                    "source": "api",
                    "owner_user_id": request.user_id,
                },
            )
        except Exception as exc:
            logger.warning(f"⚠️ Failed to pre-create session {session_key}: {exc}")

    _result_holder: dict = {}

    def _on_complete(result: dict) -> None:
        _result_holder.update(result)

    async def event_stream():
        try:
            async for token in stream_answer_tokens(
                request.query,
                user_id=session_key,
                session_store=store,
                include_path=request.include_path,
                include_feedback_prompt=request.include_feedback_prompt,
                debug=request.debug,
                on_complete=_on_complete,
                answer_fn=answer_question_adaptive,
            ):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

            result = dict(_result_holder)
            answer = str(result.get("answer", "") or "")

            latency_ms = int(float(result.get("processing_time_seconds", 0) or 0) * 1000)
            trace_raw = result.get("debug_trace") or result.get("debug")
            trace = trace_raw if isinstance(trace_raw, dict) else None
            if trace is not None:
                trace = _strip_legacy_trace_fields(trace)

            done_payload = {
                "done": True,
                "answer": answer,
                "answer_fallback": answer,
                "mode": (result.get("metadata") or {}).get("recommended_mode"),
                "latency_ms": latency_ms,
            }

            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            if request.debug and trace is not None:
                try:
                    trace = _append_trace_with_resolved_session(
                        store=store,
                        default_session_key=session_key,
                        trace_payload=trace,
                    )
                except Exception as store_exc:
                    logger.warning("[STREAM] Failed to store trace: %s", store_exc)
                yield "event: trace\n"
                yield f"data: {json.dumps(trace, ensure_ascii=False)}\n\n"
            try:
                memory = get_conversation_memory(session_key)
                schedule_fn = getattr(memory, "schedule_summary_task_if_due", None)
                if callable(schedule_fn):
                    schedule_fn()
            except Exception as summary_exc:
                logger.warning("[STREAM] Failed to schedule summary task: %s", summary_exc)

        except Exception as exc:
            logger.error("[ADAPTIVE-STREAM] failed: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ===== USER SESSIONS ENDPOINTS =====

def _session_title(item: dict) -> str:
    metadata = item.get("metadata") or {}
    raw_title = metadata.get("title")
    if isinstance(raw_title, str) and raw_title.strip():
        return raw_title.strip()

    last_user_input = (item.get("last_user_input") or "").strip()
    if not last_user_input:
        return "New chat"
    if len(last_user_input) <= 42:
        return last_user_input
    return f"{last_user_input[:42]}..."


@router.get(
    "/users/{user_id}/sessions",
    response_model=UserSessionsResponse,
    summary="User chat sessions",
    description="Get all chat sessions for user"
)
async def list_user_sessions(
    user_id: str,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        raw_sessions = manager.list_user_sessions(user_id=user_id, limit=limit)

        sessions = [
            ChatSessionInfoResponse(
                session_id=item.get("session_id", ""),
                user_id=user_id,
                created_at=item.get("created_at") or datetime.now().isoformat(),
                last_active=item.get("last_active") or item.get("created_at") or datetime.now().isoformat(),
                status=item.get("status") or "active",
                title=_session_title(item),
                turns_count=item.get("turns_count") or 0,
                last_user_input=item.get("last_user_input"),
                last_bot_response=item.get("last_bot_response"),
                last_turn_timestamp=item.get("last_turn_timestamp"),
            )
            for item in raw_sessions
        ]

        return UserSessionsResponse(
            user_id=user_id,
            total_sessions=len(sessions),
            sessions=sessions,
        )
    except Exception as e:
        logger.error(f"Error listing user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/users/{user_id}/sessions",
    response_model=ChatSessionInfoResponse,
    summary="Create user chat session",
    description="Create a new chat session for user"
)
async def create_user_session(
    user_id: str,
    request: Optional[CreateSessionRequest] = None,
    api_key: str = Depends(verify_api_key)
):
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        created = manager.create_user_session(
            user_id=user_id,
            title=(request.title if request else None),
        )

        return ChatSessionInfoResponse(
            session_id=created.get("session_id", ""),
            user_id=user_id,
            created_at=created.get("created_at") or datetime.now().isoformat(),
            last_active=created.get("last_active") or datetime.now().isoformat(),
            status=created.get("status") or "active",
            title=_session_title(created),
            turns_count=created.get("turns_count") or 0,
            last_user_input=created.get("last_user_input"),
            last_bot_response=created.get("last_bot_response"),
            last_turn_timestamp=created.get("last_turn_timestamp"),
        )
    except Exception as e:
        logger.error(f"Error creating session for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete user chat session",
    description="Delete one chat session of user"
)
async def delete_user_session(
    user_id: str,
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        payload = manager.load_session(session_id)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        session_info = payload.get("session_info", {})
        session_user_id = session_info.get("user_id")
        if session_user_id and session_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to user"
            )

        deleted = manager.delete_session_data(session_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        return DeleteSessionResponse(
            status="success",
            message=f"Session {session_id} deleted",
            user_id=user_id,
            session_id=session_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
# ===== USER HISTORY ENDPOINTS =====

@router.get(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ",
    description="РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
@router.post(
    "/users/{user_id}/history",
    response_model=UserHistoryResponse,
    summary="РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (POST)",
    description="РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ)"
)
async def get_user_history(
    user_id: str,
    last_n_turns: int = 10,
    api_key: str = Depends(verify_api_key)
):
    """
    РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
    
    **РџР°СЂР°РјРµС‚СЂС‹:**
    - `user_id`: ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    - `last_n_turns`: РџРѕСЃР»РµРґРЅРёРµ N РѕР±РѕСЂРѕС‚РѕРІ (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 10)
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - РСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіРѕРІ
    - РћСЃРЅРѕРІРЅС‹Рµ РёРЅС‚РµСЂРµСЃС‹
    - РЎСЂРµРґРЅРёР№ СЂРµР№С‚РёРЅРі
    - РџРѕСЃР»РµРґРЅРµРµ РІР·Р°РёРјРѕРґРµР№СЃС‚РІРёРµ
    """
    
    logger.info(f"рџ“‹ РСЃС‚РѕСЂРёСЏ РґР»СЏ {user_id}")
    
    try:
        memory = get_conversation_memory(user_id)
        summary = memory.get_summary()
        last_turns = memory.get_last_turns(last_n_turns)
        
        turns = []
        for turn in last_turns:
            turns.append(ConversationTurnResponse(
                timestamp=turn.timestamp,
                user_input=turn.user_input,
                user_state=turn.user_state,
                bot_response=turn.bot_response or "",
                blocks_used=turn.blocks_used,
                concepts=turn.concepts or [],
                user_feedback=turn.user_feedback,
                user_rating=turn.user_rating
            ))
        
        return UserHistoryResponse(
            user_id=user_id,
            total_turns=len(memory.turns),
            turns=turns,
            primary_interests=summary.get("primary_interests", []),
            average_rating=summary.get("average_rating", 0),
            last_interaction=summary.get("last_interaction")
        )
    
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/users/{user_id}/summary",
    response_model=UserSummaryResponse,
    summary="РЎРІРѕРґРєР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ",
    description="РљСЂР°С‚РєР°СЏ СЃРІРѕРґРєР° РїРѕ РёСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def get_user_summary(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"рџ“Њ РЎРІРѕРґРєР° РґР»СЏ {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        summary = memory.get_summary()
        return UserSummaryResponse(
            user_id=user_id,
            total_turns=summary.get("total_turns", len(memory.turns)),
            primary_interests=summary.get("primary_interests", []),
            num_challenges=summary.get("num_challenges", 0),
            num_breakthroughs=summary.get("num_breakthroughs", 0),
            average_rating=summary.get("average_rating", 0),
            last_interaction=summary.get("last_interaction")
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/users/{user_id}/session",
    response_model=SessionInfoResponse,
    summary="Session Storage Status",
    description="РЎС‚Р°С‚СѓСЃ SQLite-РїРµСЂСЃРёСЃС‚РµРЅС‚РЅРѕСЃС‚Рё РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def get_user_session_info(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        manager = memory.session_manager
        if not manager:
            return SessionInfoResponse(
                user_id=user_id,
                enabled=False,
                exists=False,
            )

        payload = manager.load_session(user_id)
        if not payload:
            return SessionInfoResponse(
                user_id=user_id,
                enabled=True,
                exists=False,
            )

        session_info = payload.get("session_info", {})
        turns = payload.get("conversation_turns", [])
        embeddings = payload.get("semantic_embeddings", [])

        return SessionInfoResponse(
            user_id=user_id,
            enabled=True,
            exists=True,
            status=session_info.get("status"),
            total_turns=len(turns),
            total_embeddings=len(embeddings),
            last_active=session_info.get("last_active"),
            has_working_state=bool(session_info.get("working_state")),
            has_summary=bool(session_info.get("conversation_summary")),
        )
    except Exception as e:
        logger.error(f"вќЊ Error loading session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/sessions/archive",
    response_model=ArchiveSessionsResponse,
    summary="Archive Old Sessions",
    description="РђСЂС…РёРІРёСЂРѕРІР°С‚СЊ СЃС‚Р°СЂС‹Рµ SQLite-СЃРµСЃСЃРёРё СЃС‚Р°СЂС€Рµ N РґРЅРµР№"
)
async def archive_old_sessions(
    active_days: int = 90,
    archive_days: int = 365,
    api_key: str = Depends(verify_api_key)
):
    if active_days < 1 or archive_days < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="active_days and archive_days must be >= 1"
        )
    try:
        manager = SessionManager(str(config.BOT_DB_PATH))
        cleanup_result = manager.run_retention_cleanup(
            active_days=active_days,
            archive_days=archive_days,
        )
        return ArchiveSessionsResponse(
            status="success",
            archived_count=cleanup_result["archived_count"],
            deleted_count=cleanup_result["deleted_count"],
            active_days=active_days,
            archive_days=archive_days,
            db_path=str(config.BOT_DB_PATH),
        )
    except Exception as e:
        logger.error(f"вќЊ Error archiving sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/users/{user_id}/semantic-stats",
    summary="Semantic Memory Stats",
    description="Get semantic memory stats for user"
)
async def get_semantic_stats(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        if not memory.semantic_memory:
            return {"enabled": False, "message": "Semantic memory disabled"}
        stats = memory.semantic_memory.get_stats()
        return {"enabled": True, "user_id": user_id, **stats}
    except Exception as e:
        logger.error(f"вќЊ Error getting semantic stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/users/{user_id}/rebuild-semantic-memory",
    summary="Rebuild Semantic Memory",
    description="Rebuild semantic memory for user"
)
async def rebuild_semantic_memory(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        if not memory.semantic_memory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Semantic memory disabled"
            )
        memory.rebuild_semantic_memory()
        stats = memory.semantic_memory.get_stats()
        return {
            "success": True,
            "message": f"Semantic memory rebuilt for {stats.get('total_embeddings', 0)} turns",
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"вќЊ Error rebuilding semantic memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/users/{user_id}/update-summary",
    summary="Update Conversation Summary",
    description="Force update conversation summary for user"
)
async def force_update_summary(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        memory = get_conversation_memory(user_id)
        if len(memory.turns) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough turns to create summary (minimum 5)"
            )
        memory._update_summary()
        return {
            "success": True,
            "summary": memory.summary,
            "updated_at_turn": memory.summary_updated_at,
            "summary_length": len(memory.summary) if memory.summary else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"вќЊ Error updating summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/users/{user_id}/history",
    response_model=DeleteHistoryResponse,
    summary="РћС‡РёСЃС‚РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ",
    description="РЈРґР°Р»РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def delete_user_history(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"рџ§№ РћС‡РёСЃС‚РєР° РёСЃС‚РѕСЂРёРё РґР»СЏ {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        memory.clear()
        return DeleteHistoryResponse(
            status="success",
            message=f"РСЃС‚РѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id} РѕС‡РёС‰РµРЅР°",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/users/{user_id}/gdpr-data",
    response_model=DeleteHistoryResponse,
    summary="GDPR Delete User Data",
    description="РџРѕР»РЅРѕСЃС‚СЊСЋ СѓРґР°Р»РёС‚СЊ РґР°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РёР· JSON/semantic cache/SQLite"
)
async def gdpr_delete_user_data(
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    logger.info(f"рџ—‘пёЏ GDPR delete for {user_id}")
    try:
        memory = get_conversation_memory(user_id)
        memory.purge_user_data()
        return DeleteHistoryResponse(
            status="success",
            message=f"Р”Р°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id} РїРѕР»РЅРѕСЃС‚СЊСЋ СѓРґР°Р»РµРЅС‹ (GDPR)",
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"вќЊ GDPR delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== FEEDBACK ENDPOINTS =====

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ",
    description="РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ РЅР° РѕС‚РІРµС‚"
)
async def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    РћС‚РїСЂР°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ РЅР° РѕС‚РІРµС‚.
    
    **РўРёРїС‹ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё:**
    - `positive`: РћС‚РІРµС‚ Р±С‹Р» РїРѕР»РµР·РµРЅ вњ…
    - `negative`: РћС‚РІРµС‚ РЅРµ РїРѕРјРѕРі вќЊ
    - `neutral`: РќРµР№С‚СЂР°Р»СЊРЅР°СЏ РѕС†РµРЅРєР° рџ¤·
    
    **Р РµР№С‚РёРЅРі:** 1-5 Р·РІРµР·Рґ
    """
    
    logger.info(f"рџ‘Ќ РћР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ РѕС‚ {request.user_id}: {request.feedback}")
    
    try:
        memory = get_conversation_memory(request.user_id)
        memory.add_feedback(
            turn_index=request.turn_index,
            feedback=request.feedback.value,
            rating=request.rating
        )
        
        return FeedbackResponse(
            status="success",
            message="РћР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ СЃРѕС…СЂР°РЅРµРЅР°",
            user_id=request.user_id,
            turn_index=request.turn_index
        )
    
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"РҐРѕРґ #{request.turn_index} РЅРµ РЅР°Р№РґРµРЅ"
        )
    except Exception as e:
        logger.error(f"вќЊ РћС€РёР±РєР°: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== STATISTICS ENDPOINTS =====

@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="РћР±С‰Р°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР°",
    description="РџРѕР»СѓС‡РёС‚СЊ РѕР±С‰СѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ СЃРёСЃС‚РµРјС‹"
)
async def get_statistics(
    api_key: str = Depends(verify_api_key)
):
    """
    РџРѕР»СѓС‡РёС‚СЊ РѕР±С‰СѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ СЃРёСЃС‚РµРјС‹.
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - Р’СЃРµРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№
    - Р’СЃРµРіРѕ РІРѕРїСЂРѕСЃРѕРІ
    - РЎСЂРµРґРЅРµРµ РІСЂРµРјСЏ РѕР±СЂР°Р±РѕС‚РєРё
    - РўРѕРї СЃРѕСЃС‚РѕСЏРЅРёР№
    - РўРѕРї РёРЅС‚РµСЂРµСЃРѕРІ
    - РЎС‚Р°С‚РёСЃС‚РёРєР° РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё
    """
    
    logger.info("рџ“Љ Р—Р°РїСЂРѕСЃ СЃС‚Р°С‚РёСЃС‚РёРєРё")
    
    avg_time = (
        _stats["total_processing_time"] / _stats["total_questions"]
        if _stats["total_questions"] > 0 else 0
    )
    
    return StatsResponse(
        total_users=_stats["total_users_approx"],
        total_questions=_stats["total_questions"],
        average_processing_time=round(avg_time, 2),
        top_states=_stats["states_count"],
        top_interests=[],
        feedback_stats={},
        timestamp=datetime.now().isoformat()
    )


# ===== HEALTH CHECK =====

@router.get(
    "/health",
    summary="РџСЂРѕРІРµСЂРєР° Р·РґРѕСЂРѕРІСЊСЏ",
    description="РџСЂРѕРІРµСЂРёС‚СЊ СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРµСЂР°"
)
async def health_check():
    """
    РџСЂРѕРІРµСЂРёС‚СЊ СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРµСЂР°.
    
    **Р’РѕР·РІСЂР°С‰Р°РµС‚:**
    - РЎС‚Р°С‚СѓСЃ (healthy/unhealthy)
    - Р’РµСЂСЃРёСЋ API
    - РЎС‚Р°С‚СѓСЃ РєР°Р¶РґРѕРіРѕ РјРѕРґСѓР»СЏ
    """
    
    data_source = str(getattr(config, "DATA_SOURCE", "unknown") or "unknown")
    degraded_mode = bool(getattr(config, "DEGRADED_MODE", False))
    blocks_loaded = len(getattr(data_loader, "all_blocks", []) or [])

    if degraded_mode:
        status_value = "degraded"
    elif data_source == "json_fallback":
        status_value = "degraded_fallback"
    else:
        status_value = "healthy"

    if data_source == "api":
        bot_db_api_status = "available"
    elif data_source in {"json_fallback", "degraded"}:
        bot_db_api_status = "unavailable"
    else:
        bot_db_api_status = "unknown"

    return {
        "status": status_value,
        "version": "0.6.1",
        "timestamp": datetime.now().isoformat(),
        "data_source": data_source,
        "blocks_loaded": blocks_loaded,
        "bot_data_base_api": bot_db_api_status,
        "modules": {
            "bot_agent": True,
            "conversation_memory": True,
            "state_classifier": True,
            "path_builder": True,
            "api": True,
        },
    }








