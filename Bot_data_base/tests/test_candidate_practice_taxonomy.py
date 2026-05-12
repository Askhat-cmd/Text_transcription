from __future__ import annotations

from tools.clean_source_reprocess import build_practice_taxonomy_report


def _mk_block(block_id: str, text: str, chunk_type: str = "lens", allowed_use: list[str] | None = None) -> dict:
    return {
        "id": block_id,
        "text": text,
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": allowed_use or ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            },
            "chunking_quality": {},
        },
    }


def test_practice_taxonomy_detects_direct_protocol_and_calibrates_chunk() -> None:
    block = _mk_block(
        "b1",
        "Цель: снизить тревогу. Время: 5 минут. Шаг 1: дыши. Шаг 2: отметь состояние.",
        chunk_type="lens",
    )
    report = build_practice_taxonomy_report(source_prd="PRD-046.0.8-HF1", candidate_blocks=[block])

    assert report["direct_practice_protocol_count"] == 1
    assert report["direct_practice_misclassified_count"] == 0
    gov = block["metadata"]["governance"]
    assert gov["chunk_type"] == "practice"
    assert "practice_suggestion" in gov["allowed_use"]
    assert "practice_requires_low_resource_check" in gov["safety_flags"]


def test_practice_taxonomy_marks_contextual_mentions_and_removes_practice_suggestion() -> None:
    block = _mk_block(
        "b2",
        "Эта глава объясняет, почему практика закрепляет навык, но не дает пошаговый протокол.",
        chunk_type="practice",
        allowed_use=["writer_context", "practice_suggestion"],
    )
    report = build_practice_taxonomy_report(source_prd="PRD-046.0.8-HF1", candidate_blocks=[block])

    assert report["practice_context_or_theory_count"] == 1
    assert report["unsafe_practice_suggestion_count"] == 0
    assert report["contextual_false_positive_count"] == 0
    gov = block["metadata"]["governance"]
    assert gov["chunk_type"] == "lens"
    assert "practice_suggestion" not in gov["allowed_use"]
