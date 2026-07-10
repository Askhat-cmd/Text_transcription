from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice2 as slice2_module


def test_extract_call_llm_slice2_request_detectors_returns_safe_guided_defaults() -> None:
    result = slice2_module._extract_call_llm_slice2_request_detectors(
        dialogue_policy_payload={},
        user_message="просто поддержи без практик",
        constraint_resolution={},
        dialogue_profile="safe_guided",
    )

    assert result.explicit_answer_need is False
    assert result.sarcasm_or_negative_feedback is False
    assert result.repair_user_dissatisfaction is False
    assert result.overruled_constraints == []
    assert result.mvp_override_block == "not_applicable_for_safe_guided_profile"


def test_extract_call_llm_slice2_request_detectors_builds_mvp_override_block_from_payload_and_detectors() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(slice2_module, "detect_practice_overview_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_examples_request", lambda _: True)
        monkeypatch.setattr(slice2_module, "detect_numbered_list_request", lambda _: True)
        monkeypatch.setattr(slice2_module, "detect_expansion_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_explicit_answer_need", lambda _: True)
        monkeypatch.setattr(slice2_module, "detect_direct_concrete_request", lambda _: True)
        monkeypatch.setattr(slice2_module, "detect_summary_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_sarcasm_or_negative_feedback", lambda _: True)
        monkeypatch.setattr(slice2_module, "detect_application_request", lambda _: False)

        result = slice2_module._extract_call_llm_slice2_request_detectors(
            dialogue_policy_payload={
                "answer_depth": "short",
                "mvp_overrides": {
                    "explicit_user_request_wins": True,
                    "old_max_sentence_constraints_softened": False,
                    "planner_advisory": True,
                    "overview_questions_allow_lists": False,
                    "target_answer_depth": "deep",
                },
                "repair_and_expand_requested": True,
            },
            user_message="дай пример и список",
            constraint_resolution={"overruled_constraints": ["short_answer", "", " tone "]},
            dialogue_profile=slice2_module.DIALOGUE_PROFILE_MVP_FREE,
        )

    assert result.explicit_answer_need is True
    assert result.sarcasm_or_negative_feedback is True
    assert result.repair_user_dissatisfaction is True
    assert result.overruled_constraints == ["short_answer", " tone "]
    assert result.mvp_override_block == "\n".join(
        [
            "MVP FREE DIALOGUE OVERRIDES:",
            "- explicit_user_request_wins=true",
            "- old_max_sentence_constraints_softened=false",
            "- planner_advisory=true",
            "- overview_questions_allow_lists=false",
            "- target_answer_depth=deep",
            "- rich_user_request_detected=true",
            "- explicit_answer_need=true",
            "- direct_concrete_request=true",
            "- summary_request=false",
            "- sarcasm_or_negative_feedback=true",
        ]
    )


def test_extract_call_llm_slice2_request_detectors_keeps_repair_override_even_without_detector_signal() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(slice2_module, "detect_practice_overview_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_examples_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_numbered_list_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_expansion_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_explicit_answer_need", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_direct_concrete_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_summary_request", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_sarcasm_or_negative_feedback", lambda _: False)
        monkeypatch.setattr(slice2_module, "detect_application_request", lambda _: False)

        result = slice2_module._extract_call_llm_slice2_request_detectors(
            dialogue_policy_payload={"mvp_overrides": {"repair_user_dissatisfaction": True}},
            user_message="",
            constraint_resolution={"overruled_constraints": ["", "keep_me"]},
            dialogue_profile=slice2_module.DIALOGUE_PROFILE_MVP_FREE,
        )

    assert result.explicit_answer_need is False
    assert result.sarcasm_or_negative_feedback is False
    assert result.repair_user_dissatisfaction is True
    assert result.overruled_constraints == ["keep_me"]
    assert "- rich_user_request_detected=false" in result.mvp_override_block
