from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import setup_phase8_runtime


def test_legacy_fallback_when_flag_off(monkeypatch) -> None:
    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=1,
        informational_branch_enabled=False,
        answer_text="Legacy fallback path is alive.",
    )

    def _legacy_flags(name: str) -> bool:
        mapping = {
            "INFORMATIONAL_BRANCH_ENABLED": False,
            "USE_NEW_DIAGNOSTICS_V1": False,
            "USE_DETERMINISTIC_ROUTE_RESOLVER": False,
            "USE_PROMPT_STACK_V2": False,
            "USE_OUTPUT_VALIDATION": False,
            "ENABLE_CONDITIONAL_RERANKER": False,
            "ENABLE_FAST_STATE_DETECTOR": False,
            "ENABLE_FAST_SD_DETECTOR": False,
            "DISABLE_SD_RUNTIME": False,
        }
        return bool(mapping.get(name, False))

    monkeypatch.setattr(adaptive.feature_flags, "enabled", _legacy_flags)

    result = adaptive.answer_question_adaptive(
        query="Проверь, что fallback к legacy-поведению работает при выключенных Neo-флагах.",
        user_id="e2e_legacy_fallback",
        debug=True,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["route_resolution_count"] == 0

