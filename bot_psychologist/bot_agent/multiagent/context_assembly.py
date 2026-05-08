"""Context assembly helpers for Writer context package."""

from __future__ import annotations

import json
import re
from typing import Any

from .contracts.context_package import (
    ContextAssemblyPackage,
    ContextAssemblyTrace,
    ContextBudget,
    TurnContextItem,
    TurnMicroSummary,
)
from .contracts.memory_bundle import MemoryBundle
from .contracts.thread_state import ThreadState


CONTEXT_ASSEMBLY_TRACE_VERSION = "context_assembly_trace_v1"
TURN_MICRO_SUMMARY_METHOD_V1 = "deterministic_extractive_v1"
RECENT_FULL_TURN_MAX_CHARS = 320
MICRO_SUMMARY_MAX_CHARS = 360
CONTEXT_BUDGET_MAX_CHARS = 8000
MAX_MEMORY_HITS_PER_SOURCE = 3


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _extract_important_quote(text: str, max_chars: int = 120) -> str | None:
    match = re.search(r"[\"'«“](.{8,200}?)[\"'»”]", text)
    if not match:
        return None
    quote = _normalize_text(match.group(1))
    return quote[:max_chars] if quote else None


def _split_sentences(text: str) -> list[str]:
    chunks = re.findall(r"[^.!?]+[.!?]?", text)
    return [_normalize_text(chunk) for chunk in chunks if _normalize_text(chunk)]


def build_turn_micro_summary_v1(
    *,
    turn_id: str,
    role: str,
    content: str,
    max_summary_chars: int = MICRO_SUMMARY_MAX_CHARS,
) -> TurnMicroSummary:
    """Create deterministic extractive micro-summary for one long turn."""
    normalized = _normalize_text(content)
    raw_chars = len(content or "")
    if not normalized:
        summary_text = ""
    else:
        sentences = _split_sentences(normalized)
        if not sentences:
            summary_text = normalized[:max_summary_chars]
        elif len(sentences) == 1:
            summary_text = sentences[0][:max_summary_chars]
        else:
            first = sentences[0]
            last = sentences[-1]
            if first == last:
                summary_text = first
            else:
                summary_text = f"{first} {last}"
            if len(summary_text) > max_summary_chars:
                summary_text = summary_text[:max_summary_chars].rstrip()
    summary_chars = len(summary_text)
    return TurnMicroSummary(
        turn_id=turn_id,
        role=role,
        summary=summary_text,
        important_quote=_extract_important_quote(normalized),
        raw_chars=raw_chars,
        summary_chars=summary_chars,
        was_truncated=raw_chars > summary_chars,
        summary_method=TURN_MICRO_SUMMARY_METHOD_V1,
    )


