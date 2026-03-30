# api/routes.py
"""
API Routes for Bot Psychologist API (Phase 5)

REST endpoints РґР»СЏ РІСЃРµС… С„СѓРЅРєС†РёР№ Phase 1-4.
"""

import json
import logging
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

# Р”РѕР±Р°РІРёС‚СЊ РїСѓС‚СЊ Рє bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_agent import (
    answer_question_basic,
    answer_question_sag_aware,
    answer_question_graph_powered,
    answer_question_adaptive
)
from bot_agent.config import config
from bot_agent.data_loader import data_loader
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.decision import (
    DecisionGate,
    build_mode_directive,
    detect_routing_signals,
    resolve_user_stage,
)
from bot_agent.response import ResponseFormatter, ResponseGenerator
from bot_agent.retrieval import HybridQueryBuilder, VoyageReranker
from bot_agent.user_level_adapter import UserLevelAdapter
from bot_agent.storage import SessionManager
from bot_agent.answer_adaptive import (
    _classify_parallel,
    _fallback_state_analysis,
    _fallback_sd_result,
    _should_use_fast_path,
    _build_fast_path_block,
    _build_state_context,
    _build_working_state,
    _get_memory_trace_metrics,
    _build_llm_prompts,
    _build_llm_prompt_previews,
    _build_llm_call_trace,
    _build_memory_context_snapshot,
    _build_config_snapshot,
    _compute_anomalies,
    _estimate_cost,
    _store_blob,
    _build_state_trajectory,
    _build_chunk_trace_lists_after_rerank,
    _detect_fast_path_reason,
    _truncate_preview,
)
from bot_agent.state_classifier import state_classifier
from bot_agent.sd_classifier import sd_classifier

from .models import (
    AskQuestionRequest, FeedbackRequest,
    AnswerResponse, AdaptiveAnswerResponse, FeedbackResponse,
    UserHistoryResponse, UserSummaryResponse, DeleteHistoryResponse, StatsResponse,
    SessionInfoResponse, ArchiveSessionsResponse,
    ChatSessionInfoResponse, UserSessionsResponse, CreateSessionRequest, DeleteSessionResponse,
    SourceResponse, StateAnalysisResponse, PathStepResponse, PathRecommendationResponse,
    ConversationTurnResponse, DebugTrace, SDClassificationTrace, ChunkTraceItem, LLMCallTrace
)
from .auth import verify_api_key, is_dev_key
from .dependencies import get_data_loader, get_graph_client, get_retriever
from .session_store import get_session_store, SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["bot"])

# Р“Р»РѕР±Р°Р»СЊРЅР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР° (РІ production РёСЃРїРѕР»СЊР·СѓР№ Р‘Р”)
_stats = {
    "total_users": set(),
    "total_questions": 0,
    "total_processing_time": 0.0,
    "states_count": {},
    "interests_count": {}
}


