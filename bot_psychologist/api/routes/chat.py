"""Chat-роуты API: /questions/* и streaming."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from bot_agent import answer_question_adaptive
from bot_agent.config import config
from bot_agent.conversation_memory import get_conversation_memory
from bot_agent.llm_streaming import stream_answer_tokens
from bot_agent.storage import SessionManager

from ..auth import is_dev_key, verify_api_key
from ..dependencies import (
    get_conversation_service,
    get_data_loader,
    get_graph_client,
    get_identity_context,
    get_retriever,
)
from ..identity import IdentityContext
from ..models import (
    AdaptiveAnswerResponse,
    AnswerResponse,
    AskQuestionRequest,
    ChunkTraceItem,
    ConversationTurnResponse,
    DebugTrace,
    LLMCallTrace,
    PathRecommendationResponse,
    PathStepResponse,
    SourceResponse,
    StateAnalysisResponse,
)
from ..session_store import SessionStore, get_session_store
from .common import (
    _append_trace_with_resolved_session,
    _build_answer_response_from_adaptive,
    _record_user,
    _run_neo_compat_answer,
    _strip_legacy_runtime_metadata,
    _strip_legacy_trace_fields,
    _to_chunk_trace_item,
    logger,
    _stats,
)

router = APIRouter(prefix="/api/v1", tags=["bot"])


def _resolve_answer_question_adaptive():
    """Возвращает answer-функцию с учетом monkeypatch в api.routes."""
    try:
        from api import routes as routes_pkg  # runtime import для избежания циклов

        candidate = getattr(routes_pkg, "answer_question_adaptive", None)
        if callable(candidate):
            return candidate
    except Exception:
        pass
    return answer_question_adaptive


def _resolve_stream_answer_tokens():
    """Возвращает stream-функцию с учетом monkeypatch в api.routes."""
    try:
        from api import routes as routes_pkg  # runtime import для избежания циклов

        candidate = getattr(routes_pkg, "stream_answer_tokens", None)
        if callable(candidate):
            return candidate
    except Exception:
        pass
    return stream_answer_tokens


@router.post(
    "/questions/basic",
    response_model=AnswerResponse,
    summary="Phase 1: Базовый QA",
    description="Базовый вопрос-ответ (Phase 1)"
)
async def ask_basic_question(
    request: AskQuestionRequest,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    conv_service=Depends(get_conversation_service),
):
    """
    **Phase 1:** Базовый QA без адаптации.
    
    спользует:
    - TF-IDF retrieval
    - GPT LLM
    - Простой ответ
    
    **Пример:**
    ```
    {
      "query": "Что такое осознавание?",
      "user_id": "user_123"
    }
    ```
    """
    
    logger.info(f"[NEO_COMPAT] Basic endpoint routed to adaptive runtime: {request.query[:50]}...")

    try:
        normalized_request = request.model_copy(
            update={"user_id": identity.user_id, "session_id": identity.session_id},
        )
        result = _run_neo_compat_answer(request=normalized_request)
        await conv_service.touch_conversation(identity.conversation_id)
        _record_user(identity.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        return _build_answer_response_from_adaptive(result)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
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
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    conv_service=Depends(get_conversation_service),
):
    """
    Phase 1 enhanced: basic QA with memory.
    """
    logger.info(f"[NEO_COMPAT] Basic+Semantic endpoint routed to adaptive runtime: {request.query[:50]}...")

    try:
        normalized_request = request.model_copy(
            update={"user_id": identity.user_id, "session_id": identity.session_id},
        )
        result = _run_neo_compat_answer(request=normalized_request)
        await conv_service.touch_conversation(identity.conversation_id)
        _record_user(identity.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        return _build_answer_response_from_adaptive(result)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/questions/graph-powered",
    response_model=AnswerResponse,
    summary="Phase 3: Knowledge Graph QA",
    description="QA с использованием Knowledge Graph"
)
async def ask_graph_powered_question(
    request: AskQuestionRequest,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
    conv_service=Depends(get_conversation_service),
):
    """
    **Phase 3:** Graph-powered QA с использованием Knowledge Graph.
    
    спользует:
    - TF-IDF retrieval
    - Knowledge Graph (95 узлов, 2182 связи)
    - Concept hierarchy
    - Практики из графа
    """
    
    logger.info(f"[NEO_COMPAT] Graph-powered endpoint routed to adaptive runtime: {request.query[:50]}...")

    try:
        normalized_request = request.model_copy(
            update={"user_id": identity.user_id, "session_id": identity.session_id},
        )
        result = _run_neo_compat_answer(request=normalized_request, session_store=store)
        await conv_service.touch_conversation(identity.conversation_id)
        _record_user(identity.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        return _build_answer_response_from_adaptive(result)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post(
    "/questions/adaptive",
    response_model=AdaptiveAnswerResponse,
    response_model_exclude_none=True,
    summary="Phase 4: Adaptive QA",
    description="Полностью адаптивный QA с анализом состояния и персональными путями"
)
async def ask_adaptive_question(
    request: AskQuestionRequest,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    _data_loader=Depends(get_data_loader),
    _graph_client=Depends(get_graph_client),
    _retriever=Depends(get_retriever),
    store: SessionStore = Depends(get_session_store),
    conv_service=Depends(get_conversation_service),
):
    """
    **Phase 4:** Полностью адаптивный QA.
    
    спользует:
    - State Classification (10 состояний)
    - Conversation Memory (история диалога)
    - Personal Path Building (персональные пути)
    - Все возможности Phase 1-3
    
    **Возвращает:**
    - Адаптивный ответ
    - Анализ состояния пользователя
    - Рекомендацию персонального пути
    - Адаптивный запрос обратной связи
    """
    
    logger.info(
        "[ADAPTIVE] Adaptive question: %s... (user=%s session=%s)",
        request.query[:50],
        identity.user_id,
        identity.session_id,
    )

    try:
        session_key = identity.session_id

        # Dev-   debug-
        if is_dev_key(api_key):
            request.debug = True

        if request.session_id:
            try:
                session_manager = SessionManager(str(config.BOT_DB_PATH))
                session_manager.create_session(
                    session_id=session_key,
                    user_id=identity.user_id,
                    metadata={
                        "source": "api",
                        "owner_user_id": identity.user_id,
                    },
                )
            except Exception as exc:
                logger.warning(f" Failed to pre-create session {session_key}: {exc}")

        result = _resolve_answer_question_adaptive()(
            request.query,
            user_id=identity.user_id,
            include_path_recommendation=request.include_path,
            include_feedback_prompt=request.include_feedback_prompt,
            debug=request.debug,
            session_store=store,
        )
        await conv_service.touch_conversation(identity.conversation_id)
        
        # Обновить статистику
        _record_user(identity.user_id)
        _stats["total_questions"] += 1
        _stats["total_processing_time"] += result.get("processing_time_seconds", 0)
        
        state = result.get("state_analysis", {}).get("primary_state", "unknown")
        _stats["states_count"][state] = _stats["states_count"].get(state, 0) + 1
        
        # Преобразовать sources
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
        
        # Построить state_analysis
        state_analysis_data = result.get("state_analysis", {})
        state_analysis = StateAnalysisResponse(
            primary_state=state_analysis_data.get("primary_state", "unknown"),
            confidence=state_analysis_data.get("confidence", 0),
            emotional_tone=state_analysis_data.get("emotional_tone", ""),
            recommendations=state_analysis_data.get("recommendations", [])
        )
        
        # Построить path_recommendation
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
        response_metadata["user_id"] = identity.user_id
        response_metadata["session_id"] = session_key
        response_metadata["conversation_id"] = identity.conversation_id

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

                # Fallback:   debug  ,    sources      .
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
        logger.error(f"❌ Ошибка: {e}")
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
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    _data_loader=Depends(get_data_loader),
    store: SessionStore = Depends(get_session_store),
    conv_service=Depends(get_conversation_service),
):
    if not config.ENABLE_STREAMING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming is disabled",
        )

    logger.info(
        "[ADAPTIVE-STREAM] query: %s... (user=%s session=%s)",
        request.query[:50],
        identity.user_id,
        identity.session_id,
    )

    session_key = identity.session_id

    if is_dev_key(api_key):
        request.debug = True

    if request.session_id:
        try:
            session_manager = SessionManager(str(config.BOT_DB_PATH))
            session_manager.create_session(
                session_id=session_key,
                user_id=identity.user_id,
                metadata={
                    "source": "api",
                    "owner_user_id": identity.user_id,
                },
            )
        except Exception as exc:
            logger.warning(f" Failed to pre-create session {session_key}: {exc}")

    _result_holder: dict = {}

    def _on_complete(result: dict) -> None:
        _result_holder.update(result)

    async def event_stream():
        try:
            async for token in _resolve_stream_answer_tokens()(
                request.query,
                user_id=identity.user_id,
                session_store=store,
                include_path=request.include_path,
                include_feedback_prompt=request.include_feedback_prompt,
                debug=request.debug,
                on_complete=_on_complete,
                answer_fn=_resolve_answer_question_adaptive(),
            ):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

            result = dict(_result_holder)
            answer = str(result.get("answer", "") or "")
            await conv_service.touch_conversation(identity.conversation_id)

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
                memory = get_conversation_memory(identity.user_id)
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

