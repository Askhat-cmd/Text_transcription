from __future__ import annotations

from tools.clean_source_reprocess import build_practice_like_report


def test_practice_like_markers_and_safe_preview() -> None:
    long_text = (
        "Цель: снизить тревогу. "
        "Время: 7 минут. "
        "Шаг 1: Сядь удобно и дыши. "
        + ("Очень длинный текст " * 40)
    )
    payload = build_practice_like_report(
        source_prd="PRD-046.0.8",
        candidate_blocks=[
            {
                "id": "b1",
                "text": long_text,
                "metadata": {"governance": {"chunk_type": "lens", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]}},
            }
        ],
    )
    assert payload["practice_like_candidates_count"] == 1
    assert payload["practice_like_misclassified_count"] == 1
    example = payload["misclassified_examples"][0]
    assert len(example["safe_preview"]) <= 240
    assert "Цель:" in long_text
