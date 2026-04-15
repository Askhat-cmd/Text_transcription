from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive


def test_generation_validation_separation_with_single_retry(monkeypatch) -> None:
    def _enabled(name: str) -> bool:
        return name == "USE_OUTPUT_VALIDATION"

    monkeypatch.setattr(adaptive.feature_flags, "enabled", _enabled)
    retry_calls = {"count": 0}

    def _retry(_hint: str):
        retry_calls["count"] += 1
        return {"answer": "Понимаю. Давай сделаем один спокойный шаг и проверим, что сработает."}

    final_text, meta, retry_result = adaptive._apply_output_validation_policy(
        answer="Ты должен сделать это немедленно.",
        route="safe_override",
        mode="VALIDATION",
        generate_retry=_retry,
    )
    assert retry_calls["count"] == 1
    assert isinstance(retry_result, dict)
    assert meta["enabled"] is True
    assert meta["fallback_used"] is False
    assert "должен" not in final_text.lower()
