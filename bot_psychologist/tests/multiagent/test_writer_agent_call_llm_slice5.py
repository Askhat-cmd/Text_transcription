from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice5 as slice5_module


def test_extract_call_llm_slice5_returns_expected_kb_and_philosophy_fields() -> None:
    ctx = {
        "writer_kb_payload_enabled": True,
        "writer_kb_payload_trace_version": "writer_kb_payload_trace_v9",
        "writer_kb_payload_failed": False,
        "philosophy_kernel_version": "kernel_ctx_v2",
        "philosophy_kernel_quote_policy": "internal_only",
        "philosophy_kernel_prompt_block": "stay grounded",
        "philosophy_kernel_prompt_compactness": {"level": "tight"},
        "writer_freedom_prompt_block": "freedom prompt",
        "writer_freedom_contract_version": "wf_ctx_v2",
        "writer_freedom_level": "high",
        "writer_mode_hint": "dialogue",
        "mode_is_hint_not_cage": False,
        "writer_question_limit": "3",
        "practice_requires_gate": False,
    }
    knowledge_answer = {
        "needed": True,
        "concept": "нейросталкинг",
        "kb_grounding_available": True,
        "writer_instruction": "answer directly",
    }
    philosophy_kernel = {
        "kernel_version": "kernel_fallback_v1",
        "quote_policy": "fallback_policy",
    }
    writer_freedom_contract = {
        "version": "wf_fallback_v1",
        "freedom_level": "guided",
        "mode_hint": "coach",
    }

    result = slice5_module._extract_call_llm_slice5_kb_payload_and_philosophy(
        ctx,
        knowledge_answer,
        True,
        False,
        True,
        philosophy_kernel,
        writer_freedom_contract,
        ["lens_a", "lens_b"],
        ["no_diagnosis", "no_unsolicited_practice"],
    )

    assert result.writer_kb_payload_enabled == "true"
    assert result.writer_kb_payload_trace_version == "writer_kb_payload_trace_v9"
    assert result.writer_kb_payload_failed == "false"
    assert result.knowledge_answer_needed == "true"
    assert result.knowledge_answer_concept == "нейросталкинг"
    assert result.knowledge_answer_kb_grounding == "true"
    assert result.knowledge_answer_first == "true"
    assert result.do_not_ask_user_to_define_term_before_answering == "false"
    assert result.practice_allowed == "true"
    assert result.knowledge_answer_writer_instruction == "answer directly"
    assert result.philosophy_kernel_version == "kernel_ctx_v2"
    assert result.philosophy_kernel_quote_policy == "internal_only"
    assert result.philosophy_kernel_selected_lenses == "lens_a, lens_b"
    assert result.philosophy_kernel_prompt_block == "stay grounded"
    assert result.philosophy_kernel_prompt_compactness == "{'level': 'tight'}"
    assert result.writer_freedom_prompt_block == "freedom prompt"
    assert result.writer_freedom_contract_version == "wf_ctx_v2"
    assert result.writer_freedom_level == "high"
    assert result.writer_mode_hint == "dialogue"
    assert result.mode_is_hint_not_cage == "false"
    assert result.writer_question_limit == 3
    assert result.practice_requires_gate == "false"
    assert result.writer_freedom_hard_boundaries == "no_diagnosis, no_unsolicited_practice"


def test_extract_call_llm_slice5_applies_fallbacks_and_defaults() -> None:
    result = slice5_module._extract_call_llm_slice5_kb_payload_and_philosophy(
        {},
        {},
        False,
        True,
        False,
        {},
        {},
        [],
        [],
    )

    assert result.writer_kb_payload_enabled == "false"
    assert result.writer_kb_payload_trace_version == "writer_kb_payload_trace_v1"
    assert result.writer_kb_payload_failed == "false"
    assert result.knowledge_answer_needed == "false"
    assert result.knowledge_answer_concept == "none"
    assert result.knowledge_answer_kb_grounding == "false"
    assert result.knowledge_answer_first == "false"
    assert result.do_not_ask_user_to_define_term_before_answering == "true"
    assert result.practice_allowed == "false"
    assert result.knowledge_answer_writer_instruction == "none"
    assert result.philosophy_kernel_version == ""
    assert result.philosophy_kernel_quote_policy == "internal_lens_not_citation"
    assert result.philosophy_kernel_selected_lenses == "none"
    assert result.philosophy_kernel_prompt_block == "none"
    assert result.philosophy_kernel_prompt_compactness == "{}"
    assert result.writer_freedom_prompt_block == "none"
    assert result.writer_freedom_contract_version == ""
    assert result.writer_freedom_level == "guided"
    assert result.writer_mode_hint == ""
    assert result.mode_is_hint_not_cage == "true"
    assert result.writer_question_limit == 1
    assert result.practice_requires_gate == "true"
    assert result.writer_freedom_hard_boundaries == "no_diagnosis,no_unsolicited_practice"


def test_extract_call_llm_slice5_prefers_ctx_over_fallback_objects() -> None:
    result = slice5_module._extract_call_llm_slice5_kb_payload_and_philosophy(
        {
            "philosophy_kernel_version": "",
            "philosophy_kernel_quote_policy": "",
            "writer_freedom_contract_version": "",
            "writer_freedom_level": "",
            "writer_mode_hint": "",
        },
        {"writer_instruction": ""},
        False,
        False,
        True,
        {
            "kernel_version": "fallback_kernel_v3",
            "quote_policy": "fallback_quote_policy",
        },
        {
            "version": "fallback_contract_v4",
            "freedom_level": "fallback_level",
            "mode_hint": "fallback_mode",
        },
        ["single_lens"],
        ["bound_a"],
    )

    assert result.knowledge_answer_writer_instruction == "none"
    assert result.philosophy_kernel_version == ""
    assert result.philosophy_kernel_quote_policy == ""
    assert result.writer_freedom_contract_version == ""
    assert result.writer_freedom_level == ""
    assert result.writer_mode_hint == ""
    assert result.philosophy_kernel_selected_lenses == "single_lens"
    assert result.writer_freedom_hard_boundaries == "bound_a"
