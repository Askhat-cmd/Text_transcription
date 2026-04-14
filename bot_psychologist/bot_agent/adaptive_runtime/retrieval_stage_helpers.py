"""Retrieval-stage helpers extracted from answer_adaptive orchestration."""

from __future__ import annotations

from typing import Any, Dict, List

from .pipeline_utils import _timed as _runtime_timed


def _prepare_hybrid_query_stage(
    *,
    query: str,
    diagnostics_v1,
    state_analysis,
    memory,
    conversation_context: str,
    config,
    logger,
) -> Dict[str, Any]:
    from ..retrieval import HybridQueryBuilder as _HybridQueryBuilder
    from .trace_helpers import _recent_user_turns as _recent_user_turns

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
    query_builder = _HybridQueryBuilder(max_chars=config.MAX_CONTEXT_SIZE + 1200)
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
    return {
        "retrieval_working_state": retrieval_working_state,
        "recent_user_turns": recent_user_turns,
        "hybrid_query": hybrid_query,
    }


def _retrieve_blocks_with_degraded_mode(
    *,
    query: str,
    hybrid_query: str,
    top_k: int,
    config,
    data_loader,
    get_retriever_fn,
    logger,
) -> Dict[str, Any]:
    retrieval_degraded_reason = None
    try:
        retriever = get_retriever_fn()
    except Exception as exc:
        logger.warning("[RETRIEVAL] get_retriever failed, degraded mode enabled: %s", exc)
        retriever = None
        retrieval_degraded_reason = "retriever_init_failed"

    author_id_filter = None
    author_map = {}
    if config.AUTHOR_BLEND_MODE in {"single", "blend"}:
        from ..semantic_analyzer import detect_author_intent as _detect_author_intent

        for block in data_loader.get_all_blocks():
            if block.author and block.author_id:
                author_map[block.author] = block.author_id

        if author_map:
            author_name = _detect_author_intent(query, list(author_map.keys()))
            if author_name:
                author_id_filter = author_map.get(author_name)
                logger.info(
                    "[RETRIEVAL] author intent detected: %s (%s)",
                    author_name,
                    author_id_filter,
                )

    if retriever is None:
        raw_retrieved_blocks = []
        stage = {
            "name": "retrieval",
            "label": "Retrieval (degraded)",
            "duration_ms": 0,
            "skipped": True,
        }
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
                stage = {
                    "name": "retrieval",
                    "label": "Retrieval (blend)",
                    "duration_ms": 0,
                    "skipped": False,
                }
            else:
                raw_retrieved_blocks, stage = _runtime_timed(
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
            stage = {
                "name": "retrieval",
                "label": "Retrieval (degraded)",
                "duration_ms": 0,
                "skipped": True,
            }

    return {
        "raw_retrieved_blocks": raw_retrieved_blocks,
        "stage": stage,
        "retrieval_degraded_reason": retrieval_degraded_reason,
        "author_id_filter": author_id_filter,
        "author_map": author_map,
    }


def _dedupe_and_apply_progressive_rag(
    *,
    raw_retrieved_blocks: List[Any],
    progressive_rag,
    debug_trace: Dict[str, Any] | None,
    logger,
) -> List[Any]:
    seen_ids = set()
    deduped_blocks = []
    for block, score in raw_retrieved_blocks:
        if block.block_id not in seen_ids:
            seen_ids.add(block.block_id)
            deduped_blocks.append((block, score))

    if len(deduped_blocks) < len(raw_retrieved_blocks):
        logger.info(
            "[RETRIEVAL] Deduped %s duplicate blocks (%s -> %s)",
            len(raw_retrieved_blocks) - len(deduped_blocks),
            len(raw_retrieved_blocks),
            len(deduped_blocks),
        )

    processed_blocks = deduped_blocks
    try:
        processed_blocks = progressive_rag.rerank_by_weights(processed_blocks)
        if debug_trace is not None:
            debug_trace["progressive_rag_enabled"] = True
    except Exception as exc:
        logger.warning("[PROGRESSIVE_RAG] rerank_by_weights failed: %s", exc)
        if debug_trace is not None:
            debug_trace["progressive_rag_enabled"] = False
            debug_trace["progressive_rag_error"] = str(exc)

    return processed_blocks


def _prepare_conditional_rerank(
    *,
    retrieved_blocks: List[Any],
    top_k: int,
    config,
    use_deterministic_router: bool,
    diagnostics_v1,
    pre_routing_result,
) -> Dict[str, Any]:
    from ..feature_flags import feature_flags as _feature_flags
    from ..reranker_gate import should_rerank as _should_rerank

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
        rerank_mode = pre_routing_result.mode if pre_routing_result is not None else "PRESENCE"
        rerank_confidence = (
            float(pre_routing_result.confidence_score)
            if pre_routing_result is not None
            else 0.5
        )

    conditional_reranker = _feature_flags.enabled("ENABLE_CONDITIONAL_RERANKER")
    rerank_flags = {
        "legacy_always_on": bool(
            config.VOYAGE_ENABLED and (not conditional_reranker or not config.RERANKER_ENABLED)
        ),
        "RERANKER_ENABLED": bool(config.RERANKER_ENABLED and conditional_reranker),
        "RERANKER_CONFIDENCE_THRESHOLD": float(config.RERANKER_CONFIDENCE_THRESHOLD),
        "RERANKER_MODE_WHITELIST": str(config.RERANKER_MODE_WHITELIST),
        "RERANKER_BLOCK_THRESHOLD": int(config.RERANKER_BLOCK_THRESHOLD),
    }
    should_run_rerank, rerank_reason = _should_rerank(
        confidence_score=rerank_confidence,
        routing_mode=rerank_mode,
        retrieved_block_count=len(retrieved_blocks),
        flags=rerank_flags,
    )
    rerank_k = min(len(retrieved_blocks), max(1, min(top_k, config.VOYAGE_TOP_K)))

    return {
        "rerank_mode": rerank_mode,
        "rerank_confidence": rerank_confidence,
        "conditional_reranker": conditional_reranker,
        "rerank_flags": rerank_flags,
        "should_run_rerank": should_run_rerank,
        "rerank_reason": rerank_reason,
        "rerank_k": rerank_k,
    }


def _run_retrieval_and_rerank_stage(
    *,
    query: str,
    top_k: int,
    config,
    data_loader,
    get_retriever_fn,
    logger,
    debug_trace,
    pipeline_stages,
    log_retrieval_pairs_fn,
    use_deterministic_router: bool,
    diagnostics_v1,
    pre_routing_result,
    voyage_reranker_cls,
    detect_routing_signals_fn,
    state_analysis,
    memory,
    hybrid_query: str,
) -> Dict[str, Any]:
    from ..progressive_rag import get_progressive_rag as _get_progressive_rag

    retrieval_stage = _retrieve_blocks_with_degraded_mode(
        query=query,
        hybrid_query=hybrid_query,
        top_k=top_k,
        config=config,
        data_loader=data_loader,
        get_retriever_fn=get_retriever_fn,
        logger=logger,
    )
    raw_retrieved_blocks = retrieval_stage["raw_retrieved_blocks"]
    stage = retrieval_stage["stage"]
    retrieval_degraded_reason = retrieval_stage["retrieval_degraded_reason"]

    if debug_trace is not None:
        pipeline_stages.append(stage)
        if retrieval_degraded_reason:
            debug_trace["retrieval_degraded_reason"] = retrieval_degraded_reason

    progressive_rag = _get_progressive_rag(str(config.BOT_DB_PATH))
    raw_retrieved_blocks = _dedupe_and_apply_progressive_rag(
        raw_retrieved_blocks=raw_retrieved_blocks,
        progressive_rag=progressive_rag,
        debug_trace=debug_trace,
        logger=logger,
    )

    log_retrieval_pairs_fn("Initial retrieval", raw_retrieved_blocks, limit=10)
    retrieved_blocks = list(raw_retrieved_blocks)
    initial_retrieved_blocks = list(raw_retrieved_blocks)
    rerank_prep = _prepare_conditional_rerank(
        retrieved_blocks=retrieved_blocks,
        top_k=top_k,
        config=config,
        use_deterministic_router=use_deterministic_router,
        diagnostics_v1=diagnostics_v1,
        pre_routing_result=pre_routing_result,
    )
    rerank_mode = rerank_prep["rerank_mode"]
    conditional_reranker = rerank_prep["conditional_reranker"]
    should_run_rerank = rerank_prep["should_run_rerank"]
    rerank_reason = rerank_prep["rerank_reason"]
    rerank_k = rerank_prep["rerank_k"]
    rerank_applied = False

    if should_run_rerank and rerank_k > 0:
        reranker = voyage_reranker_cls(
            model=config.VOYAGE_MODEL,
            enabled=bool(
                config.VOYAGE_ENABLED
                or (conditional_reranker and config.RERANKER_ENABLED)
            ),
        )
        reranked, rerank_stage = _runtime_timed(
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
                (
                    config.VOYAGE_ENABLED
                    or (conditional_reranker and config.RERANKER_ENABLED)
                )
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
    routing_signals = detect_routing_signals_fn(
        query,
        retrieved_blocks,
        state_analysis,
        memory=memory,
    )

    return {
        "retrieved_blocks": retrieved_blocks,
        "initial_retrieved_blocks": initial_retrieved_blocks,
        "reranked_blocks_for_trace": reranked_blocks_for_trace,
        "progressive_rag": progressive_rag,
        "rerank_mode": rerank_mode,
        "conditional_reranker": conditional_reranker,
        "should_run_rerank": should_run_rerank,
        "rerank_reason": rerank_reason,
        "rerank_k": rerank_k,
        "rerank_applied": rerank_applied,
        "routing_signals": routing_signals,
    }


def _run_retrieval_routing_context_stage(
    *,
    query: str,
    top_k: int,
    config,
    data_loader,
    get_retriever_fn,
    logger,
    debug_trace,
    pipeline_stages,
    log_retrieval_pairs_fn,
    use_deterministic_router: bool,
    diagnostics_v1,
    pre_routing_result,
    voyage_reranker_cls,
    detect_routing_signals_fn,
    state_analysis,
    memory,
    conversation_context: str,
    resolve_routing_and_apply_block_cap_fn,
    user_stage,
    route_resolver,
    confidence_scorer,
    decision_gate,
    informational_branch_enabled: bool,
    resolve_mode_prompt_fn,
    build_mode_directive_fn,
    finalize_routing_context_and_trace_fn,
    phase8_signals,
    correction_protocol_active: bool,
    build_first_turn_instruction_fn,
    build_mixed_query_instruction_fn,
    build_user_correction_instruction_fn,
    build_informational_guardrail_instruction_fn,
    practice_selector,
    practice_allowed_routes,
    practice_skip_routes,
    memory_context_bundle,
    mode_prompt_key,
    route_resolution_count: int,
    truncate_preview_fn,
    refresh_context_and_apply_trace_snapshot_fn,
    run_no_retrieval_stage_fn,
    start_time,
    schedule_summary_task: bool,
    debug_info,
    session_store,
    user_id: str,
    set_working_state_best_effort_fn,
    persist_turn_fn,
    finalize_failure_debug_trace_fn,
    estimate_cost_fn,
    compute_anomalies_fn,
    attach_trace_schema_fn,
    build_state_trajectory_fn,
    store_blob_fn,
    prepare_adapted_blocks_and_attach_observability_fn,
    model_used: str,
) -> Dict[str, Any]:
    hybrid_query_stage = _prepare_hybrid_query_stage(
        query=query,
        diagnostics_v1=diagnostics_v1,
        state_analysis=state_analysis,
        memory=memory,
        conversation_context=conversation_context,
        config=config,
        logger=logger,
    )
    hybrid_query = hybrid_query_stage["hybrid_query"]

    retrieval_stage = _run_retrieval_and_rerank_stage(
        query=query,
        top_k=top_k,
        config=config,
        data_loader=data_loader,
        get_retriever_fn=get_retriever_fn,
        logger=logger,
        debug_trace=debug_trace,
        pipeline_stages=pipeline_stages,
        log_retrieval_pairs_fn=log_retrieval_pairs_fn,
        use_deterministic_router=use_deterministic_router,
        diagnostics_v1=diagnostics_v1,
        pre_routing_result=pre_routing_result,
        voyage_reranker_cls=voyage_reranker_cls,
        detect_routing_signals_fn=detect_routing_signals_fn,
        state_analysis=state_analysis,
        memory=memory,
        hybrid_query=hybrid_query,
    )
    retrieved_blocks = retrieval_stage["retrieved_blocks"]
    initial_retrieved_blocks = retrieval_stage["initial_retrieved_blocks"]
    reranked_blocks_for_trace = retrieval_stage["reranked_blocks_for_trace"]
    progressive_rag = retrieval_stage["progressive_rag"]
    should_run_rerank = retrieval_stage["should_run_rerank"]
    rerank_reason = retrieval_stage["rerank_reason"]
    rerank_k = retrieval_stage["rerank_k"]
    rerank_applied = retrieval_stage["rerank_applied"]
    routing_signals = retrieval_stage["routing_signals"]

    current_stage = "rerank" if rerank_applied else "retrieval"

    routing_cap_stage = resolve_routing_and_apply_block_cap_fn(
        use_deterministic_router=use_deterministic_router,
        diagnostics_v1=diagnostics_v1,
        user_stage=user_stage,
        route_resolver=route_resolver,
        confidence_scorer=confidence_scorer,
        pre_routing_result=pre_routing_result,
        decision_gate=decision_gate,
        retrieved_blocks=retrieved_blocks,
        informational_branch_enabled=informational_branch_enabled,
        resolve_mode_prompt_fn=resolve_mode_prompt_fn,
        config=config,
        log_retrieval_pairs_fn=log_retrieval_pairs_fn,
        build_mode_directive_fn=build_mode_directive_fn,
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

    routing_context_stage = finalize_routing_context_and_trace_fn(
        informational_branch_enabled=informational_branch_enabled,
        phase8_signals=phase8_signals,
        correction_protocol_active=correction_protocol_active,
        informational_mode=informational_mode,
        build_first_turn_instruction_fn=build_first_turn_instruction_fn,
        build_mixed_query_instruction_fn=build_mixed_query_instruction_fn,
        build_user_correction_instruction_fn=build_user_correction_instruction_fn,
        build_informational_guardrail_instruction_fn=build_informational_guardrail_instruction_fn,
        routing_result=routing_result,
        diagnostics_v1=diagnostics_v1,
        query=query,
        memory=memory,
        practice_selector=practice_selector,
        practice_allowed_routes=practice_allowed_routes,
        practice_skip_routes=practice_skip_routes,
        logger=logger,
        debug_trace=debug_trace,
        mode_reason=mode_directive.reason,
        block_cap=block_cap,
        initial_retrieved_blocks=initial_retrieved_blocks,
        hybrid_query=hybrid_query,
        include_full_content=bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True)),
        truncate_preview_fn=truncate_preview_fn,
        should_run_rerank=bool(should_run_rerank),
        rerank_reason=rerank_reason,
        rerank_applied=bool(rerank_applied),
        route_resolution_count=route_resolution_count,
        mode_prompt_key=mode_prompt_key,
        conversation_context=conversation_context,
        memory_context_bundle=memory_context_bundle,
        refresh_context_and_apply_trace_snapshot_fn=refresh_context_and_apply_trace_snapshot_fn,
    )
    phase8_context_suffix = routing_context_stage["phase8_context_suffix"]
    selected_practice = routing_context_stage["selected_practice"]
    practice_alternatives = routing_context_stage["practice_alternatives"]
    practice_context_suffix = routing_context_stage["practice_context_suffix"]
    conversation_context = routing_context_stage["conversation_context"]

    if not retrieved_blocks:
        return {
            "current_stage": current_stage,
            "early_response": run_no_retrieval_stage_fn(
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
                set_working_state_best_effort_fn=set_working_state_best_effort_fn,
                persist_turn_fn=persist_turn_fn,
                finalize_failure_debug_trace_fn=finalize_failure_debug_trace_fn,
                estimate_cost_fn=estimate_cost_fn,
                compute_anomalies_fn=compute_anomalies_fn,
                attach_trace_schema_fn=attach_trace_schema_fn,
                build_state_trajectory_fn=build_state_trajectory_fn,
                store_blob_fn=store_blob_fn,
            ),
        }

    retrieval_observability_stage = prepare_adapted_blocks_and_attach_observability_fn(
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
    )

    return {
        "current_stage": current_stage,
        "early_response": None,
        "hybrid_query": hybrid_query,
        "initial_retrieved_blocks": initial_retrieved_blocks,
        "reranked_blocks_for_trace": reranked_blocks_for_trace,
        "routing_result": routing_result,
        "block_cap": block_cap,
        "route_resolution_count": route_resolution_count,
        "informational_mode": informational_mode,
        "mode_prompt_key": mode_prompt_key,
        "mode_prompt_override": mode_prompt_override,
        "mode_directive": mode_directive,
        "state_context_mode_prompt": state_context_mode_prompt,
        "phase8_context_suffix": phase8_context_suffix,
        "selected_practice": selected_practice,
        "practice_alternatives": practice_alternatives,
        "practice_context_suffix": practice_context_suffix,
        "conversation_context": conversation_context,
        "blocks": retrieval_observability_stage["blocks"],
        "adapted_blocks": retrieval_observability_stage["adapted_blocks"],
    }
