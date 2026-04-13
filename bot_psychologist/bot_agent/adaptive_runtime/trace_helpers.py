"""Trace/retrieval/LLM helper utilities for adaptive orchestration."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..config import config
from ..data_loader import Block
from ..memory_updater import memory_updater
from ..response import ResponseGenerator

logger = logging.getLogger(__name__)

LEGACY_RUNTIME_METADATA_KEYS = (
    "decision_rule_id",
    "mode_reason",
    "confidence_level",
    "confidence_score",
)


def _strip_legacy_runtime_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(metadata or {})
    for key in LEGACY_RUNTIME_METADATA_KEYS:
        cleaned.pop(key, None)
    return cleaned


def _strip_legacy_trace_fields(debug_trace: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(debug_trace, dict):
        return debug_trace

    cleaned = dict(debug_trace)
    for key in LEGACY_RUNTIME_METADATA_KEYS:
        cleaned.pop(key, None)

    cfg_snapshot = cleaned.get("config_snapshot")
    if isinstance(cfg_snapshot, dict):
        snapshot_cleaned = dict(cfg_snapshot)
        cleaned["config_snapshot"] = snapshot_cleaned

    return cleaned


def _log_retrieval_pairs(stage: str, pairs, limit: int = 5) -> None:
    logger.info(f"[RETRIEVAL] {stage}: {len(pairs)} blocks")
    for i, (block, score) in enumerate(pairs[:limit], start=1):
        title = (block.title or "")[:60]
        logger.info(
            f"[RETRIEVAL]   [{i}] block_id={block.block_id} score={float(score):.4f} title={title}"
        )


def _log_blocks(stage: str, blocks, limit: int = 5) -> None:
    logger.info(f"[RETRIEVAL] {stage}: {len(blocks)} blocks")
    for i, block in enumerate(blocks[:limit], start=1):
        title = (block.title or "")[:60]
        logger.info(f"[RETRIEVAL]   [{i}] block_id={block.block_id} title={title}")


def _truncate_preview(text: Optional[str], max_len: int = 300) -> str:
    value = str(text or "")
    return value[:max_len]


def _extract_block_trace_fields(block) -> Tuple[str, str]:
    metadata = getattr(block, "metadata", {}) or {}
    emotional_tone = getattr(block, "emotional_tone", None) or metadata.get("emotional_tone")
    return (
        str(emotional_tone or ""),
        str(getattr(block, "block_type", None) or metadata.get("block_type") or ""),
    )


def _build_chunk_trace_item(
    *,
    block,
    score_initial: float,
    score_final: float,
    passed_filter: bool,
    filter_reason: str,
) -> Dict:
    emotional_tone, block_type = _extract_block_trace_fields(block)
    preview_source = getattr(block, "content", None) or getattr(block, "summary", None) or ""
    full_text = getattr(block, "content", None) or getattr(block, "summary", None) or ""
    return {
        "block_id": str(getattr(block, "block_id", "")),
        "title": str(getattr(block, "title", "")),
        "block_type": block_type,
        "emotional_tone": emotional_tone,
        "score_initial": float(score_initial),
        "score_final": float(score_final),
        "passed_filter": bool(passed_filter),
        "filter_reason": str(filter_reason or ""),
        "preview": _truncate_preview(preview_source, 120),
        "text": full_text,  # FIX 1a: полный текст чанка
    }


def _build_chunk_trace_lists_after_rerank(
    *,
    initial_retrieved: List[Tuple],
    reranked: List[Tuple],
) -> Tuple[List[Dict], List[Dict]]:
    """Построить списки чанков для trace: все retrieved и после rerank."""
    chunks_retrieved: List[Dict] = []
    chunks_after_rerank: List[Dict] = []

    reranked_scores = {
        str(getattr(block, "block_id", "")): float(score)
        for block, score in reranked
    }

    reranked_ids = {str(getattr(block, "block_id", "")) for block, _ in reranked}

    for block, initial_score in initial_retrieved:
        block_id = str(getattr(block, "block_id", ""))
        passed = block_id in reranked_ids

        item = _build_chunk_trace_item(
            block=block,
            score_initial=float(initial_score),
            score_final=reranked_scores.get(block_id, float(initial_score)),
            passed_filter=passed,
            filter_reason="" if passed else "rerank",
        )
        chunks_retrieved.append(item)
        if passed:
            chunks_after_rerank.append(item)

    return chunks_retrieved, chunks_after_rerank


def _get_memory_trace_metrics(memory, context_turns: int) -> Dict[str, object]:
    summary_used = bool(
        config.ENABLE_CONVERSATION_SUMMARY
        and memory.summary
        and context_turns > 20
    )
    if config.ENABLE_SEMANTIC_MEMORY and memory.semantic_memory and context_turns >= 3:
        semantic_hits = int(getattr(memory.semantic_memory, "last_hits_count", 0) or 0)
    else:
        semantic_hits = 0
    return {
        "summary_used": summary_used,
        "semantic_hits": semantic_hits,
    }


def _recent_user_turns(memory, limit: int = 2) -> List[str]:
    turns = list(getattr(memory, "turns", []) or [])
    user_turns = []
    for turn in reversed(turns):
        text = str(getattr(turn, "user_input", "") or "").strip()
        if text:
            user_turns.append(text)
        if len(user_turns) >= max(1, limit):
            break
    user_turns.reverse()
    return user_turns


def _log_context_build(memory, conversation_context: str, memory_context_bundle) -> None:
    mode = "summary" if bool(getattr(memory_context_bundle, "summary_used", False)) else "full"
    summary_len = len(getattr(memory, "summary", "") or "")
    total_turns = len(getattr(memory, "turns", []) or [])
    if mode == "summary":
        recent_turns = min(
            total_turns,
            int(getattr(config, "RECENT_WINDOW", 4) or 4),
        )
    else:
        recent_turns = total_turns
    logger.info(
        "CONTEXT_BUILD mode=%s summary_len=%d recent_turns=%d total_prompt_chars=%d",
        mode,
        summary_len,
        recent_turns,
        len(conversation_context or ""),
    )


def _build_retrieval_detail(block, score: float, stage: str) -> Dict:
    source = str(getattr(block, "document_title", "") or getattr(block, "title", "") or getattr(block, "block_id", ""))
    start = str(getattr(block, "start", "") or "")
    end = str(getattr(block, "end", "") or "")
    if start and end:
        source = f"{source} [{start}-{end}]"
    return {
        "block_id": str(getattr(block, "block_id", "")),
        "score": float(score),
        "title": str(getattr(block, "title", "")),
        "text": str(getattr(block, "content", "")),
        "source": source,
        "stage": stage,
    }


def _build_llm_prompts(
    *,
    response_generator: ResponseGenerator,
    query: str,
    blocks: List[Block],
    conversation_context: str,
    user_level_adapter: Optional[object] = None,
    sd_level: str,
    mode_prompt: str,
    additional_system_context: str,
    mode_prompt_override: Optional[str] = None,
    mode_overrides_sd: bool = False,
) -> Tuple[str, str]:
    try:
        answerer = response_generator.answerer
        system_prompt = answerer.build_system_prompt()
        _ = user_level_adapter  # compatibility only; level adapter removed from active runtime
        _ = sd_level  # compatibility only; SD overlay disabled in Neo runtime
        mode_directive = mode_prompt
        raw_mode_override = ""

        if mode_prompt_override:
            if mode_overrides_sd:
                raw_mode_override = mode_prompt_override
                mode_directive = ""
            else:
                mode_directive = mode_prompt_override

        final_system_prompt = response_generator._compose_system_prompt(
            base_prompt=system_prompt,
            mode_prompt=mode_directive,
            additional_system_context=additional_system_context,
            mode="INFORMATIONAL" if mode_overrides_sd else "PRESENCE",
            raw_mode_override=raw_mode_override,
        )
        user_prompt = answerer.build_context_prompt(
            blocks,
            query,
            conversation_history=conversation_context,
        )
        return final_system_prompt, user_prompt
    except Exception as exc:
        logger.debug(f"[DEBUG_TRACE] Failed to build prompts: {exc}")
        return "", ""


def _build_llm_prompt_previews(
    *,
    response_generator: ResponseGenerator,
    query: str,
    blocks: List[Block],
    conversation_context: str,
    sd_level: str,
    mode_prompt: str,
    additional_system_context: str,
    mode_prompt_override: Optional[str] = None,
    mode_overrides_sd: bool = False,
) -> Tuple[str, str]:
    full_system, full_user = _build_llm_prompts(
        response_generator=response_generator,
        query=query,
        blocks=blocks,
        conversation_context=conversation_context,
        sd_level=sd_level,
        mode_prompt=mode_prompt,
        additional_system_context=additional_system_context,
        mode_prompt_override=mode_prompt_override,
        mode_overrides_sd=mode_overrides_sd,
    )
    return _truncate_preview(full_system, 300), _truncate_preview(full_user, 300)


def _build_llm_call_trace(
    *,
    llm_result: Dict,
    step: str,
    system_prompt_preview: str,
    user_prompt_preview: str,
    fallback_error: Optional[str],
    duration_ms: int,
    system_prompt_blob_id: Optional[str] = None,
    user_prompt_blob_id: Optional[str] = None,
    memory_snapshot_blob_id: Optional[str] = None,
) -> Dict:
    call_info = {}
    if isinstance(llm_result, dict):
        raw_info = llm_result.get("llm_call_info")
        if isinstance(raw_info, dict):
            call_info.update(raw_info)

    model_used = (
        call_info.get("model")
        or (llm_result.get("model_used") if isinstance(llm_result, dict) else None)
        or config.LLM_MODEL
    )
    response_preview = (
        call_info.get("response_preview")
        or _truncate_preview(
            (llm_result.get("answer") if isinstance(llm_result, dict) else fallback_error) or "",
            300,
        )
    )
    return {
        "step": call_info.get("step") or step,
        "model": str(model_used),
        "system_prompt_preview": call_info.get("system_prompt_preview") or system_prompt_preview,
        "user_prompt_preview": call_info.get("user_prompt_preview") or user_prompt_preview,
        "response_preview": response_preview,
        "tokens_prompt": call_info.get("tokens_prompt"),
        "tokens_completion": call_info.get("tokens_completion"),
        "tokens_total": call_info.get("tokens_total"),
        "tokens_used": llm_result.get("tokens_used") if isinstance(llm_result, dict) else None,
        "duration_ms": call_info.get("duration_ms") or duration_ms,
        "system_prompt_blob_id": system_prompt_blob_id or call_info.get("system_prompt_blob_id"),
        "user_prompt_blob_id": user_prompt_blob_id or call_info.get("user_prompt_blob_id"),
        "memory_snapshot_blob_id": memory_snapshot_blob_id,
        "blob_error": call_info.get("blob_error"),
    }


def _update_session_token_metrics(
    *,
    memory,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    model_name: str,
) -> Dict[str, Optional[float] | int]:
    previous_prompt = int(memory.metadata.get("session_tokens_prompt") or 0)
    previous_completion = int(memory.metadata.get("session_tokens_completion") or 0)
    previous_total = int(memory.metadata.get("session_tokens_total") or 0)
    previous_turns = int(memory.metadata.get("session_turns") or 0)
    previous_cost = memory.metadata.get("session_cost_usd")
    previous_cost = float(previous_cost) if isinstance(previous_cost, (int, float, str)) else 0.0

    new_prompt = previous_prompt + (int(tokens_prompt) if isinstance(tokens_prompt, (int, float)) else 0)
    new_completion = previous_completion + (int(tokens_completion) if isinstance(tokens_completion, (int, float)) else 0)
    new_total = previous_total + (int(tokens_total) if isinstance(tokens_total, (int, float)) else 0)
    if not isinstance(tokens_total, (int, float)):
        new_total = new_prompt + new_completion
    new_turns = previous_turns + 1

    cost_per_1m = {
        "gpt-5.2":      {"input": 1.75,  "output": 14.00},
        "gpt-5.1":      {"input": 1.25,  "output": 10.00},
        "gpt-5":        {"input": 1.25,  "output": 10.00},
        "gpt-5-mini":   {"input": 0.25,  "output":  2.00},
        "gpt-5-nano":   {"input": 0.05,  "output":  0.40},
        "gpt-4.1":      {"input": 2.00,  "output":  8.00},
        "gpt-4.1-mini": {"input": 0.40,  "output":  1.60},
        "gpt-4.1-nano": {"input": 0.10,  "output":  0.40},
        "gpt-4o-mini":  {"input": 0.15,  "output":  0.60},
    }

    model_key = (model_name or "").lower()
    session_cost = None
    if model_key in cost_per_1m and tokens_prompt is not None and tokens_completion is not None:
        rates = cost_per_1m[model_key]
        cost = (
            (tokens_prompt / 1_000_000 * rates["input"])
            + (tokens_completion / 1_000_000 * rates["output"])
        )
        session_cost = round(previous_cost + cost, 6)

    memory.metadata["session_tokens_prompt"] = new_prompt
    memory.metadata["session_tokens_completion"] = new_completion
    memory.metadata["session_tokens_total"] = new_total
    memory.metadata["session_turns"] = new_turns
    if session_cost is not None:
        memory.metadata["session_cost_usd"] = session_cost

    return {
        "session_tokens_prompt": new_prompt,
        "session_tokens_completion": new_completion,
        "session_tokens_total": new_total,
        "session_turns": new_turns,
        "session_cost_usd": session_cost,
    }


def _build_memory_context_snapshot(memory) -> str:
    try:
        metadata = getattr(memory, "metadata", {})
        if isinstance(metadata, dict):
            snapshot = (
                metadata.get("laststatesnapshot")
                or metadata.get("last_state_snapshot_v12")
                or metadata.get("last_state_snapshot_v11")
            )
            if isinstance(snapshot, dict):
                return _truncate_preview(json.dumps(snapshot, ensure_ascii=False), 1200)
        if not memory.turns:
            return ""
        turn = memory.turns[-1]
        payload = {
            "timestamp": turn.timestamp,
            "user_input": turn.user_input,
            "bot_response": turn.bot_response,
            "nervous_system_state": None,
            "blocks_used": turn.blocks_used,
            "concepts": turn.concepts,
        }
        return _truncate_preview(json.dumps(payload, ensure_ascii=False), 1200)
    except Exception:
        return ""


def _refresh_runtime_memory_snapshot(
    *,
    memory,
    diagnostics_payload: Optional[Dict[str, Any]],
    route: Optional[str],
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    try:
        update = memory_updater.build_runtime_context(
            memory=memory,
            diagnostics=diagnostics_payload,
            route=route,
            max_context_chars=int(getattr(config, "MAX_CONTEXT_SIZE", 2200) or 2200),
        )
        memory_updater.save_snapshot(memory, update.snapshot)
        context_text = getattr(getattr(update, "context", None), "context_text", None)
        return context_text, update.snapshot
    except Exception as exc:
        logger.warning("[MEMORY_V12] snapshot refresh skipped: %s", exc)
        return None, None


def _apply_memory_debug_info(
    debug_trace: Optional[Dict],
    memory,
    memory_trace_metrics: Optional[Dict[str, object]] = None,
) -> None:
    if debug_trace is None or memory is None:
        return
    if memory_trace_metrics is None:
        memory_trace_metrics = _get_memory_trace_metrics(memory, len(memory.turns))
    debug_trace["memory_turns"] = len(memory.turns)
    debug_trace["memory_turns_content"] = (
        memory.get_turns_preview() if hasattr(memory, "get_turns_preview") else []
    )
    debug_trace["summary_text"] = memory.summary or None
    debug_trace["summary_length"] = len(memory.summary) if memory.summary else 0
    debug_trace["summary_last_turn"] = memory.summary_updated_at
    debug_trace["summary_used"] = memory_trace_metrics.get("summary_used")
    debug_trace["semantic_hits"] = memory_trace_metrics.get("semantic_hits")
    if memory.semantic_memory and hasattr(memory.semantic_memory, "last_hits_detail"):
        debug_trace["semantic_hits_detail"] = list(memory.semantic_memory.last_hits_detail or [])

