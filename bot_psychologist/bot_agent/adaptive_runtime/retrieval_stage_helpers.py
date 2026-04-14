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
