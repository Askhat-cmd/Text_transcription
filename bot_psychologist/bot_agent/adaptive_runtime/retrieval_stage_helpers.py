"""Retrieval-stage helpers extracted from answer_adaptive orchestration."""

from __future__ import annotations

from typing import Any, Callable, Dict, List


def _retrieve_blocks_with_degraded_mode(
    *,
    query: str,
    hybrid_query: str,
    top_k: int,
    config,
    data_loader,
    get_retriever_fn,
    timed_fn,
    detect_author_intent_fn: Callable[[str, List[str]], str | None],
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
        for block in data_loader.get_all_blocks():
            if block.author and block.author_id:
                author_map[block.author] = block.author_id

        if author_map:
            author_name = detect_author_intent_fn(query, list(author_map.keys()))
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
                raw_retrieved_blocks, stage = timed_fn(
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
    feature_flag_enabled_fn,
    should_rerank_fn,
) -> Dict[str, Any]:
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

    conditional_reranker = feature_flag_enabled_fn("ENABLE_CONDITIONAL_RERANKER")
    rerank_flags = {
        "legacy_always_on": bool(
            config.VOYAGE_ENABLED and (not conditional_reranker or not config.RERANKER_ENABLED)
        ),
        "RERANKER_ENABLED": bool(config.RERANKER_ENABLED and conditional_reranker),
        "RERANKER_CONFIDENCE_THRESHOLD": float(config.RERANKER_CONFIDENCE_THRESHOLD),
        "RERANKER_MODE_WHITELIST": str(config.RERANKER_MODE_WHITELIST),
        "RERANKER_BLOCK_THRESHOLD": int(config.RERANKER_BLOCK_THRESHOLD),
    }
    should_run_rerank, rerank_reason = should_rerank_fn(
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
