from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent import answer_adaptive
from bot_agent.state_classifier import StateAnalysis, UserState


async def _fake_state_classifier(*_args, **_kwargs) -> StateAnalysis:
    return StateAnalysis(
        primary_state=UserState.CURIOUS,
        confidence=0.9,
        secondary_states=[],
        indicators=["test"],
        emotional_tone="neutral",
        depth="surface",
        recommendations=["stay curious"],
    )


class _FailingSDClassifier:
    async def classify_user(self, *_args, **_kwargs):
        raise AssertionError("sd_classifier.classify_user should not be called when DISABLE_SD_RUNTIME=true")


def test_sd_runtime_disabled_skips_sd_classifier(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "true")
    monkeypatch.setattr(answer_adaptive.state_classifier, "classify", _fake_state_classifier)
    monkeypatch.setattr(answer_adaptive, "sd_classifier", _FailingSDClassifier())

    state_result, sd_result = asyncio.run(
        answer_adaptive._classify_parallel(
            user_message="хочу разобраться",
            history_state=[],
            history_sd=[],
            user_sd_profile=None,
        )
    )

    assert state_result.primary_state == UserState.CURIOUS
    assert sd_result.method == "fallback"
    assert sd_result.indicator == "disabled_by_flag"
