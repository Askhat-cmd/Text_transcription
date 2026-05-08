# -*- coding: utf-8 -*-
import json
from collections import Counter

from chunkers.book_chunker import BookChunker
from governance.governance_adapter import apply_governance_to_blocks_v1
from governance.chunking_quality import build_chunking_quality_v1

PRACTICE_MANUAL = """# Synthetic Practice Manual

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

ARCH_NOTES = """# Neo MindBot Architecture

## Writer Rules

Бот работает как зеркало, навигатор и мягкий катализатор осознавания.
Не становиться духовным авторитетом.
Не заменять психотерапевта.

## Diagnostic Center

Diagnostic Center выбирает линзу, но не показывает внутренние labels пользователю.
"""

MIXED = """# Mixed Source

## Практика и безопасность

Практика: Шаг 1: сделай вдох. Шаг 2: отметь ощущение в теле.
Безопасность: при кризисе и риске самоповреждения нужна экстренная помощь.
"""


chunker = BookChunker(config={"target_tokens": 220, "min_tokens": 60, "max_tokens": 320, "overlap_tokens": 0})


def run_case(text: str, source_kind: str, profile: str, title: str):
    blocks = chunker.chunk_file_from_text(text, "Author", title, "ru")
    blocks = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="synthetic_src",
        source_title=title,
        source_type="book",
        source_kind=source_kind,
        governance_profile=profile,
    )
    for block in blocks:
        block.chunking_quality = build_chunking_quality_v1(block)
    return blocks


practice_blocks = run_case(PRACTICE_MANUAL, "practice_manual", "practice_manual", "Synthetic Practice Manual")
arch_blocks = run_case(ARCH_NOTES, "architecture_notes", "architecture_notes", "Neo MindBot Architecture")
mixed_blocks = run_case(MIXED, "practice_manual", "practice_manual", "Mixed Source")

summary = {
    "practice_manual": {
        "blocks": len(practice_blocks),
        "chunk_type_counts": dict(Counter(block.governance.get("chunk_type") for block in practice_blocks)),
        "practice_steps_count": [
            block.governance.get("practice_metadata", {}).get("steps_count", 0)
            for block in practice_blocks
            if block.governance.get("chunk_type") == "practice"
        ],
        "mixed_intent_risk_count": sum(1 for block in practice_blocks if block.chunking_quality.get("mixed_intent_risk")),
    },
    "architecture_notes": {
        "blocks": len(arch_blocks),
        "chunk_type_counts": dict(Counter(block.governance.get("chunk_type") for block in arch_blocks)),
        "has_internal_only": all("internal_only" in block.governance.get("allowed_use", []) for block in arch_blocks),
        "has_style_guidance": all("style_guidance" in block.governance.get("allowed_use", []) for block in arch_blocks),
        "has_not_for_direct_quote": all("not_for_direct_quote" in block.governance.get("safety_flags", []) for block in arch_blocks),
    },
    "mixed_case": {
        "blocks": len(mixed_blocks),
        "chunk_type_counts": dict(Counter(block.governance.get("chunk_type") for block in mixed_blocks)),
        "mixed_intent_risk_count": sum(1 for block in mixed_blocks if block.chunking_quality.get("mixed_intent_risk")),
    },
}

print(json.dumps(summary, ensure_ascii=False, indent=2))
