from __future__ import annotations

from tools.clean_source_reprocess import build_practice_taxonomy_report


def _mk_block(block_id: str, text: str, chunk_type: str, allowed_use: list[str], safety_flags: list[str]) -> dict:
    return {
        "id": block_id,
        "text": text,
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": allowed_use,
                "safety_flags": safety_flags,
            },
            "chunking_quality": {},
        },
    }


def test_direct_practice_gets_required_safety_bundle() -> None:
    block = _mk_block(
        "d1",
        "Цель: снизить напряжение. Время: 7 минут. Шаг 1: сделай паузу. Шаг 2: дыши медленно.",
        chunk_type="theory",
        allowed_use=["writer_context"],
        safety_flags=[],
    )

    report = build_practice_taxonomy_report(source_prd="PRD-046.0.8-HF1", candidate_blocks=[block])

    assert report["direct_practice_misclassified_count"] == 0
    assert report["unsafe_practice_suggestion_count"] == 0
    gov = block["metadata"]["governance"]
    assert gov["chunk_type"] == "practice"
    assert "practice_suggestion" in gov["allowed_use"]
    assert "not_for_direct_quote" in gov["safety_flags"]
    assert "practice_requires_low_resource_check" in gov["safety_flags"]


def test_case_or_dialogue_is_not_promoted_to_practice() -> None:
    block = _mk_block(
        "d2",
        "Из сессии: клиент говорит, что пробовал практики и продолжает избегать диалога.",
        chunk_type="practice",
        allowed_use=["writer_context", "practice_suggestion"],
        safety_flags=["not_for_direct_quote"],
    )

    report = build_practice_taxonomy_report(source_prd="PRD-046.0.8-HF1", candidate_blocks=[block])

    assert report["case_or_dialogue_about_practice_count"] == 1
    gov = block["metadata"]["governance"]
    assert gov["chunk_type"] == "case"
    assert "practice_suggestion" not in gov["allowed_use"]
