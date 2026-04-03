from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive


def test_sparse_output_triggers_regeneration_hint() -> None:
    captured: dict[str, str] = {}

    def _retry_generate(hint: str) -> dict:
        captured["hint"] = hint
        return {
            "answer": (
                "Избегание — это попытка снизить внутреннее напряжение ценой отказа от значимых действий. "
                "В отличие от осознанной паузы, избегание обычно сужает выбор и усиливает тревогу. "
                "Например, откладывание важного разговора временно успокаивает, но закрепляет страх."
            )
        }

    answer, meta, _retry_payload = adaptive._apply_output_validation_policy(
        answer="Избегание — это уход от сложного. Что из этого тебе ближе?",
        query="Объясни избегание и чем оно отличается от осознанной паузы",
        route="inform",
        mode="CLARIFICATION",
        generate_retry_fn=_retry_generate,
    )

    assert "hint" in captured
    assert "сравни по 2-3 критериям" in captured["hint"].lower()
    assert meta["enabled"] is True
    assert len(meta["attempts"]) == 2
    assert meta["final_valid"] is True
    assert "в отличие" in answer.lower()
