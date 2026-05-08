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
RECENT_FULL_TURN_MAX_CHARS = 1200
MICRO_SUMMARY_MAX_CHARS = 360
CONTEXT_BUDGET_MAX_CHARS = 8000
MAX_MEMORY_HITS_PER_SOURCE = 3

SUMMARY_USER_MARKERS = (
    "я ",
    "мне",
    "меня",
    "моё",
    "хочу",
    "не хочу",
    "не могу",
    "не получается",
    "сил нет",
    "устал",
    "устала",
    "страшно",
    "боюсь",
    "стыдно",
    "злюсь",
    "не знаю",
    "важно",
    "задевает",
    "больно",
    "один",
    "одна",
    "никому не нужен",
    "никому не нужна",
    "должен",
    "надо",
)
SUMMARY_ASSISTANT_MARKERS = (
    "можно попробовать",
    "первый шаг",
    "микро-шаг",
    "на 1 минуту",
    "практика",
    "заметь",
    "проверь",
    "вопрос",
    "если коротко",
    "смысл",
    "важно",
)
SUMMARY_UNIVERSAL_MARKERS = (
    "?",
    "!",
    "но",
    "при этом",
    "самое важное",
    "главное",
)


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _has_quoted_text(text: str) -> bool:
    return re.search(r"[\"'«“](.{8,200}?)[\"'»”]", text or "") is not None


def _split_sentences(text: str) -> list[str]:
    chunks = re.findall(r"[^.!?\n]+[.!?]?", text)
    return [_normalize_text(chunk) for chunk in chunks if _normalize_text(chunk)]


def _score_fragment(role: str, fragment: str) -> int:
    lowered = fragment.lower()
    markers = SUMMARY_ASSISTANT_MARKERS if role == "assistant" else SUMMARY_USER_MARKERS

    score = 0
    for marker in markers:
        if marker in lowered:
            score += 2
    for marker in SUMMARY_UNIVERSAL_MARKERS:
        if marker in lowered:
            score += 1

    if "?" in fragment:
        score += 1
    if 20 <= len(fragment) <= 220:
        score += 1
    return score


def _select_summary_fragments(
    *,
    role: str,
    fragments: list[str],
    max_summary_chars: int,
) -> tuple[str, list[tuple[int, str, int]]]:
    if not fragments:
        return "", []

    scored: list[tuple[int, str, int]] = []
    meaningful_indexes = [idx for idx, fragment in enumerate(fragments) if len(fragment) >= 12]
    if not meaningful_indexes:
        meaningful_indexes = list(range(len(fragments)))
    first_meaningful = meaningful_indexes[0]
    last_meaningful = meaningful_indexes[-1]

    for idx, fragment in enumerate(fragments):
        score = _score_fragment(role, fragment)
        if idx == first_meaningful:
            score += 1
        if idx == last_meaningful:
            score += 1
        scored.append((idx, fragment, score))

    target_count = max(2, min(4, len(scored)))
    ranked = sorted(scored, key=lambda item: (-item[2], -len(item[1]), item[0]))
    selected = ranked[:target_count]
    selected.sort(key=lambda item: item[0])

    summary_parts: list[str] = []
    for _, fragment, _ in selected:
        candidate = " ".join(summary_parts + [fragment]).strip()
        if len(candidate) <= max_summary_chars:
            summary_parts.append(fragment)
            continue

        used_chars = len(" ".join(summary_parts))
        remain = max_summary_chars - used_chars - (1 if summary_parts else 0)
        if remain >= 40:
            summary_parts.append(fragment[:remain].rstrip())
        break

    if not summary_parts:
        summary_parts.append(selected[0][1][:max_summary_chars].rstrip())

    return " ".join(summary_parts).strip(), scored


def _is_technical_fragment(fragment: str) -> bool:
    lowered = fragment.lower()
    technical_markers = (
        "http://",
        "https://",
        "chunk_id",
        "turn_id",
        "trace",
        "json",
        ".py",
        "error:",
    )
    return any(marker in lowered for marker in technical_markers)


