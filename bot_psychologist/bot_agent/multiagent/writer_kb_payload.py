"""Structured Writer KB payload delivery for selected retrieval hits."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..feature_flags import FeatureFlags, feature_flags


WRITER_KB_PAYLOAD_VERSION = "writer_kb_payload_v1"
WRITER_KB_PAYLOAD_TRACE_VERSION = "writer_kb_payload_trace_v1"
WRITER_KB_PAYLOAD_FUTURE_NOTES_VERSION = "writer_kb_payload_future_graduation_notes_v1"


@dataclass(frozen=True)
class WriterKbPayloadConfig:
    enabled: bool
    max_chunks: int
    max_total_chars: int
    excerpt_target_chars: int
    excerpt_max_chars: int
    sentence_boundary: bool
    use_overlay_metadata: bool


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_lines(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def get_writer_kb_payload_config() -> WriterKbPayloadConfig:
    return WriterKbPayloadConfig(
        enabled=feature_flags.enabled("WRITER_KB_PAYLOAD_ENABLED"),
        max_chunks=max(1, _to_int(feature_flags.value("WRITER_KB_PAYLOAD_MAX_CHUNKS", "2"), 2)),
        max_total_chars=max(
            400,
            _to_int(feature_flags.value("WRITER_KB_PAYLOAD_MAX_TOTAL_CHARS", "3600"), 3600),
        ),
        excerpt_target_chars=max(
            80,
            _to_int(feature_flags.value("WRITER_KB_PAYLOAD_EXCERPT_TARGET_CHARS", "1200"), 1200),
        ),
        excerpt_max_chars=max(
            120,
            _to_int(feature_flags.value("WRITER_KB_PAYLOAD_EXCERPT_MAX_CHARS", "1600"), 1600),
        ),
        sentence_boundary=feature_flags.value(
            "WRITER_KB_PAYLOAD_SENTENCE_BOUNDARY",
            "true",
        ).strip().lower() in {"1", "true", "yes", "on"},
        use_overlay_metadata=feature_flags.value(
            "WRITER_KB_PAYLOAD_USE_OVERLAY_METADATA",
            "false",
        ).strip().lower() in {"1", "true", "yes", "on"},
    )


def _split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _clip_to_word_boundary(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    candidate = text[:max_chars].rstrip()
    if " " in candidate:
        candidate = candidate.rsplit(" ", 1)[0].rstrip()
    candidate = candidate.rstrip(",;:-")
    return candidate or text[:max_chars].rstrip(), True


def _markdown_tail_sanitize(text: str) -> str:
    candidate = str(text or "").rstrip()
    if candidate.count("**") % 2 == 1:
        candidate = candidate.rsplit("**", 1)[0].rstrip()
    if candidate.count("__") % 2 == 1:
        candidate = candidate.rsplit("__", 1)[0].rstrip()
    return candidate.rstrip("#*- ").rstrip()


def _truncate_excerpt(
    *,
    content: str,
    target_chars: int,
    max_chars: int,
    sentence_boundary: bool,
) -> dict[str, Any]:
    source = _normalize_lines(content)
    original_char_count = len(source)
    if not source:
        return {
            "content_excerpt": "",
            "original_char_count": 0,
            "sent_char_count": 0,
            "content_truncated": False,
            "truncation_strategy": "none",
            "truncation_reason": "none",
            "truncated_mid_sentence": False,
        }
    if original_char_count <= max_chars:
        return {
            "content_excerpt": source,
            "original_char_count": original_char_count,
            "sent_char_count": original_char_count,
            "content_truncated": False,
            "truncation_strategy": "none",
            "truncation_reason": "none",
            "truncated_mid_sentence": False,
        }

    paragraphs = _split_paragraphs(source)
    excerpt = ""
    strategy = "paragraph_then_sentence_boundary"
    truncated_mid_sentence = False

    if len(paragraphs) > 1:
        selected: list[str] = []
        for paragraph in paragraphs:
            candidate = "\n\n".join(selected + [paragraph]).strip()
            if len(candidate) <= target_chars:
                selected.append(paragraph)
                continue
            break
        if selected:
            excerpt = "\n\n".join(selected).strip()
        else:
            excerpt = paragraphs[0]

    if not excerpt:
        excerpt = source

    if len(excerpt) > max_chars:
        sentences = _split_sentences(excerpt if sentence_boundary else source)
        selected_sentences: list[str] = []
        if sentence_boundary and sentences:
            for sentence in sentences:
                glue = " " if selected_sentences else ""
                candidate = f"{' '.join(selected_sentences)}{glue}{sentence}".strip()
                if len(candidate) <= max_chars:
                    selected_sentences.append(sentence)
                    continue
                break
            if selected_sentences:
                excerpt = " ".join(selected_sentences).strip()
                strategy = "sentence_boundary"
            else:
                excerpt, truncated_mid_sentence = _clip_to_word_boundary(source, max_chars)
                strategy = "word_boundary"
        else:
            excerpt, truncated_mid_sentence = _clip_to_word_boundary(source, max_chars)
            strategy = "word_boundary"

    excerpt = _markdown_tail_sanitize(excerpt)
    if not excerpt:
        excerpt, truncated_mid_sentence = _clip_to_word_boundary(source, max_chars)
        excerpt = _markdown_tail_sanitize(excerpt)
        strategy = "word_boundary"

    if not truncated_mid_sentence:
        trimmed = excerpt.rstrip()
        if trimmed and trimmed[-1] not in ".!?…\"'»":
            truncated_mid_sentence = strategy == "word_boundary"

    sent_char_count = len(excerpt)
    return {
        "content_excerpt": excerpt,
        "original_char_count": original_char_count,
        "sent_char_count": sent_char_count,
        "content_truncated": sent_char_count < original_char_count,
        "truncation_strategy": strategy,
        "truncation_reason": "excerpt_budget",
        "truncated_mid_sentence": truncated_mid_sentence,
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _overlay_index(overlay_items: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in list(overlay_items or []):
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id", "") or "")
        chunk_id = str(item.get("chunk_id", "") or "")
        block_id = str(item.get("block_id", "") or "")
        for key in (chunk_id, block_id, candidate_id):
            if key and key not in indexed:
                indexed[key] = dict(item)
    return indexed


def _extract_source_doc(item: dict[str, Any], overlay_item: dict[str, Any]) -> str:
    for key in ("source_doc", "source_document", "doc_title", "title"):
        value = item.get(key)
        if str(value or "").strip():
            return str(value).strip()
    for key in ("source_doc", "source_document", "doc_title", "title"):
        value = overlay_item.get(key)
        if str(value or "").strip():
            return str(value).strip()
    source = str(item.get("source", "") or overlay_item.get("source_id", "") or "unknown")
    return source


def _extract_chunk_type(item: dict[str, Any], overlay_item: dict[str, Any]) -> str:
    chunking_quality = dict(item.get("chunking_quality", {})) if isinstance(item.get("chunking_quality"), dict) else {}
    governance = dict(item.get("governance", {})) if isinstance(item.get("governance"), dict) else {}
    for candidate in (
        item.get("chunk_type"),
        chunking_quality.get("chunk_type"),
        governance.get("chunk_type"),
        overlay_item.get("chunk_type"),
    ):
        if str(candidate or "").strip():
            return str(candidate).strip()
    return "general_text"


def _quote_policy(item: dict[str, Any], overlay_item: dict[str, Any]) -> str:
    governance = dict(item.get("governance", {})) if isinstance(item.get("governance"), dict) else {}
    for candidate in (
        item.get("quote_policy"),
        governance.get("quote_policy"),
        overlay_item.get("quote_policy"),
    ):
        if str(candidate or "").strip():
            return str(candidate).strip()
    if "internal_only" in _string_list(governance.get("allowed_use")):
        return "internal_only"
    return "paraphrase_only"


def _core_thesis(text: str) -> str:
    normalized = _normalize_lines(text)
    if not normalized:
        return ""
    paragraphs = _split_paragraphs(normalized)
    head = paragraphs[0] if paragraphs else normalized
    sentences = _split_sentences(head)
    thesis = sentences[0] if sentences else head
    return thesis[:280].strip()


def build_writer_kb_payload(
    *,
    semantic_hits: list[dict[str, Any]],
    rag_for_writer: list[dict[str, Any]] | None,
    overlay_items: list[dict[str, Any]] | None,
    config: WriterKbPayloadConfig,
) -> dict[str, Any]:
    if not config.enabled:
        return {
            "schema_version": WRITER_KB_PAYLOAD_VERSION,
            "enabled": False,
            "chunk_count": 0,
            "total_sent_char_count": 0,
            "chunks": [],
            "warnings": [],
            "blockers": [],
        }

    overlay_by_id = _overlay_index(overlay_items if config.use_overlay_metadata else None)
    selected_hits = [
        dict(item)
        for item in list(rag_for_writer or [])
        if isinstance(item, dict)
    ]
    if not selected_hits:
        selected_hits = [
            dict(item)
            for item in list(semantic_hits or [])
            if isinstance(item, dict)
        ]

    total_sent = 0
    payload_chunks: list[dict[str, Any]] = []
    warnings: list[str] = []
    blockers: list[str] = []

    for item in selected_hits[: config.max_chunks]:
        content = str(item.get("content", "") or "")
        if not content.strip():
            warnings.append("empty_selected_hit_content")
            continue
        chunk_id = str(item.get("chunk_id", "") or "")
        overlay_item = overlay_by_id.get(chunk_id, {})
        excerpt = _truncate_excerpt(
            content=content,
            target_chars=config.excerpt_target_chars,
            max_chars=min(config.excerpt_max_chars, max(120, config.max_total_chars - total_sent)),
            sentence_boundary=config.sentence_boundary,
        )
        if excerpt["sent_char_count"] <= 0:
            warnings.append("empty_excerpt_after_truncation")
            continue
        if total_sent + int(excerpt["sent_char_count"]) > config.max_total_chars and payload_chunks:
            warnings.append("payload_total_budget_reached")
            break

        governance = dict(item.get("governance", {})) if isinstance(item.get("governance"), dict) else {}
        allowed_use = _string_list(item.get("allowed_use")) or _string_list(governance.get("allowed_use")) or ["direct_to_writer"]
        quote_policy = _quote_policy(item, overlay_item)
        if quote_policy == "internal_only":
            excerpt["content_excerpt"] = ""
            excerpt["sent_char_count"] = 0
            excerpt["content_truncated"] = True
            excerpt["truncation_strategy"] = "none"
            excerpt["truncation_reason"] = "invalid_source"
            warnings.append("internal_only_quote_policy_detected")

        source_id = str(
            item.get("source_id")
            or item.get("source")
            or overlay_item.get("source_id")
            or "unknown"
        )
        chunk = {
            "chunk_id": chunk_id,
            "source_id": source_id,
            "source_doc": _extract_source_doc(item, overlay_item),
            "chunk_type": _extract_chunk_type(item, overlay_item),
            "payload_item_origin": str(item.get("payload_item_origin") or ""),
            "semantic_card_id": str(item.get("semantic_card_id") or ""),
            "semantic_card_pack_id": str(item.get("semantic_card_pack_id") or ""),
            "core_thesis": str(item.get("core_thesis") or overlay_item.get("core_thesis") or _core_thesis(content)),
            "content_excerpt": excerpt["content_excerpt"],
            "mechanism_hints": _string_list(item.get("mechanism_hints")) or _string_list(overlay_item.get("mechanism_hints")),
            "user_markers_examples": _string_list(item.get("user_markers_examples")) or _string_list(overlay_item.get("user_markers_examples")),
            "use_when": _string_list(item.get("use_when")) or _string_list(overlay_item.get("use_when")),
            "avoid_when": _string_list(item.get("avoid_when")) or _string_list(overlay_item.get("avoid_when")),
            "allowed_use": allowed_use,
            "quote_policy": quote_policy,
            "writer_instruction": str(
                item.get("writer_instruction")
                or overlay_item.get("writer_instruction")
                or (
                    "Use as grounding. Paraphrase. Do not dump raw quote."
                    if quote_policy != "internal_only"
                    else "Internal-only metadata. Do not quote or dump raw text."
                )
            ),
            "recommended_moves": _string_list(item.get("recommended_moves")) or _string_list(overlay_item.get("recommended_moves")),
            "forbidden_moves": _string_list(item.get("forbidden_moves")) or _string_list(overlay_item.get("forbidden_moves")),
            "original_char_count": int(excerpt["original_char_count"]),
            "sent_char_count": int(excerpt["sent_char_count"]),
            "content_truncated": bool(excerpt["content_truncated"]),
            "truncation_strategy": str(excerpt["truncation_strategy"]),
            "truncation_reason": str(excerpt["truncation_reason"]),
            "truncated_mid_sentence": bool(excerpt["truncated_mid_sentence"]),
            "overlay_metadata_used": bool(overlay_item),
        }
        payload_chunks.append(chunk)
        total_sent += int(chunk["sent_char_count"])

    return {
        "schema_version": WRITER_KB_PAYLOAD_VERSION,
        "enabled": True,
        "chunk_count": len(payload_chunks),
        "total_sent_char_count": total_sent,
        "chunks": payload_chunks,
        "warnings": list(dict.fromkeys(warnings)),
        "blockers": list(dict.fromkeys(blockers)),
    }


def build_writer_kb_payload_trace(
    *,
    payload: dict[str, Any],
    input_rag_for_writer_count: int,
    configured_enabled: bool | None = None,
    configured_source: str = "",
    fallback_reason: str = "",
    display_preview_char_cap: int = 500,
) -> dict[str, Any]:
    chunks = [dict(item) for item in list(payload.get("chunks", []) or []) if isinstance(item, dict)]
    total_sent_char_count = sum(int(item.get("sent_char_count", 0) or 0) for item in chunks)
    effective_enabled = bool(payload.get("enabled", False))
    has_structured_payload = effective_enabled and bool(chunks)
    primary_path = WRITER_KB_PAYLOAD_VERSION if has_structured_payload else "legacy_semantic_hits_fallback_v1"
    fallback_is_primary = not has_structured_payload
    normalized_fallback_reason = str(fallback_reason or "").strip()
    if fallback_is_primary and not normalized_fallback_reason:
        normalized_fallback_reason = "disabled_by_config" if configured_enabled is False else "no_eligible_chunks"
    preview_char_count = min(total_sent_char_count, max(0, int(display_preview_char_cap or 0)))
    chunk_summaries = [
        {
            "chunk_id": str(item.get("chunk_id", "") or ""),
            "source_doc": str(item.get("source_doc", "") or ""),
            "chunk_type": str(item.get("chunk_type", "") or ""),
            "quote_policy": str(item.get("quote_policy", "") or ""),
            "allowed_use": _string_list(item.get("allowed_use")),
            "payload_item_origin": str(item.get("payload_item_origin", "") or ""),
            "semantic_card_id": str(item.get("semantic_card_id", "") or ""),
            "semantic_card_pack_id": str(item.get("semantic_card_pack_id", "") or ""),
            "writer_can_ignore": True,
            "applied_as_authority": False,
        }
        for item in chunks[:8]
    ]
    return {
        "schema_version": WRITER_KB_PAYLOAD_TRACE_VERSION,
        "enabled": effective_enabled,
        "configured_enabled": bool(configured_enabled) if configured_enabled is not None else effective_enabled,
        "configured_source": str(configured_source or ""),
        "status": "structured_payload_used" if has_structured_payload else "fallback_used",
        "primary_path": primary_path,
        "payload_version": primary_path,
        "input_rag_for_writer_count": int(input_rag_for_writer_count or 0),
        "payload_chunk_count": len(chunks),
        "total_original_char_count": sum(int(item.get("original_char_count", 0) or 0) for item in chunks),
        "total_sent_char_count": total_sent_char_count,
        "truncated_chunk_count": sum(1 for item in chunks if bool(item.get("content_truncated"))),
        "mid_sentence_cut_count": sum(1 for item in chunks if bool(item.get("truncated_mid_sentence"))),
        "overlay_metadata_used_count": sum(1 for item in chunks if bool(item.get("overlay_metadata_used"))),
        "payload_sent_to_writer_char_count": total_sent_char_count,
        "payload_display_preview_char_count": preview_char_count,
        "payload_display_is_preview": True,
        "payload_full_text_sent_to_writer": has_structured_payload,
        "payload_full_text_exposed_in_web_trace": False,
        "chunk_summaries": chunk_summaries,
        "fallback_reason": normalized_fallback_reason,
        "fallback_is_primary": fallback_is_primary,
        "warning": (
            "legacy semantic hits fallback used instead of writer_kb_payload_v1"
            if fallback_is_primary
            else ""
        ),
        "runtime_mode": FeatureFlags.app_env(),
        "warnings": list(payload.get("warnings", []) or []),
        "blockers": list(payload.get("blockers", []) or []),
    }


def build_future_graduation_notes(
    *,
    payload: dict[str, Any],
    trace: dict[str, Any],
    legacy_fallback_reason: str = "",
) -> dict[str, Any]:
    chunks = [dict(item) for item in list(payload.get("chunks", []) or []) if isinstance(item, dict)]
    head = chunks[0] if chunks else {}
    payload_source = "legacy_selected_hit"
    if chunks and any(bool(item.get("overlay_metadata_used")) for item in chunks):
        payload_source = "selected_hit_plus_overlay_metadata"
    elif not bool(payload.get("enabled", False)):
        payload_source = "fallback_trimmed_hit"
    return {
        "schema_version": WRITER_KB_PAYLOAD_FUTURE_NOTES_VERSION,
        "prd_id": "PRD-047.22",
        "payload_version": WRITER_KB_PAYLOAD_VERSION,
        "payload_source": payload_source,
        "structured_payload_used": bool(payload.get("enabled", False)) and bool(chunks),
        "legacy_semantic_hits_used": not (bool(payload.get("enabled", False)) and bool(chunks)),
        "legacy_fallback_reason": str(legacy_fallback_reason or ""),
        "accepted_overlay_used": any(bool(item.get("overlay_metadata_used")) for item in chunks),
        "overlay_item_id": "",
        "overlay_chunk_type": str(head.get("chunk_type", "") or ""),
        "overlay_allowed_use": ",".join(_string_list(head.get("allowed_use"))),
        "overlay_quote_policy": str(head.get("quote_policy", "") or ""),
        "original_char_count": int(head.get("original_char_count", 0) or 0),
        "sent_char_count": int(head.get("sent_char_count", 0) or 0),
        "content_truncated": bool(head.get("content_truncated", False)),
        "truncation_strategy": str(head.get("truncation_strategy", "none") or "none"),
        "truncation_reason": str(head.get("truncation_reason", "none") or "none"),
        "chunk_type": str(head.get("chunk_type", "") or ""),
        "allowed_use": _string_list(head.get("allowed_use")),
        "quote_policy": str(head.get("quote_policy", "") or ""),
        "writer_instruction_present": bool(str(head.get("writer_instruction", "") or "").strip()),
        "writer_received_structured_payload": bool(payload.get("enabled", False)) and bool(chunks),
        "trace_mid_sentence_cut_count": int(trace.get("mid_sentence_cut_count", 0) or 0),
    }


def format_writer_kb_payload_for_prompt(
    *,
    payload: dict[str, Any],
    legacy_hits: list[str],
    fallback_reason: str = "",
) -> str:
    chunks = [dict(item) for item in list(payload.get("chunks", []) or []) if isinstance(item, dict)]
    if bool(payload.get("enabled", False)) and chunks:
        lines = [
            f"version={payload.get('schema_version', WRITER_KB_PAYLOAD_VERSION)}",
            f"chunk_count={len(chunks)}",
            f"total_sent_char_count={int(payload.get('total_sent_char_count', 0) or 0)}",
        ]
        for index, item in enumerate(chunks, start=1):
            lines.extend(
                [
                    "",
                    f"[KB-{index}]",
                    f"chunk_id={str(item.get('chunk_id', '') or '')}",
                    f"source_doc={str(item.get('source_doc', '') or '')}",
                    f"chunk_type={str(item.get('chunk_type', '') or '')}",
                    f"quote_policy={str(item.get('quote_policy', '') or '')}",
                    f"allowed_use={','.join(_string_list(item.get('allowed_use'))) or 'none'}",
                    f"core_thesis={str(item.get('core_thesis', '') or '')}",
                    "content_excerpt:",
                    str(item.get("content_excerpt", "") or "none"),
                    f"writer_instruction={str(item.get('writer_instruction', '') or '')}",
                    f"content_truncated={str(bool(item.get('content_truncated', False))).lower()}",
                    f"truncation_strategy={str(item.get('truncation_strategy', 'none') or 'none')}",
                ]
            )
        warnings = [str(item) for item in list(payload.get("warnings", []) or []) if str(item).strip()]
        if warnings:
            lines.extend(["", f"warnings={','.join(warnings)}"])
        return "\n".join(lines).strip()

    formatted_legacy = "\n---\n".join(f"- {str(item or '').strip()}" for item in legacy_hits if str(item or "").strip())
    return "\n".join(
        [
            "version=legacy_semantic_hits_fallback_v1",
            f"reason={str(fallback_reason or 'writer_kb_payload_disabled_or_empty')}",
            "legacy_hits:",
            formatted_legacy or "нет релевантных знаний",
        ]
    ).strip()


__all__ = [
    "WRITER_KB_PAYLOAD_FUTURE_NOTES_VERSION",
    "WRITER_KB_PAYLOAD_TRACE_VERSION",
    "WRITER_KB_PAYLOAD_VERSION",
    "WriterKbPayloadConfig",
    "build_future_graduation_notes",
    "build_writer_kb_payload",
    "build_writer_kb_payload_trace",
    "format_writer_kb_payload_for_prompt",
    "get_writer_kb_payload_config",
]