def _recent_turn_pairs(raw_turns: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    for idx, turn in enumerate(raw_turns, start=1):
        turn_index = int(turn.get("turn_index", idx) or idx)
        user_text = str(turn.get("user_input", "") or "").strip()
        bot_text = str(turn.get("bot_response", "") or "").strip()
        if user_text:
            pairs.append((f"turn_{turn_index}_user", "user", user_text))
        if bot_text:
            pairs.append((f"turn_{turn_index}_assistant", "assistant", bot_text))
    return pairs


def _normalize_hit(item: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "source": source,
        "chunk_id": str(item.get("chunk_id", "")),
        "score": float(item.get("score", 0.0) or 0.0),
        "content": str(item.get("content", "") or ""),
    }


def _deduplicate_hits(
    *,
    recent_texts: set[str],
    semantic_hits: list[dict[str, Any]],
    knowledge_hits: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    duplicates_removed = 0
    seen = set(recent_texts)
    clean_semantic: list[dict[str, Any]] = []
    for hit in semantic_hits:
        content = _normalize_text(str(hit.get("content", "") or ""))
        if not content:
            continue
        if content in seen:
            duplicates_removed += 1
            continue
        seen.add(content)
        clean_semantic.append(hit)

    clean_knowledge: list[dict[str, Any]] = []
    for hit in knowledge_hits:
        content = _normalize_text(str(hit.get("content", "") or ""))
        if not content:
            continue
        if content in seen:
            duplicates_removed += 1
            continue
        seen.add(content)
        clean_knowledge.append(hit)

    return clean_semantic, clean_knowledge, duplicates_removed


def _used_chars(
    *,
    user_message: str,
    pattern_core: str,
    active_frame: dict[str, Any],
    full_items: list[TurnContextItem],
    summarized_items: list[TurnMicroSummary],
    semantic_hits: list[dict[str, Any]],
    knowledge_hits: list[dict[str, Any]],
    personal_history_context: list[dict[str, Any]],
) -> int:
    total = len(user_message or "") + len(pattern_core or "")
    total += len(json.dumps(active_frame, ensure_ascii=False))
    total += sum(len(item.content) for item in full_items)
    total += sum(len(item.summary) for item in summarized_items)
    total += sum(len(str(item.get("content", "") or "")) for item in semantic_hits)
    total += sum(len(str(item.get("content", "") or "")) for item in knowledge_hits)
    total += sum(len(str(item.get("content", "") or "")) for item in personal_history_context)
    return total


def build_context_assembly_package_v1(
    *,
    user_message: str,
    thread_state: ThreadState,
    memory_bundle: MemoryBundle,
    max_context_chars: int = CONTEXT_BUDGET_MAX_CHARS,
) -> ContextAssemblyPackage:
    """Build compact context package for Writer with deterministic rules."""
    recent_turns_raw = list(getattr(memory_bundle, "recent_turns", []) or [])
    pairs = _recent_turn_pairs(recent_turns_raw)

    full_items: list[TurnContextItem] = []
    summarized_items: list[TurnMicroSummary] = []
    for turn_id, role, content in pairs:
        raw_chars = len(content)
        if raw_chars <= RECENT_FULL_TURN_MAX_CHARS:
            full_items.append(
                TurnContextItem(
                    turn_id=turn_id,
                    role=role,
                    content=content,
                    raw_chars=raw_chars,
                    source="recent_full",
                    was_summarized=False,
                    was_truncated=False,
                )
            )
        else:
            summarized_items.append(
                build_turn_micro_summary_v1(
                    turn_id=turn_id,
                    role=role,
                    content=content,
                    max_summary_chars=MICRO_SUMMARY_MAX_CHARS,
                )
            )

    pattern_core = str(thread_state.pattern_core or "")
    active_frame = dict(thread_state.active_frame or {})
    personal_history = list(getattr(memory_bundle, "personal_history_context", []) or [])
    semantic_raw = [
        _normalize_hit(item, "semantic_memory")
        for item in list(getattr(memory_bundle, "semantic_memory_hits", []) or [])
        if isinstance(item, dict)
    ]
    knowledge_raw = [
        _normalize_hit(item, "knowledge_rag")
        for item in list(getattr(memory_bundle, "knowledge_rag_hits", []) or [])
        if isinstance(item, dict)
    ]

    semantic_raw = semantic_raw[:MAX_MEMORY_HITS_PER_SOURCE]
    knowledge_raw = knowledge_raw[:MAX_MEMORY_HITS_PER_SOURCE]

    recent_texts = {
        _normalize_text(item.content)
        for item in full_items
        if _normalize_text(item.content)
    }
    recent_texts.update(
        _normalize_text(item.summary)
        for item in summarized_items
        if _normalize_text(item.summary)
    )
    semantic_hits, knowledge_hits, duplicates_removed = _deduplicate_hits(
        recent_texts=recent_texts,
        semantic_hits=semantic_raw,
        knowledge_hits=knowledge_raw,
    )

    reasons: list[str] = []
    dropped_count = 0
    used = _used_chars(
        user_message=user_message,
        pattern_core=pattern_core,
        active_frame=active_frame,
        full_items=full_items,
        summarized_items=summarized_items,
        semantic_hits=semantic_hits,
        knowledge_hits=knowledge_hits,
        personal_history_context=personal_history,
    )

    if used > max_context_chars:
        reasons.append("budget_limit")

    while used > max_context_chars and knowledge_hits:
        knowledge_hits.pop()
        dropped_count += 1
        reasons.append("drop_knowledge_hit")
        used = _used_chars(
            user_message=user_message,
            pattern_core=pattern_core,
            active_frame=active_frame,
            full_items=full_items,
            summarized_items=summarized_items,
            semantic_hits=semantic_hits,
            knowledge_hits=knowledge_hits,
            personal_history_context=personal_history,
        )

    while used > max_context_chars and semantic_hits:
        semantic_hits.pop()
        dropped_count += 1
        reasons.append("drop_semantic_hit")
        used = _used_chars(
            user_message=user_message,
            pattern_core=pattern_core,
            active_frame=active_frame,
            full_items=full_items,
            summarized_items=summarized_items,
            semantic_hits=semantic_hits,
            knowledge_hits=knowledge_hits,
            personal_history_context=personal_history,
        )

    while used > max_context_chars and summarized_items:
        summarized_items.pop(0)
        dropped_count += 1
        reasons.append("drop_summarized_turn")
        used = _used_chars(
            user_message=user_message,
            pattern_core=pattern_core,
            active_frame=active_frame,
            full_items=full_items,
            summarized_items=summarized_items,
            semantic_hits=semantic_hits,
            knowledge_hits=knowledge_hits,
            personal_history_context=personal_history,
        )

    while used > max_context_chars and len(full_items) > 1:
        full_items.pop(0)
        dropped_count += 1
        reasons.append("drop_full_turn")
        used = _used_chars(
            user_message=user_message,
            pattern_core=pattern_core,
            active_frame=active_frame,
            full_items=full_items,
            summarized_items=summarized_items,
            semantic_hits=semantic_hits,
            knowledge_hits=knowledge_hits,
            personal_history_context=personal_history,
        )

    trace = ContextAssemblyTrace(
        version=CONTEXT_ASSEMBLY_TRACE_VERSION,
        recent_full_count=len(full_items),
        summarized_count=len(summarized_items),
        dropped_count=dropped_count,
        semantic_hits_count=len(semantic_hits),
        knowledge_hits_count=len(knowledge_hits),
        duplicates_removed=duplicates_removed,
        budget_used_chars=used,
        budget_limit_chars=max_context_chars,
        reasons=list(dict.fromkeys(reasons)),
    )
    budget = ContextBudget(
        max_chars=max_context_chars,
        used_chars=used,
        full_turns=len(full_items),
        summarized_turns=len(summarized_items),
        dropped_turns=dropped_count,
        semantic_hits=len(semantic_hits),
        knowledge_hits=len(knowledge_hits),
    )
    return ContextAssemblyPackage(
        current_user_message=user_message,
        recent_turns_full=full_items,
        recent_turns_summarized=summarized_items,
        pattern_core=pattern_core or None,
        active_frame=active_frame,
        personal_history_context=personal_history,
        semantic_memory_hits=semantic_hits,
        knowledge_rag_hits=knowledge_hits,
        context_budget=budget,
        trace=trace,
    )


def format_context_for_writer(package: ContextAssemblyPackage) -> str:
    """Render compact text block for prompt compatibility."""
    sections: list[str] = []
    if package.recent_turns_full:
        lines = [
            f"{item.role.upper()}#{item.turn_id}: {item.content}"
            for item in package.recent_turns_full
        ]
        sections.append("RECENT FULL TURNS:\n" + "\n".join(lines))
    if package.recent_turns_summarized:
        lines = [
            (
                f"{item.role.upper()}#{item.turn_id}: {item.summary}"
                + (f' | quote: "{item.important_quote}"' if item.important_quote else "")
            )
            for item in package.recent_turns_summarized
        ]
        sections.append("RECENT SUMMARIZED TURNS:\n" + "\n".join(lines))
    if package.personal_history_context:
        lines = [
            str(item.get("content", "") or "")
            for item in package.personal_history_context
            if str(item.get("content", "") or "").strip()
        ]
        if lines:
            sections.append("PERSONAL HISTORY:\n" + "\n".join(lines))
    if package.semantic_memory_hits:
        lines = [str(item.get("content", "") or "") for item in package.semantic_memory_hits]
        sections.append("SEMANTIC MEMORY HITS:\n" + "\n".join(lines))
    if package.knowledge_rag_hits:
        lines = [str(item.get("content", "") or "") for item in package.knowledge_rag_hits]
        sections.append("KNOWLEDGE RAG HITS:\n" + "\n".join(lines))
    return "\n\n".join(section for section in sections if section.strip())