def _extract_important_quote(
    *,
    text: str,
    role: str,
    scored_fragments: list[tuple[int, str, int]],
    max_chars: int = 120,
) -> tuple[str | None, bool]:
    match = re.search(r"[\"'«“](.{8,200}?)[\"'»”]", text)
    if match:
        quote = _normalize_text(match.group(1))
        return (quote[:max_chars], False) if quote else (None, False)

    if role != "user":
        return None, False

    ranked = sorted(scored_fragments, key=lambda item: (-item[2], len(item[1]), item[0]))
    for _, fragment, _ in ranked:
        quote = _normalize_text(fragment)
        if len(quote) < 20 or len(quote) > 160:
            continue
        if _is_technical_fragment(quote):
            continue
        return quote[:max_chars], True

    return None, False


def _tokenize_for_overlap(text: str) -> set[str]:
    return {tok for tok in re.findall(r"\w+", (text or "").lower()) if len(tok) >= 2}


def _token_overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    common = len(left.intersection(right))
    base = min(len(left), len(right))
    return (common / float(base)) if base else 0.0


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
        scored_fragments: list[tuple[int, str, int]] = []
    else:
        fragments = _split_sentences(normalized)
        if not fragments:
            summary_text = normalized[:max_summary_chars]
            scored_fragments = [(0, summary_text, _score_fragment(role, summary_text))]
        elif len(fragments) == 1:
            one = fragments[0]
            summary_text = one[:max_summary_chars]
            scored_fragments = [(0, one, _score_fragment(role, one))]
        else:
            summary_text, scored_fragments = _select_summary_fragments(
                role=role,
                fragments=fragments,
                max_summary_chars=max_summary_chars,
            )

    important_quote, _ = _extract_important_quote(
        text=normalized,
        role=role,
        scored_fragments=scored_fragments,
    )

    summary_chars = len(summary_text)
    return TurnMicroSummary(
        turn_id=turn_id,
        role=role,
        summary=summary_text,
        important_quote=important_quote,
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, list[str]]:
    duplicates_removed = 0
    seen = set(recent_texts)
    reasons: list[str] = []

    recent_candidates = [item for item in recent_texts if item]
    recent_tokens = [(item, _tokenize_for_overlap(item)) for item in recent_candidates]

    def classify_duplicate(content: str, source: str) -> str | None:
        for recent in recent_candidates:
            if len(recent) >= 40 and recent in content:
                return f"{source}_duplicate_recent_substring"

        hit_tokens = _tokenize_for_overlap(content)
        for _, tokens in recent_tokens:
            if _token_overlap_ratio(tokens, hit_tokens) >= 0.75:
                return f"{source}_duplicate_token_overlap"
        return None

    clean_semantic: list[dict[str, Any]] = []
    for hit in semantic_hits:
        content = _normalize_text(str(hit.get("content", "") or ""))
        if not content:
            continue

        duplicate_reason = classify_duplicate(content, "semantic")
        if duplicate_reason:
            duplicates_removed += 1
            reasons.append(duplicate_reason)
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

        duplicate_reason = classify_duplicate(content, "knowledge")
        if duplicate_reason:
            duplicates_removed += 1
            reasons.append(duplicate_reason)
            continue

        if content in seen:
            duplicates_removed += 1
            continue

        seen.add(content)
        clean_knowledge.append(hit)

    return clean_semantic, clean_knowledge, duplicates_removed, reasons


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

    reasons: list[str] = []
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
            if raw_chars > 320:
                reasons.append("medium_turn_kept_full")
            continue

        micro_summary = build_turn_micro_summary_v1(
            turn_id=turn_id,
            role=role,
            content=content,
            max_summary_chars=MICRO_SUMMARY_MAX_CHARS,
        )
        summarized_items.append(micro_summary)
        reasons.append("summary_marker_scored")
        if role == "user" and micro_summary.important_quote and not _has_quoted_text(content):
            reasons.append("important_quote_fallback_used")

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
    semantic_hits, knowledge_hits, duplicates_removed, dedup_reasons = _deduplicate_hits(
        recent_texts=recent_texts,
        semantic_hits=semantic_raw,
        knowledge_hits=knowledge_raw,
    )
    reasons.extend(dedup_reasons)

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
