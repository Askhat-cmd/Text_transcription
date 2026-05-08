# -*- coding: utf-8 -*-
import json
from collections import Counter

from chunkers.book_chunker import BookChunker
from governance.governance_adapter import apply_governance_to_blocks_v1
from governance.chunking_quality import build_chunking_quality_v1

SYNTHETIC_PRACTICE = """# Synthetic Practice Manual

## Паттерн избегания

Когда человек откладывает действие, иногда работает паттерн защиты от стыда.

## Практика 1: Стоп-кадр избегания

Цель: заметить момент откладывания.
Время: 3 минуты.

Шаг 1: остановись и назови действие, которое откладываешь.
Шаг 2: отметь чувство в теле.
Шаг 3: выбери один микрошаг на 2 минуты.

## Безопасность

Эта практика не заменяет специалиста. При кризисе или риске самоповреждения нужно обратиться за живой помощью.
"""

SYNTHETIC_ARCH = """# Neo MindBot Architecture

## Writer Rules

Бот работает как зеркало, навигатор и мягкий катализатор осознавания.
Не становиться духовным авторитетом.
Не заменять психотерапевта.

## Diagnostic Center

Diagnostic Center выбирает линзу, но не показывает внутренние labels пользователю.
"""

SYNTHETIC_MIXED = """# Mixed Chunk

## Практика с конфликтом

Практика: шаг 1 сделай вдох. шаг 2 запиши реакцию.
Безопасность: при кризисе нужна экстренная помощь.
Паттерн избегания возвращается в этой ситуации.
"""

chunker = BookChunker(config={"target_tokens": 220, "min_tokens": 60, "max_tokens": 320, "overlap_tokens": 0})


def run_case(text: str, source_title: str, source_kind: str, profile: str):
    blocks = chunker.chunk_file_from_text(text, "Author", source_title, "ru")
    blocks = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="synthetic_src",
        source_title=source_title,
        source_type="book",
        source_kind=source_kind,
        governance_profile=profile,
    )
    for block in blocks:
        block.chunking_quality = build_chunking_quality_v1(block)
    return blocks


def compact(block):
    gov = block.governance
    q = block.chunking_quality
    return {
        "title": block.title,
        "section_role_hint": block.section_role_hint,
        "chunk_type": gov.get("chunk_type"),
        "allowed_use": gov.get("allowed_use", []),
        "safety_flags": gov.get("safety_flags", []),
        "mixed_intent_severity": q.get("mixed_intent_severity"),
        "mixed_intent_reason": q.get("mixed_intent_reason"),
    }

practice_blocks = run_case(SYNTHETIC_PRACTICE, "Synthetic Practice Manual", "practice_manual", "practice_manual")
arch_blocks = run_case(SYNTHETIC_ARCH, "Neo MindBot Architecture", "architecture_notes", "architecture_notes")
mixed_blocks = run_case(SYNTHETIC_MIXED, "Mixed Chunk", "practice_manual", "practice_manual")

payload = {
    "practice_manual": {
        "blocks_generated": len(practice_blocks),
        "chunk_type_counts": dict(Counter([b.governance.get("chunk_type") for b in practice_blocks])),
        "blocks": [compact(b) for b in practice_blocks],
        "practice_suggestion_leakage": any(
            b.governance.get("chunk_type") != "practice" and "practice_suggestion" in b.governance.get("allowed_use", [])
            for b in practice_blocks
        ),
        "high_or_medium_mixed_intent_count": sum(
            1 for b in practice_blocks if b.chunking_quality.get("mixed_intent_severity") in {"medium", "high"}
        ),
    },
    "architecture_notes": {
        "blocks_generated": len(arch_blocks),
        "chunk_type_counts": dict(Counter([b.governance.get("chunk_type") for b in arch_blocks])),
        "blocks": [compact(b) for b in arch_blocks],
        "practice_suggestion_leakage": any(
            "practice_suggestion" in b.governance.get("allowed_use", []) for b in arch_blocks
        ),
        "internal_style_present": all(
            "internal_only" in b.governance.get("allowed_use", []) and "style_guidance" in b.governance.get("allowed_use", [])
            for b in arch_blocks
        ),
    },
    "true_mixed": {
        "blocks_generated": len(mixed_blocks),
        "chunk_type_counts": dict(Counter([b.governance.get("chunk_type") for b in mixed_blocks])),
        "blocks": [compact(b) for b in mixed_blocks],
        "warning_preserved": any(
            b.chunking_quality.get("mixed_intent_severity") in {"medium", "high"} for b in mixed_blocks
        ),
    },
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
