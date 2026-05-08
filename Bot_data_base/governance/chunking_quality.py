from __future__ import annotations

from models.universal_block import UniversalBlock


def build_chunking_quality_v1(block: UniversalBlock) -> dict:
    text = (block.text or "").strip()
    title = (block.title or "").strip()
    char_count = len(text)
    approx_token_count = max(1, char_count // 4) if text else 0

    too_short = approx_token_count < 80
    too_long = approx_token_count > 1800
    has_heading = bool(title)
    has_summary = bool((block.summary or "").strip())

    lowered = f"{title}\n{text}".lower()
    possible_practice_split = (
        block.governance.get("chunk_type") == "practice"
        and not any(marker in lowered for marker in ("шаг 2", "шаг 3", "время:", "цель:"))
    )
    possible_context_fragment = char_count < 240 and text.endswith(":")

    quality_notes: list[str] = []
    if too_short:
        quality_notes.append("too_short")
    if too_long:
        quality_notes.append("too_long")
    if not has_summary:
        quality_notes.append("missing_summary")
    if possible_practice_split:
        quality_notes.append("possible_practice_split")
    if possible_context_fragment:
        quality_notes.append("possible_context_fragment")

    return {
        "schema_version": "chunking_quality_v1",
        "char_count": int(char_count),
        "approx_token_count": int(approx_token_count),
        "has_heading": has_heading,
        "has_summary": has_summary,
        "possible_practice_split": possible_practice_split,
        "possible_context_fragment": possible_context_fragment,
        "too_short": too_short,
        "too_long": too_long,
        "quality_notes": quality_notes,
    }
