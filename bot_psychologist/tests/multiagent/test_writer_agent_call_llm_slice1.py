from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice1 as slice1_module


def test_extract_call_llm_slice1_inputs_normalizes_knowledge_and_practice_fields() -> None:
    ctx = {
        "knowledge_answer": {"should_answer_directly": True},
        "practice_gate": {"practice_allowed": False},
        "writer_visible_practice_instruction": "answer_without_practice",
        "philosophy_kernel": {"kernel_version": "v1"},
        "writer_freedom_contract": {"version": "v1"},
        "philosophy_kernel_selected_lenses": ["mechanism", "", 7],
        "writer_freedom_hard_boundaries": ["safety", " ", 5],
        "dialogue_policy": {"profile": "safe_guided"},
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            slice1_module,
            "format_conversation_context_for_writer_with_meta",
            lambda **_: ("FORMATTED", {"context_truncated": False}),
        )
        result = slice1_module._extract_call_llm_slice1_inputs(ctx)

    assert result.knowledge_answer == {"should_answer_directly": True}
    assert result.knowledge_answer_first is True
    assert result.do_not_ask_definition is True
    assert result.practice_allowed is False
    assert result.practice_ban_instruction == "answer_without_practice"
    assert result.known_concept_clarification_ban.endswith("known_concept_variant")
    assert result.external_surveillance_frame_ban.endswith("internal_concept_answer")
    assert result.selected_lenses == ["mechanism", "7"]
    assert result.freedom_hard_boundaries == ["safety", "5"]


def test_extract_call_llm_slice1_inputs_uses_profile_defaults_when_budget_missing() -> None:
    calls: dict[str, object] = {}

    def _fake_normalize(raw: object) -> str:
        calls["normalize_input"] = raw
        return "mvp_free_dialogue"

    def _fake_budget(profile: str) -> int:
        calls["budget_profile"] = profile
        return 1234

    def _fake_format(*, conversation_context: str, profile: str, budget_chars: int) -> tuple[str, dict[str, object]]:
        calls["format"] = {
            "conversation_context": conversation_context,
            "profile": profile,
            "budget_chars": budget_chars,
        }
        return ("CTX", {"budget_chars": budget_chars})

    ctx = {
        "dialogue_policy": {"profile": "alias_value"},
        "conversation_context": "history",
        "user_message": "hello",
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(slice1_module, "normalize_dialogue_profile", _fake_normalize)
        monkeypatch.setattr(slice1_module, "context_budget_for_profile", _fake_budget)
        monkeypatch.setattr(
            slice1_module,
            "format_conversation_context_for_writer_with_meta",
            _fake_format,
        )
        result = slice1_module._extract_call_llm_slice1_inputs(ctx)

    assert result.dialogue_profile == "mvp_free_dialogue"
    assert result.context_budget_chars == 1234
    assert result.formatted_context == "CTX"
    assert result.context_meta == {"budget_chars": 1234}
    assert calls["normalize_input"] == "alias_value"
    assert calls["budget_profile"] == "mvp_free_dialogue"
    assert calls["format"] == {
        "conversation_context": "history",
        "profile": "mvp_free_dialogue",
        "budget_chars": 1234,
    }


def test_extract_call_llm_slice1_inputs_preserves_explicit_dialogue_budget_and_defaults() -> None:
    ctx = {
        "dialogue_profile": "safe_guided",
        "dialogue_policy": {
            "context_budget_chars": "2800",
            "human_like_answer_policy": {"enabled": True},
            "constraint_resolution": {"mode": "soft"},
        },
        "knowledge_answer": [],
        "practice_gate": None,
        "conversation_context": "",
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            slice1_module,
            "format_conversation_context_for_writer_with_meta",
            lambda **_: ("", {"context_truncated": False}),
        )
        result = slice1_module._extract_call_llm_slice1_inputs(ctx)

    assert result.knowledge_answer == {}
    assert result.practice_allowed is True
    assert result.practice_ban_instruction == "false"
    assert result.dialogue_policy_payload["context_budget_chars"] == "2800"
    assert result.human_like_answer_policy == {"enabled": True}
    assert result.constraint_resolution == {"mode": "soft"}
    assert result.context_budget_chars == 2800