def _to_chunk_trace_item(raw_chunk: dict, default_sd_level: str, passed_default: bool) -> ChunkTraceItem:
    score_initial = float(raw_chunk.get("score_initial", raw_chunk.get("score", 0.0) or 0.0))
    score_final = float(raw_chunk.get("score_final", raw_chunk.get("score", score_initial) or score_initial))
    passed_filter = bool(raw_chunk.get("passed_filter", passed_default))
    preview = (
        raw_chunk.get("preview")
        or raw_chunk.get("content")
        or raw_chunk.get("summary")
        or ""
    )
    return ChunkTraceItem(
        block_id=str(raw_chunk.get("block_id", "")),
        title=str(raw_chunk.get("title", "")),
        sd_level=str(raw_chunk.get("sd_level", default_sd_level or "UNKNOWN")),
        sd_secondary=str(raw_chunk.get("sd_secondary") or ""),
        emotional_tone=str(raw_chunk.get("emotional_tone") or ""),
        score_initial=score_initial,
        score_final=score_final,
        passed_filter=passed_filter,
        filter_reason=str(raw_chunk.get("filter_reason") or ""),
        preview=str(preview)[:120],
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
    
    logger.info(f"рџ“ќ Basic question: {request.query[:50]}... (user: {request.user_id})")
    
    try:
        result = answer_question_basic(
            request.query,
            user_id=request.user_id,
            use_semantic_memory=False
        )
        
        # РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
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
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
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
    logger.info(f"рџ§  Basic+Semantic question: {request.query[:50]}... (user: {request.user_id})")

    try:
        result = answer_question_basic(
            request.query,
            user_id=request.user_id,
            debug=request.debug,
            use_semantic_memory=True
        )

        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)

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

        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
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
    "/questions/sag-aware",
    response_model=AnswerResponse,
    summary="Phase 2: SAG-aware QA",
    description="QA СЃ СѓС‡РµС‚РѕРј SAG v2.0 Рё СѓСЂРѕРІРЅСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"
)
async def ask_sag_aware_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 2:** SAG-aware QA СЃ Р°РґР°РїС‚Р°С†РёРµР№ РїРѕ СѓСЂРѕРІРЅСЋ.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - User level adaptation (beginner/intermediate/advanced)
    - Semantic analysis
    - РђРґР°РїС‚РёРІРЅС‹Рµ РѕС‚РІРµС‚С‹
    """
    
    logger.info(f"рџ§  SAG-aware question: {request.query[:50]}... (level: {request.user_level})")
    
    try:
        result = answer_question_sag_aware(
            request.query,
            user_id=request.user_id,
            user_level=request.user_level.value,
            debug=request.debug
        )
        
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
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
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
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
    "/questions/graph-powered",
    response_model=AnswerResponse,
    summary="Phase 3: Knowledge Graph QA",
    description="QA СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј Knowledge Graph"
)
async def ask_graph_powered_question(
    request: AskQuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    **Phase 3:** Graph-powered QA СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј Knowledge Graph.
    
    РСЃРїРѕР»СЊР·СѓРµС‚:
    - TF-IDF retrieval
    - Knowledge Graph (95 СѓР·Р»РѕРІ, 2182 СЃРІСЏР·Рё)
    - Concept hierarchy
    - РџСЂР°РєС‚РёРєРё РёР· РіСЂР°С„Р°
    """
    
    logger.info(f"рџ“Љ Graph-powered question: {request.query[:50]}...")
    
    try:
        result = answer_question_graph_powered(
            request.query,
            user_id=request.user_id,
            user_level=request.user_level.value,
            debug=request.debug
        )
        
        _stats["total_users"].add(request.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
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
        
        return AnswerResponse(
            status=result.get("status", "success"),
            answer=result.get("answer", ""),
            concepts=result.get("concepts", []),
            sources=sources,
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
            metadata=result.get("metadata", {}),
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
    "/questions/adaptive",
    response_model=AdaptiveAnswerResponse,
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
            user_level=request.user_level.value,
            include_path_recommendation=request.include_path,
            include_feedback_prompt=request.include_feedback_prompt,
            debug=request.debug,
            session_store=store,
        )
        
        # РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ
        _stats["total_users"].add(request.user_id)
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
        
        response_metadata = dict(result.get("metadata", {}))
        response_metadata["user_id"] = request.user_id
        response_metadata["session_id"] = session_key

        trace = None
        if request.debug:
            raw = result.get("debug_trace") or result.get("debug")
            try:
                metadata = result.get("metadata", {}) or {}
                raw_dict = raw if isinstance(raw, dict) else {}

                sd_raw = raw_dict.get("sd_classification") or {}
                if not isinstance(sd_raw, dict):
                    sd_raw = {}
                allowed_levels = (
                    sd_raw.get("allowed_levels")
                    or sd_raw.get("allowed_blocks")
                    or metadata.get("sd_allowed_blocks")
                    or []
                )
                if not isinstance(allowed_levels, list):
                    allowed_levels = []

                default_sd_level = str(sd_raw.get("primary") or metadata.get("sd_level") or "UNKNOWN")

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
                        chunks_retrieved.append(
                            _to_chunk_trace_item(c, default_sd_level=default_sd_level, passed_default=False)
                        )

                chunks_after_filter_raw = raw_dict.get("chunks_after_filter") or chunks_after_raw or []
                chunks_after_filter = []
                for c in chunks_after_filter_raw:
                    if isinstance(c, ChunkTraceItem):
                        chunks_after_filter.append(c)
                    elif isinstance(c, dict):
                        chunks_after_filter.append(
                            _to_chunk_trace_item(c, default_sd_level=default_sd_level, passed_default=True)
                        )

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
                                    "sd_level": metadata.get("sd_level", default_sd_level),
                                    "sd_secondary": metadata.get("sd_secondary", ""),
                                    "emotional_tone": "",
                                    "passed_filter": True,
                                    "preview": "",
                                },
                                default_sd_level=default_sd_level,
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
                    "sd_classification": SDClassificationTrace(
                        method=str(sd_raw.get("method", metadata.get("sd_method", "fallback"))),
                        primary=default_sd_level,
                        secondary=sd_raw.get("secondary", metadata.get("sd_secondary")),
                        confidence=float(sd_raw.get("confidence", metadata.get("sd_confidence", 0.0) or 0.0)),
                        indicator=str(sd_raw.get("indicator", "metadata_fallback")),
                        allowed_levels=[str(level) for level in allowed_levels],
                    ),
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
                    "session_tokens_total": metadata.get("session_tokens_total"),
                    "session_cost_usd": metadata.get("session_cost_usd"),
                    "session_turns": metadata.get("session_turns"),
                    "decision_rule_id": (
                        str(metadata.get("decision_rule_id"))
                        if metadata.get("decision_rule_id") is not None
                        else None
                    ),
                    "mode_reason": metadata.get("mode_reason"),
                    "sd_level": metadata.get("sd_level"),
                    "user_state": state_analysis.primary_state,
                    "recommended_mode": metadata.get("recommended_mode"),
                    "confidence_score": metadata.get("confidence_score"),
                    "confidence_level": metadata.get("confidence_level"),
                    "session_id": session_key,
                    "memory_turns": metadata.get("memory_turns"),
                    "summary_length": metadata.get("summary_length"),
                    "summary_last_turn": metadata.get("summary_last_turn"),
                    "summary_used": metadata.get("summary_used"),
                    "semantic_hits": metadata.get("semantic_hits"),
                    "sd_detail": raw_dict.get("sd_detail") or {
                        "method": sd_raw.get("method", metadata.get("sd_method", "fallback")),
                        "primary": default_sd_level,
                        "secondary": sd_raw.get("secondary", metadata.get("sd_secondary")),
                        "confidence": float(sd_raw.get("confidence", metadata.get("sd_confidence", 0.0) or 0.0)),
                        "indicator": sd_raw.get("indicator", "metadata_fallback"),
                        "allowed_levels": [str(level) for level in allowed_levels],
                    },
                }

                # Extensions from debug trace (v2.0.6)
                for key in [
                    "fast_path",
                    "fast_path_reason",
                    "block_cap",
                    "blocks_initial",
                    "blocks_after_cap",
                    "hybrid_query_preview",
                    "sd_detail",
                    "memory_turns_content",
                    "summary_text",
                    "summary_length",
                    "summary_last_turn",
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
                    "sd_level",
                    "user_state",
                    "recommended_mode",
                    "confidence_score",
                    "confidence_level",
                ]:
                    if key in raw_dict and raw_dict.get(key) is not None:
                        trace_payload[key] = raw_dict.get(key)

                if trace_payload.get("decision_rule_id") is not None:
                    trace_payload["decision_rule_id"] = str(trace_payload.get("decision_rule_id"))

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
                raw_session_cost = raw_dict.get("session_cost_usd")
                raw_session_turns = raw_dict.get("session_turns")
                if raw_session_tokens is not None:
                    trace.session_tokens_total = raw_session_tokens
                if raw_session_cost is not None:
                    trace.session_cost_usd = raw_session_cost
                if raw_session_turns is not None:
                    trace.session_turns = raw_session_turns

                try:
                    store.append_trace(session_key, trace.model_dump())
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
            recommended_mode=result.get("metadata", {}).get("recommended_mode"),
            decision_rule_id=result.get("metadata", {}).get("decision_rule_id"),
            confidence_level=result.get("metadata", {}).get("confidence_level"),
            confidence_score=result.get("metadata", {}).get("confidence_score"),
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
    _graph_client=Depends(get_graph_client),
    retriever_dep=Depends(get_retriever),
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

    async def event_stream():
        start_ts = time.perf_counter()
        pipeline_stages = []

        # Для debug режима используем не-streaming вызов (чтобы получить токены без удвоения запроса)
        if request.debug:
            logger.info("[ADAPTIVE-STREAM] Debug mode detected, using non-streaming call for accurate tokens")
            result = answer_question_adaptive(
                request.query,
                user_id=session_key,
                user_level=request.user_level.value,
                include_path_recommendation=request.include_path,
                include_feedback_prompt=request.include_feedback_prompt,
                debug=True,
                session_store=store,
            )
            # Стримим ответ по одному токену (эмуляция streaming)
            answer = result.get("answer", "")
            # Отправляем токены по одному (разбиваем по словам для имитации streaming)
            words = answer.split(" ")
            for i, word in enumerate(words):
                token = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)  # Небольшая задержка для имитации streaming
            
            latency_ms = int(result.get("processing_time_seconds", 0) * 1000)
            trace = result.get("debug_trace") or result.get("debug")
            
            done_payload = {
                "done": True,
                "answer": answer,
                "mode": result.get("metadata", {}).get("recommended_mode"),
                "sd_level": result.get("state_analysis", {}).get("primary_state"),
                "latency_ms": latency_ms,
                "trace": trace if isinstance(trace, dict) else None,
            }
            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            return
        try:
            memory = get_conversation_memory(session_key)
            conversation_context = memory.get_adaptive_context_text(request.query)
            conversation_history = [
                {"role": "user", "content": turn.user_input}
                for turn in memory.get_last_turns(config.CONVERSATION_HISTORY_DEPTH)
            ]
            conversation_history_for_sd = [
                {"role": "user", "content": turn.user_input}
                for turn in memory.get_last_turns(10)
            ]

            if request.debug:
                stage_start = time.perf_counter()
                try:
                    state_analysis = await state_classifier.classify(
                        request.query,
                        conversation_history=conversation_history,
                    )
                except Exception as exc:
                    logger.warning("[STREAM] StateClassifier failed: %s", exc)
                    state_analysis = _fallback_state_analysis()
                pipeline_stages.append(
                    {
                        "name": "state_classifier",
                        "label": "Классификатор состояния",
                        "duration_ms": int((time.perf_counter() - stage_start) * 1000),
                        "skipped": False,
                    }
                )

                stage_start = time.perf_counter()
                if sd_classifier is None:
                    sd_result = _fallback_sd_result("sd_classifier_unavailable")
                else:
                    try:
                        sd_result = await sd_classifier.classify_user(
                            message=request.query,
                            conversation_history=conversation_history_for_sd,
                            user_sd_profile=memory.get_user_sd_profile(),
                        )
                    except Exception as exc:
                        logger.warning("[STREAM] SDClassifier failed: %s", exc)
                        sd_result = _fallback_sd_result("fallback_on_error")
                pipeline_stages.append(
                    {
                        "name": "sd_classifier",
                        "label": "SD классификатор",
                        "duration_ms": int((time.perf_counter() - stage_start) * 1000),
                        "skipped": False,
                    }
                )
            else:
                state_analysis, sd_result = await _classify_parallel(
                    request.query,
                    conversation_history,
                    conversation_history_for_sd,
                    memory.get_user_sd_profile(),
                )
            user_stage = resolve_user_stage(memory, state_analysis)

            level_adapter = UserLevelAdapter(request.user_level.value)
            decision_gate = DecisionGate()

            pre_routing_signals = detect_routing_signals(request.query, [], state_analysis)
            pre_routing_result = decision_gate.route(pre_routing_signals, user_stage=user_stage)

            if _should_use_fast_path(request.query, pre_routing_result):
                mode_directive = build_mode_directive(
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    reason=pre_routing_result.decision.reason,
                    forbid=pre_routing_result.decision.forbid,
                )
                if request.debug:
                    pipeline_stages.extend(
                        [
                            {"name": "retrieval", "label": "Retrieval", "duration_ms": 0, "skipped": True},
                            {"name": "rerank", "label": "Rerank", "duration_ms": 0, "skipped": True},
                        ]
                    )
                fast_block = _build_fast_path_block(
                    query=request.query,
                    conversation_context=conversation_context,
                    state_analysis=state_analysis,
                )
                state_context = _build_state_context(
                    state_analysis,
                    mode_directive.prompt,
                    sd_level=sd_result.primary,
                )
                response_generator = ResponseGenerator()
                llm_start_ts = time.perf_counter()
                full_answer = ""
                async for token in response_generator.generate_stream(
                    request.query,
                    [fast_block],
                    conversation_context=conversation_context,
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    forbid=pre_routing_result.decision.forbid,
                    user_level_adapter=level_adapter,
                    additional_system_context=state_context,
                    sd_level=sd_result.primary,
                    model=config.LLM_MODEL,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.get_mode_max_tokens(pre_routing_result.mode),
                ):
                    full_answer += token
                    yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

                llm_duration_ms = int((time.perf_counter() - llm_start_ts) * 1000)
                if request.debug:
                    pipeline_stages.append(
                        {
                            "name": "llm",
                            "label": "LLM",
                            "duration_ms": llm_duration_ms,
                            "skipped": False,
                        }
                    )
                formatter = ResponseFormatter()
                format_start_ts = time.perf_counter()
                formatted = formatter.format_answer(
                    full_answer,
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                )
                if request.debug:
                    pipeline_stages.append(
                        {
                            "name": "format",
                            "label": "Форматирование",
                            "duration_ms": int((time.perf_counter() - format_start_ts) * 1000),
                            "skipped": False,
                        }
                    )
                if formatted.startswith(full_answer):
                    extra = formatted[len(full_answer):]
                    if extra:
                        full_answer = formatted
                        yield f"data: {json.dumps({'token': extra}, ensure_ascii=False)}\n\n"
                else:
                    full_answer = formatted

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

                memory.add_turn(
                    user_input=request.query,
                    bot_response=full_answer,
                    user_state=state_analysis.primary_state.value,
                    blocks_used=0,
                    concepts=[],
                )

                latency_ms = int((time.perf_counter() - start_ts) * 1000)
                done_payload = {
                    "done": True,
                    "mode": pre_routing_result.mode,
                    "sd_level": sd_result.primary,
                    "latency_ms": latency_ms,
                }
                if request.debug:
                    memory_metrics = _get_memory_trace_metrics(memory, len(memory.turns))
                    fast_path_reason = _detect_fast_path_reason(request.query, pre_routing_result)

                    system_preview, user_preview = _build_llm_prompt_previews(
                        response_generator=response_generator,
                        query=request.query,
                        blocks=[fast_block],
                        conversation_context=conversation_context,
                        user_level_adapter=level_adapter,
                        sd_level=sd_result.primary,
                        mode_prompt=mode_directive.prompt,
                        additional_system_context=state_context,
                    )
                    full_system_prompt, full_user_prompt = _build_llm_prompts(
                        response_generator=response_generator,
                        query=request.query,
                        blocks=[fast_block],
                        conversation_context=conversation_context,
                        user_level_adapter=level_adapter,
                        sd_level=sd_result.primary,
                        mode_prompt=mode_directive.prompt,
                        additional_system_context=state_context,
                    )

                    system_blob_id = _store_blob(store, session_key, full_system_prompt)
                    user_blob_id = _store_blob(store, session_key, full_user_prompt)

                    llm_calls = [
                        _build_llm_call_trace(
                            llm_result={"answer": full_answer},
                            step="fast_path",
                            system_prompt_preview=system_preview,
                            user_prompt_preview=user_preview,
                            fallback_error=None,
                            duration_ms=llm_duration_ms,
                            system_prompt_blob_id=system_blob_id,
                            user_prompt_blob_id=user_blob_id,
                        )
                    ]

                    context_written = _build_memory_context_snapshot(memory)
                    memory_snapshot_blob_id = _store_blob(store, session_key, context_written)

                    debug_trace = {
                        "sd_classification": {
                            "method": sd_result.method,
                            "primary": sd_result.primary,
                            "secondary": sd_result.secondary,
                            "confidence": sd_result.confidence,
                            "indicator": sd_result.indicator,
                            "allowed_levels": sd_result.allowed_blocks,
                        },
                        "chunks_retrieved": [],
                        "chunks_after_filter": [],
                        "llm_calls": llm_calls,
                        "context_written_to_memory": context_written,
                        "context_written": context_written,
                        "total_duration_ms": latency_ms,
                        "primary_model": config.LLM_MODEL,
                        "classifier_model": config.CLASSIFIER_MODEL,
                        "embedding_model": config.EMBEDDING_MODEL,
                        "reranker_model": config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None,
                        "reranker_enabled": bool(config.VOYAGE_ENABLED),
                        "tokens_prompt": None,
                        "tokens_completion": None,
                        "tokens_total": None,
                        "session_tokens_total": memory.metadata.get("session_tokens_total"),
                        "session_cost_usd": memory.metadata.get("session_cost_usd"),
                        "session_turns": memory.metadata.get("session_turns"),
                        "fast_path": True,
                        "fast_path_reason": fast_path_reason,
                        "decision_rule_id": str(pre_routing_result.decision.rule_id),
                        "mode_reason": mode_directive.reason,
                        "block_cap": 0,
                        "blocks_initial": 0,
                        "blocks_after_cap": 0,
                        "hybrid_query_preview": _truncate_preview(request.query, 400),
                        "sd_detail": sd_result.to_detail() if hasattr(sd_result, "to_detail") else None,
                        "memory_turns": len(memory.turns),
                        "memory_turns_content": memory.get_turns_preview() if hasattr(memory, "get_turns_preview") else [],
                        "summary_text": memory.summary or None,
                        "summary_length": len(memory.summary) if memory.summary else 0,
                        "summary_last_turn": memory.summary_updated_at,
                        "summary_used": memory_metrics.get("summary_used"),
                        "semantic_hits": memory_metrics.get("semantic_hits"),
                        "semantic_hits_detail": (
                            list(memory.semantic_memory.last_hits_detail or [])
                            if memory.semantic_memory and hasattr(memory.semantic_memory, "last_hits_detail")
                            else []
                        ),
                        "state_secondary": [s.value for s in state_analysis.secondary_states],
                        "state_trajectory": _build_state_trajectory(memory),
                        "pipeline_stages": pipeline_stages,
                        "anomalies": [],
                        "system_prompt_blob_id": system_blob_id,
                        "user_prompt_blob_id": user_blob_id,
                        "memory_snapshot_blob_id": memory_snapshot_blob_id,
                        "config_snapshot": _build_config_snapshot(config, request.user_level.value),
                        "estimated_cost_usd": _estimate_cost(llm_calls, str(config.LLM_MODEL)),
                        "pipeline_error": None,
                        "session_id": session_key,
                        "turn_number": len(memory.turns),
                        "sd_level": sd_result.primary,
                        "user_state": state_analysis.primary_state.value,
                        "recommended_mode": pre_routing_result.mode,
                        "confidence_score": pre_routing_result.confidence_score,
                        "confidence_level": pre_routing_result.confidence_level,
                    }

                    debug_trace["anomalies"] = _compute_anomalies(debug_trace)
                    done_payload["trace"] = debug_trace
                    try:
                        store.append_trace(session_key, debug_trace)
                    except Exception as store_exc:
                        logger.warning("[STREAM] Failed to store debug trace: %s", store_exc)

                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
                return

            query_builder = HybridQueryBuilder(max_chars=config.MAX_CONTEXT_SIZE + 1200)
            hybrid_query = query_builder.build_query(
                current_question=request.query,
                conversation_summary=memory.summary or "",
                working_state=memory.working_state,
                short_term_context=conversation_context,
            )

            retrieval_start_ts = time.perf_counter()
            raw_retrieved_blocks = retriever_dep.retrieve(hybrid_query, top_k=None)
            if request.debug:
                pipeline_stages.append(
                    {
                        "name": "retrieval",
                        "label": "Retrieval",
                        "duration_ms": int((time.perf_counter() - retrieval_start_ts) * 1000),
                        "skipped": False,
                    }
                )
            retrieved_blocks = list(raw_retrieved_blocks)

            reranker = VoyageReranker(
                model=config.VOYAGE_MODEL,
                enabled=config.VOYAGE_ENABLED,
            )
            rerank_k = min(len(retrieved_blocks), max(1, min(config.TOP_K_BLOCKS, config.VOYAGE_TOP_K)))
            if rerank_k > 0:
                rerank_start_ts = time.perf_counter()
                reranked = reranker.rerank_pairs(request.query, retrieved_blocks, top_k=rerank_k)
                if request.debug:
                    pipeline_stages.append(
                        {
                            "name": "rerank",
                            "label": "Rerank",
                            "duration_ms": int((time.perf_counter() - rerank_start_ts) * 1000),
                            "skipped": False,
                        }
                    )
                if reranked:
                    retrieved_blocks = reranked
            elif request.debug:
                pipeline_stages.append(
                    {"name": "rerank", "label": "Rerank", "duration_ms": 0, "skipped": True}
                )
            reranked_blocks_for_trace = list(retrieved_blocks)

            routing_signals = detect_routing_signals(request.query, retrieved_blocks, state_analysis)
            routing_result = decision_gate.route(routing_signals, user_stage=user_stage)
            block_cap = decision_gate.scorer.suggest_block_cap(
                len(retrieved_blocks),
                routing_result.confidence_level,
            )
            retrieved_blocks = retrieved_blocks[:block_cap]

            if not retrieved_blocks:
                fallback_text = (
                    "К сожалению, релевантный материал не найден. "
                    "Попробуйте переформулировать вопрос."
                )
                yield f"data: {json.dumps({'token': fallback_text}, ensure_ascii=False)}\n\n"
                memory.add_turn(
                    user_input=request.query,
                    bot_response=fallback_text,
                    user_state=state_analysis.primary_state.value,
                    blocks_used=0,
                    concepts=[],
                )
                if request.debug:
                    pipeline_stages.append(
                        {"name": "llm", "label": "LLM", "duration_ms": 0, "skipped": True}
                    )
                    pipeline_stages.append(
                        {"name": "format", "label": "Форматирование", "duration_ms": 0, "skipped": True}
                    )
                latency_ms = int((time.perf_counter() - start_ts) * 1000)
                done_payload = {
                    "done": True,
                    "mode": "CLARIFICATION",
                    "sd_level": sd_result.primary,
                    "latency_ms": latency_ms,
                }
                if request.debug:
                    memory_metrics = _get_memory_trace_metrics(memory, len(memory.turns))
                    chunks_retrieved, chunks_after_filter = _build_chunk_trace_lists_after_rerank(
                        initial_retrieved=raw_retrieved_blocks,
                        reranked=reranked_blocks_for_trace,
                    )
                    context_written = _build_memory_context_snapshot(memory)
                    memory_snapshot_blob_id = _store_blob(store, session_key, context_written)
                    debug_trace = {
                        "sd_classification": {
                            "method": sd_result.method,
                            "primary": sd_result.primary,
                            "secondary": sd_result.secondary,
                            "confidence": sd_result.confidence,
                            "indicator": sd_result.indicator,
                            "allowed_levels": sd_result.allowed_blocks,
                        },
                        "chunks_retrieved": chunks_retrieved,
                        "chunks_after_filter": chunks_after_filter,
                        "llm_calls": [],
                        "context_written_to_memory": context_written,
                        "context_written": context_written,
                        "total_duration_ms": latency_ms,
                        "primary_model": config.LLM_MODEL,
                        "classifier_model": config.CLASSIFIER_MODEL,
                        "embedding_model": config.EMBEDDING_MODEL,
                        "reranker_model": config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None,
                        "reranker_enabled": bool(config.VOYAGE_ENABLED),
                        "fast_path": False,
                        "decision_rule_id": str(routing_result.decision.rule_id),
                        "mode_reason": routing_result.decision.reason,
                        "block_cap": block_cap,
                        "blocks_initial": len(raw_retrieved_blocks),
                        "blocks_after_cap": 0,
                        "hybrid_query_preview": _truncate_preview(hybrid_query, 400),
                        "sd_detail": sd_result.to_detail() if hasattr(sd_result, "to_detail") else None,
                        "memory_turns": len(memory.turns),
                        "memory_turns_content": memory.get_turns_preview() if hasattr(memory, "get_turns_preview") else [],
                        "summary_text": memory.summary or None,
                        "summary_length": len(memory.summary) if memory.summary else 0,
                        "summary_last_turn": memory.summary_updated_at,
                        "summary_used": memory_metrics.get("summary_used"),
                        "semantic_hits": memory_metrics.get("semantic_hits"),
                        "semantic_hits_detail": (
                            list(memory.semantic_memory.last_hits_detail or [])
                            if memory.semantic_memory and hasattr(memory.semantic_memory, "last_hits_detail")
                            else []
                        ),
                        "state_secondary": [s.value for s in state_analysis.secondary_states],
                        "state_trajectory": _build_state_trajectory(memory),
                        "pipeline_stages": pipeline_stages,
                        "anomalies": [],
                        "memory_snapshot_blob_id": memory_snapshot_blob_id,
                        "config_snapshot": _build_config_snapshot(config, request.user_level.value),
                        "estimated_cost_usd": 0,
                        "pipeline_error": None,
                        "session_id": session_key,
                        "turn_number": len(memory.turns),
                        "sd_level": sd_result.primary,
                        "user_state": state_analysis.primary_state.value,
                        "recommended_mode": routing_result.mode,
                        "confidence_score": routing_result.confidence_score,
                        "confidence_level": routing_result.confidence_level,
                    }
                    debug_trace["anomalies"] = _compute_anomalies(debug_trace)
                    done_payload["trace"] = debug_trace
                    try:
                        store.append_trace(session_key, debug_trace)
                    except Exception as store_exc:
                        logger.warning("[STREAM] Failed to store debug trace: %s", store_exc)
                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
                return

            blocks = [block for block, _ in retrieved_blocks]
            adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
            if not adapted_blocks:
                adapted_blocks = blocks[:3]

            mode_directive = build_mode_directive(
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                reason=routing_result.decision.reason,
                forbid=routing_result.decision.forbid,
            )
            state_context = _build_state_context(
                state_analysis,
                mode_directive.prompt,
                sd_level=sd_result.primary,
            )

            response_generator = ResponseGenerator()
            llm_start_ts = time.perf_counter()
            full_answer = ""
            async for token in response_generator.generate_stream(
                request.query,
                adapted_blocks,
                conversation_context=conversation_context,
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                forbid=routing_result.decision.forbid,
                user_level_adapter=level_adapter,
                additional_system_context=state_context,
                sd_level=sd_result.primary,
                model=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.get_mode_max_tokens(routing_result.mode),
            ):
                full_answer += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

            llm_duration_ms = int((time.perf_counter() - llm_start_ts) * 1000)
            if request.debug:
                pipeline_stages.append(
                    {
                        "name": "llm",
                        "label": "LLM",
                        "duration_ms": llm_duration_ms,
                        "skipped": False,
                    }
                )
            formatter = ResponseFormatter()
            format_start_ts = time.perf_counter()
            formatted = formatter.format_answer(
                full_answer,
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
            )
            if request.debug:
                pipeline_stages.append(
                    {
                        "name": "format",
                        "label": "Форматирование",
                        "duration_ms": int((time.perf_counter() - format_start_ts) * 1000),
                        "skipped": False,
                    }
                )
            if formatted.startswith(full_answer):
                extra = formatted[len(full_answer):]
                if extra:
                    full_answer = formatted
                    yield f"data: {json.dumps({'token': extra}, ensure_ascii=False)}\n\n"
            else:
                full_answer = formatted

            try:
                memory.set_working_state(
                    _build_working_state(
                        state_analysis=state_analysis,
                        routing_result=routing_result,
                        memory=memory,
                    )
                )
            except Exception as exc:
                logger.warning(f"[ADAPTIVE-STREAM] working_state update failed: {exc}")

            memory.add_turn(
                user_input=request.query,
                bot_response=full_answer,
                user_state=state_analysis.primary_state.value,
                blocks_used=len(adapted_blocks),
                concepts=[],
            )

            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            done_payload = {
                "done": True,
                "mode": routing_result.mode,
                "sd_level": sd_result.primary,
                "latency_ms": latency_ms,
            }
            if request.debug:
                memory_metrics = _get_memory_trace_metrics(memory, len(memory.turns))
                chunks_retrieved, chunks_after_filter = _build_chunk_trace_lists_after_rerank(
                    initial_retrieved=raw_retrieved_blocks,
                    reranked=reranked_blocks_for_trace,
                )
                system_preview, user_preview = _build_llm_prompt_previews(
                    response_generator=response_generator,
                    query=request.query,
                    blocks=adapted_blocks,
                    conversation_context=conversation_context,
                    user_level_adapter=level_adapter,
                    sd_level=sd_result.primary,
                    mode_prompt=mode_directive.prompt,
                    additional_system_context=state_context,
                )
                full_system_prompt, full_user_prompt = _build_llm_prompts(
                    response_generator=response_generator,
                    query=request.query,
                    blocks=adapted_blocks,
                    conversation_context=conversation_context,
                    user_level_adapter=level_adapter,
                    sd_level=sd_result.primary,
                    mode_prompt=mode_directive.prompt,
                    additional_system_context=state_context,
                )
                system_blob_id = _store_blob(store, session_key, full_system_prompt)
                user_blob_id = _store_blob(store, session_key, full_user_prompt)
                llm_calls = [
                    _build_llm_call_trace(
                        llm_result={"answer": full_answer},
                        step="main_answer",
                        system_prompt_preview=system_preview,
                        user_prompt_preview=user_preview,
                        fallback_error=None,
                        duration_ms=llm_duration_ms,
                        system_prompt_blob_id=system_blob_id,
                        user_prompt_blob_id=user_blob_id,
                    )
                ]
                context_written = _build_memory_context_snapshot(memory)
                memory_snapshot_blob_id = _store_blob(store, session_key, context_written)
                debug_trace = {
                    "sd_classification": {
                        "method": sd_result.method,
                        "primary": sd_result.primary,
                        "secondary": sd_result.secondary,
                        "confidence": sd_result.confidence,
                        "indicator": sd_result.indicator,
                        "allowed_levels": sd_result.allowed_blocks,
                    },
                    "chunks_retrieved": chunks_retrieved,
                    "chunks_after_filter": chunks_after_filter,
                    "llm_calls": llm_calls,
                    "context_written_to_memory": context_written,
                    "context_written": context_written,
                    "total_duration_ms": latency_ms,
                    "primary_model": config.LLM_MODEL,
                    "classifier_model": config.CLASSIFIER_MODEL,
                    "embedding_model": config.EMBEDDING_MODEL,
                    "reranker_model": config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None,
                    "reranker_enabled": bool(config.VOYAGE_ENABLED),
                    "fast_path": False,
                    "decision_rule_id": str(routing_result.decision.rule_id),
                    "mode_reason": routing_result.decision.reason,
                    "block_cap": block_cap,
                    "blocks_initial": len(raw_retrieved_blocks),
                    "blocks_after_cap": len(retrieved_blocks),
                    "hybrid_query_preview": _truncate_preview(hybrid_query, 400),
                    "sd_detail": sd_result.to_detail() if hasattr(sd_result, "to_detail") else None,
                    "memory_turns": len(memory.turns),
                    "memory_turns_content": memory.get_turns_preview() if hasattr(memory, "get_turns_preview") else [],
                    "summary_text": memory.summary or None,
                    "summary_length": len(memory.summary) if memory.summary else 0,
                    "summary_last_turn": memory.summary_updated_at,
                    "summary_used": memory_metrics.get("summary_used"),
                    "semantic_hits": memory_metrics.get("semantic_hits"),
                    "semantic_hits_detail": (
                        list(memory.semantic_memory.last_hits_detail or [])
                        if memory.semantic_memory and hasattr(memory.semantic_memory, "last_hits_detail")
                        else []
                    ),
                    "state_secondary": [s.value for s in state_analysis.secondary_states],
                    "state_trajectory": _build_state_trajectory(memory),
                    "pipeline_stages": pipeline_stages,
                    "anomalies": [],
                    "system_prompt_blob_id": system_blob_id,
                    "user_prompt_blob_id": user_blob_id,
                    "memory_snapshot_blob_id": memory_snapshot_blob_id,
                    "config_snapshot": _build_config_snapshot(config, request.user_level.value),
                    "estimated_cost_usd": _estimate_cost(llm_calls, str(config.LLM_MODEL)),
                    "pipeline_error": None,
                    "session_id": session_key,
                    "turn_number": len(memory.turns),
                    "sd_level": sd_result.primary,
                    "user_state": state_analysis.primary_state.value,
                    "recommended_mode": routing_result.mode,
                    "confidence_score": routing_result.confidence_score,
                    "confidence_level": routing_result.confidence_level,
                }
                debug_trace["anomalies"] = _compute_anomalies(debug_trace)
                done_payload["trace"] = debug_trace
                try:
                    store.append_trace(session_key, debug_trace)
                except Exception as store_exc:
                    logger.warning("[STREAM] Failed to store debug trace: %s", store_exc)

            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
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
            user_level=summary.get("user_level", "beginner"),
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
        total_users=len(_stats["total_users"]),
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








